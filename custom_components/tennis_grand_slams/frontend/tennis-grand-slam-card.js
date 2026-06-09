class TennisGrandSlamCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._expandedKey = null;
  }

  setConfig(config) {
    this.config = {
      status_entity: "sensor.tennis_grand_slams_grand_slam_status",
      today_entity: "sensor.tennis_grand_slams_grand_slam_today_matches",
      live_entity: "sensor.tennis_grand_slams_grand_slam_live_matches",
      upcoming_entity: "sensor.tennis_grand_slams_grand_slam_upcoming_matches",
      results_entity: "sensor.tennis_grand_slams_grand_slam_recent_results",
      max_matches: 14,
      show_recent_results: true,
      ...config,
    };
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 8;
  }

  _render() {
    if (!this.config || !this._hass) {
      return;
    }

    const card = this._ensureCard();
    const statusEntity = this._state(this.config.status_entity);
    if (!statusEntity) {
      card.innerHTML = `
        ${this._styles()}
        <div class="tgs">
          <div class="empty">Status-Sensor nicht gefunden: ${this._escape(this.config.status_entity)}</div>
        </div>
      `;
      return;
    }

    const attrs = statusEntity.attributes || {};
    const todayEntity = this._state(this.config.today_entity);
    const liveEntity = this._state(this.config.live_entity);
    const upcomingEntity = this._state(this.config.upcoming_entity);
    const resultsEntity = this._state(this.config.results_entity);
    const todayMatches = this._matches(todayEntity);
    const liveMatches = this._matches(liveEntity);
    const upcomingMatches = this._matches(upcomingEntity);
    const resultMatches = this._matches(resultsEntity);
    const maxMatches = Number(this.config.max_matches) || 14;

    card.innerHTML = `
      ${this._styles()}
      <div class="tgs">
        ${this._renderHeader(statusEntity)}
        <div class="stats">
          ${this._renderStat("Heute", this._count(todayEntity, attrs.today_matches), "mdi:calendar-today")}
          ${this._renderStat("Live", this._count(liveEntity, attrs.live_matches), "mdi:scoreboard")}
          ${this._renderStat("Kommend", this._count(upcomingEntity, attrs.upcoming_matches), "mdi:calendar-star")}
        </div>
        ${this._renderSection("Live Matches", liveMatches, "live", maxMatches, "Aktuell keine Live-Matches gefunden.")}
        ${this._renderSection("Spiele heute", todayMatches, "today", maxMatches, "Heute sind keine Grand-Slam-Matches geplant.")}
        ${this._renderSection("N\u00e4chste Spiele", upcomingMatches, "upcoming", maxMatches, "Keine kommenden Matches gefunden.")}
        ${this.config.show_recent_results ? this._renderSection("Letzte Ergebnisse", resultMatches, "results", Math.min(maxMatches, 8), "Keine letzten Ergebnisse gefunden.") : ""}
      </div>
    `;

    for (const row of card.querySelectorAll(".match-row")) {
      row.addEventListener("click", (event) => {
        const key = event.currentTarget.dataset.key;
        this._expandedKey = this._expandedKey === key ? null : key;
        this._render();
      });
    }
  }

  _ensureCard() {
    if (!this._card) {
      this._card = document.createElement("ha-card");
      this.shadowRoot.appendChild(this._card);
    }
    return this._card;
  }

  _state(entityId) {
    return entityId ? this._hass.states[entityId] : undefined;
  }

  _matches(entity) {
    const matches = entity?.attributes?.matches;
    return Array.isArray(matches) ? matches : [];
  }

  _count(entity, fallback) {
    const value = Number(entity?.state);
    return Number.isFinite(value) ? value : fallback ?? 0;
  }

  _renderHeader(statusEntity) {
    const attrs = statusEntity.attributes || {};
    const active = Boolean(attrs.is_active);
    const slam = attrs.current_slam || attrs.next_slam || attrs;
    const name = statusEntity.state || slam.name || "Tennis Grand Slams";
    const location = slam.location ? ` in ${this._escape(slam.location)}` : "";
    const status = active ? "L\u00e4uft aktuell" : "N\u00e4chster Grand Slam";
    const dateRange = this._dateRange(slam.start, slam.end);
    const next = attrs.next_slam;
    const nextText = active && next
      ? `N\u00e4chster Start: ${this._escape(next.name)} am ${this._formatDate(next.start)}`
      : `Start: ${this._formatDate(slam.start)}${slam.days_text ? ` (${this._escape(slam.days_text)})` : ""}`;
    const url = this._safeUrl(slam.official_url || attrs.official_url || attrs.espn_url);

    return `
      <div class="hero">
        <div class="hero-main">
          <div class="eyebrow">${status}</div>
          <h2>${this._escape(name)}</h2>
          <div class="meta">${dateRange}${location}</div>
          <div class="next">${nextText}</div>
        </div>
        ${url ? `<a class="hero-link" href="${this._escape(url)}" target="_blank" rel="noreferrer" title="Offizielle Seite"><ha-icon icon="mdi:open-in-new"></ha-icon></a>` : ""}
      </div>
    `;
  }

  _renderStat(label, value, icon) {
    return `
      <div class="stat">
        <ha-icon icon="${icon}"></ha-icon>
        <span>${this._escape(value)}</span>
        <small>${this._escape(label)}</small>
      </div>
    `;
  }

  _renderSection(title, matches, section, maxMatches, emptyText) {
    const visible = matches.slice(0, maxMatches);
    const overflow = matches.length - visible.length;
    return `
      <section class="section">
        <div class="section-head">
          <h3>${this._escape(title)}</h3>
          <span>${matches.length}</span>
        </div>
        ${visible.length ? visible.map((match, index) => this._renderMatch(match, section, index)).join("") : `<div class="empty">${this._escape(emptyText)}</div>`}
        ${overflow > 0 ? `<div class="more">+${overflow} weitere Matches</div>` : ""}
      </section>
    `;
  }

  _renderMatch(match, section, index) {
    const key = `${section}:${match.id || match.short_name || match.name || index}`;
    const expanded = this._expandedKey === key;
    const status = this._matchStatus(match);
    const score = this._score(match);
    const time = this._formatTime(match.start_time);
    const date = this._formatDate(match.start_time);
    const title = match.short_name || match.name || "Tennis Match";
    const round = match.round ? `<span>${this._escape(match.round)}</span>` : "";
    const tour = match.tour ? `<span>${this._escape(match.tour)}</span>` : "";

    return `
      <div class="match ${expanded ? "expanded" : ""}">
        <button class="match-row" data-key="${this._escape(key)}" aria-expanded="${expanded}">
          <span class="time">
            <strong>${this._escape(time)}</strong>
            <small>${this._escape(date)}</small>
          </span>
          <span class="match-copy">
            <span class="match-title">${this._escape(title)}</span>
            <span class="match-meta">${round}${tour}<span>${this._escape(status)}</span></span>
          </span>
          <span class="score ${match.state === "in" ? "live" : ""}">
            ${match.state === "in" ? '<i></i>' : ""}
            ${this._escape(score || status)}
          </span>
        </button>
        ${expanded ? this._renderDetails(match) : ""}
      </div>
    `;
  }

  _renderDetails(match) {
    const competitors = Array.isArray(match.competitors) ? match.competitors : [];
    const left = competitors[0] || {};
    const right = competitors[1] || {};
    const url = this._safeUrl(match.url);
    const rows = [
      ["Status", this._matchStatus(match)],
      ["Uhrzeit", this._formatDateTime(match.start_time)],
      ["Spielstand", this._score(match) || "Noch kein Spielstand"],
      ["Runde", match.round],
      ["Court", match.detail],
      ["Turnier", match.tournament],
    ].filter((row) => row[1]);

    return `
      <div class="details">
        <div class="players">
          ${this._renderPlayer(left)}
          <span>vs.</span>
          ${this._renderPlayer(right)}
        </div>
        ${this._renderSets(competitors)}
        <dl>
          ${rows.map(([label, value]) => `<div><dt>${this._escape(label)}</dt><dd>${this._escape(value)}</dd></div>`).join("")}
        </dl>
        ${url ? `<a class="external" href="${this._escape(url)}" target="_blank" rel="noreferrer"><ha-icon icon="mdi:open-in-new"></ha-icon><span>Match bei ESPN</span></a>` : ""}
      </div>
    `;
  }

  _renderPlayer(player) {
    const name = player.name || player.short_name || "TBD";
    const score = player.score ?? "";
    return `
      <div class="player ${player.winner ? "winner" : ""}">
        <strong>${this._escape(name)}</strong>
        ${score !== "" ? `<small>${this._escape(score)}</small>` : ""}
      </div>
    `;
  }

  _renderSets(competitors) {
    if (competitors.length < 2) {
      return "";
    }

    const leftSets = Array.isArray(competitors[0].sets) ? competitors[0].sets : [];
    const rightSets = Array.isArray(competitors[1].sets) ? competitors[1].sets : [];
    const count = Math.max(leftSets.length, rightSets.length);
    if (!count) {
      return "";
    }

    const headings = Array.from({ length: count }, (_, index) => `<th>S${index + 1}</th>`).join("");
    const left = Array.from({ length: count }, (_, index) => `<td>${this._escape(leftSets[index] ?? "")}</td>`).join("");
    const right = Array.from({ length: count }, (_, index) => `<td>${this._escape(rightSets[index] ?? "")}</td>`).join("");

    return `
      <table class="sets">
        <thead><tr><th></th>${headings}</tr></thead>
        <tbody>
          <tr><th>${this._escape(competitors[0].short_name || competitors[0].name || "1")}</th>${left}</tr>
          <tr><th>${this._escape(competitors[1].short_name || competitors[1].name || "2")}</th>${right}</tr>
        </tbody>
      </table>
    `;
  }

  _matchStatus(match) {
    if (match.status) {
      return match.status;
    }
    if (match.state === "in") {
      return "Live";
    }
    if (match.state === "post") {
      return "Beendet";
    }
    return "Geplant";
  }

  _score(match) {
    if (match.current_score || match.score) {
      return match.current_score || match.score;
    }
    const competitors = Array.isArray(match.competitors) ? match.competitors : [];
    if (competitors.length >= 2 && competitors[0].score !== undefined && competitors[1].score !== undefined) {
      return `${competitors[0].score}:${competitors[1].score}`;
    }
    return "";
  }

  _dateRange(start, end) {
    if (!start && !end) {
      return "";
    }
    if (!end || start === end) {
      return this._formatDate(start);
    }
    return `${this._formatDate(start)} - ${this._formatDate(end)}`;
  }

  _formatDateTime(value) {
    if (!value) {
      return "Noch nicht terminiert";
    }
    return `${this._formatDate(value)}, ${this._formatTime(value)}`;
  }

  _formatDate(value) {
    const date = this._parseDate(value);
    if (!date) {
      return "";
    }
    return new Intl.DateTimeFormat(this._locale(), {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    }).format(date);
  }

  _formatTime(value) {
    const date = this._parseDate(value);
    if (!date) {
      return "TBA";
    }
    return new Intl.DateTimeFormat(this._locale(), {
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  }

  _parseDate(value) {
    if (!value) {
      return undefined;
    }
    const parsed = /^\d{4}-\d{2}-\d{2}$/.test(value)
      ? new Date(`${value}T12:00:00`)
      : new Date(value);
    return Number.isNaN(parsed.getTime()) ? undefined : parsed;
  }

  _locale() {
    return this.config.locale || this._hass.locale?.language || this._hass.language || navigator.language || "de-DE";
  }

  _safeUrl(value) {
    if (!value) {
      return "";
    }
    try {
      const url = new URL(value, window.location.origin);
      if (url.protocol === "http:" || url.protocol === "https:") {
        return url.href;
      }
    } catch (_err) {
      return "";
    }
    return "";
  }

  _escape(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  _styles() {
    return `
      <style>
        :host {
          display: block;
          letter-spacing: 0;
        }

        .tgs {
          --tgs-green: #0f7b5f;
          --tgs-clay: #bd5b3f;
          --tgs-ink: var(--primary-text-color);
          --tgs-muted: var(--secondary-text-color);
          --tgs-line: var(--divider-color);
          --tgs-soft: color-mix(in srgb, var(--card-background-color) 82%, var(--tgs-green) 18%);
          background: var(--card-background-color);
          background:
            linear-gradient(140deg, var(--tgs-soft), var(--card-background-color) 42%, color-mix(in srgb, var(--card-background-color) 88%, var(--tgs-clay) 12%));
          border-radius: var(--ha-card-border-radius, 8px);
          color: var(--tgs-ink);
          overflow: hidden;
          padding: 16px;
        }

        .hero {
          align-items: flex-start;
          border-bottom: 1px solid var(--tgs-line);
          display: flex;
          gap: 12px;
          justify-content: space-between;
          padding-bottom: 14px;
        }

        .eyebrow {
          color: var(--tgs-clay);
          font-size: 0.78rem;
          font-weight: 700;
          letter-spacing: 0;
          text-transform: uppercase;
        }

        h2,
        h3,
        p {
          margin: 0;
        }

        h2 {
          font-size: 1.55rem;
          line-height: 1.12;
          margin-top: 3px;
        }

        .meta,
        .next,
        .match-meta,
        .empty,
        .more {
          color: var(--tgs-muted);
        }

        .meta,
        .next {
          font-size: 0.92rem;
          line-height: 1.35;
          margin-top: 6px;
        }

        .hero-link,
        .external {
          align-items: center;
          color: var(--tgs-green);
          display: inline-flex;
          gap: 6px;
          text-decoration: none;
        }

        .hero-link {
          border: 1px solid var(--tgs-line);
          border-radius: 8px;
          flex: 0 0 auto;
          height: 38px;
          justify-content: center;
          width: 38px;
        }

        .stats {
          display: grid;
          gap: 8px;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          margin: 14px 0 16px;
        }

        .stat {
          align-items: center;
          border: 1px solid var(--tgs-line);
          border-radius: 8px;
          display: grid;
          gap: 2px 8px;
          grid-template-columns: auto 1fr;
          min-height: 50px;
          padding: 8px 10px;
        }

        .stat ha-icon {
          color: var(--tgs-green);
          grid-row: span 2;
          width: 20px;
        }

        .stat span {
          font-size: 1.12rem;
          font-weight: 800;
          line-height: 1;
        }

        .stat small {
          color: var(--tgs-muted);
          font-size: 0.75rem;
          line-height: 1.1;
        }

        .section + .section {
          margin-top: 16px;
        }

        .section-head {
          align-items: center;
          display: flex;
          justify-content: space-between;
          margin-bottom: 8px;
        }

        h3 {
          font-size: 1rem;
          line-height: 1.2;
        }

        .section-head span {
          background: color-mix(in srgb, var(--tgs-green) 12%, transparent);
          border-radius: 999px;
          color: var(--tgs-green);
          font-size: 0.78rem;
          font-weight: 700;
          min-width: 24px;
          padding: 3px 8px;
          text-align: center;
        }

        .match {
          border: 1px solid var(--tgs-line);
          border-radius: 8px;
          overflow: hidden;
        }

        .match + .match {
          margin-top: 7px;
        }

        .match-row {
          align-items: center;
          background: color-mix(in srgb, var(--card-background-color) 72%, transparent);
          border: 0;
          color: var(--tgs-ink);
          cursor: pointer;
          display: grid;
          font: inherit;
          gap: 10px;
          grid-template-columns: minmax(64px, auto) minmax(0, 1fr) minmax(74px, auto);
          min-height: 58px;
          padding: 9px 10px;
          text-align: left;
          width: 100%;
        }

        .match-row:hover,
        .match-row:focus-visible {
          background: color-mix(in srgb, var(--tgs-green) 10%, var(--card-background-color));
          outline: none;
        }

        .time {
          font-variant-numeric: tabular-nums;
        }

        .time strong,
        .time small,
        .match-copy,
        .match-title,
        .match-meta {
          display: block;
          min-width: 0;
        }

        .time strong {
          font-size: 0.95rem;
          line-height: 1.2;
        }

        .time small,
        .match-meta {
          color: var(--tgs-muted);
          font-size: 0.76rem;
          line-height: 1.3;
        }

        .match-title {
          font-weight: 750;
          line-height: 1.25;
          overflow-wrap: anywhere;
        }

        .match-meta span + span::before {
          content: " | ";
        }

        .score {
          align-items: center;
          background: color-mix(in srgb, var(--tgs-clay) 10%, transparent);
          border-radius: 8px;
          color: var(--tgs-ink);
          display: inline-flex;
          font-size: 0.86rem;
          font-weight: 800;
          gap: 6px;
          justify-content: center;
          min-height: 30px;
          min-width: 64px;
          padding: 4px 8px;
          text-align: center;
        }

        .score i {
          background: #d8342a;
          border-radius: 50%;
          display: inline-block;
          height: 7px;
          width: 7px;
        }

        .details {
          background: color-mix(in srgb, var(--card-background-color) 88%, var(--tgs-green) 12%);
          border-top: 1px solid var(--tgs-line);
          padding: 12px;
        }

        .players {
          align-items: stretch;
          display: grid;
          gap: 8px;
          grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
        }

        .players > span {
          align-self: center;
          color: var(--tgs-muted);
          font-size: 0.78rem;
          font-weight: 700;
        }

        .player {
          border: 1px solid var(--tgs-line);
          border-radius: 8px;
          min-width: 0;
          padding: 8px;
        }

        .player.winner {
          border-color: var(--tgs-green);
        }

        .player strong,
        .player small {
          display: block;
          overflow-wrap: anywhere;
        }

        .player small {
          color: var(--tgs-muted);
          margin-top: 3px;
        }

        .sets {
          border-collapse: collapse;
          font-size: 0.82rem;
          margin-top: 10px;
          table-layout: fixed;
          width: 100%;
        }

        .sets th,
        .sets td {
          border-bottom: 1px solid var(--tgs-line);
          padding: 5px;
          text-align: center;
        }

        .sets th:first-child {
          text-align: left;
          width: 34%;
        }

        dl {
          display: grid;
          gap: 6px;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          margin: 10px 0 0;
        }

        dl div {
          min-width: 0;
        }

        dt {
          color: var(--tgs-muted);
          font-size: 0.72rem;
        }

        dd {
          font-size: 0.88rem;
          margin: 2px 0 0;
          overflow-wrap: anywhere;
        }

        .external {
          font-size: 0.88rem;
          font-weight: 700;
          margin-top: 10px;
        }

        .empty,
        .more {
          border: 1px dashed var(--tgs-line);
          border-radius: 8px;
          font-size: 0.88rem;
          padding: 10px;
        }

        .more {
          margin-top: 7px;
        }

        @media (max-width: 520px) {
          .tgs {
            padding: 12px;
          }

          .hero {
            gap: 8px;
          }

          h2 {
            font-size: 1.35rem;
          }

          .stats {
            grid-template-columns: 1fr;
          }

          .match-row {
            grid-template-columns: minmax(58px, auto) minmax(0, 1fr);
          }

          .score {
            grid-column: 1 / -1;
            justify-content: flex-start;
          }

          .players,
          dl {
            grid-template-columns: 1fr;
          }

          .players > span {
            display: none;
          }
        }
      </style>
    `;
  }
}

if (!customElements.get("tennis-grand-slam-card")) {
  customElements.define("tennis-grand-slam-card", TennisGrandSlamCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "tennis-grand-slam-card")) {
  window.customCards.push({
    type: "tennis-grand-slam-card",
    name: "Tennis Grand Slam Card",
    description: "Grand Slam status, today matches, live scores and match details.",
  });
}
