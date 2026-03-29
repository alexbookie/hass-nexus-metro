"""Sensor platform for the Nexus Metro integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import homeassistant.util.dt as dt_util

from .const import DOMAIN, MAX_DEPARTURE_SLOTS
from .coordinator import NexusMetroConfigEntry, NexusMetroCoordinator
from .models import PlatformInfo, TrainDeparture

# Translation keys per departure slot index
_DEPARTURE_TRANSLATION_KEYS = ("next_departure", "departure_2", "departure_3")

_TICK_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NexusMetroConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Nexus Metro sensors from a config entry."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = []

    for platform_info in coordinator.platforms.values():
        entities.extend(
            NexusMetroDepartureSensor(coordinator, platform_info, slot) for slot in range(MAX_DEPARTURE_SLOTS)
        )
        entities.append(NexusMetroDestinationSensor(coordinator, platform_info))
        entities.append(NexusMetroLineSensor(coordinator, platform_info))

    async_add_entities(entities)


def _make_device_info(coordinator: NexusMetroCoordinator) -> DeviceInfo:
    """Create shared device info for a station."""
    return DeviceInfo(
        identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
        name=f"{coordinator.station_name} Metro",
        manufacturer="Nexus",
        model="Tyne and Wear Metro",
    )


class _NexusMetroPlatformEntity(CoordinatorEntity[NexusMetroCoordinator], SensorEntity):
    """Base class for sensors tied to a specific platform."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NexusMetroCoordinator,
        platform_info: PlatformInfo,
    ) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        self._platform_number = platform_info.platform_number
        self._platform_info = platform_info
        self._attr_device_info = _make_device_info(coordinator)

    def _get_departures(self) -> list[TrainDeparture]:
        """Get departures for this platform from coordinator data."""
        if self.coordinator.data is None:
            return []
        return self.coordinator.data.departures.get(self._platform_number, [])


class NexusMetroDepartureSensor(_NexusMetroPlatformEntity):
    """Sensor showing due-in minutes for a departure slot on a platform."""

    _attr_icon = "mdi:train"
    _attr_native_unit_of_measurement = "min"

    def __init__(
        self,
        coordinator: NexusMetroCoordinator,
        platform_info: PlatformInfo,
        departure_index: int,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, platform_info)
        self._departure_index = departure_index

        # Preserve existing unique_id for the first slot (backward compat)
        if departure_index == 0:
            self._attr_unique_id = f"{coordinator.config_entry.entry_id}_platform_{platform_info.platform_number}"
        else:
            self._attr_unique_id = (
                f"{coordinator.config_entry.entry_id}_platform_{platform_info.platform_number}"
                f"_departure_{departure_index + 1}"
            )

        self._attr_translation_key = _DEPARTURE_TRANSLATION_KEYS[departure_index]
        self._attr_translation_placeholders = {
            "platform_number": str(platform_info.platform_number),
        }

    @property
    def _departure(self) -> TrainDeparture | None:
        """Return the departure for this slot, or None."""
        departures = self._get_departures()
        if self._departure_index < len(departures):
            return departures[self._departure_index]
        return None

    @property
    def native_value(self) -> int | None:
        """Return minutes until this train, computed from departure_dt when available."""
        dep = self._departure
        if dep is None:
            return None
        if dep.due_in == -1:
            return 0
        if dep.departure_dt is not None:
            delta = (dep.departure_dt - dt_util.utcnow()).total_seconds()
            return max(0, int(delta // 60))
        return dep.due_in

    async def async_added_to_hass(self) -> None:
        """Register a 30-second tick to keep the countdown accurate between polls."""
        await super().async_added_to_hass()
        self.async_on_remove(async_track_time_interval(self.hass, self._async_tick, _TICK_INTERVAL))

    async def _async_tick(self, _now: object) -> None:
        """Push a state update every 30 seconds to reflect elapsed time."""
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return detailed departure attributes."""
        attrs: dict[str, Any] = {
            "platform_number": self._platform_number,
            "platform_direction": self._platform_info.direction.value,
            "platform_helper_text": self._platform_info.helper_text,
        }

        dep = self._departure
        if dep:
            attrs["destination"] = dep.destination
            attrs["line"] = dep.line.value if dep.line else None
            attrs["train_number"] = dep.train_number
            attrs["last_event"] = dep.last_event.value
            attrs["last_event_location"] = dep.last_event_location
            attrs["scheduled_time"] = dep.scheduled_time
            attrs["predicted_time"] = dep.predicted_time

        # Include full next_trains list only on the first slot
        if self._departure_index == 0:
            departures = self._get_departures()
            if departures:
                attrs["next_trains"] = [
                    {
                        "destination": t.destination,
                        "due_in": t.due_in,
                        "line": t.line.value if t.line else None,
                        "train_number": t.train_number,
                        "last_event": t.last_event.value,
                    }
                    for t in departures
                ]

        return attrs


class NexusMetroDestinationSensor(_NexusMetroPlatformEntity):
    """Sensor showing the destination of the next departure on a platform."""

    _attr_icon = "mdi:map-marker"

    def __init__(
        self,
        coordinator: NexusMetroCoordinator,
        platform_info: PlatformInfo,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, platform_info)
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_platform_{platform_info.platform_number}_destination"
        )
        self._attr_translation_key = "next_destination"
        self._attr_translation_placeholders = {
            "platform_number": str(platform_info.platform_number),
        }

    @property
    def native_value(self) -> str | None:
        """Return the destination of the next train."""
        departures = self._get_departures()
        if departures:
            return departures[0].destination
        return None


class NexusMetroLineSensor(_NexusMetroPlatformEntity):
    """Sensor showing the line colour of the next departure on a platform."""

    _attr_icon = "mdi:subway-variant"

    def __init__(
        self,
        coordinator: NexusMetroCoordinator,
        platform_info: PlatformInfo,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, platform_info)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_platform_{platform_info.platform_number}_line"
        self._attr_translation_key = "next_line"
        self._attr_translation_placeholders = {
            "platform_number": str(platform_info.platform_number),
        }

    @property
    def native_value(self) -> str | None:
        """Return the line of the next train."""
        departures = self._get_departures()
        if departures and departures[0].line:
            return departures[0].line.value
        return None
