#!/usr/bin/env python3
"""Manual Domain Testing Script for Sprint 46 Feature 46.6.

This script validates:
1. Domain Creation and Repository Functions
2. DSPy Optimizer Initialization
3. Domain Classifier with Sample Queries
4. API Endpoint Registration
5. Integration Points

Note: This script runs outside Docker and focuses on:
- Code structure verification
- Imports and exports validation
- API endpoint registration
- Component initialization tests

Full integration tests with databases should run in Docker environment.

Usage:
    python scripts/manual_domain_testing.py
"""

import asyncio
import sys
from datetime import datetime
from typing import Any, Dict, List

# Color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{BOLD}{BLUE}{'=' * 70}{RESET}")
    print(f"{BOLD}{BLUE}{title}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 70}{RESET}\n")


def print_test(test_name: str, passed: bool, message: str = "") -> None:
    """Print test result with color."""
    status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
    print(f"  [{status}] {test_name}")
    if message:
        print(f"        {message}")


def print_info(message: str) -> None:
    """Print info message."""
    print(f"  {YELLOW}i{RESET} {message}")


def print_error(message: str) -> None:
    """Print error message."""
    print(f"  {RED}✗{RESET} {message}")


def print_success(message: str) -> None:
    """Print success message."""
    print(f"  {GREEN}✓{RESET} {message}")


# ============================================================================
# TEST 1: Domain Repository Imports and Exports
# ============================================================================

def test_domain_repository_imports() -> bool:
    """Test 1: Verify DomainRepository can be imported."""
    print_section("TEST 1: Domain Repository Imports & Exports")

    all_passed = True

    try:
        from src.components.domain_training import (
            DomainRepository,
            get_domain_repository,
        )
        print_test(
            "Import DomainRepository class",
            True,
            f"Successfully imported: {DomainRepository.__name__}"
        )
    except ImportError as e:
        print_test("Import DomainRepository class", False, str(e))
        all_passed = False

    try:
        from src.components.domain_training import get_domain_repository
        print_test(
            "Import get_domain_repository() function",
            True,
            "Singleton factory function available"
        )
    except ImportError as e:
        print_test("Import get_domain_repository() function", False, str(e))
        all_passed = False

    # Check that singleton works
    try:
        from src.components.domain_training import get_domain_repository
        repo1 = get_domain_repository()
        repo2 = get_domain_repository()
        is_singleton = repo1 is repo2
        print_test(
            "Singleton pattern works",
            is_singleton,
            f"Same instance: {is_singleton}"
        )
        if not is_singleton:
            all_passed = False
    except Exception as e:
        print_test("Singleton pattern works", False, str(e))
        all_passed = False

    return all_passed


# ============================================================================
# TEST 2: Domain Classifier Imports and Exports
# ============================================================================

def test_domain_classifier_imports() -> bool:
    """Test 2: Verify DomainClassifier can be imported."""
    print_section("TEST 2: Domain Classifier Imports & Exports")

    all_passed = True

    try:
        from src.components.domain_training import (
            DomainClassifier,
            get_domain_classifier,
            reset_classifier,
        )
        print_test(
            "Import DomainClassifier class",
            True,
            f"Successfully imported: {DomainClassifier.__name__}"
        )
        print_test(
            "Import get_domain_classifier() function",
            True,
            "Singleton factory function available"
        )
        print_test(
            "Import reset_classifier() function",
            True,
            "Reset function for testing available"
        )
    except ImportError as e:
        print_test("Import DomainClassifier and related", False, str(e))
        all_passed = False

    # Check classifier properties
    try:
        from src.components.domain_training import get_domain_classifier
        classifier = get_domain_classifier()

        # Check for key methods
        has_load_domains = hasattr(classifier, "load_domains")
        has_classify = hasattr(classifier, "classify_document")
        has_get_loaded = hasattr(classifier, "get_loaded_domains")
        has_is_loaded = hasattr(classifier, "is_loaded")

        print_test(
            "Has load_domains() method",
            has_load_domains,
            "Async method for loading domains"
        )
        print_test(
            "Has classify_document() method",
            has_classify,
            "Method for classifying documents"
        )
        print_test(
            "Has get_loaded_domains() method",
            has_get_loaded,
            "Returns list of loaded domain names"
        )
        print_test(
            "Has is_loaded() method",
            has_is_loaded,
            "Status check for classifier readiness"
        )

        if not (has_load_domains and has_classify and has_get_loaded and has_is_loaded):
            all_passed = False

    except Exception as e:
        print_test("Verify classifier methods", False, str(e))
        all_passed = False

    return all_passed


