#!/usr/bin/env python3
"""Pre-commit hook: Validate FastAPI router prefix conventions.

Sprint 18 TD-42: Prevent router prefix issues like TD-41 (Admin Stats 404).

This hook enforces the established pattern:
- Router files: APIRouter(prefix="/relative", tags=["tag"])
- main.py: app.include_router(router, prefix="/api/v1")

CORRECT:
    # src/api/v1/admin.py
    router = APIRouter(prefix="/admin", tags=["admin"])

    # src/api/main.py
    app.include_router(admin_router, prefix="/api/v1")
    # Result: /api/v1/admin/*

INCORRECT:
    # src/api/v1/admin.py
    router = APIRouter(prefix="/api/v1/admin", tags=["admin"])  # ← BAD!

    # src/api/main.py
    app.include_router(admin_router)  # ← Missing /api/v1
    # Result: Routes not registered correctly

Usage:
    pre-commit run check-router-prefix --all-files
"""

import ast
import re
import sys
from pathlib import Path
from typing import List, Tuple, Optional


def check_router_prefix(file_path: str) -> Tuple[bool, List[str]]:
    """Check if router prefix follows conventions.

    Args:
        file_path: Path to Python file to check

    Returns:
        Tuple of (success, error_messages)
    """
    errors = []

    # Only check API router files
    if 'src/api/' not in file_path.replace('\\', '/'):
        return True, []

    # Skip main.py (different rules)
    if file_path.endswith('main.py'):
        return True, []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # Parse AST
        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError:
            # Syntax errors are caught by other hooks
            return True, []

        # Find APIRouter instantiations
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                # Check for: router = APIRouter(prefix="...", ...)
                if any(
                    isinstance(target, ast.Name) and target.id == 'router'
                    for target in node.targets
                ):
                    if isinstance(node.value, ast.Call):
                        if isinstance(node.value.func, ast.Name):
                            if node.value.func.id == 'APIRouter':
                                # Found router = APIRouter(...)
                                # Check prefix argument
                                prefix = None
                                for keyword in node.value.keywords:
                                    if keyword.arg == 'prefix':
                                        if isinstance(keyword.value, ast.Constant):
                                            prefix = keyword.value.value

                                if prefix:
                                    # Check if prefix starts with /api/v (anti-pattern)
                                    if prefix.startswith('/api/v'):
                                        errors.append(
                                            f"Line {node.lineno}: Router prefix should be RELATIVE, "
                                            f"not absolute.\n"
                                            f"   Found: APIRouter(prefix=\"{prefix}\")\n"
                                            f"   Use: APIRouter(prefix=\"{prefix.split('/')[-1]}\")\n"
                                            f"   Add \"/api/v1\" in main.py: "
                                            f"app.include_router(router, prefix=\"/api/v1\")"
                                        )

        if errors:
            return False, errors

        return True, []

    except Exception as e:
        # Don't fail on unexpected errors (could be non-router file)
        return True, []


def check_main_router_registration(file_path: str) -> Tuple[bool, List[str]]:
    """Check if main.py router registrations include prefix.

    Args:
        file_path: Path to main.py

    Returns:
        Tuple of (success, warnings)
    """
    if not file_path.endswith('main.py'):
        return True, []

    warnings = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # Look for app.include_router() calls
        pattern = r'app\.include_router\((\w+)(?:,\s*prefix=["\'](/[^"\']+)["\'])?\)'

        for match in re.finditer(pattern, source):
            router_name = match.group(1)
            prefix = match.group(2) if match.group(2) else None

            if not prefix:
                warnings.append(
                    f"WARNING: Router '{router_name}' registered without prefix.\n"
                    f"   Consider adding: app.include_router({router_name}, prefix=\"/api/v1\")"
                )

        # Informational only (don't fail)
        return True, warnings

    except Exception:
        return True, []


def main(filenames: List[str]) -> int:
    """Main entry point for pre-commit hook.

    Args:
        filenames: List of files to check

    Returns:
        Exit code (0 = success, 1 = failure)
    """
    exit_code = 0

    print("[TD-42] Validating FastAPI router prefixes...")

    for filename in filenames:
        # Only check Python files in API directory
        if not filename.endswith('.py'):
            continue

        if 'src/api/' not in filename.replace('\\', '/'):
            continue

        # Check router files
        success, errors = check_router_prefix(filename)

        if not success:
            print(f"\n[FAIL] {filename}")
            for error in errors:
                print(f"   {error}")
            exit_code = 1
        else:
            # Check main.py for informational warnings
            if filename.endswith('main.py'):
                _, warnings = check_main_router_registration(filename)
                if warnings:
                    print(f"\n[INFO] {filename}")
                    for warning in warnings:
                        print(f"   {warning}")
            else:
                print(f"[OK] {filename}")

    if exit_code == 0:
        print("\n[OK] All router prefixes follow conventions!")
        print("\nPattern established by TD-41:")
        print("  Router files: APIRouter(prefix=\"/relative\")")
        print("  main.py: app.include_router(router, prefix=\"/api/v1\")")
    else:
        print("\n[FAIL] Router prefix validation failed. Fix errors above.")

    return exit_code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
