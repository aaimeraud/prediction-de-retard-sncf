# SNCF SIRI Real-Time Data Integration

## Overview

The SIRI (Service Interface for Real-time Information) module integrates SNCF's real-time delay API to augment static GTFS schedule data for improved ML delay predictions. This enables capturing dynamic traffic disruptions, train delays, and network-wide incidents that affect punctuality.

## Architecture

### Components

#### SIRIClient
Low-level HTTP API client for SNCF SIRI endpoints.

**Features:**
- Authentication with SNCF API key
- StopMonitoring service (real-time delays per stop)
- TrafficReports service (network-wide disruptions)
- Automatic error handling and timeout management
- Response parsing for delay extraction

**Methods:**
```python
fetch_stop_monitoring(monitoring_ref, preview_interval=3600)
    Fetch real-time delays for a specific stop
    
fetch_traffic_reports()
    Fetch network-wide traffic reports and disruptions
```

#### SIRICache
Persistent SQLite cache for historical delay observations.

**Features:**
- Automatic schema creation
- Indexed storage by trip_id and line_ref
- Time-range queries (e.g., last 24 hours)
- Automatic cleanup of entries older than 30 days

**Methods:**
```python
store_delays(delays: List[SIRIDelay]) -> int
    Persist delay observations to database
    
get_recent_delays(hours=24, line_ref=None) -> List[Dict]
    Retrieve historical delays with optional filtering
    
clear_old_entries(days=30) -> int
    Remove cache entries older than threshold
```

#### SIRICollector
High-level orchestrator combining API client, caching, and rate limiting.

**Features:**
- Rate limiting (default: 10 req/60s)
- Batch collection for multiple stops
- Network-wide delay aggregation
- Historical data retrieval
- Automatic cache cleanup

**Methods:**
```python
collect_stop_delays(monitoring_refs: List[str]) -> Dict[str, int]
    Collect delays for multiple stops and cache results
    
collect_network_delays() -> int
    Fetch network-wide traffic reports
    
get_historical_delays(hours=24, line_ref=None) -> List[Dict]
    Retrieve cached delay history
    
cleanup_cache(days=30) -> int
    Remove old cache entries
```

### Data Models

#### SIRIDelay (Dataclass)
Represents a single delay observation.

```python
@dataclass
class SIRIDelay:
    trip_id: str                      # Train trip identifier
    line_ref: str                     # Line reference (e.g., "TER100")
    departure_stop: str               # Departure station name
    arrival_stop: str                 # Arrival station name
    scheduled_departure: str          # Scheduled time (ISO 8601)
    actual_departure: Optional[str]   # Actual/Real-time time
    delay_seconds: int                # Delay in seconds (positive = late)
    vehicle_ref: str                  # Vehicle identifier
    timestamp: str                    # Observation timestamp (ISO 8601)
    source: str = "siri"             # Data source identifier
```

#### SIRIQueryResult (Dataclass)
Container for API query responses.

```python
@dataclass
class SIRIQueryResult:
    status_code: int                  # HTTP status code
    delays: List[SIRIDelay]          # Parsed delay objects
    raw_response: Dict[str, Any]     # Original API response
    query_timestamp: str              # Query execution time
    error: Optional[str] = None       # Error message if failed
```

## Usage Examples

### Basic Setup

```python
from src.siri_collector import SIRICollector

collector = SIRICollector(
    api_key="YOUR_SNCF_API_KEY",
    cache_db="data/siri_cache.db",
    rate_limit_requests=10,
    rate_limit_window=60
)
```

### Collect Stop-Level Delays

```python
stops = ["stop_paris_montparnasse", "stop_bordeaux_sncf"]
results = collector.collect_stop_delays(stops)

print(results)
# Output: {"stop_paris_montparnasse": 15, "stop_bordeaux_sncf": 8}
# (15 and 8 delays recorded for each stop)
```

### Collect Network-Wide Delays

```python
count = collector.collect_network_delays()
print(f"Recorded {count} network disruptions")
```

### Retrieve Historical Data

```python
recent_delays = collector.get_historical_delays(hours=24)

for delay in recent_delays:
    print(f"{delay['trip_id']}: {delay['delay_seconds']}s late")
```

### Filter by Line Reference

```python
ter_delays = collector.get_historical_delays(
    hours=48,
    line_ref="TER100"
)

print(f"TER100 delays (48h): {len(ter_delays)} records")
```

### Cleanup Old Cache

