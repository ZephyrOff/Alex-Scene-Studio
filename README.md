# Alex Scene Studio

Intégration Home Assistant (panel dédié) pour dessiner le plan de tes pièces,
positionner tes lumières dedans, et obtenir des propositions de scènes
harmonieuses basées sur leur disposition réelle (façon application Hue, en
plus poussé).

## Ce que fait cette version

- **Éditeur de plan** (Phase 1) — dessiner le contour d'une pièce, positionner
  des lumières dedans, sauvegarder et recharger.
- **Système de scène** (Phase 2) — générer une proposition de couleurs
  harmonieuses pour les lumières d'une pièce, en aperçu ajustable, avant
  d'appliquer quoi que ce soit ou de sauvegarder en tant que vraie scène HA.

## Installation

Via HACS (dépôt personnalisé, catégorie **Intégration**) :

1. HACS → Intégrations → ⋮ → Dépôts personnalisés → coller l'URL de ce
   dépôt, catégorie *Integration*.
2. Installer « Alex Scene Studio », **redémarrer Home Assistant**.
3. Réglages → Appareils et services → Ajouter une intégration → chercher
   « Alex Scene Studio » → confirmer. Aucun champ à remplir (instance
   unique).

Un panel « Alex Scene Studio » apparaît dans la barre latérale, **réservé
aux comptes administrateurs**.

## Utilisation

### 1. Dessiner le contour

Clique dans le plan pour placer les coins de la pièce, dans l'ordre
(accroché à la grille visible, pour tracer des murs droits facilement).
Reclique près du premier point pour refermer le contour. Contour
**polygonal libre** (pas limité à un rectangle) — fonctionne pour des pièces
en L, en T, en U, etc. « Annuler le dernier point » retire le dernier coin
posé ; « Recommencer le contour » repart de zéro. **Un point déjà posé peut
être glissé** pour corriger une erreur, à tout moment.

### 2. Positionner les lumières

Une fois le contour fermé, choisis une lumière, son type de montage
(Plafond / Mur / Bureau), sa **hauteur** (en mètres) et sa **direction**
(Direct / Indirect — une source visible vs. une lumière rebondie sur une
surface), puis clique à l'intérieur du contour pour la placer. **Une
lumière déjà placée peut être glissée** directement dans le plan pour la
repositionner — si elle est déposée hors du contour, elle revient
automatiquement à sa position précédente. Hauteur et direction restent
modifiables après coup, directement dans la liste des lumières placées.

### 3. Générer une scène harmonieuse

Une fois au moins une lumière placée, la section « Scène harmonieuse »
apparaît. Deux modes :

- **Ambiance prédéfinie** — Énergique, Détente, Concentration, ou Lecture.
  Chacune fixe une plage de teinte de départ, une saturation, une
  luminosité de référence, et le schéma chromatique le plus adapté. Une
  teinte différente est tirée dans la plage à chaque génération, pour
  varier les propositions sans jamais changer d'ambiance.
- **Teinte libre** — choisis toi-même la teinte de base, la saturation, la
  luminosité, et le schéma (complémentaire / analogue / triadique).

Clique sur « Générer une proposition » : **rien n'est envoyé à aucune
lumière** — le plan affiche juste, pour chaque lumière positionnée, la
couleur qu'elle recevrait. L'algorithme mélange trois axes :

- **Harmonie chromatique** — teintes dérivées de la roue des couleurs
  (complémentaire/analogue/triadique) à partir de la teinte de base.
- **Rôle fonctionnel selon le montage** — plafond = teinte principale,
  saturation modérée (éclairage général, ne doit pas dominer) ; mur =
  teinte accent, saturation plus marquée ; bureau = teinte neutre chaude
  fixe, luminosité maximale (priorité à la fonction).
- **Direction** — une lumière indirecte reçoit une saturation et une
  luminosité réduites par rapport à la même lumière en direct (la lumière
  rebondie paraît toujours plus douce que la source directe).

Les capacités réelles de chaque lumière (RGB, température de couleur
seule, luminosité seule) sont lues **en direct** au moment du calcul
(`supported_color_modes`), jamais mises en cache — une lumière sans RGB
reçoit une température de couleur approchée à la place d'une teinte.

### 4. Appliquer ou enregistrer

- **Appliquer aux lumières** — envoie les valeurs de la proposition (telle
  quelle) aux vraies lumières.
- **Enregistrer comme scène HA** — applique d'abord la proposition, puis
  capture l'état qui en résulte dans une vraie scène Home Assistant
  (service natif `scene.create`) — utilisable ensuite comme n'importe
  quelle scène HA, indépendamment de cette intégration.

## Stockage

Fichier JSON dans `.storage/` (mécanisme `Store` natif de Home Assistant) —
une bibliothèque de pièces, chacune avec son contour (liste de points) et ses
lumières positionnées (entity_id, position, type de montage, hauteur,
direction). Les scènes générées ne sont **pas** stockées ici — seulement au
moment où tu choisis explicitement de les enregistrer en tant que vraie
scène HA (stockage natif HA pour les scènes, pas un stockage propre à cette
intégration).

## Notes techniques

- Les coordonnées du plan sont stockées dans l'espace utilisateur du SVG
  (viewBox fixe 800×500), pas en pixels d'écran bruts — le plan reste
  cohérent quelle que soit la taille de la fenêtre/de l'appareil utilisé
  pour l'éditer.
- Le test « ce point est-il dans le contour » utilise l'algorithme standard
  de comptage d'intersections (ray casting) — fonctionne pour n'importe
  quelle forme simple, convexe ou non.
- La conversion teinte → température de couleur (pour les lumières sans
  RGB) est une **heuristique**, pas une conversion colorimétrique exacte —
  teinte et température de couleur sont deux espaces de couleur différents.
  Suffisant pour une suggestion d'ambiance, pas pour une fidélité
  scientifique.
- Le calcul de scène (`compute_scene`) prend la liste des lumières
  directement dans l'appel, sans exiger que la pièce soit déjà enregistrée
  — tu peux générer un aperçu pendant que tu dessines, avant de sauvegarder
  quoi que ce soit.

## À venir (pas encore construit)

- Ajustement individuel de chaque lumière dans l'aperçu (actuellement, la
  proposition s'applique telle quelle — pas encore de curseurs pour
  corriger une lumière précise avant validation).
- Prise en compte de la hauteur dans le calcul (actuellement stockée mais
  pas encore utilisée par l'algorithme).
