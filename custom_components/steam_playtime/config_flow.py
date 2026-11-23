"""Config flow for Steam Playtime."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_API_KEY
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    SteamAuthError,
    SteamConnectionError,
    SteamNotFoundError,
    SteamPrivateError,
    get_owned_games,
    get_persona_name,
    resolve_steam_id,
)
from .const import (
    CONF_SCAN_HOURS,
    CONF_STEAM_ID,
    CONF_TOP_N,
    DEFAULT_SCAN_HOURS,
    DEFAULT_TOP_N,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        vol.Required(CONF_STEAM_ID): TextSelector(),
    }
)


class SteamPlaytimeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Steam Playtime."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            api_key = user_input[CONF_API_KEY].strip()
            try:
                steam_id = await resolve_steam_id(
                    session, api_key, user_input[CONF_STEAM_ID]
                )
                name = await get_persona_name(session, api_key, steam_id)
                await get_owned_games(session, api_key, steam_id)
            except SteamAuthError:
                errors["base"] = "invalid_auth"
            except SteamNotFoundError:
                errors[CONF_STEAM_ID] = "not_found"
            except SteamPrivateError:
                errors["base"] = "private_profile"
            except SteamConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error setting up Steam Playtime")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(steam_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=name,
                    data={CONF_API_KEY: api_key, CONF_STEAM_ID: steam_id},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return SteamPlaytimeOptionsFlow()


class SteamPlaytimeOptionsFlow(OptionsFlow):
    """Options: how many top games to list and how often to refresh."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                data={
                    CONF_TOP_N: int(user_input[CONF_TOP_N]),
                    CONF_SCAN_HOURS: int(user_input[CONF_SCAN_HOURS]),
                }
            )

        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_TOP_N, default=options.get(CONF_TOP_N, DEFAULT_TOP_N)
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=50, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Required(
                    CONF_SCAN_HOURS,
                    default=options.get(CONF_SCAN_HOURS, DEFAULT_SCAN_HOURS),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1,
                        max=24,
                        step=1,
                        unit_of_measurement="h",
                        mode=NumberSelectorMode.BOX,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
