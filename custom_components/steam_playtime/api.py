"""Minimal async client for the Steam Web API."""

from __future__ import annotations

import asyncio
import re
from typing import Any

import aiohttp

API_BASE = "https://api.steampowered.com"
_STEAMID64 = re.compile(r"^\d{17}$")


class SteamError(Exception):
    """Base Steam error."""


class SteamAuthError(SteamError):
    """The API key was rejected."""


class SteamConnectionError(SteamError):
    """Steam could not be reached or returned an unexpected response."""


class SteamPrivateError(SteamError):
    """The profile's game details are not public."""


class SteamNotFoundError(SteamError):
    """The Steam ID or custom URL could not be found."""


async def _get(
    session: aiohttp.ClientSession, path: str, params: dict[str, Any]
) -> dict[str, Any]:
    try:
        async with asyncio.timeout(20):
            async with session.get(f"{API_BASE}/{path}", params=params) as resp:
                if resp.status in (401, 403):
                    raise SteamAuthError("Steam rejected the API key")
                if resp.status != 200:
                    raise SteamConnectionError(f"Steam returned HTTP {resp.status}")
                return await resp.json(content_type=None)
    except (aiohttp.ClientError, TimeoutError) as err:
        raise SteamConnectionError(str(err) or "Timed out talking to Steam") from err


async def resolve_steam_id(
    session: aiohttp.ClientSession, api_key: str, value: str
) -> str:
    """Accept a SteamID64, a profile URL, or a custom URL name and return a SteamID64."""
    value = value.strip().rstrip("/")
    if match := re.search(r"steamcommunity\.com/profiles/(\d{17})", value):
        return match.group(1)
    if _STEAMID64.match(value):
        return value
    if match := re.search(r"steamcommunity\.com/id/([^/?#]+)", value):
        value = match.group(1)

    data = await _get(
        session,
        "ISteamUser/ResolveVanityURL/v1/",
        {"key": api_key, "vanityurl": value},
    )
    response = data.get("response", {})
    if response.get("success") != 1 or not response.get("steamid"):
        raise SteamNotFoundError(f"No Steam account found for '{value}'")
    return response["steamid"]


async def get_persona_name(
    session: aiohttp.ClientSession, api_key: str, steam_id: str
) -> str:
    """Return the account's display name, falling back to the ID."""
    data = await _get(
        session,
        "ISteamUser/GetPlayerSummaries/v2/",
        {"key": api_key, "steamids": steam_id},
    )
    players = data.get("response", {}).get("players", [])
    if not players:
        raise SteamNotFoundError(f"No Steam account found for '{steam_id}'")
    return players[0].get("personaname") or steam_id


async def get_owned_games(
    session: aiohttp.ClientSession, api_key: str, steam_id: str
) -> list[dict[str, Any]]:
    """Return every owned game with lifetime playtime (minutes)."""
    data = await _get(
        session,
        "IPlayerService/GetOwnedGames/v1/",
        {
            "key": api_key,
            "steamid": steam_id,
            "include_appinfo": 1,
            "include_played_free_games": 1,
            "format": "json",
        },
    )
    response = data.get("response", {})
    # A private profile comes back as an empty response object.
    if "game_count" not in response:
        raise SteamPrivateError("Game details on this profile are not public")
    return response.get("games", [])


async def get_recent_games(
    session: aiohttp.ClientSession, api_key: str, steam_id: str
) -> list[dict[str, Any]]:
    """Return games played in the last two weeks (playtime_2weeks in minutes)."""
    data = await _get(
        session,
        "IPlayerService/GetRecentlyPlayedGames/v1/",
        {"key": api_key, "steamid": steam_id, "format": "json"},
    )
    return data.get("response", {}).get("games", [])
