#!/usr/bin/env python3
"""Check that commit messages follow Conventional Commits format.

Expected format: <type>(<scope>): <subject>
Types: feat, fix, docs, style, refactor, test, chore, perf, ci

Allows merge commits and fixup!/squash! prefixes.
"""

import re
import sys
from pathlib import Path

TYPES = {"feat", "fix", "docs", "style", "refactor", "test", "chore", "perf", "ci"}
PATTERN = re.compile(
    r"^(?P<type>" + "|".join(TYPES) + r")"
    r"(\([\w./-]+\))?"  # optional scope
    r"!?"  # optional breaking change indicator
    r": "  # colon + space separator
    r".+"  # subject (non-empty)
)


def main() -> int:
    commit_msg_file = Path(".git/COMMIT_EDITMSG")
    # Also accept the file as first argument if provided
    if len(sys.argv) > 1:
        commit_msg_file = Path(sys.argv[1])

    if not commit_msg_file.exists():
        print(f"Commit message file not found: {commit_msg_file}")
        return 1

    msg = commit_msg_file.read_text(encoding="utf-8").strip()
    first_line = msg.split("\n")[0]

    # Allow merge commits
    if first_line.startswith("Merge "):
        return 0

    # Allow fixup/squash commits (for interactive rebase)
    if first_line.startswith(("fixup! ", "squash! ", "amend! ")):
        return 0

    if PATTERN.match(first_line):
        return 0

    types_str = ", ".join(sorted(TYPES))
    print(f"\nCommit message does not follow Conventional Commits format.")
    print(f"  Expected: <type>(<scope>): <subject>")
    print(f"  Types:    {types_str}")
    print(f"  Got:      {first_line}")
    print()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
