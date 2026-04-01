# Contexte du Projet: Prédiction Retards SNCF Temps-Réel

## État actuel global

- **Infrastructure initialisée :** 
  - Docker Compose (Standard 2026, `compose.yaml`).
  - Image Multi-arch TF 2.x (M1/M2/M3 compatible).
  - Sécurité : UID/GID mapping, utilisateur `developer` non-privilégié.
  - Arborescence interne au dépôt bare : `./worktrees/`.
- **Architecture ML cible :** TF 2.x pour classification/régression retards court terme MVP IDF.
- **Conventions Git :** Prefixes `feat/`, `hotfix/`, `docs/`, `infra/`, `chore/`, `refactor/`.
- **Données sources:** GTFS statique, GTFS-RT/SIRI flux temps réel.

## Features Complétées (Session: 31 mars - 1 avril 2026 | Phase 1-2 COMPLETE)

### Feature 1: Data Loader (feat/data-loader) - ✅ MERGED

- **Module:** src/data_loader.py - GTFSDataLoader class
- **Responsabilités:**
  - Télécharge les archives GTFS depuis l'API SNCF open data
  - Parse les fichiers ZIP et charge les CSV
  - Support tables: stops, routes, trips, stop_times, calendar
  - Cachage local pour éviter re-téléchargement
- **Tests:** 8 tests unitaires (100% passing)
- **Docstrings:** Complet, zéro commentaires inline
- **Colab-ready:** DataFrames pandas standards

### Feature 2: Data Validation (feat/data-validation) - ✅ MERGED

- **Module:** src/data_validator.py - GTFSValidator class
- **Responsabilités:**
  - ValidationResult dataclass pour résultats structurés
  - Checks: tables requises, schémas, missing values, bounds géographiques, intégrité référentielle
  - Strict mode pour traiter warnings as errors
  - Statistiques GTFS (rows, colonnes, mémoire)
- **Tests:** 13 tests unitaires (100% passing)
- **Docstrings:** Complet, zéro commentaires inline
- **Colab-ready:** Retourne rapports texte et DataFrames

### Feature 3: Feature Engineering (feat/feature-engineering) - ✅ MERGED

- **Module:** src/feature_engineer.py - FeatureEngineer class
- **Responsabilités:**
  - FeatureSet dataclass pour stockage structuré
  - Temporal features: hour_of_day, is_peak_hours, service_id
  - Geographic features: stop_lat, stop_lon, is_ile_de_france
  - Route features: route_short_name, route_type (one-hot encoded)
  - Delay history: route_avg_delay, route_delay_volatility
  - Feature importance baseline estimation
- **Tests:** 12 tests unitaires (100% passing)
- **Docstrings:** Complet, zéro commentaires inline
- **Colab-ready:** Intégration seamless avec data_loader et validator

### Feature 4: Classification Model (feat/classification-model) - ✅ MERGED

- **Module:** src/model_classifier.py - DelayClassifier class
- **Responsabilités:**
  - Binary classification: Delay > 5 min vs <= 5 min
  - Architecture: Dense(128) + BatchNorm + Dropout(0.3) → Dense(64) + BatchNorm + Dropout(0.3) → Dense(1, Sigmoid)
  - Normalization: Z-score (mean=0, std=1) avec persistence des stats
  - Training: Adam optimizer, binary crossentropy, early stopping
  - Evaluation: Accuracy, Precision, Recall, F1-score, AUC-ROC, Confusion Matrix
  - Persistence: Save/load model (.keras + metadata JSON)
- **Data Containers:** TrainingHistory, EvaluationMetrics (dataclasses)
- **Tests:** 23 tests unitaires (100% passing)
  - Initialization, normalization, training, prediction
  - Evaluation metrics, save/load consistency
  - Full pipeline integration tests
- **Docstrings:** Complet, zéro commentaires inline
- **Colab-ready:** TensorFlow 2.x, numpy/pandas standard imports
- **Commits:** 85a2eef + 7ff3924 (docs) [MERGED: c7a9964]

## État des Tests Actuels

- **Total Tests:** 77 passing, 2 skipped (API with missing model)
- **Data Pipeline (Features 1-3):** 33 tests ✅
- **Classification Model (Feature 4):** 23 tests ✅
- **FastAPI API (Feature 5):** 21 tests ✅ (2 skipped)
- **Coverage:** 100% of public methods and classes
- **Quality:** All docstrings present, zero inline comments

## Constraints & Règles (Rappel QA/Engineer)

- **Zero-Inline Comments:** Strictement docstrings `""" doc """`.
- **Git workflow:** Tous dev sur worktrees séparés.
- **Python CLI:** Exclusivement python3 et pip3.
- **Test Coverage:** Pytest pour tous modules, min 80% passing.
- **Docstrings:** Tous public methods/classes + parameters + returns.

## Pipeline Data & ML actuel

```
GTFS ZIP (remote)
  → GTFSDataLoader.download_gtfs() [cache local]
  → GTFSDataLoader.parse_gtfs_zip() [5 DataFrames]
  → GTFSValidator.validate_gtfs_data() [ValidationResult]
  → FeatureEngineer.engineer_features() [FeatureSet with ~15 features]
  → DelayClassifier.normalize_features() [z-score normalized]
  → DelayClassifier.train() [Binary classification model]
  → DelayClassifier.predict() [Delay prediction: 0 or 1]
```

## Commits Importants

- d3c3589: feat/data-loader (354 insertions, 8 tests)
- 603fa78: feat/data-validation (543 insertions, 13 tests)
- 59edbf5: feat/feature-engineering (491 insertions, 12 tests)
- 85a2eef: feat/classification-model (520 insertions, 23 tests)
- d27e76e: feat/fastapi-endpoint (864 insertions, 21 tests) [MERGED]

### Feature 5: FastAPI Inference API (feat/fastapi-endpoint) - ✅ MERGED

- **Module:** src/api_server.py - PredictionAPI class
- **Responsabilités:**
  - REST API wrapper autour du modèle de classification
  - POST /predict: Single prediction avec validation
  - POST /predict/batch: Batch predictions (1-1000 items)
  - GET /health: Server health/readiness check
  - GET /model/info: Model metadata et performance
  - Pydantic models: PredictionRequest (10 fields), BatchPredictionRequest
  - Delay categorization: LOW/MEDIUM/HIGH avec confidence levels
  - CORS middleware, Auto Swagger UI at /docs
- **Request Models:** 10 engineered features (hour, lat, lon, delay, volatility, etc.)
- **Response Models:** Predictions, probabilities, categories, confidence scores
- **Error Handling:** 422 Validation, 503 Model not loaded, 500 Server error
- **Tests:** 21 tests unitaires (100% passing)
  - Request validation, endpoints, error handling
  - API class lifecycle, CORS middleware
  - Full integration tests
- **Docstrings:** Complet, zéro commentaires inline
- **Colab-ready:** FastAPI, Pydantic, standard async/await patterns
- **Commits:** 455a410 (original) → d27e76e (authorship corrected)

## Prochaines Étapes (To-do)

1. ✅ **Feature 4: Classification Model** - COMPLETED (Phase 1)
2. **Feature 5: FastAPI endpoint** - /predict route pour inférence (Phase 2)
3. **Feature 6: QA & Context** - MCP SDK, CONTEXT.md updates (Phase 3)
4. **Feature 7: WebUI** - Colab notebook ou Streamlit dashboard
5. **Testing:** Integration tests end-to-end simulant Colab env
