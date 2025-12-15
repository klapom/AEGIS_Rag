#!/usr/bin/env python3
"""Static Code Analysis for Sprint 46 Feature 46.6: Manual Domain Testing.

This script performs static analysis of domain training components without
requiring full environment setup. It validates:

1. File existence and structure
2. Import statements and module structure
3. API endpoint registration
4. Class and function definitions
5. Configuration requirements

Usage:
    python3 scripts/static_domain_testing.py
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
# File Structure Validation
# ============================================================================

def validate_domain_training_files() -> bool:
    """Test 1: Verify all domain training files exist."""
    print_section("TEST 1: Domain Training File Structure")

    all_passed = True

    required_files = {
        "src/components/domain_training/__init__.py": "Module initialization",
        "src/components/domain_training/domain_repository.py": "Domain repository (45.1)",
        "src/components/domain_training/domain_classifier.py": "Domain classifier (45.6)",
        "src/components/domain_training/dspy_optimizer.py": "DSPy optimizer (45.2)",
        "src/components/domain_training/prompt_extractor.py": "Prompt extractor (45.2)",
        "src/components/domain_training/training_progress.py": "Progress tracker (45.5)",
        "src/components/domain_training/domain_discovery.py": "Domain discovery (45.9)",
        "src/components/domain_training/domain_analyzer.py": "Domain analyzer (46.4)",
        "src/components/domain_training/grouped_ingestion.py": "Grouped ingestion (45.10)",
        "src/components/domain_training/data_augmentation.py": "Data augmentation (45.11)",
        "src/components/domain_training/training_runner.py": "Training runner",
        "src/components/domain_training/training_stream.py": "Training stream",
        "src/api/v1/domain_training.py": "API endpoints (45.3)",
        "src/api/v1/admin/domain_discovery.py": "Admin domain discovery (46.4)",
    }

    for file_path, description in required_files.items():
        full_path = f"/home/admin/projects/aegisrag/AEGIS_Rag/{file_path}"
        exists = os.path.isfile(full_path)
        print_test(
            f"{file_path}",
            exists,
            description if exists else "File not found"
        )
        if not exists:
            all_passed = False

    return all_passed


# ============================================================================
# Module Exports Validation
# ============================================================================

def check_file_content(file_path: str, pattern: str) -> bool:
    """Check if file contains pattern."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            return re.search(pattern, content) is not None
    except FileNotFoundError:
        return False


def validate_module_exports() -> bool:
    """Test 2: Verify __all__ exports in domain training module."""
    print_section("TEST 2: Module Exports (__all__)")

    all_passed = True
    init_file = "/home/admin/projects/aegisrag/AEGIS_Rag/src/components/domain_training/__init__.py"

    # Check __all__ is defined
    has_all = check_file_content(init_file, r"^__all__\s*=\s*\[")
    print_test(
        "Module has __all__ defined",
        has_all,
        "Explicit exports list present"
    )

    if has_all:
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

        with open(init_file, 'r') as f:
            content = f.read()

        # Check each export is in __all__
        for export_name in expected_exports:
            in_all = f'"{export_name}"' in content or f"'{export_name}'" in content
            if not in_all:
                print_info(f"Export '{export_name}' not found in __all__")
                all_passed = False

        if all_passed:
            print_success("All expected exports present in __all__")

    return all_passed


# ============================================================================
# Class and Function Definitions
# ============================================================================

