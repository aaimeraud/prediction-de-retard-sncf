"""
Unit and integration tests for SIRI collector module.

Tests cover API client communication, response parsing, caching, 
rate limiting, and end-to-end collector orchestration.
"""

import pytest
import json
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from src.siri_collector import (
    SIRIDelay,
    SIRIQueryResult,
    SIRIClient,
    SIRICache,
    SIRICollector
)


class TestSIRIDelay:
    """Test SIRIDelay dataclass initialization and serialization."""

    def test_delay_initialization(self):
        """Test creating a SIRIDelay object with all fields."""
        delay = SIRIDelay(
            trip_id="SNCF_123",
            line_ref="TER001",
            departure_stop="Paris-Montparnasse",
            arrival_stop="Bordeaux",
            scheduled_departure="2026-04-04T14:00:00Z",
            actual_departure="2026-04-04T14:15:00Z",
            delay_seconds=900,
            vehicle_ref="VH_001"
        )
        
        assert delay.trip_id == "SNCF_123"
        assert delay.delay_seconds == 900
        assert delay.source == "siri"
        assert isinstance(delay.timestamp, str)

    def test_delay_default_timestamp(self):
        """Test that timestamp is auto-generated if not provided."""
        delay = SIRIDelay(
            trip_id="TEST",
            line_ref="L1",
            departure_stop="A",
            arrival_stop="B",
            scheduled_departure="T1",
            actual_departure=None,
            delay_seconds=0,
            vehicle_ref="V1"
        )
        
        assert delay.timestamp is not None
        datetime.fromisoformat(delay.timestamp)


class TestSIRIQueryResult:
    """Test SIRIQueryResult container for API responses."""

    def test_query_result_success(self):
        """Test successful query result."""
        delays = [
            SIRIDelay("T1", "L1", "A", "B", "T1", "T2", 300, "V1"),
            SIRIDelay("T2", "L1", "B", "C", "T3", "T4", 600, "V2")
        ]
        
        result = SIRIQueryResult(
            status_code=200,
            delays=delays,
            raw_response={"status": "ok"}
        )
        
        assert result.status_code == 200
        assert len(result.delays) == 2
        assert result.error is None

    def test_query_result_error(self):
        """Test query result with error."""
        result = SIRIQueryResult(
            status_code=500,
            delays=[],
            raw_response={},
            error="API timeout"
        )
        
        assert result.status_code == 500
        assert len(result.delays) == 0
        assert result.error == "API timeout"


class TestSIRIClient:
    """Test SIRI API client functionality."""

    @pytest.fixture
    def client(self):
        """Create a SIRI client instance."""
        return SIRIClient(api_key="test_key_12345")

    def test_client_initialization(self, client):
        """Test SIRI client initialization."""
        assert client.api_key == "test_key_12345"
        assert "Bearer test_key_12345" in client.session.headers["Authorization"]

    @patch("requests.Session.get")
    def test_fetch_stop_monitoring_success(self, mock_get, client):
        """Test successful stop monitoring API call."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "stop_schedules": [
                {
                    "trip": {"id": "TRIP_001"},
                    "route": {"name": "TER100"},
                    "stop_point": {"name": "Paris"},
                    "date_times": [
                        {
                            "arrival_date_time": "2026-04-04T14:00:00Z",
                            "base_arrival_date_time": "2026-04-04T14:00:00Z",
                            "data_freshness": "realtime"
                        }
                    ],
                    "vehicle_journeys": [{"id": "VJ_001"}]
                }
            ]
        }
        mock_get.return_value = mock_response
        
        result = client.fetch_stop_monitoring("stop_123")
        
        assert result.status_code == 200
        assert isinstance(result.delays, list)
        mock_get.assert_called_once()

    @patch("requests.Session.get")
    def test_fetch_stop_monitoring_timeout(self, mock_get, client):
        """Test stop monitoring API timeout handling."""
        import requests
        mock_get.side_effect = requests.Timeout("Connection timeout")
        
        result = client.fetch_stop_monitoring("stop_123")
        
        assert result.status_code == 0
        assert len(result.delays) == 0
        assert result.error is not None

    @patch("requests.Session.get")
    def test_fetch_traffic_reports_success(self, mock_get, client):
        """Test successful traffic reports API call."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "disruptions": [
                {
                    "severity": "Severe",
                    "route": {"name": "TER100"},
                    "status": "Incident",
                    "impact": "Line disrupted",
                    "updated_at": "2026-04-04T10:00:00Z"
                }
            ]
        }
        mock_get.return_value = mock_response
        
        result = client.fetch_traffic_reports()
        
        assert result.status_code == 200
        assert isinstance(result.delays, list)

    def test_calculate_delay(self):
        """Test delay calculation from passage data."""
        passage = {
            "arrival_date_time": "2026-04-04T14:00:00Z",
            "base_arrival_date_time": "2026-04-04T14:15:00Z"
        }
        
        delay = SIRIClient._calculate_delay(passage)
        
        assert delay == 900

    def test_calculate_delay_no_times(self):
        """Test delay calculation with missing data."""
        passage = {"arrival_date_time": None, "base_arrival_date_time": None}
        
        delay = SIRIClient._calculate_delay(passage)
        
        assert delay == 0

    def test_estimate_delay_from_disruption_severe(self):
        """Test delay estimation from severe disruption."""
        disruption = {"severity": "Severe"}
        
        delay = SIRIClient._estimate_delay_from_disruption(disruption)
        
        assert delay == 600

    def test_estimate_delay_from_disruption_normal(self):
        """Test delay estimation from normal disruption."""
        disruption = {"severity": "Normal"}
        
        delay = SIRIClient._estimate_delay_from_disruption(disruption)
        
        assert delay == 300


