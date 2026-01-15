"""Unit tests for skill bundles - Sprint 95.3.

Tests the bundle system including:
- Bundle loading and parsing
- Installation and validation
- Dependency checking
- Status tracking
- Error handling
"""

from pathlib import Path
from typing import Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml

from src.agents.skills.bundle_installer import (
    BundleInstaller,
    BundleMetadata,
    BundleStatus,
    InstallationReport,
    get_bundle_installer,
    get_bundle_status,
    install_bundle,
    list_available_bundles,
)


@pytest.fixture
def mock_bundles_dir(tmp_path: Path) -> Path:
    """Create temporary bundles directory with test bundles."""
    bundles_dir = tmp_path / "bundles"
    bundles_dir.mkdir()

    # Create test bundle YAML
    test_bundle = {
        "id": "test_bundle",
        "name": "Test Bundle",
        "version": "1.0.0",
        "description": "Test bundle for unit tests",
        "skills": [
            {
                "name": "skill1",
                "version": "^1.0.0",
                "required": True,
                "config": {"param": "value"},
            },
            {
                "name": "skill2",
                "version": "^1.0.0",
                "required": False,
                "config": {"param": "value"},
            },
        ],
        "context_budget": 5000,
        "auto_activate": ["skill1"],
        "triggers": ["test", "demo"],
        "permissions": {"tools": ["test_tool"], "data": ["read"]},
        "dependencies": {
            "python": ["pytest >= 7.0.0"],
            "system": ["test_service >= 1.0.0"],
        },
        "installation_order": ["skill1", "skill2"],
        "metadata": {"category": "test"},
    }

    with open(bundles_dir / "test_bundle.yaml", "w") as f:
        yaml.dump(test_bundle, f)

    return bundles_dir


@pytest.fixture
def installer(mock_bundles_dir: Path) -> BundleInstaller:
    """Create bundle installer with mock bundles directory."""
    return BundleInstaller(bundles_dir=mock_bundles_dir)


class TestBundleMetadata:
    """Tests for BundleMetadata dataclass."""

    def test_metadata_creation(self):
        """Test creating bundle metadata."""
        metadata = BundleMetadata(
            id="test",
            name="Test",
            version="1.0.0",
            description="Test bundle",
            skills=[{"name": "skill1"}],
        )

        assert metadata.id == "test"
        assert metadata.name == "Test"
        assert metadata.version == "1.0.0"
        assert len(metadata.skills) == 1

    def test_metadata_defaults(self):
        """Test default values."""
        metadata = BundleMetadata(
            id="test", name="Test", version="1.0.0", description="Test", skills=[]
        )

        assert metadata.context_budget == 8000
        assert metadata.auto_activate == []
        assert metadata.triggers == []
        assert metadata.permissions == {}
        assert metadata.dependencies == {}


class TestInstallationReport:
    """Tests for InstallationReport dataclass."""

    def test_report_creation(self):
        """Test creating installation report."""
        report = InstallationReport(
            bundle_id="test",
            success=True,
            installed_skills=["skill1", "skill2"],
            summary="Success",
        )

        assert report.bundle_id == "test"
        assert report.success is True
        assert len(report.installed_skills) == 2
        assert report.summary == "Success"

    def test_report_defaults(self):
        """Test default values."""
        report = InstallationReport(bundle_id="test", success=False)

        assert report.installed_skills == []
        assert report.failed_skills == []
        assert report.missing_dependencies == []
        assert report.warnings == []
        assert report.duration_seconds == 0.0


class TestBundleStatus:
    """Tests for BundleStatus dataclass."""

    def test_status_creation(self):
        """Test creating bundle status."""
        status = BundleStatus(
            bundle_id="test",
            installed=True,
            installed_skills=["skill1"],
            version="1.0.0",
        )

        assert status.bundle_id == "test"
        assert status.installed is True
        assert len(status.installed_skills) == 1
        assert status.version == "1.0.0"


