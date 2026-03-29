"""Tests for the Nexus Metro sensor platform."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.nexus_metro.const import DOMAIN
from custom_components.nexus_metro.models import MetroLine, TrainDeparture, TrainEvent
from custom_components.nexus_metro.sensor import NexusMetroDepartureSensor
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
import homeassistant.util.dt as dt_util


async def test_sensor_setup_creates_all_entities(
    hass: HomeAssistant,
    mock_config_entry,
    mock_nexus_api: AsyncMock,
):
    """Test that all sensors are created: 3 departure slots + destination + line per platform."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    entities = er.async_entries_for_config_entry(entity_reg, mock_config_entry.entry_id)
    # 2 platforms × (3 departure + 1 destination + 1 line) = 10
    assert len(entities) == 10


async def test_next_departure_state(
    hass: HomeAssistant,
    mock_config_entry,
    mock_nexus_api: AsyncMock,
):
    """Test the first departure slot has correct due_in state."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    entry = entity_reg.async_get_entity_id("sensor", DOMAIN, f"{mock_config_entry.entry_id}_platform_1")
    state = hass.states.get(entry)
    assert state is not None
    assert state.state == "3"


async def test_second_departure_state(
    hass: HomeAssistant,
    mock_config_entry,
    mock_nexus_api: AsyncMock,
):
    """Test the 2nd departure slot has correct due_in state."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    entry = entity_reg.async_get_entity_id("sensor", DOMAIN, f"{mock_config_entry.entry_id}_platform_1_departure_2")
    state = hass.states.get(entry)
    assert state is not None
    assert state.state == "8"


async def test_third_departure_unavailable_when_only_two_trains(
    hass: HomeAssistant,
    mock_config_entry,
    mock_nexus_api: AsyncMock,
):
    """Test the 3rd departure slot shows unknown when only 2 trains exist."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    entry = entity_reg.async_get_entity_id("sensor", DOMAIN, f"{mock_config_entry.entry_id}_platform_1_departure_3")
    state = hass.states.get(entry)
    assert state is not None
    assert state.state == "unknown"


async def test_next_departure_attributes(
    hass: HomeAssistant,
    mock_config_entry,
    mock_nexus_api: AsyncMock,
):
    """Test first departure slot extra state attributes."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    entry = entity_reg.async_get_entity_id("sensor", DOMAIN, f"{mock_config_entry.entry_id}_platform_1")
    state = hass.states.get(entry)
    assert state is not None
    attrs = state.attributes

    assert attrs["destination"] == "South Hylton"
    assert attrs["line"] == "GREEN"
    assert attrs["train_number"] == "102"
    assert attrs["last_event"] == "DEPARTED"
    assert "next_trains" in attrs
    assert len(attrs["next_trains"]) == 2


async def test_second_departure_attributes_no_next_trains_list(
    hass: HomeAssistant,
    mock_config_entry,
    mock_nexus_api: AsyncMock,
):
    """Test 2nd departure slot has its own attributes but no next_trains list."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    entry = entity_reg.async_get_entity_id("sensor", DOMAIN, f"{mock_config_entry.entry_id}_platform_1_departure_2")
    state = hass.states.get(entry)
    assert state is not None
    attrs = state.attributes

    assert attrs["destination"] == "South Shields"
    assert attrs["line"] == "YELLOW"
    assert attrs["train_number"] == "124"
    assert attrs["last_event"] == "APPROACHING"
    assert "next_trains" not in attrs


async def test_destination_sensor(
    hass: HomeAssistant,
    mock_config_entry,
    mock_nexus_api: AsyncMock,
):
    """Test destination sensor shows the next train's destination."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    entry = entity_reg.async_get_entity_id("sensor", DOMAIN, f"{mock_config_entry.entry_id}_platform_1_destination")
    state = hass.states.get(entry)
    assert state is not None
    assert state.state == "South Hylton"


async def test_line_sensor(
    hass: HomeAssistant,
    mock_config_entry,
    mock_nexus_api: AsyncMock,
):
    """Test line sensor shows the next train's line colour."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    entry = entity_reg.async_get_entity_id("sensor", DOMAIN, f"{mock_config_entry.entry_id}_platform_1_line")
    state = hass.states.get(entry)
    assert state is not None
    assert state.state == "GREEN"


async def test_sensor_no_departures(
    hass: HomeAssistant,
    mock_config_entry,
    mock_nexus_api: AsyncMock,
):
    """Test all sensors show unknown when no departures available."""
    mock_nexus_api.async_get_departures.return_value = []

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)

    # Departure sensor
    entry = entity_reg.async_get_entity_id("sensor", DOMAIN, f"{mock_config_entry.entry_id}_platform_1")
    state = hass.states.get(entry)
    assert state is not None
    assert state.state == "unknown"
    assert "destination" not in state.attributes

    # Destination sensor
    entry = entity_reg.async_get_entity_id("sensor", DOMAIN, f"{mock_config_entry.entry_id}_platform_1_destination")
    state = hass.states.get(entry)
    assert state is not None
    assert state.state == "unknown"

    # Line sensor
    entry = entity_reg.async_get_entity_id("sensor", DOMAIN, f"{mock_config_entry.entry_id}_platform_1_line")
    state = hass.states.get(entry)
    assert state is not None
    assert state.state == "unknown"


async def test_device_info(
    hass: HomeAssistant,
    mock_config_entry,
    mock_nexus_api: AsyncMock,
):
    """Test device info is set correctly."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    device_reg = dr.async_get(hass)
    device = device_reg.async_get_device(identifiers={(DOMAIN, mock_config_entry.entry_id)})
    assert device is not None
    assert device.manufacturer == "Nexus"
    assert device.model == "Tyne and Wear Metro"