def validate_domain_repository_structure() -> bool:
    """Test 3: Verify DomainRepository structure."""
    print_section("TEST 3: DomainRepository Structure")

    all_passed = True
    file_path = "/home/admin/projects/aegisrag/AEGIS_Rag/src/components/domain_training/domain_repository.py"

    with open(file_path, 'r') as f:
        content = f.read()

    # Check class definition
    has_class = "class DomainRepository:" in content
    print_test(
        "DomainRepository class defined",
        has_class,
        "Main class present"
    )

    if has_class:
        # Check key methods
        methods = [
            ("__init__", "Constructor"),
            ("initialize", "Initialization (async)"),
            ("create_domain", "Create domain (async)"),
            ("get_domain", "Get domain (async)"),
            ("list_domains", "List domains (async)"),
            ("update_domain_prompts", "Update prompts (async)"),
            ("find_best_matching_domain", "Find matching domain (async)"),
            ("delete_domain", "Delete domain (async)"),
            ("create_training_log", "Create training log (async)"),
            ("update_training_log", "Update training log (async)"),
            ("get_latest_training_log", "Get latest log (async)"),
        ]

        for method_name, description in methods:
            has_method = f"def {method_name}(" in content
            print_test(
                f"Has {method_name}() method",
                has_method,
                description
            )
            if not has_method:
                all_passed = False

    # Check singleton function
    has_get_function = "def get_domain_repository()" in content
    print_test(
        "Has get_domain_repository() singleton function",
        has_get_function,
        "Global instance factory"
    )

    return all_passed


def validate_domain_classifier_structure() -> bool:
    """Test 4: Verify DomainClassifier structure."""
    print_section("TEST 4: DomainClassifier Structure")

    all_passed = True
    file_path = "/home/admin/projects/aegisrag/AEGIS_Rag/src/components/domain_training/domain_classifier.py"

    with open(file_path, 'r') as f:
        content = f.read()

    # Check class definition
    has_class = "class DomainClassifier:" in content
    print_test(
        "DomainClassifier class defined",
        has_class,
        "Main class present"
    )

    if has_class:
        # Check key methods
        methods = [
            ("__init__", "Constructor"),
            ("_load_embedding_model", "Load embedding model (lazy)"),
            ("load_domains", "Load domains from Neo4j (async)"),
            ("classify_document", "Classify document"),
            ("_sample_text", "Sample text strategy"),
            ("get_loaded_domains", "Get loaded domain names"),
            ("is_loaded", "Check if loaded"),
            ("reload_domains", "Reload domains (async)"),
        ]

        for method_name, description in methods:
            has_method = f"def {method_name}(" in content
            print_test(
                f"Has {method_name}() method",
                has_method,
                description
            )
            if not has_method:
                all_passed = False

    # Check singleton function
    has_get_function = "def get_domain_classifier()" in content
    has_reset_function = "def reset_classifier()" in content

    print_test(
        "Has get_domain_classifier() singleton function",
        has_get_function,
        "Global instance factory"
    )
    print_test(
        "Has reset_classifier() reset function",
        has_reset_function,
        "For testing purposes"
    )

    if not (has_get_function and has_reset_function):
        all_passed = False

    return all_passed


def validate_dspy_optimizer_structure() -> bool:
    """Test 5: Verify DSPyOptimizer structure."""
    print_section("TEST 5: DSPyOptimizer Structure")

    all_passed = True
    file_path = "/home/admin/projects/aegisrag/AEGIS_Rag/src/components/domain_training/dspy_optimizer.py"

    with open(file_path, 'r') as f:
        content = f.read()

    # Check class definition
    has_class = "class DSPyOptimizer:" in content
    print_test(
        "DSPyOptimizer class defined",
        has_class,
        "Main class present"
    )

    if has_class:
        # Check key methods
        methods = [
            ("__init__", "Constructor"),
            ("optimize_entity_extraction", "Optimize entity extraction (async)"),
            ("optimize_relation_extraction", "Optimize relation extraction (async)"),
        ]

        for method_name, description in methods:
            has_method = f"def {method_name}(" in content
            print_test(
                f"Has {method_name}() method",
                has_method,
                description
            )
            if not has_method:
                all_passed = False

    # Check Signature definitions
    has_entity_sig = "class EntityExtractionSignature" in content
    has_relation_sig = "class RelationExtractionSignature" in content

    print_test(
        "Has EntityExtractionSignature DSPy signature",
        has_entity_sig,
        "DSPy signature class"
    )
    print_test(
        "Has RelationExtractionSignature DSPy signature",
        has_relation_sig,
        "DSPy signature class"
    )

    if not (has_entity_sig and has_relation_sig):
        all_passed = False

    return all_passed


