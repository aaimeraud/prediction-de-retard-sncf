# Implementation Roadmap - SNCF Delay Prediction Project

**Document Version:** 1.0  
**Last Updated:** April 1, 2026  
**Project Status:** Phase 2 Ready (After Features 1-4)

---

## 🎯 ROADMAP OVERVIEW

The project has successfully completed **Features 1-4** (Data Pipeline + ML Model). This roadmap outlines the **next 3-5 features** to move from training capability to production-ready system.

```
COMPLETED (Features 1-4)          TO DO (Features 5-7)
─────────────────────────         ──────────────────────
✅ Data Loader                     ⏳ Feature 5: API Layer (CRITICAL)
✅ Data Validator                  ⏳ Feature 6: Integration Tests
✅ Feature Engineer                ⏳ Feature 7: Web UI
✅ Classification Model            ⏳ Feature 8: Real-Time Collection
                                  ⏳ Feature 9: Model Versioning
```

---

## 📍 CURRENT STATE (April 1, 2026)

### What Works ✅
- **Data Pipeline:** GTFS download → validation → feature engineering (100% tested)
- **ML Model:** Binary classification (Delay > 5 min) with training/inference (100% tested)
- **Infrastructure:** Docker environment with TensorFlow 2.15
- **Code Quality:** 58 unit tests, zero inline comments, full docstrings

### What's Missing ❌
- **No API server** - Model cannot be accessed from outside
- **No real-time data** - Cannot use SIRI live updates
- **No web UI** - No user-facing interface
- **No integration tests** - Only unit tests present
- **No model versioning** - Cannot track/compare model versions

---

## 🚀 PHASE 2: PRODUCTION READINESS (Weeks 1-3)

### Feature 5: FastAPI Server + Inference API (CRITICAL)
**Effort:** 3-4 days  
**Priority:** 🔴 CRITICAL  
**Dependency:** Features 1-4 complete

#### Objectives
1. Create REST API for model inference
2. Load trained model from disk
3. Expose /predict endpoint for single/batch predictions
4. Add health check & model info endpoints
5. Implement error handling & validation

#### Deliverables

**File:** `src/api_server.py` (~300 LOC)
```python
"""
FastAPI server for SNCF delay prediction inference.

Provides REST endpoints:
- POST /predict - Single/batch prediction
- GET /health - Server status
- GET /model/info - Model metadata
"""

class PredictionAPI:
    """
    FastAPI wrapper for DelayClassifier model.
    
    Manages model loading, request validation, and prediction serving.
    """
    def __init__(self, model_path: str)
    def setup_routes(self) -> FastAPI
    def predict(self, features: Dict) -> PredictionResponse
    def batch_predict(self, features_list: List[Dict]) -> List[PredictionResponse]
    def get_health(self) -> HealthResponse
    def get_model_info(self) -> ModelInfoResponse
```

**File:** `src/models/model_manager.py` (~150 LOC)
```python
"""
Model versioning and persistence manager.

Handles model save/load with metadata, version tracking.
"""

class ModelManager:
    """Manage model lifecycle (save, load, version tracking)."""
    def save_model(self, classifier: DelayClassifier, version: str, metadata: Dict)
    def load_model(self, version: str = "latest") -> DelayClassifier
    def list_versions(self) -> List[str]
    def get_model_metadata(self, version: str) -> Dict
```

**File:** `tests/test_api_server.py` (~200 LOC)
- Test FastAPI routes
- Test prediction endpoint
- Test error handling
- Test batch predictions
- Test model loading/info

#### Implementation Checklist
- [ ] Create FastAPI app with CORS support
- [ ] Implement /predict endpoint (POST)
- [ ] Implement /health endpoint (GET)
- [ ] Implement /model/info endpoint (GET)
- [ ] Add request/response validation (Pydantic)
- [ ] Add error handling (404, 400, 500)
- [ ] Add model loading logic
- [ ] Write unit tests (20+ tests)
- [ ] Test with curl/Postman
- [ ] Document API with OpenAPI/Swagger

#### Success Criteria
```bash
✅ curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{"hour": 8, "route_type": "1", ...}'

✅ Response: {"prediction": 0.75, "delay_probability": "HIGH"}

✅ curl http://localhost:5000/health
✅ Response: {"status": "ready", "model_version": "v1"}
```

---

### Feature 6: End-to-End Integration Tests (HIGH)
**Effort:** 2-3 days  
**Priority:** 🟠 HIGH  
**Dependency:** Feature 5

#### Objectives
1. Create integration test suite (Data → Model → API)
2. Mock SNCF API for CI/CD
3. Simulate Colab environment
4. Test full prediction pipeline
5. Add performance benchmarks

#### Deliverables

