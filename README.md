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

Une fois le contour fermé, choisis le mode de placement (« Une lumière » ou
« Une zone », voir section suivante). En mode lumière : choisis une
lumière, précise si elle est en **couleur (RGB)** ou **blanc uniquement**
(choix explicite — plus fiable qu'une détection automatique des capacités,
qui s'est avérée peu fiable en pratique), son **type de montage** (Plafond /
Mur / Bureau — sa position physique), son **importance** (0-1), sa
**puissance** relative (1.0 = référence — une lumière plus puissante reçoit
automatiquement une consigne plus faible pour un rendu équivalent), sa
**hauteur** (en mètres) et sa **direction** (Direct / Indirect), puis clique
à l'intérieur du contour pour la placer.

Le **rôle** (Principale / Accentuation / Ambiance) se **déduit
automatiquement** du type de montage et de la direction — mais contrairement
à une version antérieure, ce n'est plus une catégorie rigide : chaque
combinaison donne un **mélange pondéré** de rôles (ex. mur + indirect =
85% ambiance / 15% accent), pas une seule case cochée. Le rôle affiché dans
le formulaire est celui qui domine ce mélange, à titre indicatif.

**Une lumière déjà placée peut être glissée** directement dans le plan pour
la repositionner — si elle est déposée hors du contour, elle revient
automatiquement à sa position précédente. Tous ces réglages restent
modifiables après coup, directement dans la liste des lumières placées.

### 3. Positionner des zones (ancrages chromatiques)

