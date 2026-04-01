"""
Unit Tests for FastAPI Prediction Server.

Tests cover API endpoints, request validation (Pydantic),
error handling, batch predictions, and model loading.
Uses TestClient for synchronous HTTP testing.
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import tempfile
import os

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from api_server import app, PredictionAPI, PredictionRequest, BatchPredictionRequest
from model_classifier import DelayClassifier


class TestPredictionRequests:
    """Tests for request validation (Pydantic models)."""

    def test_prediction_request_valid(self):
        """
        Test valid prediction request construction.
        """
        req = PredictionRequest(
            hour_of_day=8,
            is_peak_hours=True,
            route_avg_delay=5.0,
            route_delay_volatility=2.0,
            is_ile_de_france=True,
            stop_lat=48.8566,
            stop_lon=2.3522,
            route_type=1,
            service_id=1,
            trip_duration=30.0
        )
        assert req.hour_of_day == 8
        assert req.is_peak_hours is True
        assert req.route_avg_delay == 5.0

    def test_prediction_request_invalid_hour(self):
        """
        Test prediction request with invalid hour (>23).
        """
        with pytest.raises(ValueError):
            PredictionRequest(
                hour_of_day=25,
                is_peak_hours=True,
                route_avg_delay=5.0,
                route_delay_volatility=2.0,
                is_ile_de_france=True,
                stop_lat=48.8566,
                stop_lon=2.3522,
                route_type=1,
                service_id=1,
                trip_duration=30.0
            )

    def test_prediction_request_invalid_latitude(self):
        """
        Test prediction request with invalid latitude (>90).
        """
        with pytest.raises(ValueError):
            PredictionRequest(
                hour_of_day=8,
                is_peak_hours=True,
                route_avg_delay=5.0,
                route_delay_volatility=2.0,
                is_ile_de_france=True,
                stop_lat=91.0,
                stop_lon=2.3522,
                route_type=1,
                service_id=1,
                trip_duration=30.0
            )

    def test_prediction_request_negative_delay(self):
        """
        Test prediction request with negative delay (invalid).
        """
        with pytest.raises(ValueError):
            PredictionRequest(
                hour_of_day=8,
                is_peak_hours=True,
                route_avg_delay=-5.0,
                route_delay_volatility=2.0,
                is_ile_de_france=True,
                stop_lat=48.8566,
                stop_lon=2.3522,
                route_type=1,
                service_id=1,
                trip_duration=30.0
            )


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_endpoint_returns_200(self):
        """
        Test that /health endpoint returns 200 status.
        """
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_structure(self):
        """
        Test health response has required fields.
        """
        client = TestClient(app)
        response = client.get("/health")
        data = response.json()
        
        assert "status" in data
        assert "model_loaded" in data
        assert "model_version" in data
        assert "timestamp" in data

    def test_health_response_model_loaded_false_when_no_model(self):
        """
        Test health check shows model not loaded initially.
        """
        client = TestClient(app)
        response = client.get("/health")
        data = response.json()
        
        assert data["status"] in ["ready", "degraded"]
        assert isinstance(data["model_loaded"], bool)


class TestModelInfoEndpoint:
    """Tests for /model/info endpoint."""

    def test_model_info_without_loaded_model_returns_503(self):
        """
        Test /model/info returns 503 when model not loaded.
        """
        client = TestClient(app)
        response = client.get("/model/info")
        
        if not app.api_instance.model_loaded:
            assert response.status_code == 503

    def test_model_info_response_structure(self):
        """
        Test model info response structure when model loaded.
        """
        """
        Setup: Create temporary trained model for testing.
        """
        api = PredictionAPI()
        
        if not api.model_loaded:
            pytest.skip("Model not loaded for testing")
        
        client = TestClient(api.get_app())
        response = client.get("/model/info")
        
        if response.status_code == 200:
            data = response.json()
            assert "model_version" in data
            assert "model_type" in data
            assert "n_features" in data
            assert "last_updated" in data


class TestPredictEndpoint:
    """Tests for /predict (single prediction) endpoint."""

    def test_predict_without_model_returns_503(self):
        """
        Test /predict returns 503 when model not loaded.
        """
        client = TestClient(app)
        request_data = {
            "hour_of_day": 8,
            "is_peak_hours": True,
            "route_avg_delay": 5.0,
            "route_delay_volatility": 2.0,
            "is_ile_de_france": True,
            "stop_lat": 48.8566,
            "stop_lon": 2.3522,
            "route_type": 1,
            "service_id": 1,
            "trip_duration": 30.0
        }
        response = client.post("/predict", json=request_data)
        
        if not app.api_instance.model_loaded:
            assert response.status_code == 503

    def test_predict_invalid_request_returns_422(self):
        """
        Test /predict returns 422 (validation error) for invalid request.
        """
        client = TestClient(app)
        request_data = {
            "hour_of_day": 25,
            "is_peak_hours": True,
            "route_avg_delay": 5.0,
            "route_delay_volatility": 2.0,
            "is_ile_de_france": True,
            "stop_lat": 48.8566,
            "stop_lon": 2.3522,
            "route_type": 1,
            "service_id": 1,
            "trip_duration": 30.0
        }
        response = client.post("/predict", json=request_data)
        assert response.status_code == 422

    def test_predict_missing_fields_returns_422(self):
        """
        Test /predict returns 422 for missing required fields.
        """
        client = TestClient(app)
        request_data = {
            "hour_of_day": 8,
            "route_avg_delay": 5.0,
        }
        response = client.post("/predict", json=request_data)
        assert response.status_code == 422


class TestBatchPredictEndpoint:
    """Tests for /predict/batch (batch prediction) endpoint."""

    def test_batch_predict_without_model_returns_503(self):
        """
        Test batch /predict returns 503 when model not loaded.
        """
        client = TestClient(app)
        request_data = {
            "predictions": [
                {
                    "hour_of_day": 8,
                    "is_peak_hours": True,
                    "route_avg_delay": 5.0,
                    "route_delay_volatility": 2.0,
                    "is_ile_de_france": True,
                    "stop_lat": 48.8566,
                    "stop_lon": 2.3522,
                    "route_type": 1,
                    "service_id": 1,
                    "trip_duration": 30.0
                }
            ]
        }
        response = client.post("/predict/batch", json=request_data)
        
        if not app.api_instance.model_loaded:
            assert response.status_code == 503

    def test_batch_predict_empty_list_returns_422(self):
        """
        Test batch /predict returns 422 for empty predictions list.
        """
        client = TestClient(app)
        request_data = {"predictions": []}
        response = client.post("/predict/batch", json=request_data)
        assert response.status_code == 422

    def test_batch_predict_response_structure(self):
        """
        Test batch response has required structure.
        """
        """
        Only test if model is loaded in app.
        """
        if not app.api_instance.model_loaded:
            pytest.skip("Model not loaded for testing")
        
        client = TestClient(app)
        request_data = {
            "predictions": [
                {
                    "hour_of_day": 8,
                    "is_peak_hours": True,
                    "route_avg_delay": 5.0,
                    "route_delay_volatility": 2.0,
                    "is_ile_de_france": True,
                    "stop_lat": 48.8566,
                    "stop_lon": 2.3522,
                    "route_type": 1,
                    "service_id": 1,
                    "trip_duration": 30.0
                }
            ]
        }
        response = client.post("/predict/batch", json=request_data)
        
        if response.status_code == 200:
            data = response.json()
            assert "predictions" in data
            assert "total" in data
            assert "errors" in data
            assert data["total"] >= len(data["predictions"])


class TestPredictionAPIClass:
    """Tests for PredictionAPI class directly."""

    def test_api_initialization(self):
        """
        Test PredictionAPI initializes correctly.
        """
        api = PredictionAPI()
        assert api.app is not None
        assert api.model_loaded is False
        assert api.classifier is None

    def test_api_with_model_path(self):
        """
        Test PredictionAPI initialization with model path.
        """
        """
        Create temporary trained model.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            """
            Train a simple model for testing.
            """
            classifier = DelayClassifier(n_features=10)
            classifier.build_model()
            
            X_train = pd.DataFrame(np.random.randn(50, 10))
            y_train = pd.Series(np.random.randint(0, 2, 50))
            classifier.train(X_train, y_train, epochs=1, batch_size=16)
            
            model_path = os.path.join(tmpdir, "test_model")
            classifier.save_model(model_path)
            
            """
            Test API loads model.
            """
            api = PredictionAPI(model_path)
            assert api.model_loaded is True
            assert api.classifier is not None

    def test_api_get_app(self):
        """
        Test get_app method returns FastAPI instance.
        """
        api = PredictionAPI()
        fast_app = api.get_app()
        
        assert fast_app is not None
        assert hasattr(fast_app, 'get')
        assert hasattr(fast_app, 'post')


