"""Sensors for Steam Playtime."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SteamPlaytimeConfigEntry
from .const import CONF_TOP_N, DEFAULT_TOP_N, DOMAIN
from .coordinator import SteamPlaytimeCoordinator

Data = dict[str, Any]


def _header(appid: int) -> str:
    return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg"


def _game(game: dict[str, Any], key: str) -> dict[str, Any]:
    appid = game["appid"]
    return {
        "name": game.get("name", str(appid)),
        "appid": appid,
        "hours": round(game.get(key, 0) / 60, 1),
        "image": _header(appid),
    }


def _played(data: Data) -> list[dict[str, Any]]:
    return [g for g in data["games"] if g.get("playtime_forever", 0) > 0]


def _top(data: Data) -> dict[str, Any] | None:
    played = _played(data)
    return played[0] if played else None


def _recent_top(data: Data) -> dict[str, Any] | None:
    return data["recent"][0] if data["recent"] else None


@dataclass(frozen=True, kw_only=True)
class SteamPlaytimeSensorDescription(SensorEntityDescription):
    """Describes a Steam Playtime sensor."""

    value_fn: Callable[[Data], Any]
    attrs_fn: Callable[[Data, int], dict[str, Any]] | None = None
    picture_fn: Callable[[Data], str | None] | None = None


SENSORS: tuple[SteamPlaytimeSensorDescription, ...] = (
    SteamPlaytimeSensorDescription(
        key="most_played",
        name="Most played game",
        icon="mdi:trophy",
        value_fn=lambda d: (g := _top(d)) and g.get("name"),
        attrs_fn=lambda d, n: {
            **(
                {"hours": _game(g, "playtime_forever")["hours"], "appid": g["appid"]}
                if (g := _top(d))
                else {}
            ),
            "top_games": [_game(g, "playtime_forever") for g in _played(d)[:n]],
        },
        picture_fn=lambda d: _header(g["appid"]) if (g := _top(d)) else None,
    ),
    SteamPlaytimeSensorDescription(
        key="total_playtime",
        name="Total playtime",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=1,
        icon="mdi:timer-outline",
        value_fn=lambda d: round(
            sum(g.get("playtime_forever", 0) for g in d["games"]) / 60, 1
        ),
    ),
    SteamPlaytimeSensorDescription(
        key="games_owned",
        name="Games owned",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gamepad-variant",
        value_fn=lambda d: len(d["games"]),
    ),
    SteamPlaytimeSensorDescription(
        key="games_played",
        name="Games played",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gamepad-variant-outline",
        value_fn=lambda d: len(_played(d)),
    ),
    SteamPlaytimeSensorDescription(
        key="playtime_2weeks",
        name="Playtime last 2 weeks",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=1,
        icon="mdi:calendar-clock",
        value_fn=lambda d: round(
            sum(g.get("playtime_2weeks", 0) for g in d["recent"]) / 60, 1
        ),
        attrs_fn=lambda d, n: {
            "recent_games": [_game(g, "playtime_2weeks") for g in d["recent"][:n]]
        },
    ),
    SteamPlaytimeSensorDescription(
        key="most_played_recently",
        name="Most played recently",
        icon="mdi:fire",
        value_fn=lambda d: (g := _recent_top(d)) and g.get("name"),
        attrs_fn=lambda d, n: (
            {"hours": _game(g, "playtime_2weeks")["hours"], "appid": g["appid"]}
            if (g := _recent_top(d))
            else {}
        ),
        picture_fn=lambda d: _header(g["appid"]) if (g := _recent_top(d)) else None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SteamPlaytimeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    top_n = int(entry.options.get(CONF_TOP_N, DEFAULT_TOP_N))
    async_add_entities(
        SteamPlaytimeSensor(coordinator, description, top_n) for description in SENSORS
    )


class SteamPlaytimeSensor(CoordinatorEntity[SteamPlaytimeCoordinator], SensorEntity):
    """A Steam Playtime sensor."""

    _attr_has_entity_name = True
    # Game lists can be long; keep them out of the history database.
    _unrecorded_attributes = frozenset({"top_games", "recent_games"})
    entity_description: SteamPlaytimeSensorDescription

    def __init__(
        self,
        coordinator: SteamPlaytimeCoordinator,
        description: SteamPlaytimeSensorDescription,
        top_n: int,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._top_n = top_n
        steam_id = coordinator.steam_id
        self._attr_unique_id = f"{steam_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, steam_id)},
            name=coordinator.config_entry.title,
            manufacturer="Valve",
            model="Steam account",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=f"https://steamcommunity.com/profiles/{steam_id}",
        )

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if fn := self.entity_description.attrs_fn:
            return fn(self.coordinator.data, self._top_n)
        return None

    @property
    def entity_picture(self) -> str | None:
        if fn := self.entity_description.picture_fn:
            return fn(self.coordinator.data)
        return None
