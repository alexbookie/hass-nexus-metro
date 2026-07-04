"""Shared test fixtures for Nexus Metro tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from custom_components.nexus_metro.api import KmlClient, TravelineClient
from custom_components.nexus_metro.const import CONF_PLATFORMS, CONF_STATION_CODE, CONF_STATION_NAME, DOMAIN
from custom_components.nexus_metro.models import CombinedDeparture, LiveTrain, TrainEvent, TravelineDeparture
from homeassistant.core import HomeAssistant

SAMPLE_TRAVELINE_DEPARTURES: list[TravelineDeparture] = [
    TravelineDeparture(
        service="G",
        destination="South Hylton",
        due="3 mins",
        scheduled_mins=3.0,
    ),
    TravelineDeparture(
        service="Y",
        destination="South Shields",
        due="8 mins",
        scheduled_mins=8.0,
    ),
    TravelineDeparture(
        service="G",
        destination="South Hylton",
        due="14 mins",
        scheduled_mins=14.0,
    ),
]

SAMPLE_LIVE_TRAINS: list[LiveTrain] = [
    LiveTrain(
        train_id="102",
        lat=54.98,
        lon=-1.62,
        event=TrainEvent.DEPARTED,
        event_station_code="RGC",
        event_platform=1,
        event_time_mins=15 * 60 + 3,  # 15:03
        destination="South Hylton",
    ),
    LiveTrain(
        train_id="124",
        lat=55.01,
        lon=-1.55,
        event=TrainEvent.APPROACHING,
        event_station_code="PMV",
        event_platform=1,
        event_time_mins=15 * 60 + 3,  # 15:03
        destination="South Shields",
    ),
]

SAMPLE_COMBINED_DEPARTURES: list[CombinedDeparture] = [
    CombinedDeparture(
        service="G",
        destination="South Hylton",
        scheduled_due="3 mins",
        scheduled_mins=3.0,
        live_estimate_mins=3.5,
        status="On time",
        train_id="102",
        train_info="Departed RGC",
    ),
    CombinedDeparture(
        service="Y",
        destination="South Shields",
        scheduled_due="8 mins",
        scheduled_mins=8.0,
        live_estimate_mins=None,
        status="Scheduled",
        train_id="",
        train_info="",
    ),
]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable custom integrations for all tests."""


@pytest.fixture
def mock_traveline_client() -> AsyncMock:
    """Create a mock Traveline client."""
    client = AsyncMock(spec=TravelineClient)
    client.async_get_departures.return_value = SAMPLE_TRAVELINE_DEPARTURES
    return client


@pytest.fixture
def mock_kml_client() -> AsyncMock:
    """Create a mock KML client."""
    client = AsyncMock(spec=KmlClient)
    client.async_get_trains.return_value = SAMPLE_LIVE_TRAINS
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
        unique_id="JES",
        version=2,
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def mock_nexus_clients():
    """Patch Traveline and KML clients for integration-level tests."""
    with (
        patch("custom_components.nexus_metro.TravelineClient") as mock_trav_cls,
        patch("custom_components.nexus_metro.KmlClient") as mock_kml_cls,
        patch("custom_components.nexus_metro.async_get_clientsession"),
    ):
        trav_client = AsyncMock(spec=TravelineClient)
        trav_client.async_get_departures.return_value = SAMPLE_TRAVELINE_DEPARTURES

        kml_client = AsyncMock(spec=KmlClient)
        kml_client.async_get_trains.return_value = SAMPLE_LIVE_TRAINS

        mock_trav_cls.return_value = trav_client
        mock_kml_cls.return_value = kml_client

        yield trav_client, kml_client
