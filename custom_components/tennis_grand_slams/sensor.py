"""Sensors for Tennis Grand Slams."""
from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ESPN_SCOREBOARD_URL
from .coordinator import TennisGrandSlamCoordinator


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:
    """Set up sensors."""
    coordinator: TennisGrandSlamCoordinator = entry.runtime_data
    async_add_entities(
        [
            SlamStatusSensor(coordinator),
            NextSlamSensor(coordinator),
            LiveMatchesSensor(coordinator),
            UpcomingMatchesSensor(coordinator),
            RecentResultsSensor(coordinator),
            LastUpdateSensor(coordinator),
        ]
    )


class TennisBaseSensor(CoordinatorEntity[TennisGrandSlamCoordinator], SensorEntity):
    """Base tennis sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: TennisGrandSlamCoordinator, key: str, name: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{key}"
        self._attr_name = name
        self._attr_suggested_object_id = key

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, "tennis_grand_slams")},
            name="Tennis Grand Slams",
            manufacturer="ESPN data via custom integration",
            model="Grand Slam Tracker",
            entry_type=None,
        )


class SlamStatusSensor(TennisBaseSensor):
    """Current or next Grand Slam."""

    _attr_icon = "mdi:tennis"

    def __init__(self, coordinator: TennisGrandSlamCoordinator) -> None:
        super().__init__(coordinator, "grand_slam_status", "Grand Slam Status")

    @property
    def native_value(self) -> str:
        slam = self.coordinator.data.current_slam or self.coordinator.data.next_slam
        return slam.name if slam else "Kein Grand Slam gefunden"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        slam = data.current_slam or data.next_slam
        if slam is None:
            return {"espn_url": ESPN_SCOREBOARD_URL, "live_matches": 0, "upcoming_matches": 0, "debug": data.debug}
        attrs = slam.as_dict(date.today())
        attrs.update(
            {
                "is_active": data.current_slam is not None,
                "current_slam": data.current_slam.as_dict(date.today()) if data.current_slam else None,
                "next_slam": data.next_slam.as_dict(date.today()) if data.next_slam else None,
                "live_matches": len(data.live_matches),
                "upcoming_matches": len(data.upcoming_matches),
                "recent_results": len(data.recent_results),
                "espn_url": ESPN_SCOREBOARD_URL,
                "all_known_slams": [s.as_dict(date.today()) for s in data.slam_windows],
                "debug": data.debug,
            }
        )
        return attrs


class NextSlamSensor(TennisBaseSensor):
    """Days until next Grand Slam."""

    _attr_icon = "mdi:calendar-clock"
    _attr_native_unit_of_measurement = UnitOfTime.DAYS

    def __init__(self, coordinator: TennisGrandSlamCoordinator) -> None:
        # Keep the older object id spelling without ae because existing HA
        # installations may already have this entity id in their dashboards.
        super().__init__(coordinator, "tage_bis_zum_nachsten_grand_slam", "Tage bis zum nächsten Grand Slam")

    @property
    def native_value(self) -> int | None:
        slam = self.coordinator.data.next_slam
        if slam is None:
            return None
        return max((slam.start - date.today()).days, 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        slam = self.coordinator.data.next_slam
        return slam.as_dict(date.today()) if slam else {}


class LiveMatchesSensor(TennisBaseSensor):
    """Live match count."""

    _attr_icon = "mdi:scoreboard"

    def __init__(self, coordinator: TennisGrandSlamCoordinator) -> None:
        super().__init__(coordinator, "grand_slam_live_matches", "Grand Slam Live Matches")

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.live_matches)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        # Keep this list intentionally capped to reduce recorder noise.
        return {"matches": [m.as_dict() for m in self.coordinator.data.live_matches[:20]], "debug": self.coordinator.data.debug}


class UpcomingMatchesSensor(TennisBaseSensor):
    """Upcoming match count."""

    _attr_icon = "mdi:calendar-star"

    def __init__(self, coordinator: TennisGrandSlamCoordinator) -> None:
        super().__init__(coordinator, "grand_slam_upcoming_matches", "Grand Slam Upcoming Matches")

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.upcoming_matches)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"matches": [m.as_dict() for m in self.coordinator.data.upcoming_matches[:30]], "debug": self.coordinator.data.debug}


class RecentResultsSensor(TennisBaseSensor):
    """Recent results count."""

    _attr_icon = "mdi:trophy-outline"

    def __init__(self, coordinator: TennisGrandSlamCoordinator) -> None:
        super().__init__(coordinator, "grand_slam_recent_results", "Grand Slam Recent Results")

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.recent_results)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"matches": [m.as_dict() for m in self.coordinator.data.recent_results[:20]], "debug": self.coordinator.data.debug}


class LastUpdateSensor(TennisBaseSensor):
    """Diagnostics last update sensor."""

    _attr_icon = "mdi:cloud-refresh"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: TennisGrandSlamCoordinator) -> None:
        super().__init__(coordinator, "letzte_espn_aktualisierung", "Letzte ESPN Aktualisierung")

    @property
    def native_value(self) -> str:
        return self.coordinator.data.generated_at.isoformat()