**File:** `tests/test_integration.py` (~400 LOC)
```python
"""
Integration tests for complete delay prediction pipeline.

Tests full flow: Data Loading → Validation → Features → Prediction
"""

class TestPipelineIntegration:
    """Full end-to-end pipeline tests."""
    
    def test_data_to_prediction_flow(self)
    def test_api_prediction_request(self)
    def test_model_loading_and_inference(self)
    def test_batch_prediction_performance(self)
    def test_colab_environment_compatibility(self)
    def test_error_handling_scenarios(self)
```

**File:** `tests/mock_sncf_api.py` (~150 LOC)
```python
"""
Mock SNCF API for testing without external dependencies.

Provides fake GTFS data for CI/CD pipeline.
"""

class MockSNCFAPI:
    """Mock SNCF data source for testing."""
    def get_gtfs_zip(self) -> bytes
    def get_siri_updates(self) -> Dict
```

**File:** `tests/conftest.py` (~200 LOC)
```python
"""
Pytest configuration and fixtures for integration tests.

Provides reusable test data, mocked clients, temporary directories.
"""

@pytest.fixture
def sample_gtfs_data() -> Dict[str, pd.DataFrame]

@pytest.fixture
def mock_sncf_api() -> MockSNCFAPI

@pytest.fixture
def trained_model() -> DelayClassifier

@pytest.fixture
def test_features() -> pd.DataFrame
```

#### Implementation Checklist
- [ ] Create MockSNCFAPI for fake data
- [ ] Write pipeline integration tests
- [ ] Add Colab environment simulation
- [ ] Test data persistence (model save/load)
- [ ] Add performance benchmarks (inference latency)
- [ ] Add fixtures and test utilities
- [ ] Document testing procedures
- [ ] Achieve >80% code coverage

#### Success Criteria
```bash
✅ pytest tests/test_integration.py -v
   test_data_to_prediction_flow PASSED
   test_api_prediction_request PASSED
   test_model_loading_and_inference PASSED
   test_batch_prediction_performance PASSED
   
✅ All tests pass in CI/CD (mocked SNCF API)
✅ Inference latency < 100ms per prediction
✅ Batch prediction (1000 samples) < 5 seconds
```

---

## 📱 PHASE 3: USER INTERFACE (Weeks 2-4)

### Feature 7: Web Dashboard (Streamlit or Colab Notebook)
**Effort:** 4-5 days  
**Priority:** 🟡 MEDIUM  
**Dependency:** Features 1-4

#### Objectives
1. Create interactive web UI for predictions
2. Allow users to input trip parameters
3. Display prediction results + confidence
4. Show historical analysis/statistics
5. Provide downloadable reports

#### Deliverables - Option A: Streamlit Dashboard

**File:** `ui/streamlit_app.py` (~500 LOC)
```python
"""
Streamlit dashboard for SNCF delay prediction.

Interactive web interface for trip delay predictions.
"""

class StreamlitDashboard:
    """Streamlit-based user interface."""
    
    def render_input_form(self) -> Dict
    def render_prediction_results(self, prediction: float)
    def render_historical_analysis(self)
    def render_statistics(self)
    def export_report(self)
```

**File:** `ui/streamlit_utils.py` (~200 LOC)
- Helper functions for Streamlit rendering
- API client wrapper
- Data formatting utilities

**File:** `tests/test_streamlit_app.py` (~150 LOC)
- Test component rendering
- Test data validation
- Test export functionality

**Run Command:**
```bash
streamlit run ui/streamlit_app.py --server.port 8501
```

**Features:**
- Input form for trip parameters (hour, route, stop, date)
- Real-time prediction (click "Predict")
- Confidence score display
- Historical delay statistics by route
- Export prediction report as PDF/CSV

---

#### Deliverables - Option B: Jupyter Notebook (Colab)

**File:** `notebooks/delay_prediction_colab.ipynb` (~150 cells)
```
1. Setup & Authentication
   - Mount Google Drive
   - Clone repo
   - Install dependencies

2. Data Loading
   - Load GTFS data
   - Display sample data

3. Feature Engineering
   - Transform raw data
   - Visualize features

4. Model Training
   - Train classifier
   - Display training curves

5. Predictions & Analysis
   - Interactive form (ipywidgets)
   - Prediction examples
   - Performance metrics

6. Export Results
   - Download trained model
   - Export predictions CSV
```

#### Implementation Checklist
- [ ] Choose UI approach (Streamlit or Notebook)
- [ ] Create input form with parameter validation
- [ ] Integrate with API server (/predict endpoint)
- [ ] Add prediction results display
- [ ] Add historical/statistical analysis
- [ ] Add export functionality
- [ ] Write UI tests
- [ ] Document user guide
- [ ] Test in Colab environment

