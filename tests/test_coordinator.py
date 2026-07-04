"""Tests for the Nexus Metro coordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from custom_components.nexus_metro.api import NexusMetroConnectionError, NexusMetroResponseError
from custom_components.nexus_metro.coordinator import NexusMetroCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from .conftest import SAMPLE_TRAVELINE_DEPARTURES


def _make_coordinator(
    hass: HomeAssistant,
    traveline: AsyncMock,
    kml: AsyncMock,
) -> NexusMetroCoordinator:
    return NexusMetroCoordinator(
        hass=hass,
        traveline_client=traveline,
        kml_client=kml,
        station_code="JES",
        station_name="Jesmond",
        platform_numbers=[1, 2],
        scan_interval=60,
    )


class TestCoordinatorUpdate:
    async def test_successful_update(
        self,
        hass: HomeAssistant,
        mock_traveline_client: AsyncMock,
        mock_kml_client: AsyncMock,
    ):
        coordinator = _make_coordinator(hass, mock_traveline_client, mock_kml_client)
        data = await coordinator._async_update_data()

        assert data.station_code == "JES"
        assert data.station_name == "Jesmond"
        assert 1 in data.platforms
        assert 2 in data.platforms
        assert mock_traveline_client.async_get_departures.call_count == 2
        assert mock_kml_client.async_get_trains.call_count == 1

    async def test_traveline_departures_populated(
        self,
        hass: HomeAssistant,
        mock_traveline_client: AsyncMock,
        mock_kml_client: AsyncMock,
    ):
        coordinator = _make_coordinator(hass, mock_traveline_client, mock_kml_client)
        data = await coordinator._async_update_data()

        platform_data = data.platforms[1]
        assert len(platform_data.traveline_departures) == 3
        assert len(platform_data.combined_departures) == 3

    async def test_empty_departures_overnight(
        self,
        hass: HomeAssistant,
        mock_traveline_client: AsyncMock,
        mock_kml_client: AsyncMock,
    ):
        mock_traveline_client.async_get_departures.return_value = []
        mock_kml_client.async_get_trains.return_value = []

        coordinator = _make_coordinator(hass, mock_traveline_client, mock_kml_client)
        data = await coordinator._async_update_data()

        assert data.platforms[1].traveline_departures == []
        assert data.platforms[1].combined_departures == []

    async def test_traveline_connection_error_raises_update_failed(
        self,
        hass: HomeAssistant,
        mock_traveline_client: AsyncMock,
        mock_kml_client: AsyncMock,
    ):
        mock_traveline_client.async_get_departures.side_effect = NexusMetroConnectionError("timeout")

        coordinator = _make_coordinator(hass, mock_traveline_client, mock_kml_client)

        with pytest.raises(UpdateFailed, match="Cannot connect to Traveline"):
            await coordinator._async_update_data()

    async def test_kml_error_falls_back_to_scheduled_only(
        self,
        hass: HomeAssistant,
        mock_traveline_client: AsyncMock,
        mock_kml_client: AsyncMock,
    ):
        mock_kml_client.async_get_trains.side_effect = NexusMetroConnectionError("timeout")

        coordinator = _make_coordinator(hass, mock_traveline_client, mock_kml_client)
        data = await coordinator._async_update_data()

        # Should still have Traveline data, just no live matching
        assert len(data.platforms[1].traveline_departures) == 3
        assert all(d.status == "Scheduled" for d in data.platforms[1].combined_departures)

    async def test_traveline_response_error_on_one_platform_continues(
        self,
        hass: HomeAssistant,
        mock_traveline_client: AsyncMock,
        mock_kml_client: AsyncMock,
    ):
        call_count = 0

        async def side_effect(atco_code):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise NexusMetroResponseError("bad response")
            return SAMPLE_TRAVELINE_DEPARTURES

        mock_traveline_client.async_get_departures.side_effect = side_effect

        coordinator = _make_coordinator(hass, mock_traveline_client, mock_kml_client)
        data = await coordinator._async_update_data()

        assert data.platforms[1].traveline_departures == []
        assert len(data.platforms[2].traveline_departures) == 3

    async def test_all_live_trains_populated(
        self,
        hass: HomeAssistant,
        mock_traveline_client: AsyncMock,
        mock_kml_client: AsyncMock,
    ):
        coordinator = _make_coordinator(hass, mock_traveline_client, mock_kml_client)
        data = await coordinator._async_update_data()

        assert len(data.all_live_trains) == 2
