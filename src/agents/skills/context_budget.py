"""Skill Context Budget Manager.

Sprint Context:
    - Sprint 92 (2026-01-14): Feature 92.4 - Skill Context Budget Manager (4 SP)

Fine-grained context budget management per skill with priority-based allocation
and automatic rebalancing.

Features:
    - Dynamic reallocation based on usage
    - Priority-based allocation
    - Automatic budget expansion/contraction
    - Utilization tracking

Example:
    >>> from src.agents.skills.context_budget import ContextBudgetManager
    >>>
    >>> manager = ContextBudgetManager(total_budget=10000)
    >>>
    >>> # Allocate budget to skills
    >>> actual = manager.allocate("reflection", requested=2000, priority=2)
    >>> actual
    2000
    >>>
    >>> # Record usage
    >>> manager.use("reflection", 1500)
    >>> manager.get_budget("reflection").utilization
    0.75
    >>>
    >>> # Rebalance based on utilization
    >>> manager.rebalance()

Notes:
    - Underutilized skills (<30%) get reduced allocation
    - Overutilized skills (>90%) get expanded allocation
    - Priority-based reclamation from lower priority skills
    - Automatic rebalancing based on usage patterns

See Also:
    - docs/sprints/SPRINT_92_PLAN.md: Feature specification
    - src/agents/skills/lifecycle.py: Skill lifecycle management
"""

from dataclasses import dataclass
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class SkillContextBudget:
    """Budget allocation for a skill.

    Attributes:
        skill_name: Name of skill
        allocated: Allocated token budget
        used: Tokens actually used
        priority: Priority level (higher = more important)

    Properties:
        remaining: Unused tokens (allocated - used)
        utilization: Usage ratio (used / allocated)

    Example:
        >>> budget = SkillContextBudget(
        ...     skill_name="reflection",
        ...     allocated=2000,
        ...     used=1500,
        ...     priority=2
        ... )
        >>> budget.remaining
        500
        >>> budget.utilization
        0.75
    """

    skill_name: str
    allocated: int
    used: int = 0
    priority: int = 1

    @property
    def remaining(self) -> int:
        """Get remaining token budget.

        Returns:
            Unused tokens

        Example:
            >>> budget = SkillContextBudget("test", 2000, 1500)
            >>> budget.remaining
            500
        """
        return self.allocated - self.used

    @property
    def utilization(self) -> float:
        """Get utilization ratio.

        Returns:
            Usage ratio (0.0-1.0)

        Example:
            >>> budget = SkillContextBudget("test", 2000, 1500)
            >>> budget.utilization
            0.75
        """
        return self.used / self.allocated if self.allocated > 0 else 0.0


