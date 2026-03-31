"""
GTFS Data Loader Module.

This module handles downloading and parsing GTFS (General Transit Feed Specification) 
data from SNCF open data sources. It downloads GTFS ZIP files, extracts relevant CSV files,
and loads them into pandas DataFrames for ML pipeline consumption.
"""

import os
import io
import zipfile
import requests
import pandas as pd
from typing import Dict, Optional


class GTFSDataLoader:
    """
    GTFS data loader for downloading and parsing SNCF schedules.
    
    Downloads GTFS ZIP files from configured URLs, extracts CSV files,
    and provides structured access to stops, routes, trips, and schedules.
    """

    def __init__(self, cache_dir: str = "data/cache"):
        """
        Initialize GTFS data loader.
        
        Args:
            cache_dir: Directory to cache downloaded GTFS files.
        """
        self.cache_dir = cache_dir
        self.gtfs_url = "https://eu.ftp.opendatasoft.com/sncf/plandata/Export_OpenData_SNCF_GTFS_NewTripId.zip"
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """
        Create cache directory if it does not exist.
        """
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)

    def download_gtfs(self, force_download: bool = False) -> str:
        """
        Download GTFS ZIP file from SNCF open data.
        
        Args:
            force_download: If True, re-download even if cached.
            
        Returns:
            Path to the downloaded ZIP file.
            
        Raises:
            requests.RequestException: If download fails.
        """
        cache_path = os.path.join(self.cache_dir, "sncf_gtfs.zip")
        
        if os.path.exists(cache_path) and not force_download:
            return cache_path
        
        try:
            response = requests.get(self.gtfs_url, timeout=30)
            response.raise_for_status()
            
            with open(cache_path, 'wb') as f:
                f.write(response.content)
            
            return cache_path
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to download GTFS data: {str(e)}") from e

    def parse_gtfs_zip(self, zip_path: str) -> Dict[str, pd.DataFrame]:
        """
        Parse GTFS ZIP file and extract data into DataFrames.
        
        Extracts key GTFS files: stops, routes, trips, stop_times, calendar.
        
        Args:
            zip_path: Path to GTFS ZIP file.
            
        Returns:
            Dictionary with DataFrames keyed by table name.
            
        Raises:
            FileNotFoundError: If ZIP file does not exist.
            zipfile.BadZipFile: If ZIP file is corrupted.
        """
        if not os.path.exists(zip_path):
            raise FileNotFoundError(f"ZIP file not found: {zip_path}")
        
        data = {}
        required_files = {
            'stops.txt': 'stops',
            'routes.txt': 'routes',
            'trips.txt': 'trips',
            'stop_times.txt': 'stop_times',
            'calendar.txt': 'calendar'
        }
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                for file_name, table_name in required_files.items():
                    try:
                        with zf.open(file_name) as f:
                            data[table_name] = pd.read_csv(f)
                    except KeyError:
                        pass
            
            return data
        except zipfile.BadZipFile as e:
            raise RuntimeError(f"Corrupted ZIP file: {str(e)}") from e

    def load_gtfs(self, force_download: bool = False) -> Dict[str, pd.DataFrame]:
        """
        Download and parse GTFS data in one operation.
        
        Args:
            force_download: If True, force re-download of GTFS.
            
        Returns:
            Dictionary of DataFrames for GTFS tables.
            
        Raises:
            RuntimeError: If download or parsing fails.
        """
        zip_path = self.download_gtfs(force_download=force_download)
        return self.parse_gtfs_zip(zip_path)

    def get_stops(self, gtfs_data: Dict[str, pd.DataFrame]) -> Optional[pd.DataFrame]:
        """
        Extract stops DataFrame from GTFS data.
        
        Args:
            gtfs_data: Dictionary output from load_gtfs().
            
        Returns:
            DataFrame with stop information or None if not available.
        """
        return gtfs_data.get('stops')

    def get_routes(self, gtfs_data: Dict[str, pd.DataFrame]) -> Optional[pd.DataFrame]:
        """
        Extract routes DataFrame from GTFS data.
        
        Args:
            gtfs_data: Dictionary output from load_gtfs().
            
        Returns:
            DataFrame with route information or None if not available.
        """
        return gtfs_data.get('routes')

    def get_stop_times(self, gtfs_data: Dict[str, pd.DataFrame]) -> Optional[pd.DataFrame]:
        """
        Extract stop_times DataFrame from GTFS data.
        
        Args:
            gtfs_data: Dictionary output from load_gtfs().
            
        Returns:
            DataFrame with stop times information or None if not available.
        """
        return gtfs_data.get('stop_times')