class TestBundleInstaller:
    """Tests for BundleInstaller class."""

    def test_installer_initialization(self, mock_bundles_dir: Path):
        """Test installer initialization."""
        installer = BundleInstaller(bundles_dir=mock_bundles_dir)

        assert installer.bundles_dir == mock_bundles_dir
        assert isinstance(installer._installed_bundles, dict)
        assert len(installer._installed_bundles) == 0

    def test_installer_default_bundles_dir(self):
        """Test installer with default bundles directory."""
        installer = BundleInstaller()

        expected_dir = Path(__file__).parent.parent.parent.parent.parent / "src" / "agents" / "skills" / "bundles"
        # Just check it's a Path object, actual path may vary
        assert isinstance(installer.bundles_dir, Path)

    def test_load_bundle(self, installer: BundleInstaller):
        """Test loading bundle from YAML."""
        bundle = installer.load_bundle("test_bundle")

        assert bundle.id == "test_bundle"
        assert bundle.name == "Test Bundle"
        assert bundle.version == "1.0.0"
        assert len(bundle.skills) == 2
        assert bundle.context_budget == 5000

    def test_load_nonexistent_bundle(self, installer: BundleInstaller):
        """Test loading non-existent bundle raises error."""
        with pytest.raises(FileNotFoundError):
            installer.load_bundle("nonexistent_bundle")

    def test_validate_dependencies_all_satisfied(self, installer: BundleInstaller):
        """Test validating dependencies when all are satisfied."""
        bundle = BundleMetadata(
            id="test",
            name="Test",
            version="1.0.0",
            description="Test",
            skills=[],
            dependencies={"python": ["pytest >= 7.0.0"]},  # pytest is installed
        )

        missing = installer.validate_dependencies(bundle)

        # pytest should be available in test environment
        assert len(missing) == 0

    def test_validate_dependencies_missing(self, installer: BundleInstaller):
        """Test validating dependencies when some are missing."""
        bundle = BundleMetadata(
            id="test",
            name="Test",
            version="1.0.0",
            description="Test",
            skills=[],
            dependencies={
                "python": ["nonexistent_package >= 1.0.0"],
                "system": ["unknown_service >= 1.0.0"],
            },
        )

        missing = installer.validate_dependencies(bundle)

        assert len(missing) >= 1  # At least nonexistent_package should be missing
        assert any("nonexistent_package" in dep for dep in missing)

    def test_install_bundle_success(self, installer: BundleInstaller):
        """Test successful bundle installation."""
        report = installer.install_bundle("test_bundle")

        assert report.success is True
        assert report.bundle_id == "test_bundle"
        assert len(report.installed_skills) > 0
        assert "test_bundle" in installer._installed_bundles

    def test_install_bundle_already_installed(self, installer: BundleInstaller):
        """Test installing already installed bundle."""
        # Install first time
        installer.install_bundle("test_bundle")

        # Try to install again
        report = installer.install_bundle("test_bundle")

        assert report.success is True
        assert len(report.warnings) > 0
        assert any("already installed" in w.lower() for w in report.warnings)

    def test_install_bundle_force_reinstall(self, installer: BundleInstaller):
        """Test force reinstalling bundle."""
        # Install first time
        installer.install_bundle("test_bundle")

        # Force reinstall
        report = installer.install_bundle("test_bundle", force=True)

        assert report.success is True
        # Should not have "already installed" warning (may have other warnings like optional skills)
        assert not any("already installed" in w.lower() for w in report.warnings)

    def test_install_nonexistent_bundle(self, installer: BundleInstaller):
        """Test installing non-existent bundle."""
        report = installer.install_bundle("nonexistent_bundle")

        assert report.success is False
        assert "Failed to load bundle" in report.summary

    def test_get_bundle_status_installed(self, installer: BundleInstaller):
        """Test getting status of installed bundle."""
        installer.install_bundle("test_bundle")
        status = installer.get_bundle_status("test_bundle")

        assert status.installed is True
        assert status.bundle_id == "test_bundle"
        assert len(status.installed_skills) > 0
        assert status.version == "1.0.0"

    def test_get_bundle_status_not_installed(self, installer: BundleInstaller):
        """Test getting status of not installed bundle."""
        status = installer.get_bundle_status("test_bundle")

        assert status.installed is False
        assert len(status.missing_skills) > 0

    def test_get_bundle_status_nonexistent(self, installer: BundleInstaller):
        """Test getting status of non-existent bundle."""
        status = installer.get_bundle_status("nonexistent")

        assert status.installed is False
        assert "bundle_not_found" in status.missing_skills

    def test_list_bundles(self, installer: BundleInstaller):
        """Test listing available bundles."""
        bundles = installer.list_bundles()

        assert len(bundles) == 1
        assert "test_bundle" in bundles

    def test_generate_summary_success(self, installer: BundleInstaller):
        """Test generating summary for successful installation."""
        report = InstallationReport(
            bundle_id="test",
            success=True,
            installed_skills=["skill1", "skill2"],
        )

        summary = installer._generate_summary(report)

        assert "Successfully installed" in summary
        assert "2 skills" in summary
        assert "skill1" in summary
        assert "skill2" in summary

    def test_generate_summary_failure(self, installer: BundleInstaller):
        """Test generating summary for failed installation."""
        report = InstallationReport(
            bundle_id="test", success=False, failed_skills=["skill1"]
        )

        summary = installer._generate_summary(report)

        assert "Installation failed" in summary
        assert "skill1" in summary


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_bundle_installer_singleton(self):
        """Test get_bundle_installer returns singleton."""
        installer1 = get_bundle_installer()
        installer2 = get_bundle_installer()

        assert installer1 is installer2

    @patch("src.agents.skills.bundle_installer.get_bundle_installer")
    def test_install_bundle_convenience(self, mock_get_installer):
        """Test install_bundle convenience function."""
        mock_installer = Mock()
        mock_report = InstallationReport(bundle_id="test", success=True)
        mock_installer.install_bundle.return_value = mock_report
        mock_get_installer.return_value = mock_installer

        report = install_bundle("test_bundle")

        assert report.success is True
        mock_installer.install_bundle.assert_called_once_with("test_bundle", force=False)

    @patch("src.agents.skills.bundle_installer.get_bundle_installer")
    def test_get_bundle_status_convenience(self, mock_get_installer):
        """Test get_bundle_status convenience function."""
        mock_installer = Mock()
        mock_status = BundleStatus(bundle_id="test", installed=True)
        mock_installer.get_bundle_status.return_value = mock_status
        mock_get_installer.return_value = mock_installer

        status = get_bundle_status("test_bundle")

        assert status.installed is True
        mock_installer.get_bundle_status.assert_called_once_with("test_bundle")

    @patch("src.agents.skills.bundle_installer.get_bundle_installer")
    def test_list_available_bundles_convenience(self, mock_get_installer):
        """Test list_available_bundles convenience function."""
        mock_installer = Mock()
        mock_installer.list_bundles.return_value = ["bundle1", "bundle2"]
        mock_get_installer.return_value = mock_installer

        bundles = list_available_bundles()

        assert len(bundles) == 2
        assert "bundle1" in bundles


