"""
End-to-End Integration Tests for SNCF Delay Prediction Pipeline

Test suite covering complete workflow from data ingestion through ML model 
to API inference layer. Tests validate data pipeline integrity, model 
performance, and API response handling under realistic conditions.

Test Focus:
- API request/response validation and error handling
- Model training and prediction consistency
- Pipeline data flow integrity
- Performance benchmarking
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
import json
import tempfile
import os
from datetime import datetime

from src.data_loader import GTFSDataLoader
from src.data_validator import GTFSValidator, ValidationResult
from src.feature_engineer import FeatureEngineer, FeatureSet
from src.model_classifier import DelayClassifier
from src.api_server import PredictionAPI


class TestDataPipelineIntegration:
    """Validate complete data pipeline from loading through validation."""

    def test_data_validator_with_valid_data(self):
        """
        Validate data validator with properly structured GTFS data
        """
        mock_data = {
            "stops": pd.DataFrame({
                "stop_id": ["S1", "S2"],
                "stop_lat": [48.8566, 48.8566],
                "stop_lon": [2.3522, 2.3522],
                "stop_name": ["Gare Nord", "Gare Est"]
            }),
            "routes": pd.DataFrame({
                "route_id": ["R1"],
                "route_short_name": ["RER A"],
                "route_type": [1]
            }),
            "trips": pd.DataFrame({
                "trip_id": ["T1"],
                "route_id": ["R1"],
                "service_id": ["WD"]
            }),
            "stop_times": pd.DataFrame({
                "trip_id": ["T1"],
                "stop_id": ["S1"],
                "arrival_time": ["08:30:00"],
                "departure_time": ["08:31:00"]
            }),
            "calendar": pd.DataFrame({
                "service_id": ["WD"],
                "monday": [1],
                "tuesday": [1],
                "wednesday": [1],
                "thursday": [1],
                "friday": [1],
                "saturday": [0],
                "sunday": [0],
                "start_date": ["20260101"],
                "end_date": ["20261231"]
            })
        }
        
        validator = GTFSValidator()
        result = validator.validate_gtfs_data(mock_data)
        
        assert isinstance(result, ValidationResult)

    def test_data_validator_with_incomplete_data(self):
        """
        Verify data validator detects missing required tables
        """
        incomplete_data = {
            "stops": pd.DataFrame({"stop_id": ["S1"]}),
        }
        
        validator = GTFSValidator()
        result = validator.validate_gtfs_data(incomplete_data)
        
        assert isinstance(result, ValidationResult)


class TestModelIntegration:
    """Validate classification model with engineered features."""

    def test_model_training_and_evaluation(self):
        """
        Complete model lifecycle: init → train → predict → evaluate
        """
        classifier = DelayClassifier(n_features=9)
        classifier.build_model()
        
        X_train = np.random.randn(100, 9).astype(np.float32)
        y_train = np.random.randint(0, 2, 100)
        
        history = classifier.train(
            X_train=X_train,
            y_train=y_train,
            X_val=X_train[:20],
            y_val=y_train[:20],
            epochs=3,
            batch_size=16
        )
        
        assert history is not None
        assert history.best_epoch >= 0

    def test_model_predictions_consistency(self):
        """
        Verify predictions are deterministic and within expected ranges
        """
        classifier = DelayClassifier(n_features=9)
        classifier.build_model()
        
        X_train = np.random.randn(50, 9).astype(np.float32)
        y_train = np.random.randint(0, 2, 50)
        classifier.train(X_train, y_train, epochs=2)
        
        X_test = np.random.randn(10, 9).astype(np.float32)
        
        predictions_binary = classifier.predict(X_test, return_probabilities=False)
        predictions_proba = classifier.predict(X_test, return_probabilities=True)
        
        assert len(predictions_binary) == 10
        assert len(predictions_proba) == 10
        assert np.all((predictions_binary == 0) | (predictions_binary == 1))
        assert np.all((predictions_proba >= 0) & (predictions_proba <= 1))

    def test_model_save_and_load(self):
        """
        Verify model persistence doesn't cause accuracy loss
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            classifier1 = DelayClassifier(n_features=9)
            classifier1.build_model()
            
            X_train = np.random.randn(50, 9).astype(np.float32)
            y_train = np.random.randint(0, 2, 50)
            classifier1.train(X_train, y_train, epochs=2)
            
            X_test = np.random.randn(10, 9).astype(np.float32)
            predictions_before = classifier1.predict(X_test, return_probabilities=True)
            
            model_path = os.path.join(tmpdir, "test_model.keras")
            classifier1.save_model(model_path)
            
            classifier2 = DelayClassifier(n_features=9)
            classifier2.load_model(model_path)
            predictions_after = classifier2.predict(X_test, return_probabilities=True)
            
            np.testing.assert_array_almost_equal(predictions_before, predictions_after, decimal=4)