class TestSIRICache:
    """Test SIRI cache database operations."""

    @pytest.fixture
    def temp_cache(self):
        """Create temporary cache database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = os.path.join(tmpdir, "test_cache.db")
            yield SIRICache(cache_path)

    def test_cache_initialization(self, temp_cache):
        """Test cache database initialization."""
        assert os.path.exists(temp_cache.cache_db)
        
        conn = sqlite3.connect(temp_cache.cache_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='siri_delays'")
        assert cursor.fetchone() is not None
        conn.close()

    def test_store_single_delay(self, temp_cache):
        """Test storing a single delay record."""
        delay = SIRIDelay(
            trip_id="T1",
            line_ref="L1",
            departure_stop="Stop1",
            arrival_stop="Stop2",
            scheduled_departure="2026-04-04T10:00:00",
            actual_departure="2026-04-04T10:15:00",
            delay_seconds=900,
            vehicle_ref="V1"
        )
        
        rows = temp_cache.store_delays([delay])
        
        assert rows == 1

    def test_store_multiple_delays(self, temp_cache):
        """Test storing multiple delay records."""
        delays = [
            SIRIDelay("T1", "L1", "A", "B", "T1", "T2", 300, "V1"),
            SIRIDelay("T2", "L1", "B", "C", "T3", "T4", 600, "V2"),
            SIRIDelay("T3", "L2", "C", "D", "T5", "T6", 450, "V3")
        ]
        
        rows = temp_cache.store_delays(delays)
        
        assert rows == 3

    def test_get_recent_delays(self, temp_cache):
        """Test retrieving recent delay records."""
        delay = SIRIDelay("T1", "L1", "A", "B", "T1", "T2", 300, "V1")
        temp_cache.store_delays([delay])
        
        recent = temp_cache.get_recent_delays(hours=24)
        
        assert len(recent) == 1
        assert recent[0]["trip_id"] == "T1"

    def test_get_recent_delays_with_line_filter(self, temp_cache):
        """Test retrieving recent delays filtered by line."""
        delays = [
            SIRIDelay("T1", "L1", "A", "B", "T1", "T2", 300, "V1"),
            SIRIDelay("T2", "L2", "B", "C", "T3", "T4", 600, "V2")
        ]
        temp_cache.store_delays(delays)
        
        L1_delays = temp_cache.get_recent_delays(line_ref="L1")
        
        assert len(L1_delays) == 1
        assert L1_delays[0]["line_ref"] == "L1"

    def test_clear_old_entries(self, temp_cache):
        """Test clearing old cache entries."""
        delay = SIRIDelay("T1", "L1", "A", "B", "T1", "T2", 300, "V1")
        temp_cache.store_delays([delay])
        
        initial_count = len(temp_cache.get_recent_delays(hours=24))
        assert initial_count == 1
        
        deleted = temp_cache.clear_old_entries(days=0)
        
        final_count = len(temp_cache.get_recent_delays(hours=24))
        assert deleted >= 1
        assert final_count == 0


class TestSIRICollector:
    """Test high-level SIRI collector orchestration."""

    @pytest.fixture
    def temp_collector(self):
        """Create temporary collector instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = os.path.join(tmpdir, "collector_cache.db")
            yield SIRICollector(
                api_key="test_key",
                cache_db=cache_path,
                rate_limit_requests=5,
                rate_limit_window=1
            )

    def test_collector_initialization(self, temp_collector):
        """Test collector initialization."""
        assert temp_collector.client is not None
        assert temp_collector.cache is not None
        assert temp_collector.rate_limit_requests == 5

    @patch.object(SIRIClient, "fetch_stop_monitoring")
    def test_collect_stop_delays_success(self, mock_fetch, temp_collector):
        """Test collecting delays for multiple stops."""
        mock_delay = SIRIDelay("T1", "L1", "A", "B", "T1", "T2", 300, "V1")
        mock_result = SIRIQueryResult(200, [mock_delay], {})
        mock_fetch.return_value = mock_result
        
        results = temp_collector.collect_stop_delays(["stop_1", "stop_2"])
        
        assert "stop_1" in results
        assert "stop_2" in results

    @patch.object(SIRIClient, "fetch_traffic_reports")
    def test_collect_network_delays(self, mock_fetch, temp_collector):
        """Test collecting network-wide delays."""
        mock_delay = SIRIDelay("T1", "L1", "A", "B", "T1", "T2", 300, "V1")
        mock_result = SIRIQueryResult(200, [mock_delay], {})
        mock_fetch.return_value = mock_result
        
        stored = temp_collector.collect_network_delays()
        
        assert stored == 1

    def test_get_historical_delays(self, temp_collector):
        """Test retrieving historical delays."""
        delay = SIRIDelay("T1", "L1", "A", "B", "T1", "T2", 300, "V1")
        temp_collector.cache.store_delays([delay])
        
        historical = temp_collector.get_historical_delays(hours=24)
        
        assert len(historical) == 1
        assert historical[0]["trip_id"] == "T1"

    def test_cleanup_cache(self, temp_collector):
        """Test cache cleanup functionality."""
        delay = SIRIDelay("T1", "L1", "A", "B", "T1", "T2", 300, "V1")
        temp_collector.cache.store_delays([delay])
        
        deleted = temp_collector.cleanup_cache(days=0)
        
        assert deleted >= 1

    def test_rate_limiting(self, temp_collector):
        """Test rate limiting implementation."""
        import time
        
        temp_collector.rate_limit_requests = 2
        temp_collector.rate_limit_window = 1
        
        start = time.time()
        temp_collector._apply_rate_limit()
        temp_collector._apply_rate_limit()
        temp_collector._apply_rate_limit()
        
        elapsed = time.time() - start
        
        assert elapsed >= 1

    def test_rate_limit_request_tracking(self, temp_collector):
        """Test request time tracking for rate limiting."""
        temp_collector._apply_rate_limit()
        temp_collector._apply_rate_limit()
        
        assert len(temp_collector._request_times) == 2


