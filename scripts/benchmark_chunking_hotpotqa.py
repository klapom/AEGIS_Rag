#!/usr/bin/env python3
"""
Valid Chunk-Size Benchmark using HotPotQA fullwiki dataset.
Uses REAL evaluation samples with 3000-7000+ character contexts.
Tests chunk sizes: 500, 1000, 1500, 2000, 2500, 3000, 3500, 4000

This allows proper testing of how chunk size affects entity extraction.
"""
import json
import time
import requests
import argparse
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


def load_hotpotqa_samples(num_samples: int = 10, include_large: bool = True) -> list[dict]:
    """Load large samples from HotPotQA fullwiki dataset.

    Args:
        num_samples: Number of individual samples to load
        include_large: If True, also create a ~10000 char combined sample for large chunk testing
    """
    print(f"Loading {num_samples} samples from HotPotQA fullwiki...")
    ds = load_dataset('hotpot_qa', 'fullwiki', split=f'validation[:{num_samples * 3}]')

    samples = []
    raw_samples = []  # Keep raw samples for potential combination

    for sample in ds:
        # Combine all context sentences
        contexts = sample.get('context', {})
        if isinstance(contexts, dict):
            sentences = contexts.get('sentences', [])
            total_text = ' '.join([' '.join(s) if isinstance(s, list) else s for s in sentences])
        else:
            total_text = str(contexts)

        raw_samples.append({
            'id': sample.get('id', f'sample_{len(raw_samples)}'),
            'question': sample.get('question', ''),
            'answer': sample.get('answer', ''),
            'context': total_text,
            'context_length': len(total_text)
        })

        # Only keep samples with substantial text (>2000 chars for chunking tests)
        if len(total_text) >= 2000 and len(samples) < num_samples:
            samples.append({
                'id': sample.get('id', f'sample_{len(samples)}'),
                'question': sample.get('question', ''),
                'answer': sample.get('answer', ''),
                'context': total_text,
                'context_length': len(total_text)
            })

    # Create a ~10000 char combined sample for large chunk testing
    if include_large:
        combined_context = ""
        combined_questions = []
        combined_answers = []
        combined_ids = []

        for s in raw_samples:
            if len(combined_context) < 10000:
                combined_context += "\n\n" + s['context'] if combined_context else s['context']
                combined_questions.append(s['question'])
                combined_answers.append(s['answer'])
                combined_ids.append(s['id'])

        if len(combined_context) >= 8000:  # Close enough to 10000
            samples.append({
                'id': 'combined_large_' + '_'.join(combined_ids[:3]),
                'question': ' | '.join(combined_questions),  # Concatenate questions
                'answer': ' | '.join(combined_answers),
                'context': combined_context,
                'context_length': len(combined_context),
                'is_combined': True,
                'source_sample_count': len(combined_ids)
            })
            print(f"Created combined large sample: {len(combined_context)} chars from {len(combined_ids)} samples")

    print(f"Loaded {len(samples)} samples with context lengths: "
          f"{[s['context_length'] for s in samples]}")
    return samples


