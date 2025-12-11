#!/usr/bin/env python3
"""
Smart Chunk-Size Benchmark using HotPotQA fullwiki dataset.

Strategy:
- 500-4000 chunk sizes: Test with 5874 and 6787 char samples (2 samples)
- 10000 chunk size: Test with ~16000 char combined sample (1 sample)

This reduces combinatorics while still testing all chunk sizes meaningfully.
"""
import json
import time
import requests
import argparse
import sys
from datetime import datetime
from datasets import load_dataset


# Entity extraction prompt
ENTITY_PROMPT = """Extract all named entities from the following text. Return ONLY a valid JSON array.

Each entity should have:
- "name": The entity name as it appears in the text
- "type": One of: PERSON, ORGANIZATION, LOCATION, PRODUCT, EVENT, CONCEPT, TECHNOLOGY
- "description": Brief description (1 sentence)

Text:
{text}

Return ONLY a JSON array like:
[
  {{"name": "Example", "type": "PERSON", "description": "A person mentioned"}}
]

JSON Output:"""

# Relationship extraction prompt
RELATION_PROMPT = """Extract relationships between entities from the text. Return ONLY a valid JSON array.

Each relationship should have:
- "source": Source entity name
- "target": Target entity name
- "type": Relationship type (e.g., LOCATED_IN, WORKS_FOR, PART_OF, FOUNDED_BY, CREATED)
- "description": Brief description

Text:
{text}

Entities found: {entities}

Return ONLY a JSON array like:
[
  {{"source": "Entity1", "target": "Entity2", "type": "WORKS_FOR", "description": "Entity1 works for Entity2"}}
]

JSON Output:"""


def load_smart_samples() -> dict:
    """Load samples optimized for chunk-size testing.

    Returns dict with:
    - 'medium': 2 samples with 5000-7000 chars for 500-4000 chunk testing
    - 'large': 1 combined sample with ~16000 chars for 10000 chunk testing
    """
    print("Loading samples from HotPotQA fullwiki...")
    sys.stdout.flush()
    ds = load_dataset('hotpot_qa', 'fullwiki', split='validation[:20]')

    all_samples = []
    for sample in ds:
        contexts = sample.get('context', {})
        if isinstance(contexts, dict):
            sentences = contexts.get('sentences', [])
            total_text = ' '.join([' '.join(s) if isinstance(s, list) else s for s in sentences])
        else:
            total_text = str(contexts)

        all_samples.append({
            'id': sample.get('id', f'sample_{len(all_samples)}'),
            'question': sample.get('question', ''),
            'answer': sample.get('answer', ''),
            'context': total_text,
            'context_length': len(total_text)
        })

    # Find 2 samples in 5000-7000 range for medium chunk testing
    medium_samples = sorted(
        [s for s in all_samples if 5000 <= s['context_length'] <= 7500],
        key=lambda x: x['context_length'],
        reverse=True
    )[:2]

    print(f"Found {len(medium_samples)} medium samples: {[s['context_length'] for s in medium_samples]}")
    sys.stdout.flush()

    # Create combined large sample for 10000 chunk testing
    combined_context = ""
    combined_questions = []
    combined_ids = []

    for s in all_samples:
        if len(combined_context) < 15000:
            combined_context += "\n\n" + s['context'] if combined_context else s['context']
            combined_questions.append(s['question'])
            combined_ids.append(s['id'])

    large_sample = {
        'id': 'combined_large',
        'question': ' | '.join(combined_questions),
        'answer': 'Combined answers',
        'context': combined_context,
        'context_length': len(combined_context),
        'is_combined': True
    }

    print(f"Created large sample: {large_sample['context_length']} chars from {len(combined_ids)} samples")
    sys.stdout.flush()

    return {
        'medium': medium_samples,
        'large': [large_sample]
    }


