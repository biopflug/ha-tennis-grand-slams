"""Client for ESPN tennis scoreboard data."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
import logging
from typing import Any

from aiohttp import ClientError, ClientSession

from .const import ESPN_SCOREBOARD, ESPN_SCOREBOARD_URL, SLAM_DEFINITIONS, TOURS

_LOGGER = logging.getLogger(__name__)


class TennisGrandSlamError(Exception):
    """Base error for the integration."""


@dataclass(slots=True)
class Match:
    """Normalized tennis match."""

    id: str
    name: str
    short_name: str
    tournament: str
    tournament_key: str | None
    tour: str
    state: str
    status: str
    start_time: datetime | None
    competitors: list[dict[str, Any]] = field(default_factory=list)
    detail: str | None = None
    url: str = ESPN_SCOREBOARD_URL

    @property
    def is_live(self) -> bool:
        return self.state == "in"

    @property
    def is_upcoming(self) -> bool:
        return self.state == "pre"

    @property
    def is_complete(self) -> bool:
        return self.state == "post"

    def as_dict(self) -> dict[str, Any]:
        """Return match as serializable dict."""
        return {
            "id": self.id,
            "name": self.name,
            "short_name": self.short_name,
            "tournament": self.tournament,
            "tour": self.tour.upper(),
            "state": self.state,
            "status": self.status,
            "detail": self.detail,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "competitors": self.competitors,
            "url": self.url,
        }


@dataclass(slots=True)
class SlamWindow:
    """Current or future Grand Slam window."""

    key: str
    name: str
    location: str
    start: date
    end: date
    official_url: str
    espn_url: str = ESPN_SCOREBOARD_URL

    def as_dict(self, today: date | None = None) -> dict[str, Any]:
        today = today or date.today()
        active = self.start <= today <= self.end
        days = (self.end - today).days if active else (self.start - today).days
        return {
            "key": self.key,
            "name": self.name,
            "location": self.location,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "status": "Läuft aktuell" if active else "Nächstes Grand Slam",
            "days": days,
            "days_text": f"noch {days} Tage" if active else f"in {days} Tagen",
            "official_url": self.official_url,
            "espn_url": self.espn_url,
        }


@dataclass(slots=True)
class TennisData:
    """All normalized data."""

    current_slam: SlamWindow | None
    next_slam: SlamWindow | None
    slam_windows: list[SlamWindow]
    live_matches: list[Match]
    upcoming_matches: list[Match]
    recent_results: list[Match]
    all_matches: list[Match]
    generated_at: datetime


class ESPNClient:
    """Small ESPN scoreboard client.

    ESPN tennis endpoints are undocumented but power ESPN's public tennis scoreboard.
    The integration is deliberately defensive because the response shape can change.
    """

    def __init__(
        self,
        session: ClientSession,
        *,
        region: str,
        language: str,
        days_ahead: int,
    ) -> None:
        self._session = session
        self._region = region
        self._language = language
        self._days_ahead = days_ahead

    async def async_get_data(self) -> TennisData:
        """Fetch and normalize all tennis data."""
        today = datetime.now(timezone.utc).date()
        start = today - timedelta(days=7)
        end = today + timedelta(days=self._days_ahead)
        raw_payloads = await asyncio.gather(
            *(self._async_fetch_scoreboard(tour, start, end) for tour in TOURS),
            return_exceptions=True,
        )

        events: list[dict[str, Any]] = []
        for tour, payload in zip(TOURS, raw_payloads, strict=False):
            if isinstance(payload, Exception):
                _LOGGER.warning("Could not fetch %s tennis data: %s", tour.upper(), payload)
                continue
            for event in payload.get("events", []) or []:
                event["_tour"] = tour
                events.append(event)

        matches = [self._event_to_match(event) for event in events]
        matches = [match for match in matches if match is not None]
        slam_windows = self._build_slam_windows(matches, today)

        current = next((s for s in slam_windows if s.start <= today <= s.end), None)
        upcoming = [s for s in slam_windows if s.start > today]
        next_slam = min(upcoming, key=lambda s: s.start) if upcoming else None

        relevant_key = current.key if current else next_slam.key if next_slam else None
        relevant_matches = [m for m in matches if relevant_key and m.tournament_key == relevant_key]

        return TennisData(
            current_slam=current,
            next_slam=next_slam,
            slam_windows=slam_windows,
            live_matches=sorted([m for m in relevant_matches if m.is_live], key=self._sort_match),
            upcoming_matches=sorted([m for m in relevant_matches if m.is_upcoming], key=self._sort_match)[:30],
            recent_results=sorted([m for m in relevant_matches if m.is_complete], key=self._sort_match, reverse=True)[:20],
            all_matches=sorted(relevant_matches, key=self._sort_match),
            generated_at=datetime.now(timezone.utc),
        )

    async def _async_fetch_scoreboard(self, tour: str, start: date, end: date) -> dict[str, Any]:
        params = {
            "region": self._region,
            "lang": self._language,
            "dates": f"{start:%Y%m%d}-{end:%Y%m%d}",
            "limit": "1000",
        }
        url = ESPN_SCOREBOARD.format(tour=tour)
        try:
            async with self._session.get(url, params=params, timeout=20) as response:
                response.raise_for_status()
                return await response.json(content_type=None)
        except (ClientError, asyncio.TimeoutError) as exc:
            raise TennisGrandSlamError(str(exc)) from exc

    def _event_to_match(self, event: dict[str, Any]) -> Match | None:
        tournament_name = self._extract_tournament_name(event)
        tournament_key = self._match_slam_key(tournament_name or event.get("name", ""))
        if tournament_key is None:
            return None

        competitions = event.get("competitions") or []
        competition = competitions[0] if competitions else {}
        status = competition.get("status") or event.get("status") or {}
        status_type = status.get("type") or {}
        state = (status_type.get("state") or "pre").lower()
        status_text = status_type.get("shortDetail") or status_type.get("detail") or status_type.get("description") or state
        detail = status_type.get("detail") or status_text
        start_time = self._parse_dt(event.get("date") or competition.get("date"))
        competitors = []
        for comp in competition.get("competitors", []) or []:
            athlete = comp.get("athlete") or comp.get("team") or {}
            competitors.append(
                {
                    "name": athlete.get("displayName") or athlete.get("name") or comp.get("displayName"),
                    "short_name": athlete.get("shortName") or comp.get("abbreviation"),
                    "score": comp.get("score"),
                    "winner": comp.get("winner"),
                    "home_away": comp.get("homeAway"),
                    "seed": comp.get("curatedRank") or comp.get("rank"),
                    "sets": self._extract_linescores(comp),
                }
            )

        links = event.get("links") or competition.get("links") or []
        url = next((link.get("href") for link in links if link.get("href")), ESPN_SCOREBOARD_URL)

        return Match(
            id=str(event.get("id") or competition.get("id") or ""),
            name=event.get("name") or competition.get("name") or "Tennis match",
            short_name=event.get("shortName") or competition.get("shortName") or event.get("name") or "Tennis",
            tournament=tournament_name or SLAM_DEFINITIONS[tournament_key]["name"],
            tournament_key=tournament_key,
            tour=(event.get("_tour") or "").lower(),
            state=state,
            status=status_text,
            start_time=start_time,
            competitors=competitors,
            detail=detail,
            url=url,
        )

    @staticmethod
    def _extract_linescores(comp: dict[str, Any]) -> list[Any]:
        linescores = comp.get("linescores") or []
        return [line.get("value", line) if isinstance(line, dict) else line for line in linescores]

    @staticmethod
    def _extract_tournament_name(event: dict[str, Any]) -> str:
        candidates: list[str] = []
        for key in ("season", "league", "group"):
            obj = event.get(key) or {}
            if isinstance(obj, dict):
                candidates.extend(str(obj.get(k, "")) for k in ("name", "displayName", "description"))
        competitions = event.get("competitions") or []
        for competition in competitions:
            tournament = competition.get("tournament") or competition.get("series") or {}
            if isinstance(tournament, dict):
                candidates.extend(str(tournament.get(k, "")) for k in ("name", "displayName", "description"))
        candidates.extend(str(event.get(k, "")) for k in ("name", "shortName"))
        return next((c for c in candidates if c and c.lower() != "none"), "")

    @staticmethod
    def _match_slam_key(text: str) -> str | None:
        haystack = text.lower()
        for key, slam in SLAM_DEFINITIONS.items():
            if any(alias in haystack for alias in slam["aliases"]):
                return key
        return None

    def _build_slam_windows(self, matches: list[Match], today: date) -> list[SlamWindow]:
        grouped: dict[str, list[date]] = {key: [] for key in SLAM_DEFINITIONS}
        for match in matches:
            if match.tournament_key and match.start_time:
                grouped[match.tournament_key].append(match.start_time.date())

        windows: list[SlamWindow] = []
        for key, dates in grouped.items():
            if not dates:
                continue
            slam = SLAM_DEFINITIONS[key]
            # ESPN sometimes only returns main draw event dates. Padding gives a nicer dashboard window.
            start = min(dates)
            end = max(dates)
            if (end - start).days < 10:
                start = start - timedelta(days=1)
                end = end + timedelta(days=1)
            windows.append(
                SlamWindow(
                    key=key,
                    name=slam["name"],
                    location=slam["location"],
                    start=start,
                    end=end,
                    official_url=slam["official_url"],
                )
            )

        # If ESPN returns no Grand Slam events at all, keep HA useful with conservative seasonal guesses.
        if not windows:
            windows = self._fallback_windows(today.year)
        elif not any(s.start >= today for s in windows) and today.month >= 9:
            windows.extend(self._fallback_windows(today.year + 1))

        return sorted({(w.key, w.start): w for w in windows}.values(), key=lambda w: w.start)

    @staticmethod
    def _fallback_windows(year: int) -> list[SlamWindow]:
        defs = SLAM_DEFINITIONS
        return [
            SlamWindow("australian_open", defs["australian_open"]["name"], defs["australian_open"]["location"], date(year, 1, 15), date(year, 1, 29), defs["australian_open"]["official_url"]),
            SlamWindow("french_open", defs["french_open"]["name"], defs["french_open"]["location"], date(year, 5, 24), date(year, 6, 7), defs["french_open"]["official_url"]),
            SlamWindow("wimbledon", defs["wimbledon"]["name"], defs["wimbledon"]["location"], date(year, 6, 29), date(year, 7, 12), defs["wimbledon"]["official_url"]),
            SlamWindow("us_open", defs["us_open"]["name"], defs["us_open"]["location"], date(year, 8, 31), date(year, 9, 13), defs["us_open"]["official_url"]),
        ]

    @staticmethod
    def _parse_dt(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    @staticmethod
    def _sort_match(match: Match) -> datetime:
        return match.start_time or datetime.min.replace(tzinfo=timezone.utc)
