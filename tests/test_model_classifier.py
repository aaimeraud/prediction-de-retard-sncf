"""
Unit Tests for DelayClassifier Model.

Tests cover model initialization, training, prediction, evaluation,
and persistence (save/load) in a Colab-compatible environment.
Uses synthetic data to simulate GTFS features.
"""

import pytest
import numpy as np
import pandas as pd
import tempfile
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from model_classifier import DelayClassifier, TrainingHistory, EvaluationMetrics


class TestDelayClassifierInitialization:
    """Tests for model initialization."""

    def test_init_default_parameters(self):
        """
        Test initialization with default parameters.
        """
        classifier = DelayClassifier()
        assert classifier.n_features == 15
        assert classifier.random_state == 42
        assert classifier.model is None
        assert classifier.training_history is None

    def test_init_custom_parameters(self):
        """
        Test initialization with custom parameters.
        """
        classifier = DelayClassifier(n_features=20, random_state=123)
        assert classifier.n_features == 20
        assert classifier.random_state == 123

    def test_build_model_creates_keras_model(self):
        """
        Test that build_model creates a valid Keras model.
        """
        classifier = DelayClassifier(n_features=15)
        model = classifier.build_model()
        assert model is not None
        assert classifier.model is not None
        assert model.input_shape == (None, 15)

    def test_model_architecture_has_correct_layers(self):
        """
        Test that model has expected architecture (Dense, BatchNorm, Dropout).
        """
        classifier = DelayClassifier(n_features=10)
        model = classifier.build_model()
        assert len(model.layers) > 0
        layer_names = [type(layer).__name__ for layer in model.layers]
        assert 'Dense' in layer_names
        assert 'BatchNormalization' in layer_names
        assert 'Dropout' in layer_names


class TestFeatureNormalization:
    """Tests for feature normalization."""

    def test_normalize_features_fit_new_scaling(self):
        """
        Test feature normalization with fit=True (compute statistics).
        """
        classifier = DelayClassifier(n_features=5)
        X = pd.DataFrame(np.array([
            [1, 2, 3, 4, 5],
            [2, 4, 6, 8, 10],
            [3, 6, 9, 12, 15]
        ]))
        
        X_norm = classifier.normalize_features(X, fit=True)
        
        assert X_norm.shape == X.shape
        assert classifier.scaler_mean is not None
        assert classifier.scaler_std is not None
        assert np.allclose(np.mean(X_norm, axis=0), 0, atol=1e-7)

    def test_normalize_features_without_fit_uses_stored_stats(self):
        """
        Test that normalize_features without fit reuses stored statistics.
        """
        classifier = DelayClassifier(n_features=3)
        X_train = pd.DataFrame(np.array([[1, 2, 3], [4, 5, 6]]))
        X_test = pd.DataFrame(np.array([[2, 3, 4]]))
        
        classifier.normalize_features(X_train, fit=True)
        X_test_norm = classifier.normalize_features(X_test, fit=False)
        
        assert X_test_norm.shape == (1, 3)
        assert classifier.scaler_mean is not None

    def test_normalize_features_handles_zero_std(self):
        """
        Test that normalization handles zero standard deviation gracefully.
        """
        classifier = DelayClassifier(n_features=2)
        X = pd.DataFrame(np.array([[1, 5], [1, 10], [1, 15]]))
        
        X_norm = classifier.normalize_features(X, fit=True)
        
        assert not np.any(np.isnan(X_norm))
        assert not np.any(np.isinf(X_norm))


class TestModelTraining:
    """Tests for model training."""

    def test_train_without_validation(self):
        """
        Test training without validation data.
        """
        classifier = DelayClassifier(n_features=8)
        classifier.build_model()
        
        X_train = pd.DataFrame(np.random.randn(100, 8))
        y_train = pd.Series(np.random.randint(0, 2, 100))
        
        history = classifier.train(X_train, y_train, epochs=5, batch_size=16)
        
        assert isinstance(history, TrainingHistory)
        assert len(history.train_losses) == 5
        assert len(history.train_accuracies) == 5

    def test_train_with_validation(self):
        """
        Test training with validation data and early stopping.
        """
        classifier = DelayClassifier(n_features=10)
        classifier.build_model()
        
        X_train = pd.DataFrame(np.random.randn(150, 10))
        y_train = pd.Series(np.random.randint(0, 2, 150))
        X_val = pd.DataFrame(np.random.randn(50, 10))
        y_val = pd.Series(np.random.randint(0, 2, 50))
        
        history = classifier.train(
            X_train, y_train,
            X_val=X_val, y_val=y_val,
            epochs=20,
            batch_size=32,
            early_stopping_patience=3
        )
        
        assert isinstance(history, TrainingHistory)
        assert history.epochs <= 20
        assert len(history.val_losses) == history.epochs
        assert history.best_epoch < history.epochs

    def test_training_history_summary(self):
        """
        Test that TrainingHistory generates a valid summary.
        """
        history = TrainingHistory(
            epochs=5,
            train_losses=[0.5, 0.4, 0.3, 0.2, 0.1],
            val_losses=[0.55, 0.45, 0.32, 0.22, 0.15],
            train_accuracies=[0.7, 0.75, 0.8, 0.85, 0.9],
            val_accuracies=[0.65, 0.72, 0.78, 0.82, 0.87],
            best_epoch=4,
            best_val_loss=0.15
        )
        
        summary = history.summary()
        assert "Training History Summary" in summary
        assert "Epochs: 5" in summary
        assert "Best Epoch: 4" in summary