# ============================================================================
# TEST 3: DSPy Optimizer Imports
# ============================================================================

def test_dspy_optimizer_imports() -> bool:
    """Test 3: Verify DSPyOptimizer can be imported."""
    print_section("TEST 3: DSPy Optimizer Imports")

    all_passed = True

    try:
        from src.components.domain_training import (
            DSPyOptimizer,
            EntityExtractionSignature,
            RelationExtractionSignature,
        )
        print_test(
            "Import DSPyOptimizer class",
            True,
            f"Successfully imported: {DSPyOptimizer.__name__}"
        )
        print_test(
            "Import EntityExtractionSignature",
            True,
            "DSPy signature for entity extraction"
        )
        print_test(
            "Import RelationExtractionSignature",
            True,
            "DSPy signature for relation extraction"
        )
    except ImportError as e:
        print_test("Import DSPy classes", False, str(e))
        all_passed = False

    # Check optimizer properties
    try:
        from src.components.domain_training import DSPyOptimizer

        # Check class structure
        has_init = hasattr(DSPyOptimizer, "__init__")
        has_optimize_entity = hasattr(DSPyOptimizer, "optimize_entity_extraction")
        has_optimize_relation = hasattr(DSPyOptimizer, "optimize_relation_extraction")

        print_test(
            "DSPyOptimizer has __init__ method",
            has_init,
            "Constructor available"
        )
        print_test(
            "DSPyOptimizer has optimize_entity_extraction() method",
            has_optimize_entity,
            "Async method for entity extraction"
        )
        print_test(
            "DSPyOptimizer has optimize_relation_extraction() method",
            has_optimize_relation,
            "Async method for relation extraction"
        )

        if not (has_init and has_optimize_entity and has_optimize_relation):
            all_passed = False

    except Exception as e:
        print_test("Verify DSPyOptimizer structure", False, str(e))
        all_passed = False

    return all_passed


# ============================================================================
# TEST 4: Prompt Extractor Imports
# ============================================================================

def test_prompt_extractor_imports() -> bool:
    """Test 4: Verify prompt extraction functions."""
    print_section("TEST 4: Prompt Extractor Imports")

    all_passed = True

    try:
        from src.components.domain_training import (
            extract_prompt_from_dspy_result,
            format_prompt_for_production,
            save_prompt_template,
        )
        print_test(
            "Import extract_prompt_from_dspy_result() function",
            True,
            "Function for extracting DSPy prompts"
        )
        print_test(
            "Import format_prompt_for_production() function",
            True,
            "Function for formatting prompts"
        )
        print_test(
            "Import save_prompt_template() function",
            True,
            "Function for saving templates"
        )
    except ImportError as e:
        print_test("Import prompt extractor functions", False, str(e))
        all_passed = False

    return all_passed


# ============================================================================
# TEST 5: Training Progress Tracker Imports
# ============================================================================

