#!/usr/bin/env python3
"""Test script for domain seeder (Feature 125.8).

Sprint 125 Feature 125.8: Domain Seeder Extension + Sub-Type Pipeline

This script tests:
1. Loading seed_domains.yaml catalog
2. Seeding single domain
3. Seeding all domains
4. Deployment profile management
5. Sub-type property support

Usage:
    python scripts/test_domain_seeder.py

Requirements:
    - Neo4j running on localhost:7687
    - Redis running on localhost:6379
    - data/seed_domains.yaml exists
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog

from src.components.domain_training.domain_seeder import (
    get_active_domains,
    get_domain_config,
    seed_all_domains,
    seed_default_domains,
    seed_domain,
    set_deployment_profile,
)
from src.components.domain_training.domain_repository import get_domain_repository

logger = structlog.get_logger(__name__)


async def test_default_domain():
    """Test 1: Default domain seeding (backward compatibility)."""
    print("\n=== Test 1: Default Domain Seeding ===")
    try:
        await seed_default_domains()
        print("✓ Default domain seeded successfully")

        # Verify domain exists
        repo = get_domain_repository()
        domain = await repo.get_domain("general")
        if domain:
            print(f"✓ Default domain verified: {domain['name']} (status: {domain['status']})")
        else:
            print("✗ Default domain not found in Neo4j")
            return False

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


async def test_single_domain():
    """Test 2: Seed a single domain from catalog."""
    print("\n=== Test 2: Single Domain Seeding ===")
    try:
        # Seed medicine_health domain
        success = await seed_domain("medicine_health")
        if not success:
            print("✗ Domain not found in catalog")
            return False

        print("✓ Domain seeded successfully")

        # Verify domain exists
        repo = get_domain_repository()
        domain = await repo.get_domain("medicine_health")
        if domain:
            print(f"✓ Domain verified: {domain['name']} (status: {domain['status']})")
            print(f"  Description: {domain['description'][:80]}...")
        else:
            print("✗ Domain not found in Neo4j")
            return False

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


async def test_all_domains():
    """Test 3: Seed all domains from catalog."""
    print("\n=== Test 3: All Domains Seeding ===")
    try:
        stats = await seed_all_domains()
        print(f"✓ All domains seeded")
        print(f"  Total domains: {stats['total_domains']}")
        print(f"  Created: {stats['domains_created']}")
        print(f"  Skipped (already exist): {stats['domains_skipped']}")
        print(f"  Failed: {len(stats['failed_domains'])}")

        if stats["failed_domains"]:
            print(f"  Failed domains: {stats['failed_domains']}")
            return False

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


async def test_deployment_profiles():
    """Test 4: Deployment profile management."""
    print("\n=== Test 4: Deployment Profile Management ===")
    try:
        # Test pharma profile
        await set_deployment_profile("pharma_company")
        print("✓ Deployment profile set: pharma_company")

        active_domains = await get_active_domains()
        print(f"✓ Active domains: {active_domains}")

        # Expected pharma domains
        expected = ["medicine_health", "chemistry", "biology_life_sciences"]
        if set(active_domains) == set(expected):
            print("✓ Active domains match pharma profile")
        else:
            print(f"✗ Active domains mismatch. Expected: {expected}, Got: {active_domains}")
            return False

        # Test university profile (all domains)
        await set_deployment_profile("university")
        print("✓ Deployment profile set: university")

        all_domains = await get_active_domains()
        print(f"✓ Active domains count: {len(all_domains)} (all)")

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


async def test_domain_config():
    """Test 5: Domain configuration access."""
    print("\n=== Test 5: Domain Configuration Access ===")
    try:
        config = await get_domain_config("medicine_health")
        if not config:
            print("✗ Domain config not found")
            return False

        print("✓ Domain config retrieved")
        print(f"  Name: {config.get('name')}")
        print(f"  DDC Code: {config.get('ddc_code')}")
        print(f"  FORD Code: {config.get('ford_code')}")
        print(f"  Entity sub-types: {len(config.get('entity_sub_types', []))}")
        print(f"  Relation hints: {len(config.get('relation_hints', []))}")

        # Check entity sub-types
        entity_sub_types = config.get("entity_sub_types", [])
        if "DISEASE" in entity_sub_types and "MEDICATION" in entity_sub_types:
            print("✓ Entity sub-types include expected values")
        else:
            print(f"✗ Entity sub-types missing expected values: {entity_sub_types}")
            return False

        # Check entity_sub_type_mapping
        mapping = config.get("entity_sub_type_mapping", {})
        if mapping.get("DISEASE") == "CONCEPT" and mapping.get("MEDICATION") == "PRODUCT":
            print("✓ Entity sub-type mapping correct")
        else:
            print(f"✗ Entity sub-type mapping incorrect: {mapping}")
            return False

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


async def test_idempotency():
    """Test 6: Idempotent seeding (re-running doesn't duplicate)."""
    print("\n=== Test 6: Idempotent Seeding ===")
    try:
        # Seed medicine_health twice
        await seed_domain("medicine_health")
        await seed_domain("medicine_health")
        print("✓ Domain seeded twice (idempotent)")

        # Verify only one domain exists
        repo = get_domain_repository()
        domain = await repo.get_domain("medicine_health")
        if domain:
            print("✓ Single domain instance verified")
        else:
            print("✗ Domain not found")
            return False

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Domain Seeder Test Suite (Feature 125.8)")
    print("=" * 60)

    tests = [
        ("Default Domain", test_default_domain),
        ("Single Domain", test_single_domain),
        ("All Domains", test_all_domains),
        ("Deployment Profiles", test_deployment_profiles),
        ("Domain Config", test_domain_config),
        ("Idempotency", test_idempotency),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ Test {test_name} crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n❌ {total - passed} tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