# ============================================================================
# API Endpoint Validation
# ============================================================================

def validate_api_endpoints() -> bool:
    """Test 6: Verify API endpoint registration."""
    print_section("TEST 6: API Endpoint Definitions")

    all_passed = True
    api_file = "/home/admin/projects/aegisrag/AEGIS_Rag/src/api/v1/domain_training.py"

    with open(api_file, 'r') as f:
        content = f.read()

    # Check router definition
    has_router = "router = APIRouter" in content
    print_test(
        "APIRouter defined",
        has_router,
        "FastAPI router instance"
    )

    if has_router:
        # Expected endpoints (decorators)
        endpoints = [
            ("@router.post(\"/\",", "POST /admin/domains - Create domain"),
            ("@router.get(\"/\",", "GET /admin/domains - List domains"),
            ("@router.get(\"/available-models\",", "GET /admin/domains/available-models"),
            ("@router.get(\"/{domain_name}\",", "GET /admin/domains/{name}"),
            ("@router.post(\"/{domain_name}/train\",", "POST /admin/domains/{name}/train"),
            ("@router.get(\"/{domain_name}/training-status\",", "GET /admin/domains/{name}/training-status"),
            ("@router.get(\"/{domain_name}/training-stream\",", "GET stream endpoint"),
            ("@router.delete(\"/{domain_name}\",", "DELETE /admin/domains/{name}"),
            ("@router.post(\"/classify\",", "POST /admin/domains/classify"),
            ("@router.post(\"/discover\",", "POST /admin/domains/discover"),
            ("@router.post(\"/ingest-batch\",", "POST /admin/domains/ingest-batch"),
            ("@router.post(\"/augment\",", "POST /admin/domains/augment"),
        ]

        for decorator, description in endpoints:
            has_endpoint = decorator in content
            print_test(
                f"Endpoint defined: {description}",
                has_endpoint,
                "" if has_endpoint else "Not found"
            )
            if not has_endpoint:
                all_passed = False

    return all_passed


def validate_main_app_integration() -> bool:
    """Test 7: Verify integration in main FastAPI app."""
    print_section("TEST 7: FastAPI Application Integration")

    all_passed = True
    main_file = "/home/admin/projects/aegisrag/AEGIS_Rag/src/api/main.py"

    with open(main_file, 'r') as f:
        content = f.read()

    # Check router import
    has_import = "from src.api.v1.domain_training import router as domain_training_router" in content
    print_test(
        "domain_training router imported",
        has_import,
        "Import statement present"
    )

    # Note: Router inclusion in app is typically done via app.include_router()
    # Check if routers are included (may be in lifespan or elsewhere)
    has_router_ref = "domain_training_router" in content
    print_test(
        "domain_training_router referenced in main",
        has_router_ref,
        "Router is used in application"
    )

    return all_passed


# ============================================================================
# Configuration Validation
# ============================================================================

def validate_configuration() -> bool:
    """Test 8: Verify configuration requirements."""
    print_section("TEST 8: Configuration Requirements")

    all_passed = True

    # Check settings file
    settings_file = "/home/admin/projects/aegisrag/AEGIS_Rag/src/core/config.py"

    with open(settings_file, 'r') as f:
        content = f.read()

    # Check for domain-related settings
    settings = [
        ("neo4j_uri", "Neo4j connection URI"),
        ("neo4j_database", "Neo4j database name"),
        ("lightrag_llm_model", "LLM model for extraction"),
    ]

    for setting_name, description in settings:
        has_setting = setting_name in content
        print_test(
            f"Setting '{setting_name}' configured",
            has_setting,
            description
        )
        if not has_setting:
            all_passed = False

    return all_passed


# ============================================================================
# Test File Validation
# ============================================================================

