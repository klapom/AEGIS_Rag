#!/usr/bin/env python3
"""
Test script for Sprint 112 Certification Endpoints
Tests all 5 new certification endpoints with mock data

Usage:
    python3 scripts/test_certification_endpoints.py

Requirements:
    - API server running on http://localhost:8000
"""

import asyncio
import json
import sys

import aiohttp


BASE_URL = "http://localhost:8000"


async def test_get_overview():
    """Test GET /api/v1/certification/overview"""
    print("\n1. Testing GET /api/v1/certification/overview")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/v1/certification/overview") as resp:
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            data = await resp.json()
            print(f"   ✅ Overview: {data['enterprise_count']} enterprise, "
                  f"{data['standard_count']} standard, "
                  f"{data['basic_count']} basic, "
                  f"{data['uncertified_count']} uncertified")
            print(f"   ✅ Status: {data['expiring_soon_count']} expiring soon, "
                  f"{data['expired_count']} expired")
            return data


async def test_get_skills():
    """Test GET /api/v1/certification/skills"""
    print("\n2. Testing GET /api/v1/certification/skills")
    async with aiohttp.ClientSession() as session:
        # Test without filters
        async with session.get(f"{BASE_URL}/api/v1/certification/skills") as resp:
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            data = await resp.json()
            print(f"   ✅ Total skills: {len(data)}")

        # Test with level filter
        async with session.get(
            f"{BASE_URL}/api/v1/certification/skills?level=enterprise"
        ) as resp:
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            data = await resp.json()
            print(f"   ✅ Enterprise skills: {len(data)}")
            assert all(s["level"] == "enterprise" for s in data), "Filter failed"

        # Test with status filter
        async with session.get(
            f"{BASE_URL}/api/v1/certification/skills?status=expiring_soon"
        ) as resp:
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            data = await resp.json()
            print(f"   ✅ Expiring soon: {len(data)}")
            assert all(
                s["status"] == "expiring_soon" for s in data
            ), "Status filter failed"

        return data


async def test_get_expiring():
    """Test GET /api/v1/certification/expiring"""
    print("\n3. Testing GET /api/v1/certification/expiring")
    async with aiohttp.ClientSession() as session:
        # Test default (30 days)
        async with session.get(f"{BASE_URL}/api/v1/certification/expiring") as resp:
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            data = await resp.json()
            print(f"   ✅ Expiring in 30 days: {len(data)}")

        # Test custom threshold (90 days)
        async with session.get(
            f"{BASE_URL}/api/v1/certification/expiring?days=90"
        ) as resp:
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            data = await resp.json()
            print(f"   ✅ Expiring in 90 days: {len(data)}")

        return data


async def test_get_skill_report():
    """Test GET /api/v1/certification/skill/{skillName}/report"""
    print("\n4. Testing GET /api/v1/certification/skill/{skillName}/report")
    async with aiohttp.ClientSession() as session:
        # Test with known skill
        async with session.get(
            f"{BASE_URL}/api/v1/certification/skill/enterprise_skill_1/report"
        ) as resp:
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            data = await resp.json()
            print(
                f"   ✅ Validation report for {data['skill_name']}: "
                f"{data['passed_checks']}/{data['total_checks']} checks passed"
            )
            print(
                f"   ✅ Certification level: {data['certification_level']}, "
                f"{len(data['recommendations'])} recommendations"
            )

        # Test with unknown skill (should still return 200 with uncertified status)
        async with session.get(
            f"{BASE_URL}/api/v1/certification/skill/unknown_skill/report"
        ) as resp:
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            data = await resp.json()
            print(f"   ✅ Unknown skill returns uncertified report")

        return data


async def test_validate_skill():
    """Test POST /api/v1/certification/skill/{skillName}/validate"""
    print("\n5. Testing POST /api/v1/certification/skill/{skillName}/validate")
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_URL}/api/v1/certification/skill/standard_skill_1/validate"
        ) as resp:
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            data = await resp.json()
            print(
                f"   ✅ Validation triggered for {data['skill_name']}: "
                f"{data['passed_checks']}/{data['total_checks']} checks passed"
            )
            print(f"   ✅ Certification level: {data['certification_level']}")

        return data


async def main():
    """Run all certification endpoint tests"""
    print("=" * 70)
    print("Sprint 112: Certification Endpoints Test")
    print("=" * 70)

    try:
        await test_get_overview()
        await test_get_skills()
        await test_get_expiring()
        await test_get_skill_report()
        await test_validate_skill()

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED - Certification endpoints working correctly")
        print("=" * 70)
        return 0

    except aiohttp.ClientConnectorError:
        print("\n❌ ERROR: Cannot connect to API server")
        print("   Make sure the API is running on http://localhost:8000")
        print("   Start with: docker compose -f docker-compose.dgx-spark.yml up -d")
        return 1

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1

    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
