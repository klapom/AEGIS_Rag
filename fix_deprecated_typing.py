"""Fix deprecated typing imports (Dict, List, Set) across all files.

This script:
1. Removes Dict, List, Set from typing imports
2. Replaces Dict[...] with dict[...]
3. Replaces List[...] with list[...]
4. Replaces Set[...] with set[...]
"""

import re
from pathlib import Path

# Files to fix
FILES_TO_FIX = [
    "src/api/routers/graph_viz.py",
    "src/api/v1/annotations.py",
    "src/api/v1/chat.py",
    "src/api/v1/health.py",
    "src/api/v1/memory.py",
    "src/api/v1/retrieval.py",
    "src/components/graph_rag/analytics_engine.py",
    "src/components/graph_rag/batch_executor.py",
    "src/components/graph_rag/community_search.py",
    "src/components/graph_rag/dual_level_search.py",
    "src/components/graph_rag/evolution_tracker.py",
    "src/components/graph_rag/extraction_factory.py",
    "src/components/graph_rag/extraction_service.py",
    "src/components/graph_rag/lightrag_wrapper.py",
    "src/components/graph_rag/neo4j_client.py",
    "src/components/graph_rag/query_builder.py",
    "src/components/graph_rag/query_cache.py",
    "src/components/graph_rag/relation_extractor.py",
    "src/components/graph_rag/semantic_deduplicator.py",
    "src/components/graph_rag/temporal_query_builder.py",
    "src/components/graph_rag/version_manager.py",
    "src/components/graph_rag/visualization_export.py",
    "src/components/ingestion/docling_client.py",
    "src/components/ingestion/format_router.py",
    "src/components/llm_proxy/config.py",
    "src/components/mcp/client.py",
    "src/components/mcp/client_stub.py",
    "src/components/mcp/models.py",
    "src/components/mcp/result_parser.py",
    "src/components/mcp/tool_executor.py",
    "src/components/mcp/types.py",
    "src/components/memory/consolidation.py",
    "src/components/memory/enhanced_router.py",
    "src/components/memory/graphiti_wrapper.py",
    "src/components/memory/memory_router.py",
    "src/components/memory/models.py",
    "src/components/memory/monitoring.py",
    "src/components/memory/redis_manager.py",
    "src/components/memory/redis_memory.py",
    "src/components/memory/routing_strategy.py",
    "src/components/memory/temporal_queries.py",
    "src/components/memory/unified_api.py",
    "src/components/profiling/conversation_archiver.py",
    "src/components/retrieval/chunking.py",
    "src/components/shared/embedding_service.py",
    "src/components/vector_search/bm25_search.py",
    "src/components/vector_search/hybrid_search.py",
    "src/components/vector_search/ingestion.py",
    "src/components/vector_search/qdrant_client.py",
    "src/core/chunk.py",
    "src/core/exceptions.py",
    "src/core/models.py",
    "src/evaluation/custom_metrics.py",
    "src/evaluation/ragas_eval.py",
    "src/models/profiling.py",
    "src/ui/gradio_app.py",
    "src/utils/fusion.py",
]


def fix_file(file_path: Path) -> tuple[bool, int]:
    """Fix deprecated typing imports in a single file.

    Returns:
        (changed, replacements_made)
    """
    if not file_path.exists():
        print(f"SKIP: {file_path} (not found)")
        return False, 0

    content = file_path.read_text(encoding="utf-8")
    original_content = content
    replacements = 0

    # Step 1: Remove Dict, List, Set from typing imports
    # Pattern: from typing import ... Dict ... List ... Set ...

    # Handle single-line imports
    def remove_deprecated_from_import(match):
        nonlocal replacements
        imports = match.group(1)

        # Split by comma and filter out Dict, List, Set
        import_items = [item.strip() for item in imports.split(',')]
        filtered_items = [
            item for item in import_items
            if not re.match(r'\b(Dict|List|Set)\b', item)
        ]

        # Count removed items
        removed_count = len(import_items) - len(filtered_items)
        if removed_count > 0:
            replacements += removed_count

        # If all items removed, remove the entire import line
        if not filtered_items:
            return ''

        # Return filtered import
        return f"from typing import {', '.join(filtered_items)}"

    # Replace import lines
    content = re.sub(
        r'from typing import ([^\n]+)',
        remove_deprecated_from_import,
        content
    )

    # Remove empty lines left by removed imports
    content = re.sub(r'\n\n\n+', '\n\n', content)

    # Step 2: Replace Dict[...] with dict[...]
    content, dict_count = re.subn(r'\bDict\[', 'dict[', content)
    replacements += dict_count

    # Step 3: Replace List[...] with list[...]
    content, list_count = re.subn(r'\bList\[', 'list[', content)
    replacements += list_count

    # Step 4: Replace Set[...] with set[...]
    content, set_count = re.subn(r'\bSet\[', 'set[', content)
    replacements += set_count

    # Step 5: Replace standalone Dict/List/Set type hints (without brackets)
    # e.g., def foo() -> Dict:
    content, standalone_dict = re.subn(r'\bDict\b(?!\[)', 'dict', content)
    replacements += standalone_dict

    content, standalone_list = re.subn(r'\bList\b(?!\[)', 'list', content)
    replacements += standalone_list

    content, standalone_set = re.subn(r'\bSet\b(?!\[)', 'set', content)
    replacements += standalone_set

    # Write back if changed
    if content != original_content:
        file_path.write_text(content, encoding="utf-8")
        return True, replacements

    return False, 0


def main():
    """Fix all files."""
    total_files = 0
    total_changed = 0
    total_replacements = 0

    for file_str in FILES_TO_FIX:
        file_path = Path(file_str)
        changed, replacements = fix_file(file_path)

        total_files += 1
        if changed:
            total_changed += 1
            total_replacements += replacements
            print(f"FIXED: {file_path} ({replacements} replacements)")
        else:
            print(f"OK: {file_path} (no changes needed)")

    print(f"\nSummary:")
    print(f"  Total files: {total_files}")
    print(f"  Files changed: {total_changed}")
    print(f"  Total replacements: {total_replacements}")


if __name__ == "__main__":
    main()
