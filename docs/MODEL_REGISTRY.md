# Model Registry and Versioning Guide

## Overview

The Model Registry provides centralized management of trained model versions with semantic versioning, A/B testing, and deployment tracking. It enables reproducibility, safe migrations, and data-driven model promotion decisions.

## Architecture

### Components

#### ModelRegistry
Central SQLite-based registry for model storage and lifecycle management.

**Responsibilities:**
- Register new model versions with metadata
- Retrieve models by ID and version
- Promote versions to production
- Track deployment history
- Maintain model lineage (parent/child relationships)

#### SemanticVersion
Semantic versioning (MAJOR.MINOR.PATCH) for model versions.

**Version Semantics:**
- **MAJOR**: Breaking changes (architecture, input/output shape)
- **MINOR**: Feature additions (new regularization, improved training)
- **PATCH**: Bug fixes and minor improvements

#### VersionMigration
Safe migration paths between model versions with breaking change detection.

#### VersionComparator
Performance ranking and progression tracking across versions.

#### ExperimentTracker
A/B testing framework with statistical significance testing and deployment validation.

## Usage Examples

### Register a Model

```python
from src.model_registry import ModelRegistry, ModelMetadata
from datetime import datetime

registry = ModelRegistry(
    registry_db="data/model_registry.db",
    model_storage_dir="models/registry"
)

metadata = ModelMetadata(
    model_id="delay_classifier",
    version="1.0.0",
    created_at=datetime.utcnow().isoformat(),
    framework="tensorflow",
    model_type="binary_classifier",
    input_shape=(None, 10),
    output_shape=(None, 1),
    training_samples=5000,
    hyperparameters={"learning_rate": 0.001, "batch_size": 32},
    performance_metrics={"accuracy": 0.92, "precision": 0.89, "recall": 0.88},
    training_date="2026-04-04",
    data_version="v2.1",
    preprocessor_hash="abc123def456",
    model_hash="model_hash_value",
    tags=["production", "sncf-delay-prediction"],
    description="Improved delay classifier with SIRI real-time data integration"
)

storage_path = registry.register_model(
    model_id="delay_classifier",
    model_path="path/to/trained_model.keras",
    metadata=metadata,
    preprocessor_path="path/to/preprocessor.pkl"
)

print(f"Model registered at: {storage_path}")
```

### Retrieve a Model

```python
# Get latest version
model = registry.get_model("delay_classifier")

# Get specific version
model = registry.get_model("delay_classifier", version="1.0.0")

# Get production model
prod_model = registry.get_production_model("delay_classifier")

print(f"Model accuracy: {model['performance_metrics']['accuracy']}")
```

### Promote to Production

```python
# Promote new version (automatically demotes previous production)
registry.set_production("delay_classifier", "1.1.0")

# Verify promotion
prod = registry.get_production_model("delay_classifier")
print(f"Production version: {prod['version']}")
```

### Archive Old Versions

```python
registry.archive_version("delay_classifier", "1.0.0")
```

### Track Deployment

```python
registry.record_deployment(
    model_id="delay_classifier",
    version="1.1.0",
    environment="production",
    deployed_by="automation_system",
    metrics={"accuracy": 0.92, "latency_ms": 45}
)
```

## Semantic Versioning

### Version Operations

```python
from src.model_versioning import SemanticVersion

version = SemanticVersion.parse("1.2.3")

# Increment components
next_patch = version.increment_patch()      # 1.2.4
next_minor = version.increment_minor()      # 1.3.0
next_major = version.increment_major()      # 2.0.0

# Prerelease versions
beta = version.set_prerelease("beta.1")     # 1.2.3-beta.1

# Comparison
v1 = SemanticVersion.parse("1.2.0")
v2 = SemanticVersion.parse("1.2.3")
assert v1.compare(v2) == -1  # v1 < v2

# Compatibility checking
assert v1.is_compatible_with(v2)  # Same MAJOR version
```

### Version Increment Strategy

