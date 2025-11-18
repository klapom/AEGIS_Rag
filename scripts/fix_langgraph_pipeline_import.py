#!/usr/bin/env python3
"""Fix the import issue in langgraph_pipeline.py"""

from pathlib import Path

file_path = Path("C:/Users/Klaus Pommer/OneDrive - Pommer IT-Consulting GmbH/99_Studium_Klaus/AEGIS_Rag/src/components/ingestion/langgraph_pipeline.py")

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix the malformed import
content = content.replace(
    "from src.components.ingestion.langgraph_nodes import (\nfrom typing import List\n    chunking_node,",
    "from src.components.ingestion.langgraph_nodes import (\n    chunking_node,"
)

# Add typing import at the top
if "from typing import List" not in content[:500]:
    # Insert after pathlib import
    content = content.replace(
        "from pathlib import Path\n\nimport structlog",
        "from pathlib import Path\nfrom typing import List\n\nimport structlog"
    )

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed langgraph_pipeline.py")
