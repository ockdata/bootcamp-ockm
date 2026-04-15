"""Step 3: Statistical anomaly detection using EWMA + z-score.

Supports persistent state via JSON so the detector can learn across
multiple pipeline runs (continuous demo mode).
"""

from __future__ import annotations

import json
import math
import os
import tempfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from observability.logger import get_logger

log = get_logger(__name__)


@dataclass
class EWMAState:
    """Exponentially Weighted Moving Average state for a single metric bucket."""

    mean: float = 0.0
    variance: float = 1.0
    count: int = 0
    alpha: float = 0.3  # smoothing factor


@dataclass
class AnomalyResult:
    """Result of anomaly detection for a single event."""

    is_anomaly: bool = False
    z_score: float = 0.0
    bucket: str = ""
    threshold: float = 2.5


class AnomalyDetector:
    """EWMA-based anomaly detector that tracks per-bucket statistics.

    Buckets are keyed by (service, event_type) to detect per-stream anomalies.
    Optionally persists state to a JSON file so baselines survive between runs.
    """

    def __init__(
        self,
        alpha: float = 0.3,
        z_threshold: float = 2.5,
        state_file: Path | str | None = None,
    ) -> None:
        self.alpha = alpha
        self.z_threshold = z_threshold
        self.state_file = Path(state_file) if state_file else None
        self._states: dict[str, EWMAState] = defaultdict(
            lambda: EWMAState(alpha=self.alpha)
        )
        self._load_state()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_state(self) -> None:
        """Load persisted EWMA state from JSON file if it exists."""
        if self.state_file is None or not self.state_file.exists():
            return
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
            for bucket, vals in data.items():
                self._states[bucket] = EWMAState(
                    mean=vals["mean"],
                    variance=vals["variance"],
                    count=vals["count"],
                    alpha=vals.get("alpha", self.alpha),
                )
            log.info(
                "anomaly.state.loaded",
                buckets=len(data),
                file=str(self.state_file),
            )
        except (json.JSONDecodeError, KeyError, OSError) as exc:
            log.warning("anomaly.state.load_failed", error=str(exc))

    def save_state(self) -> None:
        """Persist current EWMA state to JSON (atomic write)."""
        if self.state_file is None:
            return
        data = {
            bucket: {
                "mean": round(st.mean, 6),
                "variance": round(st.variance, 6),
                "count": st.count,
                "alpha": st.alpha,
            }
            for bucket, st in self._states.items()
        }
        try:
            # Atomic write: temp file + rename
            fd, tmp = tempfile.mkstemp(
                dir=self.state_file.parent,
                suffix=".tmp",
            )
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, self.state_file)
            log.info(
                "anomaly.state.saved",
                buckets=len(data),
                file=str(self.state_file),
            )
        except OSError as exc:
            log.error("anomaly.state.save_failed", error=str(exc))

    def reset_state(self) -> None:
        """Clear in-memory state and delete the persisted file."""
        self._states.clear()
        if self.state_file and self.state_file.exists():
            self.state_file.unlink()
            log.info("anomaly.state.reset", file=str(self.state_file))

    def get_states_snapshot(self) -> dict[str, dict]:
        """Return a snapshot of all buckets for display purposes."""
        return {
            bucket: {
                "mean": round(st.mean, 3),
                "variance": round(st.variance, 3),
                "std": round(math.sqrt(st.variance), 3) if st.variance > 0 else 0.0,
                "count": st.count,
                "status": "active" if st.count >= 3 else "training",
            }
            for bucket, st in sorted(self._states.items())
        }

    # ------------------------------------------------------------------
    # Detection (unchanged logic)
    # ------------------------------------------------------------------

    def _severity_to_value(self, severity: str) -> float:
        """Convert severity to a numeric value for anomaly detection."""
        return {"low": 1.0, "medium": 2.0, "high": 3.0, "critical": 4.0}.get(severity, 1.0)

    def detect(
        self,
        service: str,
        event_type: str,
        severity: str,
    ) -> AnomalyResult:
        """Detect if the current event is anomalous given the stream history."""
        bucket = f"{service}:{event_type}"
        value = self._severity_to_value(severity)
        state = self._states[bucket]

        if state.count < 3:
            # Not enough data — update state but don't flag anomaly
            self._update(state, value)
            return AnomalyResult(bucket=bucket, z_score=0.0, is_anomaly=False)

        # Compute z-score
        std = math.sqrt(state.variance) if state.variance > 0 else 1.0
        z_score = (value - state.mean) / std
        is_anomaly = abs(z_score) > self.z_threshold

        if is_anomaly:
            log.warning(
                "anomaly.detected",
                bucket=bucket,
                z_score=round(z_score, 3),
                value=value,
                mean=round(state.mean, 3),
                std=round(std, 3),
            )

        # Update state AFTER detection
        self._update(state, value)

        return AnomalyResult(
            is_anomaly=is_anomaly,
            z_score=round(z_score, 3),
            bucket=bucket,
            threshold=self.z_threshold,
        )

    def _update(self, state: EWMAState, value: float) -> None:
        """Update EWMA mean and variance with a new observation."""
        if state.count == 0:
            state.mean = value
            state.variance = 0.0
        else:
            diff = value - state.mean
            state.mean = state.alpha * value + (1 - state.alpha) * state.mean
            state.variance = (1 - state.alpha) * (state.variance + self.alpha * diff * diff)

        state.count += 1
