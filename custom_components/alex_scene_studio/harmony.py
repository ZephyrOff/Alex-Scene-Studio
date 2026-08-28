"""Algorithme d'harmonie pour Alex Scene Studio (v2).

Reecrit a partir d'un document de conception detaille (fourni par
l'utilisateur) qui distingue explicitement :
  - le ROLE fonctionnel d'une lumiere (principale / accentuation /
    ambiance) -- INDEPENDANT de sa position physique (une lumiere murale
    peut porter un accent ou une ambiance selon l'intention) ;
  - une IMPORTANCE (0-1) propre a chaque lumiere, au sein de son role ;
  - un CONTRASTE de scene (0-1) qui determine si les roles restent proches
    (rendu uniforme, quotidien) ou tres separes (rendu dramatique, soiree) ;
  - une temperature de blanc COHERENTE pour toute la scene (une "famille"
    de kelvin proches, jamais des ecarts extremes sans intention) plutot
    que des conversions teinte->kelvin independantes par lumiere.

Deux principes du document directement encodes ici :
  - une couleur tres saturee doit generalement etre moins lumineuse
    (section 9/22) -- `_saturation_brightness_tradeoff` ;
  - l'indirect supporte generalement mieux des niveaux eleves tout en
    restant doux (section 25) -- l'indirect reduit la SATURATION, pas la
    luminosite (contrairement a la v1 de ce module).

Module volontairement independant de Home Assistant (aucun import hass).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

ROLES = ("primary", "accent", "ambient")
POSITIONS = ("ceiling", "wall", "furniture", "floor")

# Plage de luminosite (0-255) par role, avant application du contraste, de
# l'intensite globale et de l'importance individuelle -- reprend directement
# les fourchettes indicatives de la section 1 du document (60-80% / 30-50% /
# 10-30%), converties sur l'echelle HA.
ROLE_BRIGHTNESS_RANGE = {
    "primary": (153, 204),  # 60-80% de 255
    "accent": (77, 128),  # 30-50%
    "ambient": (26, 77),  # 10-30%
}

# Saturation de reference par role : la principale reste sobre (section 2 :
# "generalement peu saturee"), l'accent porte la couleur dominante
# pleinement, l'ambiance porte la couleur secondaire avec une douceur
# intermediaire.
ROLE_BASE_SATURATION = {"primary": 20, "accent": 75, "ambient": 55}

# Decalage de temperature (kelvin) par role AUTOUR de la temperature de
# base de la scene -- de petits ecarts coherents ("3000K + 2700K +
# eventuellement 2400K", section 8), jamais une conversion independante par
# teinte qui produirait des ecarts extremes.
ROLE_KELVIN_OFFSET = {"primary": 0, "accent": -150, "ambient": -300}

# Un role indirect voit sa saturation reduite (lumiere rebondie plus douce),
# mais PAS sa luminosite -- le document indique explicitement que l'indirect
# supporte generalement mieux des niveaux eleves (section 25), contrairement
# a l'hypothese de la v1 de ce module.
INDIRECT_SATURATION_FACTOR = 0.65

# ---------------------------------------------------------------------------
# Ambiances predefinies -- chacune fixe une teinte de depart, une saturation
# et une intensite globale de reference, un schema chromatique, un niveau de
# contraste (hierarchie plus ou moins marquee) et une temperature de blanc de
# base coherente pour toute la scene.
# ---------------------------------------------------------------------------
MOOD_PRESETS = {
    "energique": {
        "hue_range": (180, 260),
        "saturation": 75,
        "global_intensity": 1.05,
        "scheme": "complementary",
        "contrast": 0.75,
        "white_temperature": 4000,
    },
    "detente": {
        "hue_range": (15, 45),
        "saturation": 55,
        "global_intensity": 0.75,
        "scheme": "analogous",
        "contrast": 0.55,
        "white_temperature": 2700,
    },
    "concentration": {
        "hue_range": (190, 210),
        "saturation": 25,
        "global_intensity": 1.1,
        "scheme": "analogous",
        "contrast": 0.3,
        "white_temperature": 4500,
    },
    "lecture": {
        "hue_range": (35, 50),
        "saturation": 35,
        "global_intensity": 0.95,
        "scheme": "analogous",
        "contrast": 0.4,
        "white_temperature": 3000,
    },
    # Les quatre ambiances suivantes reprennent directement les exemples de
    # la section 20 du document de conception.
    "quotidien": {
        # "lumiere principale dominante, couleurs reduites" -- contraste
        # faible (uniforme), tres peu sature, la hierarchie normale
        # (principale > accent > ambiance) suffit sans avoir besoin d'etre
        # reshapee.
        "hue_range": (190, 210),
        "saturation": 15,
        "global_intensity": 1.0,
        "scheme": "analogous",
        "contrast": 0.25,
        "white_temperature": 4000,
        "role_multiplier": {"primary": 1.0, "accent": 0.8, "ambient": 0.6},
    },
    "cinema": {
        # "fonctionnel tres faible, ambiance presente" -- hierarchie
        # INVERSEE (le role_multiplier fait le travail que le contraste
        # seul ne peut pas faire : contraste ne fait QUE varier
        # l'amplitude, jamais l'ordre des roles).
        "hue_range": (220, 260),
        "saturation": 50,
        "global_intensity": 0.5,
        "scheme": "analogous",
        "contrast": 0.9,
        "white_temperature": 2400,
        "role_multiplier": {"primary": 0.15, "accent": 0.5, "ambient": 1.4},
    },
    "soiree": {
        # "accents et couleurs plus presents" -- schema triadique (plus de
        # couleurs simultanees que les autres ambiances), accent renforce.
        "hue_range": (280, 340),
        "saturation": 80,
        "global_intensity": 0.85,
        "scheme": "triadic",
        "contrast": 0.7,
        "white_temperature": 2700,
        "role_multiplier": {"primary": 0.7, "accent": 1.3, "ambient": 1.1},
    },
    "nuit": {
        # "tres faible intensite, temperatures chaudes" -- intensite
        # globale la plus basse de toutes les ambiances, teinte tres chaude,
        # kelvin de base tres bas.
        "hue_range": (10, 25),
        "saturation": 60,
        "global_intensity": 0.25,
        "scheme": "analogous",
        "contrast": 0.3,
        "white_temperature": 2200,
        "role_multiplier": {"primary": 0.5, "accent": 0.7, "ambient": 1.0},
    },
}


@dataclass
class LightInput:
    """Ce qu'il faut savoir sur une lumiere positionnee pour lui calculer
    une proposition."""

    entity_id: str
    position: str = "ceiling"  # "ceiling" | "wall" | "desk" | "furniture" | "floor" -- determine le role, voir derive_role
    direction: str = "direct"  # "direct" | "indirect" -- determine aussi le role
    importance: float = 0.7  # 0-1
    supports_color: bool = True
    supports_color_temp: bool = False


@dataclass
class LightSuggestion:
    entity_id: str
    hue: float
    saturation: float
    brightness: int
    color_temp_kelvin: int | None = None


# Le role (principale/accentuation/ambiance) se DEDUIT desormais de la
# position physique et de la direction, plutot que d'etre choisi a la main
# -- l'utilisateur n'a plus qu'a decrire OU est la lumiere et comment elle
# eclaire, pas a interpreter lui-meme sa fonction. Table de correspondance :
# plafond/bureau en direct restent fonctionnels (principale) ; un mur en
# direct attire l'attention (accentuation) ; tout ce qui est indirect sert
# l'ambiance (rebondi, jamais la fonction principale de voir).
_ROLE_FROM_POSITION_DIRECTION = {
    ("ceiling", "direct"): "primary",
    ("ceiling", "indirect"): "ambient",
    ("wall", "direct"): "accent",
    ("wall", "indirect"): "ambient",
    ("desk", "direct"): "primary",
    ("desk", "indirect"): "ambient",
    ("furniture", "direct"): "accent",
    ("furniture", "indirect"): "ambient",
    ("floor", "direct"): "accent",
    ("floor", "indirect"): "ambient",
}


def derive_role(position: str, direction: str) -> str:
    """Deduit le role fonctionnel a partir de la position physique et de la
    direction. Repli sur "primary" pour toute combinaison non prevue,
    plutot que d'echouer."""
    return _ROLE_FROM_POSITION_DIRECTION.get((position, direction), "primary")


