"""Data update coordinator for Steam Playtime."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    SteamAuthError,
    SteamConnectionError,
    SteamError,
    SteamPrivateError,
    get_owned_games,
    get_recent_games,
)
from .const import CONF_SCAN_HOURS, CONF_STEAM_ID, DEFAULT_SCAN_HOURS, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SteamPlaytimeCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetches owned and recently played games from Steam."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        hours = int(entry.options.get(CONF_SCAN_HOURS, DEFAULT_SCAN_HOURS))
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.title}",
            update_interval=timedelta(hours=hours),
        )
        self.api_key: str = entry.data[CONF_API_KEY]
        self.steam_id: str = entry.data[CONF_STEAM_ID]
        self.session = async_get_clientsession(hass)

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            owned = await get_owned_games(self.session, self.api_key, self.steam_id)
            recent = await get_recent_games(self.session, self.api_key, self.steam_id)
        except SteamAuthError as err:
            raise UpdateFailed("Steam rejected the API key") from err
        except SteamPrivateError as err:
            raise UpdateFailed(
                "Game details on this Steam profile are private; set them to Public"
            ) from err
        except SteamConnectionError as err:
            raise UpdateFailed(f"Error talking to Steam: {err}") from err
        except SteamError as err:
            raise UpdateFailed(str(err)) from err

        return {
            "games": sorted(
                owned, key=lambda g: g.get("playtime_forever", 0), reverse=True
            ),
            "recent": sorted(
                recent, key=lambda g: g.get("playtime_2weeks", 0), reverse=True
            ),
        }
