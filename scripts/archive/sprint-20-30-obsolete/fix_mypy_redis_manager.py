#!/usr/bin/env python3
"""Script to systematically fix MyPy errors in redis_manager.py"""

import re

file_path = "C:/Users/Klaus Pommer/OneDrive - Pommer IT-Consulting GmbH/99_Studium_Klaus/AEGIS_Rag/src/components/memory/redis_manager.py"

with open(file_path, encoding="utf-8") as f:
    content = f.read()

# Fix 1: Add type narrowing check after initialize() for all self._client usages
# Pattern: await self.initialize() followed by self._client usage
# Solution: Add "if self._client is None: raise..." check

fixes = [
    # Fix MemoryError calls - add operation and reason parameters
    (
        r'raise MemoryError\(f"Failed to connect to Redis: \{e\}"\)',
        'raise MemoryError(operation="connect", reason=str(e))',
    ),
    (
        r'raise MemoryError\(f"Failed to store memory entry: \{e\}"\)',
        'raise MemoryError(operation="store", reason=str(e))',
    ),
    (
        r'raise MemoryError\(f"Failed to retrieve memory entry: \{e\}"\)',
        'raise MemoryError(operation="retrieve", reason=str(e))',
    ),
]

for pattern, replacement in fixes:
    content = re.sub(pattern, replacement, content)

# Add type narrowing checks after initialize() calls
# Find all "await self.initialize()" and add check on next non-empty line
lines = content.split("\n")
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    new_lines.append(line)

    # Check if this is an initialize() call
    if "await self.initialize()" in line and "def initialize" not in line:
        # Check if next line already has a type narrowing check
        if i + 1 < len(lines):
            next_line = lines[i + 1]
            if "if self._client is None:" not in next_line and next_line.strip():
                # Add type narrowing check
                indent = len(line) - len(line.lstrip())
                new_lines.append(" " * indent + "")  # Empty line
                new_lines.append(" " * indent + "if self._client is None:")
                new_lines.append(
                    " " * (indent + 4)
                    + 'raise MemoryError(operation="redis_operation", reason="client_not_initialized")'
                )

    i += 1

content = "\n".join(new_lines)

# Write back
with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Fixed {file_path}")
