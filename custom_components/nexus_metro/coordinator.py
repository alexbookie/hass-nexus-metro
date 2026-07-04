"""DataUpdateCoordinator for the Nexus Metro integration."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
import time
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import KmlClient, NexusMetroConnectionError, NexusMetroResponseError, TravelineClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .matching import build_combined_departures
from .metro_data import get_atco_code
from .models import PlatformData, StationData

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

type NexusMetroConfigEntry = ConfigEntry[NexusMetroCoordinator]

_LOGGER = logging.getLogger(__name__)


class NexusMetroCoordinator(DataUpdateCoordinator[StationData]):
    """Coordinator to fetch and combine Traveline + KML data."""

    config_entry: NexusMetroConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        traveline_client: TravelineClient,
        kml_client: KmlClient,
        station_code: str,
        station_name: str,
        platform_numbers: list[int],
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{station_code}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.traveline_client = traveline_client
        self.kml_client = kml_client
        self.station_code = station_code
        self.station_name = station_name
        self.platform_numbers = platform_numbers

    async def _async_update_data(self) -> StationData:
        """Fetch Traveline + KML data and combine them."""
        timestamp_ms = int(time.time() * 1000)

        # Fetch live train positions (shared across all platforms)
        try:
            all_trains = await self.kml_client.async_get_trains(timestamp_ms)
        except (NexusMetroConnectionError, NexusMetroResponseError) as err:
            _LOGGER.warning("KML feed unavailable, using scheduled data only: %s", err)
            all_trains = []

        # KML event times are in UK local time — always use Europe/London
        uk_now = datetime.now(tz=ZoneInfo("Europe/London"))
        now_mins = uk_now.hour * 60 + uk_now.minute + uk_now.second / 60

        platforms: dict[int, PlatformData] = {}

        for platform_number in self.platform_numbers:
            atco_code = get_atco_code(self.station_code, platform_number)
            if atco_code is None:
                _LOGGER.warning(
                    "No ATCO code for %s platform %d",
                    self.station_code,
                    platform_number,
                )
                platforms[platform_number] = PlatformData(
                    platform_number=platform_number,
                )
                continue

            try:
                traveline_deps = await self.traveline_client.async_get_departures(atco_code)
            except NexusMetroConnectionError as err:
                raise UpdateFailed(f"Cannot connect to Traveline: {err}") from err
            except NexusMetroResponseError as err:
                _LOGGER.warning(
                    "Traveline error for %s platform %d: %s",
                    self.station_code,
                    platform_number,
                    err,
                )
                traveline_deps = []

            combined = build_combined_departures(
                station_code=self.station_code,
                platform_number=platform_number,
                traveline_departures=traveline_deps,
                trains=all_trains,
                now_mins=now_mins,
            )

            platforms[platform_number] = PlatformData(
                platform_number=platform_number,
                traveline_departures=traveline_deps,
                live_trains=all_trains,
                combined_departures=combined,
            )

        return StationData(
            station_code=self.station_code,
            station_name=self.station_name,
            platforms=platforms,
            all_live_trains=all_trains,
        )