def _hue_scheme(base_hue: float, scheme: str) -> list[float]:
    base_hue = base_hue % 360
    if scheme == "complementary":
        return [base_hue, (base_hue + 180) % 360]
    if scheme == "triadic":
        return [base_hue, (base_hue + 120) % 360, (base_hue + 240) % 360]
    return [base_hue, (base_hue + 30) % 360, (base_hue - 30) % 360]


def _role_hue(role: str, hue_slots: list[float]) -> float:
    """Principale = teinte de base (tres peu saturee, quasi neutre a
    l'usage) ; accentuation = teinte DOMINANTE pleinement assumee ;
    ambiance = teinte SECONDAIRE derivee du schema (section 10 : dominante +
    eventuelle secondaire, pas une couleur differente par lumiere)."""
    if role == "accent":
        return hue_slots[0]
    if role == "ambient":
        return hue_slots[1 % len(hue_slots)]
    return hue_slots[0]  # primary


def _role_brightness(role: str, contrast: float, global_intensity: float) -> float:
    """A contraste eleve, chaque role exploite pleinement sa propre plage.
    A contraste faible, les trois roles convergent vers une valeur commune
    (moyenne des plages) -- la hierarchie existe toujours un peu, mais son
    amplitude suit l'intention de la scene (section 1 : ce sont des points
    de depart, pas des regles absolues)."""
    lo, hi = ROLE_BRIGHTNESS_RANGE[role]
    role_mid = (lo + hi) / 2
    all_mid = sum((lo2 + hi2) / 2 for lo2, hi2 in ROLE_BRIGHTNESS_RANGE.values()) / len(ROLE_BRIGHTNESS_RANGE)
    value = all_mid + (role_mid - all_mid) * contrast
    return value * global_intensity


