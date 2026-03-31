# Prédiction de retard ferroviaire en temps réel

## Description
Projet visant à anticiper les retards des trains à court terme en exploitant les données ouvertes de la SNCF (horaires GTFS statiques et flux temps réel GTFS-RT/SIRI) combinées à des modèles de machine learning modernes.

## Infrastructure
- **Image Docker:** TensorFlow 2.x GPU + Colab runtime compatible.
- **Python:** 3.10+

## Protocol Git (Worktrees)
L'utilisation de `git worktree` est **obligatoire** pour développer de nouvelles fonctionnalités afin de maintenir notre environnement propre et isolé.

### Workflow pour une nouvelle feature:
1. Création du worktree et de la branche:
   ```bash
   git worktree add ../feature-<nom> -b feat/<nom>
   cd ../feature-<nom>
   ```
2. Développement
3. Commit et Push
4. Nettoyage et retour au dossier principal:
   ```bash
   cd ../main
   git worktree remove ../feature-<nom>
   ```

## Accès Colab
Ce projet est compatible avec Google Colab grâce à l'image Docker spécifiée et la configuration des notebooks. Lancez le container Docker pour avoir accès à Jupyter.

## Données
Les données peuvent être structurées dans le dossier `data/`.
Lien open data: https://data.sncf.com/explore/dataset/horaires-sncf/information/
Lien API: https://data.sncf.com/api/explore/v2.1/catalog/datasets/horaires-sncf/records?limit=20
