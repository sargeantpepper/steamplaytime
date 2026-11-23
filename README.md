# Steam Playtime for Home Assistant

Brings your Steam playtime stats into Home Assistant, set up entirely from the UI.

## Sensors (one device per Steam account)

| Sensor | State | Attributes |
|---|---|---|
| Most played game | Game name (with header art) | `hours`, `appid`, `top_games` (top N list) |
| Total playtime | Lifetime hours across all games | – |
| Games owned | Number of games in library | – |
| Games played | Games with any playtime | – |
| Playtime last 2 weeks | Hours played in the last 14 days | `recent_games` |
| Most played recently | Top game of the last 2 weeks | `hours`, `appid` |

Each entry in `top_games` / `recent_games` has `name`, `appid`, `hours` and `image`.
These lists are excluded from the recorder, so big libraries won't bloat your database.

## Before you start

1. Get a Steam Web API key: https://steamcommunity.com/dev/apikey
2. In Steam → Edit Profile → Privacy Settings, set **Game details** to **Public**.

## Install

**Manual:** copy `custom_components/steam_playtime` into your Home Assistant `config/custom_components/` folder and restart.

**HACS (custom repository):** in HACS → ⋮ → Custom repositories, add `https://github.com/sargeantpepper/steamplaytime` as type *Integration*, install, and restart.

## Set up

Settings → Devices & services → Add integration → **Steam Playtime**.
Enter your API key and your SteamID64, profile link, or custom URL name.

Use **Configure** on the integration to change how many games appear in the top lists (default 10) and how often it refreshes (default every hour).

## Dashboard example (Markdown card)

```jinja
{% for g in state_attr('sensor.YOURNAME_most_played_game', 'top_games') or [] %}
{{ loop.index }}. **{{ g.name }}** — {{ g.hours }} h
{% endfor %}
```

Swap `YOURNAME` for the start of your entity IDs (the integration names them after your Steam display name).
