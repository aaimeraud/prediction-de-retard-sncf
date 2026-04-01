"""
Unit tests for GTFS Data Loader.

Tests cover downloading, parsing, and validating GTFS data.
Compatible with Colab and pytest execution.
"""

import os
import pytest
import pandas as pd
import tempfile
import zipfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_loader import GTFSDataLoader


@pytest.fixture
def mock_gtfs_zip():
    """
    Create a mock GTFS ZIP file for testing without internet.
    
    Returns temporary directory with mock ZIP and path.
    """
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "test_gtfs.zip")
    
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr('stops.txt', 'stop_id,stop_name,stop_lat,stop_lon\n1,Gare de Lyon,48.8426,2.3739\n2,Gare du Nord,48.8861,2.3556\n')
        zf.writestr('routes.txt', 'route_id,route_short_name,route_long_name\nR1,TER,Train Express Régional\n')
        zf.writestr('trips.txt', 'trip_id,route_id,service_id\nT1,R1,WD\n')
        zf.writestr('stop_times.txt', 'trip_id,arrival_time,departure_time,stop_id\nT1,08:00:00,08:05:00,1\nT1,08:30:00,08:30:00,2\n')
        zf.writestr('calendar.txt', 'service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\nWD,1,1,1,1,1,0,0,20260101,20261231\n')
    
    yield zip_path, temp_dir
    
    import shutil
    shutil.rmtree(temp_dir)


class TestGTFSDataLoader:
    """
    Test suite for GTFSDataLoader class.
    """

    def test_loader_initialization(self):
        """
        Test GTFSDataLoader initialization with custom cache directory.
        """
        loader = GTFSDataLoader(cache_dir="test_cache")
        assert loader.cache_dir == "test_cache"
        assert loader.gtfs_url is not None

    def test_parse_gtfs_zip(self, mock_gtfs_zip):
        """
        Test parsing mock GTFS ZIP file.
        
        Verifies that all expected tables are extracted and contain data.
        """
        zip_path, temp_dir = mock_gtfs_zip
        loader = GTFSDataLoader()
        
        data = loader.parse_gtfs_zip(zip_path)
        
        assert 'stops' in data
        assert 'routes' in data
        assert 'trips' in data
        assert 'stop_times' in data
        assert 'calendar' in data
        
        assert len(data['stops']) == 2
        assert len(data['routes']) == 1
        assert 'stop_id' in data['stops'].columns
        assert 'route_id' in data['routes'].columns

    def test_get_stops(self, mock_gtfs_zip):
        """
        Test extracting stops from GTFS data.
        """
        zip_path, temp_dir = mock_gtfs_zip
        loader = GTFSDataLoader()
        gtfs_data = loader.parse_gtfs_zip(zip_path)
        
        stops = loader.get_stops(gtfs_data)
        
        assert stops is not None
        assert isinstance(stops, pd.DataFrame)
        assert len(stops) == 2
        assert 'Gare de Lyon' in stops['stop_name'].values

    def test_get_routes(self, mock_gtfs_zip):
        """
        Test extracting routes from GTFS data.
        """
        zip_path, temp_dir = mock_gtfs_zip
        loader = GTFSDataLoader()
        gtfs_data = loader.parse_gtfs_zip(zip_path)
        
        routes = loader.get_routes(gtfs_data)
        
        assert routes is not None
        assert isinstance(routes, pd.DataFrame)
        assert len(routes) == 1
        assert 'TER' in routes['route_short_name'].values

    def test_get_stop_times(self, mock_gtfs_zip):
        """
        Test extracting stop times from GTFS data.
        """
        zip_path, temp_dir = mock_gtfs_zip
        loader = GTFSDataLoader()
        gtfs_data = loader.parse_gtfs_zip(zip_path)
        
        stop_times = loader.get_stop_times(gtfs_data)
        
        assert stop_times is not None
        assert isinstance(stop_times, pd.DataFrame)
        assert len(stop_times) == 2
        assert 'arrival_time' in stop_times.columns

    def test_parse_missing_zip_file(self):
        """
        Test that parsing missing ZIP file raises FileNotFoundError.
        """
        loader = GTFSDataLoader()
        
        with pytest.raises(FileNotFoundError):
            loader.parse_gtfs_zip("/nonexistent/path/file.zip")

    def test_cache_dir_creation(self):
        """
        Test that cache directory is created automatically.
        """
        import tempfile
        import shutil
        
        temp_dir = tempfile.mkdtemp()
        cache_dir = os.path.join(temp_dir, "new_cache")
        
        loader = GTFSDataLoader(cache_dir=cache_dir)
        assert os.path.exists(cache_dir)
        
        shutil.rmtree(temp_dir)


class TestGTFSDataIntegration:
    """
    Integration tests simulating real Colab workflow.
    """

    def test_full_pipeline_with_mock_data(self, mock_gtfs_zip):
        """
        Test complete data loading pipeline as in Colab environment.
        """
        zip_path, temp_dir = mock_gtfs_zip
        loader = GTFSDataLoader()
        
        gtfs_data = loader.parse_gtfs_zip(zip_path)
        stops = loader.get_stops(gtfs_data)
        routes = loader.get_routes(gtfs_data)
        
        assert stops is not None
        assert routes is not None
        assert len(stops) > 0
        assert len(routes) > 0
        
        assert 'stop_lat' in stops.columns
        assert 'stop_lon' in stops.columns
        assert stops.iloc[0]['stop_lat'] == pytest.approx(48.8426)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
