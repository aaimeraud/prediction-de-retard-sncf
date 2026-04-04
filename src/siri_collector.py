"""
SNCF SIRI Real-Time Data Collector Module.

This module handles real-time collection of SNCF delay data via the SIRI API endpoint.
It provides querying, caching, rate limiting, and persistence of real-time traffic information
to augment the static GTFS schedule data for improved delay predictions.
"""

import os
import json
import time
import sqlite3
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
import requests
from urllib.parse import urlencode


logger = logging.getLogger(__name__)


@dataclass
class SIRIDelay:
    """
    Represents a single delay observation from SNCF SIRI feed.
    """
    trip_id: str
    line_ref: str
    departure_stop: str
    arrival_stop: str
    scheduled_departure: str
    actual_departure: Optional[str]
    delay_seconds: int
    vehicle_ref: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    source: str = "siri"


@dataclass
class SIRIQueryResult:
    """
    Result container for SIRI API query responses.
    """
    status_code: int
    delays: List[SIRIDelay]
    raw_response: Dict[str, Any]
    query_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    error: Optional[str] = None


class SIRIClient:
    """
    Low-level SNCF SIRI API client.
    
    Handles HTTP communication with SNCF SIRI endpoints, including request building,
    response parsing, and error handling.
    """

    def __init__(self, api_key: str, base_url: str = "https://api.sncf.com/v1"):
        """
        Initialize SIRI API client.
        
        Args:
            api_key: SNCF API authentication key.
            base_url: Base URL for SNCF API endpoints.
        """
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    def fetch_stop_monitoring(
        self,
        monitoring_ref: str,
        preview_interval: int = 3600
    ) -> SIRIQueryResult:
        """
        Fetch stop monitoring data from SIRI StopMonitoring service.
        
        Args:
            monitoring_ref: Stop reference ID (SNCF stop code).
            preview_interval: Seconds ahead to include arrivals (default 3600=1 hour).
            
        Returns:
            SIRIQueryResult containing parsed delays or error information.
        """
        endpoint = f"{self.base_url}/coverage/sncf/stop_areas/{monitoring_ref}/stop_schedules"
        
        try:
            response = self.session.get(
                endpoint,
                params={"data_freshness": "realtime"},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            delays = self._parse_stop_monitoring_response(data)
            
            return SIRIQueryResult(
                status_code=response.status_code,
                delays=delays,
                raw_response=data
            )
        except requests.RequestException as e:
            logger.error(f"SIRI API request failed: {e}")
            return SIRIQueryResult(
                status_code=getattr(e.response, "status_code", 0),
                delays=[],
                raw_response={},
                error=str(e)
            )

    def fetch_traffic_reports(self) -> SIRIQueryResult:
        """
        Fetch network-wide traffic reports and disruptions.
        
        Returns:
            SIRIQueryResult containing network status and known delays.
        """
        endpoint = f"{self.base_url}/coverage/sncf/traffic_reports"
        
        try:
            response = self.session.get(endpoint, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            delays = self._parse_traffic_reports_response(data)
            
            return SIRIQueryResult(
                status_code=response.status_code,
                delays=delays,
                raw_response=data
            )
        except requests.RequestException as e:
            logger.error(f"SIRI traffic reports failed: {e}")
            return SIRIQueryResult(
                status_code=getattr(e.response, "status_code", 0),
                delays=[],
                raw_response={},
                error=str(e)
            )

    def _parse_stop_monitoring_response(self, data: Dict) -> List[SIRIDelay]:
        """
        Parse stop monitoring response into SIRIDelay objects.
        
        Args:
            data: JSON response from stop monitoring endpoint.
            
        Returns:
            List of parsed SIRIDelay objects.
        """
        delays = []
        
        try:
            schedules = data.get("stop_schedules", [])
            for schedule in schedules:
                trip_id = schedule.get("trip", {}).get("id", "unknown")
                line_ref = schedule.get("route", {}).get("name", "unknown")
                
                passages = schedule.get("date_times", [])
                for passage in passages:
                    delay_seconds = passage.get("data_freshness") == "realtime" and \
                                    self._calculate_delay(passage) or 0
                    
                    if delay_seconds != 0:
                        delays.append(SIRIDelay(
                            trip_id=trip_id,
                            line_ref=line_ref,
                            departure_stop=schedule.get("stop_point", {}).get("name", ""),
                            arrival_stop="TBD",
                            scheduled_departure=passage.get("arrival_date_time", ""),
                            actual_departure=passage.get("base_arrival_date_time", ""),
                            delay_seconds=delay_seconds,
                            vehicle_ref=schedule.get("vehicle_journeys", [{}])[0].get("id", "")
                        ))
        except (KeyError, IndexError, TypeError) as e:
            logger.warning(f"Error parsing stop monitoring response: {e}")
        
        return delays

    def _parse_traffic_reports_response(self, data: Dict) -> List[SIRIDelay]:
        """
        Parse traffic reports response into delay objects.
        
        Args:
            data: JSON response from traffic reports endpoint.
            
        Returns:
            List of parsed SIRIDelay objects.
        """
        delays = []
        
        try:
            disruptions = data.get("disruptions", [])
            for disruption in disruptions:
                if disruption.get("severity") in ["Severe", "Normal"]:
                    delay_info = SIRIDelay(
                        trip_id="network",
                        line_ref=disruption.get("route", {}).get("name", "ALL"),
                        departure_stop=disruption.get("status", "unknown"),
                        arrival_stop=disruption.get("impact", ""),
                        scheduled_departure=disruption.get("updated_at", ""),
                        actual_departure=None,
                        delay_seconds=self._estimate_delay_from_disruption(disruption),
                        vehicle_ref="network"
                    )
                    delays.append(delay_info)
        except (KeyError, TypeError) as e:
            logger.warning(f"Error parsing traffic reports: {e}")
        
        return delays

    @staticmethod
    def _calculate_delay(passage: Dict) -> int:
        """
        Calculate delay in seconds from passage timing data.
        
        Args:
            passage: Passage timing information from SIRI response.
            
        Returns:
            Delay in seconds (positive = late, negative = early).
        """
        scheduled_time = passage.get("arrival_date_time")
        actual_time = passage.get("base_arrival_date_time")
        
        if scheduled_time and actual_time:
            try:
                scheduled = datetime.fromisoformat(scheduled_time.replace("Z", "+00:00"))
                actual = datetime.fromisoformat(actual_time.replace("Z", "+00:00"))
                return int((actual - scheduled).total_seconds())
            except ValueError:
                return 0
        
        return 0

    @staticmethod
    def _estimate_delay_from_disruption(disruption: Dict) -> int:
        """
        Estimate delay from disruption severity and impact.
        
        Args:
            disruption: Disruption object from traffic reports.
            
        Returns:
            Estimated delay in seconds based on severity.
        """
        severity_map = {
            "Severe": 600,
            "Normal": 300,
            "Minor": 60,
            "Unknown": 0
        }
        severity = disruption.get("severity", "Unknown")
        return severity_map.get(severity, 0)


class SIRICache:
    """
    Persistent cache for SIRI API responses using SQLite.
    
    Stores collected delay observations with timestamps for historical analysis
    and deduplication across multiple collection runs.
    """

    def __init__(self, cache_db: str = "data/siri_cache.db"):
        """
        Initialize SIRI cache database.
        
        Args:
            cache_db: Path to SQLite database file for persistence.
        """
        self.cache_db = cache_db
        self._ensure_db()

    def _ensure_db(self) -> None:
        """
        Create SQLite database and tables if they don't exist.
        """
        os.makedirs(os.path.dirname(self.cache_db) or ".", exist_ok=True)
        
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS siri_delays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id TEXT NOT NULL,
                line_ref TEXT NOT NULL,
                departure_stop TEXT,
                arrival_stop TEXT,
                scheduled_departure TEXT,
                actual_departure TEXT,
                delay_seconds INTEGER,
                vehicle_ref TEXT,
                timestamp TEXT NOT NULL,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trip_timestamp 
            ON siri_delays (trip_id, created_at)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_line_timestamp 
            ON siri_delays (line_ref, created_at)
        """)
        
        conn.commit()
        conn.close()

    def store_delays(self, delays: List[SIRIDelay]) -> int:
        """
        Store delay observations in cache database.
        
        Args:
            delays: List of SIRIDelay objects to persist.
            
        Returns:
            Number of rows inserted.
        """
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        rows_inserted = 0
        for delay in delays:
            try:
                cursor.execute("""
                    INSERT INTO siri_delays (
                        trip_id, line_ref, departure_stop, arrival_stop,
                        scheduled_departure, actual_departure, delay_seconds,
                        vehicle_ref, timestamp, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    delay.trip_id, delay.line_ref, delay.departure_stop,
                    delay.arrival_stop, delay.scheduled_departure,
                    delay.actual_departure, delay.delay_seconds,
                    delay.vehicle_ref, delay.timestamp, delay.source
                ))
                rows_inserted += 1
            except sqlite3.IntegrityError as e:
                logger.warning(f"Failed to insert delay record: {e}")
        
        conn.commit()
        conn.close()
        
        return rows_inserted

    def get_recent_delays(
        self,
        hours: int = 24,
        line_ref: Optional[str] = None
    ) -> List[Dict]:
        """
        Retrieve recent delay observations from cache.
        
        Args:
            hours: Number of hours to look back (default 24).
            line_ref: Filter by specific line reference (optional).
            
        Returns:
            List of delay dictionaries from database.
        """
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        query = "SELECT * FROM siri_delays WHERE created_at > ?"
        params = [cutoff_time.isoformat()]
        
        if line_ref:
            query += " AND line_ref = ?"
            params.append(line_ref)
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]

    def clear_old_entries(self, days: int = 30) -> int:
        """
        Remove cache entries older than specified number of days.
        
        Args:
            days: Age threshold in days (default 30).
            
        Returns:
            Number of rows deleted.
        """
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        cursor.execute(
            "DELETE FROM siri_delays WHERE created_at < ?",
            (cutoff_time.isoformat(),)
        )
        
        rows_deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        return rows_deleted


