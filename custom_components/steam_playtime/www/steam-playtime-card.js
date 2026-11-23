/*
 * Steam Playtime card
 * Shows your top Steam games and their playtime from the Steam Playtime integration.
 *
 * type: custom:steam-playtime-card
 * entity: sensor.<name>_most_played_game   # or sensor.<name>_playtime_last_2_weeks
 * title: Most played          # optional
 * count: 10                   # optional, 1-50 games to show (default 10)
 * show_images: true           # optional, game banner thumbnails
 * show_bars: true             # optional, relative playtime bars
 * show_icon: true             # optional, Steam icon in the header
 * show_total: true            # optional, total playtime on the right of the header
 * icon: mdi:steam             # optional, any Home Assistant icon
 * show_more: true             # optional, collapsible "Show more" section below the list
 * more_count: 25             # optional, games shown when expanded (up to 50)
 */

const CARD_VERSION = "1.2.0";

const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const fmtHours = (h) => {
  const n = Number(h) || 0;
  if (n >= 100) return `${Math.round(n).toLocaleString()} h`;
  return `${n.toLocaleString(undefined, { maximumFractionDigits: 1 })} h`;
};

class SteamPlaytimeCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("steam-playtime-card-editor");
  }

  static getStubConfig(hass) {
    const ids = Object.keys(hass?.states ?? {});
    const entity =
      ids.find((id) => id.startsWith("sensor.") && Array.isArray(hass.states[id].attributes.top_games)) ||
      ids.find((id) => id.startsWith("sensor.") && Array.isArray(hass.states[id].attributes.recent_games)) ||
      "";
    return { entity, title: "Most played", count: 10, show_images: true, show_bars: true, show_icon: true, show_total: true, icon: "mdi:steam", show_more: true, more_count: 25 };
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("Choose a Steam Playtime sensor (Most played game or Playtime last 2 weeks)");
    }
    this._config = { count: 10, show_images: true, show_bars: true, show_icon: true, show_total: true, icon: "mdi:steam", show_more: true, more_count: 25, ...config };
    this._lastState = undefined;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    const stateObj = hass?.states?.[this._config?.entity];
    if (stateObj === this._lastState) return; // nothing changed
    this._lastState = stateObj;
    this._render();
  }

  getCardSize() {
    return 1 + Math.ceil((this._config?.count ?? 10) / 1.5);
  }

  getGridOptions() {
    return { columns: 6, min_columns: 4 };
  }

  _games(stateObj) {
    const a = stateObj?.attributes ?? {};
    return a.top_games ?? a.recent_games ?? [];
  }

  _render() {
    if (!this.shadowRoot || !this._config) return;
    const cfg = this._config;
    const stateObj = this._hass?.states?.[cfg.entity];
    const recent = stateObj && !stateObj.attributes.top_games && stateObj.attributes.recent_games;
    const title = cfg.title ?? (recent ? "Recently played" : "Most played");
    const total = !stateObj
      ? null
      : recent
        ? Number(stateObj.state)
        : stateObj.attributes.total_hours;
    const showTotal = cfg.show_total && total != null && !Number.isNaN(Number(total));

    let body;
    if (!this._hass) {
      body = "";
    } else if (!stateObj) {
      body = `<div class="msg">Entity not found: ${esc(cfg.entity)}</div>`;
    } else {
      const count = Math.max(1, Number(cfg.count) || 10);
      const moreCount = cfg.show_more ? Math.max(count, Number(cfg.more_count) || 25) : count;
      const all = this._games(stateObj).slice(0, moreCount);
      const games = all.slice(0, count);
      const extra = all.slice(count);
      if (!games.length) {
        body = `<div class="msg">${recent ? "Nothing played in the last 2 weeks" : "No playtime yet"}</div>`;
      } else {
        const max = Math.max(...all.map((g) => Number(g.hours) || 0), 0.1);
        const row = (g, i) => {
          const pct = Math.max(2, Math.round(((Number(g.hours) || 0) / max) * 100));
          const url = `https://store.steampowered.com/app/${encodeURIComponent(g.appid)}`;
          return `
            <li>
              <span class="rank${i === 0 ? " first" : ""}">${i + 1}</span>
              ${cfg.show_images ? `<img src="${esc(g.image)}" alt="" loading="lazy" onerror="this.style.visibility='hidden'">` : ""}
              <div class="info">
                <div class="row">
                  <a class="name" href="${url}" target="_blank" rel="noreferrer" title="${esc(g.name)}">${esc(g.name)}</a>
                  <span class="hours">${fmtHours(g.hours)}</span>
                </div>
                ${cfg.show_bars ? `<div class="bar"><div style="width:${pct}%"></div></div>` : ""}
              </div>
            </li>`;
        };
        body = `<ol>${games.map((g, i) => row(g, i)).join("")}</ol>`;
        if (extra.length) {
          const open = !!this._expanded;
          body += `
            <div class="more${open ? " open" : ""}">
              <div class="more-inner"><ol>${extra.map((g, i) => row(g, i + count)).join("")}</ol></div>
            </div>
            <button class="toggle" type="button" aria-expanded="${open}">
              <span class="toggle-text">${open ? "Show less" : `Show ${extra.length} more`}</span>
              <ha-icon icon="mdi:chevron-down"></ha-icon>
            </button>`;
          this._extraCount = extra.length;
        }
      }
    }

    this.shadowRoot.innerHTML = `
      <style>
        ha-card { padding: 0 16px 12px; }
        .header { display: flex; align-items: center; gap: 8px; padding: 16px 0 8px;
          font-size: var(--ha-card-header-font-size, 20px); color: var(--ha-card-header-color, var(--primary-text-color)); }
        .title { flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .total { display: flex; flex-direction: column; align-items: flex-end; line-height: 1.15; flex: none; }
        .total-value { font-size: 18px; font-weight: 600; color: var(--primary-text-color); font-variant-numeric: tabular-nums; }
        .total-label { font-size: 12px; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: .04em; }
        .header ha-icon { --mdc-icon-size: 30px; color: var(--primary-text-color); flex: none; }
        ol { list-style: none; margin: 0; padding: 0; }
        li { display: flex; align-items: center; gap: 12px; padding: 6px 0; }
        li + li { border-top: 1px solid var(--divider-color); }
        .rank { width: 1.6em; text-align: right; font-weight: 600; color: var(--secondary-text-color); flex: none; }
        .rank.first { color: var(--primary-color); }
        .more { display: grid; grid-template-rows: 0fr; transition: grid-template-rows .3s ease; }
        .more.open { grid-template-rows: 1fr; }
        .more-inner { overflow: hidden; min-height: 0; }
        .more-inner li:first-child { border-top: 1px solid var(--divider-color); }
        .toggle { display: flex; align-items: center; justify-content: center; gap: 4px; width: 100%;
          margin-top: 6px; padding: 8px; border: none; border-radius: 8px; background: none; cursor: pointer;
          font: inherit; font-weight: 500; color: var(--primary-color); }
        .toggle:hover { background: var(--secondary-background-color); }
        .toggle ha-icon { --mdc-icon-size: 20px; transition: transform .3s ease; }
        .toggle[aria-expanded="true"] ha-icon { transform: rotate(180deg); }
        img { width: 92px; height: 43px; object-fit: cover; border-radius: 4px; flex: none;
          background: var(--secondary-background-color); }
        .info { flex: 1; min-width: 0; }
        .row { display: flex; justify-content: space-between; gap: 8px; align-items: baseline; }
        .name { color: var(--primary-text-color); text-decoration: none; font-weight: 500;
          white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .name:hover { text-decoration: underline; }
        .hours { color: var(--secondary-text-color); white-space: nowrap; font-variant-numeric: tabular-nums; flex: none; }
        .bar { height: 4px; margin-top: 6px; border-radius: 2px; background: var(--secondary-background-color, rgba(127,127,127,.15)); overflow: hidden; }
        .bar > div { height: 100%; border-radius: 2px; background: var(--primary-color); }
        .msg { padding: 8px 0 4px; color: var(--secondary-text-color); }
      </style>
      <ha-card>
        ${title || cfg.show_icon || showTotal ? `<div class="header">${cfg.show_icon ? `<ha-icon icon="${esc(cfg.icon || "mdi:steam")}"></ha-icon>` : ""}<span class="title">${esc(title)}</span>${showTotal ? `<span class="total"><span class="total-value">${fmtHours(total)}</span><span class="total-label">${recent ? "last 2 weeks" : "total"}</span></span>` : ""}</div>` : ""}
        ${body}
      </ha-card>`;

    const toggle = this.shadowRoot.querySelector(".toggle");
    if (toggle) {
      toggle.addEventListener("click", () => {
        this._expanded = !this._expanded;
        // Toggle in place so the section animates instead of re-rendering.
        this.shadowRoot.querySelector(".more")?.classList.toggle("open", this._expanded);
        toggle.setAttribute("aria-expanded", String(this._expanded));
        toggle.querySelector(".toggle-text").textContent = this._expanded
          ? "Show less"
          : `Show ${this._extraCount} more`;
      });
    }
  }
}

