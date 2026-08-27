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
