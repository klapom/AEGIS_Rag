"""Security module for permission management and access control.

Sprint Context:
    - Sprint 91 (2026-01-14): Permission Engine (8 SP)

This module provides security and access control for skill execution:
- Permission enum for capability types
- PermissionPolicy for user/role policies
- PermissionEngine for checking and enforcing permissions

Architecture:
    Skill Activation → Permission Check → Allow/Deny → Skill Execution

Based on: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
"""

from src.agents.security.permission_engine import (
    Permission,
    PermissionEngine,
    PermissionPolicy,
)

__all__ = [
    "Permission",
    "PermissionEngine",
    "PermissionPolicy",
]