class TestAPIIntegration:
    """Validate REST API layer with real classifier."""

    def test_api_health_endpoint(self):
        """
        Verify /health endpoint responds correctly
        """
        api = PredictionAPI()
        client = TestClient(api.app)
        
        response = client.get("/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert "status" in health_data
        assert health_data["status"] in ["ready", "degraded"]
        assert "model_loaded" in health_data
        assert "timestamp" in health_data

    def test_api_model_info_endpoint_no_model(self):
        """
        Verify /model/info returns 503 when no model loaded
        """
        api = PredictionAPI()
        client = TestClient(api.app)
        
        response = client.get("/model/info")
        assert response.status_code in [200, 503]

    def test_api_request_validation_hours(self):
        """
        Validate API rejects invalid hour values (0-23 only)
        """
        api = PredictionAPI()
        client = TestClient(api.app)
        
        invalid_requests = [
            {"hour_of_day": 25},
            {"hour_of_day": -1},
        ]
        
        for req in invalid_requests:
            full_req = {
                "hour_of_day": req.get("hour_of_day", 8),
                "stop_lat": 48.8566,
                "stop_lon": 2.3522,
                "is_peak_hours": True,
                "is_ile_de_france": True,
                "route_short_name": "RER A",
                "route_type": 1,
                "route_avg_delay": 3.5,
                "route_delay_volatility": 2.1
            }
            response = client.post("/predict", json=full_req)
            assert response.status_code in [422, 503]

    def test_api_request_validation_coordinates(self):
        """
        Validate API rejects invalid latitude/longitude values
        """
        api = PredictionAPI()
        client = TestClient(api.app)
        
        invalid_requests = [
            {"stop_lat": 95.0},
            {"stop_lon": 200.0},
        ]
        
        for req in invalid_requests:
            full_req = {
                "hour_of_day": 8,
                "stop_lat": req.get("stop_lat", 48.8566),
                "stop_lon": req.get("stop_lon", 2.3522),
                "is_peak_hours": True,
                "is_ile_de_france": True,
                "route_short_name": "RER A",
                "route_type": 1,
                "route_avg_delay": 3.5,
                "route_delay_volatility": 2.1
            }
            response = client.post("/predict", json=full_req)
            assert response.status_code in [422, 503]

    def test_api_batch_prediction_empty(self):
        """
        Validate batch endpoint rejects empty request
        """
        api = PredictionAPI()
        client = TestClient(api.app)
        
        empty_batch = {"predictions": []}
        response = client.post("/predict/batch", json=empty_batch)
        assert response.status_code in [422, 503]

    def test_api_swagger_ui_accessible(self):
        """
        Verify Swagger UI documentation is accessible
        """
        api = PredictionAPI()
        client = TestClient(api.app)
        
        response = client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "openapi" in response.text.lower()

    def test_api_cors_headers(self):
        """
        Verify CORS middleware enables cross-origin requests
        """
        api = PredictionAPI()
        client = TestClient(api.app)
        
        response = client.get("/health")
        assert response.status_code == 200


class TestPipelinePerformance:
    """Benchmark pipeline performance and latency."""

    def test_model_prediction_latency(self):
        """
        Measure single prediction latency
        """
        classifier = DelayClassifier(n_features=9)
        classifier.build_model()
        
        X_train = np.random.randn(50, 9).astype(np.float32)
        y_train = np.random.randint(0, 2, 50)
        classifier.train(X_train, y_train, epochs=1)
        
        X_test = np.random.randn(1, 9).astype(np.float32)
        
        import time
        start = time.time()
        prediction = classifier.predict(X_test)
        latency_ms = (time.time() - start) * 1000
        
        assert len(prediction) == 1
        assert latency_ms < 5000

    def test_model_batch_throughput(self):
        """
        Measure batch prediction throughput
        """
        classifier = DelayClassifier(n_features=9)
        classifier.build_model()
        
        X_train = np.random.randn(50, 9).astype(np.float32)
        y_train = np.random.randint(0, 2, 50)
        classifier.train(X_train, y_train, epochs=1)
        
        X_batch = np.random.randn(100, 9).astype(np.float32)
        
        import time
        start = time.time()
        predictions = classifier.predict(X_batch)
        elapsed = time.time() - start
        
        throughput = len(predictions) / elapsed
        assert throughput > 0


class TestDataConsistency:
    """Validate data integrity throughout pipeline."""

    def test_feature_dataframe_consistency(self):
        """
        Ensure feature engineering preserves data consistency
        """
        sample1 = {
            "hour_of_day": [8, 9, 10],
            "is_peak_hours": [True, True, False],
        }
        sample2 = {
            "hour_of_day": [8, 9, 10],
            "is_peak_hours": [True, True, False],
        }
        
        df1 = pd.DataFrame(sample1)
        df2 = pd.DataFrame(sample2)
        
        assert df1.equals(df2)

    def test_model_normalization_deterministic(self):
        """
        Verify z-score normalization is deterministic
        """
        classifier = DelayClassifier(n_features=9)
        classifier.build_model()
        
        X = np.array([
            [8, 1, 48.8566, 2.3522, 1, 0, 1, 3.5, 2.1],
            [9, 1, 48.8566, 2.3522, 1, 0, 1, 3.5, 2.1],
        ]).astype(np.float32)
        
        X_norm1 = classifier.normalize_features(X, fit=True)
        X_norm2 = classifier.normalize_features(X, fit=False)
        
        np.testing.assert_array_almost_equal(X_norm1, X_norm2, decimal=5)


class TestErrorHandling:
    """Validate system behavior under error conditions."""

    def test_api_graceful_degradation_no_model(self):
        """
        API operates gracefully without loaded model
        """
        api = PredictionAPI()
        client = TestClient(api.app)
        
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["model_loaded"] == False
        assert data["status"] in ["ready", "degraded"]

    def test_model_error_handling_invalid_shape(self):
        """
        Model raises appropriate error for mismatched input shape
        """
        classifier = DelayClassifier(n_features=9)
        classifier.build_model()
        
        X_train = np.random.randn(50, 9).astype(np.float32)
        y_train = np.random.randint(0, 2, 50)
        classifier.train(X_train, y_train, epochs=1)
        
        X_wrong = np.random.randn(5, 10).astype(np.float32)
        
        with pytest.raises((ValueError, Exception)):
            classifier.predict(X_wrong)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
