"""Constants for Tennis Grand Slams."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "tennis_grand_slams"
PLATFORMS = ["sensor", "calendar"]

CONF_REGION = "region"
CONF_LANGUAGE = "language"
CONF_DAYS_AHEAD = "days_ahead"
CONF_UPDATE_INTERVAL = "update_interval"

DEFAULT_REGION = "de"
DEFAULT_LANGUAGE = "de"
DEFAULT_DAYS_AHEAD = 420
DEFAULT_UPDATE_INTERVAL = 15
DEFAULT_SCAN_INTERVAL = timedelta(minutes=DEFAULT_UPDATE_INTERVAL)

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/tennis"
ESPN_SCOREBOARD = ESPN_BASE + "/{tour}/scoreboard"

TOURS = ("atp", "wta")

SLAM_DEFINITIONS = {
    "australian_open": {
        "name": "Australian Open",
        "aliases": ("australian open",),
        "location": "Melbourne",
        "official_url": "https://ausopen.com/",
    },
    "french_open": {
        "name": "French Open",
        "aliases": ("french open", "roland garros", "roland-garros"),
        "location": "Paris",
        "official_url": "https://www.rolandgarros.com/",
    },
    "wimbledon": {
        "name": "Wimbledon",
        "aliases": ("wimbledon",),
        "location": "London",
        "official_url": "https://www.wimbledon.com/",
    },
    "us_open": {
        "name": "US Open",
        "aliases": ("us open", "u.s. open", "united states open"),
        "location": "New York",
        "official_url": "https://www.usopen.org/",
    },
}

ESPN_SCOREBOARD_URL = "https://www.espn.com/tennis/scoreboard"
