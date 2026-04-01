"""
Feature Engineering Module for SNCF Delay Prediction.

Transforms raw GTFS data into features suitable for ML models.
Includes temporal features (time of day, day of week), geographic features,
and route-based features for delay prediction.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass


@dataclass
class FeatureSet:
    """
    Container for engineered features and metadata.
    
    Attributes:
        features: DataFrame with engineered features (one row per trip segment).
        feature_names: List of feature column names.
        metadata: Dictionary of metadata (scaling info, encoding, etc.).
    """
    features: pd.DataFrame
    feature_names: List[str]
    metadata: Dict = None

    def summary(self) -> str:
        """
        Generate summary of feature set.
        
        Returns:
            String describing the feature set.
        """
        lines = [
            f"Feature Set Summary",
            f"Rows: {len(self.features)}",
            f"Features: {len(self.feature_names)}",
            f"Memory (MB): {self.features.memory_usage(deep=True).sum() / 1024 / 1024:.2f}",
            f"Columns: {', '.join(self.feature_names[:5])}{'...' if len(self.feature_names) > 5 else ''}"
        ]
        return "\n".join(lines)


class FeatureEngineer:
    """
    Feature engineering for SNCF delay prediction.
    
    Transforms GTFS data + real-time updates into features:
    - Temporal: hour, day_of_week, is_weekend
    - Route: route_type, trip_duration
    - Geographic: origin_lat, origin_lon, dest_lat, dest_lon, distance
    - Historical: avg_delay_by_route, delay_by_origin
    """

    def __init__(self):
        """
        Initialize feature engineer.
        """
        self.fitted = False
        self.route_delay_stats: Dict[str, float] = {}
        self.stop_delay_stats: Dict[str, float] = {}

    def engineer_features(
        self,
        gtfs_data: Dict[str, pd.DataFrame],
        realtime_data: Optional[pd.DataFrame] = None
    ) -> FeatureSet:
        """
        Engineer features from GTFS and optional real-time data.
        
        Args:
            gtfs_data: Dictionary of GTFS DataFrames.
            realtime_data: Optional DataFrame with real-time delay observations.
            
        Returns:
            FeatureSet with engineered features.
        """
        stops = gtfs_data.get('stops')
        routes = gtfs_data.get('routes')
        trips = gtfs_data.get('trips')
        stop_times = gtfs_data.get('stop_times')
        
        if stops is None or routes is None or trips is None or stop_times is None:
            raise ValueError("Missing required GTFS tables: stops, routes, trips, stop_times")
        
        merged = stop_times.merge(trips, on='trip_id', how='left')
        merged = merged.merge(routes, on='route_id', how='left')
        merged = merged.merge(stops[['stop_id', 'stop_lat', 'stop_lon']], 
                             on='stop_id', how='left')
        
        feature_df = pd.DataFrame()
        
        feature_df['trip_id'] = merged['trip_id']
        feature_df['stop_id'] = merged['stop_id']
        feature_df['route_id'] = merged['route_id']
        
        feature_df = self._add_temporal_features(feature_df, merged)
        feature_df = self._add_route_features(feature_df, merged)
        feature_df = self._add_geographic_features(feature_df, merged)
        
        if realtime_data is not None:
            feature_df = self._add_delay_history(feature_df, realtime_data)
        
        feature_names = [col for col in feature_df.columns 
                        if col not in ['trip_id', 'stop_id', 'route_id']]
        
        self.fitted = True
        
        return FeatureSet(
            features=feature_df,
            feature_names=feature_names,
            metadata={'n_features': len(feature_names), 'n_samples': len(feature_df)}
        )

    def _add_temporal_features(
        self,
        feature_df: pd.DataFrame,
        data: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Add temporal features (hour, day_of_week, etc.).
        """
        def parse_time(time_str):
            """
            Parse HH:MM:SS time string to seconds since midnight.
            """
            if pd.isna(time_str):
                return np.nan
            try:
                parts = str(time_str).split(':')
                h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
                return h * 3600 + m * 60 + s
            except:
                return np.nan
        
        if 'arrival_time' in data.columns:
            arrival_seconds = data['arrival_time'].apply(parse_time)
            feature_df['hour_of_day'] = (arrival_seconds / 3600).astype(int) % 24
            feature_df['time_of_day_seconds'] = arrival_seconds
        
        if 'service_id' in data.columns:
            feature_df['service_id'] = data['service_id'].values
        
        feature_df['is_peak_hours'] = (
            (feature_df['hour_of_day'] >= 7) & 
            (feature_df['hour_of_day'] <= 9) |
            (feature_df['hour_of_day'] >= 17) & 
            (feature_df['hour_of_day'] <= 19)
        ).astype(int)
        
        return feature_df

    def _add_route_features(
        self,
        feature_df: pd.DataFrame,
        data: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Add route-based features.
        """
        if 'route_short_name' in data.columns:
            feature_df['route_short_name'] = data['route_short_name'].values
        
        if 'route_type' in data.columns:
            route_types = pd.get_dummies(data['route_type'], prefix='route_type')
            for col in route_types.columns:
                feature_df[col] = route_types[col].values
        
        return feature_df

    def _add_geographic_features(
        self,
        feature_df: pd.DataFrame,
        data: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Add geographic features (coordinates, distance).
        """
        if 'stop_lat' in data.columns:
            feature_df['stop_lat'] = data['stop_lat'].values
        
        if 'stop_lon' in data.columns:
            feature_df['stop_lon'] = data['stop_lon'].values
        
        if 'stop_lat' in data.columns and 'stop_lon' in data.columns:
            lats = data['stop_lat'].values
            lons = data['stop_lon'].values
            
            feature_df['is_ile_de_france'] = (
                (lats >= 48.1) & (lats <= 49.0) &
                (lons >= 1.5) & (lons <= 3.0)
            ).astype(int)
        
        return feature_df

    def _add_delay_history(
        self,
        feature_df: pd.DataFrame,
        realtime_data: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Add historical delay statistics.
        """
        if 'route_id' in realtime_data.columns and 'delay_minutes' in realtime_data.columns:
            route_delays = realtime_data.groupby('route_id')['delay_minutes'].agg(['mean', 'std', 'max'])
            
            feature_df['route_avg_delay'] = feature_df['route_id'].map(
                route_delays['mean']
            ).fillna(0)
            
            feature_df['route_delay_volatility'] = feature_df['route_id'].map(
                route_delays['std']
            ).fillna(0)
        
        return feature_df

    def get_feature_importance_baseline(
        self,
        feature_names: List[str]
    ) -> Dict[str, float]:
        """
        Generate baseline feature importance estimates.
        
        Returns:
            Dictionary mapping feature names to importance scores.
        """
        importance = {}
        
        importance_mapping = {
            'hour_of_day': 0.15,
            'is_peak_hours': 0.12,
            'route_avg_delay': 0.18,
            'is_ile_de_france': 0.10,
            'route_delay_volatility': 0.12,
            'service_id': 0.08,
            'stop_lat': 0.05,
            'stop_lon': 0.05
        }
        
        for feature in feature_names:
            for key, value in importance_mapping.items():
                if key in feature:
                    importance[feature] = value
                    break
            else:
                importance[feature] = 0.02
        
        return importance