class ContextBudgetManager:
    """Manage context budgets across active skills.

    Features:
        - Dynamic reallocation based on usage
        - Priority-based allocation
        - Automatic budget expansion/contraction
        - Utilization tracking

    Rebalancing Logic:
        - Underutilized (<30%): Reduce allocation by 30%
        - Overutilized (>90%): Expand if budget available
        - Priority-based reclamation

    Attributes:
        total_budget: Total available token budget
        _budgets: Active skill budgets
        _usage_history: Historical usage data

    Example:
        >>> manager = ContextBudgetManager(total_budget=10000)
        >>>
        >>> # Allocate with priority
        >>> actual = manager.allocate("reflection", 2000, priority=2)
        >>> actual
        2000
        >>>
        >>> # Record usage
        >>> manager.use("reflection", 1500)
        >>> True
        >>>
        >>> # Check utilization
        >>> budget = manager.get_budget("reflection")
        >>> budget.utilization
        0.75
    """

    def __init__(self, total_budget: int = 10000):
        """Initialize context budget manager.

        Args:
            total_budget: Total available token budget (default: 10000)
        """
        self.total_budget = total_budget
        self._budgets: dict[str, SkillContextBudget] = {}
        self._usage_history: list[dict] = []

        logger.info("context_budget_manager_initialized", total_budget=total_budget)

    def allocate(
        self,
        skill_name: str,
        requested: int,
        priority: int = 1,
    ) -> int:
        """Allocate context budget to skill.

        Args:
            skill_name: Name of skill
            requested: Requested token budget
            priority: Priority level (default: 1, higher = more important)

        Returns:
            Actual allocation (may be less than requested)

        Example:
            >>> manager = ContextBudgetManager(total_budget=10000)
            >>> actual = manager.allocate("reflection", 2000, priority=2)
            >>> actual
            2000
            >>> manager.allocate("synthesis", 9000, priority=1)
            8000  # Limited by available budget
        """
        available = self._get_available()

        # Priority-based allocation
        allocation = min(requested, available)

        if allocation < requested and priority > 1:
            # Try to reclaim from lower priority skills
            reclaimed = self._reclaim_from_lower_priority(requested - allocation, priority)
            allocation += reclaimed
            logger.info(
                "reclaimed_budget",
                skill_name=skill_name,
                reclaimed=reclaimed,
                priority=priority,
            )

        self._budgets[skill_name] = SkillContextBudget(
            skill_name=skill_name,
            allocated=allocation,
            priority=priority,
        )

        logger.info(
            "budget_allocated",
            skill_name=skill_name,
            requested=requested,
            allocated=allocation,
            priority=priority,
            available_after=self._get_available(),
        )

        return allocation

    def use(self, skill_name: str, tokens: int) -> bool:
        """Record token usage for skill.

        Args:
            skill_name: Name of skill
            tokens: Number of tokens used

        Returns:
            True if usage recorded (within budget), False if over budget

        Example:
            >>> manager = ContextBudgetManager()
            >>> manager.allocate("reflection", 2000)
            >>> manager.use("reflection", 1500)
            True
            >>> manager.use("reflection", 1000)  # Exceeds budget
            False
        """
        budget = self._budgets.get(skill_name)
        if not budget:
            logger.warning("budget_not_found", skill_name=skill_name)
            return False

        if budget.remaining >= tokens:
            budget.used += tokens
            logger.debug(
                "token_usage_recorded",
                skill_name=skill_name,
                tokens=tokens,
                utilization=budget.utilization,
            )
            return True

        logger.warning(
            "budget_exceeded",
            skill_name=skill_name,
            requested=tokens,
            remaining=budget.remaining,
        )
        return False

    def release(self, skill_name: str):
        """Release skill's budget.

        Args:
            skill_name: Name of skill

        Example:
            >>> manager = ContextBudgetManager()
            >>> manager.allocate("reflection", 2000)
            >>> manager.release("reflection")
            >>> manager.get_budget("reflection")
            None
        """
        if skill_name in self._budgets:
            # Record in history
            budget = self._budgets[skill_name]
            self._usage_history.append(
                {
                    "skill_name": skill_name,
                    "allocated": budget.allocated,
                    "used": budget.used,
                    "utilization": budget.utilization,
                }
            )

            del self._budgets[skill_name]
            logger.info("budget_released", skill_name=skill_name)

    def rebalance(self):
        """Rebalance budgets based on usage patterns.

        Logic:
            - Underutilized (<30%): Reduce allocation by 30%
            - Overutilized (>90%): Expand if budget available

        Example:
            >>> manager = ContextBudgetManager(total_budget=10000)
            >>> manager.allocate("skill1", 2000)
            >>> manager.use("skill1", 200)  # 10% utilization
            >>> manager.rebalance()
            >>> manager.get_budget("skill1").allocated
            1400  # Reduced by 30%
        """
        for name, budget in self._budgets.items():
            if budget.utilization < 0.3:
                # Reduce allocation
                old_allocation = budget.allocated
                budget.allocated = int(budget.allocated * 0.7)
                logger.info(
                    "budget_reduced_underutilized",
                    skill_name=name,
                    old=old_allocation,
                    new=budget.allocated,
                    utilization=budget.utilization,
                )
            elif budget.utilization > 0.9:
                # Try to expand
                available = self._get_available()
                expansion = min(available // 2, budget.allocated)
                if expansion > 0:
                    old_allocation = budget.allocated
                    budget.allocated += expansion
                    logger.info(
                        "budget_expanded_overutilized",
                        skill_name=name,
                        old=old_allocation,
                        new=budget.allocated,
                        utilization=budget.utilization,
                    )

    def get_budget(self, skill_name: str) -> Optional[SkillContextBudget]:
        """Get budget for skill.

        Args:
            skill_name: Name of skill

        Returns:
            SkillContextBudget or None if not found

        Example:
            >>> manager = ContextBudgetManager()
            >>> manager.allocate("reflection", 2000)
            >>> budget = manager.get_budget("reflection")
            >>> budget.allocated
            2000
        """
        return self._budgets.get(skill_name)

    def get_all_budgets(self) -> dict[str, SkillContextBudget]:
        """Get all active skill budgets.

        Returns:
            Dict mapping skill name to budget

        Example:
            >>> manager = ContextBudgetManager()
            >>> manager.allocate("skill1", 2000)
            >>> manager.allocate("skill2", 1500)
            >>> budgets = manager.get_all_budgets()
            >>> len(budgets)
            2
        """
        return dict(self._budgets)

    def get_total_allocated(self) -> int:
        """Get total allocated budget.

        Returns:
            Total allocated tokens

        Example:
            >>> manager = ContextBudgetManager(total_budget=10000)
            >>> manager.allocate("skill1", 2000)
            >>> manager.allocate("skill2", 1500)
            >>> manager.get_total_allocated()
            3500
        """
        return sum(b.allocated for b in self._budgets.values())

    def get_total_used(self) -> int:
        """Get total used budget.

        Returns:
            Total used tokens

        Example:
            >>> manager = ContextBudgetManager()
            >>> manager.allocate("skill1", 2000)
            >>> manager.use("skill1", 1500)
            >>> manager.get_total_used()
            1500
        """
        return sum(b.used for b in self._budgets.values())

    def _get_available(self) -> int:
        """Get available budget.

        Returns:
            Available tokens
        """
        allocated = sum(b.allocated for b in self._budgets.values())
        return self.total_budget - allocated

    def _reclaim_from_lower_priority(
        self,
        needed: int,
        min_priority: int,
    ) -> int:
        """Reclaim budget from lower priority skills.

        Args:
            needed: Amount of budget needed
            min_priority: Minimum priority to respect

        Returns:
            Amount reclaimed

        Example:
            >>> manager = ContextBudgetManager(total_budget=10000)
            >>> manager.allocate("low", 3000, priority=1)
            >>> manager.allocate("high", 8000, priority=2)  # Over budget
            >>> # Manager will reclaim from "low" priority skill
        """
        reclaimed = 0

        # Sort by priority (lowest first)
        candidates = sorted(
            self._budgets.items(),
            key=lambda x: x[1].priority,
        )

        for name, budget in candidates:
            if budget.priority >= min_priority:
                break

            reclaimable = budget.remaining
            if reclaimable > 0:
                take = min(reclaimable, needed - reclaimed)
                budget.allocated -= take
                reclaimed += take
                logger.info(
                    "budget_reclaimed",
                    from_skill=name,
                    amount=take,
                    priority=budget.priority,
                )

            if reclaimed >= needed:
                break

        return reclaimed
