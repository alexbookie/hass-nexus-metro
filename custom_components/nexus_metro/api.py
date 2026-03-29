"""API client for the Nexus Metro RTI (Real-Time Information) API."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

import aiohttp

from .models import MetroLine, PlatformDirection, PlatformInfo, TrainDeparture, TrainEvent

if TYPE_CHECKING:
    from .auth import NexusMetroTokenManager

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://metro-rti.nexus.org.uk/api"
USER_AGENT = "okhttp/3.12.1"

_LONDON_TZ = ZoneInfo("Europe/London")


class NexusMetroApiError(Exception):
    """Base exception for Nexus Metro API errors."""


class NexusMetroAuthError(NexusMetroApiError):
    """Raised when token acquisition or authentication fails."""


class NexusMetroConnectionError(NexusMetroApiError):
    """Raised when the API is unreachable."""


class NexusMetroResponseError(NexusMetroApiError):
    """Raised when the API returns an unexpected response."""


def _parse_uk_timestamp(raw: str | None) -> datetime | None:
    """Parse a naive UK local timestamp string into a timezone-aware datetime."""
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).replace(tzinfo=_LONDON_TZ)
    except ValueError:
        _LOGGER.warning("Could not parse timestamp: %r", raw)
        return None


def _parse_line(raw: str | None) -> MetroLine | None:
    """Parse a metro line string, returning None for unknown values."""
    if raw is None:
        return None
    try:
        return MetroLine(raw)
    except ValueError:
        _LOGGER.warning("Unknown metro line value: %s", raw)
        return None


def _parse_event(raw: str) -> TrainEvent:
    """Parse a train event string."""
    try:
        return TrainEvent(raw)
    except ValueError:
        _LOGGER.warning("Unknown train event value: %s, defaulting to DEPARTED", raw)
        return TrainEvent.DEPARTED


def _parse_departure(data: dict[str, Any]) -> TrainDeparture:
    """Parse a single train departure from API JSON."""
    departure_dt = _parse_uk_timestamp(data.get("actualPredictedTime")) or _parse_uk_timestamp(
        data.get("actualScheduledTime")
    )
    return TrainDeparture(
        train_number=str(data.get("trn", "")),
        destination=data.get("destination", "Unknown"),
        due_in=int(data.get("dueIn", -1)),
        line=_parse_line(data.get("line")),
        last_event=_parse_event(data.get("lastEvent", "DEPARTED")),
        last_event_location=data.get("lastEventLocation", ""),
        last_event_time=data.get("lastEventTime", ""),
        scheduled_time=data.get("actualScheduledTime"),
        predicted_time=data.get("actualPredictedTime"),
        departure_dt=departure_dt,
    )


def _parse_platforms(raw: list[dict[str, Any]]) -> dict[int, PlatformInfo]:
    """Parse platform info list into a dict keyed by platform number."""
    platforms: dict[int, PlatformInfo] = {}
    for item in raw:
        number = int(item["platformNumber"])
        platforms[number] = PlatformInfo(
            platform_number=number,
            direction=PlatformDirection(item["direction"]),
            helper_text=item.get("helperText", ""),
        )
    return platforms


class NexusMetroApiClient:
    """Client for the Nexus Metro RTI API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        token_manager: NexusMetroTokenManager | None = None,
    ) -> None:
        """Initialise with an aiohttp session and optional token manager."""
        self._session = session
        self._token_manager = token_manager

    async def _get(self, path: str) -> Any:
        """Make a GET request to the API."""
        url = f"{BASE_URL}{path}"
        headers: dict[str, str] = {"User-Agent": USER_AGENT}

        if self._token_manager is not None:
            token = await self._token_manager.async_get_token()
            headers["Authorization"] = f"Bearer {token}"

        try:
            async with self._session.get(url, headers=headers) as resp:
                if resp.status == 401 and self._token_manager is not None:
                    # Token may have expired — invalidate and retry once
                    self._token_manager.invalidate()
                    new_token = await self._token_manager.async_get_token()
                    headers["Authorization"] = f"Bearer {new_token}"
                    async with self._session.get(url, headers=headers) as retry_resp:
                        if retry_resp.status == 401:
                            raise NexusMetroAuthError(f"API returned 401 for {path} after token refresh")
                        if retry_resp.status != 200:
                            raise NexusMetroResponseError(f"API returned HTTP {retry_resp.status} for {path}")
                        return await retry_resp.json()
                if resp.status == 401:
                    raise NexusMetroResponseError(
                        f"API returned 401 for {path} — the API may now require authentication"
                    )
                if resp.status != 200:
                    raise NexusMetroResponseError(f"API returned HTTP {resp.status} for {path}")
                return await resp.json()
        except aiohttp.ClientError as err:
            raise NexusMetroConnectionError(f"Failed to connect to Nexus Metro API: {err}") from err

    async def async_get_stations(self) -> dict[str, str]:
        """Fetch all stations.

        Returns a dict of {station_code: station_name}.
        """
        data = await self._get("/stations")
        if not isinstance(data, dict):
            raise NexusMetroResponseError(f"Expected dict from /stations, got {type(data).__name__}")
        return data

    async def async_get_platforms(self, station_code: str) -> dict[int, PlatformInfo]:
        """Fetch platform info for all stations and return platforms for the given station."""
        data = await self._get("/stations/platforms")
        if not isinstance(data, dict):
            raise NexusMetroResponseError(f"Expected dict from /stations/platforms, got {type(data).__name__}")
        station_upper = station_code.upper()
        raw_platforms = data.get(station_upper, [])
        if not raw_platforms:
            raise NexusMetroResponseError(f"No platform data found for station {station_upper}")
        return _parse_platforms(raw_platforms)

    async def async_get_departures(self, station_code: str, platform_number: int) -> list[TrainDeparture]:
        """Fetch upcoming departures for a specific platform at a station."""
        path = f"/times/{station_code.upper()}/{platform_number}"
        data = await self._get(path)
        if not isinstance(data, list):
            raise NexusMetroResponseError(f"Expected list from {path}, got {type(data).__name__}")
        return [_parse_departure(item) for item in data]

    async def async_test_connection(self) -> bool:
        """Test API connectivity by fetching the station list."""
        stations = await self.async_get_stations()
        return len(stations) > 0
