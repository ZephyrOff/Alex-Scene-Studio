"""Constantes pour Alex Scene Studio."""

DOMAIN = "alex_scene_studio"

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.rooms"

PANEL_URL_PATH = "alex-scene-studio"
PANEL_TITLE = "Alex Scene Studio"
PANEL_ICON = "mdi:floor-plan"

# Types de montage possibles pour une lumiere positionnee -- combine a la
# direction (direct/indirect), determine automatiquement son role
# fonctionnel dans l'algorithme d'harmonie (voir harmony.derive_role).
MOUNT_TYPES = ("ceiling", "wall", "desk")

# Direct = source visible eclairant la piece ; indirect = lumiere rebondie
# sur une surface (corniche, uplighter...) -- avec mount_type, determine le
# role fonctionnel (harmony.derive_role) et influence directement la
# saturation calculee (voir harmony.py).
DIRECTION_TYPES = ("direct", "indirect")
