"""Tests for the Nexus Metro sensor platform."""

from __future__ import annotations

from unittest.mock import AsyncMock

from custom_components.nexus_metro.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er


async def test_sensor_setup_and_state(
    hass: HomeAssistant,
    mock_config_entry,
    mock_nexus_api: AsyncMock,
):
    """Test that sensors are created and have correct state."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    entities = er.async_entries_for_config_entry(entity_reg, mock_config_entry.entry_id)
    assert len(entities) == 2

    state_1 = hass.states.get(entities[0].entity_id)
    assert state_1 is not None
    assert state_1.state == "3"


async def test_sensor_attributes(
    hass: HomeAssistant,
    mock_config_entry,
    mock_nexus_api: AsyncMock,
):
    """Test sensor extra state attributes."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    entities = er.async_entries_for_config_entry(entity_reg, mock_config_entry.entry_id)

    state = hass.states.get(entities[0].entity_id)
    assert state is not None
    attrs = state.attributes

    assert attrs["destination"] == "South Hylton"
    assert attrs["line"] == "GREEN"
    assert attrs["train_number"] == "102"
    assert attrs["last_event"] == "DEPARTED"
    assert "next_trains" in attrs
    assert len(attrs["next_trains"]) == 2


async def test_sensor_no_departures(
    hass: HomeAssistant,
    mock_config_entry,
    mock_nexus_api: AsyncMock,
):
    """Test sensor state when no departures available."""
    mock_nexus_api.async_get_departures.return_value = []

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    entities = er.async_entries_for_config_entry(entity_reg, mock_config_entry.entry_id)

    state = hass.states.get(entities[0].entity_id)
    assert state is not None
    assert state.state == "unknown"
    assert "destination" not in state.attributes


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