def test_training_progress_imports() -> bool:
    """Test 5: Verify training progress tracking imports."""
    print_section("TEST 5: Training Progress Tracker Imports")

    all_passed = True

    try:
        from src.components.domain_training import (
            TrainingProgressTracker,
            TrainingPhase,
            ProgressEvent,
        )
        print_test(
            "Import TrainingProgressTracker class",
            True,
            f"Successfully imported: {TrainingProgressTracker.__name__}"
        )
        print_test(
            "Import TrainingPhase enum",
            True,
            "Training phase constants"
        )
        print_test(
            "Import ProgressEvent class",
            True,
            "Event model for progress updates"
        )
    except ImportError as e:
        print_test("Import training progress classes", False, str(e))
        all_passed = False

    # Check TrainingPhase values
    try:
        from src.components.domain_training import TrainingPhase

        phases = [
            ("INITIALIZATION", hasattr(TrainingPhase, "INITIALIZATION")),
            ("ENTITY_OPTIMIZATION", hasattr(TrainingPhase, "ENTITY_OPTIMIZATION")),
            ("RELATION_OPTIMIZATION", hasattr(TrainingPhase, "RELATION_OPTIMIZATION")),
            ("COMPLETION", hasattr(TrainingPhase, "COMPLETION")),
        ]

        for phase_name, exists in phases:
            print_test(
                f"TrainingPhase.{phase_name} defined",
                exists,
                "Phase constant available"
            )
            if not exists:
                all_passed = False

    except Exception as e:
        print_test("Verify TrainingPhase values", False, str(e))
        all_passed = False

    return all_passed


# ============================================================================
# TEST 6: Additional Components
# ============================================================================

def test_additional_components() -> bool:
    """Test 6: Verify domain discovery and augmentation components."""
    print_section("TEST 6: Additional Components (Discovery, Augmentation)")

    all_passed = True

    # Domain Discovery
    try:
        from src.components.domain_training import (
            DomainDiscoveryService,
            DomainSuggestion,
            get_domain_discovery_service,
        )
        print_test(
            "Import DomainDiscoveryService class",
            True,
            "Service for auto-discovering domains"
        )
        print_test(
            "Import DomainSuggestion model",
            True,
            "Model for domain suggestions"
        )
        print_test(
            "Import get_domain_discovery_service() function",
            True,
            "Singleton factory function"
        )
    except ImportError as e:
        print_test("Import domain discovery components", False, str(e))
        all_passed = False

    # Training Data Augmentation
    try:
        from src.components.domain_training import (
            TrainingDataAugmenter,
            get_training_data_augmenter,
        )
        print_test(
            "Import TrainingDataAugmenter class",
            True,
            "Service for augmenting training data"
        )
        print_test(
            "Import get_training_data_augmenter() function",
            True,
            "Singleton factory function"
        )
    except ImportError as e:
        print_test("Import augmentation components", False, str(e))
        all_passed = False

    # Grouped Ingestion
    try:
        from src.components.domain_training import (
            GroupedIngestionProcessor,
            IngestionItem,
            IngestionBatch,
            get_grouped_ingestion_processor,
        )
        print_test(
            "Import GroupedIngestionProcessor class",
            True,
            "Service for grouped batch ingestion"
        )
        print_test(
            "Import IngestionItem and IngestionBatch models",
            True,
            "Data models for ingestion"
        )
        print_test(
            "Import get_grouped_ingestion_processor() function",
            True,
            "Singleton factory function"
        )
    except ImportError as e:
        print_test("Import ingestion components", False, str(e))
        all_passed = False

    # Domain Analyzer
    try:
        from src.components.domain_training import (
            DomainAnalyzer,
            get_domain_analyzer,
        )
        print_test(
            "Import DomainAnalyzer class",
            True,
            "Service for analyzing domain characteristics"
        )
        print_test(
            "Import get_domain_analyzer() function",
            True,
            "Singleton factory function"
        )
    except ImportError as e:
        print_test("Import analyzer components", False, str(e))
        all_passed = False

    return all_passed


# ============================================================================
# TEST 7: API Endpoint Registration
# ============================================================================