def _saturation_brightness_tradeoff(saturation: float, brightness: float) -> float:
    """Une couleur tres saturee doit generalement etre moins lumineuse
    (section 9/22) -- reduit la luminosite jusqu'a 35% a saturation
    maximale, sans jamais l'annuler completement."""
    factor = 1 - (saturation / 100) * 0.35
    return brightness * factor


def compute_scene(
    lights: list[LightInput],
    scheme: str,
    mood: str | None = None,
    base_hue: float | None = None,
    saturation: float | None = None,
    global_intensity: float | None = None,
    contrast: float | None = None,
    white_temperature: float | None = None,
    role_multiplier: dict[str, float] | None = None,
    rng: random.Random | None = None,
) -> list[LightSuggestion]:
    """Calcule une proposition pour chaque lumiere. Soit `mood` (pioche une
    teinte au hasard dans sa plage a chaque appel, les autres parametres
    de scene -- y compris `role_multiplier` -- viennent du preset), soit
    les parametres manuels fournis explicitement (`base_hue` obligatoire
    dans ce cas).

    `role_multiplier` : {role: facteur} applique APRES le calcul normal de
    luminosite par role -- permet a une ambiance de RESHAPER la hierarchie,
    pas seulement d'en faire varier l'amplitude (contrairement au
    contraste). Necessaire par exemple pour "cinema" : fonctionnel presque
    eteint, ambiance dominante -- un ordre INVERSE de la hierarchie
    habituelle, que le seul contraste ne peut pas produire."""
    rng = rng or random.Random()

    if mood is not None:
        preset = MOOD_PRESETS.get(mood)
        if preset is None:
            raise ValueError(f"Ambiance inconnue: {mood}")
        lo, hi = preset["hue_range"]
        resolved_hue = rng.uniform(lo, hi)
        resolved_sat = preset["saturation"]
        resolved_intensity = preset["global_intensity"]
        resolved_contrast = preset["contrast"]
        resolved_white_temp = preset["white_temperature"]
        resolved_role_mult = preset.get("role_multiplier", {})
        scheme = preset["scheme"]
    else:
        if base_hue is None:
            raise ValueError("base_hue requis si aucune ambiance n'est fournie")
        resolved_hue = base_hue
        resolved_sat = saturation if saturation is not None else 60.0
        resolved_intensity = global_intensity if global_intensity is not None else 1.0
        resolved_contrast = contrast if contrast is not None else 0.6
        resolved_white_temp = white_temperature if white_temperature is not None else 2700.0
        resolved_role_mult = role_multiplier or {}

    hue_slots = _hue_scheme(resolved_hue, scheme)

    suggestions: list[LightSuggestion] = []
    for light in lights:
        role = derive_role(light.position, light.direction)

        hue = _role_hue(role, hue_slots)
        sat = ROLE_BASE_SATURATION[role] * (resolved_sat / 60.0)  # 60 = saturation de reference "neutre"
        bri = _role_brightness(role, resolved_contrast, resolved_intensity)
        bri *= resolved_role_mult.get(role, 1.0)

        # Importance : une lumiere moins importante au sein de son role
        # reste allumee de facon coherente, mais avec moins de poids visuel
        # -- jamais reduite a zero (0.4 plancher) pour rester une source
        # utilisable, pas juste desactivee.
        importance = max(0.0, min(1.0, light.importance))
        bri *= 0.4 + 0.6 * importance

        if light.direction == "indirect":
            sat *= INDIRECT_SATURATION_FACTOR
            # Volontairement PAS de reduction de luminosite ici : l'indirect
            # supporte generalement mieux des niveaux eleves tout en restant
            # doux (section 25) -- contrairement a la v1 de ce module.

        sat = max(0.0, min(100.0, sat))
        bri = _saturation_brightness_tradeoff(sat, bri)
        bri_int = max(1, min(255, round(bri)))

        color_temp_kelvin = None
        if not light.supports_color and light.supports_color_temp:
            # Decalage COHERENT autour de la temperature de base de la
            # scene, jamais une conversion teinte->kelvin independante par
            # lumiere (qui produirait des ecarts incoherents entre
            # lumieres blanches -- exactement ce que le document identifie
            # comme un defaut, section 8).
            color_temp_kelvin = int(max(2000, min(6500, resolved_white_temp + ROLE_KELVIN_OFFSET[role])))

        suggestions.append(
            LightSuggestion(
                entity_id=light.entity_id,
                hue=hue,
                saturation=sat,
                brightness=bri_int,
                color_temp_kelvin=color_temp_kelvin,
            )
        )

    return suggestions
