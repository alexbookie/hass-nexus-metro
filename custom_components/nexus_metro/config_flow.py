"""Config flow for Nexus Metro."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_PLATFORMS,
    CONF_SCAN_INTERVAL,
    CONF_STATION_CODE,
    CONF_STATION_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .metro_data import STATION_PLATFORM_NUMBERS, get_configurable_stations, get_platform_description

_LOGGER = logging.getLogger(__name__)


class NexusMetroConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Nexus Metro."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialise the config flow."""
        self._selected_station_code: str = ""
        self._selected_station_name: str = ""

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle station selection."""
        if user_input is not None:
            self._selected_station_code = user_input[CONF_STATION_CODE]
            stations = get_configurable_stations()
            self._selected_station_name = stations[self._selected_station_code]
            return await self.async_step_platforms()

        stations = get_configurable_stations()
        sorted_stations = dict(sorted(stations.items(), key=lambda x: x[1]))

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_STATION_CODE): vol.In(sorted_stations)}),
        )

    async def async_step_platforms(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle platform selection."""
        if user_input is not None:
            selected = [int(p) for p in user_input.get(CONF_PLATFORMS, [])]

            await self.async_set_unique_id(self._selected_station_code)
            self._abort_if_unique_id_configured()

            # For Monument, include both MTS and MTW platforms
            all_platform_numbers = self._get_available_platforms()
            if not selected:
                selected = all_platform_numbers

            return self.async_create_entry(
                title=self._selected_station_name,
                data={
                    CONF_STATION_CODE: self._selected_station_code,
                    CONF_STATION_NAME: self._selected_station_name,
                    CONF_PLATFORMS: sorted(selected),
                },
            )

        platform_numbers = self._get_available_platforms()
        platform_options = {
            str(num): get_platform_description(self._selected_station_code, num) for num in platform_numbers
        }

        return self.async_show_form(
            step_id="platforms",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_PLATFORMS,
                        default=[str(k) for k in platform_numbers],
                    ): cv.multi_select(platform_options),
                }
            ),
            description_placeholders={
                "station_name": self._selected_station_name,
            },
        )

    def _get_available_platforms(self) -> list[int]:
        """Get platform numbers for the selected station."""
        code = self._selected_station_code
        platforms = list(STATION_PLATFORM_NUMBERS.get(code, [1, 2]))
        # Monument: combine N-S (MTS 1,2) and E-W (MTW 3,4) platforms
        if code == "MTS":
            platforms.extend(STATION_PLATFORM_NUMBERS.get("MTW", []))
        return platforms

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> NexusMetroOptionsFlow:
        """Get the options flow handler."""
        return NexusMetroOptionsFlow()


class NexusMetroOptionsFlow(OptionsFlow):
    """Handle options flow for Nexus Metro."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the options step."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): vol.All(int, vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)),
                }
            ),
        )
