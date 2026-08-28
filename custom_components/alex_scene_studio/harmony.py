"""Algorithme d'harmonie pour Alex Scene Studio.

Calcule, pour chaque lumiere positionnee d'une piece, une proposition de
couleur/luminosite -- melange pondere de trois axes decides avec
l'utilisateur :
  1. Harmonie chromatique (roue des couleurs -- complementaire/analogue/
     triadique) a partir d'une teinte de base (choisie ou tiree d'une
     ambiance predefinie) ;
  2. Equilibre de luminosite selon le role de la lumiere ;
  3. Role fonctionnel selon le type de montage (plafond=general,
     mur=accent, bureau=tache) et la direction (direct/indirect).

Module volontairement independant de Home Assistant (aucun import hass) :
la logique de calcul se teste et se relit isolement. La lecture des
capacites reelles de chaque lumiere (RGB/color_temp/luminosite seule) se
fait cote appelant (scanner HA), pas ici.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Ambiances predefinies
# ---------------------------------------------------------------------------
# Chaque ambiance definit une plage de teinte de depart (0-360, roue HSV),
# une saturation et une luminosite de reference (0-255, echelle HA), et le
# schema chromatique le plus adapte a l'intention de l'ambiance.
MOOD_PRESETS = {
    "energique": {
        "hue_range": (180, 260),  # bleu-violet, dynamique
        "saturation": 75,
        "brightness": 220,
        "scheme": "complementary",
    },
    "detente": {
        "hue_range": (15, 45),  # orange chaud
        "saturation": 55,
        "brightness": 130,
        "scheme": "analogous",
    },
    "concentration": {
        "hue_range": (190, 210),  # bleu neutre, lumiere de type "jour"
        "saturation": 30,
        "brightness": 230,
        "scheme": "analogous",
    },
    "lecture": {
        "hue_range": (35, 50),  # blanc chaud legerement teinte
        "saturation": 40,
        "brightness": 200,
        "scheme": "analogous",
    },
}

# Biais multiplicatifs par role (type de montage) -- appliques a la
# saturation/luminosite de reference. Le bureau reste volontairement proche
# du neutre (priorite a la fonction sur l'esthetique), le mur porte l'accent
# le plus marque, le plafond reste modere pour ne pas dominer visuellement.
ROLE_SATURATION_FACTOR = {"ceiling": 0.7, "wall": 1.2, "desk": 0.3}
ROLE_BRIGHTNESS_FACTOR = {"ceiling": 0.85, "wall": 0.55, "desk": 1.0}

# Une lumiere indirecte (rebondie sur une surface) percoit une saturation et
# une luminosite plus faibles qu'une source directe -- approximation
# raisonnable, pas une simulation physique de la reflexion lumineuse.
INDIRECT_SATURATION_FACTOR = 0.6
INDIRECT_BRIGHTNESS_FACTOR = 0.85

# Teinte proche du blanc chaud neutre utilisee pour les lumieres de bureau,
# independamment du schema chromatique choisi -- la fonction (voir/travailler)
# prime sur l'harmonie decorative pour ce role precis.
DESK_HUE = 45.0


@dataclass
class LightInput:
    """Ce qu'il faut savoir sur une lumiere positionnee pour lui calculer
    une proposition."""

    entity_id: str
    mount_type: str  # "ceiling" | "wall" | "desk"
    direction: str = "direct"  # "direct" | "indirect"
    # Capacites reelles de l'entite HA (supported_color_modes) -- lues en
    # direct cote appelant, jamais mises en cache ici.
    supports_color: bool = True
    supports_color_temp: bool = False


@dataclass
class LightSuggestion:
    entity_id: str
    hue: float  # 0-360, avant conversion eventuelle en color_temp
    saturation: float  # 0-100
    brightness: int  # 0-255
    color_temp_kelvin: int | None = None  # rempli seulement si la lumiere n'a pas de RGB


def _hue_scheme(base_hue: float, scheme: str) -> list[float]:
    """Renvoie les teintes derivees de la teinte de base selon le schema
    chromatique choisi -- roue des couleurs classique."""
    base_hue = base_hue % 360
    if scheme == "complementary":
        return [base_hue, (base_hue + 180) % 360]
    if scheme == "triadic":
        return [base_hue, (base_hue + 120) % 360, (base_hue + 240) % 360]
    # "analogous" par defaut : la base plus deux teintes voisines.
    return [base_hue, (base_hue + 30) % 360, (base_hue - 30) % 360]


def _hue_to_kelvin(hue: float) -> int:
    """Conversion approximative teinte -> temperature de couleur, pour les
    lumieres qui n'ont que color_temp (pas de RGB). Ce n'est PAS une
    conversion physique exacte (teinte HSV et temperature de couleur sont
    deux espaces de couleur different) -- juste une heuristique raisonnable :
    teintes chaudes (rouge/orange, ~0-60°) -> Kelvin bas (chaud),
    teintes froides (bleu, ~180-240°) -> Kelvin haut (froid), interpolation
    lineaire entre les deux pour le reste."""
    hue = hue % 360
    # Ramene la teinte sur un axe chaud(0) -> froid(1) en passant par le
    # chemin le plus court sur la roue chromatique.
    if hue <= 60:
        t = hue / 60 * 0.5  # 0 (rouge) -> 0.5 (jaune)
    elif hue <= 240:
        t = 0.5 + (hue - 60) / 180 * 0.5  # 0.5 (jaune) -> 1.0 (bleu)
    else:
        t = 1.0 - (hue - 240) / 120 * 0.5  # retour vers le chaud au-dela du bleu
    kelvin = 2000 + t * (6500 - 2000)
    return int(max(2000, min(6500, kelvin)))


def compute_scene(
    lights: list[LightInput],
    scheme: str,
    mood: str | None = None,
    base_hue: float | None = None,
    saturation: float | None = None,
    brightness: float | None = None,
    rng: random.Random | None = None,
) -> list[LightSuggestion]:
    """Calcule une proposition pour chaque lumiere de la liste.

    Soit `mood` (nom d'une ambiance predefinie -- pioche une teinte de base
    au hasard dans sa plage a chaque appel, pour varier les propositions),
    soit `base_hue`/`saturation`/`brightness` fournis explicitement (mode
    libre). L'un des deux doit etre fourni."""
    rng = rng or random.Random()

    if mood is not None:
        preset = MOOD_PRESETS.get(mood)
        if preset is None:
            raise ValueError(f"Ambiance inconnue: {mood}")
        lo, hi = preset["hue_range"]
        resolved_hue = rng.uniform(lo, hi)
        resolved_sat = preset["saturation"]
        resolved_bri = preset["brightness"]
        scheme = preset["scheme"]
    else:
        if base_hue is None:
            raise ValueError("base_hue requis si aucune ambiance n'est fournie")
        resolved_hue = base_hue
        resolved_sat = saturation if saturation is not None else 60.0
        resolved_bri = brightness if brightness is not None else 180.0

    hue_slots = _hue_scheme(resolved_hue, scheme)

    suggestions: list[LightSuggestion] = []
    for i, light in enumerate(lights):
        if light.mount_type == "desk":
            hue = DESK_HUE
        elif light.mount_type == "wall":
            hue = hue_slots[1 % len(hue_slots)]
        else:  # ceiling, ou tout autre role par defaut
            hue = hue_slots[0]

        sat_factor = ROLE_SATURATION_FACTOR.get(light.mount_type, 0.7)
        bri_factor = ROLE_BRIGHTNESS_FACTOR.get(light.mount_type, 0.85)

        sat = resolved_sat * sat_factor
        bri = resolved_bri * bri_factor

        if light.direction == "indirect":
            sat *= INDIRECT_SATURATION_FACTOR
            bri *= INDIRECT_BRIGHTNESS_FACTOR

        sat = max(0.0, min(100.0, sat))
        bri_int = max(1, min(255, round(bri)))

        color_temp_kelvin = None
        if not light.supports_color and light.supports_color_temp:
            color_temp_kelvin = _hue_to_kelvin(hue)

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