class TestSIRIIntegration:
    """Integration tests for SIRI collector end-to-end workflows."""

    @pytest.fixture
    def integration_collector(self):
        """Create collector for integration testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = os.path.join(tmpdir, "integration_cache.db")
            yield SIRICollector(
                api_key="test_integration_key",
                cache_db=cache_path
            )

    @patch.object(SIRIClient, "fetch_stop_monitoring")
    @patch.object(SIRIClient, "fetch_traffic_reports")
    def test_end_to_end_collection_workflow(
        self,
        mock_traffic,
        mock_stop,
        integration_collector
    ):
        """Test complete workflow from collection to retrieval."""
        delay = SIRIDelay("T1", "L1", "Paris", "Lyon", "T1", "T2", 600, "V1")
        
        mock_stop.return_value = SIRIQueryResult(200, [delay], {})
        mock_traffic.return_value = SIRIQueryResult(200, [delay], {})
        
        stop_results = integration_collector.collect_stop_delays(["stop_1"])
        network_count = integration_collector.collect_network_delays()
        
        historical = integration_collector.get_historical_delays(hours=24)
        
        assert stop_results["stop_1"] >= 1
        assert network_count >= 1
        assert len(historical) >= 2

    def test_cache_persistence_across_collections(self, integration_collector):
        """Test that cache persists data across collection runs."""
        delay1 = SIRIDelay("T1", "L1", "A", "B", "T1", "T2", 300, "V1")
        delay2 = SIRIDelay("T2", "L2", "C", "D", "T3", "T4", 600, "V2")
        
        integration_collector.cache.store_delays([delay1])
        retrieved_1 = len(integration_collector.get_historical_delays())
        
        integration_collector.cache.store_delays([delay2])
        retrieved_2 = len(integration_collector.get_historical_delays())
        
        assert retrieved_2 > retrieved_1
        assert retrieved_2 == 2
