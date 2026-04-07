"""
Quick model training script to generate delay_classifier.keras for Streamlit testing.

Creates a minimal trained model that can be loaded by the dashboard.
"""

import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent / "src"))

from model_classifier import DelayClassifier


def train_minimal_model():
    """
    Train a minimal model with random data for testing purposes.
    
    Saves model to models/delay_classifier.keras
    """
    print("🏋️ Training minimal model for testing...")
    
    Path("models").mkdir(exist_ok=True)
    
    classifier = DelayClassifier(n_features=9)
    
    X_train = np.random.randn(100, 9)
    y_train = np.random.randint(0, 2, 100)
    
    print("Training on 100 synthetic samples...")
    history = classifier.train(
        X_train, 
        y_train, 
        epochs=5, 
        batch_size=16, 
        validation_split=0.2,
        verbose=0
    )
    
    model_path = "models/delay_classifier.keras"
    classifier.save_model(model_path)
    
    print(f"✅ Model saved to: {model_path}")
    print(f"   Accuracy: {history.metrics['accuracy'][-1]:.2%}")


if __name__ == "__main__":
    train_minimal_model()