#### Success Criteria
```bash
✅ Streamlit app runs on localhost:8501
✅ User can input trip parameters
✅ Prediction displays with confidence (0-100%)
✅ Historical stats load from API
✅ Export report as CSV/PDF works
✅ Colab notebook runs start-to-finish
```

---

## 🔄 PHASE 4: ADVANCED FEATURES (Weeks 3-6)

### Feature 8: Real-Time SIRI Integration (HIGH)
**Effort:** 4-5 days  
**Priority:** 🟠 HIGH  
**Dependency:** Features 1-4

#### Objectives
1. Complete SIRI API client implementation
2. Collect real-time delay observations
3. Update training data pipeline
4. Retrain model with recent delays
5. Add streaming predictions

#### Current State
- `realtime_collector.py` started (267 LOC) but untested
- Needs: SIRI endpoint integration, error handling, tests

#### Deliverables

**File:** `src/realtime_collector.py` (Complete, ~400 LOC)
```python
"""
SIRI/GTFS-RT real-time delay collector.

Fetches live delay data from SNCF SIRI endpoints.
"""

class SIRICollector:
    """SIRI API client for real-time delay collection."""
    
    def connect_siri_endpoint(self, url: str)
    def fetch_live_delays(self) -> pd.DataFrame
    def parse_delay_data(self, raw_data: Dict) -> pd.DataFrame
    def store_delays(self, delays: pd.DataFrame)
    def get_delay_statistics(self, window_hours: int = 24) -> Dict
```

**File:** `tests/test_realtime_collector.py` (~250 LOC)
- Test SIRI connection
- Test data parsing
- Test error handling (connection timeouts)
- Test storage operations

#### Implementation Checklist
- [ ] Research SIRI/GTFS-RT endpoints for SNCF
- [ ] Implement SIRI API client
- [ ] Add delay parsing logic
- [ ] Add data storage (cache/database)
- [ ] Write comprehensive tests
- [ ] Add error handling (network failures)
- [ ] Document SIRI API usage
- [ ] Test with real SNCF data (if available)

---

### Feature 9: Model Versioning & Registry (MEDIUM)
**Effort:** 2-3 days  
**Priority:** 🟡 MEDIUM  
**Dependency:** Features 1-4, 5

#### Objectives
1. Track multiple model versions
2. Store model metadata + performance metrics
3. Support A/B testing (compare models)
4. Automatic model selection (best performer)
5. Rollback capability

#### Deliverables

**File:** `src/models/model_registry.py` (~250 LOC)
```python
"""
Model registry for versioning and tracking.

Manages model versions, metadata, and performance metrics.
"""

class ModelRegistry:
    """Track and manage model versions."""
    
    def register_model(self, classifier: DelayClassifier, metadata: Dict)
    def get_best_model(self, metric: str = "f1_score") -> DelayClassifier
    def list_models(self) -> List[ModelVersion]
    def compare_models(self, v1: str, v2: str) -> Dict
    def rollback_model(self, version: str)
    def archive_model(self, version: str)
```

**Directory Structure:**
```
models/
├── v1/
│   ├── model.keras
│   ├── metadata.json          {training_date, accuracy, F1, etc.}
│   ├── feature_scaler.json
│   └── README.md
├── v2/
│   ├── model.keras
│   ├── metadata.json
│   └── ...
├── latest/ → symlink to v2
└── registry.json              {all versions metadata}
```

#### Implementation Checklist
- [ ] Create ModelRegistry class
- [ ] Implement version storage structure
- [ ] Add metadata persistence (JSON)
- [ ] Add model comparison logic
- [ ] Add automatic best-model selection
- [ ] Write tests
- [ ] Document model versioning workflow

---

## 📅 TIMELINE & MILESTONES

### Week 1: API Layer (Feature 5)
```
Mon-Tue: Design API, implement /predict endpoint
Wed:     Add model loading, implement /health endpoint
Thu:     Write unit tests, test with curl
Fri:     Review, documentation, deployment prep
```

**Deliverable:** FastAPI server running on port 5000

### Week 2: Integration Tests (Feature 6) + Real-Time (Feature 8 start)
```
Mon-Tue: Create integration test suite, mock SNCF API
Wed-Thu: Write end-to-end tests, performance benchmarks
Fri:     CI/CD setup, documentation
```

**Deliverable:** 30+ integration tests, all passing

### Week 3: Web UI (Feature 7)
```
Mon-Tue: Design UI, create input form
Wed:     Implement predictions display, add charts
Thu:     Add export functionality
Fri:     Test in Colab, documentation
```

**Deliverable:** Streamlit app or Colab notebook

### Week 4: Advanced Features (Features 8-9)
```
Mon-Tue: Complete real-time collector, add tests
Wed:     Implement model registry
Thu-Fri: Integration, testing, documentation
```

