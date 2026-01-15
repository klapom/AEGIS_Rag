"""Unit tests for Skill Certification Framework.

Test Coverage:
- CertificationLevel enum comparison
- CertificationCheck dataclass
- CertificationReport dataclass and serialization
- SkillCertificationFramework certification logic
- All 4 certification levels (UNCERTIFIED, BASIC, STANDARD, ENTERPRISE)
- Security pattern detection
- GDPR validation
- Permission checks
- Audit integration checks
- Explainability checks
- Level determination logic
- Recommendation generation
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from src.governance.certification.framework import (
    BLOCKED_PATTERNS,
    HIGH_RISK_TOOLS,
    REQUIRED_SKILL_FIELDS,
    CertificationCheck,
    CertificationLevel,
    CertificationReport,
    SkillCertificationFramework,
)
from src.governance.gdpr.compliance import LegalBasis


class TestCertificationLevel:
    """Test CertificationLevel enum."""

    def test_level_ordering(self):
        """Test certification level comparison operators."""
        assert CertificationLevel.UNCERTIFIED < CertificationLevel.BASIC
        assert CertificationLevel.BASIC < CertificationLevel.STANDARD
        assert CertificationLevel.STANDARD < CertificationLevel.ENTERPRISE

        assert CertificationLevel.BASIC <= CertificationLevel.STANDARD
        assert CertificationLevel.STANDARD <= CertificationLevel.STANDARD

        assert CertificationLevel.ENTERPRISE > CertificationLevel.STANDARD
        assert CertificationLevel.STANDARD >= CertificationLevel.BASIC

    def test_level_equality(self):
        """Test certification level equality."""
        assert CertificationLevel.BASIC == CertificationLevel.BASIC
        assert CertificationLevel.BASIC != CertificationLevel.STANDARD

    def test_level_values(self):
        """Test certification level values."""
        assert CertificationLevel.UNCERTIFIED.value == "uncertified"
        assert CertificationLevel.BASIC.value == "basic"
        assert CertificationLevel.STANDARD.value == "standard"
        assert CertificationLevel.ENTERPRISE.value == "enterprise"


class TestCertificationCheck:
    """Test CertificationCheck dataclass."""

    def test_check_creation(self):
        """Test creating certification check."""
        check = CertificationCheck(
            name="test.check",
            passed=True,
            level_required=CertificationLevel.BASIC,
            message="Test check passed",
        )

        assert check.name == "test.check"
        assert check.passed is True
        assert check.level_required == CertificationLevel.BASIC
        assert check.message == "Test check passed"
        assert check.details is None

    def test_check_with_details(self):
        """Test check with details."""
        check = CertificationCheck(
            name="test.check",
            passed=False,
            level_required=CertificationLevel.STANDARD,
            message="Check failed",
            details={"error": "Missing field", "expected": "value"},
        )

        assert check.details == {"error": "Missing field", "expected": "value"}


class TestCertificationReport:
    """Test CertificationReport dataclass."""

    def test_report_creation(self):
        """Test creating certification report."""
        checks = [
            CertificationCheck(
                name="test.check",
                passed=True,
                level_required=CertificationLevel.BASIC,
                message="Test passed",
            )
        ]

        report = CertificationReport(
            skill_path=Path("/tmp/test-skill"),
            target_level=CertificationLevel.BASIC,
            achieved_level=CertificationLevel.BASIC,
            passed=True,
            checks=checks,
            recommendations=[],
        )

        assert report.skill_path == Path("/tmp/test-skill")
        assert report.target_level == CertificationLevel.BASIC
        assert report.achieved_level == CertificationLevel.BASIC
        assert report.passed is True
        assert len(report.checks) == 1
        assert len(report.recommendations) == 0

    def test_report_serialization(self):
        """Test report to_dict() serialization."""
        checks = [
            CertificationCheck(
                name="test.check",
                passed=True,
                level_required=CertificationLevel.BASIC,
                message="Test passed",
            )
        ]

        report = CertificationReport(
            skill_path=Path("/tmp/test-skill"),
            target_level=CertificationLevel.STANDARD,
            achieved_level=CertificationLevel.BASIC,
            passed=False,
            checks=checks,
            recommendations=["Fix GDPR declarations"],
        )

        data = report.to_dict()

        assert data["skill_path"] == "/tmp/test-skill"
        assert data["target_level"] == "standard"
        assert data["achieved_level"] == "basic"
        assert data["passed"] is False
        assert len(data["checks"]) == 1
        assert data["checks"][0]["name"] == "test.check"
        assert data["recommendations"] == ["Fix GDPR declarations"]
        assert "timestamp" in data
        assert "expiry" in data

    def test_report_expiry(self):
        """Test report expiry is 90 days from creation."""
        report = CertificationReport(
            skill_path=Path("/tmp/test"),
            target_level=CertificationLevel.BASIC,
            achieved_level=CertificationLevel.BASIC,
            passed=True,
            checks=[],
        )

        # Expiry should be ~90 days from now
        expiry_delta = report.expiry - report.timestamp
        assert 89 <= expiry_delta.days <= 91  # Allow 1 day tolerance


class TestSkillCertificationFramework:
    """Test SkillCertificationFramework main logic."""

    @pytest.fixture
    def framework(self):
        """Create framework instance."""
        return SkillCertificationFramework()

    @pytest.fixture
    def fixtures_dir(self):
        """Get fixtures directory path."""
        return Path(__file__).parent.parent.parent.parent / "fixtures" / "skills"

    # Test BASIC certification

    @pytest.mark.asyncio
    async def test_basic_certification_success(self, framework, fixtures_dir):
        """Test BASIC level certification success."""
        skill_path = fixtures_dir / "basic_skill"

        report = await framework.certify(skill_path, CertificationLevel.BASIC)

        assert report.achieved_level == CertificationLevel.BASIC
        assert report.passed is True
        assert report.target_level == CertificationLevel.BASIC

        # Check required field checks
        field_checks = [c for c in report.checks if c.name.startswith("syntax.field_")]
        assert len(field_checks) >= 2  # name, version
        assert all(c.passed for c in field_checks)

    @pytest.mark.asyncio
    async def test_missing_skill_md(self, framework, tmp_path):
        """Test certification with missing SKILL.md."""
        report = await framework.certify(tmp_path, CertificationLevel.BASIC)

        assert report.achieved_level == CertificationLevel.UNCERTIFIED
        assert report.passed is False
        assert len(report.checks) == 1
        assert report.checks[0].name == "file.skill_md_exists"
        assert not report.checks[0].passed

    @pytest.mark.asyncio
    async def test_invalid_skill_md_yaml(self, framework, tmp_path):
        """Test certification with invalid YAML in SKILL.md."""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\ninvalid: yaml: syntax: bad\n---")

        report = await framework.certify(tmp_path, CertificationLevel.BASIC)

        assert report.achieved_level == CertificationLevel.UNCERTIFIED
        assert report.passed is False
        assert report.checks[0].name == "file.skill_md_parse"

    @pytest.mark.asyncio
    async def test_missing_required_fields(self, framework, tmp_path):
        """Test certification with missing required fields."""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: test\n---")  # Missing version

        report = await framework.certify(tmp_path, CertificationLevel.BASIC)

        assert report.achieved_level == CertificationLevel.UNCERTIFIED
        assert report.passed is False

        # Check version field check failed
        version_check = next(c for c in report.checks if "version" in c.name)
        assert not version_check.passed

    # Test STANDARD certification

    @pytest.mark.asyncio
    async def test_standard_certification_success(self, framework, fixtures_dir):
        """Test STANDARD level certification success."""
        skill_path = fixtures_dir / "standard_skill"

        report = await framework.certify(skill_path, CertificationLevel.STANDARD)

        assert report.achieved_level == CertificationLevel.STANDARD
        assert report.passed is True

        # Check all check categories present
        check_names = [c.name for c in report.checks]
        assert any("syntax" in name for name in check_names)
        assert any("security" in name for name in check_names)
        assert any("gdpr" in name for name in check_names)
        assert any("permissions" in name for name in check_names)

    @pytest.mark.asyncio
    async def test_security_dangerous_patterns(self, framework, fixtures_dir):
        """Test security check detects dangerous patterns."""
        skill_path = fixtures_dir / "dangerous_skill"

        report = await framework.certify(skill_path, CertificationLevel.STANDARD)

        # Should not achieve STANDARD due to dangerous patterns
        assert report.achieved_level < CertificationLevel.STANDARD
        assert report.passed is False

        # Find security check
        security_check = next(
            c for c in report.checks if c.name == "security.dangerous_patterns"
        )
        assert not security_check.passed
        assert security_check.details is not None
        assert len(security_check.details["patterns"]) > 0

        # Verify dangerous patterns detected
        patterns = security_check.details["patterns"]
        pattern_strings = [p["pattern"] for p in patterns]
        assert any("exec" in p for p in pattern_strings)

    @pytest.mark.asyncio
    async def test_gdpr_validation(self, framework, fixtures_dir):
        """Test GDPR validation checks."""
        skill_path = fixtures_dir / "standard_skill"

        report = await framework.certify(skill_path, CertificationLevel.STANDARD)

        # Find GDPR checks
        gdpr_checks = [c for c in report.checks if c.name.startswith("gdpr.")]
        assert len(gdpr_checks) >= 3  # legal_basis, purpose, retention_days

        # All should pass for standard_skill
        assert all(c.passed for c in gdpr_checks)

    @pytest.mark.asyncio
    async def test_gdpr_invalid_legal_basis(self, framework, tmp_path):
        """Test GDPR check with invalid legal basis."""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            """---
