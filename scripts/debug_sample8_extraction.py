#!/usr/bin/env python3
"""Debug Sample 8 (Q146) extraction issue.

This script reproduces the 0-entity extraction issue for Sample 8 (Q146)
and captures the raw LLM response for debugging.

Usage:
    poetry run python scripts/debug_sample8_extraction.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.components.graph_rag.extraction_benchmark import (
    UNIFIED_EXTRACTION_PROMPT,
    ExtractionBenchmark,
    ExtractionStrategy,
)
from src.components.llm_proxy import get_aegis_llm_proxy
from src.components.llm_proxy.models import (
    Complexity,
    LLMTask,
    QualityRequirement,
    TaskType,
)


def load_sample_8():
    """Load Sample 8 (Q146) from WikiQA dataset."""
    try:
        from datasets import load_dataset
        ds = load_dataset('explodinggradients/ragas-wikiqa', split='train')

        # Sample 8 is at index 7*step where step = len(ds)//30
        # But we need to find Q146 specifically
        for i, item in enumerate(ds):
            qid = item.get('question_id', f'Q{i}')
            if qid == 'Q146' or i == 7:  # Index 7 or Q146
                contexts = item.get('context', [])
                if isinstance(contexts, list):
                    context_text = "\n\n".join(contexts)
                else:
                    context_text = str(contexts)

                return {
                    'sample_id': qid,
                    'question': item.get('question', ''),
                    'context': context_text,
                    'index': i,
                }

        # Fallback: get sample at index 7
        item = ds[7]
        contexts = item.get('context', [])
        if isinstance(contexts, list):
            context_text = "\n\n".join(contexts)
        else:
            context_text = str(contexts)

        return {
            'sample_id': item.get('question_id', 'Q7'),
            'question': item.get('question', ''),
            'context': context_text,
            'index': 7,
        }

    except Exception as e:
        print(f"Error loading dataset: {e}")
        return None


async def debug_extraction(sample: dict):
    """Run extraction with detailed debugging."""

    print("=" * 80)
    print("DEBUG: Sample 8 (Q146) Extraction")
    print("=" * 80)

    print("\n--- Sample Info ---")
    print(f"Sample ID: {sample['sample_id']}")
    print(f"Index: {sample['index']}")
    print(f"Question: {sample['question']}")
    print(f"Context length: {len(sample['context'])} chars")
    print(f"Context preview: {sample['context'][:500]}...")

    # Step 1: Test direct LLM call with UNIFIED prompt
    print("\n--- Step 1: Direct LLM Call (UNIFIED) ---")

    proxy = get_aegis_llm_proxy()
    prompt = UNIFIED_EXTRACTION_PROMPT.format(text=sample['context'])

    print(f"Prompt length: {len(prompt)} chars")

    task = LLMTask(
        task_type=TaskType.EXTRACTION,
        prompt=prompt,
        quality_requirement=QualityRequirement.HIGH,
        complexity=Complexity.HIGH,
        max_tokens=8192,  # Increased from 4096
        temperature=0.1,
        model_local="qwen3:32b",
    )

    print("Calling LLM...")
    response = await proxy.generate(task)

    print("\n--- Raw LLM Response ---")
    print(f"Response length: {len(response.content)} chars")
    print(f"Input tokens: {response.tokens_input}")
    print(f"Output tokens: {response.tokens_output}")
    print(f"\nFull response:\n{'-' * 40}")
    print(response.content)
    print(f"{'-' * 40}")

    # Step 2: Try to parse the response
    print("\n--- Step 2: JSON Parsing ---")

    cleaned = response.content.strip()

    # Remove markdown code blocks
    if "```" in cleaned:
        import re
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if match:
            cleaned = match.group(1).strip()
            print(f"Extracted from code block: {len(cleaned)} chars")

    # Try direct parsing
    try:
        data = json.loads(cleaned)
        print("Direct parse SUCCESS!")
        print(f"Entities: {len(data.get('entities', []))}")
        print(f"Relationships: {len(data.get('relationships', []))}")

        if data.get('entities'):
            print("\nFirst 5 entities:")
            for e in data['entities'][:5]:
                print(f"  - {e.get('name')} ({e.get('type')})")

    except json.JSONDecodeError as e:
        print(f"Direct parse FAILED: {e}")

        # Try extracting JSON object
        import re
        for pattern in [r"\{[\s\S]*\}", r"\[[\s\S]*\]"]:
            match = re.search(pattern, cleaned)
            if match:
                try:
                    data = json.loads(match.group(0))
                    print(f"Pattern match SUCCESS: {pattern}")
                    if isinstance(data, dict):
                        print(f"Entities: {len(data.get('entities', []))}")
                        print(f"Relationships: {len(data.get('relationships', []))}")
                    break
                except json.JSONDecodeError:
                    print(f"Pattern match FAILED: {pattern}")
                    continue

    # Step 3: Test with ExtractionBenchmark
    print("\n--- Step 3: ExtractionBenchmark Test ---")

    benchmark = ExtractionBenchmark(max_tokens=8192)

    try:
        result = await benchmark.extract(
            text=sample['context'],
            chunk_id=sample['sample_id'],
            document_id=f"debug_{sample['sample_id']}",
            strategy=ExtractionStrategy.UNIFIED,
        )

        print("Extraction completed!")
        print(f"Entities: {result.metrics.entities_extracted}")
        print(f"Typed relations: {result.metrics.typed_relations_extracted}")
        print(f"Semantic relations: {result.metrics.semantic_relations_extracted}")
        print(f"Time: {result.metrics.total_time_ms:.0f}ms")
        print(f"Errors: {result.metrics.errors}")

        if result.entities:
            print(f"\nExtracted entities ({len(result.entities)}):")
            for e in result.entities[:10]:
                print(f"  - {e.name} ({e.type}): {e.description[:50]}...")

        if result.typed_relationships:
            print(f"\nExtracted relationships ({len(result.typed_relationships)}):")
            for r in result.typed_relationships[:10]:
                print(f"  - {r.source} --[{r.type}]--> {r.target}")

    except Exception as e:
        print(f"Extraction FAILED: {e}")
        import traceback
        traceback.print_exc()

    # Step 4: Test with SEQUENTIAL for comparison
    print("\n--- Step 4: SEQUENTIAL Comparison ---")

    try:
        result_seq = await benchmark.extract(
            text=sample['context'],
            chunk_id=sample['sample_id'],
            document_id=f"debug_{sample['sample_id']}_seq",
            strategy=ExtractionStrategy.SEQUENTIAL,
        )

        print("SEQUENTIAL completed!")
        print(f"Entities: {result_seq.metrics.entities_extracted}")
        print(f"Typed relations: {result_seq.metrics.typed_relations_extracted}")
        print(f"Semantic relations: {result_seq.metrics.semantic_relations_extracted}")
        print(f"Time: {result_seq.metrics.total_time_ms:.0f}ms")

        if result_seq.entities:
            print(f"\nSEQUENTIAL entities ({len(result_seq.entities)}):")
            for e in result_seq.entities[:10]:
                print(f"  - {e.name} ({e.type})")

    except Exception as e:
        print(f"SEQUENTIAL FAILED: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main entry point."""
    sample = load_sample_8()

    if not sample:
        print("Failed to load sample!")
        return

    await debug_extraction(sample)


if __name__ == "__main__":
    asyncio.run(main())
