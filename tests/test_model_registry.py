"""
Unit and integration tests for model registry, versioning, and A/B testing.

Tests cover model registration, version management, semantic versioning,
and A/B test experiment tracking.
"""

import pytest
import json
import tempfile
import sqlite3
import os
from datetime import datetime
from src.model_registry import ModelRegistry, ModelMetadata
from src.model_versioning import (
    SemanticVersion,
    VersionedModel,
    VersionMigration,
    VersionComparator
)
from src.ab_testing import (
    Experiment,
    ExperimentStatus,
    TrafficAllocationStrategy,
    ExperimentTracker,
    ObservationData
)


class TestSemanticVersion:
    """Test semantic versioning functionality."""

    def test_version_creation(self):
        """Test creating semantic version."""
        version = SemanticVersion(1, 2, 3)
        assert str(version) == "1.2.3"

    def test_version_parse(self):
        """Test parsing semantic version string."""
        version = SemanticVersion.parse("1.2.3")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_version_with_prerelease(self):
        """Test version with prerelease suffix."""
        version = SemanticVersion.parse("1.2.3-alpha.1")
        assert version.major == 1
        assert version.prerelease == "alpha.1"
        assert str(version) == "1.2.3-alpha.1"

    def test_version_increment_major(self):
        """Test incrementing major version."""
        version = SemanticVersion(1, 2, 3)
        incremented = version.increment_major()
        assert str(incremented) == "2.0.0"

    def test_version_increment_minor(self):
        """Test incrementing minor version."""
        version = SemanticVersion(1, 2, 3)
        incremented = version.increment_minor()
        assert str(incremented) == "1.3.0"

    def test_version_increment_patch(self):
        """Test incrementing patch version."""
        version = SemanticVersion(1, 2, 3)
        incremented = version.increment_patch()
        assert str(incremented) == "1.2.4"

    def test_version_compare(self):
        """Test version comparison."""
        v1 = SemanticVersion(1, 2, 3)
        v2 = SemanticVersion(1, 2, 4)
        v3 = SemanticVersion(1, 2, 3)

        assert v1.compare(v2) == -1
        assert v2.compare(v1) == 1
        assert v1.compare(v3) == 0

    def test_version_compatibility(self):
        """Test version compatibility checking."""
        v1 = SemanticVersion(1, 2, 3)
        v2 = SemanticVersion(1, 3, 0)
        v3 = SemanticVersion(2, 0, 0)

        assert v1.is_compatible_with(v2)
        assert not v1.is_compatible_with(v3)

    def test_version_breaking_change(self):
        """Test breaking change detection."""
        v1 = SemanticVersion(1, 2, 3)
        v2 = SemanticVersion(2, 0, 0)
        v3 = SemanticVersion(1, 3, 0)

        assert v1.is_breaking_change(v2)
        assert not v1.is_breaking_change(v3)


class TestVersionMigration:
    """Test model version migration."""

    def test_migration_validation(self):
        """Test migration validation."""
        migration = VersionMigration("1.2.3", "1.3.0")
        assert migration.validate()

    def test_migration_breaking_change(self):
        """Test detecting breaking changes."""
        migration = VersionMigration("1.2.3", "2.0.0")
        assert migration.breaking

    def test_migration_downgrade_invalid(self):
        """Test that downgrading is invalid."""
        migration = VersionMigration("1.3.0", "1.2.3")
        assert not migration.validate()

    def test_migration_steps(self):
        """Test getting migration steps."""
        migration = VersionMigration("1.2.3", "1.4.0")
        steps = migration.get_migration_steps()
        assert len(steps) > 0


class TestVersionComparator:
    """Test version comparison and ranking."""

    def test_compare_performance(self):
        """Test comparing model performance."""
        winner, improvement = VersionComparator.compare_performance(
            "1.0.0",
            {"accuracy": 0.85},
            "1.1.0",
            {"accuracy": 0.90}
        )
        assert winner == "1.1.0"
        assert improvement > 0

    def test_rank_versions(self):
        """Test ranking versions by metric."""
        versions = [
            ("1.0.0", {"accuracy": 0.85}),
            ("1.1.0", {"accuracy": 0.90}),
            ("1.0.1", {"accuracy": 0.87})
        ]
        ranked = VersionComparator.rank_versions(versions)
        assert ranked[0][0] == "1.1.0"
        assert ranked[1][0] == "1.0.1"
        assert ranked[2][0] == "1.0.0"