name: test
version: 1.0.0
gdpr:
  legal_basis: invalid_basis
  purpose: Test
  retention_days: 30
permissions:
  - file_read
---"""
        )

        report = await framework.certify(tmp_path, CertificationLevel.STANDARD)

        # Find legal_basis check
        legal_basis_check = next(c for c in report.checks if c.name == "gdpr.legal_basis")
        assert not legal_basis_check.passed

    @pytest.mark.asyncio
    async def test_permissions_validation(self, framework, fixtures_dir):
        """Test permission validation checks."""
        skill_path = fixtures_dir / "standard_skill"

        report = await framework.certify(skill_path, CertificationLevel.STANDARD)

        # Find permission checks
        perm_checks = [c for c in report.checks if c.name.startswith("permissions.")]
        assert len(perm_checks) >= 2  # declared, high_risk

        # Check declared permissions
        declared_check = next(c for c in perm_checks if c.name == "permissions.declared")
        assert declared_check.passed

    @pytest.mark.asyncio
    async def test_high_risk_permissions(self, framework, tmp_path):
        """Test high-risk permission detection."""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            """---
name: test
version: 1.0.0
gdpr:
  legal_basis: consent
  purpose: Test
  retention_days: 30
permissions:
  - file_read
  - file_delete
  - database_write
