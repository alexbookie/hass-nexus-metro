"""Tests for the Nexus Metro API client."""

from __future__ import annotations

from unittest.mock import AsyncMock

import aiohttp
import pytest

from custom_components.nexus_metro.api import (
    NexusMetroApiClient,
    NexusMetroConnectionError,
    NexusMetroResponseError,
    _parse_departure,
    _parse_event,
    _parse_line,
    _parse_platforms,
)
from custom_components.nexus_metro.models import MetroLine, PlatformDirection, TrainEvent

from .conftest import SAMPLE_DEPARTURES_PARSED, SAMPLE_DEPARTURES_RAW, SAMPLE_PLATFORMS_RAW, SAMPLE_STATIONS

# --- Helper / parser unit tests ---


class TestParseLine:
    def test_green(self):
        assert _parse_line("GREEN") == MetroLine.GREEN

    def test_yellow(self):
        assert _parse_line("YELLOW") == MetroLine.YELLOW

    def test_none(self):
        assert _parse_line(None) is None

    def test_unknown_returns_none(self):
        assert _parse_line("PURPLE") is None


class TestParseEvent:
    def test_all_known_events(self):
        assert _parse_event("ARRIVED") == TrainEvent.ARRIVED
        assert _parse_event("DEPARTED") == TrainEvent.DEPARTED
        assert _parse_event("APPROACHING") == TrainEvent.APPROACHING
        assert _parse_event("READY_TO_START") == TrainEvent.READY_TO_START

    def test_unknown_defaults_to_departed(self):
        assert _parse_event("UNKNOWN_STATE") == TrainEvent.DEPARTED


class TestParseDeparture:
    def test_full_data(self):
        result = _parse_departure(SAMPLE_DEPARTURES_RAW[0])
        assert result == SAMPLE_DEPARTURES_PARSED[0]

    def test_minimal_data(self):
        result = _parse_departure({"lastEvent": "ARRIVED"})
        assert result.train_number == ""
        assert result.destination == "Unknown"
        assert result.due_in == -1
        assert result.line is None
        assert result.last_event == TrainEvent.ARRIVED
        assert result.scheduled_time is None
        assert result.predicted_time is None

    def test_arrived_negative_due_in(self):
        raw = {**SAMPLE_DEPARTURES_RAW[0], "dueIn": -1, "lastEvent": "ARRIVED"}
        result = _parse_departure(raw)
        assert result.due_in == -1
        assert result.last_event == TrainEvent.ARRIVED


class TestParsePlatforms:
    def test_standard_two_platforms(self):
        result = _parse_platforms(SAMPLE_PLATFORMS_RAW["JES"])
        assert len(result) == 2
        assert result[1].direction == PlatformDirection.IN
        assert result[2].direction == PlatformDirection.OUT
        assert result[1].helper_text == "To South Hylton and South Shields"

    def test_empty_list(self):
        result = _parse_platforms([])
        assert result == {}


# --- API client tests ---


def _mock_response(status: int = 200, json_data: object = None) -> AsyncMock:
    """Create a mock aiohttp response as an async context manager."""
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_data)

    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


class TestGetStations:
    async def test_success(self, mock_session: AsyncMock, api_client: NexusMetroApiClient):
        mock_session.get.return_value = _mock_response(json_data=SAMPLE_STATIONS)

        result = await api_client.async_get_stations()

        assert result == SAMPLE_STATIONS
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert "/stations" in call_args.args[0]
        assert call_args.kwargs["headers"]["User-Agent"] == "okhttp/3.12.1"

    async def test_non_dict_response(self, mock_session: AsyncMock, api_client: NexusMetroApiClient):
        mock_session.get.return_value = _mock_response(json_data=["not", "a", "dict"])

        with pytest.raises(NexusMetroResponseError, match="Expected dict"):
            await api_client.async_get_stations()

    async def test_401_response(self, mock_session: AsyncMock, api_client: NexusMetroApiClient):
        mock_session.get.return_value = _mock_response(status=401)

        with pytest.raises(NexusMetroResponseError, match="401"):
            await api_client.async_get_stations()

    async def test_500_response(self, mock_session: AsyncMock, api_client: NexusMetroApiClient):
        mock_session.get.return_value = _mock_response(status=500)

        with pytest.raises(NexusMetroResponseError, match="500"):
            await api_client.async_get_stations()

    async def test_connection_error(self, mock_session: AsyncMock, api_client: NexusMetroApiClient):
        mock_session.get.side_effect = aiohttp.ClientError("Connection refused")

        with pytest.raises(NexusMetroConnectionError, match="Failed to connect"):
            await api_client.async_get_stations()


