"""
GTFS Data Validation & Quality Checks Module.

This module provides comprehensive validation of GTFS data including schema checks,
referential integrity, missing values, and geographic validity. Ensures data quality
before ML pipeline consumption.
"""

import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """
    Container for validation check results.
    
    Attributes:
        is_valid: Whether validation passed.
        errors: List of validation errors found.
        warnings: List of non-critical warnings.
    """
    is_valid: bool
    errors: List[str]
    warnings: List[str]

    def summary(self) -> str:
        """
        Generate human-readable validation summary.
        
        Returns:
            String summary of validation results.
        """
        status = "VALID" if self.is_valid else "INVALID"
        lines = [f"Validation Status: {status}"]
        
        if self.errors:
            lines.append(f"Errors ({len(self.errors)}):")
            for err in self.errors[:5]:
                lines.append(f"  - {err}")
            if len(self.errors) > 5:
                lines.append(f"  ... and {len(self.errors) - 5} more")
        
        if self.warnings:
            lines.append(f"Warnings ({len(self.warnings)}):")
            for warn in self.warnings[:3]:
                lines.append(f"  - {warn}")
            if len(self.warnings) > 3:
                lines.append(f"  ... and {len(self.warnings) - 3} more")
        
        return "\n".join(lines)


class GTFSValidator:
    """
    Comprehensive GTFS data validator.
    
    Performs schema validation, referential integrity checks, missing value analysis,
    and geographic bounds validation for GTFS datasets.
    """

    def __init__(self, strict_mode: bool = False):
        """
        Initialize GTFS validator.
        
        Args:
            strict_mode: If True, all warnings are treated as errors.
        """
        self.strict_mode = strict_mode
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def reset(self) -> None:
        """
        Clear validation errors and warnings.
        Used before running new validation checks.
        """
        self.errors = []
        self.warnings = []

    def validate_gtfs_data(
        self,
        gtfs_data: Dict[str, pd.DataFrame]
    ) -> ValidationResult:
        """
        Perform comprehensive validation on GTFS dataset.
        
        Args:
            gtfs_data: Dictionary of DataFrames from GTFSDataLoader.
            
        Returns:
            ValidationResult with detailed findings.
        """
        self.reset()
        
        self._check_required_tables(gtfs_data)
        self._check_table_schemas(gtfs_data)
        self._check_missing_values(gtfs_data)
        self._check_geographic_bounds(gtfs_data)
        self._check_referential_integrity(gtfs_data)
        
        is_valid = len(self.errors) == 0
        if self.strict_mode and len(self.warnings) > 0:
            is_valid = False
        
        return ValidationResult(
            is_valid=is_valid,
            errors=self.errors.copy(),
            warnings=self.warnings.copy()
        )

    def _check_required_tables(self, gtfs_data: Dict[str, pd.DataFrame]) -> None:
        """
        Verify that all required GTFS tables are present.
        """
        required_tables = {'stops', 'routes', 'trips', 'stop_times', 'calendar'}
        missing = required_tables - set(gtfs_data.keys())
        
        if missing:
            self.errors.append(f"Missing required GTFS tables: {missing}")
        elif len(gtfs_data) < len(required_tables):
            found = set(gtfs_data.keys())
            self.warnings.append(f"Optional tables missing: {required_tables - found}")

    def _check_table_schemas(self, gtfs_data: Dict[str, pd.DataFrame]) -> None:
        """
        Validate column presence in each table.
        """
        schemas = {
            'stops': {'stop_id', 'stop_name', 'stop_lat', 'stop_lon'},
            'routes': {'route_id', 'route_short_name'},
            'trips': {'trip_id', 'route_id', 'service_id'},
            'stop_times': {'trip_id', 'stop_id', 'arrival_time', 'departure_time'},
            'calendar': {'service_id', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'}
        }
        
        for table_name, required_cols in schemas.items():
            if table_name not in gtfs_data:
                continue
            
            df = gtfs_data[table_name]
            missing_cols = required_cols - set(df.columns)
            
            if missing_cols:
                self.errors.append(
                    f"Table '{table_name}' missing columns: {missing_cols}"
                )

    def _check_missing_values(self, gtfs_data: Dict[str, pd.DataFrame]) -> None:
        """
        Check for missing values in critical columns.
        """
        critical_columns = {
            'stops': ['stop_id', 'stop_name', 'stop_lat', 'stop_lon'],
            'routes': ['route_id', 'route_short_name'],
            'trips': ['trip_id', 'route_id'],
            'stop_times': ['trip_id', 'stop_id', 'arrival_time']
        }
        
        for table_name, cols in critical_columns.items():
            if table_name not in gtfs_data:
                continue
            
            df = gtfs_data[table_name]
            for col in cols:
                if col in df.columns:
                    nulls = df[col].isnull().sum()
                    if nulls > 0:
                        pct = (nulls / len(df)) * 100
                        if pct > 5:
                            self.errors.append(
                                f"Table '{table_name}', column '{col}': {nulls} nulls ({pct:.1f}%)"
                            )
                        elif pct > 0:
                            self.warnings.append(
                                f"Table '{table_name}', column '{col}': {nulls} nulls ({pct:.1f}%)"
                            )

    def _check_geographic_bounds(self, gtfs_data: Dict[str, pd.DataFrame]) -> None:
        """
        Validate geographic coordinates are within reasonable bounds (France).
        """
        if 'stops' not in gtfs_data:
            return
        
        df = gtfs_data['stops']
        
        if 'stop_lat' not in df.columns or 'stop_lon' not in df.columns:
            return
        
        invalid_lat = (df['stop_lat'] < 40) | (df['stop_lat'] > 52)
        invalid_lon = (df['stop_lon'] < -8) | (df['stop_lon'] > 8)
        invalid_coords = invalid_lat | invalid_lon
        
        if invalid_coords.any():
            count = invalid_coords.sum()
            self.warnings.append(
                f"Found {count} stops with coordinates outside France bounds"
            )

    def _check_referential_integrity(
        self,
        gtfs_data: Dict[str, pd.DataFrame]
    ) -> None:
        """
        Verify foreign key relationships between tables.
        """
        required_tables = {'routes', 'trips', 'stops', 'stop_times'}
        if not required_tables.issubset(set(gtfs_data.keys())):
            return
        
        routes = gtfs_data['routes']
        trips = gtfs_data['trips']
        stops = gtfs_data['stops']
        stop_times = gtfs_data['stop_times']
        
        if 'route_id' in trips.columns and 'route_id' in routes.columns:
            orphan_trips = trips[~trips['route_id'].isin(routes['route_id'])]
            if len(orphan_trips) > 0:
                self.errors.append(
                    f"Found {len(orphan_trips)} trips referencing non-existent routes"
                )
        
        if 'stop_id' in stop_times.columns and 'stop_id' in stops.columns:
            orphan_stop_times = stop_times[~stop_times['stop_id'].isin(stops['stop_id'])]
            if len(orphan_stop_times) > 0:
                self.warnings.append(
                    f"Found {len(orphan_stop_times)} stop_times with invalid stop_ids"
                )

    def get_data_statistics(
        self,
        gtfs_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, Dict[str, int]]:
        """
        Generate summary statistics for GTFS data.
        
        Args:
            gtfs_data: Dictionary of GTFS DataFrames.
            
        Returns:
            Dictionary with row counts and column counts per table.
        """
        stats = {}
        
        for table_name, df in gtfs_data.items():
            stats[table_name] = {
                'rows': len(df),
                'columns': len(df.columns),
                'memory_mb': df.memory_usage(deep=True).sum() / 1024 / 1024
            }
        
        return stats
