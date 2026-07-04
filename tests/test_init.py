"""Tests for config entry setup, unload, and migration."""

from __future__ import annotations

from unittest.mock import AsyncMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nexus_metro.const import CONF_PLATFORMS, CONF_STATION_CODE, CONF_STATION_NAME, DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant


def _make_v1_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a config entry as v0.1.0 stored it (version 1, same data keys)."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="West Jesmond",
        data={
            CONF_STATION_CODE: "WJS",
            CONF_STATION_NAME: "West Jesmond",
            CONF_PLATFORMS: [1, 2],
        },
        unique_id="WJS",
        version=1,
    )
    entry.add_to_hass(hass)
    return entry


async def test_migrate_entry_v1_to_v2(
    hass: HomeAssistant,
    mock_nexus_clients: tuple[AsyncMock, AsyncMock],
):
    """A v1 entry (from the RTI-based v0.1.0) migrates and sets up successfully."""
    entry = _make_v1_entry(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 2
    assert entry.state is ConfigEntryState.LOADED
    # Data keys survive migration unchanged
    assert entry.data[CONF_STATION_CODE] == "WJS"
    assert entry.data[CONF_PLATFORMS] == [1, 2]


async def test_migrated_entry_creates_entities_with_stable_unique_ids(
    hass: HomeAssistant,
    mock_nexus_clients: tuple[AsyncMock, AsyncMock],
):
    """The primary sensor keeps the v1 unique_id format after migration."""
    from homeassistant.helpers import entity_registry as er

    entry = _make_v1_entry(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    # v0.1.0's primary sensor unique_id format must resolve to an entity
    entity_id = entity_reg.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_platform_1")
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state not in ("unknown", "unavailable")


async def test_unload_entry(
    hass: HomeAssistant,
    mock_config_entry,
    mock_nexus_clients: tuple[AsyncMock, AsyncMock],
):
    """A loaded entry unloads cleanly."""
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
