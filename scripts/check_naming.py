#!/usr/bin/env python3
"""
Naming Convention Checker
Validates Python code against AEGIS RAG naming conventions.
"""
import re
import sys
from pathlib import Path
from typing import List, Tuple


class NamingChecker:
    """Checks code against naming conventions."""

    # Naming patterns
    PATTERNS = {
        'class': re.compile(r'^[A-Z][A-Za-z0-9]*(?:Service|Repository|Controller|Model|Config|Agent|Processor|Handler|Manager|Builder|Factory|Adapter|Strategy|Validator|Error|Exception|Evaluator)?$'),
        'function': re.compile(r'^[a-z]+(?:_[a-z]+)*$'),
        'constant': re.compile(r'^[A-Z]+(?:_[A-Z]+)*$'),
        'variable': re.compile(r'^[a-z]+(?:_[a-z]+)*$'),
    }

    # File naming patterns
    FILE_PATTERNS = {
        'service': re.compile(r'^[a-z]+(?:_[a-z]+)*_service\.py$'),
        'repository': re.compile(r'^[a-z]+(?:_[a-z]+)*_repository\.py$'),
        'controller': re.compile(r'^[a-z]+(?:_[a-z]+)*_controller\.py$'),
        'model': re.compile(r'^[a-z]+(?:_[a-z]+)*(?:_model)?\.py$'),
        'test': re.compile(r'^test_[a-z]+(?:_[a-z]+)*\.py$'),
        'config': re.compile(r'^[a-z]+(?:_[a-z]+)*_config\.py$'),
        'util': re.compile(r'^[a-z]+(?:_[a-z]+)*_utils?\.py$'),
    }

    def __init__(self):
        self.errors: List[Tuple[str, int, str]] = []

    def check_file(self, filepath: Path) -> bool:
        """Check a single Python file for naming violations."""
        if not filepath.suffix == '.py':
            return True

        # Check filename
        if not self._check_filename(filepath):
            self.errors.append((str(filepath), 0, f"Invalid filename: {filepath.name}"))

        # Check content
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                self._check_content(filepath, lines)
        except Exception as e:
            print(f"Error reading {filepath}: {e}", file=sys.stderr)
            return False

        return len(self.errors) == 0

    def _check_filename(self, filepath: Path) -> bool:
        """Check if filename follows conventions."""
        name = filepath.name

        # Skip __init__.py and __main__.py
        if name.startswith('__') and name.endswith('__.py'):
            return True

        # Check against known patterns
        for pattern in self.FILE_PATTERNS.values():
            if pattern.match(name):
                return True

        # Generic snake_case check
        if re.match(r'^[a-z]+(?:_[a-z]+)*\.py$', name):
            return True

        return False

    def _check_content(self, filepath: Path, lines: List[str]):
        """Check file content for naming violations."""
        for line_no, line in enumerate(lines, 1):
            line = line.strip()

            # Check class definitions
            if line.startswith('class '):
                match = re.match(r'class\s+(\w+)', line)
                if match:
                    class_name = match.group(1)
                    if not self.PATTERNS['class'].match(class_name):
                        self.errors.append((
                            str(filepath),
                            line_no,
                            f"Class name '{class_name}' doesn't follow PascalCase convention"
                        ))

            # Check function definitions
            elif line.startswith('def '):
                match = re.match(r'def\s+(\w+)', line)
                if match:
                    func_name = match.group(1)
                    # Skip magic methods and private methods
                    if not func_name.startswith('_'):
                        if not self.PATTERNS['function'].match(func_name):
                            self.errors.append((
                                str(filepath),
                                line_no,
                                f"Function name '{func_name}' doesn't follow snake_case convention"
                            ))

            # Check constants (heuristic: all caps assignments at module level)
            elif '=' in line and line.split('=')[0].strip().isupper():
                const_name = line.split('=')[0].strip()
                if not self.PATTERNS['constant'].match(const_name):
                    self.errors.append((
                        str(filepath),
                        line_no,
                        f"Constant name '{const_name}' doesn't follow UPPER_SNAKE_CASE convention"
                    ))

    def print_errors(self):
        """Print all collected errors."""
        if not self.errors:
            return

        print("\n❌ Naming Convention Violations Found:\n")
        for filepath, line_no, message in self.errors:
            if line_no > 0:
                print(f"  {filepath}:{line_no}")
            else:
                print(f"  {filepath}")
            print(f"    {message}\n")

        print(f"Total violations: {len(self.errors)}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: check_naming.py <file_or_directory>...")
        sys.exit(1)

    checker = NamingChecker()
    all_ok = True

    for path_str in sys.argv[1:]:
        path = Path(path_str)

        if path.is_file():
            if not checker.check_file(path):
                all_ok = False
        elif path.is_dir():
            for py_file in path.rglob('*.py'):
                if not checker.check_file(py_file):
                    all_ok = False
        else:
            print(f"Warning: {path} not found", file=sys.stderr)

    checker.print_errors()

    if all_ok:
        print("✅ All naming conventions are followed!")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
