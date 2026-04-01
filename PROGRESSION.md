# Progression du Projet ML: Retards SNCF

## Fait (Fini)

- [x] Scaffolding de l'arborescence du projet (src, tests, docker, etc.).
- [x] Rédaction des guidelines (Zero-Inline comments, worktrees, python3/pip3).
- [x] **Infrastructure Docker & Sécurité (infra/docker-setup)**
  - [x] Dockerfile optimisé Apple Silicon (Multi-arch)
  - [x] compose.yaml (Standards 2026, sans version tag)
  - [x] Sécurisation via UID/GID mapping et utilisateur non-root
  - [x] Documentation des procédures Docker dans README et GUIDELINES
  - [x] Restructuration du dépôt (dossier ./worktrees/)
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
- [x] **Feature 4: Classification Model (feat/classification-model) - Phase 1**
  - [x] DelayClassifier class (TensorFlow/Keras)
  - [x] Architecture: Dense + BatchNorm + Dropout (binary classification)
  - [x] Training: Early stopping, validation split, z-score normalization
  - [x] Evaluation: Accuracy, Precision, Recall, F1-score, AUC-ROC
  - [x] Persistence: Save/load model avec metadata
  - [x] Tests unitaires: 23 tests passing (100%)
  - [x] Quality: 100% docstrings, zéro commentaires inline
  - [x] Merge vers develop: c7a9964

## En cours

- [x] Merge feat/classification-model vers develop - COMPLETE
- [ ] Validation all tests passing (56/56 ✅)
- [ ] Tag release v0.2 (Features 1-4 complete)
- [ ] Phase 2 kickoff: Feature 5 (FastAPI API)

## To-do (Phase 2-4)

- [ ] Feature 5: FastAPI Inference API (CRITICAL - 3-4 jours)
  - [ ] POST /predict endpoint
  - [ ] GET /health endpoint
  - [ ] GET /model/info endpoint
  - [ ] Unit tests: 20+
- [ ] Feature 6: Integration Tests (2-3 jours)
  - [ ] End-to-end pipeline tests
  - [ ] Mock SNCF API
  - [ ] Performance benchmarks
- [ ] Feature 7: WebUI (4-5 jours)
  - [ ] Streamlit dashboard OR Colab notebook
  - [ ] Real-time predictions
  - [ ] Model comparison
- [ ] Feature 8: Real-time Collection (3-4 jours)
  - [ ] SIRI streaming integration
  - [ ] Data pipeline update
- [ ] Feature 9: Model Registry (2-3 jours)
- [ ] Tests d'acceptation end-to-end