```
Initial release:              1.0.0
Bug fix patch:                1.0.1  ← Use for error corrections
Feature addition (backward):  1.1.0  ← Use for new layers, regularization
Model architecture change:    2.0.0  ← Use for reshaping, new input features
```

## A/B Testing

### Create Experiment

```python
from src.ab_testing import (
    ExperimentTracker,
    Experiment,
    TrafficAllocationStrategy,
    ExperimentStatus
)
from datetime import datetime

tracker = ExperimentTracker(db_path="data/ab_experiments.db")

experiment = Experiment(
    experiment_id="exp_v1_1_vs_v1_0",
    name="Delay Classifier v1.1 vs v1.0",
    baseline_model_id="delay_classifier",
    baseline_version="1.0.0",
    candidate_model_id="delay_classifier",
    candidate_version="1.1.0",
    start_date=datetime.utcnow().isoformat(),
    traffic_allocation_strategy=TrafficAllocationStrategy.UNIFORM,
    baseline_traffic_pct=50.0,
    candidate_traffic_pct=50.0,
    primary_metric="accuracy",
    confidence_level=0.95,
    minimum_sample_size=1000,
    description="Testing SIRI integration improvements"
)

tracker.create_experiment(experiment)
```

### Record Observations

```python
from src.ab_testing import ObservationData

observation = ObservationData(
    experiment_id="exp_v1_1_vs_v1_0",
    timestamp=datetime.utcnow().isoformat(),
    model_version="1.0.0",
    prediction=45.2,
    actual=43.0,
    delay_minutes=2,
    trip_id="SNCF_12345",
    line_ref="TER100"
)

tracker.record_observation(observation)
```

### Analyze Results

```python
# Get experiment status
status = tracker.get_experiment_status("exp_v1_1_vs_v1_0")
print(f"Observations: {status['observations']}")

# Calculate statistical significance
results = tracker.calculate_results(
    experiment_id="exp_v1_1_vs_v1_0",
    baseline_metric=0.89,
    candidate_metric=0.91
)

print(f"Improvement: {results.improvement_pct:.1f}%")
print(f"P-value: {results.p_value:.4f}")
print(f"Significant: {results.is_significant}")
print(f"Recommendation: {results.recommendation}")
```

## Database Schema

### model_registry Table

```sql
CREATE TABLE model_registry (
    id INTEGER PRIMARY KEY,
    model_id TEXT NOT NULL,
    version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    framework TEXT,
    model_type TEXT,
    input_shape TEXT,
    output_shape TEXT,
    training_samples INTEGER,
    hyperparameters TEXT (JSON),
    performance_metrics TEXT (JSON),
    training_date TEXT,
    data_version TEXT,
    preprocessor_hash TEXT,
    model_hash TEXT,
    tags TEXT (JSON),
    description TEXT,
    is_production BOOLEAN DEFAULT 0,
    is_archived BOOLEAN DEFAULT 0,
    storage_path TEXT,
    UNIQUE(model_id, version)
);
```

### model_lineage Table

```sql
CREATE TABLE model_lineage (
    id INTEGER PRIMARY KEY,
    parent_model_id TEXT,
    parent_version TEXT,
    child_model_id TEXT,
    child_version TEXT,
    relationship_type TEXT,  -- "derived_from", "fine_tuned_from"
    created_at TEXT,
    notes TEXT
);
```

### deployment_history Table

```sql
CREATE TABLE deployment_history (
    id INTEGER PRIMARY KEY,
    model_id TEXT NOT NULL,
    version TEXT NOT NULL,
    environment TEXT,  -- "dev", "staging", "production"
    deployed_at TEXT,
    deployed_by TEXT,
    status TEXT,  -- "success", "rollback", "failed"
    metrics_at_deployment TEXT (JSON)
);
```

### experiments Table

```sql
CREATE TABLE experiments (
    id INTEGER PRIMARY KEY,
    experiment_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    baseline_model_id TEXT NOT NULL,
    baseline_version TEXT NOT NULL,
    candidate_model_id TEXT NOT NULL,
    candidate_version TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT,
    status TEXT,  -- "planned", "running", "completed"
    traffic_allocation_strategy TEXT
);
```

