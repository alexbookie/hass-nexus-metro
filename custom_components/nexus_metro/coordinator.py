"""DataUpdateCoordinator for the Nexus Metro integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import TYPE_CHECKING

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NexusMetroApiClient, NexusMetroApiError, NexusMetroAuthError, NexusMetroConnectionError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .models import PlatformInfo, StationData, TrainDeparture

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

type NexusMetroConfigEntry = ConfigEntry[NexusMetroCoordinator]

_LOGGER = logging.getLogger(__name__)


class NexusMetroCoordinator(DataUpdateCoordinator[StationData]):
    """Coordinator to fetch departure data from the Nexus Metro API."""

    config_entry: NexusMetroConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: NexusMetroApiClient,
        station_code: str,
        station_name: str,
        platforms: dict[int, PlatformInfo],
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{station_code}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self.station_code = station_code
        self.station_name = station_name
        self.platforms = platforms

    async def _async_update_data(self) -> StationData:
        """Fetch departure data for all platforms at the station."""
        departures: dict[int, list[TrainDeparture]] = {}

        for platform_number in self.platforms:
            try:
                departures[platform_number] = await self.client.async_get_departures(self.station_code, platform_number)
            except NexusMetroConnectionError as err:
                raise UpdateFailed(f"Cannot connect to Nexus Metro API: {err}") from err
            except NexusMetroAuthError as err:
                raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
            except NexusMetroApiError as err:
                _LOGGER.warning(
                    "Failed to fetch departures for %s platform %s: %s",
                    self.station_code,
                    platform_number,
                    err,
                )
                departures[platform_number] = []

        return StationData(
            station_code=self.station_code,
            station_name=self.station_name,
            platforms=self.platforms,
            departures=departures,
        )
