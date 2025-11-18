#!/usr/bin/env python3
"""Fix escaped triple quotes in Python files."""

from pathlib import Path

BASE_DIR = Path("C:/Users/Klaus Pommer/OneDrive - Pommer IT-Consulting GmbH/99_Studium_Klaus/AEGIS_Rag")
SRC_DIR = BASE_DIR / "src"

def fix_file(file_path: Path) -> bool:
    """Fix escaped triple quotes in a single file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Fix escaped triple quotes
        content = content.replace('\\"\\"\\"', '"""')
        content = content.replace("\\'\\'\\'", "'''")

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
    print("Fixing escaped triple quotes...")
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