const EDITOR_SCHEMA = [
  {
    name: "entity",
    required: true,
    selector: { entity: { filter: { integration: "steam_playtime", domain: "sensor" } } },
  },
  { name: "title", selector: { text: {} } },
  { name: "count", selector: { number: { min: 1, max: 50, step: 1, mode: "slider" } } },
  { name: "more_count", selector: { number: { min: 1, max: 50, step: 1, mode: "slider" } } },
  {
    type: "grid",
    name: "",
    schema: [
      { name: "show_images", selector: { boolean: {} } },
      { name: "show_bars", selector: { boolean: {} } },
      { name: "show_icon", selector: { boolean: {} } },
      { name: "show_total", selector: { boolean: {} } },
      { name: "show_more", selector: { boolean: {} } },
      { name: "icon", selector: { icon: {} } },
    ],
  },
];

const EDITOR_LABELS = {
  entity: "Sensor (Most played game = lifetime, Playtime last 2 weeks = recent)",
  title: "Title",
  count: "Number of games to show",
  more_count: "Games shown when expanded",
  show_images: "Show game images",
  show_bars: "Show playtime bars",
  show_icon: "Show Steam icon",
  show_total: "Show total playtime",
  show_more: "Show more / less button",
  icon: "Icon",
};

class SteamPlaytimeCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { count: 10, show_images: true, show_bars: true, show_icon: true, show_total: true, icon: "mdi:steam", ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (s) => EDITOR_LABELS[s.name] ?? s.name;
      this._form.addEventListener("value-changed", (ev) => {
        this._config = ev.detail.value;
        this.dispatchEvent(
          new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true })
        );
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.schema = EDITOR_SCHEMA;
    this._form.data = this._config;
  }
}

if (!customElements.get("steam-playtime-card")) {
  customElements.define("steam-playtime-card", SteamPlaytimeCard);
  customElements.define("steam-playtime-card-editor", SteamPlaytimeCardEditor);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "steam-playtime-card",
    name: "Steam Playtime",
    description: "Your top Steam games and their playtime.",
    preview: true,
    documentationURL: "https://github.com/sargeantpepper/steamplaytime",
  });
  console.info(`%c STEAM-PLAYTIME-CARD %c ${CARD_VERSION} `, "background:#1b2838;color:#fff", "");
}
