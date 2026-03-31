"""
Test suite for GTFS Data Validation.

Tests cover schema validation, integrity checks, and data quality metrics.
"""

import pytest
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_validator import GTFSValidator, ValidationResult


@pytest.fixture
def valid_gtfs_data():
    """
    Create valid mock GTFS data for testing.
    """
    data = {
        'stops': pd.DataFrame({
            'stop_id': ['1', '2', '3'],
            'stop_name': ['Gare de Lyon', 'Gare du Nord', 'Châtelet'],
            'stop_lat': [48.8426, 48.8861, 48.8629],
            'stop_lon': [2.3739, 2.3556, 2.3472]
        }),
        'routes': pd.DataFrame({
            'route_id': ['R1', 'R2'],
            'route_short_name': ['TER', 'TGV']
        }),
        'trips': pd.DataFrame({
            'trip_id': ['T1', 'T2', 'T3'],
            'route_id': ['R1', 'R1', 'R2'],
            'service_id': ['WD', 'WD', 'WE']
        }),
        'stop_times': pd.DataFrame({
            'trip_id': ['T1', 'T1', 'T2', 'T2', 'T3'],
            'stop_id': ['1', '2', '2', '3', '1'],
            'arrival_time': ['08:00:00', '08:30:00', '09:00:00', '09:30:00', '10:00:00'],
            'departure_time': ['08:05:00', '08:30:00', '09:00:00', '09:30:00', '10:05:00']
        }),
        'calendar': pd.DataFrame({
            'service_id': ['WD', 'WE'],
            'monday': [1, 0],
            'tuesday': [1, 0],
            'wednesday': [1, 0],
            'thursday': [1, 0],
            'friday': [1, 0],
            'saturday': [0, 1],
            'sunday': [0, 1],
            'start_date': ['20260101', '20260101'],
            'end_date': ['20261231', '20261231']
        })
    }
    return data


@pytest.fixture
def invalid_gtfs_data():
    """
    Create invalid mock GTFS data with errors.
    """
    data = {
        'stops': pd.DataFrame({
            'stop_id': ['1', '2', '3'],
            'stop_name': ['Gare de Lyon', None, 'Châtelet'],
            'stop_lat': [48.8426, 48.8861, 75.0],
            'stop_lon': [2.3739, 2.3556, 10.0]
        }),
        'routes': pd.DataFrame({
            'route_id': ['R1'],
            'route_short_name': ['TER']
        }),
        'trips': pd.DataFrame({
            'trip_id': ['T1', 'T2'],
            'route_id': ['R1', 'R999'],
            'service_id': ['WD', 'WD']
        }),
        'stop_times': pd.DataFrame({
            'trip_id': ['T1', 'T1', 'T2'],
            'stop_id': ['1', '999', '1'],
            'arrival_time': ['08:00:00', '08:30:00', '09:00:00'],
            'departure_time': ['08:05:00', '08:30:00', '09:00:00']
        }),
        'calendar': pd.DataFrame({
            'service_id': ['WD'],
            'monday': [1],
            'tuesday': [1],
            'wednesday': [1],
            'thursday': [1],
            'friday': [1],
            'saturday': [0],
            'sunday': [0]
        })
    }
    return data