def validate_test_structure() -> bool:
    """Test 9: Verify test file structure."""
    print_section("TEST 9: Test File Structure")

    all_passed = True

    test_files = {
        "tests/unit/components/domain_training/__init__.py": "Unit test init",
        "tests/unit/components/domain_training/test_domain_repository.py": "Repository tests",
        "tests/unit/components/domain_training/test_domain_classifier.py": "Classifier tests",
        "tests/unit/components/domain_training/test_dspy_optimizer.py": "DSPy optimizer tests",
        "tests/unit/components/domain_training/test_training_progress.py": "Progress tracker tests",
        "tests/integration/api/test_domain_training_api.py": "API integration tests",
    }

    for file_path, description in test_files.items():
        full_path = f"/home/admin/projects/aegisrag/AEGIS_Rag/{file_path}"
        exists = os.path.isfile(full_path)
        print_test(
            f"{file_path}",
            exists,
            description if exists else "Test file not found"
        )
        if not exists:
            all_passed = False

    return all_passed


# ============================================================================
# Documentation Validation
# ============================================================================

def validate_documentation() -> bool:
    """Test 10: Verify documentation files."""
    print_section("TEST 10: Documentation")

    all_passed = True

    doc_checks = [
        ("docs/adr/ADR_INDEX.md", "ADR index"),
        ("docs/sprints/SPRINT_PLAN.md", "Sprint plans"),
        ("docs/NAMING_CONVENTIONS.md", "Naming conventions"),
    ]

    for file_path, description in doc_checks:
        full_path = f"/home/admin/projects/aegisrag/AEGIS_Rag/{file_path}"
        exists = os.path.isfile(full_path)
        print_test(
            f"{file_path}",
            exists,
            description if exists else "Documentation file not found"
        )

    return all_passed


# ============================================================================
# Code Quality Checks
# ============================================================================

def check_code_quality() -> bool:
    """Test 11: Basic code quality checks."""
    print_section("TEST 11: Code Quality Checks")

    all_passed = True

    # Check domain_training init file
    init_file = "/home/admin/projects/aegisrag/AEGIS_Rag/src/components/domain_training/__init__.py"

    with open(init_file, 'r') as f:
        content = f.read()

    # Check docstring
    has_docstring = '"""' in content[:200]  # Check first 200 chars
    print_test(
        "Module has docstring",
        has_docstring,
        "Documentation present"
    )

    # Check imports organized
    imports_before_all = content.find("import") < content.find("__all__")
    print_test(
        "Imports before __all__",
        imports_before_all,
        "Proper organization"
    )

    # Check type hints used
    has_type_hints = "from typing" in content or "->" in content
    print_test(
        "Type hints used",
        has_type_hints,
        "Type annotations present"
    )

    return all_passed


# ============================================================================
# Sprint Requirements Validation
# ============================================================================

def validate_sprint_requirements() -> bool:
    """Test 12: Verify Sprint 45/46 feature requirements."""
    print_section("TEST 12: Sprint Requirements (45.1-46.6)")

    all_passed = True

    features = {
        "45.1 Domain Registry": {
            "file": "src/components/domain_training/domain_repository.py",
            "required": ["DomainRepository", "get_domain_repository"]
        },
        "45.2 DSPy Optimization": {
            "file": "src/components/domain_training/dspy_optimizer.py",
            "required": ["DSPyOptimizer", "EntityExtractionSignature", "RelationExtractionSignature"]
        },
        "45.3 API Endpoints": {
            "file": "src/api/v1/domain_training.py",
            "required": ["router", "@router.post", "@router.get", "@router.delete"]
        },
        "45.5 Progress Tracking": {
            "file": "src/components/domain_training/training_progress.py",
            "required": ["TrainingProgressTracker", "TrainingPhase", "ProgressEvent"]
        },
        "45.6 Domain Classifier": {
            "file": "src/components/domain_training/domain_classifier.py",
            "required": ["DomainClassifier", "get_domain_classifier"]
        },
        "45.9 Domain Discovery": {
            "file": "src/components/domain_training/domain_discovery.py",
            "required": ["DomainDiscoveryService", "DomainSuggestion"]
        },
        "45.10 Grouped Ingestion": {
            "file": "src/components/domain_training/grouped_ingestion.py",
            "required": ["GroupedIngestionProcessor", "IngestionItem", "IngestionBatch"]
        },
        "45.11 Data Augmentation": {
            "file": "src/components/domain_training/data_augmentation.py",
            "required": ["TrainingDataAugmenter", "get_training_data_augmenter"]
        },
        "46.4 Domain Analyzer": {
            "file": "src/components/domain_training/domain_analyzer.py",
            "required": ["DomainAnalyzer", "get_domain_analyzer"]
        },
    }

    for feature_name, details in features.items():
        file_path = f"/home/admin/projects/aegisrag/AEGIS_Rag/{details['file']}"

        if not os.path.isfile(file_path):
            print_test(feature_name, False, f"File not found: {details['file']}")
            all_passed = False
            continue

        with open(file_path, 'r') as f:
            content = f.read()

        # Check all required items are present
        all_present = all(req in content for req in details['required'])
        print_test(
            feature_name,
            all_present,
            f"Required items: {', '.join(details['required'][:2])}..."
        )

        if not all_present:
            missing = [r for r in details['required'] if r not in content]
            print_info(f"Missing: {', '.join(missing)}")
            all_passed = False

    return all_passed


