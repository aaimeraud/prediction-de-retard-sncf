"""
Unit tests for Feature Engineering Module.

Tests cover feature extraction, transformation, and quality checks.
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.feature_engineer import FeatureEngineer, FeatureSet


@pytest.fixture
def sample_gtfs_data():
    """
    Create sample GTFS data for feature engineering.
    """
    return {
        'stops': pd.DataFrame({
            'stop_id': ['S1', 'S2', 'S3'],
            'stop_name': ['Gare de Lyon', 'Gare du Nord', 'Châtelet'],
            'stop_lat': [48.8426, 48.8861, 48.8629],
            'stop_lon': [2.3739, 2.3556, 2.3472]
        }),
        'routes': pd.DataFrame({
            'route_id': ['R1', 'R2'],
            'route_short_name': ['TER-1', 'TGV-2'],
            'route_type': ['2', '3']
        }),
        'trips': pd.DataFrame({
            'trip_id': ['T1', 'T2'],
            'route_id': ['R1', 'R2'],
            'service_id': ['WD', 'WD']
        }),
        'stop_times': pd.DataFrame({
            'trip_id': ['T1', 'T1', 'T2', 'T2'],
            'stop_id': ['S1', 'S2', 'S2', 'S3'],
            'arrival_time': ['08:00:00', '08:30:00', '09:15:00', '09:45:00'],
            'departure_time': ['08:05:00', '08:30:00', '09:20:00', '09:45:00']
        }),
        'calendar': pd.DataFrame({
            'service_id': ['WD'],
            'monday': [1]
        })
    }


@pytest.fixture
def sample_realtime_data():
    """
    Create sample real-time delay data.
    """
    return pd.DataFrame({
        'route_id': ['R1', 'R1', 'R1', 'R2', 'R2'],
        'trip_id': ['T1', 'T1', 'T1', 'T2', 'T2'],
        'stop_id': ['S1', 'S2', 'S1', 'S2', 'S3'],
        'delay_minutes': [0, 5, 3, 0, 8]
    })


class TestFeatureEngineer:
    """
    Test suite for FeatureEngineer class.
    """

    def test_initialization(self):
        """
        Test FeatureEngineer initialization.
        """
        engineer = FeatureEngineer()
        
        assert engineer.fitted is False
        assert isinstance(engineer.route_delay_stats, dict)

    def test_engineer_features_basic(self, sample_gtfs_data):
        """
        Test basic feature engineering from GTFS data.
        """
        engineer = FeatureEngineer()
        feature_set = engineer.engineer_features(sample_gtfs_data)
        
        assert isinstance(feature_set, FeatureSet)
        assert len(feature_set.features) > 0
        assert len(feature_set.feature_names) > 0
        assert engineer.fitted is True

    def test_feature_set_summary(self, sample_gtfs_data):
        """
        Test FeatureSet summary generation.
        """
        engineer = FeatureEngineer()
        feature_set = engineer.engineer_features(sample_gtfs_data)
        
        summary = feature_set.summary()
        
        assert 'Feature Set Summary' in summary
        assert 'Rows:' in summary
        assert 'Features:' in summary

    def test_temporal_features(self, sample_gtfs_data):
        """
        Test temporal feature extraction.
        """
        engineer = FeatureEngineer()
        feature_set = engineer.engineer_features(sample_gtfs_data)
        
        assert 'hour_of_day' in feature_set.feature_names
        assert 'is_peak_hours' in feature_set.feature_names
        
        hours = feature_set.features['hour_of_day'].unique()
        assert all(0 <= h <= 23 for h in hours if pd.notna(h))

    def test_geographic_features(self, sample_gtfs_data):
        """
        Test geographic feature extraction.
        """
        engineer = FeatureEngineer()
        feature_set = engineer.engineer_features(sample_gtfs_data)
        
        assert 'is_ile_de_france' in feature_set.feature_names
        
        if 'is_ile_de_france' in feature_set.features.columns:
            values = feature_set.features['is_ile_de_france'].unique()
            assert all(v in [0, 1] for v in values)

    def test_route_features(self, sample_gtfs_data):
        """
        Test route-based feature extraction.
        """
        engineer = FeatureEngineer()
        feature_set = engineer.engineer_features(sample_gtfs_data)
        
        assert 'route_short_name' in feature_set.features.columns

    def test_with_realtime_data(self, sample_gtfs_data, sample_realtime_data):
        """
        Test feature engineering with real-time delay data.
        """
        engineer = FeatureEngineer()
        feature_set = engineer.engineer_features(
            sample_gtfs_data,
            realtime_data=sample_realtime_data
        )
        
        assert 'route_avg_delay' in feature_set.feature_names

    def test_missing_tables_raises_error(self):
        """
        Test that missing required tables raise ValueError.
        """
        incomplete_gtfs = {
            'stops': pd.DataFrame({'stop_id': ['S1']}),
            'routes': pd.DataFrame({'route_id': ['R1']})
        }
        
        engineer = FeatureEngineer()
        
        with pytest.raises(ValueError):
            engineer.engineer_features(incomplete_gtfs)

    def test_feature_importance_baseline(self, sample_gtfs_data):
        """
        Test feature importance baseline estimation.
        """
        engineer = FeatureEngineer()
        feature_set = engineer.engineer_features(sample_gtfs_data)
        
        importance = engineer.get_feature_importance_baseline(feature_set.feature_names)
        
        assert isinstance(importance, dict)
        assert len(importance) == len(feature_set.feature_names)
        assert all(0 <= v <= 1 for v in importance.values())

    def test_no_nulls_in_key_features(self, sample_gtfs_data):
        """
        Test that key features don't have unexpected nulls.
        """
        engineer = FeatureEngineer()
        feature_set = engineer.engineer_features(sample_gtfs_data)
        
        if 'is_peak_hours' in feature_set.features.columns:
            assert feature_set.features['is_peak_hours'].isnull().sum() == 0


class TestFeatureEngineeringIntegration:
    """
    Integration tests for feature engineering pipeline.
    """

    def test_full_pipeline_with_realtime(self, sample_gtfs_data, sample_realtime_data):
        """
        Test complete feature engineering pipeline.
        """
        engineer = FeatureEngineer()
        
        feature_set = engineer.engineer_features(
            sample_gtfs_data,
            realtime_data=sample_realtime_data
        )
        
        assert feature_set.features is not None
        assert len(feature_set.features) > 0
        assert feature_set.metadata['n_features'] > 0

    def test_feature_consistency(self, sample_gtfs_data):
        """
        Test that engineered features are consistent across runs.
        """
        engineer1 = FeatureEngineer()
        engineer2 = FeatureEngineer()
        
        fs1 = engineer1.engineer_features(sample_gtfs_data)
        fs2 = engineer2.engineer_features(sample_gtfs_data)
        
        assert len(fs1.features) == len(fs2.features)
        assert set(fs1.feature_names) == set(fs2.feature_names)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