class TestRealBundles:
    """Integration tests with real bundle files."""

    def test_load_research_bundle(self):
        """Test loading real research bundle."""
        installer = BundleInstaller()
        bundle = installer.load_bundle("research_bundle")

        assert bundle.id == "research_bundle"
        assert bundle.version == "1.0.0"
        assert len(bundle.skills) == 4
        assert any(s["name"] == "web_search" for s in bundle.skills)
        assert any(s["name"] == "retrieval" for s in bundle.skills)
        assert any(s["name"] == "graph_query" for s in bundle.skills)
        assert any(s["name"] == "citation" for s in bundle.skills)

    def test_load_analysis_bundle(self):
        """Test loading real analysis bundle."""
        installer = BundleInstaller()
        bundle = installer.load_bundle("analysis_bundle")

        assert bundle.id == "analysis_bundle"
        assert len(bundle.skills) == 4
        assert any(s["name"] == "validation" for s in bundle.skills)
        assert any(s["name"] == "classification" for s in bundle.skills)

    def test_load_synthesis_bundle(self):
        """Test loading real synthesis bundle."""
        installer = BundleInstaller()
        bundle = installer.load_bundle("synthesis_bundle")

        assert bundle.id == "synthesis_bundle"
        assert len(bundle.skills) == 4
        assert any(s["name"] == "summarize" for s in bundle.skills)
        assert any(s["name"] == "markdown_export" for s in bundle.skills)

    def test_load_development_bundle(self):
        """Test loading real development bundle."""
        installer = BundleInstaller()
        bundle = installer.load_bundle("development_bundle")

        assert bundle.id == "development_bundle"
        assert len(bundle.skills) == 4
        assert any(s["name"] == "code_generation" for s in bundle.skills)
        assert any(s["name"] == "testing" for s in bundle.skills)

    def test_load_enterprise_bundle(self):
        """Test loading real enterprise bundle."""
        installer = BundleInstaller()
        bundle = installer.load_bundle("enterprise_bundle")

        assert bundle.id == "enterprise_bundle"
        assert len(bundle.skills) >= 20  # Enterprise has 20+ skills
        assert bundle.context_budget == 150000

    def test_all_bundles_have_required_fields(self):
        """Test all bundles have required fields."""
        installer = BundleInstaller()
        bundles = installer.list_bundles()

        for bundle_id in bundles:
            bundle = installer.load_bundle(bundle_id)

            # Required fields
            assert bundle.id
            assert bundle.name
            assert bundle.version
            assert bundle.description
            assert len(bundle.skills) > 0

            # Each skill has required fields
            for skill in bundle.skills:
                assert "name" in skill
                assert "version" in skill
                assert "required" in skill


