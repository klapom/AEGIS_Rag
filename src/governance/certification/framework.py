"""Skill Certification Framework.

Core Components:
    - CertificationLevel: 4-tier certification levels (UNCERTIFIED → ENTERPRISE)
    - CertificationCheck: Single validation check result
    - CertificationReport: Complete certification report with recommendations
    - SkillCertificationFramework: Main certification engine

Certification Levels:
    - UNCERTIFIED: No validation passed
    - BASIC: name + version fields required
    - STANDARD: + GDPR + permissions
    - ENTERPRISE: + audit + explainability

Security Features:
    - Dangerous pattern detection (exec, eval, subprocess)
    - GDPR legal basis validation
    - Permission risk assessment
    - Audit integration checks
    - Explainability compliance

Example:
    >>> framework = SkillCertificationFramework()
    >>> report = await framework.certify(
    ...     skill_path=Path("skills/rag-retrieval"),
    ...     target_level=CertificationLevel.ENTERPRISE
    ... )
    >>> print(f"Achieved: {report.achieved_level.value}")
    >>> print(f"Passed: {report.passed}")
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from src.governance.gdpr.compliance import LegalBasis

logger = logging.getLogger(__name__)


class CertificationLevel(Enum):
    """Skill certification levels (lowest to highest).

    UNCERTIFIED: No validation passed
    BASIC: Syntax validation (name, version)
    STANDARD: + Security + GDPR + Permissions
    ENTERPRISE: + Audit + Explainability
    """

    UNCERTIFIED = "uncertified"
    BASIC = "basic"
    STANDARD = "standard"
    ENTERPRISE = "enterprise"

    def __lt__(self, other: "CertificationLevel") -> bool:
        """Compare certification levels."""
        order = [
            CertificationLevel.UNCERTIFIED,
            CertificationLevel.BASIC,
            CertificationLevel.STANDARD,
            CertificationLevel.ENTERPRISE,
        ]
        return order.index(self) < order.index(other)

    def __le__(self, other: "CertificationLevel") -> bool:
        """Compare certification levels (less than or equal)."""
        return self == other or self < other

    def __gt__(self, other: "CertificationLevel") -> bool:
        """Compare certification levels (greater than)."""
        return not self <= other

    def __ge__(self, other: "CertificationLevel") -> bool:
        """Compare certification levels (greater than or equal)."""
        return self == other or self > other


@dataclass
class CertificationCheck:
    """Single certification check result.

    Attributes:
        name: Check name (e.g., "syntax.name_field")
        passed: Whether check passed
        level_required: Minimum level requiring this check
        message: Human-readable message
        details: Additional details (optional)
    """

    name: str
    passed: bool
    level_required: CertificationLevel
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class CertificationReport:
    """Complete certification report.

    Attributes:
        skill_path: Path to skill directory
        target_level: Requested certification level
        achieved_level: Actual achieved level
        passed: Whether target level was achieved
        checks: List of all checks performed
        recommendations: List of improvement recommendations
        timestamp: Report generation timestamp
        expiry: Report expiry timestamp (90 days)
    """

    skill_path: Path
    target_level: CertificationLevel
    achieved_level: CertificationLevel
    passed: bool
    checks: List[CertificationCheck]
    recommendations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    expiry: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(days=90))

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "skill_path": str(self.skill_path),
            "target_level": self.target_level.value,
            "achieved_level": self.achieved_level.value,
            "passed": self.passed,
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "level_required": c.level_required.value,
                    "message": c.message,
                    "details": c.details,
                }
                for c in self.checks
            ],
            "recommendations": self.recommendations,
            "timestamp": self.timestamp.isoformat(),
            "expiry": self.expiry.isoformat(),
        }


# Required fields for each certification level
REQUIRED_SKILL_FIELDS = {
    CertificationLevel.BASIC: ["name", "version"],
    CertificationLevel.STANDARD: ["name", "version", "gdpr", "permissions"],
    CertificationLevel.ENTERPRISE: [
        "name",
        "version",
        "gdpr",
        "permissions",
        "audit",
        "explainability",
    ],
}

# Blocked code patterns (security risks)
BLOCKED_PATTERNS = [
    r"exec\s*\(",
    r"eval\s*\(",
    r"__import__",
    r"subprocess",
    r"os\.system",
]

# High-risk tool categories
HIGH_RISK_TOOLS = {
    "file_write",
    "file_delete",
    "network_request",
    "database_write",
    "shell_execute",
}


class SkillCertificationFramework:
    """Main skill certification engine.

    Validates skills against 3-tier certification requirements:
    - BASIC: Syntax validation
    - STANDARD: + Security + GDPR + Permissions
    - ENTERPRISE: + Audit + Explainability

    Attributes:
        None

    Example:
        >>> framework = SkillCertificationFramework()
        >>> report = await framework.certify(
        ...     skill_path=Path("skills/rag-retrieval"),
        ...     target_level=CertificationLevel.STANDARD
        ... )
    """

    def __init__(self):
        """Initialize certification framework."""
        pass

    async def certify(
        self,
        skill_path: Path,
        target_level: CertificationLevel = CertificationLevel.STANDARD,
    ) -> CertificationReport:
        """Certify skill against target certification level.

        Performs all checks required for target level and determines
        highest achieved level.

        Args:
            skill_path: Path to skill directory
            target_level: Target certification level

        Returns:
            Certification report with results and recommendations

        Example:
            >>> report = await framework.certify(
            ...     skill_path=Path("skills/rag-001"),
            ...     target_level=CertificationLevel.ENTERPRISE
            ... )
            >>> print(f"Achieved: {report.achieved_level.value}")
        """
        logger.info(f"Starting certification for {skill_path} | target={target_level.value}")

        # Load skill metadata
        meta_path = skill_path / "SKILL.md"
        if not meta_path.exists():
            logger.error(f"SKILL.md not found: {meta_path}")
            return CertificationReport(
                skill_path=skill_path,
                target_level=target_level,
                achieved_level=CertificationLevel.UNCERTIFIED,
                passed=False,
                checks=[
                    CertificationCheck(
                        name="file.skill_md_exists",
                        passed=False,
                        level_required=CertificationLevel.BASIC,
                        message="SKILL.md file not found",
                    )
                ],
                recommendations=["Create SKILL.md with required metadata"],
            )

        # Parse SKILL.md metadata
        try:
            meta = self._parse_skill_metadata(meta_path)
        except Exception as e:
            logger.error(f"Failed to parse SKILL.md: {e}")
            return CertificationReport(
                skill_path=skill_path,
                target_level=target_level,
                achieved_level=CertificationLevel.UNCERTIFIED,
                passed=False,
                checks=[
                    CertificationCheck(
                        name="file.skill_md_parse",
                        passed=False,
                        level_required=CertificationLevel.BASIC,
                        message=f"Failed to parse SKILL.md: {e}",
                    )
                ],
                recommendations=["Fix SKILL.md YAML syntax"],
            )

        # Run all checks
        all_checks: List[CertificationCheck] = []

        # Always run BASIC level checks
        all_checks.extend(self._check_syntax(meta, CertificationLevel.BASIC))

        # STANDARD level checks (only if target is STANDARD+)
        if target_level >= CertificationLevel.STANDARD:
            all_checks.extend(self._check_syntax(meta, CertificationLevel.STANDARD))
            all_checks.extend(self._check_security(skill_path, meta))
            all_checks.extend(await self._check_gdpr(meta))
            all_checks.extend(self._check_permissions(meta))

        # ENTERPRISE level checks (only if target is ENTERPRISE)
        if target_level >= CertificationLevel.ENTERPRISE:
            all_checks.extend(self._check_syntax(meta, CertificationLevel.ENTERPRISE))
            all_checks.extend(self._check_audit_integration(meta))
            all_checks.extend(self._check_explainability(meta))

        # Determine achieved level
        achieved_level = self._determine_level(all_checks)
        passed = achieved_level >= target_level

        # Generate recommendations
        recommendations = self._generate_recommendations(all_checks, achieved_level, target_level)

        report = CertificationReport(
            skill_path=skill_path,
            target_level=target_level,
            achieved_level=achieved_level,
            passed=passed,
            checks=all_checks,
            recommendations=recommendations,
        )

        logger.info(
            f"Certification complete: {skill_path} | "
            f"target={target_level.value} | achieved={achieved_level.value} | "
            f"passed={passed}"
        )

        return report

    def _parse_skill_metadata(self, meta_path: Path) -> Dict[str, Any]:
        """Parse SKILL.md YAML frontmatter.

        Args:
            meta_path: Path to SKILL.md file

        Returns:
            Parsed metadata dictionary

        Raises:
            ValueError: If YAML parsing fails
        """
        content = meta_path.read_text()

        # Extract YAML frontmatter (between --- markers)
        match = re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL | re.MULTILINE)
        if not match:
            raise ValueError("No YAML frontmatter found in SKILL.md")

        yaml_content = match.group(1)
        meta = yaml.safe_load(yaml_content)

        if not isinstance(meta, dict):
            raise ValueError("YAML frontmatter must be a dictionary")

        return meta

    def _check_syntax(
        self,
        meta: Dict[str, Any],
        check_level: CertificationLevel,
    ) -> List[CertificationCheck]:
        """Check required metadata fields for specific certification level.

        Args:
            meta: Parsed skill metadata
            check_level: Certification level to check fields for

        Returns:
            List of syntax check results
        """
        checks: List[CertificationCheck] = []

        # Get fields specific to this level (not cumulative)
        all_fields_for_level = REQUIRED_SKILL_FIELDS.get(check_level, [])

        # Get fields from previous levels to exclude
        if check_level == CertificationLevel.BASIC:
            level_specific_fields = all_fields_for_level
        elif check_level == CertificationLevel.STANDARD:
            basic_fields = REQUIRED_SKILL_FIELDS[CertificationLevel.BASIC]
            level_specific_fields = [f for f in all_fields_for_level if f not in basic_fields]
        elif check_level == CertificationLevel.ENTERPRISE:
            standard_fields = REQUIRED_SKILL_FIELDS[CertificationLevel.STANDARD]
            level_specific_fields = [f for f in all_fields_for_level if f not in standard_fields]
        else:
            level_specific_fields = []

        for field_name in level_specific_fields:
            exists = field_name in meta and meta[field_name] is not None
            checks.append(
                CertificationCheck(
                    name=f"syntax.field_{field_name}",
                    passed=exists,
                    level_required=check_level,
                    message=f"Field '{field_name}' {'present' if exists else 'missing'}",
                )
            )

        return checks

    def _check_security(
        self,
        skill_path: Path,
        meta: Dict[str, Any],
    ) -> List[CertificationCheck]:
        """Check for dangerous code patterns (STANDARD level).

        Scans all Python files in skill directory for:
        - exec/eval calls
        - __import__ usage
        - subprocess module
        - os.system calls

        Args:
            skill_path: Path to skill directory
            meta: Parsed skill metadata

        Returns:
            List of security check results
        """
        checks: List[CertificationCheck] = []

        # Scan all Python files
        python_files = list(skill_path.glob("**/*.py"))

        dangerous_patterns_found: List[Dict[str, str]] = []

        for py_file in python_files:
            try:
                code = py_file.read_text()

                for pattern in BLOCKED_PATTERNS:
                    matches = re.findall(pattern, code, re.IGNORECASE)
                    if matches:
                        dangerous_patterns_found.append(
                            {
                                "file": str(py_file.relative_to(skill_path)),
                                "pattern": pattern,
                                "matches": len(matches),
                            }
                        )
            except Exception as e:
                logger.warning(f"Failed to scan {py_file}: {e}")

        passed = len(dangerous_patterns_found) == 0

        checks.append(
            CertificationCheck(
                name="security.dangerous_patterns",
                passed=passed,
                level_required=CertificationLevel.STANDARD,
                message=(
                    "No dangerous patterns detected"
                    if passed
                    else f"{len(dangerous_patterns_found)} dangerous pattern(s) found"
                ),
                details={"patterns": dangerous_patterns_found} if not passed else None,
            )
        )

        return checks

    async def _check_gdpr(self, meta: Dict[str, Any]) -> List[CertificationCheck]:
        """Validate GDPR declarations (STANDARD level).

        Checks:
        - legal_basis is valid Article 6 basis
        - purpose is specified
        - retention_days is specified

        Args:
            meta: Parsed skill metadata

        Returns:
            List of GDPR check results
        """
        checks: List[CertificationCheck] = []

        gdpr = meta.get("gdpr", {})

        # Check legal_basis
        legal_basis = gdpr.get("legal_basis")
        valid_bases = {b.value for b in LegalBasis}
        legal_basis_valid = legal_basis in valid_bases

        checks.append(
            CertificationCheck(
                name="gdpr.legal_basis",
                passed=legal_basis_valid,
                level_required=CertificationLevel.STANDARD,
                message=(
                    f"Legal basis '{legal_basis}' is valid"
                    if legal_basis_valid
                    else f"Invalid legal basis: {legal_basis}"
                ),
                details={"valid_bases": list(valid_bases)},
            )
        )

        # Check purpose
        purpose = gdpr.get("purpose")
        purpose_valid = bool(purpose and isinstance(purpose, str))

        checks.append(
            CertificationCheck(
                name="gdpr.purpose",
                passed=purpose_valid,
                level_required=CertificationLevel.STANDARD,
                message=(
                    "Processing purpose specified"
                    if purpose_valid
                    else "Processing purpose missing"
                ),
            )
        )

        # Check retention_days
        retention_days = gdpr.get("retention_days")
        retention_valid = isinstance(retention_days, int) and retention_days > 0

        checks.append(
            CertificationCheck(
                name="gdpr.retention_days",
                passed=retention_valid,
                level_required=CertificationLevel.STANDARD,
                message=(
                    f"Retention period: {retention_days} days"
                    if retention_valid
                    else "Retention period not specified"
                ),
            )
        )

        return checks

    def _check_permissions(self, meta: Dict[str, Any]) -> List[CertificationCheck]:
        """Check permission declarations (STANDARD level).

        Validates:
        - Permissions list exists
        - High-risk permissions are flagged

        Args:
            meta: Parsed skill metadata

        Returns:
            List of permission check results
        """
        checks: List[CertificationCheck] = []

        permissions = meta.get("permissions", [])

        # Check permissions exist
        permissions_exist = isinstance(permissions, list) and len(permissions) > 0

        checks.append(
            CertificationCheck(
                name="permissions.declared",
                passed=permissions_exist,
                level_required=CertificationLevel.STANDARD,
                message=(
                    f"{len(permissions)} permission(s) declared"
                    if permissions_exist
                    else "No permissions declared"
                ),
            )
        )

        # Check for high-risk permissions
        if permissions_exist:
            high_risk = [p for p in permissions if p in HIGH_RISK_TOOLS]
            has_high_risk = len(high_risk) > 0

            checks.append(
                CertificationCheck(
                    name="permissions.high_risk",
                    passed=not has_high_risk,  # Passes if NO high-risk permissions
                    level_required=CertificationLevel.STANDARD,
                    message=(
                        f"High-risk permissions detected: {high_risk}"
                        if has_high_risk
                        else "No high-risk permissions"
                    ),
                    details={"high_risk_permissions": high_risk} if has_high_risk else None,
                )
            )

        return checks

    def _check_audit_integration(self, meta: Dict[str, Any]) -> List[CertificationCheck]:
        """Check audit integration (ENTERPRISE level).

        Validates:
        - Audit config exists
        - Required audit fields present

        Args:
            meta: Parsed skill metadata

        Returns:
            List of audit check results
        """
        checks: List[CertificationCheck] = []

        audit = meta.get("audit", {})

        # Check audit config exists
        audit_exists = isinstance(audit, dict) and len(audit) > 0

        checks.append(
            CertificationCheck(
                name="audit.config_exists",
                passed=audit_exists,
                level_required=CertificationLevel.ENTERPRISE,
                message=(
                    "Audit configuration present" if audit_exists else "Audit configuration missing"
                ),
            )
        )

        # Check required audit fields
        if audit_exists:
            required_fields = ["enabled", "events"]
            for field in required_fields:
                field_exists = field in audit

                checks.append(
                    CertificationCheck(
                        name=f"audit.field_{field}",
                        passed=field_exists,
                        level_required=CertificationLevel.ENTERPRISE,
                        message=(
                            f"Audit field '{field}' present"
                            if field_exists
                            else f"Audit field '{field}' missing"
                        ),
                    )
                )

        return checks

    def _check_explainability(self, meta: Dict[str, Any]) -> List[CertificationCheck]:
        """Check explainability compliance (ENTERPRISE level).

        Validates:
        - Explainability config exists
        - Decision logging enabled

        Args:
            meta: Parsed skill metadata

        Returns:
            List of explainability check results
        """
        checks: List[CertificationCheck] = []

        explainability = meta.get("explainability", {})

        # Check explainability config exists
        explainability_exists = isinstance(explainability, dict) and len(explainability) > 0

        checks.append(
            CertificationCheck(
                name="explainability.config_exists",
                passed=explainability_exists,
                level_required=CertificationLevel.ENTERPRISE,
                message=(
                    "Explainability configuration present"
                    if explainability_exists
                    else "Explainability configuration missing"
                ),
            )
        )

        # Check decision logging
        if explainability_exists:
            decision_logging = explainability.get("decision_logging", False)

            checks.append(
                CertificationCheck(
                    name="explainability.decision_logging",
                    passed=decision_logging,
                    level_required=CertificationLevel.ENTERPRISE,
                    message=(
                        "Decision logging enabled"
                        if decision_logging
                        else "Decision logging disabled"
                    ),
                )
            )

        return checks

    def _determine_level(self, checks: List[CertificationCheck]) -> CertificationLevel:
        """Determine highest achieved certification level.

        Finds highest level where ALL required checks pass.

        Args:
            checks: List of all checks performed

        Returns:
            Highest achieved certification level
        """
        # Group checks by level
        checks_by_level: Dict[CertificationLevel, List[CertificationCheck]] = {
            CertificationLevel.BASIC: [],
            CertificationLevel.STANDARD: [],
            CertificationLevel.ENTERPRISE: [],
        }

        for check in checks:
            if check.level_required in checks_by_level:
                checks_by_level[check.level_required].append(check)

        # Check each level in order (BASIC → STANDARD → ENTERPRISE)
        achieved = CertificationLevel.UNCERTIFIED

        for level in [
            CertificationLevel.BASIC,
            CertificationLevel.STANDARD,
            CertificationLevel.ENTERPRISE,
        ]:
            # Get all checks for this level only
            level_checks = checks_by_level[level]

            # If no checks for this level, we can't achieve it
            if len(level_checks) == 0:
                break

            # All checks for this level must pass
            if all(c.passed for c in level_checks):
                achieved = level
            else:
                break

        return achieved

    def _generate_recommendations(
        self,
        checks: List[CertificationCheck],
        achieved_level: CertificationLevel,
        target_level: CertificationLevel,
    ) -> List[str]:
        """Generate improvement recommendations.

        Args:
            checks: List of all checks performed
            achieved_level: Achieved certification level
            target_level: Target certification level

        Returns:
            List of recommendation strings
        """
        recommendations: List[str] = []

        # If target achieved, no recommendations needed
        if achieved_level >= target_level:
            return recommendations

        # Find failed checks
        failed_checks = [c for c in checks if not c.passed]

        # Group by level
        failed_by_level: Dict[CertificationLevel, List[CertificationCheck]] = {}
        for check in failed_checks:
            if check.level_required not in failed_by_level:
                failed_by_level[check.level_required] = []
            failed_by_level[check.level_required].append(check)

        # Generate recommendations for next level
        next_level_map = {
            CertificationLevel.UNCERTIFIED: CertificationLevel.BASIC,
            CertificationLevel.BASIC: CertificationLevel.STANDARD,
            CertificationLevel.STANDARD: CertificationLevel.ENTERPRISE,
        }

        next_level = next_level_map.get(achieved_level)
        if next_level and next_level in failed_by_level:
            recommendations.append(
                f"To achieve {next_level.value} certification, fix the following:"
            )
            for check in failed_by_level[next_level]:
                recommendations.append(f"  - {check.name}: {check.message}")

        return recommendations
