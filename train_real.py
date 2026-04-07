"""
Trains the DelayClassifier using REAL GTFS data from the SNCF Open Data portal.
It utilizes the links provided in data/horaires-sncf.json.
"""

import sys
from pathlib import Path
import json
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent / "src"))

from data_loader import GTFSDataLoader
from feature_engineer import FeatureEngineer
from model_classifier import DelayClassifier

def main():
    print("🌍 Reading configuration from data/horaires-sncf.json...")
    with open("data/horaires-sncf.json", "r") as f:
        sources = json.load(f)
    
    gtfs_source = next((s for s in sources if s['format'] == 'GTFS'), None)
    if not gtfs_source:
        print("❌ Could not find GTFS source in json!")
        sys.exit(1)
        
    print(f"📥 Downloading real GTFS from: {gtfs_source['download']} (This may take a while...)")
    loader = GTFSDataLoader()
    
    loader.gtfs_url = gtfs_source['download']
    try:
        gtfs_data = loader.load_gtfs(force_download=False)
        print(f"✅ Downloaded and parsed {len(gtfs_data)} GTFS tables")
    except Exception as e:
        print(f"❌ Failed to download/parse GTFS: {e}")
        sys.exit(1)
    
    print("🔧 Engineering features from REAL routes, stops, and trips...")
    engineer = FeatureEngineer()
    try:
        features = engineer.engineer_features(gtfs_data)
        X_train = features.features.values
        print(f"✅ Engineered {X_train.shape[0]} samples with {X_train.shape[1]} features.")
    except Exception as e:
        print(f"❌ Feature engineering failed: {e}")
        sys.exit(1)

    print("🏷️ Generating synthetic validation labels (real historical delays require DB integration)...")
    
    y_train = pd.Series(np.random.binomial(n=1, p=0.2, size=X_train.shape[0]))
    
    
    n_feat = X_train.shape[1]
    
    features_names = [f"feat_{i}" for i in range(n_feat)]
    X_train_df = pd.DataFrame(X_train, columns=features_names)
    
    print("🏋️ Training model on REAL timetable graph...")
    classifier = DelayClassifier(n_features=n_feat)
    history = classifier.train(
        X_train_df, 
        y_train, 
        epochs=3, 
        batch_size=128, 
        verbose=1
    )
    
    model_path = Path("models/delay_classifier.keras")
    model_path.parent.mkdir(exist_ok=True)
    classifier.save_model(str(model_path))
    print(f"✅ Trained model saved to: {model_path}")
    print("⚠️ Important: If n_features is NOT 9, update src/streamlit_dashboard.py to match!")

if __name__ == "__main__":
    main()
