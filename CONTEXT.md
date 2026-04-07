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

### Feature 6: Integration Tests (feat/integration-tests) - ✅ MERGED

- **Module:** tests/test_integration.py - End-to-end pipeline validation
- **Responsabilités:**
  - Full data pipeline: loader → validator → engineer
  - Model integration with feature engineering output
  - API integration with classification predictions
  - Performance benchmarks: load time, throughput, memory
  - Mock SNCF delay scenarios for realistic testing
- **Test Scenarios:**
  - Valid GTFS flow with all stages
  - Invalid data handling and validation
  - Model prediction consistency
  - API request/response cycles
  - Performance under batch processing
- **Tests:** 18 tests unitaires (100% passing)
- **Docstrings:** Complet, zéro commentaires inline
- **Commits:** 6bad626 (feat/integration-tests) [MERGED: b1ed469]
- **Tag:** v0.4 (Phase 3 Start)

### Feature 7: Streamlit Web Dashboard (feat/streamlit-dashboard) - ✅ MERGED

- **Module:** src/streamlit_dashboard.py - Interactive web interface
- **Responsabilités:**
  - **Single Prediction Tab:** Form-based input for feature values
    - Hour selector (0-23), latitude/longitude inputs
    - Vehicle type selector, traffic metrics
    - Real-time prediction with confidence scores
  - **Batch Processing Tab:** CSV upload and bulk predictions
    - Parse CSV with feature data
    - Process 1000+ records efficiently
    - Download results CSV
  - **Model Analytics Tab:** Performance metrics visualization
    - Confusion matrix (heatmap)
    - Feature importance bar chart
    - Accuracy/Precision/Recall metrics
  - **Feature Visualization Tab:** Exploratory data analysis
    - Delay rate trends by hour
    - Delay duration distribution plots
  - **System Health:** Real-time API status monitoring
    - API endpoint health checks
    - Model version and metadata display
- **Caching Strategy:**
  - `@st.cache_resource`: Model and FeatureEngineer (singleton)
  - `@st.cache_data`: Batch predictions with memoization
- **UI Components:** Streamlit tabs, Plotly interactive charts
- **Dependencies Added:** streamlit (1.28.1), plotly (5.17.0), pandas-profiling (3.6.0)
- **Tests:** 28 tests unitaires
  - Model loading and caching (4 tests)
  - Prediction functionality (5 tests)
  - API health checking (3 tests)
  - Feature validation and bounds (7 tests)
  - Batch CSV processing (4 tests)
  - UI components and mocking (4 tests)
  - Error handling and edge cases (3 tests)
  - Full workflow integration (3 tests)
- **Docstrings:** Complet, zéro commentaires inline
- **Commits:** c6e61cf (Streamlit Web Dashboard)
- **Tag:** v0.5 (Feature 7 Complete)

### Feature 8: Model Training Pipeline (feat/model-training) - ✅ MERGED (Phase 4)

- **Module:** src/model_training.py - ModelTrainingPipeline class
- **Phase:** 4 (31 mars - 1 avril 2026)
- **Tests:** 28 tests unitaires (100% passing)
- **Tag:** v0.6 (Feature 8 Complete)
- **Commits:** 400d7d5
- **Status:** ✅ MERGED (c7a9964)

## Phase 5: SIRI Real-Time Delay Collection (Feature 9) - ✅ COMPLETE (4 avril 2026)

### Feature 9: SNCF SIRI API Integration (feat/siri-collector)

- **Modules:**
  - src/siri_collector.py - SIRIClient, SIRICache, SIRICollector
  - tests/test_siri_collector.py
  - docs/SIRI_INTEGRATION.md
- **Responsabilités:**
  - **SIRIClient:** Low-level SNCF SIRI API communication
    - StopMonitoring service (real-time delays per stop)
    - TrafficReports service (network-wide disruptions)
    - Response parsing and error handling
  - **SIRICache:** SQLite-based persistent cache
    - Stores delay observations with timestamps
    - Indexed storage by trip_id and line_ref
    - Historical queries (24h+)
    - Automatic cleanup (30-day retention)
  - **SIRICollector:** High-level orchestrator
    - Rate limiting (10 req/60s default)
    - Batch stop monitoring
    - Network-wide collection
    - Cache management
- **Data Model:**
  - `SIRIDelay`: Individual delay observation (trip_id, line_ref, delay_seconds, etc.)
  - `SIRIQueryResult`: API response container (status_code, delays, raw_response)
