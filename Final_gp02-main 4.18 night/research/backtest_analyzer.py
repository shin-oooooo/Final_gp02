"""Stores walk-forward residuals for shadow inference (Phase 2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class BacktestAnalyzer:
    """Lightweight store for epsilon_t and consistency at t vs residual at t+1."""

    residuals_naive: List[float] = field(default_factory=list)
    residuals_kronos: List[float] = field(default_factory=list)
    consistency: List[float] = field(default_factory=list)
    dates: List[str] = field(default_factory=list)

    def append_step(
        self,
        date: str,
        eps_naive: float,
        eps_kronos: float,
        consistency_score: float,
    ) -> None:
        self.dates.append(date)
        self.residuals_naive.append(eps_naive)
        self.residuals_kronos.append(eps_kronos)
        self.consistency.append(consistency_score)

    def mse_red_light(self, c_thresh: float = 0.45) -> Optional[Dict[str, float]]:
        """Compare MSE in low-consistency subsample."""
        if not self.consistency:
            return None
        mask = [c < c_thresh for c in self.consistency]
        if not any(mask):
            return {"mse_naive": None, "mse_kronos": None, "n": 0}
        import numpy as np

        rn = np.array(self.residuals_naive)[mask]
        rk = np.array(self.residuals_kronos)[mask]
        return {
            "mse_naive": float(np.mean(rn**2)),
            "mse_kronos": float(np.mean(rk**2)),
            "n": int(np.sum(mask)),
        }
