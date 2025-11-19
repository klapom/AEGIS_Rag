"""Script to batch-fix VectorSearchError calls with missing arguments."""

import re
from pathlib import Path

# Files to fix
FILES_TO_FIX = [
    "src/components/profiling/conversation_archiver.py",
    "src/agents/vector_search_agent.py",
]


def fix_file(file_path: Path) -> int:
    """Fix VectorSearchError calls in a file.

    Returns:
        Number of fixes made
    """
    content = file_path.read_text(encoding="utf-8")
    original_content = content

    # Pattern 1: raise VectorSearchError(f"message: {e}") from e
    # Replace with: raise VectorSearchError(query="", reason=f"message: {e}") from e
    pattern1 = r'raise VectorSearchError\(f"([^"]+)"\) from e'
    replacement1 = r'raise VectorSearchError(query="", reason=f"\1") from e'
    content = re.sub(pattern1, replacement1, content)

    # Pattern 2: raise VectorSearchError("message")
    # Replace with: raise VectorSearchError(query="", reason="message")
    pattern2 = r'raise VectorSearchError\("([^"]+)"\)(?! from)'
    replacement2 = r'raise VectorSearchError(query="", reason="\1")'
    content = re.sub(pattern2, replacement2, content)

    # Pattern 3: raise VectorSearchError(query, f"message: {e}") from e
    # Replace with: raise VectorSearchError(query=query, reason=f"message: {e}") from e
    pattern3 = r'raise VectorSearchError\((\w+), f"([^"]+)"\) from e'
    replacement3 = r'raise VectorSearchError(query=\1, reason=f"\2") from e'
    content = re.sub(pattern3, replacement3, content)

    if content != original_content:
        file_path.write_text(content, encoding="utf-8")
        fixes = content.count("VectorSearchError(query=") - original_content.count(
            "VectorSearchError(query="
        )
        return fixes
    return 0


def main() -> None:
    """Fix all files."""
    total_fixes = 0

    for file_path_str in FILES_TO_FIX:
        file_path = Path(file_path_str)
        if not file_path.exists():
            print(f"SKIP (not found): {file_path}")
            continue

        fixes = fix_file(file_path)
        total_fixes += fixes
        status = "FIXED" if fixes > 0 else "OK"
        print(f"{status}: {file_path} ({fixes} fixes)")

    print(f"\nTotal fixes: {total_fixes}")


if __name__ == "__main__":
    main()
