"""Remove unused type:ignore comments reported by MyPy.

This script reads MyPy output and removes unused # type: ignore comments.
"""

import re
import sys
from pathlib import Path


def remove_unused_ignores(mypy_output_file: str, dry_run: bool = False) -> None:
    """Remove unused type:ignore comments from files."""
    # Read MyPy output
    output_path = Path(mypy_output_file)
    if not output_path.exists():
        print(f"Error: {mypy_output_file} not found")
        return

    with open(output_path) as f:
        lines = f.readlines()

    # Parse errors
    unused_ignores = []
    pattern = r'(.+):(\d+): error: Unused "type: ignore" comment'

    for line in lines:
        match = re.match(pattern, line)
        if match:
            file_path = match.group(1)
            line_num = int(match.group(2))
            unused_ignores.append((file_path, line_num))

    print(f"Found {len(unused_ignores)} unused type:ignore comments")

    # Group by file
    files_to_fix = {}
    for file_path, line_num in unused_ignores:
        if file_path not in files_to_fix:
            files_to_fix[file_path] = []
        files_to_fix[file_path].append(line_num)

    # Fix each file
    for file_path, line_numbers in files_to_fix.items():
        fix_file(file_path, line_numbers, dry_run)


def fix_file(file_path: str, line_numbers: list[int], dry_run: bool) -> None:
    """Remove type:ignore comments from specific lines."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Skipping {file_path} (not found)")
        return

    modified = False
    for line_num in sorted(line_numbers, reverse=True):  # Reverse to keep line numbers valid
        idx = line_num - 1  # Convert to 0-indexed
        if idx < len(lines):
            original = lines[idx]
            # Remove # type: ignore[...] or  # type: ignore
            cleaned = re.sub(r"\s*#\s*type:\s*ignore(?:\[[^\]]+\])?", "", original)
            if cleaned != original:
                lines[idx] = cleaned
                modified = True
                print(f"  Line {line_num}: Removed type:ignore")

    if modified and not dry_run:
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"✓ Fixed {file_path}")
    elif modified:
        print(f"[DRY RUN] Would fix {file_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python remove_unused_ignores.py <mypy_output_file> [--dry-run]")
        sys.exit(1)

    mypy_file = sys.argv[1]
    dry_run = "--dry-run" in sys.argv

    remove_unused_ignores(mypy_file, dry_run)
