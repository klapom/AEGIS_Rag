#!/usr/bin/env python3
"""Debug deduplication initialization."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import get_settings
from src.components.graph_rag.semantic_deduplicator import create_deduplicator_from_config

# Get settings
settings = get_settings()

print("=" * 80)
print("DEBUG: Semantic Deduplication Configuration")
print("=" * 80)
print(f"enable_semantic_dedup: {getattr(settings, 'enable_semantic_dedup', 'NOT_FOUND')}")
print(f"semantic_dedup_model: {getattr(settings, 'semantic_dedup_model', 'NOT_FOUND')}")
print(f"semantic_dedup_threshold: {getattr(settings, 'semantic_dedup_threshold', 'NOT_FOUND')}")
print(f"semantic_dedup_device: {getattr(settings, 'semantic_dedup_device', 'NOT_FOUND')}")
print()

# Try to create deduplicator
print("Attempting to create deduplicator...")
try:
    dedup = create_deduplicator_from_config(settings)
    if dedup is None:
        print("RESULT: Deduplicator is None (disabled)")
    else:
        print(f"RESULT: Deduplicator created successfully: {type(dedup).__name__}")
        print(f"        Model: {dedup.model}")
        print(f"        Threshold: {dedup.threshold}")
        print(f"        Device: {dedup.device}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback

    traceback.print_exc()

print("=" * 80)
