# Contexte du Projet: Prédiction Retards SNCF Temps-Réel

## État actuel global
- **Infrastructure initialisée:** (Dockerfile TF+Colab, arborescence, guidelines, config Git).
- **Architecture ML cible:** TF 2.x pour classification/régression des retards court terme sur un MVP concentré en IDF ou axe unique.
- **Données sources:** GTFS statique, GTFS-RT/SIRI flux temps réel.

## Constraints & Règles (Rappel QA/Engineer)
- **Zero-Inline Comments:** Strictement docstrings `""" doc """`.
- **Git workflow:** Tous les dev sur worktrees séparés.

## Événements Récents
- Projet YAML lu et interprété.
- Arborescence scafoldée par Agent 1 (Infra-Architect).
- Initialisation des docs et des directives.