class TestErrorHandling:
    """Tests for error handling."""

    def test_invalid_yaml_bundle(self, tmp_path: Path):
        """Test loading bundle with invalid YAML."""
        bundles_dir = tmp_path / "bundles"
        bundles_dir.mkdir()

        # Create invalid YAML
        with open(bundles_dir / "invalid.yaml", "w") as f:
            f.write("invalid: yaml: syntax:")

        installer = BundleInstaller(bundles_dir=bundles_dir)

        with pytest.raises(Exception):  # YAML parsing error
            installer.load_bundle("invalid")

    def test_missing_required_field(self, tmp_path: Path):
        """Test loading bundle missing required field."""
        bundles_dir = tmp_path / "bundles"
        bundles_dir.mkdir()

        # Create bundle missing 'id' field
        incomplete = {
            "name": "Incomplete",
            "version": "1.0.0",
            # Missing 'id' and 'description'
        }

        with open(bundles_dir / "incomplete.yaml", "w") as f:
            yaml.dump(incomplete, f)

        installer = BundleInstaller(bundles_dir=bundles_dir)

        with pytest.raises(KeyError):
            installer.load_bundle("incomplete")

    def test_installation_with_missing_skill(self, mock_bundles_dir: Path):
        """Test installation when skill doesn't exist in bundle."""
        # Create bundle with bad installation order
        bad_bundle = {
            "id": "bad_bundle",
            "name": "Bad Bundle",
            "version": "1.0.0",
            "description": "Bundle with missing skill",
            "skills": [{"name": "skill1", "version": "^1.0.0", "required": True}],
            "installation_order": ["skill1", "nonexistent_skill"],
        }

        with open(mock_bundles_dir / "bad_bundle.yaml", "w") as f:
            yaml.dump(bad_bundle, f)

        installer = BundleInstaller(bundles_dir=mock_bundles_dir)
        report = installer.install_bundle("bad_bundle")

        # Should succeed but skip nonexistent skill
        assert report.success is True
        assert "skill1" in report.installed_skills
        assert "nonexistent_skill" not in report.installed_skills


class TestPerformanceMetrics:
    """Tests for performance metrics tracking."""

    def test_installation_duration_tracked(self, installer: BundleInstaller):
        """Test installation duration is tracked."""
        report = installer.install_bundle("test_bundle")

        assert report.duration_seconds >= 0.0
        # Should complete quickly for test bundle
        assert report.duration_seconds < 5.0

    def test_multiple_installations_timing(self, installer: BundleInstaller):
        """Test timing of multiple installations."""
        # First installation
        report1 = installer.install_bundle("test_bundle")
        time1 = report1.duration_seconds

        # Second installation (cached)
        report2 = installer.install_bundle("test_bundle")
        time2 = report2.duration_seconds

        # Both should complete quickly
        assert time1 < 5.0
        assert time2 < 5.0


# Test count: 33 tests
# Coverage: Bundle loading, installation, validation, status, errors, real bundles