**Deliverable:** Model versioning + real-time collection

---

## 🔗 DEPENDENCY GRAPH

```
Feature 5 (API)
  ├── Requires: Features 1-4 ✅
  └── Blocks: Feature 7 (UI needs API)

Feature 6 (Integration Tests)
  ├── Requires: Feature 5 (API testing)
  └── No blockers

Feature 7 (Web UI)
  ├── Requires: Feature 5 (API integration)
  └── Blocks: Nothing critical

Feature 8 (Real-Time)
  ├── Requires: Features 1-4 (data pipeline)
  └── Enhances: Feature 6 (integration tests)

Feature 9 (Model Registry)
  ├── Requires: Feature 5 (API usage)
  └── Nice-to-have: Feature 8
```

---

## 📊 SUCCESS METRICS

### Feature 5 (API)
- ✅ /predict endpoint responds < 100ms
- ✅ Supports single + batch predictions
- ✅ 100% request validation
- ✅ All error cases handled (400, 404, 500)

### Feature 6 (Integration Tests)
- ✅ >80% code coverage
- ✅ End-to-end pipeline tested
- ✅ Colab compatibility verified
- ✅ All tests pass in CI/CD

### Feature 7 (Web UI)
- ✅ User can make predictions via UI
- ✅ Prediction time < 1 second (end-to-end)
- ✅ Historical statistics display correctly
- ✅ Export functionality works

### Feature 8 (Real-Time)
- ✅ SIRI data collected successfully
- ✅ Delay statistics computed accurately
- ✅ Model retrained with new data
- ✅ Predictions improve (F1 score +5%)

### Feature 9 (Model Registry)
- ✅ Multiple model versions stored
- ✅ Best model automatically selected
- ✅ A/B testing possible
- ✅ Rollback functionality works

---

## 🛠️ TECHNICAL STANDARDS (Continuation)

**Code Quality (Apply to all new code):**
- ✅ Zero inline comments (`#`), docstrings only
- ✅ 100% type hints on all methods
- ✅ Unit tests for every module (>80% coverage)
- ✅ Error handling with context
- ✅ Dataclasses for structured data
- ✅ Full docstring documentation

**Git Workflow:**
- Create new worktree for each feature: `git worktree add ./worktrees/feat/NAME -b feat/NAME`
- Meaningful commit messages
- PR with code review before merge
- Squash commits on merge

**Testing:**
- Unit tests: `pytest tests/`
- Integration tests: `pytest tests/test_integration.py`
- Coverage target: >80%
- Colab compatibility required

---

## 🚦 GO/NO-GO DECISION POINTS

### End of Feature 5 (API)
**Go-NoGo Check:**
- [ ] API server runs without errors
- [ ] /predict endpoint tested successfully
- [ ] Model loads correctly from disk
- [ ] All error cases handled
- [ ] Code review approved

**If NoGo:** Fix issues, retest, reschedule

### End of Feature 6 (Integration Tests)
**Go-NoGo Check:**
- [ ] >80% code coverage achieved
- [ ] All integration tests passing
- [ ] Colab environment verified compatible
- [ ] CI/CD working properly
- [ ] Performance benchmarks acceptable

**If NoGo:** Add more tests, optimize code, retest

### End of Feature 7 (Web UI)
**Go-NoGo Check:**
- [ ] UI renders correctly (Streamlit or Colab)
- [ ] Predictions work from UI
- [ ] Export functionality verified
- [ ] Documentation complete
- [ ] User testing positive

**If NoGo:** Refine UI, retest, gather feedback

---

## 📚 RESOURCES & REFERENCES

### Documentation URLs
- **FastAPI:** https://fastapi.tiangolo.com/
- **Streamlit:** https://docs.streamlit.io/
- **TensorFlow Serving:** https://www.tensorflow.org/tfx/guide/serving
- **Pytest:** https://docs.pytest.org/
- **SIRI Standard:** http://www.siri.org.uk/

### Example Code Patterns
- **API Error Handling:** See `src/api_server.py` (will be created)
- **Test Fixtures:** See `tests/conftest.py` (will be created)
- **Model Persistence:** Study `src/model_classifier.py` (existing Feature 4)

### Team Contacts
- Data Pipeline Questions → Feature 1-3 implementer
- ML Model Questions → Feature 4 implementer
- Docker/Infra Questions → Dockerfile maintainer
- Git/Workflow Questions → Project lead

---

## ✅ ROADMAP SIGN-OFF

**Document Created:** April 1, 2026  
**Last Reviewed:** April 1, 2026  
**Next Review:** After Feature 5 completion

**Approved By:** AI ML Project Orchestrator  
**Status:** Ready for Implementation 🚀

---

**End of Roadmap Document**