# ============================================================================
# Main Test Runner
# ============================================================================

def run_all_tests() -> Dict[str, bool]:
    """Run all static analysis tests."""
    results = {}

    results["Test 1: File Structure"] = validate_domain_training_files()
    results["Test 2: Module Exports"] = validate_module_exports()
    results["Test 3: DomainRepository"] = validate_domain_repository_structure()
    results["Test 4: DomainClassifier"] = validate_domain_classifier_structure()
    results["Test 5: DSPyOptimizer"] = validate_dspy_optimizer_structure()
    results["Test 6: API Endpoints"] = validate_api_endpoints()
    results["Test 7: FastAPI Integration"] = validate_main_app_integration()
    results["Test 8: Configuration"] = validate_configuration()
    results["Test 9: Test Structure"] = validate_test_structure()
    results["Test 10: Documentation"] = validate_documentation()
    results["Test 11: Code Quality"] = check_code_quality()
    results["Test 12: Sprint Requirements"] = validate_sprint_requirements()

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
        print(f"{GREEN}{BOLD}All static analysis tests passed!{RESET}\n")
        return True
    else:
        print(f"{RED}{BOLD}{total - passed} test(s) failed.{RESET}\n")
        return False


def main() -> int:
    """Main entry point."""
    print(f"\n{BOLD}{BLUE}{'=' * 70}{RESET}")
    print(f"{BOLD}{BLUE}Sprint 46 Feature 46.6: Manual Domain Testing{RESET}")
    print(f"{BOLD}{BLUE}Static Code Analysis (No Runtime Environment Required){RESET}")
    print(f"{BOLD}{BLUE}{'=' * 70}{RESET}\n")

    print(f"Started: {datetime.now().isoformat()}")
    print("Type: Static code analysis")
    print("Focus: Code structure, imports, exports, configuration\n")

    try:
        # Run tests
        results = run_all_tests()

        # Print summary
        all_passed = print_summary(results)

        # Print next steps
        print_section("NEXT STEPS")

        print("To validate with actual imports and runtime:")
        print("  1. Ensure Poetry dependencies are installed:")
        print("       poetry install")
        print("")
        print("  2. Run dynamic testing with pytest:")
        print("       pytest tests/unit/components/domain_training/ -v")
        print("       pytest tests/integration/api/test_domain_training_api.py -v")
        print("")
        print("To test with Docker:")
        print("  1. Ensure Neo4j is running:")
        print("       docker-compose up -d neo4j")
        print("")
        print("  2. Run full integration tests:")
        print("       pytest tests/integration/ -v --tb=short")
        print("")
        print("To run manual domain testing:")
        print("  1. After dependencies installed:")
        print("       PYTHONPATH=/home/admin/projects/aegisrag/AEGIS_Rag python3 scripts/manual_domain_testing.py")
        print("")

        return 0 if all_passed else 1

    except Exception as e:
        print_error(f"Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
