"""Cost Tracker for LLM Requests - Backward Compatibility Facade.

Sprint 56: Re-exports from src.domains.llm_integration.cost

Recommended import:
    from src.domains.llm_integration.cost import CostTracker, get_cost_tracker
"""

# Re-export from domain location
from src.domains.llm_integration.cost import (
    CostTracker,
    get_cost_tracker,
)

__all__ = [
    "CostTracker",
    "get_cost_tracker",
]
