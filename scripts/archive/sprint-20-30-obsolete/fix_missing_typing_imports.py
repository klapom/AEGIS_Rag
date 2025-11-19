#!/usr/bin/env python3
"""Fix missing typing imports (Dict, List, Set, Any) in Python files."""

import re
from pathlib import Path

BASE_DIR = Path("C:/Users/Klaus Pommer/OneDrive - Pommer IT-Consulting GmbH/99_Studium_Klaus/AEGIS_Rag")
SRC_DIR = BASE_DIR / "src"


def needs_typing_import(content: str, type_name: str) -> bool:
    """Check if a type is used but not imported."""
    # Check if type is used
    if f"{type_name}[" not in content and f", {type_name}" not in content:
        return False
    # Check if already imported
    if f"from typing import" in content and type_name in content[:content.find("\nclass ") if "\nclass " in content else 1000]:
        return True  # Check more carefully
    return True


def add_typing_imports(content: str) -> str:
    """Add missing typing imports."""
    # Detect which types are used
    types_used = set()
    if "Dict[" in content or ": Dict" in content or "-> Dict" in content:
        types_used.add("Dict")
    if "List[" in content or ": List" in content or "-> List" in content:
        types_used.add("List")
    if "Set[" in content or ": Set" in content or "-> Set" in content:
        types_used.add("Set")
    if ": Any" in content or "-> Any" in content or "[Any" in content:
        types_used.add("Any")
    if "timezone.utc" in content:
        types_used.add("timezone")

    if not types_used:
        return content

    # Check existing imports
    lines = content.split("\n")
    typing_import_line = None
    timezone_import_line = None

    for i, line in enumerate(lines):
        if line.startswith("from typing import"):
            typing_import_line = i
        if line.startswith("from datetime import") and "timezone" in line:
            timezone_import_line = i

    # Handle timezone separately
    if "timezone" in types_used:
        types_used.remove("timezone")
        if timezone_import_line is None:
            # Find datetime import line
            for i, line in enumerate(lines):
                if line.startswith("from datetime import"):
                    if "timezone" not in line:
                        lines[i] = line.rstrip() + ", timezone"
                    timezone_import_line = i
                    break
            if timezone_import_line is None:
                # Add new import after other imports
                import_idx = 0
                for i, line in enumerate(lines):
                    if line.startswith("import ") or line.startswith("from "):
                        import_idx = i + 1
                lines.insert(import_idx, "from datetime import timezone")

    # Handle typing imports
    if types_used:
        if typing_import_line is not None:
            # Update existing import
            existing_imports = lines[typing_import_line]
            for type_name in types_used:
                if type_name not in existing_imports:
                    # Add to import line
                    if existing_imports.endswith(")"):
                        # Multiline import
                        lines[typing_import_line] = existing_imports[:-1] + f", {type_name})"
                    else:
                        lines[typing_import_line] = existing_imports.rstrip() + f", {type_name}"
        else:
            # Add new typing import
            new_import = f"from typing import {', '.join(sorted(types_used))}"
            # Find where to insert (after other imports)
            import_idx = 0
            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from "):
                    import_idx = i + 1
            lines.insert(import_idx, new_import)

    return "\n".join(lines)


def fix_file(file_path: Path) -> bool:
    """Fix missing typing imports in a single file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content
        content = add_typing_imports(content)

        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main execution."""
    print("Fixing missing typing imports...")
    print(f"Source directory: {SRC_DIR}\n")

    # Get all Python files
    python_files = list(SRC_DIR.rglob("*.py"))
    print(f"Found {len(python_files)} Python files\n")

    total_fixed = 0
    for file_path in python_files:
        if fix_file(file_path):
            total_fixed += 1
            print(f"[OK] Fixed {file_path.relative_to(BASE_DIR)}")

    print(f"\nCompleted! Fixed {total_fixed} files.")


if __name__ == "__main__":
    main()