class SIRICollector:
    """
    High-level orchestrator for SNCF SIRI real-time delay collection.
    
    Manages API client, caching, rate limiting, and scheduling of delay data collection
    for ML pipeline augmentation. Provides both on-demand and scheduled collection modes.
    """

    def __init__(
        self,
        api_key: str,
        cache_db: str = "data/siri_cache.db",
        rate_limit_requests: int = 10,
        rate_limit_window: int = 60
    ):
        """
        Initialize SIRI data collector.
        
        Args:
            api_key: SNCF API authentication key.
            cache_db: Path to SQLite cache database.
            rate_limit_requests: Max requests per rate_limit_window.
            rate_limit_window: Seconds for rate limiting window.
        """
        self.client = SIRIClient(api_key)
        self.cache = SIRICache(cache_db)
        self.rate_limit_requests = rate_limit_requests
        self.rate_limit_window = rate_limit_window
        self._request_times = []

    def collect_stop_delays(self, monitoring_refs: List[str]) -> Dict[str, int]:
        """
        Collect delay data for multiple stops.
        
        Args:
            monitoring_refs: List of SNCF stop reference IDs.
            
        Returns:
            Dictionary with stop_id -> delays_found count.
        """
        results = {}
        
        for stop_ref in monitoring_refs:
            self._apply_rate_limit()
            
            query_result = self.client.fetch_stop_monitoring(stop_ref)
            
            if query_result.status_code == 200:
                stored = self.cache.store_delays(query_result.delays)
                results[stop_ref] = stored
                logger.info(f"Collected {stored} delays for stop {stop_ref}")
            else:
                results[stop_ref] = 0
                logger.error(f"Failed to collect delays for {stop_ref}: {query_result.error}")
        
        return results

    def collect_network_delays(self) -> int:
        """
        Collect network-wide traffic reports and disruptions.
        
        Returns:
            Number of delay records stored.
        """
        self._apply_rate_limit()
        
        query_result = self.client.fetch_traffic_reports()
        
        if query_result.status_code == 200:
            stored = self.cache.store_delays(query_result.delays)
            logger.info(f"Collected {stored} network-wide delays")
            return stored
        else:
            logger.error(f"Failed to collect network delays: {query_result.error}")
            return 0

    def get_historical_delays(
        self,
        hours: int = 24,
        line_ref: Optional[str] = None
    ) -> List[Dict]:
        """
        Retrieve historical delay observations from cache.
        
        Args:
            hours: Number of hours to look back.
            line_ref: Optional filter by line reference.
            
        Returns:
            List of historical delay records.
        """
        return self.cache.get_recent_delays(hours=hours, line_ref=line_ref)

    def cleanup_cache(self, days: int = 30) -> int:
        """
        Remove old entries from cache database.
        
        Args:
            days: Age threshold for deletion.
            
        Returns:
            Number of rows deleted.
        """
        deleted = self.cache.clear_old_entries(days=days)
        logger.info(f"Cleaned up {deleted} old cache entries")
        return deleted

    def _apply_rate_limit(self) -> None:
        """
        Apply token-bucket rate limiting to API requests.
        """
        now = time.time()
        
        self._request_times = [t for t in self._request_times if now - t < self.rate_limit_window]
        
        if len(self._request_times) >= self.rate_limit_requests:
            sleep_time = self.rate_limit_window - (now - self._request_times[0])
            if sleep_time > 0:
                logger.info(f"Rate limit reached, sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
        
        self._request_times.append(now)
