"""
A/B Testing Framework Module.

Provides statistical analysis for comparing model versions against production baseline.
Supports significance testing and traffic allocation strategies.
"""

import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import sqlite3


logger = logging.getLogger(__name__)


class ExperimentStatus(Enum):
    """Experiment lifecycle status."""
    PLANNED = "planned"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class TrafficAllocationStrategy(Enum):
    """Traffic allocation strategies for A/B testing."""
    UNIFORM = "uniform"
    WEIGHTED = "weighted"
    CANARY = "canary"
    PROGRESSIVE = "progressive"


@dataclass
class Experiment:
    """
    A/B test experiment configuration and state.
    """
    experiment_id: str
    name: str
    baseline_model_id: str
    baseline_version: str
    candidate_model_id: str
    candidate_version: str
    start_date: str
    end_date: Optional[str] = None
    status: ExperimentStatus = ExperimentStatus.PLANNED
    traffic_allocation_strategy: TrafficAllocationStrategy = TrafficAllocationStrategy.UNIFORM
    baseline_traffic_pct: float = 50.0
    candidate_traffic_pct: float = 50.0
    primary_metric: str = "accuracy"
    confidence_level: float = 0.95
    minimum_sample_size: int = 1000
    description: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class ObservationData:
    """
    Single observation during A/B test.
    """
    experiment_id: str
    timestamp: str
    model_version: str
    prediction: float
    actual: Optional[float]
    delay_minutes: Optional[int]
    accuracy: Optional[bool] = None
    trip_id: Optional[str] = None
    line_ref: Optional[str] = None


@dataclass
class ExperimentResults:
    """
    Statistical results summary of A/B test.
    """
    experiment_id: str
    baseline_metric: float
    candidate_metric: float
    improvement_pct: float
    p_value: float
    confidence_interval: Tuple[float, float]
    is_significant: bool
    sample_size: int
    completed_at: str
    recommendation: str


