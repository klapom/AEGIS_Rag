"""Validation component for index consistency checks.

Sprint 49 Feature 49.6: Index Consistency Validation (TD-048)
"""

from src.components.validation.index_consistency import (
    IssueType,
    ValidationIssue,
    ValidationReport,
    fix_orphaned_chunks,
    fix_orphaned_entities,
    validate_index_consistency,
)

__all__ = [
    "ValidationReport",
    "ValidationIssue",
    "IssueType",
    "validate_index_consistency",
    "fix_orphaned_entities",
    "fix_orphaned_chunks",
]
