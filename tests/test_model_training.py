"""
Unit Tests for Model Training Pipeline.

Test coverage:
- Pipeline initialization
- Data loading and validation
- Feature engineering integration
- Model training workflow
- Model evaluation metrics
- Persistence (save/load)
- Error handling and edge cases
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import json
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from model_training import ModelTrainingPipeline
from data_loader import GTFSDataLoader
from data_validator import GTFSValidator
from feature_engineer import FeatureEngineer
from model_classifier import DelayClassifier


class TestPipelineInitialization:
    """Test suite for pipeline initialization."""
    
    def test_pipeline_init(self):
        """
        Verify ModelTrainingPipeline initializes correctly.
        """
        pipeline = ModelTrainingPipeline()
        
        assert isinstance(pipeline, ModelTrainingPipeline)
        assert pipeline.model_dir.exists()
        assert isinstance(pipeline.loader, GTFSDataLoader)
        assert isinstance(pipeline.validator, GTFSValidator)
        assert isinstance(pipeline.engineer, FeatureEngineer)
        assert isinstance(pipeline.classifier, DelayClassifier)
    
    def test_pipeline_custom_data_path(self):
        """
        Verify pipeline accepts custom data path.
        """
        custom_path = "custom_data.json"
        pipeline = ModelTrainingPipeline(data_path=custom_path)
        
        assert str(pipeline.data_path) == custom_path
    
    def test_model_dir_creation(self):
        """
        Verify models directory is created if missing.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_pipeline_path = Path(tmpdir) / "test_pipeline"
            custom_pipeline_path.mkdir(parents=True, exist_ok=True)
            
            pipeline = ModelTrainingPipeline()
            assert pipeline.model_dir.exists()


class TestDataLoading:
    """Test suite for data loading step."""
    
    def test_load_data_file_not_found(self):
        """
        Verify error handling for missing data file.
        """
        pipeline = ModelTrainingPipeline(data_path="nonexistent.json")
        
        with pytest.raises(FileNotFoundError):
            pipeline.load_data()
    
    def test_load_data_unsupported_format(self):
        """
        Verify error handling for unsupported file formats.
        """
        with tempfile.NamedTemporaryFile(suffix=".txt") as f:
            pipeline = ModelTrainingPipeline(data_path=f.name)
            
            with pytest.raises(ValueError):
                pipeline.load_data()
    
    @patch('model_training.GTFSDataLoader.load_gtfs_from_json')
    def test_load_data_json(self, mock_load):
        """
        Verify JSON data loading.
        """
        mock_gtfs = {
            'stops': pd.DataFrame(),
            'routes': pd.DataFrame(),
            'trips': pd.DataFrame(),
            'stop_times': pd.DataFrame(),
            'calendar': pd.DataFrame()
        }
        mock_load.return_value = mock_gtfs
        
        with tempfile.NamedTemporaryFile(suffix=".json") as f:
            pipeline = ModelTrainingPipeline(data_path=f.name)
            result = pipeline.load_data()
            
            mock_load.assert_called_once()
            assert len(result) == 5


class TestDataValidation:
    """Test suite for data validation step."""
    
    @patch('model_training.GTFSValidator.validate_gtfs_data')
    def test_validate_data_success(self, mock_validate):
        """
        Verify successful data validation.
        """
        mock_result = Mock()
        mock_result.is_valid = True
        mock_result.record_count = 100
        mock_result.errors = []
        mock_validate.return_value = mock_result
        
        pipeline = ModelTrainingPipeline()
        gtfs_data = {}
        
        result = pipeline.validate_data(gtfs_data)
        
        assert result is True
        mock_validate.assert_called_once()
    
    @patch('model_training.GTFSValidator.validate_gtfs_data')
    def test_validate_data_failure(self, mock_validate):
        """
        Verify error handling for validation failure.
        """
        mock_result = Mock()
        mock_result.is_valid = False
        mock_result.errors = ["Missing column: stop_id"]
        mock_validate.return_value = mock_result
        
        pipeline = ModelTrainingPipeline()
        gtfs_data = {}
        
        with pytest.raises(RuntimeError):
            pipeline.validate_data(gtfs_data)


class TestFeatureEngineering:
    """Test suite for feature engineering step."""
    
    @patch('model_training.FeatureEngineer.engineer_features')
    def test_engineer_features(self, mock_engineer):
        """
        Verify feature engineering integration.
        """
        mock_feature_set = Mock()
        mock_feature_set.features_array = np.random.randn(100, 9)
        mock_engineer.return_value = mock_feature_set
        
        pipeline = ModelTrainingPipeline()
        gtfs_data = {}
        
        features = pipeline.engineer_features(gtfs_data)
        
        assert features.shape == (100, 9)
        mock_engineer.assert_called_once()


class TestSyntheticLabels:
    """Test suite for synthetic label generation."""
    
    def test_generate_synthetic_labels_shape(self):
        """
        Verify generated labels have correct shape.
        """
        pipeline = ModelTrainingPipeline()
        
        labels = pipeline.generate_synthetic_labels(100)
        
        assert labels.shape == (100,)
        assert all(l in [0, 1] for l in labels)
    
    def test_generate_synthetic_labels_distribution(self):
        """
        Verify label distribution is realistic (~20% delayed).
        """
        pipeline = ModelTrainingPipeline()
        
        labels = pipeline.generate_synthetic_labels(1000)
        
        delay_ratio = labels.sum() / len(labels)
        assert 0.1 < delay_ratio < 0.3
    
    def test_generate_synthetic_labels_reproducible(self):
        """
        Verify label generation is reproducible with seed.
        """
        pipeline1 = ModelTrainingPipeline()
        pipeline2 = ModelTrainingPipeline()
        
        labels1 = pipeline1.generate_synthetic_labels(100)
        labels2 = pipeline2.generate_synthetic_labels(100)
        
        np.testing.assert_array_equal(labels1, labels2)


