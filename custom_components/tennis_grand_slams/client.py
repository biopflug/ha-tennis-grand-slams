"""Client for ESPN tennis scoreboard data."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
import html
import logging
import re
from typing import Any, Iterable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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
            "tournament_key": self.tournament_key,
            "tour": self.tour.upper(),
            "state": self.state,
            "status": self.status,
            "detail": self.detail,
            "score": self.score,
            "current_score": self.score,
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