## Integration with Training Pipeline

### Register After Training

```python
from src.model_training import ModelTrainingPipeline
from src.model_registry import ModelRegistry, ModelMetadata
from datetime import datetime

pipeline = ModelTrainingPipeline()
registry = ModelRegistry()

# Train model
model = pipeline.train(training_data)

# Extract metrics
metrics = model.evaluate(test_data)

# Create metadata
metadata = ModelMetadata(
    model_id="delay_classifier",
    version="1.1.0",
    created_at=datetime.utcnow().isoformat(),
    framework="tensorflow",
    model_type="binary_classifier",
    input_shape=(None, 10),
    output_shape=(None, 1),
    training_samples=len(training_data),
    hyperparameters=pipeline.hyperparameters,
    performance_metrics=metrics,
    training_date=datetime.utcnow().strftime("%Y-%m-%d"),
    data_version="v2.1",
    preprocessor_hash=pipeline.get_preprocessor_hash(),
    model_hash=pipeline.get_model_hash()
)

# Register
registry.register_model(
    model_id="delay_classifier",
    model_path=pipeline.model_path,
    metadata=metadata,
    preprocessor_path=pipeline.preprocessor_path
)
```

### Load for Prediction

```python
from src.api_server import PredictionAPI
from src.model_registry import ModelRegistry

registry = ModelRegistry()
api = PredictionAPI()

# Get production model
prod_model = registry.get_production_model("delay_classifier")

# Load and use
api.load_model(
    model_id=prod_model['model_id'],
    version=prod_model['version'],
    storage_path=prod_model['storage_path']
)

predictions = api.predict(features)
```

## Best Practices

### Version Increment Strategy

1. **Patch releases (1.0.0 → 1.0.1)**
   - Error corrections
   - Small training improvements (<1% metric change)
   - Same architecture and input/output

2. **Minor releases (1.0.0 → 1.1.0)**
   - New layers or regularization
   - Data augmentation improvements
   - Backward compatible
   - Can use existing preprocessors

3. **Major releases (1.0.0 → 2.0.0)**
   - Input shape changes
   - Architecture redesigns
   - Output format changes
   - Requires new preprocessing

### Model Promotion Workflow

```
Development → Staging → Production
    ↓           ↓           ↓
test_*      stage_* (A/B)  prod_*
(1.x.x-dev) (1.x.x-rc1)   (1.x.x)
```

### Deployment Checklist

- [ ] Version incremented correctly
- [ ] Metrics improved or stable
- [ ] Tests pass (100%)
- [ ] Model hash computed
- [ ] Preprocessor compatibility verified
- [ ] A/B test results analyzed
- [ ] Rollback plan documented

## Troubleshooting

### Model Not Found

```python
versions = registry.get_all_versions("delay_classifier")
print(f"Available: {[v['version'] for v in versions]}")
```

### Version Compatibility Issues

```python
from src.model_versioning import SemanticVersion

v1 = SemanticVersion.parse("1.5.3")
v2 = SemanticVersion.parse("2.0.0")

if not v1.is_compatible_with(v2):
    print("Major version change - requires new preprocessing!")
```

### A/B Test Not Significant

```python
if not results.is_significant and results.improvement_pct > 0:
    print(f"Improvement exists ({results.improvement_pct:.1f}%)")
    print(f"But sample size {results.sample_size} is too small")
    print(f"Need at least {results.minimum_sample_size} samples")
```

## Future Enhancements

1. **Cloud Storage Integration**: S3/GCS model storage
2. **Model Comparison Dashboard**: Visual diff of architectures
3. **Automated Promotion**: Trigger production promotion on significance
4. **Rollback Manager**: Gradual traffic shift on degradation
5. **Model Compression**: Version optimization for deployment
6. **Multi-Region Support**: Distributed model serving

## References

- Semantic Versioning: https://semver.org/
- A/B Testing Best Practices: https://en.wikipedia.org/wiki/A/B_testing
- Model Registry Patterns: MLflow Model Registry
