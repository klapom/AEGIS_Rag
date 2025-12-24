"""Integration tests for domain persistence and transaction handling (Sprint 64.2).

These tests validate that:
1. Domains are created transactionally in Neo4j
2. No orphaned domains exist on validation failures
3. Domains are properly rolled back on training failures
4. Domain state is consistent across retries
5. Training metrics are correctly persisted
"""

import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from neo4j import AsyncGraphDatabase

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class TestDomainPersistence:
    """Test domain creation and persistence in Neo4j."""

    @pytest.fixture(scope="class")
    async def neo4j_driver(self):
        """Get Neo4j driver for validation."""
        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value()),
        )
        yield driver
        await driver.close()

    @pytest.fixture
    async def cleanup_domains(self, neo4j_driver):
        """Cleanup test domains after each test."""
        yield
        # Cleanup
        async with neo4j_driver.session() as session:
            await session.run(
                "MATCH (d:Domain) WHERE d.name STARTS WITH 'test_' DETACH DELETE d"
            )

    @staticmethod
    def create_test_dataset(num_samples: int) -> str:
        """Create JSONL training dataset."""
        samples = []
        for i in range(num_samples):
            sample = {
                "text": f"Training sample {i}",
                "entities": [{"text": f"Entity_{i}", "type": "CONCEPT"}],
                "relations": [
                    {
                        "head": f"Entity_{i}",
                        "relation": "DESCRIBES",
                        "tail": "concept",
                    }
                ],
            }
            samples.append(sample)

        temp_file = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".jsonl",
            delete=False,
        )

        for sample in samples:
            temp_file.write(json.dumps(sample) + "\n")

        temp_file.close()
        return temp_file.name

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_domain_not_created_on_validation_failure(
        self,
        neo4j_driver,
        cleanup_domains,
    ):
        """Verify domain is NOT created when validation fails.

        Scenario:
        - Attempt to train domain with < 5 samples
        - Training API should reject with 422
        - Domain should not exist in Neo4j
        """
        domain_name = "test_validation_failure"

        try:
            # Import the training service
            from src.domains.domain_training.domain_training_service import (
                DomainTrainingService,
            )

            service = DomainTrainingService()

            # Attempt to train with invalid samples
            invalid_dataset = self.create_test_dataset(2)

            with pytest.raises(ValueError) as exc_info:
                await service.train_domain(
                    domain_name=domain_name,
                    description="Test",
                    dataset_path=invalid_dataset,
                )

            assert "minimum" in str(exc_info.value).lower()

            logger.info(f"Validation error raised: {exc_info.value}")

            # Verify domain does NOT exist in Neo4j
            async with neo4j_driver.session() as session:
                result = await session.run(
                    "MATCH (d:Domain {name: $name}) RETURN d",
                    name=domain_name,
                )

                record = await result.single()
                assert record is None, f"Orphaned domain found: {domain_name}"

            logger.info("Test passed: No orphaned domain created")

        except ImportError:
            logger.warning("Domain training service not yet implemented, skipping test")
            pytest.skip("Domain training service not available")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_domain_created_on_successful_training(
        self,
        neo4j_driver,
        cleanup_domains,
    ):
        """Verify domain is created only after successful training.

        Scenario:
        - Train domain with valid samples
        - Verify domain exists in Neo4j
        - Verify metrics are persisted
        """
        domain_name = "test_successful_training"

        from src.domains.domain_training.domain_training_service import (
            DomainTrainingService,
        )

        service = DomainTrainingService()

        # Train with valid samples
        valid_dataset = self.create_test_dataset(8)

        result = await service.train_domain(
            domain_name=domain_name,
            description="Test successful training",
            dataset_path=valid_dataset,
        )

        logger.info(f"Training result: {result}")

        # Verify domain exists in Neo4j
        async with neo4j_driver.session() as session:
            query_result = await session.run(
                "MATCH (d:Domain {name: $name}) RETURN d.f1_score as f1, d.precision as precision, d.recall as recall",
                name=domain_name,
            )

            record = await query_result.single()
            assert record is not None, f"Domain not found: {domain_name}"

            f1_score = record["f1"]
            precision = record["precision"]
            recall = record["recall"]

            logger.info(f"Domain metrics - F1: {f1_score}, Precision: {precision}, Recall: {recall}")

            # Verify realistic metrics
            assert 0.0 <= f1_score <= 1.0, f"Invalid F1 score: {f1_score}"
            assert 0.0 <= precision <= 1.0, f"Invalid precision: {precision}"
            assert 0.0 <= recall <= 1.0, f"Invalid recall: {recall}"

        logger.info("Test passed: Domain created successfully")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_domain_rollback_on_training_exception(
        self,
        neo4j_driver,
        cleanup_domains,
    ):
        """Verify domain is rolled back if training fails after creation.

        Scenario:
        - Domain created in Neo4j (transactional)
        - DSPy training fails with exception
        - Domain should be rolled back
        """
        domain_name = "test_training_exception_rollback"

        from src.domains.domain_training.domain_training_service import (
            DomainTrainingService,
        )

        service = DomainTrainingService()
        valid_dataset = self.create_test_dataset(8)

        # Mock DSPy trainer to raise exception
        with patch(
            "src.domains.domain_training.domain_training_service.DSPyTrainer"
        ) as mock_trainer:
            mock_instance = AsyncMock()
            mock_instance.train.side_effect = RuntimeError("DSPy training failed")
            mock_trainer.return_value = mock_instance

            # Attempt to train
            with pytest.raises(RuntimeError) as exc_info:
                await service.train_domain(
                    domain_name=domain_name,
                    description="Test exception handling",
                    dataset_path=valid_dataset,
                )

            logger.info(f"Training exception caught: {exc_info.value}")

            # Verify domain was rolled back
            async with neo4j_driver.session() as session:
                result = await session.run(
                    "MATCH (d:Domain {name: $name}) RETURN d",
                    name=domain_name,
                )

                record = await result.single()
                assert record is None, f"Domain not rolled back: {domain_name}"

        logger.info("Test passed: Domain rolled back on exception")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_domain_unique_constraint(
        self,
        neo4j_driver,
        cleanup_domains,
    ):
        """Verify domain name uniqueness constraint.

        Scenario:
        - Create domain with name "test_unique"
        - Attempt to create another domain with same name
        - Should fail with constraint violation
        """
        domain_name = "test_unique_constraint"

        from src.domains.domain_training.domain_training_service import (
            DomainTrainingService,
        )

        service = DomainTrainingService()
        valid_dataset = self.create_test_dataset(8)

        # Create first domain
        result1 = await service.train_domain(
            domain_name=domain_name,
            description="First domain",
            dataset_path=valid_dataset,
        )

        logger.info("First domain created")

        # Attempt to create domain with same name
        with pytest.raises(Exception) as exc_info:  # Should be constraint error
            result2 = await service.train_domain(
                domain_name=domain_name,
                description="Duplicate domain",
                dataset_path=valid_dataset,
            )

        logger.info(f"Duplicate creation rejected: {exc_info.value}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_domain_metrics_persistence(
        self,
        neo4j_driver,
        cleanup_domains,
    ):
        """Verify all training metrics are correctly persisted.

        Metrics to verify:
        - F1 score (0.0-1.0, not exactly 0.850)
        - Precision (0.0-1.0)
        - Recall (0.0-1.0)
        - Training samples count
        - Training timestamp
        - Model version
        """
        domain_name = "test_metrics_persistence"

        from src.domains.domain_training.domain_training_service import (
            DomainTrainingService,
        )

        service = DomainTrainingService()
        valid_dataset = self.create_test_dataset(10)

        # Train domain
        result = await service.train_domain(
            domain_name=domain_name,
            description="Test metrics persistence",
            dataset_path=valid_dataset,
        )

        logger.info(f"Training completed: {result}")

        # Verify metrics in Neo4j
        async with neo4j_driver.session() as session:
            query_result = await session.run(
                """
                MATCH (d:Domain {name: $name})
                RETURN
                  d.f1_score as f1,
                  d.precision as precision,
                  d.recall as recall,
                  d.sample_count as sample_count,
                  d.training_timestamp as training_timestamp,
                  d.model_version as model_version
                """,
                name=domain_name,
            )

            record = await query_result.single()
            assert record is not None

            f1 = record["f1"]
            precision = record["precision"]
            recall = record["recall"]
            sample_count = record["sample_count"]
            training_timestamp = record["training_timestamp"]
            model_version = record["model_version"]

            logger.info(f"F1: {f1}")
            logger.info(f"Precision: {precision}")
            logger.info(f"Recall: {recall}")
            logger.info(f"Sample count: {sample_count}")
            logger.info(f"Training timestamp: {training_timestamp}")
            logger.info(f"Model version: {model_version}")

            # Validate metrics
            assert isinstance(f1, (int, float)), "F1 should be numeric"
            assert 0.0 <= f1 <= 1.0, f"F1 out of range: {f1}"
            assert f1 != 0.850, "F1 should not be mock value (0.850)"

            assert isinstance(precision, (int, float)), "Precision should be numeric"
            assert 0.0 <= precision <= 1.0, f"Precision out of range: {precision}"

            assert isinstance(recall, (int, float)), "Recall should be numeric"
            assert 0.0 <= recall <= 1.0, f"Recall out of range: {recall}"

            assert sample_count == 10, f"Sample count should be 10, got {sample_count}"
            assert training_timestamp is not None, "Training timestamp should be set"
            assert model_version is not None, "Model version should be set"

        logger.info("Test passed: All metrics persisted correctly")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_domain_can_be_updated(
        self,
        neo4j_driver,
        cleanup_domains,
    ):
        """Verify domains can be retrained with new samples.

        Scenario:
        - Train domain version 1
        - Retrain domain with different samples
        - Verify metrics are updated
        - Verify version incremented
        """
        domain_name = "test_domain_update"

        from src.domains.domain_training.domain_training_service import (
            DomainTrainingService,
        )

        service = DomainTrainingService()

        # First training
        dataset_v1 = self.create_test_dataset(8)

        result_v1 = await service.train_domain(
            domain_name=domain_name,
            description="Version 1",
            dataset_path=dataset_v1,
        )

        async with neo4j_driver.session() as session:
            v1_result = await session.run(
                "MATCH (d:Domain {name: $name}) RETURN d.f1_score as f1, d.model_version as version",
                name=domain_name,
            )

            v1_record = await v1_result.single()
            v1_f1 = v1_record["f1"]
            v1_version = v1_record["version"]

            logger.info(f"V1 - F1: {v1_f1}, Version: {v1_version}")

        # Second training (update)
        dataset_v2 = self.create_test_dataset(12)

        result_v2 = await service.train_domain(
            domain_name=domain_name,
            description="Version 2",
            dataset_path=dataset_v2,
        )

        async with neo4j_driver.session() as session:
            v2_result = await session.run(
                "MATCH (d:Domain {name: $name}) RETURN d.f1_score as f1, d.model_version as version",
                name=domain_name,
            )

            v2_record = await v2_result.single()
            v2_f1 = v2_record["f1"]
            v2_version = v2_record["version"]

            logger.info(f"V2 - F1: {v2_f1}, Version: {v2_version}")

            # Verify version incremented
            assert v2_version > v1_version, "Version should increment"

        logger.info("Test passed: Domain successfully updated")
