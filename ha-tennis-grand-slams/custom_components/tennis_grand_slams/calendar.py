"""Calendar entity for Tennis Grand Slams."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TennisGrandSlamCoordinator


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:
    """Set up calendar entity."""
    coordinator: TennisGrandSlamCoordinator = entry.runtime_data
    async_add_entities([GrandSlamCalendar(coordinator)])


class GrandSlamCalendar(CoordinatorEntity[TennisGrandSlamCoordinator], CalendarEntity):
    """Calendar with detected Grand Slam tournament windows."""

    _attr_has_entity_name = True
    _attr_name = "Grand Slam Kalender"
    _attr_unique_id = f"{DOMAIN}_grand_slam_kalender"
    _attr_suggested_object_id = "grand_slam_kalender"
    _attr_icon = "mdi:calendar-star"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, "tennis_grand_slams")},
            name="Tennis Grand Slams",
            manufacturer="ESPN data via custom integration",
            model="Grand Slam Tracker",
        )

    @property
    def event(self) -> CalendarEvent | None:
        slam = self.coordinator.data.current_slam or self.coordinator.data.next_slam
        if slam is None:
            return None
        return CalendarEvent(
            summary=slam.name,
            start=slam.start,
            end=slam.end + timedelta(days=1),
            location=slam.location,
            description=f"{slam.name} · {slam.official_url}",
        )

    async def async_get_events(self, hass, start_date: datetime, end_date: datetime) -> list[CalendarEvent]:
        """Return Grand Slam calendar events in the requested window."""
        events: list[CalendarEvent] = []
        start_day = start_date.astimezone(timezone.utc).date() if start_date.tzinfo else start_date.date()
        end_day = end_date.astimezone(timezone.utc).date() if end_date.tzinfo else end_date.date()
        for slam in self.coordinator.data.slam_windows:
            if slam.end < start_day or slam.start > end_day:
                continue
            events.append(
                CalendarEvent(
                    summary=slam.name,
                    start=slam.start,
                    end=slam.end + timedelta(days=1),
                    location=slam.location,
                    description=f"Offizielle Website: {slam.official_url}\nESPN: {slam.espn_url}",
                )
            )
        return events

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "events": [s.as_dict() for s in self.coordinator.data.slam_windows]
        }
