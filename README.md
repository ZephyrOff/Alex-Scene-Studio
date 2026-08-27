# Alex Scene Studio

Intégration Home Assistant (panel dédié) pour dessiner le plan de tes pièces
et positionner tes lumières dedans — première étape vers un système de
suggestion de scènes harmonieuses basées sur la disposition réelle des
sources lumineuses (façon application Hue, en plus poussé).

## Périmètre de cette première version (Phase 1)

Cette version se limite au **modèle de données et à l'éditeur de plan** :
dessiner le contour d'une pièce, positionner des lumières dedans, sauvegarder
et recharger. **Rien n'est envoyé à aucune lumière** depuis cet écran — pas
encore d'algorithme d'harmonie, pas encore d'aperçu de scène. Ça viendra dans
une phase ultérieure, une fois cette base validée.

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

1. **Dessiner le contour** — clique dans le plan pour placer les coins de la
   pièce, dans l'ordre. Reclique près du premier point pour refermer le
   contour. Contour **polygonal libre** (pas limité à un rectangle) —
   fonctionne pour des pièces en L, en T, en U, etc. « Annuler le dernier
   point » retire le dernier coin posé ; « Recommencer le contour » repart de
   zéro.
2. **Positionner les lumières** — une fois le contour fermé, choisis une
   lumière et son type de montage (Plafond / Mur / Bureau), puis clique à
   l'intérieur du contour pour la placer. Le type de montage n'a pas encore
   d'effet dans cette version — il sera utilisé par l'algorithme d'harmonie
   d'une phase ultérieure pour distinguer éclairage général (plafond),
   accent (mur), et tâche (bureau).
3. **Enregistrer** — donne un nom à la pièce et clique sur « Enregistrer la
   pièce ». Réutilise le même nom de pièce pour la mettre à jour plutôt que
   d'en créer une nouvelle (sélectionne-la d'abord dans la liste à gauche).

## Stockage

Fichier JSON dans `.storage/` (mécanisme `Store` natif de Home Assistant) —
une bibliothèque de pièces, chacune avec son contour (liste de points) et ses
lumières positionnées (entity_id, position, type de montage).

## Notes techniques

- Les coordonnées sont stockées dans l'espace utilisateur du SVG (viewBox
  fixe 800×500), pas en pixels d'écran bruts — le plan reste cohérent quelle
  que soit la taille de la fenêtre/de l'appareil utilisé pour l'éditer.
- Le test « ce point est-il dans le contour » (pour valider le placement
  d'une lumière) utilise l'algorithme standard de comptage d'intersections
  (ray casting) — fonctionne pour n'importe quelle forme simple, convexe ou
  non.
- Les capacités de chaque lumière (RGB, température de couleur, luminosité
  seule) ne sont pas stockées ici — elles seront lues en direct depuis HA
  (`supported_color_modes`) au moment du calcul d'harmonie, pas mises en
  cache, pour rester à jour si un appareil change.

## À venir (phases suivantes, pas encore construites)

- Algorithme d'harmonie (mélange pondéré : harmonie chromatique, équilibre de
  luminosité, rôle fonctionnel selon le type de montage), avec ambiances
  prédéfinies (Énergique, Détente, Concentration, Lecture...) ou une teinte
  de base librement choisie.
- Panel d'aperçu de la scène suggérée, ajustable avant validation.
- Application aux vraies lumières + sauvegarde optionnelle en tant que vraie
  scène Home Assistant.