```python
deleted = collector.cleanup_cache(days=30)
print(f"Deleted {deleted} cache entries older than 30 days")
```

## MLB Pipeline Integration

### Feature Engineering

Real-time SIRI data augments the feature engineering pipeline:

```python
from src.siri_collector import SIRICollector
from src.feature_engineer import FeatureEngineer

collector = SIRICollector(api_key=os.getenv("SNCF_API_KEY"))
engineer = FeatureEngineer()

# Collect recent network delays (augment training data)
delays = collector.get_historical_delays(hours=1)

# Aggregate delay statistics by line
delay_by_line = {}
for delay in delays:
    line = delay['line_ref']
    delay_by_line[line] = delay_by_line.get(line, 0) + delay['delay_seconds']

# Use as additional feature
features = engineer.extract_features(trips_data)
features['avg_network_delay_1h'] = [
    delay_by_line.get(trip['line_ref'], 0) for trip in trips_data
]
```

### Training Pipeline

```python
from src.model_training import ModelTrainingPipeline
from src.siri_collector import SIRICollector

collector = SIRICollector(api_key=os.getenv("SNCF_API_KEY"))
pipeline = ModelTrainingPipeline()

# Collect real-time data before training
network_delays = collector.collect_network_delays()

# Train with augmented data
model = pipeline.train({
    'gtfs_data': gtfs,
    'network_disruptions': network_delays,
    'target_delay': delay_labels
})
```

## Testing

### Run Unit Tests

```bash
python3 -m pytest tests/test_siri_collector.py -v
```

### Run Integration Tests

```bash
python3 -m pytest tests/test_siri_collector.py::TestSIRIIntegration -v
```

### Expected Results

```
27 tests collected
├── TestSIRIDelay (2 tests)
├── TestSIRIQueryResult (2 tests)
├── TestSIRIClient (6 tests)
├── TestSIRICache (6 tests)
├── TestSIRICollector (8 tests)
└── TestSIRIIntegration (2 tests)

Status: ALL PASSING ✅
```

## Database Schema

### siri_delays Table

```sql
CREATE TABLE siri_delays (
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
);

CREATE INDEX idx_trip_timestamp ON siri_delays (trip_id, created_at);
CREATE INDEX idx_line_timestamp ON siri_delays (line_ref, created_at);
```

## Configuration

### Environment Variables

```bash
SNCF_API_KEY=your_api_key_here      # SNCF SIRI API authentication
SIRI_CACHE_DB=data/siri_cache.db    # Cache database path
SIRI_RATE_LIMIT=10                  # Max requests per window
SIRI_RATE_WINDOW=60                 # Rate limit window (seconds)
```

### Docker Compose

The SIRI collector is pre-configured in `compose.yaml`:

```yaml
services:
  ml-engine:
    environment:
      - SNCF_API_KEY=${SNCF_API_KEY}
    volumes:
      - ./data:/app/data   # Persistent cache storage
```

## Performance Considerations

### Rate Limiting
- Default: 10 requests per 60 seconds
- Token-bucket algorithm prevents API throttling
- Configurable per SIRICollector instance

### Caching Strategy
- Automatically indexes by trip_id and line_ref
- 30-day retention (configurable)
- Cleanup runs on-demand or via scheduler

### Database Performance
- SQLite indices optimize time-range queries
- Batch insertion reduces I/O overhead
- Vacuum recommended monthly

## Troubleshooting

### Connection Timeout
```python
# Increase timeout (default 10s for stop monitoring, 15s for reports)
client = SIRIClient(api_key, base_url="...")
# Timeout is hardcoded; adjust in fetch_stop_monitoring() if needed
```

### Rate Limiting Delays
```python
# Adjust rate limiting
collector.rate_limit_requests = 20
collector.rate_limit_window = 60
```

### Cache Size Growth
```python
# Cleanup old entries
collector.cleanup_cache(days=7)  # Keep only 7 days
```

## Future Enhancements

1. **Async Collection**: async/await for parallel stop monitoring
2. **WebSocket Support**: Real-time event streaming (if SNCF supports)
3. **Prediction Feedback Loop**: Use SIRI data to validate model predictions
4. **Alert System**: Trigger alerts when delays exceed thresholds
5. **Dashboard Widget**: Real-time delay visualization in Streamlit

## References

- SNCF Open Data: https://data.sncf.com
- SIRI Standard: https://www.ifopt.org.uk/siri/
- API Documentation: Contact SNCF data team
