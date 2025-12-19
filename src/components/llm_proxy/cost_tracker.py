"""Cost Tracker for LLM Requests - Backward Compatibility Facade.

Sprint 56: Re-exports from src.domains.llm_integration.cost
OPL-006: These re-exports will be removed in Sprint 58.

Migrate to:
    from src.domains.llm_integration.cost import CostTracker, get_cost_tracker
"""

# OPL-006: Re-export from new domain location
from src.domains.llm_integration.cost import (
    CostTracker,
    get_cost_tracker,
)

__all__ = [
    "CostTracker",
    "get_cost_tracker",
]