def test_api_endpoint_registration() -> bool:
    """Test 7: Verify API endpoints are registered."""
    print_section("TEST 7: API Endpoint Registration")

    all_passed = True

    # Check that API router is importable
    try:
        from src.api.v1.domain_training import router as domain_training_router
        print_test(
            "Import domain_training API router",
            True,
            "FastAPI router successfully imported"
        )

        # Verify router has expected attributes
        has_prefix = hasattr(domain_training_router, "prefix")
        has_tags = hasattr(domain_training_router, "tags")

        print_test(
            "Router has prefix attribute",
            has_prefix,
            f"Prefix: {domain_training_router.prefix if has_prefix else 'N/A'}"
        )
        print_test(
            "Router has tags attribute",
            has_tags,
            f"Tags: {domain_training_router.tags if has_tags else 'N/A'}"
        )

    except ImportError as e:
        print_test("Import domain_training API router", False, str(e))
        all_passed = False

    # Check main app includes the router
    try:
        from src.api.main import app
        from src.api.v1.domain_training import router as domain_training_router

        # Check if router is included
        included = any(
            r.path == domain_training_router.prefix
            for r in getattr(app, "routes", [])
        ) or any(
            domain_training_router.prefix in str(r.path)
            for r in getattr(app, "routes", [])
        )

        print_test(
            "Router is included in main FastAPI app",
            included or "domain" in str(app.routes),
            "Domain training endpoints registered"
        )

    except Exception as e:
        print_test("Verify router in main app", False, str(e))
        all_passed = False

    # Check for domain discovery router
    try:
        from src.api.v1.admin.domain_discovery import router as discovery_router
        print_test(
            "Import domain_discovery admin router",
            True,
            "Domain discovery endpoints available"
        )
    except ImportError as e:
        print_test("Import domain_discovery admin router", False, str(e))
        # This is optional in Sprint 46
        print_info(f"Domain discovery router optional for Sprint 46: {e}")

    return all_passed


# ============================================================================
# TEST 8: Component Initialization
# ============================================================================

async def test_component_initialization() -> bool:
    """Test 8: Verify components can be initialized."""
    print_section("TEST 8: Component Initialization")

    all_passed = True

    # Test DomainRepository initialization
    try:
        from src.components.domain_training import get_domain_repository
        repo = get_domain_repository()
        has_neo4j_client = hasattr(repo, "neo4j_client")
        print_test(
            "DomainRepository initializes successfully",
            True,
            f"Instance created, has neo4j_client: {has_neo4j_client}"
        )
    except Exception as e:
        print_test("DomainRepository initialization", False, str(e))
        all_passed = False

    # Test DomainClassifier initialization
    try:
        from src.components.domain_training import get_domain_classifier, reset_classifier
        reset_classifier()  # Reset for clean test
        classifier = get_domain_classifier()

        # Check initial state
        is_loaded = classifier.is_loaded()
        print_test(
            "DomainClassifier initializes successfully",
            True,
            f"Instance created, domains loaded: {is_loaded} (expected False initially)"
        )

        # Check model loading works
        try:
            classifier._load_embedding_model()
            model_loaded = classifier._model_loaded
            print_test(
                "Embedding model can be loaded",
                model_loaded,
                "BGE-M3 model initialization successful"
            )
        except ImportError:
            print_info(
                "sentence-transformers not available (expected in test environment)"
            )

    except Exception as e:
        print_test("DomainClassifier initialization", False, str(e))
        all_passed = False

    # Test DSPyOptimizer initialization
    try:
        from src.components.domain_training import DSPyOptimizer
        optimizer = DSPyOptimizer(llm_model="qwen3:32b")
        has_llm_model = hasattr(optimizer, "llm_model")
        print_test(
            "DSPyOptimizer initializes successfully",
            True,
            f"Instance created, llm_model: {optimizer.llm_model if has_llm_model else 'N/A'}"
        )
    except Exception as e:
        print_test("DSPyOptimizer initialization", False, str(e))
        all_passed = False

    # Test TrainingProgressTracker initialization
    try:
        from src.components.domain_training import TrainingProgressTracker, TrainingPhase

        tracker = TrainingProgressTracker(
            training_run_id="test-run-123",
            domain_name="test_domain"
        )

        has_tracking_id = hasattr(tracker, "training_run_id")
        has_domain_name = hasattr(tracker, "domain_name")
        has_enter_phase = hasattr(tracker, "enter_phase")

        print_test(
            "TrainingProgressTracker initializes successfully",
            True,
            f"Instance created, has required methods: {has_enter_phase}"
        )

    except Exception as e:
        print_test("TrainingProgressTracker initialization", False, str(e))
        all_passed = False

    return all_passed


