"""L'integration Alex Scene Studio.

Phase 1 : modele de donnees + stockage des pieces (contour polygonal +
lumieres positionnees).
Phase 2 (celle-ci) : calcul d'une proposition de scene harmonieuse
(harmony.py) a partir d'une piece, avec lecture EN DIRECT des capacites
reelles de chaque lumiere (jamais mise en cache) ; application aux vraies
lumieres seulement sur demande explicite ; sauvegarde optionnelle en tant
que vraie scene HA (service natif scene.create, snapshot des etats tout
juste appliques -- pas de stockage maison pour ca).

Stockage : Store natif HA (.storage/), une bibliotheque de pieces
{room_id: {name, points, lights}}.
"""
from __future__ import annotations

import logging
import os
import random
import re
import uuid
from dataclasses import asdict, dataclass, field

import voluptuous as vol
from homeassistant.components import panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from . import harmony
from .const import DOMAIN, DIRECTION_TYPES, MOUNT_TYPES, PANEL_ICON, PANEL_TITLE, PANEL_URL_PATH, STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)

# Modes de couleur HA qui impliquent une capacite RGB reelle -- le reste
# (color_temp seul, brightness seule, onoff) n'en fait pas partie.
_COLOR_CAPABLE_MODES = {"hs", "rgb", "rgbw", "rgbww", "xy"}


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

COMPUTE_SCENE_SCHEMA = {
    vol.Required("type"): f"{DOMAIN}/compute_scene",
    vol.Required("lights"): [LIGHT_SCHEMA],
    vol.Required("scheme"): vol.In(["complementary", "analogous", "triadic"]),
    vol.Optional("mood"): vol.In(list(harmony.MOOD_PRESETS)),
    vol.Optional("base_hue"): vol.Coerce(float),
    vol.Optional("saturation"): vol.Coerce(float),
    vol.Optional("brightness"): vol.Coerce(float),
}

SUGGESTION_SCHEMA = {
    vol.Required("entity_id"): str,
    vol.Required("hue"): vol.Coerce(float),
    vol.Required("saturation"): vol.Coerce(float),
    vol.Required("brightness"): vol.Coerce(int),
    # vol.Optional rend la CLE optionnelle (absente autorisee), mais
    # n'autorise pas a elle seule la valeur None quand la cle EST presente --
    # or dataclasses.asdict() inclut toujours color_temp_kelvin, meme a None
    # (lumieres RGB qui n'ont pas besoin d'une conversion en kelvin). Sans
    # vol.Any(None, ...), cette valeur explicitement None se fait rejeter
    # par vol.Coerce(int) des l'aller-retour Appliquer.
    vol.Optional("color_temp_kelvin"): vol.Any(None, vol.Coerce(int)),
}

APPLY_SCENE_SCHEMA = {
    vol.Required("type"): f"{DOMAIN}/apply_scene",
    vol.Required("suggestions"): [SUGGESTION_SCHEMA],
}

SAVE_AS_HA_SCENE_SCHEMA = {
    vol.Required("type"): f"{DOMAIN}/save_as_ha_scene",
    vol.Required("scene_name"): str,
    vol.Required("entity_ids"): [str],
}


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
        websocket_api.async_register_command(hass, websocket_compute_scene)
        websocket_api.async_register_command(hass, websocket_apply_scene)
        websocket_api.async_register_command(hass, websocket_save_as_ha_scene)
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


def _light_capabilities(hass: HomeAssistant, entity_id: str) -> tuple[bool, bool]:
    """Lit EN DIRECT (jamais mis en cache) les capacites reelles d'une
    lumiere -- peuvent changer si l'appareil/son firmware change, donc
    toujours relues au moment du calcul plutot que stockees avec la piece."""
    state = hass.states.get(entity_id)
    if state is None:
        return False, False
    modes = set(state.attributes.get("supported_color_modes") or [])
    return bool(modes & _COLOR_CAPABLE_MODES), "color_temp" in modes


@websocket_api.websocket_command(COMPUTE_SCENE_SCHEMA)
@websocket_api.async_response
async def websocket_compute_scene(hass: HomeAssistant, connection, msg) -> None:
    """Calcule une proposition -- ne touche a AUCUNE lumiere reelle, se
    contente de renvoyer les valeurs suggerees pour apercu/ajustement.
    Prend les lumieres directement dans le message (pas besoin d'avoir deja
    enregistre la piece -- l'utilisateur peut generer un apercu pendant
    qu'il dessine, avant de sauvegarder quoi que ce soit)."""
    light_inputs = []
    for l in msg["lights"]:
        supports_color, supports_color_temp = _light_capabilities(hass, l["entity_id"])
        light_inputs.append(
            harmony.LightInput(
                entity_id=l["entity_id"],
                mount_type=l["mount_type"],
                direction=l.get("direction", "direct"),
                supports_color=supports_color,
                supports_color_temp=supports_color_temp,
            )
        )

    try:
        suggestions = harmony.compute_scene(
            light_inputs,
            scheme=msg["scheme"],
            mood=msg.get("mood"),
            base_hue=msg.get("base_hue"),
            saturation=msg.get("saturation"),
            brightness=msg.get("brightness"),
            rng=random.Random(),
        )
    except ValueError as exc:
        connection.send_error(msg["id"], "invalid_params", str(exc))
        return

    connection.send_result(msg["id"], {"suggestions": [asdict(s) for s in suggestions]})


@websocket_api.websocket_command(APPLY_SCENE_SCHEMA)
@websocket_api.async_response
async def websocket_apply_scene(hass: HomeAssistant, connection, msg) -> None:
    """Envoie les valeurs (potentiellement ajustees par l'utilisateur apres
    apercu) aux vraies lumieres. Jamais appele automatiquement -- seulement
    sur action explicite depuis le panel."""
    for s in msg["suggestions"]:
        data = {"entity_id": s["entity_id"], "brightness": s["brightness"]}
        if s.get("color_temp_kelvin") is not None:
            data["color_temp_kelvin"] = s["color_temp_kelvin"]
        else:
            data["hs_color"] = [s["hue"], s["saturation"]]
        await hass.services.async_call("light", "turn_on", data, blocking=True)
    connection.send_result(msg["id"], {"applied": len(msg["suggestions"])})


@websocket_api.websocket_command(SAVE_AS_HA_SCENE_SCHEMA)
@websocket_api.async_response
async def websocket_save_as_ha_scene(hass: HomeAssistant, connection, msg) -> None:
    """Cree une vraie scene HA (service natif scene.create) a partir des
    etats ACTUELS des lumieres listees -- suppose que apply_scene a deja ete
    appele juste avant, pour que ces etats reflectent bien la proposition
    validee plutot que ce qui etait allume avant."""
    scene_id = re.sub(r"[^a-z0-9]+", "_", msg["scene_name"].lower()).strip("_") or "alex_scene_studio_scene"
    await hass.services.async_call(
        "scene",
        "create",
        {"scene_id": scene_id, "snapshot_entities": msg["entity_ids"]},
        blocking=True,
    )
    connection.send_result(msg["id"], {"scene_entity_id": f"scene.{scene_id}"})


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