async def test_unload_entry(
    hass: HomeAssistant,
    mock_config_entry,
    mock_nexus_api: AsyncMock,
):
    """Test unloading the config entry."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.async_unload(mock_config_entry.entry_id)
    assert result is True


def _make_departure(**kwargs) -> TrainDeparture:
    """Build a TrainDeparture with sensible defaults for countdown tests."""
    defaults = {
        "train_number": "102",
        "destination": "South Hylton",
        "due_in": 5,
        "line": MetroLine.GREEN,
        "last_event": TrainEvent.DEPARTED,
        "last_event_location": "Regent Centre",
        "last_event_time": "2024-01-15T15:03:12",
        "scheduled_time": None,
        "predicted_time": None,
        "departure_dt": None,
    }
    return TrainDeparture(**{**defaults, **kwargs})


class TestNativeValueCountdown:
    """Unit tests for NexusMetroDepartureSensor.native_value countdown logic."""

    def _make_sensor(self, coordinator, platform_info) -> NexusMetroDepartureSensor:
        return NexusMetroDepartureSensor(coordinator, platform_info, departure_index=0)

    def test_uses_departure_dt_when_available(self, mock_config_entry, mock_nexus_api):
        """departure_dt set to 4m30s in the future → native_value == 4 (floor)."""
        from unittest.mock import MagicMock

        coordinator = MagicMock()
        coordinator.config_entry = mock_config_entry
        coordinator.station_name = "Jesmond"

        from custom_components.nexus_metro.models import PlatformDirection, PlatformInfo

        platform_info = PlatformInfo(
            platform_number=1,
            direction=PlatformDirection.IN,
            helper_text="To South Hylton",
        )
        sensor = self._make_sensor(coordinator, platform_info)

        now = dt_util.utcnow()
        dep = _make_departure(departure_dt=now + timedelta(minutes=4, seconds=30))
        coordinator.data.departures = {1: [dep]}

        with patch("custom_components.nexus_metro.sensor.dt_util.utcnow", return_value=now):
            assert sensor.native_value == 4

    def test_clamps_to_zero_when_overdue(self, mock_config_entry, mock_nexus_api):
        """departure_dt 30s in the past → native_value == 0 (clamped)."""
        from unittest.mock import MagicMock

        coordinator = MagicMock()
        coordinator.config_entry = mock_config_entry
        coordinator.station_name = "Jesmond"

        from custom_components.nexus_metro.models import PlatformDirection, PlatformInfo

        platform_info = PlatformInfo(
            platform_number=1,
            direction=PlatformDirection.IN,
            helper_text="To South Hylton",
        )
        sensor = self._make_sensor(coordinator, platform_info)

        now = dt_util.utcnow()
        dep = _make_departure(departure_dt=now - timedelta(seconds=30))
        coordinator.data.departures = {1: [dep]}

        with patch("custom_components.nexus_metro.sensor.dt_util.utcnow", return_value=now):
            assert sensor.native_value == 0

    def test_preserves_arrived_sentinel(self, mock_config_entry, mock_nexus_api):
        """due_in=-1 always returns -1 regardless of departure_dt."""
        from unittest.mock import MagicMock

        coordinator = MagicMock()
        coordinator.config_entry = mock_config_entry
        coordinator.station_name = "Jesmond"

        from custom_components.nexus_metro.models import PlatformDirection, PlatformInfo

        platform_info = PlatformInfo(
            platform_number=1,
            direction=PlatformDirection.IN,
            helper_text="To South Hylton",
        )
        sensor = self._make_sensor(coordinator, platform_info)

        now = dt_util.utcnow()
        dep = _make_departure(due_in=-1, departure_dt=now + timedelta(minutes=10))
        coordinator.data.departures = {1: [dep]}

        with patch("custom_components.nexus_metro.sensor.dt_util.utcnow", return_value=now):
            assert sensor.native_value == -1

    def test_falls_back_to_raw_due_in_when_no_dt(self, mock_config_entry, mock_nexus_api):
        """departure_dt=None falls back to raw due_in integer."""
        from unittest.mock import MagicMock

        coordinator = MagicMock()
        coordinator.config_entry = mock_config_entry
        coordinator.station_name = "Jesmond"

        from custom_components.nexus_metro.models import PlatformDirection, PlatformInfo

        platform_info = PlatformInfo(
            platform_number=1,
            direction=PlatformDirection.IN,
            helper_text="To South Hylton",
        )
        sensor = self._make_sensor(coordinator, platform_info)

        dep = _make_departure(due_in=7, departure_dt=None)
        coordinator.data.departures = {1: [dep]}

        assert sensor.native_value == 7


async def test_tick_updates_state_without_coordinator_fetch(
    hass: HomeAssistant,
    mock_config_entry,
    mock_nexus_api: AsyncMock,
):
    """Firing time forward 30s should push a state update without a new API call."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    initial_call_count = mock_nexus_api.async_get_departures.call_count

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
    await hass.async_block_till_done()

    # No additional API calls — tick only calls async_write_ha_state
    assert mock_nexus_api.async_get_departures.call_count == initial_call_count