class TestModelTraining:
    """Test suite for model training step."""
    
    def test_train_model_output_shape(self):
        """
        Verify training runs and returns history.
        """
        pipeline = ModelTrainingPipeline()
        
        X = np.random.randn(100, 9)
        y = np.random.randint(0, 2, 100)
        
        history = pipeline.train_model(X, y, epochs=2, verbose=0)
        
        assert isinstance(history, dict)
        assert 'accuracy' in history
        assert len(history['accuracy']) > 0
    
    def test_train_model_stores_history(self):
        """
        Verify training history is stored in pipeline.
        """
        pipeline = ModelTrainingPipeline()
        
        X = np.random.randn(100, 9)
        y = np.random.randint(0, 2, 100)
        
        pipeline.train_model(X, y, epochs=2, verbose=0)
        
        assert len(pipeline.training_history) > 0


class TestModelEvaluation:
    """Test suite for model evaluation step."""
    
    def test_evaluate_model_metrics(self):
        """
        Verify evaluation returns all required metrics.
        """
        pipeline = ModelTrainingPipeline()
        
        X_train = np.random.randn(100, 9)
        y_train = np.random.randint(0, 2, 100)
        pipeline.train_model(X_train, y_train, epochs=2, verbose=0)
        
        X_test = np.random.randn(20, 9)
        y_test = np.random.randint(0, 2, 20)
        
        metrics = pipeline.evaluate_model(X_test, y_test)
        
        assert 'accuracy' in metrics
        assert 'precision' in metrics
        assert 'recall' in metrics
        assert 'f1_score' in metrics
        assert all(0 <= v <= 1 for v in metrics.values())


class TestModelPersistence:
    """Test suite for model saving and loading."""
    
    def test_save_model_creates_files(self):
        """
        Verify save_model creates both model and metadata files.
        """
        pipeline = ModelTrainingPipeline()
        
        X = np.random.randn(100, 9)
        y = np.random.randint(0, 2, 100)
        pipeline.train_model(X, y, epochs=2, verbose=0)
        
        model_path = pipeline.save_model()
        
        assert model_path.exists()
        assert (model_path.parent / "delay_classifier_metadata.json").exists()
    
    def test_save_model_metadata_content(self):
        """
        Verify metadata file contains required information.
        """
        pipeline = ModelTrainingPipeline()
        
        X = np.random.randn(100, 9)
        y = np.random.randint(0, 2, 100)
        pipeline.train_model(X, y, epochs=2, verbose=0)
        
        X_test = np.random.randn(20, 9)
        y_test = np.random.randint(0, 2, 20)
        pipeline.evaluate_model(X_test, y_test)
        
        pipeline.save_model()
        
        metadata_path = pipeline.model_dir / "delay_classifier_metadata.json"
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        
        assert metadata["model_version"] == "1.0"
        assert metadata["n_features"] == 9
        assert len(metadata["feature_names"]) == 9
        assert "created_at" in metadata


class TestPipelineIntegration:
    """Integration tests for complete pipeline."""
    
    @patch('model_training.GTFSDataLoader.load_gtfs_from_json')
    @patch('model_training.GTFSValidator.validate_gtfs_data')
    @patch('model_training.FeatureEngineer.engineer_features')
    def test_pipeline_run_workflow(self, mock_engineer, mock_validate, mock_load):
        """
        Verify complete pipeline execution workflow.
        """
        mock_load.return_value = {
            'stops': pd.DataFrame(),
            'routes': pd.DataFrame(),
            'trips': pd.DataFrame(),
            'stop_times': pd.DataFrame(),
            'calendar': pd.DataFrame()
        }
        
        mock_result = Mock()
        mock_result.is_valid = True
        mock_result.record_count = 100
        mock_validate.return_value = mock_result
        
        mock_feature_set = Mock()
        mock_feature_set.features_array = np.random.randn(100, 9)
        mock_engineer.return_value = mock_feature_set
        
        with tempfile.NamedTemporaryFile(suffix=".json") as f:
            pipeline = ModelTrainingPipeline(data_path=f.name)
            model_path = pipeline.run()
            
            assert model_path.exists()
            mock_load.assert_called_once()
            mock_validate.assert_called_once()
            mock_engineer.assert_called_once()


class TestErrorHandling:
    """Test suite for error handling and edge cases."""
    
    def test_invalid_feature_dimensions(self):
        """
        Verify error handling for mismatched feature dimensions.
        """
        pipeline = ModelTrainingPipeline()
        
        X = np.random.randn(100, 5)
        y = np.random.randint(0, 2, 100)
        
        with pytest.raises(Exception):
            pipeline.train_model(X, y, epochs=1, verbose=0)
    
    def test_empty_datasets(self):
        """
        Verify error handling for empty datasets.
        """
        pipeline = ModelTrainingPipeline()
        
        X = np.array([]).reshape(0, 9)
        y = np.array([])
        
        with pytest.raises(Exception):
            pipeline.train_model(X, y, epochs=1, verbose=0)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
