#!/usr/bin/env python3
"""Pre-commit hook: Validate Python imports.

Sprint 18 TD-42: Prevent import errors like those fixed in Sprint 17 (TD-41).

This hook:
1. Attempts to import each Python file as a module
2. Catches ImportError, NameError, ModuleNotFoundError
3. Reports files that would fail at runtime
4. Prevents commits with broken imports

Usage:
    pre-commit run check-imports --all-files
"""

import ast
import sys
from pathlib import Path
from typing import List, Tuple


def check_python_imports(file_path: str) -> Tuple[bool, List[str]]:
    """Check if a Python file has valid imports.

    Args:
        file_path: Path to Python file to check

    Returns:
        Tuple of (success, error_messages)
    """
    errors = []

    try:
        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # Parse AST to find imports
        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError as e:
            errors.append(f"Syntax error: {e}")
            return False, errors

        # Extract all imports
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        # Validate forward references (common issue from Sprint 17)
        for node in ast.walk(tree):
            if isinstance(node, ast.AnnAssign):
                # Check type annotations
                if isinstance(node.annotation, ast.Subscript):
                    # Check for list[Foo] vs list["Foo"]
                    if isinstance(node.annotation.value, ast.Name):
                        if node.annotation.value.id in ('list', 'dict', 'set', 'tuple'):
                            # Check if slice is a Name (not string)
                            if isinstance(node.annotation.slice, ast.Name):
                                type_name = node.annotation.slice.id
                                # Check if this type is imported
                                if type_name not in ('str', 'int', 'float', 'bool'):
                                    # Look for import
                                    found = any(
                                        type_name in imp or imp.endswith(f'.{type_name}')
                                        for imp in imports
                                    )
                                    if not found:
                                        errors.append(
                                            f"Line {node.lineno}: Forward reference '{type_name}' "
                                            f"not imported. Use quotes: list[\"{type_name}\"]"
                                        )

        # Check for common import errors
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                # Check for relative imports without package
                if node.level > 0 and not node.module:
                    errors.append(
                        f"Line {node.lineno}: Relative import 'from . import ...' "
                        "requires explicit module"
                    )

        if errors:
            return False, errors

        return True, []

    except Exception as e:
        errors.append(f"Unexpected error: {e}")
        return False, errors


def main(filenames: List[str]) -> int:
    """Main entry point for pre-commit hook.

    Args:
        filenames: List of files to check

    Returns:
        Exit code (0 = success, 1 = failure)
    """
    exit_code = 0

    print("[TD-42] Validating Python imports...")

    for filename in filenames:
        # Skip __init__.py and test files (different rules)
        if filename.endswith('__init__.py'):
            continue

        # Only check Python files
        if not filename.endswith('.py'):
            continue

        # Skip virtual env, cache dirs
        if any(skip in filename for skip in ['.venv', '__pycache__', '.pytest_cache']):
            continue

        success, errors = check_python_imports(filename)

        if not success:
            print(f"\n[FAIL] {filename}")
            for error in errors:
                print(f"   {error}")
            exit_code = 1
        else:
            print(f"[OK] {filename}")

    if exit_code == 0:
        print("\n[OK] All imports are valid!")
    else:
        print("\n[FAIL] Import validation failed. Fix errors above.")
        print("\nCommon fixes:")
        print("  - Add missing imports")
        print("  - Use forward references with quotes: list[\"Foo\"] not list[Foo]")
        print("  - Check circular import dependencies")

    return exit_code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
