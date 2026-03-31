# Progression du Projet ML: Retards SNCF

## Fait (Fini)

- [x] Scaffolding de l'arborescence du projet (src, tests, docker, etc.).
- [x] Rédaction des guidelines (Zero-Inline comments, worktrees, python3/pip3).
- [x] Création du Dockerfile compatible TF + Colab et requirements de base.
- [x] **Feature 1: Data Loader (feat/data-loader)**
  - [x] GTFSDataLoader class pour télécharger et parser les fichiers GTFS
  - [x] Support des tables: stops, routes, trips, stop_times, calendar
  - [x] Tests unitaires: 8 tests passing
  - [x] Commit: d3c3589
- [x] **Feature 2: Data Validation (feat/data-validation)**
  - [x] GTFSValidator class avec 5 types de vérifications
  - [x] ValidationResult pour résultats structurés
  - [x] Tests unitaires: 13 tests passing
  - [x] Commit: 603fa78
- [x] **Feature 3: Feature Engineering (feat/feature-engineering)**
  - [x] FeatureEngineer class avec extraction de features
  - [x] Temporal features (heure, heures de pointe)
  - [x] Geographic features (coordonnées, région Île-de-France)
  - [x] Route features (type, nom court)
  - [x] Tests unitaires: 12 tests passing
  - [x] Commit: 59edbf5

## En cours

- [ ] Review et merge des 3 features dans develop
- [ ] Communication des résultats au client

## To-do

- [ ] Feature 4: Classification Model (retard > 5min) avec TensorFlow
- [ ] Feature 5: APIs FastAPI pour prédictions
- [ ] Feature 6: WebUI pour visualisation
- [ ] Integration MCP SDK Python pour persistance de contexte
- [ ] Deployment sur Colab
- [ ] Tests d'acceptation end-to-end
