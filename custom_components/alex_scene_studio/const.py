"""Constantes pour Alex Scene Studio."""

DOMAIN = "alex_scene_studio"

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.rooms"

PANEL_URL_PATH = "alex-scene-studio"
PANEL_TITLE = "Alex Scene Studio"
PANEL_ICON = "mdi:floor-plan"

# Types de montage possibles pour une lumiere positionnee -- pilote le role
# fonctionnel dans l'algorithme d'harmonie (phase 2, pas encore construite) :
# plafond = eclairage general, mur = accent, bureau = tache.
MOUNT_TYPES = ("ceiling", "wall", "desk")

# Role fonctionnel d'une lumiere (independant de sa position physique) --
# section 19 du document de conception : une lumiere murale peut porter un
# accent ou une ambiance selon l'intention, pas automatiquement l'un ou
# l'autre juste parce qu'elle est au mur.
ROLES = ("primary", "accent", "ambient")

# Direct = source visible eclairant la piece ; indirect = lumiere rebondie
# sur une surface (corniche, uplighter...) -- influencera plus tard
# l'algorithme d'harmonie (contribution differente a la couleur/l'ambiance
# percue de la piece).
DIRECTION_TYPES = ("direct", "indirect")