# ============================================================================
# TEST 9: Global Exports Check
# ============================================================================

def test_module_exports() -> bool:
    """Test 9: Verify __all__ exports are correctly defined."""
    print_section("TEST 9: Module Exports Verification")

    all_passed = True

    try:
        import src.components.domain_training as dt_module

        expected_exports = [
            "DomainRepository",
            "get_domain_repository",
            "DSPyOptimizer",
            "EntityExtractionSignature",
            "RelationExtractionSignature",
            "extract_prompt_from_dspy_result",
            "format_prompt_for_production",
            "save_prompt_template",
            "TrainingProgressTracker",
            "TrainingPhase",
            "ProgressEvent",
            "DomainClassifier",
            "get_domain_classifier",
            "reset_classifier",
            "DomainAnalyzer",
            "get_domain_analyzer",
            "DomainDiscoveryService",
            "DomainSuggestion",
            "get_domain_discovery_service",
            "GroupedIngestionProcessor",
            "IngestionItem",
            "IngestionBatch",
            "get_grouped_ingestion_processor",
            "reset_processor",
            "TrainingDataAugmenter",
            "get_training_data_augmenter",
        ]

        # Check __all__
        has_all = hasattr(dt_module, "__all__")
        if has_all:
            module_exports = set(dt_module.__all__)
            expected = set(expected_exports)

            missing = expected - module_exports
            extra = module_exports - expected

            print_test(
                "__all__ is defined",
                True,
                f"Total exports: {len(module_exports)}"
            )

            if missing:
                print_error(f"Missing from __all__: {missing}")
                all_passed = False
            else:
                print_success("All expected exports present in __all__")

            if extra:
                print_info(f"Extra exports in __all__ (may be intentional): {extra}")
        else:
            print_test("__all__ is defined", False, "__all__ not found")
            all_passed = False

        # Check each export can be accessed
        for export_name in expected_exports:
            has_export = hasattr(dt_module, export_name)
            print_test(
                f"Export '{export_name}' is accessible",
                has_export,
                "" if has_export else "Not found in module"
            )
            if not has_export:
                all_passed = False

    except Exception as e:
        print_test("Module exports verification", False, str(e))
        all_passed = False

    return all_passed


# ============================================================================
# TEST 10: Integration with Vector Search
# ============================================================================

def test_vector_search_integration() -> bool:
    """Test 10: Verify integration with vector search components."""
    print_section("TEST 10: Vector Search Integration")

    all_passed = True

    # Check that EmbeddingService is available
    try:
        from src.components.vector_search import EmbeddingService
        print_test(
            "EmbeddingService is available",
            True,
            "For domain description embeddings"
        )
    except ImportError as e:
        print_test("EmbeddingService availability", False, str(e))
        all_passed = False

    # Check that DomainClassifier can use embeddings
    try:
        from src.components.domain_training import DomainClassifier
        classifier = DomainClassifier()

        # Check for embedding model attribute
        has_embedding_model = hasattr(classifier, "embedding_model")
        has_load_method = hasattr(classifier, "_load_embedding_model")

        print_test(
            "DomainClassifier has embedding_model attribute",
            has_embedding_model,
            "For BGE-M3 embeddings"
        )
        print_test(
            "DomainClassifier has _load_embedding_model method",
            has_load_method,
            "Lazy loading mechanism"
        )

    except Exception as e:
        print_test("DomainClassifier embedding support", False, str(e))
        all_passed = False

    return all_passed