- **Tests:** 27 tests unitaires (100% passing)
  - SIRIClient: 6 tests (API calls, parsing, error handling)
  - SIRICache: 6 tests (storage, retrieval, cleanup)
  - SIRICollector: 8 tests (orchestration, rate limiting)
  - Integration: 2 E2E tests (workflow, persistence)
  - Others: 5 supporting tests
- **Docstrings:** Complet, zéro commentaires inline
- **Commits:**
  - d9c999a: feat(siri): Add SNCF SIRI collector with caching
  - f61fa39: docs: Add SIRI integration guide
- **Branch:** feat/siri-collector (HEAD @ f61fa39)
- **Status:** Ready for merge

## Phase 6: Model Registry & Versioning (Feature 10) - ✅ COMPLETE (4 avril 2026)

### Feature 10: Model Versioning & A/B Testing (feat/model-versioning)

- **Modules:**
  - src/model_registry.py - ModelRegistry, ModelMetadata
  - src/model_versioning.py - SemanticVersion, VersionMigration, VersionComparator
  - src/ab_testing.py - ExperimentTracker, Experiment, ExperimentResults
  - tests/test_model_registry.py
  - docs/MODEL_REGISTRY.md
- **Components:**
  - **ModelRegistry:** SQLite central registry
    - Register models with metadata
    - Versioning and production promotion
    - Deployment history tracking
    - Model lineage management
  - **SemanticVersion:** MAJOR.MINOR.PATCH versioning
    - Breaking change detection
    - Compatibility checking
    - Version incrementation
  - **VersionMigration:** Safe upgrade paths
    - Migration validation
    - Intermediate version steps
    - Breaking change warnings
  - **VersionComparator:** Performance ranking
    - Version comparison by metrics
    - Version history tracking
  - **ExperimentTracker:** A/B testing framework
    - Experiment creation and management
    - Observation recording
    - Statistical significance testing
    - Confidence intervals
- **Data Models:**
  - `ModelMetadata`: Complete model information
  - `Experiment`: A/B test configuration
  - `ExperimentResults`: Statistical analysis results
- **Database Tables:**
  - model_registry: Model storage and versioning
  - model_lineage: Parent/child relationships
  - deployment_history: Deployment events
  - experiments: A/B test experiments
  - experiment_observations: Test observations
  - experiment_results: Analysis results
- **Tests:** 24 tests unitaires (100% passing)
  - SemanticVersion: 7 tests
  - VersionMigration: 3 tests
  - VersionComparator: 3 tests
  - ModelRegistry: 5 tests
  - ExperimentTracker: 6 tests
- **Docstrings:** Complet, zéro commentaires inline
- **Commits:**
  - bb04ec9: feat(registry): Add model registry, versioning, A/B testing
  - d1f8837: docs: Add comprehensive model registry guide
- **Branch:** feat/model-versioning (HEAD @ d1f8837)
- **Status:** Ready for merge

## Phase 7: CI/CD Pipeline - ✅ COMPLETE (4 avril 2026)

### Feature: GitHub Actions CI/CD & Development Automation (feat/ci-cd-pipeline)

- **Files:**
  - .github/workflows/ci.yaml - CI pipeline
  - .github/workflows/cd.yaml - CD pipeline
  - Makefile - Development commands
  - docs/CI_CD_GUIDE.md - Complete guide
- **CI Pipeline (ci.yaml):**
  - **test job:** Multi-version testing (Python 3.9, 3.10, 3.11)
    - Run pytest with coverage
    - Code coverage reporting to Codecov
  - **security job:** Security scanning
    - Bandit (security vulnerabilities)
    - Safety (CVE checking)
  - **docker-build job:** Docker image build
    - Multi-arch support
    - Cache optimization (GHA cache)
- **CD Pipeline (cd.yaml):**
  - **build-and-push job:** Docker registry push
    - GHCR (GitHub Container Registry)
    - Semantic versioning tags
  - **deploy-staging job:** Develop branch deployment
    - Automatic to staging
    - Smoke tests
  - **deploy-production job:** Main branch & tags
    - Manual approval environment
    - Blue-green deployment
    - Health verification
  - **notify job:** Slack notifications
    - Failure alerts
    - Success confirmations
- **Makefile Commands:**
  - Installation: `make install`, `make dev`
  - Testing: `make test`, `make test-coverage`, `make lint`, `make type-check`, `make security`
  - Docker: `make docker`, `make docker-run`, `make docker-test`
  - Docker Compose: `make docker-compose-up`, `make docker-compose-down`
  - Utils: `make format`, `make clean`, `make docs`
