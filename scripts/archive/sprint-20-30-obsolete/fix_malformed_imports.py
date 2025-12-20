#!/usr/bin/env python3
"""Fix malformed imports where 'from typing import' was inserted incorrectly."""

import re
from pathlib import Path

BASE_DIR = Path(
    "C:/Users/Klaus Pommer/OneDrive - Pommer IT-Consulting GmbH/99_Studium_Klaus/AEGIS_Rag"
)
SRC_DIR = BASE_DIR / "src"


def fix_malformed_imports(content: str) -> str:
    """Fix imports where 'from typing import X' was inserted in middle of other imports."""
    # Pattern: from X import (\nfrom typing import Y\n    Z,
    pattern = r"(from [^\n]+ import \()\nfrom typing import ([A-Za-z, ]+)\n(\s+)"

    # Find all occurrences
    matches = list(re.finditer(pattern, content))

    if not matches:
        return content

    # Extract typing imports and remove them from wrong position
    typing_imports = set()
    for match in matches:
        imports = match.group(2).split(", ")
        typing_imports.update(imports)

    # Remove malformed imports
    content = re.sub(pattern, r"\1\n\3", content)

    # Add typing imports at correct location (after first import block)
    if typing_imports:
        typing_import_line = f"from typing import {', '.join(sorted(typing_imports))}"

        # Find first import block
        lines = content.split("\n")
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("from pathlib import") or line.startswith("from datetime import"):
                insert_idx = i + 1
                break

        # Check if typing import already exists
        has_typing_import = any("from typing import" in line for line in lines[:20])

        if not has_typing_import:
            lines.insert(insert_idx, typing_import_line)
            content = "\n".join(lines)

    return content


def fix_file(file_path: Path) -> bool:
    """Fix malformed imports in a single file."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        original_content = content
        content = fix_malformed_imports(content)

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
    print("Fixing malformed imports...")
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