class TestModelPrediction:
    """Tests for model prediction."""

    def test_predict_binary_classification(self):
        """
        Test binary classification predictions (0 or 1).
        """
        classifier = DelayClassifier(n_features=6)
        classifier.build_model()
        
        X_train = pd.DataFrame(np.random.randn(80, 6))
        y_train = pd.Series(np.random.randint(0, 2, 80))
        classifier.train(X_train, y_train, epochs=3, batch_size=16)
        
        X_test = pd.DataFrame(np.random.randn(20, 6))
        predictions = classifier.predict(X_test, return_probabilities=False)
        
        assert predictions.shape == (20,)
        assert set(predictions).issubset({0, 1})

    def test_predict_probability_scores(self):
        """
        Test probability score predictions (0 to 1).
        """
        classifier = DelayClassifier(n_features=6)
        classifier.build_model()
        
        X_train = pd.DataFrame(np.random.randn(80, 6))
        y_train = pd.Series(np.random.randint(0, 2, 80))
        classifier.train(X_train, y_train, epochs=3, batch_size=16)
        
        X_test = pd.DataFrame(np.random.randn(20, 6))
        probabilities = classifier.predict(X_test, return_probabilities=True)
        
        assert probabilities.shape == (20,)
        assert np.all(probabilities >= 0.0)
        assert np.all(probabilities <= 1.0)

    def test_predict_raises_error_without_model(self):
        """
        Test that predict raises error if model not built.
        """
        classifier = DelayClassifier(n_features=5)
        X_test = pd.DataFrame(np.random.randn(10, 5))
        
        with pytest.raises(ValueError):
            classifier.predict(X_test)


class TestModelEvaluation:
    """Tests for model evaluation."""

    def test_evaluate_returns_metrics_object(self):
        """
        Test that evaluate returns EvaluationMetrics object.
        """
        classifier = DelayClassifier(n_features=7)
        classifier.build_model()
        
        X_train = pd.DataFrame(np.random.randn(100, 7))
        y_train = pd.Series(np.random.randint(0, 2, 100))
        classifier.train(X_train, y_train, epochs=3, batch_size=16)
        
        X_test = pd.DataFrame(np.random.randn(30, 7))
        y_test = pd.Series(np.random.randint(0, 2, 30))
        
        metrics = classifier.evaluate(X_test, y_test)
        
        assert isinstance(metrics, EvaluationMetrics)
        assert 0.0 <= metrics.accuracy <= 1.0
        assert 0.0 <= metrics.precision <= 1.0
        assert 0.0 <= metrics.recall <= 1.0

    def test_evaluation_metrics_summary(self):
        """
        Test that EvaluationMetrics generates a valid summary.
        """
        confusion_matrix = np.array([[80, 10], [5, 105]])
        metrics = EvaluationMetrics(
            accuracy=0.95,
            precision=0.91,
            recall=0.95,
            f1_score=0.93,
            auc_roc=0.97,
            confusion_matrix=confusion_matrix
        )
        
        summary = metrics.summary()
        assert "Evaluation Metrics Summary" in summary
        assert "Accuracy: 0.9500" in summary
        assert "Precision: 0.9100" in summary
        assert "Confusion Matrix" in summary

    def test_evaluate_confusion_matrix_dimensions(self):
        """
        Test that confusion matrix has correct shape.
        """
        classifier = DelayClassifier(n_features=5)
        classifier.build_model()
        
        X_train = pd.DataFrame(np.random.randn(100, 5))
        y_train = pd.Series(np.random.randint(0, 2, 100))
        classifier.train(X_train, y_train, epochs=2, batch_size=16)
        
        X_test = pd.DataFrame(np.random.randn(40, 5))
        y_test = pd.Series(np.random.randint(0, 2, 40))
        
        metrics = classifier.evaluate(X_test, y_test)
        
        assert metrics.confusion_matrix.shape == (2, 2)
        assert np.sum(metrics.confusion_matrix) == 40