class TestGetPlatforms:
    async def test_success(self, mock_session: AsyncMock, api_client: NexusMetroApiClient):
        mock_session.get.return_value = _mock_response(json_data=SAMPLE_PLATFORMS_RAW)

        result = await api_client.async_get_platforms("JES")

        assert len(result) == 2
        assert result[1].direction == PlatformDirection.IN
        assert result[2].direction == PlatformDirection.OUT

    async def test_case_insensitive_station_code(self, mock_session: AsyncMock, api_client: NexusMetroApiClient):
        mock_session.get.return_value = _mock_response(json_data=SAMPLE_PLATFORMS_RAW)

        result = await api_client.async_get_platforms("jes")

        assert len(result) == 2

    async def test_unknown_station(self, mock_session: AsyncMock, api_client: NexusMetroApiClient):
        mock_session.get.return_value = _mock_response(json_data=SAMPLE_PLATFORMS_RAW)

        with pytest.raises(NexusMetroResponseError, match="No platform data found"):
            await api_client.async_get_platforms("ZZZ")

    async def test_non_dict_response(self, mock_session: AsyncMock, api_client: NexusMetroApiClient):
        mock_session.get.return_value = _mock_response(json_data="not a dict")

        with pytest.raises(NexusMetroResponseError, match="Expected dict"):
            await api_client.async_get_platforms("JES")


class TestGetDepartures:
    async def test_success(self, mock_session: AsyncMock, api_client: NexusMetroApiClient):
        mock_session.get.return_value = _mock_response(json_data=SAMPLE_DEPARTURES_RAW)

        result = await api_client.async_get_departures("JES", 1)

        assert len(result) == 2
        assert result[0] == SAMPLE_DEPARTURES_PARSED[0]
        assert result[1] == SAMPLE_DEPARTURES_PARSED[1]

    async def test_empty_response_overnight(self, mock_session: AsyncMock, api_client: NexusMetroApiClient):
        mock_session.get.return_value = _mock_response(json_data=[])

        result = await api_client.async_get_departures("JES", 1)

        assert result == []

    async def test_case_insensitive_station_code(self, mock_session: AsyncMock, api_client: NexusMetroApiClient):
        mock_session.get.return_value = _mock_response(json_data=[])

        await api_client.async_get_departures("jes", 1)

        call_url = mock_session.get.call_args.args[0]
        assert "/times/JES/1" in call_url

    async def test_non_list_response(self, mock_session: AsyncMock, api_client: NexusMetroApiClient):
        mock_session.get.return_value = _mock_response(json_data={"error": "bad"})

        with pytest.raises(NexusMetroResponseError, match="Expected list"):
            await api_client.async_get_departures("JES", 1)


class TestTestConnection:
    async def test_success(self, mock_session: AsyncMock, api_client: NexusMetroApiClient):
        mock_session.get.return_value = _mock_response(json_data=SAMPLE_STATIONS)

        result = await api_client.async_test_connection()

        assert result is True

    async def test_empty_stations(self, mock_session: AsyncMock, api_client: NexusMetroApiClient):
        mock_session.get.return_value = _mock_response(json_data={})

        result = await api_client.async_test_connection()

        assert result is False

    async def test_connection_failure_propagates(self, mock_session: AsyncMock, api_client: NexusMetroApiClient):
        mock_session.get.side_effect = aiohttp.ClientError("timeout")

        with pytest.raises(NexusMetroConnectionError):
            await api_client.async_test_connection()
