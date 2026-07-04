"""Sensor platform for the Nexus Metro integration.

Creates three sensor types per platform:
- Scheduled: raw Traveline departure data
- Live estimate: KML-derived ETAs
- Combined: intelligent merge with status
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MAX_DEPARTURE_SLOTS, NUM_DEPARTURE_SENSORS
from .coordinator import NexusMetroConfigEntry, NexusMetroCoordinator
from .metro_data import get_platform_description
from .models import CombinedDeparture, PlatformData

_TICK_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NexusMetroConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Nexus Metro sensors from a config entry."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = []

    for platform_number in coordinator.platform_numbers:
        entities.append(NexusMetroScheduledSensor(coordinator, platform_number))
        entities.append(NexusMetroLiveEstimateSensor(coordinator, platform_number))
        entities.extend(
            NexusMetroCombinedSensor(coordinator, platform_number, departure_index=slot)
            for slot in range(NUM_DEPARTURE_SENSORS)
        )

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
        platform_number: int,
    ) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        self._platform_number = platform_number
        self._attr_device_info = _make_device_info(coordinator)

    def _get_platform_data(self) -> PlatformData | None:
        """Get platform data from coordinator."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.platforms.get(self._platform_number)


class NexusMetroScheduledSensor(_NexusMetroPlatformEntity):
    """Sensor showing scheduled departure time from Traveline.

    State = minutes until next scheduled train.
    Attributes include the full list of upcoming scheduled departures.
    """

    _attr_icon = "mdi:clock-outline"
    _attr_native_unit_of_measurement = "min"

    def __init__(
        self,
        coordinator: NexusMetroCoordinator,
        platform_number: int,
    ) -> None:
        """Initialise the scheduled departure sensor."""
        super().__init__(coordinator, platform_number)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_platform_{platform_number}_scheduled"
        self._attr_translation_key = "scheduled_departure"
        self._attr_translation_placeholders = {
            "platform_number": str(platform_number),
        }

    @property
    def native_value(self) -> float | None:
        """Return minutes until next scheduled train."""
        platform_data = self._get_platform_data()
        if not platform_data or not platform_data.traveline_departures:
            return None
        dep = platform_data.traveline_departures[0]
        return dep.scheduled_mins

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return scheduled departure attributes."""
        attrs: dict[str, Any] = {
            "platform_number": self._platform_number,
            "platform_description": get_platform_description(self.coordinator.station_code, self._platform_number),
        }

        platform_data = self._get_platform_data()
        if not platform_data:
            return attrs

        deps = platform_data.traveline_departures
        if deps:
            first = deps[0]
            attrs["destination"] = first.destination
            attrs["service"] = first.service
            attrs["due"] = first.due

        attrs["departures"] = [
            {
                "service": d.service,
                "destination": d.destination,
                "due": d.due,
                "scheduled_mins": d.scheduled_mins,
            }
            for d in deps[:MAX_DEPARTURE_SLOTS]
        ]

        return attrs


class NexusMetroLiveEstimateSensor(_NexusMetroPlatformEntity):
    """Sensor showing live estimated arrival from KML matching.

    State = minutes until next live-tracked train (None if no match).
    Attributes include matched train details.
    """

    _attr_icon = "mdi:train-variant"
    _attr_native_unit_of_measurement = "min"

    def __init__(
        self,
        coordinator: NexusMetroCoordinator,
        platform_number: int,
    ) -> None:
        """Initialise the live estimate sensor."""
        super().__init__(coordinator, platform_number)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_platform_{platform_number}_live"
        self._attr_translation_key = "live_estimate"
        self._attr_translation_placeholders = {
            "platform_number": str(platform_number),
        }

    @property
    def native_value(self) -> float | None:
        """Return minutes until next live-tracked train."""
        platform_data = self._get_platform_data()
        if not platform_data:
            return None

        for dep in platform_data.combined_departures:
            if dep.live_estimate_mins is not None:
                return round(dep.live_estimate_mins, 1)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return live estimate attributes."""
        attrs: dict[str, Any] = {
            "platform_number": self._platform_number,
        }

        platform_data = self._get_platform_data()
        if not platform_data:
            return attrs

        # Find all departures with live matches
        live_matched = [d for d in platform_data.combined_departures if d.live_estimate_mins is not None]

        if live_matched:
            first = live_matched[0]
            attrs["destination"] = first.destination
            attrs["train_id"] = first.train_id
            attrs["train_info"] = first.train_info
            attrs["status"] = first.status

        attrs["trains"] = [
            {
                "destination": d.destination,
                "train_id": d.train_id,
                "live_estimate_mins": round(d.live_estimate_mins, 1) if d.live_estimate_mins is not None else None,
                "status": d.status,
                "train_info": d.train_info,
            }
            for d in live_matched[:MAX_DEPARTURE_SLOTS]
        ]

        return attrs


