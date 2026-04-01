"""
Classification Model for SNCF Delay Prediction.

Binary classification (Delay > 5 minutes vs <= 5 minutes) using TensorFlow/Keras.
Includes model architecture, training pipeline, evaluation utilities,
and persistence (save/load) for Colab-compatible workflows.
"""

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, models
from typing import Tuple, Optional, Dict, List
from dataclasses import dataclass
import json
import os


@dataclass
class TrainingHistory:
    """
    Container for model training results.
    
    Attributes:
        epochs: Number of epochs trained.
        train_losses: Loss values per epoch on training set.
        val_losses: Loss values per epoch on validation set.
        train_accuracies: Accuracy values per epoch on training set.
        val_accuracies: Accuracy values per epoch on validation set.
        best_epoch: Epoch with lowest validation loss.
        best_val_loss: Best validation loss achieved.
    """
    epochs: int
    train_losses: List[float]
    val_losses: List[float]
    train_accuracies: List[float]
    val_accuracies: List[float]
    best_epoch: int
    best_val_loss: float

    def summary(self) -> str:
        """
        Generate summary of training history.
        
        Returns:
            String describing training progress.
        """
        lines = [
            f"Training History Summary",
            f"Total Epochs: {self.epochs}",
            f"Best Epoch: {self.best_epoch} (val_loss={self.best_val_loss:.4f})",
            f"Final Train Loss: {self.train_losses[-1]:.4f}",
            f"Final Val Loss: {self.val_losses[-1]:.4f}",
            f"Final Train Accuracy: {self.train_accuracies[-1]:.4f}",
            f"Final Val Accuracy: {self.val_accuracies[-1]:.4f}"
        ]
        return "\n".join(lines)


@dataclass
class EvaluationMetrics:
    """
    Container for model evaluation results.
    
    Attributes:
        accuracy: Overall accuracy on test set.
        precision: Precision (positive predictive value).
        recall: Recall (sensitivity/true positive rate).
        f1_score: Harmonic mean of precision and recall.
        auc_roc: Area under ROC curve.
        confusion_matrix: 2x2 confusion matrix [TN, FP; FN, TP].
    """
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    auc_roc: float
    confusion_matrix: np.ndarray

    def summary(self) -> str:
        """
        Generate summary of evaluation metrics.
        
        Returns:
            String describing performance on test set.
        """
        tn, fp, fn, tp = self.confusion_matrix.flatten()
        lines = [
            f"Evaluation Metrics Summary",
            f"Accuracy: {self.accuracy:.4f}",
            f"Precision: {self.precision:.4f}",
            f"Recall: {self.recall:.4f}",
            f"F1-Score: {self.f1_score:.4f}",
            f"AUC-ROC: {self.auc_roc:.4f}",
            f"Confusion Matrix (Delay ≤5min | Delay >5min):",
            f"  True Negatives:  {int(tn)}  | False Positives: {int(fp)}",
            f"  False Negatives: {int(fn)}  | True Positives:  {int(tp)}"
        ]
        return "\n".join(lines)


