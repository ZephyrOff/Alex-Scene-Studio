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

Une fois le contour fermé, choisis une lumière, précise si elle est en
**couleur (RGB)** ou **blanc uniquement** (choix explicite — plus fiable
qu'une détection automatique des capacités, qui s'est avérée peu fiable en
pratique), son **type de montage** (Plafond / Mur / Bureau — sa position
physique), son **importance** (0-1, son poids au sein de son rôle), sa
**hauteur** (en mètres) et sa **direction** (Direct / Indirect — une source
visible vs. une lumière rebondie sur une surface), puis clique à l'intérieur
du contour pour la placer.

Le **rôle** (Principale / Accentuation / Ambiance — sa fonction dans la
hiérarchie lumineuse) se **déduit automatiquement** du type de montage et de
la direction, affiché en lecture seule dans le formulaire et dans la liste
des lumières placées — pas besoin de le choisir toi-même :

| Montage | Direct | Indirect |
|---|---|---|
| Plafond | Principale | Ambiance |
| Mur | Accentuation | Ambiance |
| Bureau | Principale | Ambiance |

**Une lumière déjà placée peut être glissée** directement dans le plan pour
la repositionner — si elle est déposée hors du contour, elle revient
automatiquement à sa position précédente. Tous ces réglages restent
modifiables après coup, directement dans la liste des lumières placées.

### 3. Générer une scène harmonieuse

Une fois au moins une lumière placée, la section « Scène harmonieuse »
apparaît. Deux modes :

- **Ambiance prédéfinie** — huit ambiances au total : Énergique, Détente,
  Concentration, Lecture, Quotidien, Cinéma, Soirée, et Nuit (les quatre
  dernières reprennent directement les exemples du document de conception).
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
- **Dégradé de teinte selon la hauteur** — inspiré de **Hue SpatialAware**
  (fonctionnalité réelle de Philips Hue, lancée début 2026) : plutôt qu'une
  teinte fixe par rôle (deux lumières « accentuation » recevaient
  auparavant exactement la même couleur, peu importe leur position réelle),
  la teinte de chaque lumière est désormais **interpolée en continu** selon
  sa hauteur relative dans la pièce — reproduisant l'exemple typique d'un
  coucher de soleil chez Hue : teintes chaudes en bas, froides en haut, en
  dégradé fluide plutôt que par blocs. Deux lumières du même rôle à des
  hauteurs différentes reçoivent maintenant des teintes différentes ; deux
  lumières à la même hauteur reçoivent la même teinte.
- **Reshape par ambiance** — certaines ambiances (Cinéma notamment) vont
  plus loin que le contraste : elles **inversent** carrément la hiérarchie
  habituelle (fonctionnel presque éteint, ambiance dominante — « fonctionnel
  très faible, ambiance présente »), ce que le seul contraste ne peut pas
  produire (il ne fait varier que l'amplitude, jamais l'ordre des rôles).
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

- Les capacités couleur d'une lumière (RGB ou blanc uniquement) sont
  désormais un **choix explicite** de l'utilisateur (`light_type`), pas une
  détection automatique via `supported_color_modes` — cette dernière
  s'était avérée peu fiable en pratique (des lumières RGB confirmées ne
  recevaient jamais de couleur). Le champ reste pré-rempli à titre
  indicatif à partir des capacités détectées au moment du placement, mais
  c'est toujours la valeur choisie qui fait foi pour le calcul.
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
- Le dégradé de teinte utilise la **hauteur** comme seul axe spatial pour
  cette version (reproduit l'exemple « coucher de soleil » de Hue
  SpatialAware, un dégradé vertical). Une position horizontale (par exemple
  « chaud d'un côté de la pièce, froid de l'autre ») n'est pas encore prise
  en compte — Hue combine généralement plusieurs axes selon la scène, mais
  un seul axe suffisait à corriger le vrai défaut signalé (toutes les
  lumières d'un même rôle recevaient exactement la même teinte).
- Cas limite connu : pour le schéma **complémentaire** (les deux teintes
  sont à exactement 180° l'une de l'autre), l'interpolation à la hauteur
  médiane exacte choisit arbitrairement l'un des deux chemins possibles sur
  la roue chromatique (les deux faisant la même longueur) — sans
  conséquence sur la validité du résultat, juste un choix qui pourrait
  surprendre si une lumière tombe pile à cette hauteur médiane.

## À venir (pas encore construit)

- Ajustement individuel de chaque lumière dans l'aperçu (actuellement, la
  proposition s'applique telle quelle — pas encore de curseurs pour
  corriger une lumière précise avant validation).
- Un axe spatial horizontal en plus de la hauteur (position x/y dans la
  pièce), pour des scènes du type « chaud d'un côté, froid de l'autre »
  combinées au dégradé vertical déjà en place.
- Prise en compte de la surface éclairée (couleur/texture du mur, section 6
  du document de conception) dans le calcul.
- Variation automatique selon l'heure/la lumière naturelle (section 17 du
  document de conception).
