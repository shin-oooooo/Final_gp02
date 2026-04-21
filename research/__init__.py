"""Research pipeline: Phase 0–3, schemas, state, defense resolver."""

from research.schemas import (
    DefensePolicyConfig,
    Phase0Input,
    Phase0Output,
    Phase1Input,
    Phase1Output,
    Phase2Input,
    Phase2Output,
    Phase3Input,
    Phase3Output,
)
from research.state_manager import GlobalStateManager
from research.defense_state import (
    DefenseLevel,
    any_adf_asset_failure,
    diagnostic_failed_adf,
    resolve_defense_level,
)

DefenseStateResolver = resolve_defense_level  # alias for plan naming

__all__ = [
    "DefensePolicyConfig",
    "Phase0Input",
    "Phase0Output",
    "Phase1Input",
    "Phase1Output",
    "Phase2Input",
    "Phase2Output",
    "Phase3Input",
    "Phase3Output",
    "GlobalStateManager",
    "DefenseStateResolver",
    "resolve_defense_level",
    "DefenseLevel",
    "any_adf_asset_failure",
    "diagnostic_failed_adf",
]
