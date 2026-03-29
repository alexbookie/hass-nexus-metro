"""Tests for the Nexus Metro config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from custom_components.nexus_metro.api import NexusMetroConnectionError
from custom_components.nexus_metro.const import CONF_PLATFORMS, CONF_STATION_CODE, CONF_STATION_NAME, DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import SAMPLE_PLATFORMS_PARSED, SAMPLE_STATIONS


@pytest.fixture
def mock_flow_client():
    """Patch the API client in the config flow module."""
    with (
        patch("custom_components.nexus_metro.config_flow.NexusMetroApiClient") as mock_cls,
        patch("custom_components.nexus_metro.config_flow.NexusMetroTokenManager"),
        patch("custom_components.nexus_metro.config_flow.async_get_clientsession"),
    ):
        client = AsyncMock()
        client.async_get_stations.return_value = SAMPLE_STATIONS
        client.async_get_platforms.return_value = SAMPLE_PLATFORMS_PARSED
        mock_cls.return_value = client
        yield client


class TestUserStep:
    async def test_show_form(self, hass: HomeAssistant, mock_flow_client: AsyncMock):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {}

    async def test_station_selected_goes_to_platforms(self, hass: HomeAssistant, mock_flow_client: AsyncMock):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_STATION_CODE: "JES"},
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "platforms"

    async def test_cannot_connect_on_station_fetch(self, hass: HomeAssistant, mock_flow_client: AsyncMock):
        mock_flow_client.async_get_stations.side_effect = NexusMetroConnectionError("timeout")

        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}

    async def test_cannot_connect_on_platform_fetch(self, hass: HomeAssistant, mock_flow_client: AsyncMock):
        mock_flow_client.async_get_platforms.side_effect = NexusMetroConnectionError("timeout")

        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_STATION_CODE: "JES"},
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"base": "cannot_connect"}

    async def test_unknown_error(self, hass: HomeAssistant, mock_flow_client: AsyncMock):
        mock_flow_client.async_get_stations.side_effect = RuntimeError("unexpected")

        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "unknown"}


class TestPlatformsStep:
    async def test_create_entry_all_platforms(self, hass: HomeAssistant, mock_flow_client: AsyncMock):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_STATION_CODE: "JES"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_PLATFORMS: ["1", "2"]},
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "Jesmond"
        assert result["data"][CONF_STATION_CODE] == "JES"
        assert result["data"][CONF_STATION_NAME] == "Jesmond"
        assert result["data"][CONF_PLATFORMS] == [1, 2]

    async def test_create_entry_single_platform(self, hass: HomeAssistant, mock_flow_client: AsyncMock):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_STATION_CODE: "JES"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_PLATFORMS: ["1"]},
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_PLATFORMS] == [1]

    async def test_create_entry_no_platforms_selected_defaults_to_all(
        self, hass: HomeAssistant, mock_flow_client: AsyncMock
    ):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_STATION_CODE: "JES"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_PLATFORMS: []},
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_PLATFORMS] == [1, 2]

    async def test_duplicate_station_aborts(self, hass: HomeAssistant, mock_flow_client: AsyncMock):
        # Create first entry
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_STATION_CODE: "JES"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_PLATFORMS: ["1", "2"]},
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY

        # Try to add same station again
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_STATION_CODE: "JES"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_PLATFORMS: ["1", "2"]},
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"
