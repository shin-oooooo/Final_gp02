"""Global state singleton for one-way data flow between phases."""

from __future__ import annotations

from typing import Any, Dict, Optional

from research.schemas import (
    DefensePolicyConfig,
    Phase0Output,
    Phase1Output,
    Phase2Output,
    Phase3Output,
)


class GlobalStateManager:
    """Holds phase outputs; no circular dependencies — phases read prior fields only."""

    def __init__(self) -> None:
        self.policy: DefensePolicyConfig = DefensePolicyConfig()
        self.phase0: Optional[Phase0Output] = None
        self.phase1: Optional[Phase1Output] = None
        self.phase2: Optional[Phase2Output] = None
        self.phase3: Optional[Phase3Output] = None
        self.defense_level: int = 0
        self.extra: Dict[str, Any] = {}

    def reset(self) -> None:
        self.phase0 = None
        self.phase1 = None
        self.phase2 = None
        self.phase3 = None
        self.defense_level = 0
        self.extra.clear()

    def set_policy(self, policy: DefensePolicyConfig) -> None:
        self.policy = policy.model_copy()


# module-level default for convenience
STATE = GlobalStateManager()