class TestGTFSValidator:
    """
    Test suite for GTFSValidator class.
    """

    def test_validator_initialization(self):
        """
        Test GTFSValidator initialization.
        """
        validator = GTFSValidator()
        assert validator.strict_mode is False
        assert validator.errors == []
        assert validator.warnings == []

    def test_validator_strict_mode(self):
        """
        Test GTFSValidator with strict mode enabled.
        """
        validator = GTFSValidator(strict_mode=True)
        assert validator.strict_mode is True

    def test_reset(self):
        """
        Test resetting validator state.
        """
        validator = GTFSValidator()
        validator.errors.append("test error")
        validator.warnings.append("test warning")
        
        validator.reset()
        
        assert validator.errors == []
        assert validator.warnings == []

    def test_validate_valid_gtfs(self, valid_gtfs_data):
        """
        Test validation of correct GTFS data.
        """
        validator = GTFSValidator()
        result = validator.validate_gtfs_data(valid_gtfs_data)
        
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_invalid_gtfs(self, invalid_gtfs_data):
        """
        Test validation detects errors in GTFS data.
        """
        validator = GTFSValidator()
        result = validator.validate_gtfs_data(invalid_gtfs_data)
        
        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_check_missing_tables(self):
        """
        Test detection of missing required tables.
        """
        incomplete_data = {
            'stops': pd.DataFrame({'stop_id': ['1']}),
            'routes': pd.DataFrame({'route_id': ['R1']})
        }
        
        validator = GTFSValidator()
        result = validator.validate_gtfs_data(incomplete_data)
        
        assert result.is_valid is False
        assert any('Missing required' in err for err in result.errors)

    def test_check_schema_errors(self):
        """
        Test schema validation catches missing columns.
        """
        bad_schema = {
            'stops': pd.DataFrame({
                'stop_id': ['1'],
                'stop_name': ['Test'],
            }),
            'routes': pd.DataFrame({'route_id': ['R1']}),
            'trips': pd.DataFrame({'trip_id': ['T1']}),
            'stop_times': pd.DataFrame({'trip_id': ['T1']}),
            'calendar': pd.DataFrame({'service_id': ['WD']})
        }
        
        validator = GTFSValidator()
        result = validator.validate_gtfs_data(bad_schema)
        
        assert result.is_valid is False

    def test_check_referential_integrity(self, invalid_gtfs_data):
        """
        Test detection of orphaned records.
        """
        validator = GTFSValidator()
        result = validator.validate_gtfs_data(invalid_gtfs_data)
        
        assert any('referencing non-existent' in err for err in result.errors)

    def test_validation_result_summary(self):
        """
        Test ValidationResult summary generation.
        """
        result = ValidationResult(
            is_valid=False,
            errors=['Error 1', 'Error 2'],
            warnings=['Warning 1']
        )
        
        summary = result.summary()
        
        assert 'INVALID' in summary
        assert 'Error 1' in summary
        assert 'Warning 1' in summary

    def test_get_data_statistics(self, valid_gtfs_data):
        """
        Test statistics generation for GTFS data.
        """
        validator = GTFSValidator()
        stats = validator.get_data_statistics(valid_gtfs_data)
        
        assert 'stops' in stats
        assert 'routes' in stats
        assert stats['stops']['rows'] == 3
        assert stats['routes']['rows'] == 2
        assert 'memory_mb' in stats['stops']

    def test_strict_mode_warnings_as_errors(self, invalid_gtfs_data):
        """
        Test that strict mode treats warnings as errors.
        """
        validator = GTFSValidator(strict_mode=True)
        result = validator.validate_gtfs_data(invalid_gtfs_data)
        
        if len(result.warnings) > 0:
            assert result.is_valid is False


class TestGTFSValidationIntegration:
    """
    Integration tests for complete validation workflow.
    """

    def test_full_validation_workflow(self, valid_gtfs_data):
        """
        Test complete validation workflow.
        """
        validator = GTFSValidator()
        
        result = validator.validate_gtfs_data(valid_gtfs_data)
        stats = validator.get_data_statistics(valid_gtfs_data)
        
        assert result.is_valid is True
        assert len(stats) == 5
        assert sum(s['rows'] for s in stats.values()) > 0

    def test_error_collection_across_multiple_checks(self):
        """
        Test that multiple validation errors are collected properly.
        """
        partial_data = {
            'stops': pd.DataFrame({'stop_id': ['1']}),
            'routes': pd.DataFrame({'route_id': ['R1']})
        }
        
        validator = GTFSValidator()
        result = validator.validate_gtfs_data(partial_data)
        
        assert len(result.errors) >= 1
        assert all(isinstance(e, str) for e in result.errors)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