def chunk_text(text: str, chunk_size: int, overlap: int = 0) -> list[str]:
    """Split text into chunks of approximately chunk_size characters."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        # Try to break at sentence boundary
        if end < len(text):
            for boundary in ['. ', '.\n', '? ', '! ']:
                last_boundary = text.rfind(boundary, start + chunk_size // 2, end + 100)
                if last_boundary != -1:
                    end = last_boundary + len(boundary)
                    break
        chunks.append(text[start:end].strip())
        start = end - overlap if overlap else end

    return [c for c in chunks if c]


def parse_json_array(text: str) -> list | None:
    """Try to extract a JSON array from text."""
    import re
    text = text.strip()

    # Direct parse
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except:
        pass

    # Find JSON array
    match = re.search(r'\[[\s\S]*\]', text)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, list):
                return data
        except:
            pass

    # Remove markdown code blocks
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
        raw_response = data.get("response", "")
        result["tokens_out"] = data.get("eval_count", 0)
        result["entity_time"] = time.time() - entity_start

        entities = parse_json_array(raw_response)
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
            raw_response = data.get("response", "")
            result["tokens_out"] += data.get("eval_count", 0)
            result["relation_time"] = time.time() - rel_start

            relations = parse_json_array(raw_response)
            if relations:
                result["relations"] = relations
    except:
        pass

    return result


def benchmark_sample_with_chunk_size(model: str, sample: dict, chunk_size: int) -> dict:
    """Run benchmark for a specific sample and chunk size."""
    text = sample['context']
    chunks = chunk_text(text, chunk_size)

    all_entities = []
    all_relations = []
    total_time = 0
    total_tokens_in = 0
    total_tokens_out = 0
    chunk_results = []

    for i, chunk in enumerate(chunks):
        result = extract_from_chunk(model, chunk, i)
        chunk_results.append(result)

        all_entities.extend(result["entities"])
        all_relations.extend(result["relations"])
        total_time += result["entity_time"] + result["relation_time"]
        total_tokens_in += result["tokens_in"]
        total_tokens_out += result["tokens_out"]

    # Deduplicate entities by name
    unique_entities = {}
    for e in all_entities:
        name = e.get("name", "").lower()
        if name and name not in unique_entities:
            unique_entities[name] = e

    return {
        "sample_id": sample['id'],
        "question": sample['question'],
        "context_length": len(text),
        "chunk_size": chunk_size,
        "num_chunks": len(chunks),
        "total_entities": len(all_entities),
        "unique_entities": len(unique_entities),
        "total_relations": len(all_relations),
        "total_time": total_time,
        "tokens_in": total_tokens_in,
        "tokens_out": total_tokens_out,
        "avg_time_per_chunk": total_time / len(chunks) if chunks else 0,
    }


def main():
    parser = argparse.ArgumentParser(description="HotPotQA Chunk-Size Benchmark")
    parser.add_argument("--model", default="gemma3:4b", help="Model to benchmark")
    parser.add_argument("--samples", type=int, default=5, help="Number of samples to test")
    parser.add_argument("--chunk-sizes", default="500,1000,1500,2000,2500,3000,3500,4000,10000",
                       help="Comma-separated chunk sizes (includes 10000 for large sample test)")
    args = parser.parse_args()

    chunk_sizes = [int(x) for x in args.chunk_sizes.split(",")]

    # Load HotPotQA samples
    samples = load_hotpotqa_samples(args.samples)

    print("\n" + "=" * 80)
    print("HOTPOTQA CHUNK-SIZE BENCHMARK")
    print("=" * 80)
    print(f"Model: {args.model}")
    print(f"Samples: {len(samples)}")
    print(f"Chunk sizes: {chunk_sizes}")
    print("=" * 80)

    all_results = []

    for sample in samples:
        print(f"\n--- Sample: {sample['id']} ({sample['context_length']} chars) ---")
        print(f"    Question: {sample['question'][:60]}...")

        for chunk_size in chunk_sizes:
            result = benchmark_sample_with_chunk_size(args.model, sample, chunk_size)
            all_results.append(result)

            print(f"  Chunk {chunk_size}: {result['num_chunks']} chunks -> "
                  f"{result['unique_entities']} entities, {result['total_relations']} relations "
                  f"({result['total_time']:.1f}s, {result['tokens_out']} tokens out)")

    # Summary by chunk size
    print("\n" + "=" * 100)
    print("SUMMARY BY CHUNK SIZE")
    print("=" * 100)

    print(f"\n{'Chunk Size':<12} {'Avg Chunks':<12} {'Avg Entities':<14} {'Avg Relations':<14} "
          f"{'Avg Time (s)':<14} {'Avg Tok Out':<12}")
    print("-" * 100)

    for cs in chunk_sizes:
        cs_results = [r for r in all_results if r['chunk_size'] == cs]
        avg_chunks = sum(r['num_chunks'] for r in cs_results) / len(cs_results)
        avg_entities = sum(r['unique_entities'] for r in cs_results) / len(cs_results)
        avg_relations = sum(r['total_relations'] for r in cs_results) / len(cs_results)
        avg_time = sum(r['total_time'] for r in cs_results) / len(cs_results)
        avg_tokens = sum(r['tokens_out'] for r in cs_results) / len(cs_results)

        print(f"{cs:<12} {avg_chunks:<12.1f} {avg_entities:<14.1f} {avg_relations:<14.1f} "
              f"{avg_time:<14.1f} {avg_tokens:<12.0f}")

    print("-" * 100)

    # Save results
    output_file = f"reports/benchmark_hotpotqa_{args.model.replace(':', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "model": args.model,
            "num_samples": len(samples),
            "chunk_sizes": chunk_sizes,
            "samples": [{"id": s['id'], "question": s['question'], "context_length": s['context_length']}
                       for s in samples],
            "results": all_results
        }, f, indent=2)

    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()
