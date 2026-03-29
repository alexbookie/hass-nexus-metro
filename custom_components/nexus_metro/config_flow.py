"""Config flow for Nexus Metro."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NexusMetroApiClient, NexusMetroApiError, NexusMetroAuthError, NexusMetroConnectionError
from .auth import NexusMetroTokenManager
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
        self._client: NexusMetroApiClient | None = None
        self._stations: dict[str, str] = {}
        self._selected_station_code: str = ""
        self._selected_station_name: str = ""
        self._platforms: dict[int, PlatformInfo] = {}

    def _get_client(self) -> NexusMetroApiClient:
        """Get or create the API client for this flow."""
        if self._client is None:
            session = async_get_clientsession(self.hass)
            token_manager = NexusMetroTokenManager(session=session)
            self._client = NexusMetroApiClient(session=session, token_manager=token_manager)
        return self._client

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the station selection step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._selected_station_code = user_input[CONF_STATION_CODE]
            self._selected_station_name = self._stations[self._selected_station_code]

            try:
                self._platforms = await self._get_client().async_get_platforms(self._selected_station_code)
            except NexusMetroAuthError as err:
                _LOGGER.error("Auth error fetching platforms: %s", err)
                errors["base"] = "invalid_auth"
            except NexusMetroConnectionError as err:
                _LOGGER.error("Connection error fetching platforms: %s", err)
                errors["base"] = "cannot_connect"
            except NexusMetroApiError as err:
                _LOGGER.error("API error fetching platforms: %s", err)
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return await self.async_step_platforms()

        # Fetch stations if not already loaded
        if not self._stations:
            try:
                self._stations = await self._get_client().async_get_stations()
            except NexusMetroAuthError as err:
                _LOGGER.error("Auth error fetching stations: %s", err)
                errors["base"] = "invalid_auth"
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema({}),
                    errors=errors,
                )
            except (NexusMetroConnectionError, NexusMetroApiError) as err:
                _LOGGER.error("Error fetching stations: %s", err)
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
            selected = [int(p) for p in user_input.get(CONF_PLATFORMS, [])]

            await self.async_set_unique_id(self._selected_station_code)
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
            str(num): f"Platform {num} — {info.helper_text}" for num, info in sorted(self._platforms.items())
        }

        return self.async_show_form(
            step_id="platforms",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_PLATFORMS, default=[str(k) for k in self._platforms]): cv.multi_select(
                        platform_options,
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
        config_entry: ConfigEntry,
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
