"""Custom integration to integrate Nexus Metro with Home Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NexusMetroApiClient, NexusMetroConnectionError
from .const import (
    CONF_PLATFORMS,
    CONF_SCAN_INTERVAL,
    CONF_STATION_CODE,
    CONF_STATION_NAME,
    DEFAULT_SCAN_INTERVAL,
    PLATFORMS,
)
from .coordinator import NexusMetroCoordinator
from .models import PlatformInfo

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .coordinator import NexusMetroConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: NexusMetroConfigEntry) -> bool:
    """Set up Nexus Metro from a config entry."""
    session = async_get_clientsession(hass)
    client = NexusMetroApiClient(session=session)

    station_code: str = entry.data[CONF_STATION_CODE]
    station_name: str = entry.data[CONF_STATION_NAME]

    # Reconstruct platform info from stored config
    platform_numbers: list[int] = entry.data[CONF_PLATFORMS]
    platforms: dict[int, PlatformInfo] = {}
    try:
        platforms = await client.async_get_platforms(station_code)
    except NexusMetroConnectionError as err:
        raise ConfigEntryNotReady(f"Could not connect to Nexus Metro API: {err}") from err
    except Exception as err:
        raise ConfigEntryNotReady(f"Error fetching platform data: {err}") from err

    # Filter to selected platforms only
    if platform_numbers:
        platforms = {k: v for k, v in platforms.items() if k in platform_numbers}

    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    coordinator = NexusMetroCoordinator(
        hass=hass,
        client=client,
        station_code=station_code,
        station_name=station_name,
        platforms=platforms,
        scan_interval=scan_interval,
    )

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: NexusMetroConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
