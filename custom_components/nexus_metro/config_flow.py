"""Config flow for Nexus Metro."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NexusMetroApiClient, NexusMetroApiError, NexusMetroConnectionError
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
from .models import PlatformInfo

_LOGGER = logging.getLogger(__name__)


class NexusMetroConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Nexus Metro."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise the config flow."""
        self._stations: dict[str, str] = {}
        self._selected_station_code: str = ""
        self._selected_station_name: str = ""
        self._platforms: dict[int, PlatformInfo] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the station selection step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._selected_station_code = user_input[CONF_STATION_CODE]
            self._selected_station_name = self._stations[self._selected_station_code]

            try:
                session = async_get_clientsession(self.hass)
                client = NexusMetroApiClient(session=session)
                self._platforms = await client.async_get_platforms(self._selected_station_code)
            except NexusMetroConnectionError:
                errors["base"] = "cannot_connect"
            except NexusMetroApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return await self.async_step_platforms()

        # Fetch stations if not already loaded
        if not self._stations:
            try:
                session = async_get_clientsession(self.hass)
                client = NexusMetroApiClient(session=session)
                self._stations = await client.async_get_stations()
            except (NexusMetroConnectionError, NexusMetroApiError):
                errors["base"] = "cannot_connect"
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema({}),
                    errors=errors,
                )
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema({}),
                    errors=errors,
                )

        sorted_stations = dict(sorted(self._stations.items(), key=lambda x: x[1]))

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STATION_CODE): vol.In(sorted_stations),
                }
            ),
            errors=errors,
        )

    async def async_step_platforms(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the optional platform selection step."""
        if user_input is not None:
            selected = user_input.get(CONF_PLATFORMS, [])

            await self.async_set_unique_id(
                f"{self._selected_station_code}_{'_'.join(str(p) for p in sorted(selected)) if selected else 'all'}"
            )
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=self._selected_station_name,
                data={
                    CONF_STATION_CODE: self._selected_station_code,
                    CONF_STATION_NAME: self._selected_station_name,
                    CONF_PLATFORMS: sorted(selected) if selected else list(self._platforms.keys()),
                },
            )

        platform_options = {
            num: f"Platform {num} — {info.helper_text}" for num, info in sorted(self._platforms.items())
        }

        return self.async_show_form(
            step_id="platforms",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_PLATFORMS, default=list(self._platforms.keys())): vol.All(
                        [vol.In(platform_options)],
                    ),
                }
            ),
            description_placeholders={
                "station_name": self._selected_station_name,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigFlow,
    ) -> NexusMetroOptionsFlow:
        """Get the options flow handler."""
        return NexusMetroOptionsFlow()


class NexusMetroOptionsFlow(OptionsFlow):
    """Handle options flow for Nexus Metro."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
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
