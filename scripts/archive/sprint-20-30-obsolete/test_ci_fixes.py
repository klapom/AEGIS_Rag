#!/usr/bin/env python3
"""
Test CI Fixes Locally Before Pushing

This script runs the same checks that CI will run, allowing you to verify
fixes work locally before pushing to GitHub.

Sprint 25 Feature 25.X: CI Pipeline Reliability

Usage:
    python scripts/test_ci_fixes.py
"""

import subprocess
import sys
import time
from pathlib import Path
from typing import List, Tuple


class CIFixTester:
    """Test CI fixes locally before pushing."""

    def __init__(self):
        self.passed: List[str] = []
        self.failed: List[str] = []
        self.warnings: List[str] = []

    def run_test(self, name: str, command: List[str], description: str) -> bool:
        """Run a single test and track results."""
        print(f"\n{'=' * 70}")
        print(f"TEST: {name}")
        print(f"Description: {description}")
        print(f"Command: {' '.join(command)}")
        print(f"{'=' * 70}\n")

        start_time = time.time()

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
            )

            elapsed = time.time() - start_time

            if result.returncode == 0:
                print(f"\nPASSED ({elapsed:.1f}s)")
                self.passed.append(f"{name} ({elapsed:.1f}s)")
                return True
            else:
                print(f"\nFAILED ({elapsed:.1f}s)")
                print("\nSTDOUT:")
                print(result.stdout)
                print("\nSTDERR:")
                print(result.stderr)
                self.failed.append(f"{name} (exit code {result.returncode})")
                return False

        except subprocess.TimeoutExpired:
            print("\nFAILED (timeout > 120s)")
            self.failed.append(f"{name} (timeout)")
            return False
        except Exception as e:
            print(f"\nFAILED (exception: {e})")
            self.failed.append(f"{name} (exception)")
            return False

    def test_clear_pyc_cache(self) -> bool:
        """Test 1: Clear Python bytecode cache."""
        return self.run_test(
            name="Clear .pyc Cache",
            command=[
                "bash",
                "-c",
                'find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true; '
                'find . -type f -name "*.pyc" -delete 2>/dev/null || true; '
                'echo "Cache cleared"',
            ],
            description="Clear stale .pyc files that may reference deleted modules",
        )

    def test_naming_conventions(self) -> bool:
        """Test 2: Naming convention check."""
        return self.run_test(
            name="Naming Conventions",
            command=["python", "scripts/check_naming.py", "src/"],
            description="Verify all Python code follows naming conventions",
        )

    def test_optimized_import_validation(self) -> bool:
        """Test 3: Optimized Python import validation."""
        script = """
import sys
import importlib
from pathlib import Path

errors = []
python_files = [f for f in Path("src").rglob("*.py") if "__pycache__" not in str(f)]

print(f"Checking {len(python_files)} Python files...")

for py_file in python_files:
    module_path = str(py_file).replace("/", ".").replace("\\\\", ".").replace(".py", "")
    try:
        importlib.import_module(module_path)
        print(f"  OK: {py_file.name}")
    except Exception as e:
        error_msg = f"{py_file}: {type(e).__name__}: {e}"
        print(f"  FAIL: {error_msg}")
        errors.append(error_msg)

print(f"\\nResults: {len(python_files) - len(errors)}/{len(python_files)} passed")

if errors:
    print(f"\\nFailed imports ({len(errors)}):")
    for error in errors:
        print(f"  - {error}")
    sys.exit(1)
"""
        return self.run_test(
            name="Python Import Validation (Optimized)",
            command=["poetry", "run", "python", "-c", script],
            description="Validate all Python modules can be imported (single process)",
        )

    def test_unit_tests(self) -> bool:
        """Test 4: Unit tests with verbose output."""
        return self.run_test(
            name="Unit Tests",
            command=[
                "poetry",
                "run",
                "pytest",
                "tests/unit/",
                "-vv",
                "--tb=long",
                "-m",
                "not integration",
                "--maxfail=5",  # Stop after 5 failures for faster feedback
            ],
            description="Run unit tests with verbose output (stops after 5 failures)",
        )

    def test_api_loading(self) -> bool:
        """Test 5: FastAPI app loading."""
        script = """
from src.api.main import app
print(f'FastAPI app loaded: {app.title}')
print(f'Routes registered: {len(app.routes)}')
"""
        return self.run_test(
            name="API Loading",
            command=["poetry", "run", "python", "-c", script],
            description="Verify FastAPI app loads without import errors",
        )

    def test_integration_with_mocking(self) -> bool:
        """Test 6: Integration tests with LLM mocking."""
        # Only test a subset of integration tests for speed
        return self.run_test(
            name="Integration Tests (LLM Mocking)",
            command=[
                "bash",
                "-c",
                'CI=true poetry run pytest tests/integration/ -v -k "llm" --maxfail=3',
            ],
            description="Run LLM-related integration tests with CI=true (mocked LLM)",
        )

    def test_deleted_module_imports(self) -> bool:
        """Test 7: Check for imports of deleted modules."""
        deleted_modules = [
            "src.agents.base",
            "src.components.graph_rag.three_phase_extractor",
        ]

        print(f"\n{'=' * 70}")
        print("TEST: Deleted Module Imports Check")
        print("Description: Verify no imports of deleted modules remain")
        print(f"{'=' * 70}\n")

        found_imports = []

        for module in deleted_modules:
            # Check for "from X import" patterns
            cmd1 = [
                "grep",
                "-rn",
                f"from {module} import",
                "src/",
                "tests/",
            ]
            # Check for "import X" patterns
            cmd2 = ["grep", "-rn", f"import {module}", "src/", "tests/"]

            try:
                result1 = subprocess.run(cmd1, capture_output=True, text=True)
                result2 = subprocess.run(cmd2, capture_output=True, text=True)

                if result1.stdout or result2.stdout:
                    found_imports.append(f"{module}:\\n{result1.stdout}{result2.stdout}")
                    print(f"FOUND: Imports of {module}")
                    print(result1.stdout)
                    print(result2.stdout)
                else:
                    print(f"OK: No imports of {module}")
            except Exception:
                # grep not found or error - skip on Windows
                self.warnings.append("Deleted module check skipped (grep not available)")
                return True

        if found_imports:
            print("\nFAILED: Found imports of deleted modules")
            self.failed.append("Deleted Module Imports (found imports)")
            return False
        else:
            print("\nPASSED: No imports of deleted modules found")
            self.passed.append("Deleted Module Imports")
            return True

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)

        if self.passed:
            print(f"\nPASSED ({len(self.passed)}):")
            for test in self.passed:
                print(f"  ✓ {test}")

        if self.warnings:
            print(f"\nWARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  ⚠ {warning}")

        if self.failed:
            print(f"\nFAILED ({len(self.failed)}):")
            for test in self.failed:
                print(f"  ✗ {test}")

        print(f"\nTotal: {len(self.passed)}/{len(self.passed) + len(self.failed)} passed")

        if self.failed:
            print("\nCI FIXES NOT READY - Fix failures before pushing")
            return False
        else:
            print("\nCI FIXES READY - All tests passed, safe to push!")
            return True


def main():
    """Run all tests."""
    print("=" * 70)
    print("CI FIXES LOCAL TESTING")
    print("Sprint 25 Feature 25.X: CI Pipeline Reliability")
    print("=" * 70)

    tester = CIFixTester()

    # Run all tests
    tests = [
        tester.test_clear_pyc_cache,
        tester.test_deleted_module_imports,
        tester.test_naming_conventions,
        tester.test_optimized_import_validation,
        tester.test_api_loading,
        tester.test_unit_tests,
        tester.test_integration_with_mocking,
    ]

    for test_func in tests:
        test_func()

    # Print summary and exit
    all_passed = tester.print_summary()
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