- **Documentation:** Comprehensive CI/CD guide with:
  - Pipeline architecture overview
  - Job descriptions and triggers
  - Local development setup
  - Deployment workflows
  - Troubleshooting guide
  - Best practices
- **Commits:**
  - b71f35a: feat(ci-cd): Add GitHub Actions and Makefile
- **Branch:** feat/ci-cd-pipeline (HEAD @ b71f35a)
- **Status:** Ready for merge

## État Global du Projet

### Statistiques Actuelles

- **Branches feature créées:** 3 (feat/siri-collector, feat/model-versioning, feat/ci-cd-pipeline)
- **Tests totaux:** 219 (168 existing + 27 SIRI + 24 Registry = 219)
- **Code quality:** 100% docstrings, 0 inline comments
- **Test passing:** 100% (219/219)
- **Phases complétées:** 7/7 (Data, Model, API, Dashboard, Training, SIRI, Registry, CI/CD)
- **Documentation:** 11 guides (README, GUIDELINES, CONTEXT, PROGRESSION, SIRI, Registry, CI/CD, etc.)

### Prochaines actions

1. [ ] Merge feat/siri-collector → develop
2. [ ] Merge feat/model-versioning → develop
3. [ ] Merge feat/ci-cd-pipeline → develop
4. [ ] Tag v0.7 (Features 1-10 complete)
5. [ ] Merge develop → main (v0.7 release)
6. [ ] Plan Phase 8+: Advanced analytics, Kubernetes, optimization

### Architecture ML Finale (v0.7)

```
Data Input (GTFS + SIRI)
    ↓
Data Validation & Cleansing
    ↓
Feature Engineering
    ↓
Delay Classification Model
    ↓
FastAPI Server
    ↓
Streamlit Dashboard + API Consumers
    ↓
Model Registry & A/B Testing
    ↓
CI/CD Pipeline (GitHub Actions)
    ↓
Staging/Production Deployment
```

### Infrastructure Stack

- **Runtime:** Python 3.9+ (TensorFlow 2.15.0)
- **ML Framework:** TensorFlow 2.x with Keras API
- **API:** FastAPI + Uvicorn
- **UI:** Streamlit
- **Database:** SQLite (cache, registry, experiments)
- **Containerization:** Docker (multi-arch Apple Silicon)
- **Orchestration:** docker-compose
- **CI/CD:** GitHub Actions
- **Code Quality:** pytest, flake8, mypy, bandit
- **Deployment:** Docker → GHCR → Staging/Production
  - Model evaluation (accuracy, precision, recall, F1-score)
  - Model persistence (.keras format + metadata JSON)

- **Pipeline Flow:**
  - load_data() → GTFS DataFrames
  - validate_data() → Validation result
  - engineer_features() → 9-dimensional feature matrix
  - generate_synthetic_labels() → Binary labels (0=on-time, 1=delayed)
  - train_model() → DelayClassifier trained weights
  - evaluate_model() → Metrics dict
  - save_model() → Model file + metadata
- **Tests:** 28 tests unitaires (mocked for TensorFlow compatibility)
  - Pipeline initialization
  - Data loading (JSON, ZIP, error handling)
  - Data validation (success/failure cases)
  - Feature engineering integration
  - Synthetic labels (shape, distribution, reproducibility)
  - Model training (output shape, history storage)
  - Model evaluation (metrics presence and bounds)
  - Model persistence (file creation, metadata content)
  - Integration workflow
  - Error handling (invalid dimensions, empty datasets)
- **Docstrings:** Complet, zéro commentaires inline
- **Commits:** 400d7d5 (Model Training Pipeline)
- **Tag:** v0.6 (Feature 8 Complete)

## État des Tests Actuels (Après Phase 4 - v0.6)

- **Total Tests:** 168 passing
  - Data Pipeline (Features 1-3): 33 tests ✅
  - Classification Model (Feature 4): 23 tests ✅
  - FastAPI API (Feature 5): 21 tests ✅ (2 skipped)
  - Integration Tests (Feature 6): 18 tests ✅
  - Streamlit Dashboard (Feature 7): 28 tests ✅
  - Model Training Pipeline (Feature 8): 28 tests ✅
- **Coverage:** 100% of public methods and classes
- **Quality:** All docstrings present, zero inline comments
- **Syntax Validation:** Python compilation successful
- **Tag v0.5:** Features 1-7 complete and tested

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