En mode zone : donne un nom (ex. « Mur TV », « Coin lecture »), une teinte,
une saturation, et une **portée** (rayon d'influence), puis clique dans le
contour pour la placer. Une zone tire la teinte des lumières **proches**
vers la sienne — l'influence décroît linéairement avec la distance et
s'annule à la portée choisie. Permet des scènes avec plusieurs ambiances
chromatiques simultanées dans une même pièce (ex. bleu près de la TV, chaud
dans le coin lecture), pas seulement un unique dégradé du sol au plafond.
Une zone déjà placée peut aussi être glissée pour la repositionner.

### 4. Générer une scène harmonieuse

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
- **Palette riche à 6 teintes, en dégradé continu selon la hauteur** —
  inspiré de **Hue SpatialAware** (fonctionnalité réelle de Philips Hue,
  lancée début 2026) et comparé directement à de vraies scènes de la
  galerie Hue (Crépuscule tropical, Scintillement d'émeraude, Rio...),
  toutes composées de **6 teintes distinctes** réparties sur un large arc
  de la roue chromatique — pas 2-3 points isolés comme dans une version
  antérieure de cet algorithme, qui donnait un rendu bien trop uniforme une
  fois comparé à ces vraies références. Chaque lumière reçoit une teinte
  **interpolée en continu** le long de ce dégradé à 6 points selon sa
  hauteur relative dans la pièce (reproduisant l'exemple typique d'un
  coucher de soleil chez Hue : teintes chaudes en bas, froides en haut).
  Le sens du balayage (vers le violet/magenta ou vers le vert/jaune depuis
  une même teinte de départ) est tiré au hasard à chaque génération, comme
  la teinte elle-même — deux vraies scènes Hue à teintes de départ proches
  peuvent diverger dans des sens opposés, un seul sens fixe ne suffisait
  pas à reproduire cette variété. Deux lumières du même rôle à des hauteurs
  différentes reçoivent maintenant des teintes réellement différentes ;
  deux lumières à la même hauteur reçoivent la même teinte.
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
- **Zones à influence par distance** — reconstruit à partir d'un guide de
  référence sur les moteurs de lumière spatiale. Chaque zone tire la teinte
  des lumières proches vers la sienne, avec un poids qui décroît
  linéairement jusqu'à sa portée (au-delà, aucune influence). Une lumière
  peut être influencée par zéro, une, ou plusieurs zones simultanément.
- **Mélange en espace de couleur perceptuel (OKLCH)** — quand plusieurs
  contributions chromatiques se combinent (le dégradé de base + une ou
  plusieurs zones proches), le mélange se fait en OKLCH plutôt qu'en simple
  moyenne RGB/HSV, qui produirait des couleurs « sales » (grisâtres/brunes)
  dès que plusieurs teintes différentes se rencontrent. La teinte finale
  utilise en plus une **moyenne circulaire** (pas linéaire) pour éviter
  qu'un mélange proche de la limite 350°/10° ne donne à tort une moyenne
  autour de 180°.
- **Puissance relative des luminaires** — une bande LED puissante et une
  petite ampoule ne reçoivent pas la même consigne pour un rendu
  équivalent : une lumière deux fois plus puissante (réglage à 2.0) reçoit
  automatiquement une luminosité réduite en conséquence.

Les capacités réelles de chaque lumière (RGB, température de couleur
seule, luminosité seule) sont lues **en direct** au moment du calcul
(`supported_color_modes`), jamais mises en cache.

### 5. Appliquer ou enregistrer

- **Appliquer aux lumières** — envoie les valeurs de la proposition (telle
  quelle) aux vraies lumières.
- **Enregistrer comme scène HA** — applique d'abord la proposition, puis
  capture l'état qui en résulte dans une vraie scène Home Assistant
  (service natif `scene.create`) — utilisable ensuite comme n'importe
  quelle scène HA, indépendamment de cette intégration.

## Stockage

Fichier JSON dans `.storage/` (mécanisme `Store` natif de Home Assistant) —
une bibliothèque de pièces, chacune avec son contour (liste de points), ses
lumières positionnées (entity_id, position, importance, puissance, hauteur,
direction, couleur/blanc), et ses zones (nom, position, teinte, saturation,
portée). Les scènes générées ne sont **pas** stockées ici — seulement au
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
- Le dégradé de base utilise la **hauteur** comme axe spatial (reproduit
  l'exemple « coucher de soleil » de Hue SpatialAware) ; les **zones**
  ajoutent une influence supplémentaire par distance réelle (x/y dans le
  plan), permettant plusieurs ambiances chromatiques dans une même pièce —
  ce que l'axe vertical seul ne permettait pas.
- La largeur d'arc par schéma (`SCHEME_ARC_WIDTH`) est une **approximation**
  mesurée à l'œil sur quelques vraies scènes Hue, pas une réplique exacte
  de leurs choix précis — les palettes Hue sont composées à la main par de
  vrais coloristes, avec un espacement qui n'est probablement pas
  parfaitement régulier comme le fait cet algorithme. Reproduit l'esprit du
  résultat (un vrai dégradé riche à 6 teintes sur un large arc), pas une
  copie pixel-perfect.
- La conversion OKLCH utilise les formules publiées par Björn Ottosson
  (2020) — testées avec un aller-retour exact (sans perte) sur les couleurs
  de référence (rouge, vert, bleu, blanc...).
- Le falloff d'influence des zones est **linéaire** (1 à distance nulle, 0
  à la portée choisie) — le guide de référence utilisé pour cette version
  propose aussi des variantes quadratique/exponentielle/à puissance
  réglable pour des formes de dégradé différentes, non retenues pour cette
  première implémentation par souci de simplicité.

## À venir (pas encore construit)

- Ajustement individuel de chaque lumière dans l'aperçu (actuellement, la
  proposition s'applique telle quelle — pas encore de curseurs pour
  corriger une lumière précise avant validation).
- Orientation/angle de faisceau pour les spots (nécessiterait de capturer
  une direction vectorielle, pas juste une position) — explicitement classé
  comme avancé dans le guide de référence utilisé pour cette version.
- Prise en compte de la surface éclairée (couleur/texture du mur) dans le
  calcul.
- Lissage par graphe de voisinage (éviter que deux lumières très proches
  reçoivent des teintes trop opposées, sauf si la scène le demande),
  métriques de score d'harmonie, variation automatique selon l'heure/la
  lumière naturelle, calibration par appareil réel — toutes explicitement
  classées comme des extensions à ajouter après validation du noyau, pas
  avant, dans le guide de référence utilisé pour cette version.