---"""
        )

        report = await framework.certify(tmp_path, CertificationLevel.STANDARD)

        # Find high-risk check
        high_risk_check = next(
            c for c in report.checks if c.name == "permissions.high_risk"
        )
        assert not high_risk_check.passed  # Should fail due to high-risk permissions
        assert high_risk_check.details is not None
        assert "file_delete" in high_risk_check.details["high_risk_permissions"]
        assert "database_write" in high_risk_check.details["high_risk_permissions"]

    # Test ENTERPRISE certification

    @pytest.mark.asyncio
    async def test_enterprise_certification_success(self, framework, fixtures_dir):
        """Test ENTERPRISE level certification success."""
        skill_path = fixtures_dir / "enterprise_skill"

        report = await framework.certify(skill_path, CertificationLevel.ENTERPRISE)

        assert report.achieved_level == CertificationLevel.ENTERPRISE
        assert report.passed is True

        # Check all check categories present
        check_names = [c.name for c in report.checks]
        assert any("audit" in name for name in check_names)
        assert any("explainability" in name for name in check_names)

    @pytest.mark.asyncio
    async def test_audit_integration_checks(self, framework, fixtures_dir):
        """Test audit integration validation."""
        skill_path = fixtures_dir / "enterprise_skill"

        report = await framework.certify(skill_path, CertificationLevel.ENTERPRISE)

        # Find audit checks
        audit_checks = [c for c in report.checks if c.name.startswith("audit.")]
        assert len(audit_checks) >= 1

        # All should pass for enterprise_skill
        assert all(c.passed for c in audit_checks)

    @pytest.mark.asyncio
    async def test_audit_missing_config(self, framework, tmp_path):
        """Test audit check with missing config."""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            """---
