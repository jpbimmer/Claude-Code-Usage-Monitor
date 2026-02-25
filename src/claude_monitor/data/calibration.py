"""Calibration store for correcting Est. Claude Usage predictions."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CalibrationStore:
    """Stores calibration data points and computes a rolling multiplier."""

    MAX_SAMPLES = 20

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        self.config_dir = config_dir or Path.home() / ".claude-monitor"
        self.file_path = self.config_dir / "calibration.json"
        self._samples: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if self.file_path.exists():
            try:
                with open(self.file_path) as f:
                    data = json.load(f)
                self._samples = data if isinstance(data, list) else []
            except Exception as e:
                logger.warning(f"Failed to load calibration data: {e}")
                self._samples = []

    def _save(self) -> None:
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            temp = self.file_path.with_suffix(".tmp")
            with open(temp, "w") as f:
                json.dump(self._samples, f, indent=2)
            temp.replace(self.file_path)
        except Exception as e:
            logger.warning(f"Failed to save calibration data: {e}")

    def add_sample(self, estimated: float, actual: float) -> None:
        """Add a calibration data point."""
        from datetime import datetime, timezone

        self._samples.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "estimated_pct": round(estimated, 2),
            "actual_pct": round(actual, 2),
        })
        # Keep only the last N samples
        self._samples = self._samples[-self.MAX_SAMPLES:]
        self._save()

    def get_multiplier(self) -> float:
        """Return mean(actual/estimated) from stored samples, default 1.0."""
        self._load()
        if not self._samples:
            return 1.0

        ratios = []
        for s in self._samples:
            est = s.get("estimated_pct", 0)
            act = s.get("actual_pct", 0)
            if est > 0:
                ratios.append(act / est)

        if not ratios:
            return 1.0

        return sum(ratios) / len(ratios)