class TestModelRegistry:
    """Test model registry functionality."""

    @pytest.fixture
    def temp_registry(self):
        """Create temporary registry for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = ModelRegistry(
                registry_db=os.path.join(tmpdir, "registry.db"),
                model_storage_dir=os.path.join(tmpdir, "models")
            )
            yield registry

    def test_registry_initialization(self, temp_registry):
        """Test registry initialization."""
        assert os.path.exists(temp_registry.registry_db)

    def test_register_model(self, temp_registry):
        """Test registering a model."""
        with tempfile.NamedTemporaryFile(suffix=".keras") as model_file:
            model_file.write(b"mock_model_data")
            model_file.flush()

            metadata = ModelMetadata(
                model_id="delay_classifier",
                version="1.0.0",
                created_at=datetime.utcnow().isoformat(),
                framework="tensorflow",
                model_type="binary_classifier",
                input_shape=(None, 10),
                output_shape=(None, 1),
                training_samples=5000,
                hyperparameters={"learning_rate": 0.001},
                performance_metrics={"accuracy": 0.92},
                training_date="2026-04-04",
                data_version="v2.1",
                preprocessor_hash="abc123",
                model_hash="def456"
            )

            storage_path = temp_registry.register_model(
                "delay_classifier",
                model_file.name,
                metadata
            )

            assert storage_path is not None
            assert os.path.exists(storage_path)

    def test_get_model(self, temp_registry):
        """Test retrieving registered model."""
        with tempfile.NamedTemporaryFile(suffix=".keras") as model_file:
            model_file.write(b"mock_model_data")
            model_file.flush()

            metadata = ModelMetadata(
                model_id="classifier",
                version="1.0.0",
                created_at=datetime.utcnow().isoformat(),
                framework="tensorflow",
                model_type="classifier",
                input_shape=(None, 10),
                output_shape=(None, 1),
                training_samples=5000,
                hyperparameters={},
                performance_metrics={"accuracy": 0.92},
                training_date="2026-04-04",
                data_version="v1",
                preprocessor_hash="h1",
                model_hash="h2"
            )

            temp_registry.register_model("classifier", model_file.name, metadata)

            retrieved = temp_registry.get_model("classifier", "1.0.0")

            assert retrieved is not None
            assert retrieved["model_id"] == "classifier"
            assert retrieved["version"] == "1.0.0"

    def test_get_production_model(self, temp_registry):
        """Test retrieving production model."""
        with tempfile.NamedTemporaryFile(suffix=".keras") as model_file:
            model_file.write(b"mock_model_data")
            model_file.flush()

            metadata = ModelMetadata(
                model_id="prod_model",
                version="1.0.0",
                created_at=datetime.utcnow().isoformat(),
                framework="tensorflow",
                model_type="classifier",
                input_shape=(None, 10),
                output_shape=(None, 1),
                training_samples=5000,
                hyperparameters={},
                performance_metrics={"accuracy": 0.92},
                training_date="2026-04-04",
                data_version="v1",
                preprocessor_hash="h1",
                model_hash="h2"
            )

            temp_registry.register_model("prod_model", model_file.name, metadata)
            temp_registry.set_production("prod_model", "1.0.0")

            prod_model = temp_registry.get_production_model("prod_model")

            assert prod_model is not None
            assert prod_model["is_production"] == 1


class TestExperimentTracker:
    """Test A/B testing experiment tracking."""

    @pytest.fixture
    def temp_tracker(self):
        """Create temporary tracker for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ExperimentTracker(
                os.path.join(tmpdir, "experiments.db")
            )
            yield tracker

    def test_tracker_initialization(self, temp_tracker):
        """Test tracker database initialization."""
        assert os.path.exists(temp_tracker.db_path)

    def test_create_experiment(self, temp_tracker):
        """Test creating experiment."""
        experiment = Experiment(
            experiment_id="exp_001",
            name="Model v1.1 vs v1.0",
            baseline_model_id="classifier",
            baseline_version="1.0.0",
            candidate_model_id="classifier",
            candidate_version="1.1.0",
            start_date=datetime.utcnow().isoformat(),
            traffic_allocation_strategy=TrafficAllocationStrategy.UNIFORM
        )

        success = temp_tracker.create_experiment(experiment)
        assert success

    def test_record_observation(self, temp_tracker):
        """Test recording experiment observation."""
        experiment = Experiment(
            experiment_id="exp_002",
            name="Test experiment",
            baseline_model_id="classifier",
            baseline_version="1.0.0",
            candidate_model_id="classifier",
            candidate_version="1.1.0",
            start_date=datetime.utcnow().isoformat()
        )

        temp_tracker.create_experiment(experiment)

        observation = ObservationData(
            experiment_id="exp_002",
            timestamp=datetime.utcnow().isoformat(),
            model_version="1.0.0",
            prediction=45.2,
            actual=43.0,
            delay_minutes=2
        )

        success = temp_tracker.record_observation(observation)
        assert success

    def test_get_experiment_status(self, temp_tracker):
        """Test retrieving experiment status."""
        experiment = Experiment(
            experiment_id="exp_003",
            name="Status test",
            baseline_model_id="classifier",
            baseline_version="1.0.0",
            candidate_model_id="classifier",
            candidate_version="1.1.0",
            start_date=datetime.utcnow().isoformat()
        )

        temp_tracker.create_experiment(experiment)

        status = temp_tracker.get_experiment_status("exp_003")
        assert status is not None
        assert status["experiment_id"] == "exp_003"

    def test_calculate_results(self, temp_tracker):
        """Test calculating experiment results."""
        experiment = Experiment(
            experiment_id="exp_004",
            name="Results test",
            baseline_model_id="classifier",
            baseline_version="1.0.0",
            candidate_model_id="classifier",
            candidate_version="1.1.0",
            start_date=datetime.utcnow().isoformat()
        )

        temp_tracker.create_experiment(experiment)

        results = temp_tracker.calculate_results(
            "exp_004",
            baseline_metric=0.85,
            candidate_metric=0.90
        )

        assert results is not None
        assert results.improvement_pct > 0