def chunk_text(text: str, chunk_size: int) -> list[str]:
    """Split text into chunks."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            for boundary in ['. ', '.\n', '? ', '! ']:
                last_boundary = text.rfind(boundary, start + chunk_size // 2, end + 100)
                if last_boundary != -1:
                    end = last_boundary + len(boundary)
                    break
        chunks.append(text[start:end].strip())
        start = end

    return [c for c in chunks if c]


def parse_json_array(text: str) -> list | None:
    """Try to extract a JSON array from text."""
    import re
    text = text.strip()

    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except:
        pass

    match = re.search(r'\[[\s\S]*\]', text)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, list):
                return data
        except:
            pass

    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    match = re.search(r'\[[\s\S]*\]', text)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, list):
                return data
        except:
            pass

    return None


def extract_from_chunk(model: str, chunk: str, chunk_id: int, timeout: int = 180) -> dict:
    """Extract entities and relationships from a single chunk."""
    result = {
        "chunk_id": chunk_id,
        "chunk_length": len(chunk),
        "entities": [],
        "relations": [],
        "entity_time": 0,
        "relation_time": 0,
        "tokens_in": 0,
        "tokens_out": 0,
        "error": None
    }

    # Entity extraction
    try:
        entity_start = time.time()
        prompt = ENTITY_PROMPT.format(text=chunk)
        result["tokens_in"] = len(prompt) // 4

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 4096}
            },
            timeout=timeout
        )

        if response.status_code != 200:
            result["error"] = f"HTTP {response.status_code}"
            return result

        data = response.json()
        result["tokens_out"] = data.get("eval_count", 0)
        result["entity_time"] = time.time() - entity_start

        entities = parse_json_array(data.get("response", ""))
        if entities:
            result["entities"] = entities
    except Exception as e:
        result["error"] = str(e)
        return result

    # Relationship extraction
    try:
        rel_start = time.time()
        entity_names = [e.get("name", "") for e in (entities or [])]
        prompt = RELATION_PROMPT.format(text=chunk, entities=", ".join(entity_names))

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 4096}
            },
            timeout=timeout
        )

        if response.status_code == 200:
            data = response.json()
            result["tokens_out"] += data.get("eval_count", 0)
            result["relation_time"] = time.time() - rel_start
            relations = parse_json_array(data.get("response", ""))
            if relations:
                result["relations"] = relations
    except:
        pass

    return result


def benchmark_sample(model: str, sample: dict, chunk_size: int) -> dict:
    """Run benchmark for a specific sample and chunk size."""
    text = sample['context']
    chunks = chunk_text(text, chunk_size)

    all_entities = []
    all_relations = []
    total_time = 0
    total_tokens_out = 0

    for i, chunk in enumerate(chunks):
        result = extract_from_chunk(model, chunk, i)
        all_entities.extend(result["entities"])
        all_relations.extend(result["relations"])
        total_time += result["entity_time"] + result["relation_time"]
        total_tokens_out += result["tokens_out"]

        print(f"      Chunk {i+1}/{len(chunks)}: {len(result['entities'])} ent, "
              f"{len(result['relations'])} rel ({result['entity_time']:.1f}s)")
        sys.stdout.flush()

    # Deduplicate
    unique_entities = {}
    for e in all_entities:
        name = e.get("name", "").lower()
        if name and name not in unique_entities:
            unique_entities[name] = e

    return {
        "sample_id": sample['id'],
        "context_length": len(text),
        "chunk_size": chunk_size,
        "num_chunks": len(chunks),
        "total_entities": len(all_entities),
        "unique_entities": len(unique_entities),
        "total_relations": len(all_relations),
        "total_time": total_time,
        "tokens_out": total_tokens_out,
    }


def main():
    parser = argparse.ArgumentParser(description="Smart Chunk-Size Benchmark")
    parser.add_argument("--model", default="gemma3:4b", help="Model to benchmark")
    args = parser.parse_args()

    # Load samples
    samples = load_smart_samples()

    print("\n" + "=" * 80)
    print("SMART CHUNK-SIZE BENCHMARK")
    print("=" * 80)
    print(f"Model: {args.model}")
    print(f"Medium samples (500-4000): {len(samples['medium'])} samples")
    print(f"Large sample (10000): {len(samples['large'])} samples")
    print("=" * 80)
    sys.stdout.flush()

    all_results = []

    # Test 500-4000 with medium samples
    chunk_sizes_medium = [500, 1000, 1500, 2000, 2500, 3000, 3500, 4000]

    for sample in samples['medium']:
        print(f"\n--- Medium Sample: {sample['id'][:30]}... ({sample['context_length']} chars) ---")
        print(f"    Question: {sample['question'][:50]}...")
        sys.stdout.flush()

        for chunk_size in chunk_sizes_medium:
            print(f"  Chunk size {chunk_size}:")
            sys.stdout.flush()
            result = benchmark_sample(args.model, sample, chunk_size)
            all_results.append(result)
            print(f"    -> {result['num_chunks']} chunks, {result['unique_entities']} unique entities, "
                  f"{result['total_relations']} relations, {result['total_time']:.1f}s total")
            sys.stdout.flush()

    # Test 10000 with large sample
    for sample in samples['large']:
        print(f"\n--- Large Sample: {sample['id']} ({sample['context_length']} chars) ---")
        print(f"    Question: {sample['question'][:80]}...")
        sys.stdout.flush()

        print(f"  Chunk size 10000:")
        sys.stdout.flush()
        result = benchmark_sample(args.model, sample, 10000)
        all_results.append(result)
        print(f"    -> {result['num_chunks']} chunks, {result['unique_entities']} unique entities, "
              f"{result['total_relations']} relations, {result['total_time']:.1f}s total")
        sys.stdout.flush()

    # Summary
    print("\n" + "=" * 100)
    print("BENCHMARK SUMMARY")
    print("=" * 100)

    print(f"\n{'Chunk Size':<12} {'Sample':<15} {'Chunks':<8} {'Entities':<10} {'Relations':<10} "
          f"{'Time (s)':<10} {'Tok Out':<10}")
    print("-" * 100)

    for r in all_results:
        sample_id = r['sample_id'][:12] + "..." if len(r['sample_id']) > 15 else r['sample_id']
        print(f"{r['chunk_size']:<12} {sample_id:<15} {r['num_chunks']:<8} {r['unique_entities']:<10} "
              f"{r['total_relations']:<10} {r['total_time']:<10.1f} {r['tokens_out']:<10}")

    print("-" * 100)
    sys.stdout.flush()

    # Save results
    output_file = f"reports/benchmark_smart_{args.model.replace(':', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "model": args.model,
            "strategy": "medium samples for 500-4000, large sample for 10000",
            "results": all_results
        }, f, indent=2)

    print(f"\nResults saved to: {output_file}")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