name: test
version: 1.0.0
gdpr:
  legal_basis: consent
  purpose: Test
  retention_days: 30
permissions:
  - file_read
explainability:
  decision_logging: true
---"""
        )  # Missing audit section

        report = await framework.certify(tmp_path, CertificationLevel.ENTERPRISE)

        # Find audit config check
        audit_check = next(c for c in report.checks if c.name == "audit.config_exists")
        assert not audit_check.passed

    @pytest.mark.asyncio
    async def test_explainability_checks(self, framework, fixtures_dir):
        """Test explainability validation."""
        skill_path = fixtures_dir / "enterprise_skill"

        report = await framework.certify(skill_path, CertificationLevel.ENTERPRISE)

        # Find explainability checks
        explain_checks = [c for c in report.checks if c.name.startswith("explainability.")]
        assert len(explain_checks) >= 1

        # All should pass for enterprise_skill
        assert all(c.passed for c in explain_checks)

    @pytest.mark.asyncio
    async def test_explainability_missing_config(self, framework, tmp_path):
        """Test explainability check with missing config."""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            """---
name: test
version: 1.0.0
gdpr:
  legal_basis: consent
  purpose: Test
  retention_days: 30
permissions:
  - file_read
audit:
  enabled: true
  events: []
---"""
        )  # Missing explainability section

        report = await framework.certify(tmp_path, CertificationLevel.ENTERPRISE)

        # Find explainability config check
        explain_check = next(
            c for c in report.checks if c.name == "explainability.config_exists"
        )
        assert not explain_check.passed

    # Test level determination

    def test_determine_level_all_pass(self, framework):
        """Test level determination when all checks pass."""
        checks = [
            CertificationCheck(
                "syntax.name", True, CertificationLevel.BASIC, "Passed"
            ),
            CertificationCheck(
                "syntax.version", True, CertificationLevel.BASIC, "Passed"
            ),
            CertificationCheck(
                "security.patterns", True, CertificationLevel.STANDARD, "Passed"
            ),
            CertificationCheck(
                "gdpr.legal_basis", True, CertificationLevel.STANDARD, "Passed"
            ),
            CertificationCheck(
                "audit.config", True, CertificationLevel.ENTERPRISE, "Passed"
            ),
        ]

        level = framework._determine_level(checks)
        assert level == CertificationLevel.ENTERPRISE

    def test_determine_level_partial_pass(self, framework):
        """Test level determination with partial pass."""
        checks = [
            CertificationCheck(
                "syntax.name", True, CertificationLevel.BASIC, "Passed"
            ),
            CertificationCheck(
                "syntax.version", True, CertificationLevel.BASIC, "Passed"
            ),
            CertificationCheck(
                "security.patterns", True, CertificationLevel.STANDARD, "Passed"
            ),
            CertificationCheck(
                "gdpr.legal_basis", False, CertificationLevel.STANDARD, "Failed"
            ),
            CertificationCheck(
                "audit.config", True, CertificationLevel.ENTERPRISE, "Passed"
            ),
        ]

        level = framework._determine_level(checks)
        assert level == CertificationLevel.BASIC  # STANDARD check failed

    def test_determine_level_basic_fail(self, framework):
        """Test level determination when BASIC checks fail."""
        checks = [
            CertificationCheck(
                "syntax.name", True, CertificationLevel.BASIC, "Passed"
            ),
            CertificationCheck(
                "syntax.version", False, CertificationLevel.BASIC, "Failed"
            ),
        ]

        level = framework._determine_level(checks)
        assert level == CertificationLevel.UNCERTIFIED

    # Test recommendation generation

    def test_generate_recommendations_target_achieved(self, framework):
        """Test recommendations when target level achieved."""
        checks = [
            CertificationCheck(
                "syntax.name", True, CertificationLevel.BASIC, "Passed"
            ),
        ]

        recommendations = framework._generate_recommendations(
            checks, CertificationLevel.BASIC, CertificationLevel.BASIC
        )

        assert len(recommendations) == 0

    def test_generate_recommendations_target_not_achieved(self, framework):
        """Test recommendations when target level not achieved."""
        checks = [
            CertificationCheck(
                "syntax.name", True, CertificationLevel.BASIC, "Passed"
            ),
            CertificationCheck(
                "syntax.version", True, CertificationLevel.BASIC, "Passed"
            ),
            CertificationCheck(
                "security.patterns", False, CertificationLevel.STANDARD, "Failed"
            ),
            CertificationCheck(
                "gdpr.legal_basis", False, CertificationLevel.STANDARD, "Failed"
            ),
        ]

        recommendations = framework._generate_recommendations(
            checks, CertificationLevel.BASIC, CertificationLevel.STANDARD
        )

        assert len(recommendations) > 0
        assert any("standard" in r.lower() for r in recommendations)
        assert any("security.patterns" in r for r in recommendations)
        assert any("gdpr.legal_basis" in r for r in recommendations)

    # Test metadata parsing

    def test_parse_skill_metadata_valid(self, framework, fixtures_dir):
        """Test parsing valid SKILL.md metadata."""
        skill_path = fixtures_dir / "standard_skill" / "SKILL.md"

        meta = framework._parse_skill_metadata(skill_path)

        assert meta["name"] == "standard-skill"
        assert meta["version"] == "2.0.0"
        assert "gdpr" in meta
        assert "permissions" in meta

    def test_parse_skill_metadata_no_frontmatter(self, framework, tmp_path):
        """Test parsing SKILL.md without frontmatter."""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("# Just a markdown file\n\nNo YAML frontmatter here.")

        with pytest.raises(ValueError, match="No YAML frontmatter"):
            framework._parse_skill_metadata(skill_md)

    def test_parse_skill_metadata_invalid_yaml(self, framework, tmp_path):
        """Test parsing SKILL.md with invalid YAML."""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\ninvalid: yaml: : :\n---")

        with pytest.raises(Exception):  # YAML parse error
            framework._parse_skill_metadata(skill_md)


class TestRequiredFieldsConfiguration:
    """Test REQUIRED_SKILL_FIELDS configuration."""

    def test_required_fields_basic(self):
        """Test BASIC level required fields."""
        fields = REQUIRED_SKILL_FIELDS[CertificationLevel.BASIC]
        assert "name" in fields
        assert "version" in fields
        assert len(fields) == 2

    def test_required_fields_standard(self):
        """Test STANDARD level required fields."""
        fields = REQUIRED_SKILL_FIELDS[CertificationLevel.STANDARD]
        assert "name" in fields
        assert "version" in fields
        assert "gdpr" in fields
        assert "permissions" in fields
        assert len(fields) == 4

    def test_required_fields_enterprise(self):
        """Test ENTERPRISE level required fields."""
        fields = REQUIRED_SKILL_FIELDS[CertificationLevel.ENTERPRISE]
        assert "name" in fields
        assert "version" in fields
        assert "gdpr" in fields
        assert "permissions" in fields
        assert "audit" in fields
        assert "explainability" in fields
        assert len(fields) == 6


class TestSecurityConfiguration:
    """Test security configuration."""

    def test_blocked_patterns(self):
        """Test BLOCKED_PATTERNS list."""
        assert len(BLOCKED_PATTERNS) >= 5
        assert any("exec" in p for p in BLOCKED_PATTERNS)
        assert any("eval" in p for p in BLOCKED_PATTERNS)
        assert any("__import__" in p for p in BLOCKED_PATTERNS)
        assert any("subprocess" in p for p in BLOCKED_PATTERNS)
        assert any("os" in p and "system" in p for p in BLOCKED_PATTERNS)

    def test_high_risk_tools(self):
        """Test HIGH_RISK_TOOLS set."""
        assert "file_write" in HIGH_RISK_TOOLS
        assert "file_delete" in HIGH_RISK_TOOLS
        assert "network_request" in HIGH_RISK_TOOLS
        assert "database_write" in HIGH_RISK_TOOLS
        assert "shell_execute" in HIGH_RISK_TOOLS
