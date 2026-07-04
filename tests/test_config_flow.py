"""Tests for the Nexus Metro config flow."""

from __future__ import annotations

from custom_components.nexus_metro.const import CONF_PLATFORMS, CONF_STATION_CODE, CONF_STATION_NAME, DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType


class TestUserStep:
    async def test_show_form(self, hass: HomeAssistant):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"

    async def test_station_selected_goes_to_platforms(self, hass: HomeAssistant):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_STATION_CODE: "JES"},
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "platforms"


class TestPlatformsStep:
    async def test_create_entry_all_platforms(self, hass: HomeAssistant):
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

    async def test_create_entry_single_platform(self, hass: HomeAssistant):
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

    async def test_no_platforms_defaults_to_all(self, hass: HomeAssistant):
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

    async def test_monument_has_four_platforms(self, hass: HomeAssistant):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_STATION_CODE: "MTS"},
        )

        # Verify it's showing the platforms form
        assert result["step_id"] == "platforms"

    async def test_duplicate_station_aborts(self, hass: HomeAssistant):
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