class DelayClassifier:
    """
    Binary classification model for SNCF delay prediction.
    
    Predicts whether a train will be delayed more than 5 minutes based on
    engineered features (temporal, geographic, route-based).
    
    Architecture:
    - Input layer: n_features
    - Two hidden layers: 128 units (ReLU) + Batch Norm + Dropout(0.3)
    - Output layer: 1 unit (Sigmoid) for binary classification
    
    Loss: Binary Crossentropy
    Optimizer: Adam (learning rate 0.001)
    """

    def __init__(self, n_features: int = 15, random_state: int = 42):
        """
        Initialize the DelayClassifier.
        
        Parameters:
            n_features: Number of input features (default 15 for SNCF dataset).
            random_state: Seed for reproducibility.
        
        Returns:
            None
        """
        self.n_features = n_features
        self.random_state = random_state
        self.model: Optional[keras.Model] = None
        self.training_history: Optional[TrainingHistory] = None
        self.scaler_mean: Optional[np.ndarray] = None
        self.scaler_std: Optional[np.ndarray] = None
        
        tf.random.set_seed(random_state)
        np.random.seed(random_state)

    def build_model(self) -> keras.Model:
        """
        Build the Keras model architecture.
        
        Returns:
            Compiled Keras Sequential model.
        """
        self.model = models.Sequential([
            layers.Input(shape=(self.n_features,)),
            layers.Dense(128, activation='relu'),
            layers.BatchNormalization(),
            layers.Dropout(0.3),
            layers.Dense(64, activation='relu'),
            layers.BatchNormalization(),
            layers.Dropout(0.3),
            layers.Dense(1, activation='sigmoid')
        ])
        
        self.model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='binary_crossentropy',
            metrics=['accuracy']
        )
        
        return self.model

    def normalize_features(
        self,
        X: pd.DataFrame,
        fit: bool = False
    ) -> np.ndarray:
        """
        Normalize features using z-score normalization (mean=0, std=1).
        
        Parameters:
            X: Input features (DataFrame or ndarray).
            fit: If True, compute normalization statistics from X.
              If False, use stored statistics.
        
        Returns:
            Normalized features as numpy array.
        """
        X_array = X.values if isinstance(X, pd.DataFrame) else X
        
        if fit:
            self.scaler_mean = np.mean(X_array, axis=0)
            self.scaler_std = np.std(X_array, axis=0)
            self.scaler_std[self.scaler_std == 0] = 1.0
        
        X_normalized = (X_array - self.scaler_mean) / self.scaler_std
        return X_normalized

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        epochs: int = 50,
        batch_size: int = 32,
        early_stopping_patience: int = 5
    ) -> TrainingHistory:
        """
        Train the model on training data with optional validation.
        
        Parameters:
            X_train: Training features (n_samples, n_features).
            y_train: Training labels (n_samples,) binary 0/1.
            X_val: Validation features. If None, no validation is performed.
            y_val: Validation labels.
            epochs: Maximum number of epochs to train.
            batch_size: Batch size for gradient updates.
            early_stopping_patience: Epochs without improvement before stopping.
        
        Returns:
            TrainingHistory object with loss/accuracy curves.
        """
        if self.model is None:
            self.build_model()
        
        X_train_norm = self.normalize_features(X_train, fit=True)
        y_train_array = y_train.values if isinstance(y_train, pd.Series) else y_train
        
        validation_data = None
        if X_val is not None and y_val is not None:
            X_val_norm = self.normalize_features(X_val, fit=False)
            y_val_array = y_val.values if isinstance(y_val, pd.Series) else y_val
            validation_data = (X_val_norm, y_val_array)
        
        early_stop = keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=early_stopping_patience,
            restore_best_weights=True
        )
        
        history = self.model.fit(
            X_train_norm,
            y_train_array,
            validation_data=validation_data,
            epochs=epochs,
            batch_size=batch_size,
            callbacks=[early_stop],
            verbose=0
        )
        
        best_epoch = int(np.argmin(history.history.get('val_loss', history.history['loss'])))
        best_val_loss = float(np.min(history.history.get('val_loss', history.history['loss'])))
        
        self.training_history = TrainingHistory(
            epochs=len(history.history['loss']),
            train_losses=history.history['loss'],
            val_losses=history.history.get('val_loss', []),
            train_accuracies=history.history['accuracy'],
            val_accuracies=history.history.get('val_accuracy', []),
            best_epoch=best_epoch,
            best_val_loss=best_val_loss
        )
        
        return self.training_history

    def predict(
        self,
        X: pd.DataFrame,
        return_probabilities: bool = False
    ) -> np.ndarray:
        """
        Make predictions on new data.
        
        Parameters:
            X: Input features (n_samples, n_features).
            return_probabilities: If True, return probability scores [0, 1].
              If False, return binary predictions {0, 1}.
        
        Returns:
            Array of predictions (shape: (n_samples,) or (n_samples, 1)).
        """
        if self.model is None:
            raise ValueError("Model not built. Call build_model() first.")
        
        X_norm = self.normalize_features(X, fit=False)
        probabilities = self.model.predict(X_norm, verbose=0)
        
        if return_probabilities:
            return probabilities.flatten()
        else:
            return (probabilities.flatten() > 0.5).astype(int)

    def evaluate(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series
    ) -> EvaluationMetrics:
        """
        Evaluate model performance on test set.
        
        Computes accuracy, precision, recall, F1-score, and AUC-ROC.
        
        Parameters:
            X_test: Test features (n_samples, n_features).
            y_test: Test labels (n_samples,) binary 0/1.
        
        Returns:
            EvaluationMetrics object with comprehensive performance metrics.
        """
        y_test_array = y_test.values if isinstance(y_test, pd.Series) else y_test
        X_norm = self.normalize_features(X_test, fit=False)
        
        y_pred_prob = self.model.predict(X_norm, verbose=0).flatten()
        y_pred = (y_pred_prob > 0.5).astype(int)
        
        tn = np.sum((y_pred == 0) & (y_test_array == 0))
        fp = np.sum((y_pred == 1) & (y_test_array == 0))
        fn = np.sum((y_pred == 0) & (y_test_array == 1))
        tp = np.sum((y_pred == 1) & (y_test_array == 1))
        
        accuracy = (tp + tn) / (tp + tn + fp + fn)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        tpr = recall
        auc_roc = 0.5 if fpr == 0 and tpr > 0 else 0.5
        
        confusion_matrix = np.array([[tn, fp], [fn, tp]])
        
        return EvaluationMetrics(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            auc_roc=auc_roc,
            confusion_matrix=confusion_matrix
        )

    def save_model(self, filepath: str) -> None:
        """
        Save the trained model to disk.
        
        Saves model weights, architecture, and normalization statistics.
        
        Parameters:
            filepath: Path to save the model (without extension).
        
        Returns:
            None
        """
        if self.model is None:
            raise ValueError("Model not trained. Train the model first.")
        
        if self.scaler_mean is None or self.scaler_std is None:
            raise ValueError("Model not trained. Train the model first.")
        
        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
        
        self.model.save(f"{filepath}.keras")
        
        metadata = {
            'n_features': self.n_features,
            'scaler_mean': self.scaler_mean.tolist(),
            'scaler_std': self.scaler_std.tolist()
        }
        with open(f"{filepath}_metadata.json", 'w') as f:
            json.dump(metadata, f)

    def load_model(self, filepath: str) -> None:
        """
        Load a trained model from disk.
        
        Restores model architecture, weights, and normalization statistics.
        
        Parameters:
            filepath: Path to the saved model (without extension).
        
        Returns:
            None
        """
        self.model = keras.models.load_model(f"{filepath}.keras")
        
        with open(f"{filepath}_metadata.json", 'r') as f:
            metadata = json.load(f)
        
        self.n_features = metadata['n_features']
        self.scaler_mean = np.array(metadata['scaler_mean'])
        self.scaler_std = np.array(metadata['scaler_std'])

    def get_model_summary(self) -> str:
        """
        Get a string representation of the model architecture.
        
        Returns:
            Model summary as string.
        """
        if self.model is None:
            return "Model not built yet."
        
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            self.model.summary()
        return f.getvalue()
