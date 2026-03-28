"""Sensor platform for the Nexus Metro integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NexusMetroConfigEntry, NexusMetroCoordinator
from .models import PlatformInfo, TrainDeparture


async def async_setup_entry(
    hass: object,
    entry: NexusMetroConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Nexus Metro sensors from a config entry."""
    coordinator = entry.runtime_data
    entities = [
        NexusMetroDepartureSensor(coordinator, platform_info) for platform_info in coordinator.platforms.values()
    ]
    async_add_entities(entities)


class NexusMetroDepartureSensor(CoordinatorEntity[NexusMetroCoordinator], SensorEntity):
    """Sensor showing next departure for a platform."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:train"
    _attr_native_unit_of_measurement = "min"

    def __init__(
        self,
        coordinator: NexusMetroCoordinator,
        platform_info: PlatformInfo,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._platform_number = platform_info.platform_number
        self._platform_info = platform_info

        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_platform_{platform_info.platform_number}"
        self._attr_translation_key = "next_departure"
        self._attr_translation_placeholders = {
            "platform_number": str(platform_info.platform_number),
        }
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name=f"{coordinator.station_name} Metro",
            manufacturer="Nexus",
            model="Tyne and Wear Metro",
        )

    @property
    def native_value(self) -> int | None:
        """Return minutes until next train, or None if no data."""
        departures = self._departures
        if not departures:
            return None
        return departures[0].due_in

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return detailed departure attributes."""
        departures = self._departures
        attrs: dict[str, Any] = {
            "platform_number": self._platform_number,
            "platform_direction": self._platform_info.direction.value,
            "platform_helper_text": self._platform_info.helper_text,
        }

        if departures:
            next_train = departures[0]
            attrs["destination"] = next_train.destination
            attrs["line"] = next_train.line.value if next_train.line else None
            attrs["train_number"] = next_train.train_number
            attrs["last_event"] = next_train.last_event.value
            attrs["last_event_location"] = next_train.last_event_location
            attrs["scheduled_time"] = next_train.scheduled_time
            attrs["predicted_time"] = next_train.predicted_time

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

    @property
    def _departures(self) -> list[TrainDeparture]:
        """Get departures for this platform from coordinator data."""
        if self.coordinator.data is None:
            return []
        return self.coordinator.data.departures.get(self._platform_number, [])