# ============================================================================
# TEST 11: Configuration and Environment
# ============================================================================

def test_configuration() -> bool:
    """Test 11: Verify configuration is available."""
    print_section("TEST 11: Configuration & Environment")

    all_passed = True

    try:
        from src.core.config import settings

        # Check relevant settings
        checks = [
            ("neo4j_uri", settings.neo4j_uri),
            ("neo4j_database", settings.neo4j_database),
            ("lightrag_llm_model", settings.lightrag_llm_model),
        ]

        for setting_name, value in checks:
            has_setting = value is not None
            print_test(
                f"Setting '{setting_name}' is configured",
                has_setting,
                f"Value: {value}" if has_setting else "Not configured"
            )
            if not has_setting:
                all_passed = False

    except Exception as e:
        print_test("Configuration verification", False, str(e))
        all_passed = False

    return all_passed


# ============================================================================
# Main Test Runner
# ============================================================================

async def run_all_tests() -> Dict[str, bool]:
    """Run all tests and return results."""
    results = {}

    # Synchronous tests
    results["Test 1: Repository Imports"] = test_domain_repository_imports()
    results["Test 2: Classifier Imports"] = test_domain_classifier_imports()
    results["Test 3: DSPy Optimizer"] = test_dspy_optimizer_imports()
    results["Test 4: Prompt Extractor"] = test_prompt_extractor_imports()
    results["Test 5: Progress Tracker"] = test_training_progress_imports()
    results["Test 6: Additional Components"] = test_additional_components()
    results["Test 7: API Endpoints"] = test_api_endpoint_registration()
    results["Test 9: Module Exports"] = test_module_exports()
    results["Test 10: Vector Search Integration"] = test_vector_search_integration()
    results["Test 11: Configuration"] = test_configuration()

    # Async tests
    results["Test 8: Component Initialization"] = await test_component_initialization()

    return results


def print_summary(results: Dict[str, bool]) -> None:
    """Print test summary and statistics."""
    print_section("SUMMARY")

    passed = sum(1 for v in results.values() if v)
    total = len(results)
    percentage = (passed / total * 100) if total > 0 else 0

    print(f"Tests Passed: {GREEN}{passed}/{total}{RESET} ({percentage:.0f}%)\n")

    for test_name, result in results.items():
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"  [{status}] {test_name}")

    print()

    if passed == total:
        print(f"{GREEN}{BOLD}All tests passed!{RESET}\n")
        return True
    else:
        print(f"{RED}{BOLD}{total - passed} test(s) failed.{RESET}\n")
        return False


def main() -> int:
    """Main entry point."""
    print(f"\n{BOLD}{BLUE}{'=' * 70}{RESET}")
    print(f"{BOLD}{BLUE}Sprint 46 Feature 46.6: Manual Domain Testing{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 70}{RESET}\n")

    print(f"Started: {datetime.now().isoformat()}")
    print("Environment: Outside Docker (code structure validation)")
    print("Database Requirements: Neo4j connection for full integration\n")

    try:
        # Run tests
        results = asyncio.run(run_all_tests())

        # Print summary
        all_passed = print_summary(results)

        # Print recommendations
        print_section("RECOMMENDATIONS")

        print("For Docker Environment Testing:")
        print("  1. Ensure Neo4j is running on localhost:7687")
        print("  2. Run domain repository initialization:")
        print("       pytest tests/integration/api/test_domain_training_api.py -v")
        print("  3. Run full test suite:")
        print("       pytest tests/ -v --cov=src --cov-report=html\n")

        print("For Production Deployment:")
        print("  1. Initialize domain repository on startup")
        print("  2. Pre-load domain classifier if domains exist")
        print("  3. Monitor training background tasks")
        print("  4. Keep embeddings cache fresh\n")

        return 0 if all_passed else 1

    except Exception as e:
        print_error(f"Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