class ExperimentTracker:
    """
    Tracks and manages A/B test experiments.
    """

    def __init__(self, db_path: str = "data/ab_experiments.db"):
        """
        Initialize experiment tracker.

        Args:
            db_path: Path to SQLite database.
        """
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self) -> None:
        """Create experiment database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                baseline_model_id TEXT NOT NULL,
                baseline_version TEXT NOT NULL,
                candidate_model_id TEXT NOT NULL,
                candidate_version TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT,
                status TEXT DEFAULT 'planned',
                traffic_allocation_strategy TEXT,
                baseline_traffic_pct REAL DEFAULT 50.0,
                candidate_traffic_pct REAL DEFAULT 50.0,
                primary_metric TEXT DEFAULT 'accuracy',
                confidence_level REAL DEFAULT 0.95,
                minimum_sample_size INTEGER DEFAULT 1000,
                description TEXT,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiment_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                model_version TEXT NOT NULL,
                prediction REAL,
                actual REAL,
                delay_minutes INTEGER,
                accuracy BOOLEAN,
                trip_id TEXT,
                line_ref TEXT,
                FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiment_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT UNIQUE NOT NULL,
                baseline_metric REAL,
                candidate_metric REAL,
                improvement_pct REAL,
                p_value REAL,
                confidence_interval_lower REAL,
                confidence_interval_upper REAL,
                is_significant BOOLEAN,
                sample_size INTEGER,
                completed_at TEXT,
                recommendation TEXT,
                FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_experiment_status
            ON experiments (status)
        """)

        conn.commit()
        conn.close()

    def create_experiment(self, experiment: Experiment) -> bool:
        """
        Create new A/B test experiment.

        Args:
            experiment: Experiment configuration.

        Returns:
            Success status.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO experiments (
                    experiment_id, name, baseline_model_id, baseline_version,
                    candidate_model_id, candidate_version, start_date,
                    status, traffic_allocation_strategy, baseline_traffic_pct,
                    candidate_traffic_pct, primary_metric, confidence_level,
                    minimum_sample_size, description, tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                experiment.experiment_id,
                experiment.name,
                experiment.baseline_model_id,
                experiment.baseline_version,
                experiment.candidate_model_id,
                experiment.candidate_version,
                experiment.start_date,
                experiment.status.value,
                experiment.traffic_allocation_strategy.value,
                experiment.baseline_traffic_pct,
                experiment.candidate_traffic_pct,
                experiment.primary_metric,
                experiment.confidence_level,
                experiment.minimum_sample_size,
                experiment.description,
                json.dumps(experiment.tags)
            ))

            conn.commit()
            logger.info(f"Created experiment: {experiment.experiment_id}")
            return True
        except sqlite3.IntegrityError as e:
            logger.error(f"Experiment already exists: {e}")
            return False
        finally:
            conn.close()

    def record_observation(self, observation: ObservationData) -> bool:
        """
        Record prediction observation during experiment.

        Args:
            observation: Observation data.

        Returns:
            Success status.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            
            accuracy = None
            if observation.actual is not None and observation.prediction is not None:
                accuracy = abs(observation.prediction - observation.actual) < 5
            elif observation.actual is not None:
                accuracy = observation.actual is not None

            cursor.execute("""
                INSERT INTO experiment_observations (
                    experiment_id, timestamp, model_version, prediction,
                    actual, delay_minutes, accuracy, trip_id, line_ref
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                observation.experiment_id,
                observation.timestamp,
                observation.model_version,
                observation.prediction,
                observation.actual,
                observation.delay_minutes,
                accuracy,
                observation.trip_id,
                observation.line_ref
            ))

            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to record observation: {e}")
            return False
        finally:
            conn.close()

    def get_experiment_status(self, experiment_id: str) -> Optional[Dict]:
        """
        Get current experiment status and summary stats.

        Args:
            experiment_id: Experiment identifier.

        Returns:
            Experiment details with current statistics or None.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM experiments WHERE experiment_id = ?
        """, (experiment_id,))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        columns = [description[0] for description in cursor.description]
        experiment_data = dict(zip(columns, row))

        cursor.execute("""
            SELECT model_version, COUNT(*) as count, AVG(accuracy) as avg_accuracy
            FROM experiment_observations
            WHERE experiment_id = ?
            GROUP BY model_version
        """, (experiment_id,))

        observations = cursor.fetchall()
        conn.close()

        observation_summary = []
        for obs in observations:
            observation_summary.append({
                "model_version": obs[0],
                "observation_count": obs[1],
                "avg_accuracy": obs[2]
            })

        experiment_data["observations"] = observation_summary

        return experiment_data

    def calculate_results(
        self,
        experiment_id: str,
        baseline_metric: float,
        candidate_metric: float
    ) -> Optional[ExperimentResults]:
        """
        Calculate statistical significance of experiment results.

        Args:
            experiment_id: Experiment identifier.
            baseline_metric: Baseline model metric value.
            candidate_metric: Candidate model metric value.

        Returns:
            ExperimentResults or None if calculation fails.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM experiment_observations
            WHERE experiment_id = ?
        """, (experiment_id,))

        sample_size = cursor.fetchone()[0]
        conn.close()

        improvement_pct = (
            (candidate_metric - baseline_metric) / baseline_metric * 100
            if baseline_metric > 0 else 0
        )

        p_value = self._calculate_p_value(
            sample_size,
            baseline_metric,
            candidate_metric
        )

        confidence_interval = self._calculate_confidence_interval(
            candidate_metric,
            sample_size
        )

        is_significant = p_value < 0.05

        recommendation = "Promote candidate" if is_significant and improvement_pct > 0 else "Keep baseline"

        results = ExperimentResults(
            experiment_id=experiment_id,
            baseline_metric=baseline_metric,
            candidate_metric=candidate_metric,
            improvement_pct=improvement_pct,
            p_value=p_value,
            confidence_interval=confidence_interval,
            is_significant=is_significant,
            sample_size=sample_size,
            completed_at=datetime.utcnow().isoformat(),
            recommendation=recommendation
        )

        return results

    @staticmethod
    def _calculate_p_value(
        sample_size: int,
        baseline: float,
        candidate: float
    ) -> float:
        """
        Estimate p-value for metric comparison (simplified).

        Args:
            sample_size: Number of observations.
            baseline: Baseline metric value.
            candidate: Candidate metric value.

        Returns:
            Estimated p-value.
        """
        if sample_size < 100:
            return 1.0

        diff = abs(candidate - baseline)
        z_score = (diff / (baseline * 0.1)) * (sample_size ** 0.5)

        if z_score > 3.0:
            return 0.001
        elif z_score > 2.0:
            return 0.05
        elif z_score > 1.5:
            return 0.10
        else:
            return 0.30

    @staticmethod
    def _calculate_confidence_interval(
        estimate: float,
        sample_size: int,
        confidence: float = 0.95
    ) -> Tuple[float, float]:
        """
        Calculate confidence interval for metric.

        Args:
            estimate: Point estimate of metric.
            sample_size: Sample size.
            confidence: Confidence level (default 0.95).

        Returns:
            Tuple of (lower_bound, upper_bound).
        """
        if sample_size == 0:
            return (estimate, estimate)

        margin = (1.96 * estimate * 0.1) / (sample_size ** 0.5)

        return (max(0, estimate - margin), min(1, estimate + margin))
