"""Shared test fixtures for Nexus Metro tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from custom_components.nexus_metro.api import NexusMetroApiClient
from custom_components.nexus_metro.const import CONF_PLATFORMS, CONF_STATION_CODE, CONF_STATION_NAME, DOMAIN
from custom_components.nexus_metro.models import MetroLine, PlatformDirection, PlatformInfo, TrainDeparture, TrainEvent
from homeassistant.core import HomeAssistant

SAMPLE_STATIONS: dict[str, str] = {
    "JES": "Jesmond",
    "HAY": "Haymarket",
    "MTS": "Monument N-S",
    "CEN": "Central",
    "SGF": "South Gosforth",
}

SAMPLE_PLATFORMS_RAW: dict[str, list[dict]] = {
    "JES": [
        {"platformNumber": 1, "direction": "IN", "helperText": "To South Hylton and South Shields"},
        {"platformNumber": 2, "direction": "OUT", "helperText": "To Airport and St. James via Whitley Bay"},
    ],
    "SGF": [
        {"platformNumber": 1, "direction": "IN", "helperText": "To South Hylton and South Shields"},
        {"platformNumber": 2, "direction": "OUT", "helperText": "To Airport and St. James via Whitley Bay"},
    ],
}

SAMPLE_DEPARTURES_RAW: list[dict] = [
    {
        "trn": "102",
        "lastEvent": "DEPARTED",
        "lastEventLocation": "Regent Centre Platform 1",
        "lastEventTime": "2024-01-15T15:03:12",
        "destination": "South Hylton",
        "dueIn": 3,
        "line": "GREEN",
        "actualScheduledTime": "2024-01-15T15:05:00",
        "actualPredictedTime": "2024-01-15T15:06:30",
    },
    {
        "trn": "124",
        "lastEvent": "APPROACHING",
        "lastEventLocation": "Palmersville Platform 1",
        "lastEventTime": "2024-01-15T15:03:43",
        "destination": "South Shields",
        "dueIn": 8,
        "line": "YELLOW",
        "actualScheduledTime": "2024-01-15T15:10:00",
        "actualPredictedTime": "2024-01-15T15:11:00",
    },
]

SAMPLE_DEPARTURES_PARSED: list[TrainDeparture] = [
    TrainDeparture(
        train_number="102",
        destination="South Hylton",
        due_in=3,
        line=MetroLine.GREEN,
        last_event=TrainEvent.DEPARTED,
        last_event_location="Regent Centre Platform 1",
        last_event_time="2024-01-15T15:03:12",
        scheduled_time="2024-01-15T15:05:00",
        predicted_time="2024-01-15T15:06:30",
    ),
    TrainDeparture(
        train_number="124",
        destination="South Shields",
        due_in=8,
        line=MetroLine.YELLOW,
        last_event=TrainEvent.APPROACHING,
        last_event_location="Palmersville Platform 1",
        last_event_time="2024-01-15T15:03:43",
        scheduled_time="2024-01-15T15:10:00",
        predicted_time="2024-01-15T15:11:00",
    ),
]

SAMPLE_PLATFORMS_PARSED: dict[int, PlatformInfo] = {
    1: PlatformInfo(
        platform_number=1,
        direction=PlatformDirection.IN,
        helper_text="To South Hylton and South Shields",
    ),
    2: PlatformInfo(
        platform_number=2,
        direction=PlatformDirection.OUT,
        helper_text="To Airport and St. James via Whitley Bay",
    ),
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable custom integrations for all tests."""


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock aiohttp session."""
    return AsyncMock(spec=["get"])


@pytest.fixture
def api_client(mock_session: AsyncMock) -> NexusMetroApiClient:
    """Create a NexusMetroApiClient with a mocked session."""
    return NexusMetroApiClient(session=mock_session)


@pytest.fixture
def mock_api_client() -> AsyncMock:
    """Create a fully mocked API client for higher-level tests."""
    client = AsyncMock(spec=NexusMetroApiClient)
    client.async_get_stations.return_value = SAMPLE_STATIONS
    client.async_get_departures.return_value = SAMPLE_DEPARTURES_PARSED
    client.async_get_platforms.return_value = SAMPLE_PLATFORMS_PARSED
    client.async_test_connection.return_value = True
    return client


@pytest.fixture
def mock_config_entry(hass: HomeAssistant):
    """Create a mock config entry."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Jesmond",
        data={
            CONF_STATION_CODE: "JES",
            CONF_STATION_NAME: "Jesmond",
            CONF_PLATFORMS: [1, 2],
        },
        unique_id="JES_1_2",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def mock_nexus_api():
    """Patch the NexusMetroApiClient for integration-level tests."""
    with (
        patch("custom_components.nexus_metro.config_flow.NexusMetroApiClient") as mock_flow,
        patch("custom_components.nexus_metro.NexusMetroApiClient") as mock_init,
        patch("custom_components.nexus_metro.async_get_clientsession"),
    ):
        client = AsyncMock(spec=NexusMetroApiClient)
        client.async_get_stations.return_value = SAMPLE_STATIONS
        client.async_get_platforms.return_value = SAMPLE_PLATFORMS_PARSED
        client.async_get_departures.return_value = SAMPLE_DEPARTURES_PARSED
        client.async_test_connection.return_value = True

        mock_flow.return_value = client
        mock_init.return_value = client

        yield client
