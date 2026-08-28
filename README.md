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

Une fois le contour fermé, choisis une lumière, son **type de montage**
(Plafond / Mur / Bureau — sa position physique), son **rôle**
(Principale / Accentuation / Ambiance — sa fonction dans la hiérarchie
lumineuse, **indépendante** du montage : un mur peut porter un accent ou
une ambiance selon l'intention, pas automatiquement l'un ou l'autre juste
parce qu'il est mural), son **importance** (0-1, son poids au sein de son
rôle), sa **hauteur** (en mètres) et sa **direction** (Direct / Indirect —
une source visible vs. une lumière rebondie sur une surface), puis clique à
l'intérieur du contour pour la placer. **Une lumière déjà placée peut être
glissée** directement dans le plan pour la repositionner — si elle est
déposée hors du contour, elle revient automatiquement à sa position
précédente. Tous ces réglages restent modifiables après coup, directement
dans la liste des lumières placées.

### 3. Générer une scène harmonieuse

Une fois au moins une lumière placée, la section « Scène harmonieuse »
apparaît. Deux modes :

- **Ambiance prédéfinie** — Énergique, Détente, Concentration, ou Lecture.
  Chacune fixe une plage de teinte de départ, une saturation, une intensité
  globale, un niveau de contraste, une température de blanc de base, et le
  schéma chromatique le plus adapté. Une teinte différente est tirée dans
  la plage à chaque génération, pour varier les propositions sans jamais
  changer d'ambiance.
- **Teinte libre** — choisis toi-même la teinte de base, la saturation,
  l'intensité globale, le **contraste**, la **température de blanc**, et le
  schéma (complémentaire / analogue / triadique).

Clique sur « Générer une proposition » : **rien n'est envoyé à aucune
lumière** — le plan affiche juste, pour chaque lumière positionnée, la
couleur qu'elle recevrait. L'algorithme (reconstruit à partir d'un document
de conception détaillé sur l'éclairage harmonieux) combine :

- **Hiérarchie par rôle** — principale = luminosité 60-80%, saturation
  faible (fonctionnelle) ; accentuation = 30-50%, porte la teinte
  **dominante** pleinement ; ambiance = 10-30%, porte la teinte
  **secondaire** (dérivée du schéma chromatique), avec plus de douceur.
  Ce ne sont que des points de départ — le **contraste** en contrôle
  l'amplitude réelle : contraste faible = les trois rôles se rapprochent
  (rendu uniforme, façon quotidien) ; contraste élevé = pleine séparation
  (rendu marqué, façon soirée).
- **Importance individuelle** — une lumière moins importante au sein de
  son rôle reste allumée de façon cohérente, mais avec moins de poids
  visuel (jamais réduite à l'extinction, juste plus discrète).
- **Compromis saturation/luminosité** — une couleur très saturée est
  automatiquement un peu moins lumineuse (jusqu'à -35% à saturation
  maximale) : une source saturée qui domine visuellement une pièce sombre
  est presque toujours un signe de déséquilibre, pas d'harmonie.
- **Direction** — l'indirect reçoit une saturation réduite (lumière
  rebondie, toujours plus douce) mais **pas** une luminosité réduite —
  l'indirect supporte généralement mieux des niveaux élevés tout en
  restant confortable.
- **Famille de température cohérente** — pour les lumières sans RGB
  (température de couleur seule), chacune s'écarte légèrement (quelques
  centaines de kelvins selon son rôle) d'une température de **base commune
  à toute la scène**, plutôt qu'une conversion indépendante par lumière qui
  produirait des écarts incohérents entre lumières blanches d'une même
  pièce.

Les capacités réelles de chaque lumière (RGB, température de couleur
seule, luminosité seule) sont lues **en direct** au moment du calcul
(`supported_color_modes`), jamais mises en cache.

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
lumières positionnées (entity_id, position, rôle, importance, hauteur,
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
- La conversion température de blanc → kelvin par rôle est un **décalage
  cohérent** autour d'une base commune à la scène, pas une conversion
  colorimétrique exacte teinte→kelvin (deux espaces de couleur différents).
  Suffisant pour une suggestion d'ambiance cohérente, pas pour une fidélité
  scientifique.
- Le calcul de scène (`compute_scene`) prend la liste des lumières
  directement dans l'appel, sans exiger que la pièce soit déjà enregistrée
  — tu peux générer un aperçu pendant que tu dessines, avant de sauvegarder
  quoi que ce soit.
- L'algorithme d'harmonie (`harmony.py`) est volontairement indépendant de
  Home Assistant (aucun import `hass`) — testable et relisible isolément.

## À venir (pas encore construit)

- Ajustement individuel de chaque lumière dans l'aperçu (actuellement, la
  proposition s'applique telle quelle — pas encore de curseurs pour
  corriger une lumière précise avant validation).
- Prise en compte de la hauteur et de la surface éclairée (couleur/texture
  du mur, section 6 du document de conception) dans le calcul — actuellement
  la hauteur est stockée mais pas encore utilisée par l'algorithme.
- Scènes définies par intention plutôt que par ambiance fixe (« Quotidien »,
  « Cinéma », « Soirée », « Nuit » — section 20 du document) avec variation
  automatique selon l'heure/la lumière naturelle (section 17).
