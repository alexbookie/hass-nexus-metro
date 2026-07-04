"""Tests for the Nexus Metro sensor platform."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock

from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.nexus_metro.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
import homeassistant.util.dt as dt_util


async def test_sensor_setup_creates_all_entities(
    hass: HomeAssistant,
    mock_config_entry,
    mock_nexus_clients: tuple[AsyncMock, AsyncMock],
):
    """Test that 5 sensors per platform are created (scheduled + live + 3 combined)."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    entities = er.async_entries_for_config_entry(entity_reg, mock_config_entry.entry_id)
    # 2 platforms * (1 scheduled + 1 live + 3 combined) = 10
    assert len(entities) == 10


async def test_combined_sensor_state(
    hass: HomeAssistant,
    mock_config_entry,
    mock_nexus_clients: tuple[AsyncMock, AsyncMock],
):
    """Test the combined sensor shows next departure time."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    entity_id = entity_reg.async_get_entity_id("sensor", DOMAIN, f"{mock_config_entry.entry_id}_platform_1")
    state = hass.states.get(entity_id)
    assert state is not None
    # Should have a numeric value (minutes)
    assert state.state not in ("unknown", "unavailable")


async def test_combined_sensor_attributes(
    hass: HomeAssistant,
    mock_config_entry,
    mock_nexus_clients: tuple[AsyncMock, AsyncMock],
):
    """Test combined sensor has destination and departures list."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    entity_id = entity_reg.async_get_entity_id("sensor", DOMAIN, f"{mock_config_entry.entry_id}_platform_1")
    state = hass.states.get(entity_id)
    assert state is not None
    attrs = state.attributes

    assert "destination" in attrs
    assert "status" in attrs
    assert "departures" in attrs
    assert isinstance(attrs["departures"], list)


async def test_scheduled_sensor_state(
    hass: HomeAssistant,
    mock_config_entry,
    mock_nexus_clients: tuple[AsyncMock, AsyncMock],
):
    """Test the scheduled sensor shows scheduled minutes."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    entity_id = entity_reg.async_get_entity_id("sensor", DOMAIN, f"{mock_config_entry.entry_id}_platform_1_scheduled")
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "3.0"


async def test_scheduled_sensor_attributes(
    hass: HomeAssistant,
    mock_config_entry,
    mock_nexus_clients: tuple[AsyncMock, AsyncMock],
):
    """Test scheduled sensor has departures list."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    entity_id = entity_reg.async_get_entity_id("sensor", DOMAIN, f"{mock_config_entry.entry_id}_platform_1_scheduled")
    state = hass.states.get(entity_id)
    assert state is not None
    attrs = state.attributes

    assert attrs["destination"] == "South Hylton"
    assert "departures" in attrs
    assert len(attrs["departures"]) >= 1


async def test_live_estimate_sensor(
    hass: HomeAssistant,
    mock_config_entry,
    mock_nexus_clients: tuple[AsyncMock, AsyncMock],
):
    """Test the live estimate sensor."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    entity_id = entity_reg.async_get_entity_id("sensor", DOMAIN, f"{mock_config_entry.entry_id}_platform_1_live")
    state = hass.states.get(entity_id)
    assert state is not None
    # May be "unknown" if no trains matched, or a number if matched
    attrs = state.attributes
    assert "trains" in attrs


async def test_no_departures_shows_unknown(
    hass: HomeAssistant,
    mock_config_entry,
    mock_nexus_clients: tuple[AsyncMock, AsyncMock],
):
    """Test all sensors show unknown when no departures available."""
    trav_client, kml_client = mock_nexus_clients
    trav_client.async_get_departures.return_value = []
    kml_client.async_get_trains.return_value = []

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)

    for suffix in ["", "_scheduled", "_live", "_departure_2", "_departure_3"]:
        entity_id = entity_reg.async_get_entity_id("sensor", DOMAIN, f"{mock_config_entry.entry_id}_platform_1{suffix}")
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == "unknown"


async def test_device_info(
    hass: HomeAssistant,
    mock_config_entry,
    mock_nexus_clients: tuple[AsyncMock, AsyncMock],
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
    mock_nexus_clients: tuple[AsyncMock, AsyncMock],
):
    """Test unloading the config entry."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.async_unload(mock_config_entry.entry_id)
    assert result is True


async def test_tick_updates_state_without_api_call(
    hass: HomeAssistant,
    mock_config_entry,
    mock_nexus_clients: tuple[AsyncMock, AsyncMock],
):
    """Firing time forward 30s should push a state update without new API calls."""
    trav_client, kml_client = mock_nexus_clients

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    initial_trav_count = trav_client.async_get_departures.call_count
    initial_kml_count = kml_client.async_get_trains.call_count

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
    await hass.async_block_till_done()

    # No additional API calls — tick only calls async_write_ha_state
    assert trav_client.async_get_departures.call_count == initial_trav_count
    assert kml_client.async_get_trains.call_count == initial_kml_count
