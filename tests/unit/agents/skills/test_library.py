"""Unit tests for Skill Libraries & Bundles.

Sprint 95 Feature 95.2: Skill Libraries & Bundles (8 SP)

Test Coverage:
    - SkillMetadata: Creation, validation, search matching
    - SkillManifest: YAML parsing, conversion to metadata
    - SkillBundle: Creation, skill extraction, serialization
    - SkillLibrary: Discovery, path resolution
    - SkillLibraryManager: Registration, search, bundle loading
    - Dependency validation
    - Version compatibility

Target: 40+ tests, 100% coverage
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
import yaml

from src.agents.skills.library import (
    SkillBundle,
    SkillLibrary,
    SkillLibraryManager,
    SkillManifest,
    SkillMetadata,
)


# =============================================================================
# Test SkillMetadata
# =============================================================================


class TestSkillMetadata:
    """Tests for SkillMetadata dataclass."""

    def test_metadata_creation(self):
        """Test creating SkillMetadata."""
        metadata = SkillMetadata(
            name="web_search",
            version="1.0.0",
            description="Web search skill",
            capabilities=["search", "web_access"],
            dependencies=["requests>=2.28.0"],
            tools=["google_search"],
            tags=["research", "web"],
        )

        assert metadata.name == "web_search"
        assert metadata.version == "1.0.0"
        assert "search" in metadata.capabilities
        assert "research" in metadata.tags

    def test_metadata_matches_query(self):
        """Test query matching."""
        metadata = SkillMetadata(
            name="web_search",
            version="1.0.0",
            description="Search the web using multiple engines",
            tags=["research", "web"],
        )

        assert metadata.matches_query("web")
        assert metadata.matches_query("search")
        assert metadata.matches_query("research")
        assert not metadata.matches_query("database")

    def test_metadata_matches_query_case_insensitive(self):
        """Test query matching is case-insensitive."""
        metadata = SkillMetadata(
            name="WebSearch",
            version="1.0.0",
            description="Web Search Tool",
            tags=["Research"],
        )

        assert metadata.matches_query("web")
        assert metadata.matches_query("WEB")
        assert metadata.matches_query("research")

    def test_metadata_has_capability(self):
        """Test capability checking."""
        metadata = SkillMetadata(
            name="web_search",
            version="1.0.0",
            description="",
            capabilities=["search", "web_access"],
        )

        assert metadata.has_capability("search")
        assert metadata.has_capability("web_access")
        assert not metadata.has_capability("database")

    def test_metadata_has_capability_case_insensitive(self):
        """Test capability checking is case-insensitive."""
        metadata = SkillMetadata(
            name="test",
            version="1.0.0",
            description="",
            capabilities=["Search", "WebAccess"],
        )

        assert metadata.has_capability("search")
        assert metadata.has_capability("WEBACCESS")

    def test_metadata_to_dict(self):
        """Test serialization to dict."""
        metadata = SkillMetadata(
            name="web_search",
            version="1.0.0",
            description="Web search",
            capabilities=["search"],
        )

        data = metadata.to_dict()

        assert data["name"] == "web_search"
        assert data["version"] == "1.0.0"
        assert "search" in data["capabilities"]

    def test_metadata_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "name": "web_search",
            "version": "1.0.0",
            "description": "Web search",
            "capabilities": ["search"],
            "dependencies": ["requests>=2.28.0"],
        }

        metadata = SkillMetadata.from_dict(data)

        assert metadata.name == "web_search"
        assert metadata.version == "1.0.0"
        assert "search" in metadata.capabilities

    def test_metadata_from_dict_with_defaults(self):
        """Test deserialization with missing fields uses defaults."""
        data = {"name": "test"}

        metadata = SkillMetadata.from_dict(data)

        assert metadata.name == "test"
        assert metadata.version == "1.0.0"
        assert metadata.capabilities == []


# =============================================================================
# Test SkillManifest
# =============================================================================


class TestSkillManifest:
    """Tests for SkillManifest."""

    def test_manifest_creation(self):
        """Test creating SkillManifest."""
        manifest = SkillManifest(
            name="web_search",
            version="1.0.0",
            description="Web search skill",
            skill_path=Path("skills/web_search/SKILL.md"),
            capabilities=["search"],
        )

        assert manifest.name == "web_search"
        assert manifest.skill_path.name == "SKILL.md"

    def test_manifest_from_yaml(self, tmp_path):
        """Test loading manifest from YAML."""
        skill_dir = tmp_path / "web_search"
        skill_dir.mkdir()

        manifest_yaml = skill_dir / "MANIFEST.yaml"
        manifest_yaml.write_text(
            yaml.dump(
                {
                    "name": "web_search",
                    "version": "1.0.0",
                    "description": "Web search",
                    "capabilities": ["search"],
                    "dependencies": ["requests>=2.28.0"],
                }
            )
        )

        manifest = SkillManifest.from_yaml(manifest_yaml)

        assert manifest.name == "web_search"
        assert manifest.version == "1.0.0"
        assert "search" in manifest.capabilities

    def test_manifest_to_metadata(self):
        """Test conversion to SkillMetadata."""
        manifest = SkillManifest(
            name="web_search",
            version="1.0.0",
            description="Web search",
            skill_path=Path("skills/web_search/SKILL.md"),
            capabilities=["search"],
            dependencies=["requests>=2.28.0"],
        )

        metadata = manifest.to_metadata()

        assert isinstance(metadata, SkillMetadata)
        assert metadata.name == "web_search"
        assert metadata.capabilities == ["search"]


# =============================================================================
# Test SkillBundle
# =============================================================================


class TestSkillBundle:
    """Tests for SkillBundle dataclass."""

    def test_bundle_creation(self):
        """Test creating SkillBundle."""
        bundle = SkillBundle(
            name="research_assistant",
            version="1.0.0",
            description="Research workflow",
            skills=["core/retrieval", "research/web_search"],
            context_budget=8000,
        )

        assert bundle.name == "research_assistant"
        assert len(bundle.skills) == 2
        assert bundle.context_budget == 8000

    def test_bundle_get_skill_names(self):
        """Test extracting skill names from paths."""
        bundle = SkillBundle(
            name="test",
            version="1.0.0",
            description="",
            skills=["core/retrieval", "research/web_search", "synthesis"],
        )

        names = bundle.get_skill_names()

        assert "retrieval" in names
        assert "web_search" in names
        assert "synthesis" in names
        assert len(names) == 3

    def test_bundle_to_dict(self):
        """Test serialization to dict."""
        bundle = SkillBundle(
            name="research",
            version="1.0.0",
            description="Research bundle",
            skills=["core/retrieval"],
            context_budget=5000,
            auto_activate=["retrieval"],
        )

        data = bundle.to_dict()

        assert data["name"] == "research"
        assert data["context_budget"] == 5000
        assert "retrieval" in data["auto_activate"]

    def test_bundle_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "name": "research",
            "version": "1.0.0",
            "description": "Research bundle",
            "skills": ["core/retrieval"],
            "context_budget": 5000,
        }

        bundle = SkillBundle.from_dict(data)

        assert bundle.name == "research"
        assert bundle.context_budget == 5000
        assert "core/retrieval" in bundle.skills


# =============================================================================
# Test SkillLibrary
# =============================================================================


class TestSkillLibrary:
    """Tests for SkillLibrary dataclass."""

    def test_library_creation(self):
        """Test creating SkillLibrary."""
        library = SkillLibrary(
            name="research",
            version="1.0.0",
            description="Research skills",
            skills=["web_search", "academic"],
            path=Path("skill_libraries/research"),
        )

        assert library.name == "research"
        assert len(library.skills) == 2

    def test_library_get_skill_path(self, tmp_path):
        """Test getting skill path."""
        lib_dir = tmp_path / "research"
        lib_dir.mkdir()

        skill_dir = lib_dir / "web_search"
        skill_dir.mkdir()

        library = SkillLibrary(
            name="research",
            version="1.0.0",
            description="",
            skills=["web_search"],
            path=lib_dir,
        )

        path = library.get_skill_path("web_search")

        assert path is not None
        assert path.name == "web_search"

    def test_library_get_skill_path_not_found(self, tmp_path):
        """Test getting path for non-existent skill."""
        library = SkillLibrary(
            name="research",
            version="1.0.0",
            description="",
            skills=["web_search"],
            path=tmp_path,
        )

        path = library.get_skill_path("nonexistent")

        assert path is None

    def test_library_to_dict(self):
        """Test serialization to dict."""
        library = SkillLibrary(
            name="research",
            version="1.0.0",
            description="Research skills",
            skills=["web_search"],
            path=Path("skill_libraries/research"),
        )

        data = library.to_dict()

        assert data["name"] == "research"
        assert "web_search" in data["skills"]


# =============================================================================
# Test SkillLibraryManager
# =============================================================================


class TestSkillLibraryManager:
    """Tests for SkillLibraryManager."""

    @pytest.fixture
    def mock_lifecycle(self):
        """Create mock SkillLifecycleManager."""
        mock = Mock()
        mock.load = AsyncMock()
        mock.activate = AsyncMock()
        mock.unload = AsyncMock()
        return mock

    @pytest.fixture
    def manager(self, tmp_path, mock_lifecycle):
        """Create SkillLibraryManager with temp directory."""
        return SkillLibraryManager(
            libraries_dir=tmp_path,
            skill_manager=mock_lifecycle,
        )

    def test_manager_initialization(self, tmp_path, mock_lifecycle):
        """Test manager initialization."""
        manager = SkillLibraryManager(
            libraries_dir=tmp_path,
            skill_manager=mock_lifecycle,
        )

        assert manager.libraries_dir == tmp_path
        assert manager.skills == mock_lifecycle

    def test_register_skill(self, manager):
        """Test registering a skill."""
        metadata = SkillMetadata(
            name="web_search",
            version="1.0.0",
            description="Web search",
            capabilities=["search"],
        )

        manager.register_skill("web_search", metadata)

        assert "web_search" in manager._skill_metadata
        assert manager._skill_metadata["web_search"].capabilities == ["search"]

    def test_get_skill(self, manager):
        """Test retrieving a skill."""
        metadata = SkillMetadata(
            name="web_search",
            version="1.0.0",
            description="Web search",
        )
        manager.register_skill("web_search", metadata)

        result = manager.get_skill("web_search")

        assert result is not None
        assert result.name == "web_search"

    def test_get_skill_with_version(self, manager):
        """Test retrieving skill with version constraint."""
        metadata = SkillMetadata(
            name="web_search",
            version="1.0.0",
            description="Web search",
        )
        manager.register_skill("web_search", metadata)

        result = manager.get_skill("web_search", "1.0.0")

        assert result is not None

    def test_get_skill_version_mismatch(self, manager):
        """Test getting skill with wrong version returns None."""
        metadata = SkillMetadata(
            name="web_search",
            version="1.0.0",
            description="Web search",
        )
        manager.register_skill("web_search", metadata)

        result = manager.get_skill("web_search", "2.0.0")

        assert result is None

    def test_search_skills_by_query(self, manager):
        """Test searching skills by query."""
        manager.register_skill(
            "web_search",
            SkillMetadata(
                name="web_search",
                version="1.0.0",
                description="Search the web",
            ),
        )
        manager.register_skill(
            "database",
            SkillMetadata(
                name="database",
                version="1.0.0",
                description="Database operations",
            ),
        )

        results = manager.search_skills(query="web")

        assert len(results) == 1
        assert results[0].name == "web_search"

    def test_search_skills_by_capabilities(self, manager):
        """Test searching skills by capabilities."""
        manager.register_skill(
            "web_search",
            SkillMetadata(
                name="web_search",
                version="1.0.0",
                description="",
                capabilities=["search", "web_access"],
            ),
        )
        manager.register_skill(
            "database",
            SkillMetadata(
                name="database",
                version="1.0.0",
                description="",
                capabilities=["database"],
            ),
        )

        results = manager.search_skills(capabilities=["search"])

        assert len(results) == 1
        assert results[0].name == "web_search"

    def test_search_skills_multiple_capabilities(self, manager):
        """Test searching with multiple required capabilities."""
        manager.register_skill(
            "web_search",
            SkillMetadata(
                name="web_search",
                version="1.0.0",
                description="",
                capabilities=["search", "web_access"],
            ),
        )
        manager.register_skill(
            "local_search",
            SkillMetadata(
                name="local_search",
                version="1.0.0",
                description="",
                capabilities=["search"],
            ),
        )

        results = manager.search_skills(capabilities=["search", "web_access"])

        assert len(results) == 1
        assert results[0].name == "web_search"

    @pytest.mark.asyncio
    async def test_load_bundle(self, manager, mock_lifecycle):
        """Test loading a skill bundle."""
        bundle = SkillBundle(
            name="research",
            version="1.0.0",
            description="Research bundle",
            skills=["core/retrieval", "research/web_search"],
            context_budget=8000,
        )
        manager._bundles["research"] = bundle

        loaded = await manager.load_bundle("research")

        assert len(loaded) == 2
        assert "retrieval" in loaded
        assert "web_search" in loaded
        assert mock_lifecycle.load.call_count == 2

    @pytest.mark.asyncio
    async def test_load_bundle_with_auto_activate(self, manager, mock_lifecycle):
        """Test loading bundle with auto-activation."""
        bundle = SkillBundle(
            name="research",
            version="1.0.0",
            description="",
            skills=["core/retrieval", "research/web_search"],
            context_budget=8000,
            auto_activate=["retrieval"],
        )
        manager._bundles["research"] = bundle

        await manager.load_bundle("research")

        assert mock_lifecycle.activate.call_count == 1

    @pytest.mark.asyncio
    async def test_load_bundle_not_found(self, manager):
        """Test loading non-existent bundle raises error."""
        with pytest.raises(ValueError, match="Bundle not found"):
            await manager.load_bundle("nonexistent")

    @pytest.mark.asyncio
    async def test_load_bundle_with_custom_budget(self, manager, mock_lifecycle):
        """Test loading bundle with custom context budget."""
        bundle = SkillBundle(
            name="research",
            version="1.0.0",
            description="",
            skills=["core/retrieval"],
            context_budget=5000,
        )
        manager._bundles["research"] = bundle

        await manager.load_bundle("research", context_budget=10000)

        # Budget should be split among skills
        mock_lifecycle.load.assert_called()

    @pytest.mark.asyncio
    async def test_unload_bundle(self, manager, mock_lifecycle):
        """Test unloading a bundle."""
        bundle = SkillBundle(
            name="research",
            version="1.0.0",
            description="",
            skills=["core/retrieval", "research/web_search"],
        )
        manager._bundles["research"] = bundle
        manager._loaded_bundles.add("research")

        success = await manager.unload_bundle("research")

        assert success
        assert "research" not in manager._loaded_bundles
        assert mock_lifecycle.unload.call_count == 2

    @pytest.mark.asyncio
    async def test_unload_bundle_not_found(self, manager):
        """Test unloading non-existent bundle."""
        success = await manager.unload_bundle("nonexistent")

        assert not success

    def test_list_skills(self, manager):
        """Test listing all skills."""
        manager.register_skill(
            "web_search",
            SkillMetadata(name="web_search", version="1.0.0", description=""),
        )
        manager.register_skill(
            "database",
            SkillMetadata(name="database", version="1.0.0", description=""),
        )

        skills = manager.list_skills()

        assert len(skills) == 2
        assert "web_search" in skills
        assert "database" in skills

    def test_list_libraries(self, manager):
        """Test listing all libraries."""
        manager._libraries["core"] = SkillLibrary(
            name="core",
            version="1.0.0",
            description="",
            skills=[],
        )
        manager._libraries["research"] = SkillLibrary(
            name="research",
            version="1.0.0",
            description="",
            skills=[],
        )

        libraries = manager.list_libraries()

        assert len(libraries) == 2
        assert "core" in libraries

    def test_list_bundles(self, manager):
        """Test listing all bundles."""
        manager._bundles["research"] = SkillBundle(
            name="research",
            version="1.0.0",
            description="",
            skills=[],
        )

        bundles = manager.list_bundles()

        assert len(bundles) == 1
        assert "research" in bundles

    def test_get_library_skills(self, manager):
        """Test getting skills in a library."""
        library = SkillLibrary(
            name="research",
            version="1.0.0",
            description="",
            skills=["web_search", "academic"],
        )
        manager._libraries["research"] = library

        skills = manager.get_library_skills("research")

        assert len(skills) == 2
        assert "web_search" in skills

    def test_get_bundle_skills(self, manager):
        """Test getting skills in a bundle."""
        bundle = SkillBundle(
            name="research",
            version="1.0.0",
            description="",
            skills=["core/retrieval", "research/web_search"],
        )
        manager._bundles["research"] = bundle

        skills = manager.get_bundle_skills("research")

        assert len(skills) == 2
        assert "core/retrieval" in skills

    def test_validate_dependencies_satisfied(self, manager):
        """Test validating satisfied dependencies."""
        metadata = SkillMetadata(
            name="test",
            version="1.0.0",
            description="",
            dependencies=["pytest>=7.0.0"],  # pytest is installed in test env
        )
        manager.register_skill("test", metadata)

        satisfied, missing = manager.validate_dependencies("test")

        assert satisfied
        assert len(missing) == 0

    def test_validate_dependencies_missing(self, manager):
        """Test validating missing dependencies."""
        metadata = SkillMetadata(
            name="test",
            version="1.0.0",
            description="",
            dependencies=["nonexistent-package>=1.0.0"],
        )
        manager.register_skill("test", metadata)

        satisfied, missing = manager.validate_dependencies("test")

        assert not satisfied
        assert len(missing) > 0

    def test_validate_dependencies_skill_not_found(self, manager):
        """Test validating dependencies for non-existent skill."""
        satisfied, missing = manager.validate_dependencies("nonexistent")

        assert not satisfied
        assert "Skill not found" in missing[0]

    def test_create_bundle(self, manager):
        """Test creating a bundle dynamically."""
        bundle = manager.create_bundle(
            name="custom",
            skills=["core/retrieval", "research/web_search"],
            context_budget=6000,
            description="Custom bundle",
            auto_activate=["retrieval"],
        )

        assert bundle.name == "custom"
        assert bundle.context_budget == 6000
        assert "custom" in manager._bundles

    def test_get_metrics(self, manager):
        """Test getting manager metrics."""
        manager._libraries["core"] = SkillLibrary(
            name="core",
            version="1.0.0",
            description="",
            skills=["retrieval"],
        )
        manager._bundles["research"] = SkillBundle(
            name="research",
            version="1.0.0",
            description="",
            skills=[],
        )
        manager.register_skill(
            "test",
            SkillMetadata(name="test", version="1.0.0", description=""),
        )

        metrics = manager.get_metrics()

        assert metrics["libraries"] == 1
        assert metrics["bundles"] == 1
        assert metrics["registered_skills"] == 1

    def test_discover_libraries_creates_library_from_yaml(self, tmp_path, mock_lifecycle):
        """Test discovering library from YAML."""
        lib_dir = tmp_path / "research"
        lib_dir.mkdir()

        lib_yaml = lib_dir / "LIBRARY.yaml"
        lib_yaml.write_text(
            yaml.dump(
                {
                    "name": "research",
                    "version": "1.0.0",
                    "description": "Research skills",
                    "skills": ["web_search"],
                }
            )
        )

        manager = SkillLibraryManager(
            libraries_dir=tmp_path,
            skill_manager=mock_lifecycle,
        )
        libraries = manager.discover_libraries()

        assert "research" in libraries
        assert libraries["research"].version == "1.0.0"

    def test_discover_libraries_infers_from_structure(self, tmp_path, mock_lifecycle):
        """Test discovering library by inferring from directory structure."""
        lib_dir = tmp_path / "research"
        lib_dir.mkdir()

        skill_dir = lib_dir / "web_search"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Web Search")

        manager = SkillLibraryManager(
            libraries_dir=tmp_path,
            skill_manager=mock_lifecycle,
        )
        libraries = manager.discover_libraries()

        assert "research" in libraries
        assert "web_search" in libraries["research"].skills

    def test_discover_bundles_from_yaml(self, tmp_path, mock_lifecycle):
        """Test discovering bundles from YAML."""
        bundles_dir = tmp_path / "bundles"
        bundles_dir.mkdir()

        bundle_dir = bundles_dir / "research"
        bundle_dir.mkdir()

        bundle_yaml = bundle_dir / "BUNDLE.yaml"
        bundle_yaml.write_text(
            yaml.dump(
                {
                    "name": "research",
                    "version": "1.0.0",
                    "description": "Research bundle",
                    "skills": ["core/retrieval"],
                    "context_budget": 5000,
                }
            )
        )

        manager = SkillLibraryManager(
            libraries_dir=tmp_path,
            skill_manager=mock_lifecycle,
        )
        manager.discover_libraries()

        assert "research" in manager._bundles
        assert manager._bundles["research"].context_budget == 5000

    def test_discover_bundles_from_json(self, tmp_path, mock_lifecycle):
        """Test discovering bundles from JSON."""
        bundles_dir = tmp_path / "bundles"
        bundles_dir.mkdir()

        bundle_dir = bundles_dir / "research"
        bundle_dir.mkdir()

        bundle_json = bundle_dir / "BUNDLE.json"
        bundle_json.write_text(
            json.dumps(
                {
                    "name": "research",
                    "version": "1.0.0",
                    "description": "Research bundle",
                    "skills": ["core/retrieval"],
                    "context_budget": 5000,
                }
            )
        )

        manager = SkillLibraryManager(
            libraries_dir=tmp_path,
            skill_manager=mock_lifecycle,
        )
        manager.discover_libraries()

        assert "research" in manager._bundles

    def test_resolve_skill_path_with_library(self, manager):
        """Test resolving library/skill path."""
        result = manager._resolve_skill_path("core/retrieval")

        assert result == "retrieval"

    def test_resolve_skill_path_without_library(self, manager):
        """Test resolving skill-only path."""
        result = manager._resolve_skill_path("retrieval")

        assert result == "retrieval"

    @pytest.mark.asyncio
    async def test_install_bundle_alias(self, manager, mock_lifecycle):
        """Test that install_bundle is an alias for load_bundle."""
        bundle = SkillBundle(
            name="research",
            version="1.0.0",
            description="",
            skills=["core/retrieval"],
        )
        manager._bundles["research"] = bundle

        loaded = await manager.install_bundle("research")

        assert "retrieval" in loaded
        assert mock_lifecycle.load.called
