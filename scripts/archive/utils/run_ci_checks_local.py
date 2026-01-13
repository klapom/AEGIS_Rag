#!/usr/bin/env python3
"""Run CI checks locally to simulate GitHub Actions pipeline.

This script runs the same checks as the GitHub Actions CI pipeline,
allowing you to verify fixes before pushing to GitHub.

Usage:
    poetry run python scripts/run_ci_checks_local.py
    poetry run python scripts/run_ci_checks_local.py --quick  # Skip slow tests
"""

import subprocess
import sys
import time
from pathlib import Path

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{BOLD}{BLUE}{'=' * 80}{RESET}")
    print(f"{BOLD}{BLUE}{text:^80}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 80}{RESET}\n")


def print_success(text: str) -> None:
    """Print success message."""
    print(f"{GREEN}[PASS]{RESET} {text}")


def print_error(text: str) -> None:
    """Print error message."""
    print(f"{RED}[FAIL]{RESET} {text}")


def print_warning(text: str) -> None:
    """Print warning message."""
    print(f"{YELLOW}[WARN]{RESET} {text}")


def run_command(
    command: list[str],
    description: str,
    allow_failure: bool = False,
) -> tuple[bool, str]:
    """Run a command and return success status and output.

    Args:
        command: Command to run as list of strings
        description: Human-readable description
        allow_failure: If True, don't exit on failure

    Returns:
        Tuple of (success, output)
    """
    print(f"\n{BOLD}Running: {description}{RESET}")
    print(f"Command: {' '.join(command)}")

    start_time = time.time()

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

        elapsed = time.time() - start_time

        if result.returncode == 0:
            print_success(f"PASSED in {elapsed:.2f}s")
            return True, result.stdout
        else:
            print_error(f"FAILED in {elapsed:.2f}s (exit code {result.returncode})")
            if result.stderr:
                print(f"\n{RED}stderr:{RESET}")
                print(result.stderr[:1000])  # First 1000 chars
            if result.stdout:
                print(f"\n{YELLOW}stdout:{RESET}")
                print(result.stdout[:1000])  # First 1000 chars

            if not allow_failure:
                sys.exit(1)
            return False, result.stderr + result.stdout

    except Exception as e:
        print_error(f"EXCEPTION: {e}")
        if not allow_failure:
            sys.exit(1)
        return False, str(e)


def main() -> None:
    """Run all CI checks locally."""
    quick_mode = "--quick" in sys.argv

    print_header("AegisRAG Local CI Checks")
    print(f"Quick Mode: {quick_mode}")
    print(f"Working Directory: {Path.cwd()}")

    results = []

    # ============================================================
    # 1. Python Import Validation
    # ============================================================
    print_header("1/7: Python Import Validation")

    # Test critical imports
    critical_modules = [
        "src.components.llm_proxy.aegis_llm_proxy",
        "src.components.llm_proxy.cost_tracker",
        "src.components.memory.relevance_scorer",
        "src.components.memory.consolidation",
        "src.components.memory.graphiti_wrapper",
    ]

    import_failures = []
    for module in critical_modules:
        success, output = run_command(
            ["poetry", "run", "python", "-c", f"import {module}; print('OK: {module}')"],
            f"Import {module}",
            allow_failure=True,
        )
        results.append(("Import Validation", module, success))
        if not success:
            import_failures.append(module)

    if import_failures:
        print_error(f"Import validation failed for {len(import_failures)} modules")
    else:
        print_success("All critical imports successful!")

    # ============================================================
    # 2. MyPy Type Checking
    # ============================================================
    print_header("2/7: MyPy Type Checking")

    success, output = run_command(
        ["poetry", "run", "mypy", "src/", "--config-file=pyproject.toml"],
        "MyPy strict type checking",
        allow_failure=True,
    )
    results.append(("MyPy", "type-checking", success))

    # Parse error count from output
    if "Found" in output:
        import re

        match = re.search(r"Found (\d+) error", output)
        if match:
            error_count = int(match.group(1))
            print(f"\n{YELLOW}MyPy Errors: {error_count}{RESET}")
            if error_count < 500:
                print_success("Error count acceptable (<500)")
            else:
                print_warning("Error count high (>500)")

    # ============================================================
    # 3. Code Quality - Ruff
    # ============================================================
    print_header("3/7: Code Quality (Ruff)")

    success, output = run_command(
        ["poetry", "run", "ruff", "check", "src/", "--output-format=concise"],
        "Ruff linting",
        allow_failure=True,
    )
    results.append(("Ruff", "linting", success))

    # ============================================================
    # 4. Code Formatting - Black
    # ============================================================
    print_header("4/7: Code Formatting (Black)")

    success, output = run_command(
        ["poetry", "run", "black", "--check", "src/"],
        "Black formatting check",
        allow_failure=True,
    )
    results.append(("Black", "formatting", success))

    # ============================================================
    # 5. Unit Tests
    # ============================================================
    print_header("5/7: Unit Tests")

    if quick_mode:
        print_warning("Skipped in quick mode")
        results.append(("Unit Tests", "all", None))
    else:
        success, output = run_command(
            [
                "poetry",
                "run",
                "pytest",
                "tests/unit/",
                "-v",
                "--tb=short",
                "--maxfail=5",
            ],
            "Unit tests",
            allow_failure=True,
        )
        results.append(("Unit Tests", "all", success))

    # ============================================================
    # 6. Integration Tests
    # ============================================================
    print_header("6/7: Integration Tests")

    if quick_mode:
        print_warning("Skipped in quick mode")
        results.append(("Integration Tests", "all", None))
    else:
        success, output = run_command(
            [
                "poetry",
                "run",
                "pytest",
                "tests/integration/",
                "-v",
                "--tb=short",
                "--maxfail=3",
            ],
            "Integration tests",
            allow_failure=True,
        )
        results.append(("Integration Tests", "all", success))

    # ============================================================
    # 7. API Contract Validation
    # ============================================================
    print_header("7/7: API Contract Generation")

    success, output = run_command(
        ["poetry", "run", "python", "-c", "from src.api.main import app; print('API imports OK')"],
        "API contract validation",
        allow_failure=True,
    )
    results.append(("API Contract", "import", success))

    # ============================================================
    # Summary
    # ============================================================
    print_header("CI Check Summary")

    passed = sum(1 for _, _, success in results if success is True)
    failed = sum(1 for _, _, success in results if success is False)
    skipped = sum(1 for _, _, success in results if success is None)
    total = len(results)

    print(f"\n{BOLD}Results:{RESET}")
    print(f"  {GREEN}Passed:{RESET}  {passed}/{total}")
    print(f"  {RED}Failed:{RESET}  {failed}/{total}")
    if skipped:
        print(f"  {YELLOW}Skipped:{RESET} {skipped}/{total}")

    print(f"\n{BOLD}Details:{RESET}")
    for category, check, success in results:
        if success is True:
            status = f"{GREEN}[PASS]{RESET}"
        elif success is False:
            status = f"{RED}[FAIL]{RESET}"
        else:
            status = f"{YELLOW}[SKIP]{RESET}"
        print(f"  {status} {category:20s} {check}")

    # Exit code
    print()
    if failed > 0:
        print_error(f"CI checks FAILED ({failed} failures)")
        sys.exit(1)
    elif passed == total:
        print_success("All CI checks PASSED!")
        sys.exit(0)
    else:
        print_warning(f"CI checks PARTIAL ({skipped} skipped)")
        sys.exit(0)


if __name__ == "__main__":
    main()
