"""L'integration Alex Scene Studio.

Phase 1 : modele de donnees + stockage des pieces (contour polygonal +
lumieres positionnees). L'algorithme d'harmonie et l'application des
suggestions aux vraies lumieres viendront dans une phase ulterieure -- cette
version ne fait que dessiner/sauvegarder/charger des pieces, rien n'est
encore envoye a aucune lumiere.

Stockage : Store natif HA (.storage/), une bibliotheque de pieces
{room_id: {name, points, lights}}.
"""
from __future__ import annotations

import logging
import os
import uuid
from dataclasses import asdict, dataclass, field

import voluptuous as vol
from homeassistant.components import panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, DIRECTION_TYPES, MOUNT_TYPES, PANEL_ICON, PANEL_TITLE, PANEL_URL_PATH, STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)


@dataclass
class LightPosition:
    entity_id: str
    x: float
    y: float
    mount_type: str  # "ceiling" | "wall" | "desk"
    height: float = 2.2  # metres
    direction: str = "direct"  # "direct" | "indirect"


@dataclass
class Room:
    id: str
    name: str
    points: list[dict]  # [{"x": .., "y": ..}, ...] -- contour polygonal, ordre = trace
    lights: list[dict] = field(default_factory=list)  # liste de LightPosition serialisees


POINT_SCHEMA = {vol.Required("x"): vol.Coerce(float), vol.Required("y"): vol.Coerce(float)}

LIGHT_SCHEMA = {
    vol.Required("entity_id"): str,
    vol.Required("x"): vol.Coerce(float),
    vol.Required("y"): vol.Coerce(float),
    vol.Required("mount_type"): vol.In(MOUNT_TYPES),
    vol.Optional("height", default=2.2): vol.Coerce(float),
    vol.Optional("direction", default="direct"): vol.In(DIRECTION_TYPES),
}

SAVE_ROOM_SCHEMA = {
    vol.Required("type"): f"{DOMAIN}/save_room",
    vol.Optional("room_id"): str,  # absent = nouvelle piece
    vol.Required("name"): str,
    vol.Required("points"): [POINT_SCHEMA],
    vol.Optional("lights", default=list): [LIGHT_SCHEMA],
}

DELETE_ROOM_SCHEMA = {vol.Required("type"): f"{DOMAIN}/delete_room", vol.Required("room_id"): str}

GET_ROOMS_SCHEMA = {vol.Required("type"): f"{DOMAIN}/get_rooms"}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Initialise l'integration : stockage + commandes websocket + panel."""
    store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    data = await store.async_load() or {"rooms": {}}

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"store": store, "rooms": data.get("rooms", {})}

    if not hass.data[DOMAIN].get("ws_registered"):
        websocket_api.async_register_command(hass, websocket_get_rooms)
        websocket_api.async_register_command(hass, websocket_save_room)
        websocket_api.async_register_command(hass, websocket_delete_room)
        hass.data[DOMAIN]["ws_registered"] = True

    # L'entry_id courant, pour que les commandes websocket (qui n'ont pas
    # acces a `entry` directement) sachent ou lire/ecrire.
    hass.data[DOMAIN]["active_entry_id"] = entry.entry_id

    await _async_register_panel(hass)
    return True


def _entry_data(hass: HomeAssistant) -> dict:
    entry_id = hass.data[DOMAIN]["active_entry_id"]
    return hass.data[DOMAIN][entry_id]


async def _async_persist(hass: HomeAssistant) -> None:
    entry_data = _entry_data(hass)
    await entry_data["store"].async_save({"rooms": entry_data["rooms"]})


@websocket_api.websocket_command(GET_ROOMS_SCHEMA)
@websocket_api.async_response
async def websocket_get_rooms(hass: HomeAssistant, connection, msg) -> None:
    connection.send_result(msg["id"], {"rooms": list(_entry_data(hass)["rooms"].values())})


@websocket_api.websocket_command(SAVE_ROOM_SCHEMA)
@websocket_api.async_response
async def websocket_save_room(hass: HomeAssistant, connection, msg) -> None:
    """Cree une nouvelle piece (pas de `id` fourni) ou met a jour une piece
    existante (upsert par id, meme principe que Gradient Studio pour ses
    scenes)."""
    rooms = _entry_data(hass)["rooms"]
    room_id = msg.get("room_id") or str(uuid.uuid4())
    room = Room(id=room_id, name=msg["name"], points=msg["points"], lights=msg.get("lights", []))
    rooms[room_id] = asdict(room)
    await _async_persist(hass)
    connection.send_result(msg["id"], {"room": rooms[room_id]})


@websocket_api.websocket_command(DELETE_ROOM_SCHEMA)
@websocket_api.async_response
async def websocket_delete_room(hass: HomeAssistant, connection, msg) -> None:
    rooms = _entry_data(hass)["rooms"]
    removed = rooms.pop(msg["room_id"], None)
    if removed is not None:
        await _async_persist(hass)
    connection.send_result(msg["id"], {"deleted": removed is not None})


async def _async_register_panel(hass: HomeAssistant) -> None:
    """Enregistre le panel dans la barre laterale (une seule fois)."""
    registered_key = f"{DOMAIN}_panel_registered"
    if hass.data.get(registered_key):
        return
    hass.data[registered_key] = True

    panel_dir = os.path.join(os.path.dirname(__file__), "panel")
    panel_static_url = f"/{DOMAIN}_panel"

    await hass.http.async_register_static_paths(
        [StaticPathConfig(panel_static_url, panel_dir, cache_headers=False)]
    )

    await panel_custom.async_register_panel(
        hass,
        webcomponent_name="alex-scene-studio-panel",
        frontend_url_path=PANEL_URL_PATH,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        module_url=f"{panel_static_url}/alex-scene-studio-panel.js",
        embed_iframe=False,
        require_admin=True,
    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True
