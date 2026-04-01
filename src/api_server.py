"""
FastAPI server for SNCF delay prediction inference.

Provides REST endpoints for model serving:
- POST /predict - Single/batch prediction with engineered features
- GET /health - Server health and readiness status
- GET /model/info - Model metadata and performance metrics
- GET /docs - Interactive API documentation (Swagger UI)

Implements proper error handling, request validation (Pydantic),
and CORS support for cross-origin requests.
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Any
import numpy as np
import pandas as pd
import logging
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from model_classifier import DelayClassifier


"""
Configure logging for API operations.
"""
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PredictionRequest(BaseModel):
    """
    Request body for single prediction.
    
    Attributes:
        hour_of_day: Hour of day (0-23).
        is_peak_hours: Boolean indicating peak hours.
        route_avg_delay: Average delay for this route (minutes).
        route_delay_volatility: Standard deviation of delays.
        is_ile_de_france: Boolean for Île-de-France region.
        stop_lat: Stop latitude coordinate.
        stop_lon: Stop longitude coordinate.
        route_type: Route type identifier (0-9).
        service_id: GTFS service identifier.
        trip_duration: Expected trip duration (minutes).
    """
    hour_of_day: int = Field(..., ge=0, le=23, description="Hour of day (0-23)")
    is_peak_hours: bool = Field(..., description="Is peak hours")
    route_avg_delay: float = Field(..., ge=0, description="Average route delay (minutes)")
    route_delay_volatility: float = Field(..., ge=0, description="Route delay volatility")
    is_ile_de_france: bool = Field(..., description="Is in Île-de-France region")
    stop_lat: float = Field(..., ge=-90, le=90, description="Stop latitude")
    stop_lon: float = Field(..., ge=-180, le=180, description="Stop longitude")
    route_type: int = Field(..., ge=0, le=9, description="Route type")
    service_id: int = Field(..., ge=0, description="Service ID")
    trip_duration: float = Field(..., ge=0, description="Trip duration (minutes)")

    @validator('route_avg_delay', 'route_delay_volatility', 'trip_duration')
    def validate_non_negative(cls, v):
        """
        Validate non-negative numeric fields.
        """
        if v < 0:
            raise ValueError('Value must be non-negative')
        return v


class BatchPredictionRequest(BaseModel):
    """
    Request body for batch predictions.
    
    Attributes:
        predictions: List of prediction requests.
    """
    predictions: List[PredictionRequest] = Field(..., min_items=1, max_items=1000)


class PredictionResponse(BaseModel):
    """
    Response body for single prediction.
    
    Attributes:
        prediction: Binary prediction (0 or 1).
        probability: Probability score (0.0 to 1.0).
        delay_category: Categorical delay label (LOW, MEDIUM, HIGH).
        confidence: Confidence level (LOW, MEDIUM, HIGH).
    """
    prediction: int = Field(..., description="Binary prediction: 0=No delay, 1=Delay")
    probability: float = Field(..., ge=0.0, le=1.0, description="Probability score")
    delay_category: str = Field(..., description="Delay category: LOW, MEDIUM, HIGH")
    confidence: str = Field(..., description="Confidence: LOW, MEDIUM, HIGH")


class BatchPredictionResponse(BaseModel):
    """
    Response body for batch predictions.
    
    Attributes:
        predictions: List of prediction responses.
        total: Total number of predictions.
        errors: Number of errors (if any).
    """
    predictions: List[PredictionResponse]
    total: int
    errors: int = 0


class HealthResponse(BaseModel):
    """
    Response body for health check endpoint.
    
    Attributes:
        status: Server status (ready, degraded, unavailable).
        model_loaded: Whether model is loaded.
        model_version: Version identifier of loaded model.
        timestamp: Server timestamp.
    """
    status: str = Field(..., description="Server status")
    model_loaded: bool = Field(..., description="Is model loaded")
    model_version: str = Field(..., description="Model version")
    timestamp: str = Field(..., description="Server timestamp")


class ModelInfoResponse(BaseModel):
    """
    Response body for model info endpoint.
    
    Attributes:
        model_version: Version identifier.
        model_type: Model architecture.
        n_features: Number of input features.
        training_date: Training date.
        last_updated: Last update timestamp.
        performance_metrics: Dictionary of performance metrics.
    """
    model_version: str = Field(..., description="Model version")
    model_type: str = Field(..., description="Model type")
    n_features: int = Field(..., description="Number of features")
    training_date: Optional[str] = Field(None, description="Training date")
    last_updated: str = Field(..., description="Last update timestamp")
    performance_metrics: Dict[str, Any] = Field(..., description="Performance metrics")


class PredictionAPI:
    """
    FastAPI wrapper for DelayClassifier model.
    
    Manages REST API, request routing, model loading/inference,
    validation, and error handling.
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize PredictionAPI server.
        
        Parameters:
            model_path: Path to trained model (without extension).
              If None, model will not be loaded initially.
        
        Returns:
            None
        """
        self.app = FastAPI(
            title="SNCF Delay Prediction API",
            description="Binary classification API for train delay prediction",
            version="1.0.0"
        )
        self.classifier: Optional[DelayClassifier] = None
        self.model_path = model_path
        self.model_loaded = False
        self.model_version = "v1.0"
        self.performance_metrics = {
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1_score": 0.0
        }
        
        """
        Add CORS middleware for cross-origin requests.
        """
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        """
        Register routes.
        """
        self._setup_routes()
        
        """
        Load model if path provided.
        """
        if model_path:
            self._load_model(model_path)

    def _setup_routes(self) -> None:
        """
        Setup FastAPI routes and handlers.
        
        Returns:
            None
        """
        @self.app.get("/health", response_model=HealthResponse)
        def health_check():
            """
            Health check endpoint.
            
            Returns:
                HealthResponse with server status and model info.
            """
            return HealthResponse(
                status="ready" if self.model_loaded else "degraded",
                model_loaded=self.model_loaded,
                model_version=self.model_version,
                timestamp=datetime.utcnow().isoformat()
            )

        @self.app.get("/model/info", response_model=ModelInfoResponse)
        def model_info():
            """
            Get model metadata and performance information.
            
            Returns:
                ModelInfoResponse with model details.
            
            Raises:
                HTTPException 503 if model not loaded.
            """
            if not self.model_loaded:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Model not loaded"
                )
            
            n_features = self.classifier.n_features if self.classifier else 0
            return ModelInfoResponse(
                model_version=self.model_version,
                model_type="DelayClassifier (TensorFlow/Keras)",
                n_features=n_features,
                training_date="2026-03-31",
                last_updated=datetime.utcnow().isoformat(),
                performance_metrics=self.performance_metrics
            )

        @self.app.post("/predict", response_model=PredictionResponse)
        def predict(request: PredictionRequest):
            """
            Make single prediction.
            
            Parameters:
                request: PredictionRequest with engineered features.
            
            Returns:
                PredictionResponse with prediction and probability.
            
            Raises:
                HTTPException 503 if model not loaded.
                HTTPException 400 if request validation fails.
            """
            if not self.model_loaded:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Model not loaded"
                )
            
            try:
                prediction = self._predict_single(request)
                return prediction
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
            except Exception as e:
                logger.error(f"Prediction error: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Prediction failed"
                )

        @self.app.post("/predict/batch", response_model=BatchPredictionResponse)
        def predict_batch(request: BatchPredictionRequest):
            """
            Make batch predictions.
            
            Parameters:
                request: BatchPredictionRequest with list of requests.
            
            Returns:
                BatchPredictionResponse with list of predictions.
            
            Raises:
                HTTPException 503 if model not loaded.
                HTTPException 400 if request validation fails.
            """
            if not self.model_loaded:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Model not loaded"
                )
            
            predictions = []
            errors = 0
            
            for pred_request in request.predictions:
                try:
                    prediction = self._predict_single(pred_request)
                    predictions.append(prediction)
                except Exception as e:
                    logger.warning(f"Batch prediction error: {str(e)}")
                    errors += 1
            
            return BatchPredictionResponse(
                predictions=predictions,
                total=len(request.predictions),
                errors=errors
            )

    def _predict_single(self, request: PredictionRequest) -> PredictionResponse:
        """
        Make single prediction from request.
        
        Parameters:
            request: PredictionRequest with features.
        
        Returns:
            PredictionResponse with prediction and metadata.
        
        Raises:
            ValueError if features invalid.
        """
        """
        Prepare feature array from request.
        """
        features = np.array([[
            request.hour_of_day,
            float(request.is_peak_hours),
            request.route_avg_delay,
            request.route_delay_volatility,
            float(request.is_ile_de_france),
            request.stop_lat,
            request.stop_lon,
            request.route_type,
            request.service_id,
            request.trip_duration
        ]])
        
        """
        Get prediction and probability from model.
        """
        pred_binary = self.classifier.predict(features, return_probabilities=False)[0]
        pred_prob = self.classifier.predict(features, return_probabilities=True)[0]
        
        """
        Categorize delay and confidence.
        """
        if pred_prob < 0.33:
            delay_category = "LOW"
            confidence = "HIGH"
        elif pred_prob < 0.67:
            delay_category = "MEDIUM"
            confidence = "MEDIUM"
        else:
            delay_category = "HIGH"
            confidence = "HIGH" if pred_prob > 0.8 else "MEDIUM"
        
        return PredictionResponse(
            prediction=int(pred_binary),
            probability=float(pred_prob),
            delay_category=delay_category,
            confidence=confidence
        )

    def _load_model(self, model_path: str) -> None:
        """
        Load trained model from disk.
        
        Parameters:
            model_path: Path to model (without extension).
        
        Returns:
            None
        """
        try:
            self.classifier = DelayClassifier()
            self.classifier.load_model(model_path)
            self.model_loaded = True
            logger.info(f"Model loaded successfully from {model_path}")
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            self.model_loaded = False

    def get_app(self) -> FastAPI:
        """
        Get FastAPI application instance.
        
        Returns:
            FastAPI application.
        """
        return self.app


"""
Create API instance and expose app.
"""
api = PredictionAPI()
app = api.get_app()


"""
Store api instance as attribute on app for testing access.
"""
app.api_instance = api


if __name__ == "__main__":
    import uvicorn
    
    """
    Run development server on port 5000.
    """
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5000,
        log_level="info"
    )