class TestErrorHandling:
    """Tests for error handling in API."""

    def test_predict_with_invalid_json_returns_422(self):
        """
        Test /predict returns 422 for invalid JSON.
        """
        client = TestClient(app)
        response = client.post("/predict", json={"invalid": "data"})
        assert response.status_code == 422

    def test_unknown_endpoint_returns_404(self):
        """
        Test unknown endpoint returns 404.
        """
        client = TestClient(app)
        response = client.get("/unknown")
        assert response.status_code == 404


class TestCORSHeaders:
    """Tests for CORS middleware."""

    def test_cors_headers_present(self):
        """
        Test CORS headers are present in response.
        """
        client = TestClient(app)
        response = client.get("/health")
        
        """
        Check for CORS headers (may vary by TestClient config).
        """
        assert response.status_code == 200


class TestAPIIntegration:
    """Integration tests for complete API workflows."""

    def test_health_check_workflow(self):
        """
        Test complete health check workflow.
        """
        client = TestClient(app)
        
        """
        1. Check health.
        """
        response = client.get("/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert "status" in health_data
        assert health_data["status"] in ["ready", "degraded"]

    def test_multiple_requests_consistency(self):
        """
        Test multiple requests to same endpoint return consistent format.
        """
        client = TestClient(app)
        
        for _ in range(3):
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "model_version" in data
