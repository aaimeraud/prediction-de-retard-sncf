"""
Model Versioning and Version Control Module.

Provides semantic versioning, version comparison, and migration management
for model lifecycle tracking and reproducibility.
"""

import re
import logging
from typing import Optional, Tuple, List
from dataclasses import dataclass
from datetime import datetime


logger = logging.getLogger(__name__)


@dataclass
class SemanticVersion:
    """
    Semantic versioning for ML models (MAJOR.MINOR.PATCH).
    
    MAJOR: Breaking changes (architecture, input/output shape)
    MINOR: Feature additions (new regularization, improved training)
    PATCH: Bug fixes and minor improvements (same interface)
    """

    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None
    metadata: Optional[str] = None

    def __str__(self) -> str:
        """Return semantic version string."""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.metadata:
            version += f"+{self.metadata}"
        return version

    @classmethod
    def parse(cls, version_string: str) -> "SemanticVersion":
        """
        Parse semantic version string into SemanticVersion object.

        Args:
            version_string: Version in format "MAJOR.MINOR.PATCH" or "MAJOR.MINOR.PATCH-prerelease+metadata"

        Returns:
            SemanticVersion instance.

        Raises:
            ValueError: If version string format is invalid.
        """
        pattern = r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9\-\.]+))?(?:\+([a-zA-Z0-9\-\.]+))?$"
        match = re.match(pattern, version_string)

        if not match:
            raise ValueError(f"Invalid semantic version format: {version_string}")

        major, minor, patch, prerelease, metadata = match.groups()

        return cls(
            major=int(major),
            minor=int(minor),
            patch=int(patch),
            prerelease=prerelease,
            metadata=metadata
        )

    def increment_major(self) -> "SemanticVersion":
        """Return version with incremented MAJOR component."""
        return SemanticVersion(
            major=self.major + 1,
            minor=0,
            patch=0
        )

    def increment_minor(self) -> "SemanticVersion":
        """Return version with incremented MINOR component."""
        return SemanticVersion(
            major=self.major,
            minor=self.minor + 1,
            patch=0
        )

    def increment_patch(self) -> "SemanticVersion":
        """Return version with incremented PATCH component."""
        return SemanticVersion(
            major=self.major,
            minor=self.minor,
            patch=self.patch + 1
        )

    def set_prerelease(self, prerelease: str) -> "SemanticVersion":
        """Create prerelease version (e.g., alpha, beta, rc)."""
        return SemanticVersion(
            major=self.major,
            minor=self.minor,
            patch=self.patch,
            prerelease=prerelease
        )

    def compare(self, other: "SemanticVersion") -> int:
        """
        Compare two semantic versions.

        Args:
            other: Version to compare against.

        Returns:
            -1: self < other
             0: self == other
             1: self > other
        """
        if (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch):
            return -1
        elif (self.major, self.minor, self.patch) > (other.major, other.minor, other.patch):
            return 1
        else:
            return 0

    def is_compatible_with(self, other: "SemanticVersion") -> bool:
        """
        Check if versions are compatible (same MAJOR).

        Args:
            other: Version to check compatibility with.

        Returns:
            True if MAJOR versions match.
        """
        return self.major == other.major

    def is_breaking_change(self, other: "SemanticVersion") -> bool:
        """
        Check if transition to other version is breaking.

        Args:
            other: Version to check.

        Returns:
            True if MAJOR version differs.
        """
        return self.major != other.major


class VersionedModel:
    """
    Wrapper for managing model versions and migrations.
    """

    def __init__(
        self,
        model_id: str,
        version: str,
        created_at: Optional[str] = None
    ):
        """
        Initialize versioned model reference.

        Args:
            model_id: Model identifier.
            version: Semantic version string.
            created_at: Creation timestamp (auto-generated if None).
        """
        self.model_id = model_id
        self.version = SemanticVersion.parse(version)
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.metadata: dict = {}

    def __str__(self) -> str:
        """Return model identifier with version."""
        return f"{self.model_id}:{self.version}"

    def get_next_patch_version(self) -> str:
        """Get incremented PATCH version string."""
        return str(self.version.increment_patch())

    def get_next_minor_version(self) -> str:
        """Get incremented MINOR version string."""
        return str(self.version.increment_minor())

    def get_next_major_version(self) -> str:
        """Get incremented MAJOR version string."""
        return str(self.version.increment_major())


class VersionMigration:
    """
    Manages migrations between model versions.
    """

    def __init__(self, from_version: str, to_version: str):
        """
        Initialize version migration.

        Args:
            from_version: Source semantic version.
            to_version: Target semantic version.
        """
        self.from_version = SemanticVersion.parse(from_version)
        self.to_version = SemanticVersion.parse(to_version)
        self.breaking = self._is_breaking_change()

    def _is_breaking_change(self) -> bool:
        """Check if migration is breaking change."""
        return self.from_version.major != self.to_version.major

    def validate(self) -> bool:
        """
        Validate migration is possible.

        Returns:
            False if breaking change with no migration path.
        """
        if self.breaking:
            logger.warning(
                f"Breaking change: {self.from_version} → {self.to_version}"
            )
            return False

        if self.from_version.compare(self.to_version) >= 0:
            logger.warning(
                f"Invalid migration: cannot downgrade from {self.from_version} to {self.to_version}"
            )
            return False

        return True

    def get_migration_steps(self) -> List[str]:
        """
        Get intermediate versions for gradual migration.

        Returns:
            List of intermediate version strings.
        """
        steps = []

        current = self.from_version

        while current.minor < self.to_version.minor:
            steps.append(str(current.increment_patch()))
            current = current.increment_minor()

        steps.append(str(self.to_version))

        return steps


class VersionComparator:
    """
    Compare and rank multiple model versions.
    """

    @staticmethod
    def compare_performance(
        version1: str,
        metrics1: dict,
        version2: str,
        metrics2: dict,
        primary_metric: str = "accuracy"
    ) -> Tuple[str, float]:
        """
        Compare two model versions by performance.

        Args:
            version1: First model version.
            metrics1: First model metrics.
            version2: Second model version.
            metrics2: Second model metrics.
            primary_metric: Metric to use for comparison.

        Returns:
            Tuple of (winner_version, improvement_percentage).
        """
        metric1 = metrics1.get(primary_metric, 0)
        metric2 = metrics2.get(primary_metric, 0)

        improvement = ((metric2 - metric1) / metric1 * 100) if metric1 > 0 else 0

        winner = version2 if metric2 >= metric1 else version1

        return winner, improvement

    @staticmethod
    def rank_versions(
        versions: List[Tuple[str, dict]],
        metric: str = "accuracy",
        descending: bool = True
    ) -> List[Tuple[str, float]]:
        """
        Rank model versions by metric.

        Args:
            versions: List of (version_string, metrics_dict) tuples.
            metric: Metric name to use for ranking.
            descending: Sort descending (higher is better).

        Returns:
            Sorted list of (version, metric_value) tuples.
        """
        ranked = [
            (version, metrics.get(metric, 0))
            for version, metrics in versions
        ]

        ranked.sort(key=lambda x: x[1], reverse=descending)

        return ranked

    @staticmethod
    def get_version_history(
        versions: List[Tuple[str, dict]],
        metric: str = "accuracy"
    ) -> List[Tuple[str, float]]:
        """
        Get metric progression across versions.

        Args:
            versions: List of (version_string, metrics_dict) tuples.
            metric: Metric to track.

        Returns:
            Chronological list of (version, metric_value) tuples.
        """
        return [
            (version, metrics.get(metric, 0))
            for version, metrics in versions
        ]
