"""Client for ESPN tennis scoreboard data."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
import logging
from typing import Any, Iterable

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
    score: str | None = None
    round: str | None = None
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
            "score": self.score,
            "round": self.round,
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
    debug: dict[str, Any] = field(default_factory=dict)


class ESPNClient:
    """Small ESPN tennis scoreboard client.

    v0.1.3 is deliberately more tolerant than v0.1.2:
    - it fetches day requests, one date-range request and the default scoreboard;
    - it uses the built-in Grand Slam calendar to classify matches when ESPN's
      event payload does not explicitly contain "French Open"/"Roland Garros";
    - it exposes debug counters so the dashboard can show whether ESPN returned
      raw events but the parser filtered them out.
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
        slam_windows = self._fallback_windows(today.year) + self._fallback_windows(today.year + 1)
        current = next((s for s in slam_windows if s.start <= today <= s.end), None)
        upcoming_slams = [s for s in slam_windows if s.start > today]
        next_slam = min(upcoming_slams, key=lambda s: s.start) if upcoming_slams else None
        relevant_key = current.key if current else next_slam.key if next_slam else None

        fetch_start, fetch_end = self._scoreboard_window(today, current, next_slam)
        fetch_dates = list(self._date_range(fetch_start, fetch_end))

        requests: list[tuple[str, str, date | tuple[date, date] | None]] = []
        for tour in TOURS:
            # Today/default endpoint often works best for live scoreboards.
            requests.append((tour, "default", None))
            requests.append((tour, "range", (fetch_start, fetch_end)))
            for day in fetch_dates:
                requests.append((tour, "day", day))

        raw_payloads = await asyncio.gather(
            *(self._async_fetch_scoreboard(tour, mode, value) for tour, mode, value in requests),
            return_exceptions=True,
        )

        events: list[dict[str, Any]] = []
        fetch_errors = 0
        for (tour, mode, value), payload in zip(requests, raw_payloads, strict=False):
            if isinstance(payload, Exception):
                fetch_errors += 1
                _LOGGER.debug("Could not fetch %s tennis data (%s %s): %s", tour.upper(), mode, value, payload)
                continue
            for event in payload.get("events", []) or []:
                event = dict(event)
                event["_tour"] = tour
                event["_query_mode"] = mode
                event["_query_date"] = value.isoformat() if isinstance(value, date) else None
                events.append(event)

        matches: list[Match] = []
        seen_ids: set[str] = set()
        dropped_no_players = 0
        dropped_not_slam = 0
        for event in events:
            event_matches = self._event_to_matches(event, current=current, relevant_key=relevant_key)
            if not event_matches:
                # These counters are approximate but helpful in HA attributes.
                if self._looks_like_match_shell(event):
                    dropped_no_players += 1
                else:
                    dropped_not_slam += 1
            for match in event_matches:
                if match.id in seen_ids:
                    continue
                seen_ids.add(match.id)
                matches.append(match)

        relevant_matches = [m for m in matches if relevant_key and m.tournament_key == relevant_key]

        live_matches = [m for m in relevant_matches if m.is_live]
        upcoming_matches = [
            m for m in relevant_matches
            if m.is_upcoming and (m.start_time is None or m.start_time.date() >= today)
        ]
        recent_results = [
            m for m in relevant_matches
            if m.is_complete and (m.start_time is None or m.start_time.date() >= today - timedelta(days=5))
        ]

        debug = {
            "fetch_start": fetch_start.isoformat(),
            "fetch_end": fetch_end.isoformat(),
            "requests": len(requests),
            "fetch_errors": fetch_errors,
            "raw_events": len(events),
            "parsed_matches": len(matches),
            "relevant_matches": len(relevant_matches),
            "dropped_no_players_or_shells": dropped_no_players,
            "dropped_not_slam": dropped_not_slam,
            "relevant_key": relevant_key,
            "current_slam": current.name if current else None,
        }

        return TennisData(
            current_slam=current,
            next_slam=next_slam,
            slam_windows=slam_windows,
            live_matches=sorted(live_matches, key=self._sort_match),
            upcoming_matches=sorted(upcoming_matches, key=self._sort_match)[:60],
            recent_results=sorted(recent_results, key=self._sort_match, reverse=True)[:50],
            all_matches=sorted(relevant_matches, key=self._sort_match),
            generated_at=datetime.now(timezone.utc),
            debug=debug,
        )

    def _scoreboard_window(
        self,
        today: date,
        current: SlamWindow | None,
        next_slam: SlamWindow | None,
    ) -> tuple[date, date]:
        """Return the date window used for scoreboard requests."""
        look_back = today - timedelta(days=2)
        if current:
            # During a running slam, the user mostly needs today + coming days.
            return max(current.start, look_back), min(current.end, today + timedelta(days=7))
        if next_slam:
            return max(today, next_slam.start - timedelta(days=1)), min(next_slam.end, next_slam.start + timedelta(days=7))
        return look_back, today + timedelta(days=7)

    @staticmethod
    def _date_range(start: date, end: date) -> Iterable[date]:
        if end < start:
            end = start
        max_days = 14
        for offset in range(min((end - start).days + 1, max_days)):
            yield start + timedelta(days=offset)

    async def _async_fetch_scoreboard(
        self,
        tour: str,
        mode: str,
        value: date | tuple[date, date] | None,
    ) -> dict[str, Any]:
        params: dict[str, str] = {
            "region": self._region,
            "lang": self._language,
            "limit": "1000",
        }
        if mode == "day" and isinstance(value, date):
            params["dates"] = f"{value:%Y%m%d}"
        elif mode == "range" and isinstance(value, tuple):
            start, end = value
            params["dates"] = f"{start:%Y%m%d}-{end:%Y%m%d}"

        url = ESPN_SCOREBOARD.format(tour=tour)
        try:
            async with self._session.get(url, params=params, timeout=20) as response:
                response.raise_for_status()
                return await response.json(content_type=None)
        except (ClientError, asyncio.TimeoutError) as exc:
            raise TennisGrandSlamError(str(exc)) from exc

    def _event_to_matches(
        self,
        event: dict[str, Any],
        *,
        current: SlamWindow | None,
        relevant_key: str | None,
    ) -> list[Match]:
        """Convert one ESPN event to zero, one or many match entities."""
        tournament_name = self._extract_tournament_name(event)
        text_for_key = " ".join([
            tournament_name,
            str(event.get("name", "")),
            str(event.get("shortName", "")),
            str(event.get("uid", "")),
        ])
        tournament_key = self._match_slam_key(text_for_key)

        # ESPN tennis payloads sometimes lack the tournament name on match rows.
        # If we are currently inside a Grand Slam window and the event date is in
        # that window, classify the match as the current slam instead of dropping it.
        event_day = self._event_date(event)
        if tournament_key is None and current and event_day and current.start <= event_day <= current.end:
            tournament_key = current.key
            tournament_name = current.name

        if tournament_key is None:
            return []
        if relevant_key and tournament_key != relevant_key:
            return []

        competitions = event.get("competitions") or []
        if not competitions:
            # Some ESPN responses model the match directly as an event.
            competitions = [event]

        matches: list[Match] = []
        for competition in competitions:
            competitors = self._extract_competitors(competition)
            if len([c for c in competitors if c.get("name")]) < 2:
                # Last fallback: parse "Player A vs Player B" from name/shortName.
                parsed = self._parse_names_from_text(competition.get("name") or event.get("name") or "")
                if len(parsed) >= 2:
                    competitors = [
                        {"name": parsed[0], "short_name": parsed[0], "score": None, "winner": None, "sets": []},
                        {"name": parsed[1], "short_name": parsed[1], "score": None, "winner": None, "sets": []},
                    ]
            real_names = [c.get("name") for c in competitors if c.get("name")]
            if len(real_names) < 2:
                continue

            status = competition.get("status") or event.get("status") or {}
            status_type = status.get("type") or {}
            state = self._normalize_state(status_type)
            status_text = (
                status_type.get("shortDetail")
                or status_type.get("detail")
                or status_type.get("description")
                or status.get("displayClock")
                or state
            )
            detail = status_type.get("detail") or status_text
            start_time = self._parse_dt(competition.get("date") or event.get("date"))

            round_name = self._extract_round(event, competition)
            name = self._match_name(real_names, event, competition)
            short_name = self._short_match_name(competitors, name)
            score = self._format_score(competitors)

            links = competition.get("links") or event.get("links") or []
            url = next((link.get("href") for link in links if link.get("href")), ESPN_SCOREBOARD_URL)

            identifier = str(competition.get("id") or event.get("id") or f"{short_name}-{start_time}-{event.get('_tour')}")
            matches.append(
                Match(
                    id=f"{event.get('_tour','tennis')}-{identifier}",
                    name=name,
                    short_name=short_name,
                    tournament=tournament_name or SLAM_DEFINITIONS[tournament_key]["name"],
                    tournament_key=tournament_key,
                    tour=(event.get("_tour") or "").lower(),
                    state=state,
                    status=status_text,
                    start_time=start_time,
                    competitors=competitors,
                    detail=detail,
                    score=score,
                    round=round_name,
                    url=url,
                )
            )
        return matches

    def _event_date(self, event: dict[str, Any]) -> date | None:
        parsed = self._parse_dt(event.get("date"))
        if parsed:
            return parsed.date()
        query_date = event.get("_query_date")
        if query_date:
            try:
                return date.fromisoformat(query_date)
            except ValueError:
                return None
        return None

    @staticmethod
    def _normalize_state(status_type: dict[str, Any]) -> str:
        state = str(status_type.get("state") or "").lower()
        if state in {"pre", "in", "post"}:
            return state
        if status_type.get("completed") is True:
            return "post"
        description = str(status_type.get("description") or status_type.get("name") or "").lower()
        if any(token in description for token in ("final", "complete", "completed", "ended")):
            return "post"
        if any(token in description for token in ("in progress", "live", "set", "game")):
            return "in"
        return "pre"

    @staticmethod
    def _looks_like_match_shell(event: dict[str, Any]) -> bool:
        text = " ".join(str(event.get(k, "")) for k in ("name", "shortName"))
        return bool(text.strip())

    def _extract_competitors(self, competition: dict[str, Any]) -> list[dict[str, Any]]:
        source = competition.get("competitors") or competition.get("competitions") or []
        competitors: list[dict[str, Any]] = []
        for comp in source:
            if not isinstance(comp, dict):
                continue
            athlete = comp.get("athlete") or comp.get("team") or comp.get("competitor") or {}
            name = (
                athlete.get("displayName")
                or athlete.get("fullName")
                or athlete.get("name")
                or comp.get("displayName")
                or comp.get("name")
            )
            short_name = (
                athlete.get("shortName")
                or athlete.get("abbreviation")
                or comp.get("abbreviation")
                or name
            )
            competitors.append(
                {
                    "name": name,
                    "short_name": short_name,
                    "score": comp.get("score") or comp.get("displayScore"),
                    "winner": comp.get("winner"),
                    "home_away": comp.get("homeAway"),
                    "seed": comp.get("curatedRank") or comp.get("rank") or athlete.get("seed"),
                    "sets": self._extract_linescores(comp),
                }
            )
        return competitors

    @staticmethod
    def _extract_linescores(comp: dict[str, Any]) -> list[Any]:
        linescores = comp.get("linescores") or []
        values: list[Any] = []
        for line in linescores:
            if isinstance(line, dict):
                values.append(line.get("displayValue") or line.get("value") or line.get("score") or line)
            else:
                values.append(line)
        return values

    @staticmethod
    def _parse_names_from_text(text: str) -> list[str]:
        if not text:
            return []
        lowered = text.replace(" v. ", " vs ").replace(" vs. ", " vs ")
        for sep in (" vs ", " VS ", " v ", " @ "):
            if sep in lowered:
                parts = [p.strip(" -–—") for p in lowered.split(sep, 1)]
                if len(parts) == 2 and all(parts):
                    return parts
        return []

    @staticmethod
    def _match_name(real_names: list[str], event: dict[str, Any], competition: dict[str, Any]) -> str:
        if len(real_names) >= 2:
            return f"{real_names[0]} vs. {real_names[1]}"
        return competition.get("name") or event.get("name") or "Tennis Match"

    @staticmethod
    def _short_match_name(competitors: list[dict[str, Any]], fallback: str) -> str:
        names = [c.get("short_name") or c.get("name") for c in competitors if c.get("short_name") or c.get("name")]
        if len(names) >= 2:
            return f"{names[0]} vs. {names[1]}"
        return fallback

    @staticmethod
    def _format_score(competitors: list[dict[str, Any]]) -> str | None:
        if len(competitors) < 2:
            return None
        set_parts: list[str] = []
        left_sets = competitors[0].get("sets") or []
        right_sets = competitors[1].get("sets") or []
        for left, right in zip(left_sets, right_sets, strict=False):
            if left in (None, "") or right in (None, ""):
                continue
            set_parts.append(f"{left}:{right}")
        if set_parts:
            return ", ".join(set_parts)

        left_score = competitors[0].get("score")
        right_score = competitors[1].get("score")
        if left_score not in (None, "") and right_score not in (None, ""):
            return f"{left_score}:{right_score}"
        return None

    @staticmethod
    def _extract_round(event: dict[str, Any], competition: dict[str, Any]) -> str | None:
        candidates: list[str] = []
        for obj in (competition.get("round"), event.get("round"), competition.get("type"), event.get("type"), competition.get("group"), event.get("group")):
            if isinstance(obj, dict):
                candidates.extend(str(obj.get(k, "")) for k in ("displayName", "name", "description", "abbreviation"))
            elif obj:
                candidates.append(str(obj))
        return next((c for c in candidates if c and c.lower() != "none"), None)

    @staticmethod
    def _extract_tournament_name(event: dict[str, Any]) -> str:
        candidates: list[str] = []
        candidates.extend(str(event.get(k, "")) for k in ("name", "shortName", "uid"))
        for key in ("season", "league", "group"):
            obj = event.get(key) or {}
            if isinstance(obj, dict):
                candidates.extend(str(obj.get(k, "")) for k in ("name", "displayName", "description", "slug"))
        for competition in event.get("competitions") or []:
            tournament = competition.get("tournament") or competition.get("series") or competition.get("group") or {}
            if isinstance(tournament, dict):
                candidates.extend(str(tournament.get(k, "")) for k in ("name", "displayName", "description", "slug"))
        return next((c for c in candidates if c and c.lower() != "none"), "")

    @staticmethod
    def _match_slam_key(text: str) -> str | None:
        haystack = text.lower()
        for key, slam in SLAM_DEFINITIONS.items():
            if any(alias in haystack for alias in slam["aliases"]):
                return key
        return None

    @staticmethod
    def _fallback_windows(year: int) -> list[SlamWindow]:
        defs = SLAM_DEFINITIONS
        return [
            SlamWindow("australian_open", defs["australian_open"]["name"], defs["australian_open"]["location"], date(year, 1, 12), date(year, 1, 26), defs["australian_open"]["official_url"]),
            SlamWindow("french_open", defs["french_open"]["name"], defs["french_open"]["location"], date(year, 5, 24), date(year, 6, 7), defs["french_open"]["official_url"]),
            SlamWindow("wimbledon", defs["wimbledon"]["name"], defs["wimbledon"]["location"], date(year, 6, 29), date(year, 7, 12), defs["wimbledon"]["official_url"]),
            SlamWindow("us_open", defs["us_open"]["name"], defs["us_open"]["location"], date(year, 8, 31), date(year, 9, 13), defs["us_open"]["official_url"]),
        ]

    @staticmethod
    def _parse_dt(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            return None

    @staticmethod
    def _sort_match(match: Match) -> datetime:
        return match.start_time or datetime.min.replace(tzinfo=timezone.utc)