class NexusMetroCombinedSensor(_NexusMetroPlatformEntity):
    """Sensor showing best available departure time (live preferred, else scheduled).

    State = minutes until next train (best estimate).
    Attributes include full combined departure list with status.
    """

    _attr_icon = "mdi:subway"
    _attr_native_unit_of_measurement = "min"

    def __init__(
        self,
        coordinator: NexusMetroCoordinator,
        platform_number: int,
        departure_index: int = 0,
    ) -> None:
        """Initialise the combined departure sensor."""
        super().__init__(coordinator, platform_number)
        self._departure_index = departure_index

        if departure_index == 0:
            # Use the original unique_id format for backward compatibility
            self._attr_unique_id = f"{coordinator.config_entry.entry_id}_platform_{platform_number}"
            self._attr_translation_key = "next_departure"
        else:
            self._attr_unique_id = (
                f"{coordinator.config_entry.entry_id}_platform_{platform_number}_departure_{departure_index + 1}"
            )
            self._attr_translation_key = "nth_departure"

        self._attr_translation_placeholders = {
            "platform_number": str(platform_number),
            "departure_number": str(departure_index + 1),
        }

    async def async_added_to_hass(self) -> None:
        """Register a 30-second tick to keep countdown accurate between polls."""
        await super().async_added_to_hass()
        self.async_on_remove(async_track_time_interval(self.hass, self._async_tick, _TICK_INTERVAL))

    async def _async_tick(self, _now: object) -> None:
        """Push a state update every 30 seconds to reflect elapsed time."""
        self.async_write_ha_state()

    def _get_departure(self) -> CombinedDeparture | None:
        """Get the departure at this sensor's index."""
        platform_data = self._get_platform_data()
        if not platform_data or len(platform_data.combined_departures) <= self._departure_index:
            return None
        return platform_data.combined_departures[self._departure_index]

    @property
    def native_value(self) -> float | None:
        """Return minutes until this train, preferring live estimate."""
        dep = self._get_departure()
        if dep is None:
            return None
        if dep.live_estimate_mins is not None:
            return round(dep.live_estimate_mins, 1)
        return dep.scheduled_mins

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return combined departure attributes."""
        attrs: dict[str, Any] = {
            "platform_number": self._platform_number,
            "platform_description": get_platform_description(self.coordinator.station_code, self._platform_number),
        }

        dep = self._get_departure()
        if dep:
            attrs["destination"] = dep.destination
            attrs["status"] = dep.status
            attrs["scheduled_due"] = dep.scheduled_due
            attrs["live_estimate_mins"] = (
                round(dep.live_estimate_mins, 1) if dep.live_estimate_mins is not None else None
            )
            attrs["train_id"] = dep.train_id
            attrs["train_info"] = dep.train_info

        # Only include the full list on the primary (index 0) sensor
        if self._departure_index == 0:
            platform_data = self._get_platform_data()
            deps = platform_data.combined_departures if platform_data else []
            attrs["departures"] = [_combined_departure_to_dict(d) for d in deps[:MAX_DEPARTURE_SLOTS]]

        return attrs


def _combined_departure_to_dict(dep: CombinedDeparture) -> dict[str, Any]:
    """Convert a CombinedDeparture to a dict for state attributes."""
    return {
        "service": dep.service,
        "destination": dep.destination,
        "scheduled_due": dep.scheduled_due,
        "scheduled_mins": dep.scheduled_mins,
        "live_estimate_mins": (round(dep.live_estimate_mins, 1) if dep.live_estimate_mins is not None else None),
        "status": dep.status,
        "train_id": dep.train_id,
        "train_info": dep.train_info,
    }
