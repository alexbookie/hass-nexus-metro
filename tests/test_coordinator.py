"""Tests for the Nexus Metro coordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from custom_components.nexus_metro.api import NexusMetroConnectionError, NexusMetroResponseError
from custom_components.nexus_metro.auth import NexusMetroAuthError
from custom_components.nexus_metro.coordinator import NexusMetroCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from .conftest import SAMPLE_DEPARTURES_PARSED, SAMPLE_PLATFORMS_PARSED


def _make_coordinator(
    hass: HomeAssistant,
    client: AsyncMock,
) -> NexusMetroCoordinator:
    """Create a coordinator for testing."""
    return NexusMetroCoordinator(
        hass=hass,
        client=client,
        station_code="JES",
        station_name="Jesmond",
        platforms=SAMPLE_PLATFORMS_PARSED,
        scan_interval=90,
    )


class TestCoordinatorUpdate:
    async def test_successful_update(self, hass: HomeAssistant, mock_api_client: AsyncMock):
        coordinator = _make_coordinator(hass, mock_api_client)

        data = await coordinator._async_update_data()

        assert data.station_code == "JES"
        assert data.station_name == "Jesmond"
        assert 1 in data.departures
        assert 2 in data.departures
        assert mock_api_client.async_get_departures.call_count == 2

    async def test_empty_departures_overnight(self, hass: HomeAssistant, mock_api_client: AsyncMock):
        mock_api_client.async_get_departures.return_value = []

        coordinator = _make_coordinator(hass, mock_api_client)
        data = await coordinator._async_update_data()

        assert data.departures[1] == []
        assert data.departures[2] == []

    async def test_connection_error_raises_update_failed(self, hass: HomeAssistant, mock_api_client: AsyncMock):
        mock_api_client.async_get_departures.side_effect = NexusMetroConnectionError("timeout")

        coordinator = _make_coordinator(hass, mock_api_client)

        with pytest.raises(UpdateFailed, match="Cannot connect"):
            await coordinator._async_update_data()

    async def test_response_error_on_one_platform_continues(self, hass: HomeAssistant, mock_api_client: AsyncMock):
        """A non-connection API error on one platform should not fail the whole update."""
        call_count = 0

        async def side_effect(station_code, platform_number):
            nonlocal call_count
            call_count += 1
            if platform_number == 1:
                raise NexusMetroResponseError("unexpected format")
            return SAMPLE_DEPARTURES_PARSED

        mock_api_client.async_get_departures.side_effect = side_effect

        coordinator = _make_coordinator(hass, mock_api_client)
        data = await coordinator._async_update_data()

        assert data.departures[1] == []
        assert len(data.departures[2]) == 2

    async def test_auth_error_raises_config_entry_auth_failed(self, hass: HomeAssistant, mock_api_client: AsyncMock):
        mock_api_client.async_get_departures.side_effect = NexusMetroAuthError("token expired")

        coordinator = _make_coordinator(hass, mock_api_client)

        with pytest.raises(ConfigEntryAuthFailed, match="Authentication failed"):
            await coordinator._async_update_data()

    async def test_platforms_in_data(self, hass: HomeAssistant, mock_api_client: AsyncMock):
        coordinator = _make_coordinator(hass, mock_api_client)
        data = await coordinator._async_update_data()

        assert data.platforms == SAMPLE_PLATFORMS_PARSED
