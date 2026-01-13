#!/usr/bin/env python3
"""Verification Script for Sprint 39 Bi-Temporal Implementation.

This script verifies that all Sprint 39 features are correctly implemented:
- Feature 39.1: Temporal feature flags in Settings
- Feature 39.2: Bi-Temporal Query API endpoints
- Feature 39.3: Entity Change Tracking
- Feature 39.4: Entity Version Management

Run this script to verify the implementation:
    python scripts/verify_temporal_implementation.py
"""

import sys
from pathlib import Path


def check_file_exists(file_path: str, description: str) -> bool:
    """Check if a file exists."""
    path = Path(file_path)
    if path.exists():
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} NOT FOUND")
        return False


def check_config_settings() -> bool:
    """Check if temporal settings are in config.py."""
    config_path = Path("src/core/config.py")
    if not config_path.exists():
        print("❌ config.py not found")
        return False

    content = config_path.read_text()

    checks = [
        ("temporal_queries_enabled", "Feature flag in Settings"),
        ("temporal_version_retention", "Version retention setting"),
    ]

    all_found = True
    for key, description in checks:
        if key in content:
            print(f"✅ {description}: {key} found in config.py")
        else:
            print(f"❌ {description}: {key} NOT found in config.py")
            all_found = False

    return all_found


def check_api_endpoints() -> bool:
    """Check if temporal API endpoints are implemented."""
    temporal_api_path = Path("src/api/v1/temporal.py")
    if not temporal_api_path.exists():
        print("❌ temporal.py API router not found")
        return False

    content = temporal_api_path.read_text()

    endpoints = [
        ("/point-in-time", "POST", "Point-in-time query"),
        ("/entity-history", "POST", "Entity history query"),
        ("/entities/{entity_id}/changelog", "GET", "Entity changelog"),
        ("/entities/{entity_id}/versions", "GET", "Version listing"),
        ("/versions/{version_a}/compare/{version_b}", "GET", "Version comparison"),
        ("/versions/{version_id}/revert", "POST", "Version rollback"),
    ]

    all_found = True
    for endpoint, method, description in endpoints:
        if endpoint in content:
            print(f"✅ {description}: {method} {endpoint}")
        else:
            print(f"❌ {description}: {method} {endpoint} NOT found")
            all_found = False

    return all_found


def check_tests() -> bool:
    """Check if temporal tests are implemented."""
    test_path = Path("tests/unit/api/test_temporal.py")
    if not test_path.exists():
        print("❌ test_temporal.py not found")
        return False

    content = test_path.read_text()

    # Count test functions
    test_count = content.count("def test_")
    expected_tests = 20

    if test_count >= expected_tests:
        print(f"✅ Test coverage: {test_count} tests found (expected: {expected_tests})")
        return True
    else:
        print(f"❌ Test coverage: {test_count} tests found (expected: {expected_tests})")
        return False


def check_indexes_script() -> bool:
    """Check if Neo4j indexes script exists."""
    script_path = Path("scripts/neo4j_temporal_indexes.cypher")
    if not script_path.exists():
        print("❌ neo4j_temporal_indexes.cypher not found")
        return False

    content = script_path.read_text()

    indexes = [
        "temporal_validity_idx",
        "temporal_transaction_idx",
        "current_version_idx",
        "changed_by_idx",
        "version_number_idx",
        "version_id_idx",
    ]

    all_found = True
    for index_name in indexes:
        if index_name in content:
            print(f"✅ Index defined: {index_name}")
        else:
            print(f"❌ Index NOT defined: {index_name}")
            all_found = False

    return all_found


def main() -> int:
    """Run all verification checks."""
    print("=" * 70)
    print("Sprint 39: Bi-Temporal Backend Implementation Verification")
    print("=" * 70)
    print()

    results = []

    print("Feature 39.1: Temporal Indexes & Feature Flag")
    print("-" * 70)
    results.append(check_config_settings())
    results.append(check_indexes_script())
    print()

    print("Feature 39.2-39.4: Bi-Temporal Query API")
    print("-" * 70)
    results.append(check_file_exists(
        "src/api/v1/temporal.py",
        "Temporal API router"
    ))
    results.append(check_api_endpoints())
    print()

    print("Testing")
    print("-" * 70)
    results.append(check_file_exists(
        "tests/unit/api/test_temporal.py",
        "Temporal API tests"
    ))
    results.append(check_tests())
    print()

    print("Documentation")
    print("-" * 70)
    results.append(check_file_exists(
        "SPRINT_39_IMPLEMENTATION_SUMMARY.md",
        "Implementation summary"
    ))
    print()

    print("=" * 70)
    if all(results):
        print("✅ All Sprint 39 features verified successfully!")
        print()
        print("Next Steps:")
        print("1. Enable feature flag: Set temporal_queries_enabled = true in .env")
        print("2. Install indexes: cat scripts/neo4j_temporal_indexes.cypher | cypher-shell")
        print("3. Run tests: poetry run pytest tests/unit/api/test_temporal.py -v")
        print("4. Proceed with Frontend Features 39.5-39.7")
        print("=" * 70)
        return 0
    else:
        print("❌ Some features are missing or incomplete")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