class TestModelPersistence:
    """Tests for model save/load functionality."""

    def test_save_model_creates_files(self):
        """
        Test that save_model creates model and metadata files.
        """
        classifier = DelayClassifier(n_features=8)
        classifier.build_model()
        
        X_train = pd.DataFrame(np.random.randn(50, 8))
        y_train = pd.Series(np.random.randint(0, 2, 50))
        classifier.train(X_train, y_train, epochs=2, batch_size=16)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test_model")
            classifier.save_model(filepath)
            
            assert os.path.exists(f"{filepath}.keras")
            assert os.path.exists(f"{filepath}_metadata.json")

    def test_load_model_restores_state(self):
        """
        Test that load_model correctly restores model state.
        """
        classifier = DelayClassifier(n_features=8)
        classifier.build_model()
        
        X_train = pd.DataFrame(np.random.randn(50, 8))
        y_train = pd.Series(np.random.randint(0, 2, 50))
        classifier.train(X_train, y_train, epochs=2, batch_size=16)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test_model")
            classifier.save_model(filepath)
            
            classifier_loaded = DelayClassifier()
            classifier_loaded.load_model(filepath)
            
            assert classifier_loaded.n_features == 8
            assert classifier_loaded.scaler_mean is not None
            assert classifier_loaded.scaler_std is not None

    def test_save_without_trained_model_raises_error(self):
        """
        Test that save_model raises error if model not trained.
        """
        classifier = DelayClassifier(n_features=5)
        classifier.build_model()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test_model")
            with pytest.raises(ValueError):
                classifier.save_model(filepath)

    def test_predictions_consistent_before_after_save_load(self):
        """
        Test that predictions are consistent after save/load.
        """
        classifier = DelayClassifier(n_features=6)
        classifier.build_model()
        
        X_train = pd.DataFrame(np.random.randn(80, 6))
        y_train = pd.Series(np.random.randint(0, 2, 80))
        classifier.train(X_train, y_train, epochs=2, batch_size=16)
        
        X_test = pd.DataFrame(np.random.randn(20, 6))
        pred_before = classifier.predict(X_test, return_probabilities=True)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test_model")
            classifier.save_model(filepath)
            
            classifier_loaded = DelayClassifier()
            classifier_loaded.load_model(filepath)
            pred_after = classifier_loaded.predict(X_test, return_probabilities=True)
            
            assert np.allclose(pred_before, pred_after, atol=1e-5)


class TestModelIntegration:
    """Integration tests for complete workflows."""

    def test_full_training_and_evaluation_pipeline(self):
        """
        Test complete training and evaluation pipeline.
        """
        classifier = DelayClassifier(n_features=12)
        
        n_samples = 300
        X = pd.DataFrame(np.random.randn(n_samples, 12))
        y = pd.Series(np.random.randint(0, 2, n_samples))
        
        split_idx = 250
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        
        classifier.build_model()
        history = classifier.train(X_train, y_train, epochs=5, batch_size=32)
        
        predictions = classifier.predict(X_test)
        metrics = classifier.evaluate(X_test, y_test)
        
        assert history is not None
        assert predictions.shape[0] == len(X_test)
        assert metrics.accuracy > 0
        assert metrics.confusion_matrix.shape == (2, 2)

    def test_train_validation_test_split(self):
        """
        Test proper separation of train/validation/test sets.
        """
        n_train, n_val, n_test = 200, 50, 50
        n_features = 10
        
        X_all = pd.DataFrame(np.random.randn(n_train + n_val + n_test, n_features))
        y_all = pd.Series(np.random.randint(0, 2, n_train + n_val + n_test))
        
        X_train = X_all.iloc[:n_train]
        y_train = y_all.iloc[:n_train]
        X_val = X_all.iloc[n_train:n_train + n_val]
        y_val = y_all.iloc[n_train:n_train + n_val]
        X_test = X_all.iloc[n_train + n_val:]
        y_test = y_all.iloc[n_train + n_val:]
        
        classifier = DelayClassifier(n_features=n_features)
        classifier.build_model()
        
        history = classifier.train(
            X_train, y_train,
            X_val=X_val, y_val=y_val,
            epochs=10,
            early_stopping_patience=3
        )
        
        metrics = classifier.evaluate(X_test, y_test)
        
        assert len(X_train) == n_train
        assert len(X_test) == n_test
        assert metrics is not None

    def test_model_summary_generation(self):
        """
        Test model summary string generation.
        """
        classifier = DelayClassifier(n_features=15)
        classifier.build_model()
        
        summary = classifier.get_model_summary()
        
        assert "Model:" in summary or "Layer" in summary
        assert len(summary) > 0
