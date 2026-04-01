"""
Model Training Pipeline for SNCF Delay Prediction.

Orchestrates the complete training workflow:
- Load GTFS data from local/remote sources
- Validate data quality
- Engineer features from raw GTFS records
- Train DelayClassifier with optimal hyperparameters
- Evaluate model performance
- Persist trained model to disk
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
from typing import Tuple, Dict
import json

sys.path.insert(0, str(Path(__file__).parent / "src"))

from data_loader import GTFSDataLoader
from data_validator import GTFSValidator
from feature_engineer import FeatureEngineer
from model_classifier import DelayClassifier


class ModelTrainingPipeline:
    """
    Complete machine learning pipeline for SNCF delay prediction model training.
    
    Handles data loading, validation, feature engineering, model training,
    and persistence orchestration.
    """
    
    def __init__(self, data_path: str = "data/horaires-sncf.json"):
        """
        Initialize training pipeline with data source.
        
        Args:
            data_path: Path to GTFS data file (JSON or ZIP).
        """
        self.data_path = Path(data_path)
        self.model_dir = Path(__file__).parent.parent / "models"
        self.model_dir.mkdir(exist_ok=True)
        
        self.loader = GTFSDataLoader()
        self.validator = GTFSValidator()
        self.engineer = FeatureEngineer()
        self.classifier = DelayClassifier(n_features=9)
        
        self.training_history = {}
        self.evaluation_metrics = {}
    
    def load_data(self) -> Dict:
        """
        Load GTFS data from configured path.
        
        Returns:
            Dict: GTFS DataFrames (stops, routes, trips, stop_times, calendar).
        
        Raises:
            FileNotFoundError: If data source not found.
            ValueError: If data loading fails.
        """
        print(f"📥 Loading GTFS data from {self.data_path}...")
        
        if not self.data_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.data_path}")
        
        if self.data_path.suffix == ".json":
            gtfs_data = self.loader.load_gtfs_from_json(str(self.data_path))
        elif self.data_path.suffix == ".zip":
            gtfs_data = self.loader.load_gtfs_from_zip(str(self.data_path))
        else:
            raise ValueError(f"Unsupported file format: {self.data_path.suffix}")
        
        print(f"✅ Loaded {len(gtfs_data)} GTFS dataframes")
        return gtfs_data
    
    def validate_data(self, gtfs_data: Dict) -> bool:
        """
        Validate loaded GTFS data quality.
        
        Args:
            gtfs_data: GTFS DataFrames dict.
        
        Returns:
            bool: True if validation passes (with warnings allowed).
        
        Raises:
            RuntimeError: If validation fails critically.
        """
        print("🔍 Validating GTFS data...")
        
        result = self.validator.validate_gtfs_data(gtfs_data, strict=False)
        
        if not result.is_valid:
            raise RuntimeError(f"Data validation failed: {result.errors}")
        
        print(f"✅ Validation passed ({result.record_count} records)")
        return True
    
    def engineer_features(self, gtfs_data: Dict) -> np.ndarray:
        """
        Extract and engineer features from GTFS data.
        
        Args:
            gtfs_data: GTFS DataFrames dict.
        
        Returns:
            np.ndarray: Feature matrix (n_samples, n_features=9).
        """
        print("🔧 Engineering features...")
        
        feature_set = self.engineer.engineer_features(gtfs_data)
        features = feature_set.features_array
        
        print(f"✅ Engineered {features.shape[0]} samples with {features.shape[1]} features")
        return features
    
    def generate_synthetic_labels(self, n_samples: int) -> np.ndarray:
        """
        Generate synthetic delay labels for training (0=on-time, 1=delayed).
        
        In production, these would come from actual historical delay data.
        Uses realistic distribution: ~20% delayed, ~80% on-time.
        
        Args:
            n_samples: Number of samples to generate labels for.
        
        Returns:
            np.ndarray: Binary labels (0 or 1).
        """
        np.random.seed(42)
        labels = np.random.binomial(n=1, p=0.2, size=n_samples)
        return labels
    
    def train_model(
        self,
        X: np.ndarray,
        y: np.ndarray,
        epochs: int = 20,
        batch_size: int = 32,
        validation_split: float = 0.2
    ) -> Dict:
        """
        Train DelayClassifier on feature matrix and labels.
        
        Args:
            X: Feature matrix (n_samples, n_features).
            y: Binary labels (n_samples,).
            epochs: Number of training epochs.
            batch_size: Training batch size.
            validation_split: Fraction for validation set.
        
        Returns:
            Dict: Training history with metrics.
        """
        print(f"🏋️ Training model ({len(X)} samples, {epochs} epochs)...")
        
        history = self.classifier.train(
            X, y,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            verbose=1
        )
        
        self.training_history = history.metrics
        print(f"✅ Training complete")
        print(f"   Final accuracy: {history.metrics['accuracy'][-1]:.2%}")
        
        return history.metrics
    
    def evaluate_model(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict:
        """
        Evaluate trained model on test set.
        
        Args:
            X_test: Test feature matrix.
            y_test: Test labels.
        
        Returns:
            Dict: Evaluation metrics.
        """
        print("📊 Evaluating model on test set...")
        
        predictions = self.classifier.predict(X_test)
        probabilities = self.classifier.predict_proba(X_test)
        
        metrics = self.classifier.evaluate(X_test, y_test)
        
        self.evaluation_metrics = metrics.metrics
        
        print(f"✅ Evaluation complete")
        print(f"   Accuracy: {metrics.metrics['accuracy']:.2%}")
        print(f"   Precision: {metrics.metrics['precision']:.2%}")
        print(f"   Recall: {metrics.metrics['recall']:.2%}")
        print(f"   F1-Score: {metrics.metrics['f1_score']:.2%}")
        
        return metrics.metrics
    
    def save_model(self) -> Path:
        """
        Save trained model to disk with metadata.
        
        Saves:
        - Model weights: models/delay_classifier.keras
        - Metadata: models/delay_classifier_metadata.json
        
        Returns:
            Path: Path to saved model.
        """
        print("💾 Saving model...")
        
        model_path = self.model_dir / "delay_classifier.keras"
        metadata_path = self.model_dir / "delay_classifier_metadata.json"
        
        self.classifier.save_model(str(model_path))
        
        metadata = {
            "model_version": "1.0",
            "n_features": 9,
            "feature_names": [
                "hour_of_day", "stop_lat", "stop_lon", "num_stops",
                "day_of_week", "vehicle_type", "avg_delay",
                "weather_impact", "other"
            ],
            "training_metrics": self.training_history,
            "evaluation_metrics": self.evaluation_metrics,
            "created_at": pd.Timestamp.now().isoformat()
        }
        
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✅ Model saved to {model_path}")
        print(f"   Metadata saved to {metadata_path}")
        
        return model_path
    
    def run(self) -> Path:
        """
        Execute complete training pipeline.
        
        Returns:
            Path: Path to saved trained model.
        """
        print("\n" + "="*60)
        print("🚆 SNCF Delay Prediction - Model Training Pipeline")
        print("="*60 + "\n")
        
        gtfs_data = self.load_data()
        self.validate_data(gtfs_data)
        features = self.engineer_features(gtfs_data)
        labels = self.generate_synthetic_labels(len(features))
        
        X_train, X_test = features[:int(0.8*len(features))], features[int(0.8*len(features)):]
        y_train, y_test = labels[:int(0.8*len(labels))], labels[int(0.8*len(labels)):]
        
        self.train_model(X_train, y_train, epochs=20)
        self.evaluate_model(X_test, y_test)
        model_path = self.save_model()
        
        print("\n" + "="*60)
        print("✅ Pipeline Complete!")
        print("="*60 + "\n")
        
        return model_path


def main():
    """
    Main entry point for model training.
    
    Executes complete training pipeline and handles errors gracefully.
    """
    try:
        pipeline = ModelTrainingPipeline(data_path="data/horaires-sncf.json")
        model_path = pipeline.run()
        print(f"\n✨ Model ready at: {model_path}")
    
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("   Make sure data/horaires-sncf.json exists")
        sys.exit(1)
    
    except Exception as e:
        print(f"❌ Training failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
