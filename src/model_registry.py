"""
Model Registry and Versioning Management Module.

Provides centralized storage, versioning, and lifecycle management for trained models.
Supports model registration, retrieval, metadata tracking, and cloud storage integration.
"""

import os
import json
import pickle
import hashlib
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict, field
from pathlib import Path
import sqlite3


logger = logging.getLogger(__name__)


@dataclass
class ModelMetadata:
    """
    Complete metadata for a registered model version.
    """
    model_id: str
    version: str
    created_at: str
    framework: str
    model_type: str
    input_shape: Tuple[int, ...]
    output_shape: Tuple[int, ...]
    training_samples: int
    hyperparameters: Dict[str, Any]
    performance_metrics: Dict[str, float]
    training_date: str
    data_version: str
    preprocessor_hash: str
    model_hash: str
    tags: List[str] = field(default_factory=list)
    description: str = ""
    is_production: bool = False
    is_archived: bool = False


@dataclass
class ModelRegistry:
    """
    Central registry for model versions with SQLite persistence.
    
    Manages model metadata, versioning, and lifecycle (dev → staging → production).
    Supports local and cloud storage backends.
    """

    registry_db: str = "data/model_registry.db"
    model_storage_dir: str = "models/registry"

    def __post_init__(self) -> None:
        """Initialize registry database and storage directories."""
        Path(self.model_storage_dir).mkdir(parents=True, exist_ok=True)
        self._ensure_db()

    def _ensure_db(self) -> None:
        """Create SQLite database schema if not exists."""
        conn = sqlite3.connect(self.registry_db)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id TEXT NOT NULL,
                version TEXT NOT NULL,
                created_at TEXT NOT NULL,
                framework TEXT,
                model_type TEXT,
                input_shape TEXT,
                output_shape TEXT,
                training_samples INTEGER,
                hyperparameters TEXT,
                performance_metrics TEXT,
                training_date TEXT,
                data_version TEXT,
                preprocessor_hash TEXT,
                model_hash TEXT,
                tags TEXT,
                description TEXT,
                is_production BOOLEAN DEFAULT 0,
                is_archived BOOLEAN DEFAULT 0,
                storage_path TEXT,
                UNIQUE(model_id, version)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_lineage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_model_id TEXT,
                parent_version TEXT,
                child_model_id TEXT,
                child_version TEXT,
                relationship_type TEXT,
                created_at TEXT,
                notes TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deployment_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id TEXT NOT NULL,
                version TEXT NOT NULL,
                environment TEXT,
                deployed_at TEXT,
                deployed_by TEXT,
                status TEXT,
                metrics_at_deployment TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_model_id_version
            ON model_registry (model_id, version)
        """)

        conn.commit()
        conn.close()

    def register_model(
        self,
        model_id: str,
        model_path: str,
        metadata: ModelMetadata,
        preprocessor_path: Optional[str] = None
    ) -> str:
        """
        Register new model version in registry.

        Args:
            model_id: Model identifier.
            model_path: Path to serialized model file.
            metadata: Complete model metadata.
            preprocessor_path: Optional path to preprocessor (scaler, encoder).

        Returns:
            Storage path of registered model.
        """
        storage_path = os.path.join(
            self.model_storage_dir,
            model_id,
            metadata.version
        )
        Path(storage_path).mkdir(parents=True, exist_ok=True)

        model_file = os.path.join(storage_path, "model.keras")
        os.makedirs(os.path.dirname(model_file), exist_ok=True)

        try:
            if model_path.endswith(".keras"):
                with open(model_path, "rb") as src:
                    with open(model_file, "wb") as dst:
                        dst.write(src.read())
            else:
                with open(model_path, "rb") as src:
                    with open(model_file, "wb") as dst:
                        dst.write(src.read())
        except IOError as e:
            logger.error(f"Failed to copy model file: {e}")
            return None

        if preprocessor_path and os.path.exists(preprocessor_path):
            preprocessor_file = os.path.join(storage_path, "preprocessor.pkl")
            with open(preprocessor_path, "rb") as src:
                with open(preprocessor_file, "wb") as dst:
                    dst.write(src.read())

        metadata_file = os.path.join(storage_path, "metadata.json")
        with open(metadata_file, "w") as f:
            json.dump(asdict(metadata), f, indent=2, default=str)

        conn = sqlite3.connect(self.registry_db)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO model_registry (
                    model_id, version, created_at, framework, model_type,
                    input_shape, output_shape, training_samples, hyperparameters,
                    performance_metrics, training_date, data_version,
                    preprocessor_hash, model_hash, tags, description,
                    storage_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metadata.model_id,
                metadata.version,
                metadata.created_at,
                metadata.framework,
                metadata.model_type,
                str(metadata.input_shape),
                str(metadata.output_shape),
                metadata.training_samples,
                json.dumps(metadata.hyperparameters),
                json.dumps(metadata.performance_metrics),
                metadata.training_date,
                metadata.data_version,
                metadata.preprocessor_hash,
                metadata.model_hash,
                json.dumps(metadata.tags),
                metadata.description,
                storage_path
            ))
            conn.commit()
            logger.info(f"Registered model {model_id}:{metadata.version}")
        except sqlite3.IntegrityError as e:
            logger.error(f"Model already registered: {e}")
        finally:
            conn.close()

        return storage_path

    def get_model(
        self,
        model_id: str,
        version: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve model metadata and path by ID and version.

        Args:
            model_id: Model identifier.
            version: Specific version (None for latest).

        Returns:
            Dictionary with model metadata and path, or None if not found.
        """
        conn = sqlite3.connect(self.registry_db)
        cursor = conn.cursor()

        if version:
            cursor.execute("""
                SELECT * FROM model_registry
                WHERE model_id = ? AND version = ?
                LIMIT 1
            """, (model_id, version))
        else:
            cursor.execute("""
                SELECT * FROM model_registry
                WHERE model_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (model_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        columns = [description[0] for description in cursor.description]
        model_data = dict(zip(columns, row))

        model_data['hyperparameters'] = json.loads(
            model_data.get('hyperparameters', '{}')
        )
        model_data['performance_metrics'] = json.loads(
            model_data.get('performance_metrics', '{}')
        )
        model_data['tags'] = json.loads(model_data.get('tags', '[]'))

        return model_data

    def get_all_versions(self, model_id: str) -> List[Dict[str, Any]]:
        """
        List all versions of a model.

        Args:
            model_id: Model identifier.

        Returns:
            List of model version metadata dictionaries.
        """
        conn = sqlite3.connect(self.registry_db)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM model_registry
            WHERE model_id = ?
            ORDER BY created_at DESC
        """, (model_id,))

        rows = cursor.fetchall()
        conn.close()

        versions = []
        for row in rows:
            columns = [description[0] for description in cursor.description]
            model_data = dict(zip(columns, row))
            model_data['hyperparameters'] = json.loads(
                model_data.get('hyperparameters', '{}')
            )
            model_data['performance_metrics'] = json.loads(
                model_data.get('performance_metrics', '{}')
            )
            versions.append(model_data)

        return versions

    def set_production(self, model_id: str, version: str) -> bool:
        """
        Promote model version to production.
        Automatically demotes previous production version.

        Args:
            model_id: Model identifier.
            version: Version to promote.

        Returns:
            Success status.
        """
        conn = sqlite3.connect(self.registry_db)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE model_registry
                SET is_production = 0
                WHERE model_id = ? AND is_production = 1
            """, (model_id,))

            cursor.execute("""
                UPDATE model_registry
                SET is_production = 1
                WHERE model_id = ? AND version = ?
            """, (model_id, version))

            conn.commit()
            logger.info(f"Promoted {model_id}:{version} to production")
            return True
        except Exception as e:
            logger.error(f"Failed to promote model: {e}")
            return False
        finally:
            conn.close()

    def get_production_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve currently deployed production model.

        Args:
            model_id: Model identifier.

        Returns:
            Production model metadata or None.
        """
        conn = sqlite3.connect(self.registry_db)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM model_registry
            WHERE model_id = ? AND is_production = 1
            LIMIT 1
        """, (model_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        columns = [description[0] for description in cursor.description]
        return dict(zip(columns, row))

    def archive_version(self, model_id: str, version: str) -> bool:
        """
        Archive old model version (mark for cleanup).

        Args:
            model_id: Model identifier.
            version: Version to archive.

        Returns:
            Success status.
        """
        conn = sqlite3.connect(self.registry_db)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE model_registry
                SET is_archived = 1
                WHERE model_id = ? AND version = ?
            """, (model_id, version))

            conn.commit()
            logger.info(f"Archived {model_id}:{version}")
            return True
        except Exception as e:
            logger.error(f"Failed to archive model: {e}")
            return False
        finally:
            conn.close()

    def get_model_lineage(
        self,
        model_id: str,
        version: str
    ) -> List[Dict[str, str]]:
        """
        Retrieve model lineage (parent/child relationships).

        Args:
            model_id: Model identifier.
            version: Model version.

        Returns:
            List of lineage records.
        """
        conn = sqlite3.connect(self.registry_db)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM model_lineage
            WHERE (parent_model_id = ? AND parent_version = ?)
               OR (child_model_id = ? AND child_version = ?)
            ORDER BY created_at DESC
        """, (model_id, version, model_id, version))

        rows = cursor.fetchall()
        conn.close()

        lineage = []
        for row in rows:
            columns = [description[0] for description in cursor.description]
            lineage.append(dict(zip(columns, row)))

        return lineage

    def record_deployment(
        self,
        model_id: str,
        version: str,
        environment: str,
        deployed_by: str,
        metrics: Optional[Dict[str, float]] = None
    ) -> bool:
        """
        Record model deployment event.

        Args:
            model_id: Model identifier.
            version: Deployed version.
            environment: Deployment environment (dev/staging/prod).
            deployed_by: Deployer user/system ID.
            metrics: Optional performance metrics at deployment.

        Returns:
            Success status.
        """
        conn = sqlite3.connect(self.registry_db)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO deployment_history (
                    model_id, version, environment, deployed_at,
                    deployed_by, status, metrics_at_deployment
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                model_id,
                version,
                environment,
                datetime.utcnow().isoformat(),
                deployed_by,
                "success",
                json.dumps(metrics) if metrics else None
            ))

            conn.commit()
            logger.info(f"Recorded deployment: {model_id}:{version} to {environment}")
            return True
        except Exception as e:
            logger.error(f"Failed to record deployment: {e}")
            return False
        finally:
            conn.close()
