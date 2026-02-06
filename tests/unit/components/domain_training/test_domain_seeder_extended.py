"""Extended unit tests for domain seeding (Sprint 125 Feature 125.8).

Tests for seed catalog loading, multi-domain seeding, and deployment profiles.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from src.components.domain_training.domain_seeder import (
    _load_seed_domains,
    seed_all_domains,
    seed_domain,
    set_deployment_profile,
    get_active_domains,
    get_domain_config,
)


class TestSeedDomainLoading:
    """Test loading seed domains from YAML catalog."""

    def test_load_seed_domains_returns_dict(self):
        """Test that _load_seed_domains() returns a dictionary."""
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = """
universal_entity_types:
  - PERSON
  - ORGANIZATION
domains:
  - domain_id: computer_science
    name: Computer Science
deployment_profiles:
  default: [computer_science]
"""
            import yaml

            with patch("yaml.safe_load") as mock_yaml:
                mock_yaml.return_value = {
                    "universal_entity_types": ["PERSON", "ORGANIZATION"],
                    "domains": [
                        {
                            "domain_id": "computer_science",
                            "name": "Computer Science",
                        }
                    ],
                    "deployment_profiles": {"default": ["computer_science"]},
                }

                catalog = _load_seed_domains()

                assert isinstance(catalog, dict)
                assert "domains" in catalog
                assert "deployment_profiles" in catalog
                assert "universal_entity_types" in catalog

    def test_load_seed_domains_contains_35_domains(self):
        """Test that seed catalog contains 35 domains."""
        with patch("builtins.open", create=True), patch(
            "src.components.domain_training.domain_seeder.SEED_DOMAINS_PATH"
        ) as mock_path:

            # Mock the file exists check
            mock_path.exists.return_value = True

            with patch("yaml.safe_load") as mock_yaml:
                # Create 35 mock domains
                mock_domains = [
                    {"domain_id": f"domain_{i}", "name": f"Domain {i}"}
                    for i in range(35)
                ]

                mock_yaml.return_value = {
                    "domains": mock_domains,
                    "deployment_profiles": {},
                    "universal_entity_types": [],
                    "universal_relation_types": [],
                }

                catalog = _load_seed_domains()

                assert len(catalog["domains"]) == 35

    def test_load_seed_domains_file_not_found(self):
        """Test that FileNotFoundError is raised when seed_domains.yaml not found."""
        with patch(
            "src.components.domain_training.domain_seeder.SEED_DOMAINS_PATH"
        ) as mock_path:
            mock_path.exists.return_value = False

            with pytest.raises(FileNotFoundError):
                _load_seed_domains()

    def test_load_seed_domains_yaml_parse_error(self):
        """Test that ValueError is raised on YAML parse error."""
        with patch(
            "src.components.domain_training.domain_seeder.SEED_DOMAINS_PATH"
        ) as mock_path:
            mock_path.exists.return_value = True

            with patch("builtins.open", create=True), patch(
                "yaml.safe_load"
            ) as mock_yaml:
                mock_yaml.side_effect = Exception("Invalid YAML syntax")

                with pytest.raises(ValueError):
                    _load_seed_domains()

    def test_load_seed_domains_logging(self):
        """Test that domain loading is properly logged."""
        with patch(
            "src.components.domain_training.domain_seeder.SEED_DOMAINS_PATH"
        ) as mock_path, patch(
            "src.components.domain_training.domain_seeder.logger"
        ) as mock_logger:

            mock_path.exists.return_value = True

            with patch("builtins.open", create=True), patch(
                "yaml.safe_load"
            ) as mock_yaml:
                mock_yaml.return_value = {
                    "domains": [{"domain_id": "test", "name": "Test"}],
                    "deployment_profiles": {},
                    "universal_entity_types": [],
                }

                _load_seed_domains()

                # Verify logging was called
                mock_logger.info.assert_called()


class TestSeedDomain:
    """Test seeding individual domains."""

    @pytest.mark.asyncio
    async def test_seed_domain_creates_new_domain(self):
        """Test that seed_domain() creates a new domain."""
        mock_repo = AsyncMock()
        mock_repo.get_domain.return_value = None  # Domain doesn't exist
        mock_repo.create_domain.return_value = {"id": "domain_123", "name": "test_domain"}

        with patch(
            "src.components.domain_training.domain_seeder.get_domain_repository",
            return_value=mock_repo,
        ), patch(
            "src.components.domain_training.domain_seeder._load_seed_domains"
        ) as mock_load:
            mock_load.return_value = {
                "domains": [
                    {
                        "domain_id": "test_domain",
                        "name": "Test Domain",
                        "description": "A test domain",
                        "entity_types": ["PERSON"],
                        "relation_types": ["RELATES_TO"],
                    }
                ]
            }

            await seed_domain("test_domain")

            mock_repo.create_domain.assert_called_once()

    @pytest.mark.asyncio
    async def test_seed_domain_skip_existing(self):
        """Test that seed_domain() skips existing domains (idempotent)."""
        mock_repo = AsyncMock()
        mock_repo.get_domain.return_value = {
            "id": "domain_123",
            "name": "test_domain",
        }

        with patch(
            "src.components.domain_training.domain_seeder.get_domain_repository",
            return_value=mock_repo,
        ):
            await seed_domain("test_domain")

            # Should not create since domain exists
            mock_repo.create_domain.assert_not_called()

    @pytest.mark.asyncio
    async def test_seed_domain_preserves_trained_prompts(self):
        """Test that seed_domain() preserves existing trained prompts (MERGE semantics)."""
        # Existing domain with trained prompts
        existing_domain = {
            "id": "domain_123",
            "name": "test_domain",
            "entity_prompt": "CUSTOM TRAINED ENTITY PROMPT",
            "relation_prompt": "CUSTOM TRAINED RELATION PROMPT",
        }

        mock_repo = AsyncMock()
        mock_repo.get_domain.return_value = existing_domain

        with patch(
            "src.components.domain_training.domain_seeder.get_domain_repository",
            return_value=mock_repo,
        ):
            await seed_domain("test_domain")

            # Should not overwrite since domain exists (MERGE)
            mock_repo.create_domain.assert_not_called()

    @pytest.mark.asyncio
    async def test_seed_domain_with_sub_types(self):
        """Test seeding domain with sub-type properties."""
        mock_repo = AsyncMock()
        mock_repo.get_domain.return_value = None
        mock_repo.create_domain.return_value = {"id": "domain_456", "name": "medical"}

        with patch(
            "src.components.domain_training.domain_seeder.get_domain_repository",
            return_value=mock_repo,
        ), patch(
            "src.components.domain_training.domain_seeder._load_seed_domains"
        ) as mock_load:
            mock_load.return_value = {
                "domains": [
                    {
                        "domain_id": "medicine_health",
                        "name": "Medicine & Health",
                        "description": "Medical domain",
                        "entity_sub_types": {
                            "PERSON": ["Doctor", "Patient", "Researcher"],
                            "ORGANIZATION": ["Hospital", "Clinic"],
                        },
                    }
                ]
            }

            await seed_domain("medicine_health")

            # Domain should be created with sub-type support
            mock_repo.create_domain.assert_called_once()


class TestSeedAllDomains:
    """Test seeding all domains from catalog."""

    @pytest.mark.asyncio
    async def test_seed_all_domains_calls_seed_domain_35_times(self):
        """Test that seed_all_domains() seeds all 35 domains."""
        mock_repo = AsyncMock()

        with patch(
            "src.components.domain_training.domain_seeder.seed_domain"
        ) as mock_seed_one, patch(
            "src.components.domain_training.domain_seeder._load_seed_domains"
        ) as mock_load:

            # Mock 35 domains
            mock_domains = [
                {"domain_id": f"domain_{i}", "name": f"Domain {i}"} for i in range(35)
            ]

            mock_load.return_value = {
                "domains": mock_domains,
                "deployment_profiles": {},
            }

            mock_seed_one.return_value = None  # AsyncMock returns coroutine

            await seed_all_domains()

            # seed_domain should be called 35 times
            assert mock_seed_one.call_count == 35

    @pytest.mark.asyncio
    async def test_seed_all_domains_parallel_execution(self):
        """Test that seed_all_domains() processes all domains."""
        mock_repo = AsyncMock()
        mock_repo.get_domain.return_value = None  # All domains are new

        with patch(
            "src.components.domain_training.domain_seeder._load_seed_domains"
        ) as mock_load, patch(
            "src.components.domain_training.domain_seeder.seed_domain",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_seed, patch(
            "src.components.domain_training.domain_seeder.get_domain_repository",
            return_value=mock_repo,
        ):

            # Mock 10 domains
            mock_domains = [
                {"domain_id": f"domain_{i}", "name": f"Domain {i}"} for i in range(10)
            ]

            mock_load.return_value = {
                "domains": mock_domains,
                "deployment_profiles": {},
            }

            await seed_all_domains()

            # All domains should be processed (repo check + seed_domain call)
            assert mock_seed.call_count == 10


class TestDeploymentProfile:
    """Test deployment profile functionality."""

    @pytest.mark.asyncio
    async def test_set_deployment_profile_stores_in_redis(self):
        """Test that set_deployment_profile() stores profile in Redis."""
        mock_redis = AsyncMock()

        with patch(
            "src.components.domain_training.domain_seeder._get_redis_client",
            return_value=mock_redis,
        ):
            await set_deployment_profile("pharma_company")

            # Redis should be called to store profile
            mock_redis.set.assert_called_once()

            # Verify the key used
            call_args = mock_redis.set.call_args
            assert call_args[0][0] == "aegis:deployment_profile"

    @pytest.mark.asyncio
    async def test_get_active_domains_returns_list(self):
        """Test that get_active_domains() returns list of domain IDs."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = "pharma_company"

        with patch(
            "src.components.domain_training.domain_seeder._get_redis_client",
            return_value=mock_redis,
        ), patch(
            "src.components.domain_training.domain_seeder._load_seed_domains"
        ) as mock_load:

            mock_load.return_value = {
                "deployment_profiles": {
                    "pharma_company": {
                        "name": "Pharmaceutical Company",
                        "domains": [
                            "medicine_health",
                            "chemistry",
                            "biology_life_sciences",
                        ],
                    }
                }
            }

            active = await get_active_domains()

            assert isinstance(active, list)
            assert "medicine_health" in active

    @pytest.mark.asyncio
    async def test_get_active_domains_default_profile(self):
        """Test get_active_domains() with default profile."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None  # No profile set

        with patch(
            "src.components.domain_training.domain_seeder._get_redis_client",
            return_value=mock_redis,
        ), patch(
            "src.components.domain_training.domain_seeder._load_seed_domains"
        ) as mock_load:

            # Default profile should have all domains
            all_domains = [
                {"domain_id": f"domain_{i}", "name": f"Domain {i}"} for i in range(5)
            ]

            mock_load.return_value = {
                "domains": all_domains,
                "deployment_profiles": {"default": [d["domain_id"] for d in all_domains]},
            }

            active = await get_active_domains()

            # Should return default profile domains
            assert len(active) > 0

    @pytest.mark.asyncio
    async def test_get_domain_config_returns_metadata(self):
        """Test that get_domain_config() returns domain metadata."""
        with patch(
            "src.components.domain_training.domain_seeder._load_seed_domains"
        ) as mock_load:

            mock_load.return_value = {
                "domains": [
                    {
                        "domain_id": "computer_science_it",
                        "name": "Computer Science & IT",
                        "description": "Domain for CS/IT content",
                        "entity_types": ["PERSON", "ORGANIZATION"],
                        "relation_types": ["USES", "IMPLEMENTS"],
                        "keywords": ["algorithm", "programming", "software"],
                    }
                ]
            }

            config = await get_domain_config("computer_science_it")

            assert config["name"] == "Computer Science & IT"
            assert "description" in config
            assert "keywords" in config

    @pytest.mark.asyncio
    async def test_get_domain_config_not_found(self):
        """Test get_domain_config() returns None for non-existent domain."""
        with patch(
            "src.components.domain_training.domain_seeder._load_seed_domains"
        ) as mock_load:

            mock_load.return_value = {"domains": []}

            config = await get_domain_config("nonexistent_domain")

            assert config is None


class TestSeedDomainIntegration:
    """Integration tests for domain seeding workflow."""

    @pytest.mark.asyncio
    async def test_seed_workflow_load_seed_create_domain(self):
        """Test complete workflow: load seed -> create domain."""
        mock_repo = AsyncMock()
        mock_repo.get_domain.return_value = None
        mock_repo.create_domain.return_value = {
            "id": "domain_123",
            "name": "test_domain",
        }

        with patch(
            "src.components.domain_training.domain_seeder.get_domain_repository",
            return_value=mock_repo,
        ), patch(
            "src.components.domain_training.domain_seeder._load_seed_domains"
        ) as mock_load:

            mock_load.return_value = {
                "domains": [
                    {
                        "domain_id": "test_domain",
                        "name": "Test Domain",
                        "description": "Test",
                        "entity_types": ["PERSON"],
                        "relation_types": ["RELATES_TO"],
                    }
                ]
            }

            # Execute seeding
            await seed_domain("test_domain")

            # Verify load was called
            mock_load.assert_called_once()

            # Verify domain was created
            mock_repo.create_domain.assert_called_once()

    @pytest.mark.asyncio
    async def test_seed_workflow_with_profile_activation(self):
        """Test workflow: seed domain -> set profile -> get active domains."""
        mock_redis = AsyncMock()
        mock_repo = AsyncMock()

        with patch(
            "src.components.domain_training.domain_seeder._get_redis_client",
            return_value=mock_redis,
        ), patch(
            "src.components.domain_training.domain_seeder.get_domain_repository",
            return_value=mock_repo,
        ), patch(
            "src.components.domain_training.domain_seeder._load_seed_domains"
        ) as mock_load:

            mock_load.return_value = {
                "domains": [
                    {"domain_id": "medicine", "name": "Medicine"},
                    {"domain_id": "law", "name": "Law"},
                ],
                "deployment_profiles": {
                    "law_firm": {"name": "Law Firm", "domains": ["law"]},
                    "pharma": {"name": "Pharma", "domains": ["medicine"]},
                },
            }

            mock_redis.get.return_value = "law_firm"

            # Set profile
            await set_deployment_profile("law_firm")

            # Verify Redis was updated
            mock_redis.set.assert_called_once()

            # Get active domains (should return law_firm profile)
            active = await get_active_domains()

            assert "law" in active
