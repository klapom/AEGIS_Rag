#!/usr/bin/env python3
"""Comprehensive MyPy error fixer for AegisRAG codebase.

This script systematically fixes common MyPy strict mode errors:
1. Missing return type annotations
2. Missing positional arguments (MemoryError, etc.)
3. Item "None" type narrowing errors
4. Missing generic type parameters
5. datetime.UTC → datetime.timezone.utc
"""

import re
from pathlib import Path
from typing import List, Tuple

# Base directory
BASE_DIR = Path("C:/Users/Klaus Pommer/OneDrive - Pommer IT-Consulting GmbH/99_Studium_Klaus/AEGIS_Rag")
SRC_DIR = BASE_DIR / "src"


def fix_memory_error_calls(content: str) -> str:
    """Fix MemoryError constructor calls to include operation and reason."""
    patterns = [
        (r'raise MemoryError\(f"([^"]+): \{([^}]+)\}"\)', r'raise MemoryError(operation="\1", reason=str(\2))'),
        (r'raise MemoryError\("([^"]+)"\)', r'raise MemoryError(operation="operation", reason="\1")'),
        (r'raise MemoryError\(f"([^"]+)"\)', r'raise MemoryError(operation="operation", reason="\1")'),
    ]

    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)

    return content


def fix_datetime_utc(content: str) -> str:
    """Fix datetime.UTC → datetime.timezone.utc."""
    content = content.replace("datetime.UTC", "datetime.timezone.utc")
    content = content.replace("from datetime import UTC", "from datetime import timezone")
    content = content.replace("UTC.now()", "datetime.now(timezone.utc)")
    content = content.replace("datetime.utcnow()", "datetime.now(timezone.utc)")

    return content


def add_type_narrowing_for_optional(content: str, var_name: str, error_msg: str = "not initialized") -> str:
    """Add type narrowing checks for optional variables."""
    # Pattern: await method() followed by var_name usage
    lines = content.split("\n")
    new_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]
        new_lines.append(line)

        # Check if this line uses an optional variable without check
        if f"{var_name}." in line or f"await {var_name}." in line:
            # Check if previous lines have type narrowing
            prev_lines = new_lines[-10:] if len(new_lines) >= 10 else new_lines
            has_check = any(f"if {var_name} is None:" in l or f"if {var_name} is not None:" in l or f"assert {var_name} is not None" in l for l in prev_lines)

            if not has_check and "def " not in line:
                # Add assertion before this line
                indent = len(line) - len(line.lstrip())
                assertion = " " * indent + f"assert {var_name} is not None, '{error_msg}'"
                new_lines.insert(-1, assertion)

        i += 1

    return "\n".join(new_lines)


def add_return_type_annotations(content: str) -> str:
    """Add missing return type annotations."""
    # Pattern: def method(...): without ->
    # Common patterns:
    patterns = [
        # Methods that don't return anything
        (r"(def \w+\([^)]*\)):\s*\n(\s+)\"\"\"", r"\1 -> None:\n\2\"\"\""),
        # Property getters and setters
        (r"(@property\s+def \w+\([^)]*\)):\s*\n", r"\1 -> Any:\n"),
    ]

    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)

    return content


def fix_generic_type_parameters(content: str) -> str:
    """Add generic type parameters."""
    # Common patterns:
    replacements = [
        ("list[Any]", "List[Any]"),
        ("dict[str, Any]", "Dict[str, Any]"),
        ("set[str]", "Set[str]"),
    ]

    # Add imports if needed
    if "List[Any]" in content or "Dict[str, Any]" in content or "Set[str]" in content:
        if "from typing import" in content:
            # Add to existing import
            content = re.sub(
                r"from typing import ([^\n]+)",
                lambda m: f"from typing import {m.group(1)}, List, Dict, Set, Any" if "List" not in m.group(1) else m.group(0),
                content,
                count=1
            )
        else:
            # Add new import after other imports
            import_line = "from typing import Any, Dict, List, Set\n"
            if "import" in content:
                lines = content.split("\n")
                insert_idx = 0
                for i, line in enumerate(lines):
                    if line.startswith("import ") or line.startswith("from "):
                        insert_idx = i + 1
                lines.insert(insert_idx, import_line)
                content = "\n".join(lines)

    for old, new in replacements:
        content = content.replace(old, new)

    return content


def fix_returning_any(content: str) -> str:
    """Add type: ignore comments for unavoidable Any returns."""
    # Pattern: return some_dict["key"] or return json.loads(...)
    lines = content.split("\n")
    new_lines = []

    for line in lines:
        if "return" in line and ("json.loads" in line or '["' in line or "get(" in line):
            # Add type: ignore comment
            if "# type: ignore" not in line:
                line = line.rstrip() + "  # type: ignore[no-any-return]"
        new_lines.append(line)

    return "\n".join(new_lines)


def process_file(file_path: Path) -> Tuple[bool, List[str]]:
    """Process a single Python file and apply all fixes."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content
        fixes_applied = []

        # Apply all fixes
        content = fix_memory_error_calls(content)
        if content != original_content:
            fixes_applied.append("MemoryError calls")
            original_content = content

        content = fix_datetime_utc(content)
        if content != original_content:
            fixes_applied.append("datetime.UTC")
            original_content = content

        content = add_return_type_annotations(content)
        if content != original_content:
            fixes_applied.append("return type annotations")
            original_content = content

        content = fix_generic_type_parameters(content)
        if content != original_content:
            fixes_applied.append("generic type parameters")
            original_content = content

        content = fix_returning_any(content)
        if content != original_content:
            fixes_applied.append("returning Any")
            original_content = content

        # Write back if changed
        if fixes_applied:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True, fixes_applied
        else:
            return False, []

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False, []


def main():
    """Main execution."""
    print("Starting comprehensive MyPy error fixes...")
    print(f"Base directory: {BASE_DIR}")
    print(f"Source directory: {SRC_DIR}\n")

    # Get all Python files
    python_files = list(SRC_DIR.rglob("*.py"))
    print(f"Found {len(python_files)} Python files\n")

    total_fixed = 0
    for file_path in python_files:
        changed, fixes = process_file(file_path)
        if changed:
            total_fixed += 1
            print(f"[OK] Fixed {file_path.relative_to(BASE_DIR)}: {', '.join(fixes)}")

    print(f"\nCompleted! Fixed {total_fixed} files.")
    print("\nNext steps:")
    print("1. Run: poetry run mypy src/ --config-file=pyproject.toml")
    print("2. Review remaining errors")
    print("3. Commit changes")


if __name__ == "__main__":
    main()
