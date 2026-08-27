/* =========================================================================
 * === alex-scene-studio-panel =============================================
 * Editeur de plan de piece (contour polygonal libre, trace au clic) et
 * positionnement des lumieres a l'interieur. Phase 1 : dessiner/sauvegarder/
 * charger des pieces -- l'algorithme d'harmonie et l'application aux
 * vraies lumieres viendront dans une phase ulterieure. Rien n'est envoye a
 * aucune lumiere depuis cet ecran pour l'instant.
 * ========================================================================= */

function escapeHtml(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[c]));
}

// Point-dans-polygone par comptage d'intersections (ray casting) -- fonctionne
// pour n'importe quel contour simple (convexe ou non, formes en L/T/U
// comprises), teste avec ce cas precis avant integration.
function pointInPolygon(point, polygon) {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i].x, yi = polygon[i].y;
    const xj = polygon[j].x, yj = polygon[j].y;
    const intersect =
      yi > point.y !== yj > point.y &&
      point.x < ((xj - xi) * (point.y - yi)) / (yj - yi) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}

function distance(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

const CLOSE_THRESHOLD = 15; // unites SVG, distance sous laquelle un clic pres du premier point ferme le contour
const VIEWBOX_W = 800;
const VIEWBOX_H = 500;
const GRID_SIZE = 20; // unites SVG entre deux lignes de la grille -- meme pas utilise pour l'accroche des points de mur

function snapToGrid(v) {
  return Math.round(v / GRID_SIZE) * GRID_SIZE;
}

const MOUNT_TYPE_LABELS = { ceiling: "Plafond", wall: "Mur", desk: "Bureau" };
const MOUNT_TYPE_ICONS = { ceiling: "\u2B24", wall: "\u25A0", desk: "\u25B2" }; // cercle / carre / triangle plein, distinction visuelle rapide sans dependre d'icones externes

class AlexSceneStudioPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._built = false;
    this._rooms = [];
    this._loading = false;
    this._error = null;

    // Piece en cours d'edition (pas encore forcement sauvegardee).
    this._editingRoomId = null; // null = nouvelle piece
    this._roomName = "";
    this._points = []; // contour, ferme des que _closed = true
    this._closed = false;
    this._lights = []; // {entity_id, x, y, mount_type, height, direction}

    // Selections courantes pour le placement de la prochaine lumiere.
    this._pendingEntity = "";
    this._pendingMountType = "ceiling";
    this._pendingHeight = 2.2; // metres, valeur de depart raisonnable (hauteur sous plafond courante)
    this._pendingDirection = "direct";

    // Glisser-depose : point de mur ou lumiere en cours de deplacement.
    // { kind: "point"|"light", index: N, startX, startY } ou null.
    this._dragging = null;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._built && this.isConnected) {
      this._renderShell();
      this._built = true;
      this._loadRooms();
    }
  }

  set panel(panel) {
    this._panelConfig = panel && panel.config;
  }

  connectedCallback() {
    if (this._hass && !this._built) {
      this._renderShell();
      this._built = true;
      this._loadRooms();
    }
  }

  async _loadRooms() {
    this._loading = true;
    this._error = null;
    this._renderRoomList();
    try {
      const result = await this._hass.callWS({ type: "alex_scene_studio/get_rooms" });
      this._rooms = (result && result.rooms) || [];
    } catch (err) {
      this._error = (err && err.message) || String(err);
      this._rooms = [];
    }
    this._loading = false;
    this._renderRoomList();
  }

  _resetEditor() {
    this._editingRoomId = null;
    this._roomName = "";
    this._points = [];
    this._closed = false;
    this._lights = [];
    this._pendingEntity = "";
    this._pendingMountType = "ceiling";
    this._pendingHeight = 2.2;
    this._pendingDirection = "direct";
    this._dragging = null;
  }

  _loadRoomIntoEditor(room) {
    this._editingRoomId = room.id;
    this._roomName = room.name;
    this._points = room.points.map((p) => ({ x: p.x, y: p.y }));
    this._closed = this._points.length >= 3;
    // height/direction : repli sur des valeurs par defaut pour les pieces
    // enregistrees avant l'ajout de ces deux champs.
    this._lights = room.lights.map((l) => ({
      height: 2.2,
      direction: "direct",
      ...l,
    }));
    this._syncEditorInputs();
    this._renderCanvas();
    this._renderLightsList();
    this._renderRoomList();
  }

  _syncEditorInputs() {
    const nameInput = this.shadowRoot.querySelector("#room-name");
    if (nameInput) nameInput.value = this._roomName;
  }

  // -----------------------------------------------------------------------
  // Coquille statique
  // -----------------------------------------------------------------------
  _renderShell() {
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block; height: 100%; overflow: hidden;
          background: var(--primary-background-color, #111);
          color: var(--primary-text-color, #fff);
          font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
          box-sizing: border-box;
        }
        * { box-sizing: border-box; }
        .header {
          display: flex; align-items: center; gap: 12px; padding: 16px 24px;
          background: var(--app-header-background-color, var(--primary-color, #03a9f4));
        }
        .header button.menu-btn {
          display: none; width: 40px; height: 40px; border-radius: 8px; border: none;
          background: transparent; color: white; cursor: pointer;
          align-items: center; justify-content: center; flex-shrink: 0;
        }
        .header button.menu-btn svg { width: 24px; height: 24px; fill: currentColor; }
        @media (max-width: 870px) { .header button.menu-btn { display: flex; } }
        .header h1 { margin: 0; font-size: 20px; font-weight: 500; color: white; flex: 1; }
        .layout { display: flex; height: calc(100% - 64px); }
        .sidebar {
          width: 300px; flex: 0 0 300px; overflow-y: auto;
          border-right: 1px solid var(--divider-color, #333); padding: 12px;
        }
        .content { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 16px; }
        .card {
          background: var(--card-background-color, #1e1e1e); border-radius: 16px; padding: 16px;
        }
        .card h2 { margin: 0 0 10px; font-size: 14px; font-weight: 600; }
        .room-row {
          display: flex; align-items: center; gap: 8px; padding: 8px 10px;
          border-radius: 8px; cursor: pointer; margin-bottom: 4px; font-size: 13px;
        }
        .room-row:hover { background: rgba(255,255,255,.06); }
        .room-row.selected { background: rgba(var(--rgb-primary-color,3,169,244),.18); }
        .room-row .del-btn { margin-left: auto; opacity: .6; cursor: pointer; }
        .room-row .del-btn:hover { opacity: 1; }
        .btn {
          padding: 9px 16px; border-radius: 10px; border: none; cursor: pointer;
          font-size: 13px; font-weight: 600;
        }
        .btn-primary { background: var(--primary-color, #03a9f4); color: white; }
        .btn-outline { background: transparent; color: var(--secondary-text-color); border: 1px solid var(--divider-color, #444); }
        .btn:disabled { opacity: .4; cursor: not-allowed; }
        input[type="text"], select {
          padding: 8px 10px; border-radius: 8px; border: 1px solid var(--divider-color, #444);
          background: var(--card-background-color, #1e1e1e); color: var(--primary-text-color, #fff);
          font-size: 13px; width: 100%;
        }
        .row { display: flex; gap: 10px; align-items: center; margin-bottom: 10px; flex-wrap: wrap; }
        .row label { flex: 0 0 100px; font-size: 12px; color: var(--secondary-text-color); }
        .row > *:not(label) { flex: 1; min-width: 120px; }
        #canvas-wrap {
          background: var(--card-background-color, #1e1e1e); border-radius: 16px; padding: 10px;
          border: 1px dashed var(--divider-color, #444);
        }
        svg#plan { width: 100%; height: auto; display: block; cursor: crosshair; touch-action: none; }
        .hint { font-size: 12px; color: var(--secondary-text-color); margin-top: 8px; line-height: 1.4; }
        .empty { font-size: 13px; color: var(--secondary-text-color); padding: 8px 0; }
        .error { color: var(--error-color, #db4437); font-size: 13px; }
        .light-item {
          display: flex; align-items: center; gap: 8px; padding: 6px 8px;
          border: 1px solid var(--divider-color, #333); border-radius: 8px; margin-bottom: 6px; font-size: 12px;
        }
        .light-item .del-btn { margin-left: auto; cursor: pointer; opacity: .6; }
        .light-item .del-btn:hover { opacity: 1; }
        .actions { display: flex; gap: 8px; flex-wrap: wrap; }
      </style>

      <div class="header">
        <button class="menu-btn" id="menu-btn" title="Menu">
          <svg viewBox="0 0 24 24"><path d="M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z"/></svg>
        </button>
        <h1>Alex Scene Studio</h1>
        <button class="btn btn-outline" id="new-room-btn">+ Nouvelle pièce</button>
      </div>

      <div class="layout">
        <div class="sidebar">
          <h2 style="font-size:13px;margin:4px 0 10px;color:var(--secondary-text-color);">Pièces enregistrées</h2>
          <div id="room-list"></div>
        </div>

        <div class="content">
          <div class="card">
            <h2>Contour de la pièce</h2>
            <div class="row">
              <label>Nom</label>
              <input type="text" id="room-name" placeholder="ex. Bureau" />
            </div>
            <div id="canvas-wrap">
              <svg id="plan" viewBox="0 0 ${VIEWBOX_W} ${VIEWBOX_H}" xmlns="http://www.w3.org/2000/svg"></svg>
            </div>
            <div class="hint" id="draw-hint">
              Clique dans le plan pour placer les coins du contour. Clique près du premier point pour refermer.
            </div>
            <div class="actions" style="margin-top:10px;">
              <button class="btn btn-outline" id="undo-point-btn">Annuler le dernier point</button>
              <button class="btn btn-outline" id="reset-outline-btn">Recommencer le contour</button>
            </div>
          </div>

          <div class="card" id="lights-card" style="display:none;">
            <h2>Positionner les lumières</h2>
            <div class="row">
              <label>Lumière</label>
              <select id="entity-select"></select>
            </div>
            <div class="row">
              <label>Type</label>
              <select id="mount-select">
                <option value="ceiling">Plafond</option>
                <option value="wall">Mur</option>
                <option value="desk">Bureau</option>
              </select>
            </div>
            <div class="row">
              <label>Hauteur (m)</label>
              <input type="number" id="height-input" min="0" max="10" step="0.1" value="2.2" />
            </div>
            <div class="row">
              <label>Direction</label>
              <select id="direction-select">
                <option value="direct">Direct</option>
                <option value="indirect">Indirect</option>
              </select>
            </div>
            <div class="hint">
              Choisis la lumière et ses réglages ci-dessus, puis clique dans le contour pour la placer.
              Une fois placée, glisse-la directement dans le plan pour la repositionner.
            </div>
            <div id="lights-list" style="margin-top:12px;"></div>
          </div>

          <div class="actions">
            <button class="btn btn-primary" id="save-room-btn">Enregistrer la pièce</button>
          </div>
        </div>
      </div>
    `;

    this.shadowRoot.querySelector("#menu-btn").addEventListener("click", () => {
      this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true }));
    });
    this.shadowRoot.querySelector("#new-room-btn").addEventListener("click", () => {
      this._resetEditor();
      this._syncEditorInputs();
      this._renderCanvas();
      this._renderLightsList();
      this._renderRoomList();
    });
    this.shadowRoot.querySelector("#room-name").addEventListener("input", (ev) => {
      this._roomName = ev.target.value;
    });
    this.shadowRoot.querySelector("#undo-point-btn").addEventListener("click", () => {
      if (this._closed || this._points.length === 0) return;
      this._points.pop();
      this._renderCanvas();
    });
    this.shadowRoot.querySelector("#reset-outline-btn").addEventListener("click", () => {
      this._points = [];
      this._closed = false;
      this._lights = [];
      this._renderCanvas();
      this._renderLightsList();
    });
    this.shadowRoot.querySelector("#entity-select").addEventListener("change", (ev) => {
      this._pendingEntity = ev.target.value;
    });
    this.shadowRoot.querySelector("#mount-select").addEventListener("change", (ev) => {
      this._pendingMountType = ev.target.value;
    });
    this.shadowRoot.querySelector("#height-input").addEventListener("input", (ev) => {
      const v = parseFloat(ev.target.value);
      this._pendingHeight = Number.isFinite(v) ? v : 2.2;
    });
    this.shadowRoot.querySelector("#direction-select").addEventListener("change", (ev) => {
      this._pendingDirection = ev.target.value;
    });
    this.shadowRoot.querySelector("#save-room-btn").addEventListener("click", () => this._saveRoom());

    const svg = this.shadowRoot.querySelector("#plan");
    svg.addEventListener("click", (ev) => this._onCanvasClick(ev));
    svg.addEventListener("pointermove", (ev) => this._onCanvasPointerMove(ev));
    svg.addEventListener("pointerup", () => this._onCanvasPointerUp());
    svg.addEventListener("pointerleave", () => this._onCanvasPointerUp());

    this._populateEntitySelect();
    this._renderCanvas();
  }

  _populateEntitySelect() {
    const sel = this.shadowRoot.querySelector("#entity-select");
    if (!sel || !this._hass) return;
    const lights = Object.keys(this._hass.states)
      .filter((id) => id.startsWith("light."))
      .sort();
    sel.innerHTML = lights
      .map((id) => {
        const name = (this._hass.states[id].attributes && this._hass.states[id].attributes.friendly_name) || id;
        return `<option value="${escapeHtml(id)}">${escapeHtml(name)}</option>`;
      })
      .join("");
    if (lights.length && !this._pendingEntity) {
      this._pendingEntity = lights[0];
    }
    sel.value = this._pendingEntity;
  }

  // -----------------------------------------------------------------------
  // Canvas SVG : conversion coordonnees ecran -> espace utilisateur SVG,
  // necessaire car le SVG est redimensionne par CSS (width:100%) tout en
  // gardant un viewBox fixe -- un simple clientX/clientY ne suffit pas.
  // -----------------------------------------------------------------------
  _svgPointFromEvent(ev) {
    const svg = this.shadowRoot.querySelector("#plan");
    const pt = svg.createSVGPoint();
    pt.x = ev.clientX;
    pt.y = ev.clientY;
    const ctm = svg.getScreenCTM();
    if (!ctm) return { x: 0, y: 0 };
    const transformed = pt.matrixTransform(ctm.inverse());
    return { x: transformed.x, y: transformed.y };
  }

  _onCanvasClick(ev) {
    // Un clic qui suit immediatement un glisser-depose ne doit pas EN PLUS
    // ajouter un point ou placer une lumiere -- sans ce garde-fou, relacher
    // le glissement declenche aussi un "click" fantome au meme endroit.
    if (this._justDragged) {
      this._justDragged = false;
      return;
    }

    const p = this._svgPointFromEvent(ev);

    if (!this._closed) {
      // Mode dessin du contour : clic pres du premier point -> ferme.
      if (this._points.length >= 3 && distance(p, this._points[0]) <= CLOSE_THRESHOLD) {
        this._closed = true;
        this._renderCanvas();
        this._renderLightsList();
        return;
      }
      this._points.push({ x: snapToGrid(p.x), y: snapToGrid(p.y) });
      this._renderCanvas();
      return;
    }

    // Mode placement des lumieres : seulement a l'interieur du contour.
    if (!this._pendingEntity) return;
    if (!pointInPolygon(p, this._points)) return;
    this._lights.push({
      entity_id: this._pendingEntity,
      x: p.x,
      y: p.y,
      mount_type: this._pendingMountType,
      height: this._pendingHeight,
      direction: this._pendingDirection,
    });
    this._renderCanvas();
    this._renderLightsList();
  }

  // -----------------------------------------------------------------------
  // Glisser-depose des points de mur et des lumieres deja places. pointerdown
  // demarre sur le marqueur lui-meme (attache apres chaque rendu, voir
  // _renderCanvas) ; pointermove/pointerup sont sur le SVG entier pour ne
  // pas perdre le geste si le curseur sort brievement du marqueur.
  // -----------------------------------------------------------------------
  _onMarkerPointerDown(ev, kind, index) {
    ev.stopPropagation();
    const source = kind === "point" ? this._points[index] : this._lights[index];
    this._dragging = { kind, index, startX: source.x, startY: source.y, moved: false };
  }

  _onCanvasPointerMove(ev) {
    if (!this._dragging) return;
    const p = this._svgPointFromEvent(ev);
    this._dragging.moved = true;
    if (this._dragging.kind === "point") {
      this._points[this._dragging.index] = { x: snapToGrid(p.x), y: snapToGrid(p.y) };
    } else {
      this._lights[this._dragging.index].x = p.x;
      this._lights[this._dragging.index].y = p.y;
    }
    this._renderCanvas();
  }

  _onCanvasPointerUp() {
    if (!this._dragging) return;
    const { kind, index, startX, startY, moved } = this._dragging;
    if (kind === "light" && moved) {
      // Une lumiere deposee hors du contour revient a sa position de depart
      // plutot que d'accepter une position invalide.
      const l = this._lights[index];
      if (!pointInPolygon(l, this._points)) {
        l.x = startX;
        l.y = startY;
      }
    }
    this._justDragged = moved;
    this._dragging = null;
    this._renderCanvas();
    this._renderLightsList();
  }

  _renderCanvas() {
    const svg = this.shadowRoot.querySelector("#plan");
    if (!svg) return;

    const lightsCard = this.shadowRoot.querySelector("#lights-card");
    const drawHint = this.shadowRoot.querySelector("#draw-hint");
    if (lightsCard) lightsCard.style.display = this._closed ? "block" : "none";
    if (drawHint) {
      drawHint.textContent = this._closed
        ? "Contour terminé. Glisse un point ou une lumière pour la repositionner ; « Recommencer le contour » pour tout retracer."
        : "Clique dans le plan pour placer les coins du contour (accroché à la grille). Clique près du premier point pour refermer.";
    }

    const pointsAttr = this._points.map((p) => `${p.x},${p.y}`).join(" ");
    const shapeEl = this._points.length
      ? this._closed
        ? `<polygon points="${pointsAttr}" fill="rgba(3,169,244,0.12)" stroke="var(--primary-color,#03a9f4)" stroke-width="2" />`
        : `<polyline points="${pointsAttr}" fill="none" stroke="var(--primary-color,#03a9f4)" stroke-width="2" />`
      : "";

    const cornerDots = this._points
      .map(
        (p, i) =>
          `<circle class="wall-point" data-point-index="${i}" cx="${p.x}" cy="${p.y}" r="7"
             fill="${i === 0 ? "#f4a935" : "#03a9f4"}" stroke="white" stroke-width="1.5"
             style="cursor:grab;" />`
      )
      .join("");

    const lightMarkers = this._lights
      .map((l, i) => {
        const color = l.mount_type === "ceiling" ? "#f4a935" : l.mount_type === "wall" ? "#4caf50" : "#e91e63";
        return `
          <g class="light-marker" data-light-index="${i}" style="cursor:grab;">
            <circle cx="${l.x}" cy="${l.y}" r="10" fill="${color}" stroke="white" stroke-width="1.5" opacity="0.9" />
            <text x="${l.x}" y="${l.y + 3}" font-size="9" text-anchor="middle" fill="white" style="pointer-events:none;">${MOUNT_TYPE_ICONS[l.mount_type] || ""}</text>
          </g>`;
      })
      .join("");

    // Grille de fond façon papier quadrille -- aide purement visuelle, les
    // points de mur s'accrochent en plus reellement a ce pas (snapToGrid).
    svg.innerHTML = `
      <defs>
        <pattern id="grid" width="${GRID_SIZE}" height="${GRID_SIZE}" patternUnits="userSpaceOnUse">
          <path d="M ${GRID_SIZE} 0 L 0 0 0 ${GRID_SIZE}" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="1" />
        </pattern>
      </defs>
      <rect x="0" y="0" width="${VIEWBOX_W}" height="${VIEWBOX_H}" fill="rgba(255,255,255,0.02)" />
      <rect x="0" y="0" width="${VIEWBOX_W}" height="${VIEWBOX_H}" fill="url(#grid)" />
      ${shapeEl}
      ${cornerDots}
      ${lightMarkers}
    `;

    svg.querySelectorAll(".wall-point").forEach((el) => {
      el.addEventListener("pointerdown", (ev) =>
        this._onMarkerPointerDown(ev, "point", parseInt(el.getAttribute("data-point-index"), 10))
      );
    });
    svg.querySelectorAll(".light-marker").forEach((el) => {
      el.addEventListener("pointerdown", (ev) =>
        this._onMarkerPointerDown(ev, "light", parseInt(el.getAttribute("data-light-index"), 10))
      );
    });
  }

  _renderLightsList() {
    const list = this.shadowRoot.querySelector("#lights-list");
    if (!list) return;
    if (!this._lights.length) {
      list.innerHTML = `<div class="empty">Aucune lumière placée pour l'instant.</div>`;
      return;
    }
    list.innerHTML = this._lights
      .map((l, i) => {
        const st = this._hass.states[l.entity_id];
        const name = (st && st.attributes && st.attributes.friendly_name) || l.entity_id;
        return `
          <div class="light-item" data-index="${i}">
            <span>${MOUNT_TYPE_ICONS[l.mount_type] || ""}</span>
            <span style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escapeHtml(name)}</span>
            <span style="color:var(--secondary-text-color);">(${MOUNT_TYPE_LABELS[l.mount_type] || l.mount_type})</span>
            <input type="number" class="light-height" data-index="${i}" min="0" max="10" step="0.1"
                   value="${l.height != null ? l.height : 2.2}" style="width:56px;flex:0 0 56px;" title="Hauteur (m)" />
            <select class="light-direction" data-index="${i}" style="flex:0 0 90px;" title="Direction">
              <option value="direct" ${l.direction !== "indirect" ? "selected" : ""}>Direct</option>
              <option value="indirect" ${l.direction === "indirect" ? "selected" : ""}>Indirect</option>
            </select>
            <span class="del-btn" data-del-index="${i}">✕</span>
          </div>`;
      })
      .join("");
    list.querySelectorAll(".light-height").forEach((el) => {
      el.addEventListener("input", (ev) => {
        const idx = parseInt(el.getAttribute("data-index"), 10);
        const v = parseFloat(ev.target.value);
        this._lights[idx].height = Number.isFinite(v) ? v : 2.2;
      });
    });
    list.querySelectorAll(".light-direction").forEach((el) => {
      el.addEventListener("change", (ev) => {
        const idx = parseInt(el.getAttribute("data-index"), 10);
        this._lights[idx].direction = ev.target.value;
      });
    });
    list.querySelectorAll("[data-del-index]").forEach((el) => {
      el.addEventListener("click", () => {
        const idx = parseInt(el.getAttribute("data-del-index"), 10);
        this._lights.splice(idx, 1);
        this._renderCanvas();
        this._renderLightsList();
      });
    });
  }

  _renderRoomList() {
    const list = this.shadowRoot.querySelector("#room-list");
    if (!list) return;
    if (this._loading) {
      list.innerHTML = `<div class="empty">Chargement…</div>`;
      return;
    }
    if (this._error) {
      list.innerHTML = `<div class="error">Erreur : ${escapeHtml(this._error)}</div>`;
      return;
    }
    if (!this._rooms.length) {
      list.innerHTML = `<div class="empty">Aucune pièce enregistrée.</div>`;
      return;
    }
    list.innerHTML = this._rooms
      .map(
        (r) => `
          <div class="room-row ${r.id === this._editingRoomId ? "selected" : ""}" data-room-id="${escapeHtml(r.id)}">
            <span>${escapeHtml(r.name)}</span>
            <span class="del-btn" data-del-room="${escapeHtml(r.id)}">✕</span>
          </div>`
      )
      .join("");
    list.querySelectorAll(".room-row").forEach((row) => {
      row.addEventListener("click", (ev) => {
        if (ev.target.hasAttribute("data-del-room")) return;
        const room = this._rooms.find((r) => r.id === row.getAttribute("data-room-id"));
        if (room) this._loadRoomIntoEditor(room);
      });
    });
    list.querySelectorAll("[data-del-room]").forEach((el) => {
      el.addEventListener("click", async (ev) => {
        ev.stopPropagation();
        const roomId = el.getAttribute("data-del-room");
        await this._hass.callWS({ type: "alex_scene_studio/delete_room", room_id: roomId });
        if (this._editingRoomId === roomId) {
          this._resetEditor();
          this._syncEditorInputs();
          this._renderCanvas();
          this._renderLightsList();
        }
        this._loadRooms();
      });
    });
  }

  async _saveRoom() {
    if (!this._roomName.trim()) {
      this.shadowRoot.querySelector("#room-name").focus();
      return;
    }
    if (this._points.length < 3 || !this._closed) {
      alert("Termine d'abord le contour de la pièce (au moins 3 points, refermé).");
      return;
    }
    const payload = {
      type: "alex_scene_studio/save_room",
      name: this._roomName.trim(),
      points: this._points.map((p) => ({ x: p.x, y: p.y })),
      lights: this._lights.map((l) => ({ ...l })),
    };
    if (this._editingRoomId) payload.room_id = this._editingRoomId;

    const result = await this._hass.callWS(payload);
    if (result && result.room) {
      this._editingRoomId = result.room.id;
    }
    await this._loadRooms();
  }
}

customElements.define("alex-scene-studio-panel", AlexSceneStudioPanel);
