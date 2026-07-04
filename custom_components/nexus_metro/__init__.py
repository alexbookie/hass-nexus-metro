"""Custom integration to integrate Nexus Metro with Home Assistant."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import KmlClient, TravelineClient
from .const import (
    CONF_PLATFORMS,
    CONF_SCAN_INTERVAL,
    CONF_STATION_CODE,
    CONF_STATION_NAME,
    DEFAULT_SCAN_INTERVAL,
    PLATFORMS,
)
from .coordinator import NexusMetroCoordinator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .coordinator import NexusMetroConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: NexusMetroConfigEntry) -> bool:
    """Set up Nexus Metro from a config entry."""
    session = async_get_clientsession(hass)
    traveline_client = TravelineClient(session=session)
    kml_client = KmlClient(session=session)

    station_code: str = entry.data[CONF_STATION_CODE]
    station_name: str = entry.data[CONF_STATION_NAME]
    platform_numbers: list[int] = entry.data[CONF_PLATFORMS]

    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    coordinator = NexusMetroCoordinator(
        hass=hass,
        traveline_client=traveline_client,
        kml_client=kml_client,
        station_code=station_code,
        station_name=station_name,
        platform_numbers=platform_numbers,
        scan_interval=scan_interval,
    )

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_options))

    return True


async def _async_update_options(hass: HomeAssistant, entry: NexusMetroConfigEntry) -> None:
    """Reload the integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: NexusMetroConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, config_entry: NexusMetroConfigEntry) -> bool:
    """Migrate old config entries to new version."""
    if config_entry.version < 2:
        _LOGGER.info(
            "Migrating config entry %s from version %d to 2",
            config_entry.entry_id,
            config_entry.version,
        )
        # V1 -> V2: data structure is compatible (station_code, station_name, platforms)
        # but the underlying data sources changed completely.
        # The platforms list format is the same (list of ints), so we can keep it.
        hass.config_entries.async_update_entry(
            config_entry,
            version=2,
        )
        _LOGGER.info("Migration to version 2 successful")
    return True
