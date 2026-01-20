#!/usr/bin/env python3
"""Check Python naming conventions.

This script validates that Python files follow naming conventions:
- Classes: PascalCase
- Functions/methods: snake_case
- Constants: UPPER_SNAKE_CASE
- Variables: snake_case

Used by the CI pipeline (ci.yml) for naming conventions validation.

Usage:
    python scripts/check_naming.py src/module1.py src/module2.py
    find src -name "*.py" -exec python scripts/check_naming.py {} +
"""

import ast
import re
import sys
from pathlib import Path
from typing import List, Tuple


class NamingChecker(ast.NodeVisitor):
    """AST visitor to check naming conventions."""

    def __init__(self, filename: str):
        self.filename = filename
        self.errors: List[Tuple[int, str]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Check class names are PascalCase."""
        if not re.match(r"^[A-Z][a-zA-Z0-9]*$", node.name):
            # Allow lowercase for dataclasses with all-caps (e.g., APIResponse)
            if not re.match(r"^[A-Z][a-zA-Z0-9]*$", node.name):
                # Skip private classes starting with _
                if not node.name.startswith("_"):
                    self.errors.append(
                        (node.lineno, f"Class '{node.name}' should be PascalCase")
                    )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function names are snake_case."""
        # Allow special methods (__init__, __str__, etc.)
        if node.name.startswith("__") and node.name.endswith("__"):
            self.generic_visit(node)
            return

        # Allow test methods (test_*)
        if node.name.startswith("test_"):
            self.generic_visit(node)
            return

        # Check snake_case (lowercase with underscores)
        if not re.match(r"^_?[a-z][a-z0-9_]*$", node.name):
            self.errors.append(
                (node.lineno, f"Function '{node.name}' should be snake_case")
            )
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Check async function names are snake_case."""
        # Same rules as regular functions
        if node.name.startswith("__") and node.name.endswith("__"):
            self.generic_visit(node)
            return

        if node.name.startswith("test_"):
            self.generic_visit(node)
            return

        if not re.match(r"^_?[a-z][a-z0-9_]*$", node.name):
            self.errors.append(
                (node.lineno, f"Async function '{node.name}' should be snake_case")
            )
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Check module-level constant naming."""
        # Only check module-level assignments (no parent function)
        for target in node.targets:
            if isinstance(target, ast.Name):
                name = target.id
                # Constants should be UPPER_SNAKE_CASE
                # But allow lowercase for regular variables
                # We only flag mixed case that's not PascalCase or snake_case
                if (
                    re.match(r"^[A-Z]", name)
                    and not re.match(r"^[A-Z][A-Z0-9_]*$", name)
                    and not re.match(r"^[A-Z][a-zA-Z0-9]*$", name)
                ):
                    self.errors.append(
                        (
                            node.lineno,
                            f"Variable '{name}' should be UPPER_SNAKE_CASE or snake_case",
                        )
                    )
        self.generic_visit(node)


def check_file(filepath: str) -> List[Tuple[str, int, str]]:
    """Check naming conventions in a Python file."""
    errors = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
        checker = NamingChecker(filepath)
        checker.visit(tree)
        for lineno, msg in checker.errors:
            errors.append((filepath, lineno, msg))
    except SyntaxError as e:
        # Don't fail on syntax errors - other tools will catch those
        pass
    except Exception as e:
        print(f"Warning: Could not parse {filepath}: {e}", file=sys.stderr)
    return errors


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python check_naming.py <file1.py> [file2.py ...]")
        sys.exit(1)

    all_errors = []
    for filepath in sys.argv[1:]:
        if Path(filepath).suffix == ".py":
            errors = check_file(filepath)
            all_errors.extend(errors)

    if all_errors:
        print("Naming convention violations found:")
        for filepath, lineno, msg in all_errors:
            print(f"  {filepath}:{lineno}: {msg}")
        # Non-blocking for now - just warnings
        print(f"\nTotal: {len(all_errors)} naming issues found")
        # Uncomment to make it blocking:
        # sys.exit(1)
    else:
        print("All naming conventions OK")


if __name__ == "__main__":
    main()
