#!/usr/bin/env python3
"""
Benchmark LLM Models with Different Chunk Sizes.

Tests models (gemma3:4b, qwen2.5:7b) across chunk sizes: 500-4000 (step 500) + 10000.
Uses 10 RAGAS samples for consistent evaluation.

Usage:
    poetry run python scripts/benchmark_model_chunksizes.py --model gemma3:4b
    poetry run python scripts/benchmark_model_chunksizes.py --model qwen2.5:7b
    poetry run python scripts/benchmark_model_chunksizes.py --model parallel  # Both in parallel
"""

import argparse
import asyncio
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# RAGAS SAMPLES - LARGE (concatenated to ~4000 chars for chunking tests)
# =============================================================================

# Original small samples for reference
RAGAS_SAMPLES_SMALL = [
    "Arthur's Magazine (1844–1846) was an American literary periodical published in Philadelphia in the 19th century. First for Women is a woman's magazine published by Bauer Media Group in the USA. The Oberoi family is an Indian family that is famous for its involvement in hotels, namely through The Oberoi Group. The Oberoi Group is a hotel company with its head office in Delhi.",
    'Allison Beth "Allie" Goertz (born March 2, 1991) is an American musician. She\'s known for her satirical songs based on various pop culture topics. "Cossbysweater" by Goertz is a satirical song about comedian Bill Cosby that appeared on YouTube and became viral. Richard Nixon\'s second vice president was Gerald Ford. The Simpsons is an animated TV series created by Matt Groening.',
    "Leaving Las Vegas is a 1995 American drama film written and directed by Mike Figgis and based on the semi-autobiographical 1990 novel of the same name by John O'Brien. It stars Nicolas Cage as a suicidal alcoholic in Los Angeles who, having lost his family and been fired from his job, has decided to move to Las Vegas and drink himself to death. He meets a prostitute played by Elisabeth Shue and they become close. Nicolas Cage won the Academy Award for Best Actor for his role in the film.",
    "The Python programming language was created by Guido van Rossum and first released in 1991. Python is maintained by the Python Software Foundation. Django is a high-level Python web framework that encourages rapid development. It was created by Adrian Holovaty and Simon Willison while working at the Lawrence Journal-World newspaper. Flask is another Python web framework created by Armin Ronacher as part of the Pallets project.",
    "Apple Inc. is an American multinational technology company headquartered in Cupertino, California. Steve Jobs, Steve Wozniak, and Ronald Wayne founded Apple in 1976. Tim Cook became CEO of Apple in 2011 after Steve Jobs' resignation. The iPhone was first introduced by Steve Jobs in 2007 and revolutionized the smartphone industry. Apple Park is the corporate headquarters of Apple Inc., located in Cupertino.",
    "The European Union is a political and economic union of 27 member states. The EU was established by the Maastricht Treaty in 1993. The European Commission is the executive branch of the EU, headquartered in Brussels, Belgium. Ursula von der Leyen is the President of the European Commission since 2019. The European Central Bank, located in Frankfurt, Germany, manages the euro currency.",
    "SpaceX, founded by Elon Musk in 2002, is an American aerospace manufacturer. The company is headquartered in Hawthorne, California. SpaceX developed the Falcon 9 rocket and the Dragon spacecraft. In 2020, SpaceX became the first private company to send astronauts to the International Space Station. Starlink is SpaceX's satellite internet constellation project aiming to provide global internet coverage.",
    "The Beatles were an English rock band formed in Liverpool in 1960. The group consisted of John Lennon, Paul McCartney, George Harrison, and Ringo Starr. They are regarded as the most influential band of all time. Their producer George Martin helped shape their innovative sound at Abbey Road Studios. The band officially disbanded in 1970 after releasing the album Let It Be.",
    "Amazon.com was founded by Jeff Bezos in 1994 in Seattle, Washington. It started as an online bookstore but has since diversified. Amazon Web Services (AWS) was launched in 2006 and is now the world's largest cloud computing platform. Andy Jassy became CEO of Amazon in 2021. Amazon acquired Whole Foods Market in 2017 for approximately $13.7 billion.",
    "NVIDIA Corporation is an American multinational technology company founded by Jensen Huang, Chris Malachowsky, and Curtis Priem in 1993. The company is headquartered in Santa Clara, California. NVIDIA is known for designing graphics processing units (GPUs) and system-on-chip units. The company's GeForce series is popular among gamers, while their Tesla and A100 GPUs are used in data centers for AI workloads.",
]

# Create large samples by concatenating all small samples (~4000 chars each)
# This allows testing chunking behavior with different chunk sizes
RAGAS_SAMPLES = [
    {
        "id": "large_sample_1",
        "text": " ".join(RAGAS_SAMPLES_SMALL)  # ~4000 chars
    }
]


# =============================================================================
# PROMPTS
# =============================================================================

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

RELATION_PROMPT = """Extract relationships between entities from the text. Return ONLY a valid JSON array.

Each relationship should have:
- "source": Source entity name
- "target": Target entity name
- "type": Relationship type (e.g., LOCATED_IN, WORKS_FOR, PART_OF, CREATED_BY)
- "description": Brief description

Text:
{text}

Entities found: {entities}

Return ONLY a JSON array like:
[
  {{"source": "Entity1", "target": "Entity2", "type": "WORKS_FOR", "description": "Entity1 works for Entity2"}}
]

JSON Output:"""


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def chunk_text_by_size(text: str, max_chars: int) -> list[str]:
    """Split text into chunks of approximately max_chars size."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    paragraphs = text.split('\n\n')
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= max_chars:
            current_chunk += ("\n\n" if current_chunk else "") + para
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            if len(para) > max_chars:
                # Split long paragraphs by sentences
                sentences = para.replace('. ', '.\n').split('\n')
                current_chunk = ""
                for sent in sentences:
                    if len(current_chunk) + len(sent) + 1 <= max_chars:
                        current_chunk += (" " if current_chunk else "") + sent
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = sent
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks if chunks else [text]


def parse_json_array(text: str) -> list | None:
    """Try to extract a JSON array from text."""
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


def extract_with_model(model: str, text: str, timeout: int = 300) -> dict:
    """Extract entities and relationships using a specific model."""
    result = {
        "model": model,
        "entities": [],
        "relations": [],
        "entity_time_ms": 0,
        "relation_time_ms": 0,
        "total_time_ms": 0,
        "tokens_output": 0,
        "error": None,
    }

    # Entity extraction
    try:
        entity_start = time.time()
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": ENTITY_PROMPT.format(text=text),
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 4096,
                }
            },
            timeout=timeout
        )

        if response.status_code != 200:
            result["error"] = f"Entity HTTP {response.status_code}"
            return result

        data = response.json()
        raw_response = data.get("response", "")
        tokens = data.get("eval_count", 0)
        result["entity_time_ms"] = (time.time() - entity_start) * 1000
        result["tokens_output"] += tokens

        entities = parse_json_array(raw_response)
        if entities:
            result["entities"] = entities

    except requests.exceptions.Timeout:
        result["error"] = f"Entity timeout after {timeout}s"
        return result
    except Exception as e:
        result["error"] = f"Entity error: {e}"
        return result

    # Relationship extraction
    if result["entities"]:
        try:
            rel_start = time.time()
            entity_names = [e.get("name", "") for e in result["entities"]]
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": RELATION_PROMPT.format(
                        text=text,
                        entities=", ".join(entity_names)
                    ),
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 4096,
                    }
                },
                timeout=timeout
            )

            if response.status_code == 200:
                data = response.json()
                raw_response = data.get("response", "")
                tokens = data.get("eval_count", 0)
                result["relation_time_ms"] = (time.time() - rel_start) * 1000
                result["tokens_output"] += tokens

                relations = parse_json_array(raw_response)
                if relations:
                    result["relations"] = relations

        except:
            pass  # Relations are optional

    result["total_time_ms"] = result["entity_time_ms"] + result["relation_time_ms"]
    return result


async def extract_parallel(text: str, timeout: int = 300) -> dict:
    """Extract with both gemma3:4b and qwen2.5:7b in parallel, then merge."""
    import concurrent.futures

    result = {
        "model": "parallel(gemma3:4b+qwen2.5:7b)",
        "entities": [],
        "relations": [],
        "entity_time_ms": 0,
        "relation_time_ms": 0,
        "total_time_ms": 0,
        "tokens_output": 0,
        "error": None,
        "model_results": {},
    }

    start_time = time.time()

    # Run both models in parallel using ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_gemma = executor.submit(extract_with_model, "gemma3:4b", text, timeout)
        future_qwen = executor.submit(extract_with_model, "qwen2.5:7b", text, timeout)

        gemma_result = future_gemma.result()
        qwen_result = future_qwen.result()

    result["model_results"]["gemma3:4b"] = gemma_result
    result["model_results"]["qwen2.5:7b"] = qwen_result

    # Merge entities (deduplicate by name)
    entity_map = {}
    for e in gemma_result.get("entities", []):
        name = e.get("name", "").lower().strip()
        if name and name not in entity_map:
            entity_map[name] = e
    for e in qwen_result.get("entities", []):
        name = e.get("name", "").lower().strip()
        if name and name not in entity_map:
            entity_map[name] = e

    result["entities"] = list(entity_map.values())

    # Merge relations (deduplicate by source+target+type)
    rel_map = {}
    for r in gemma_result.get("relations", []):
        key = f"{r.get('source', '').lower()}|{r.get('target', '').lower()}|{r.get('type', '').lower()}"
        if key not in rel_map:
            rel_map[key] = r
    for r in qwen_result.get("relations", []):
        key = f"{r.get('source', '').lower()}|{r.get('target', '').lower()}|{r.get('type', '').lower()}"
        if key not in rel_map:
            rel_map[key] = r

    result["relations"] = list(rel_map.values())

    # Aggregate times (parallel = max of both, not sum)
    result["entity_time_ms"] = max(
        gemma_result.get("entity_time_ms", 0),
        qwen_result.get("entity_time_ms", 0)
    )
    result["relation_time_ms"] = max(
        gemma_result.get("relation_time_ms", 0),
        qwen_result.get("relation_time_ms", 0)
    )
    result["total_time_ms"] = (time.time() - start_time) * 1000
    result["tokens_output"] = gemma_result.get("tokens_output", 0) + qwen_result.get("tokens_output", 0)

    return result


# =============================================================================
# BENCHMARK RUNNER
# =============================================================================

def run_benchmark_for_model(
    model: str,
    samples: list[dict],
    chunk_sizes: list[int],
) -> dict:
    """Run benchmark for a model across all chunk sizes."""
    results = {
        "model": model,
        "timestamp": datetime.now().isoformat(),
        "num_samples": len(samples),
        "chunk_sizes": chunk_sizes,
        "chunk_results": [],
    }

    for chunk_size in chunk_sizes:
        print(f"\n{'='*70}")
        print(f"Chunk Size: {chunk_size} chars | Model: {model}")
        print(f"{'='*70}")

        chunk_result = {
            "chunk_size": chunk_size,
            "samples": [],
            "totals": {
                "total_entities": 0,
                "total_relations": 0,
                "total_time_ms": 0,
                "total_chunks": 0,
            }
        }

        for sample in samples:
            sample_id = sample["id"]
            text = sample["text"]

            # Chunk the text
            chunks = chunk_text_by_size(text, chunk_size)
            print(f"  {sample_id}: {len(text)} chars -> {len(chunks)} chunks")

            sample_result = {
                "sample_id": sample_id,
                "text_length": len(text),
                "num_chunks": len(chunks),
                "chunks": [],
                "sample_totals": {
                    "entities": 0,
                    "relations": 0,
                    "time_ms": 0,
                }
            }

            for i, chunk in enumerate(chunks):
                if model == "parallel":
                    # Async parallel extraction
                    extraction = asyncio.run(extract_parallel(chunk))
                else:
                    extraction = extract_with_model(model, chunk)

                num_entities = len(extraction.get("entities", []))
                num_relations = len(extraction.get("relations", []))
                time_ms = extraction.get("total_time_ms", 0)

                print(f"    Chunk {i}: {num_entities} entities, {num_relations} rels, {time_ms:.0f}ms")

                sample_result["chunks"].append({
                    "chunk_index": i,
                    "chunk_chars": len(chunk),
                    "entities": num_entities,
                    "relations": num_relations,
                    "time_ms": time_ms,
                    "error": extraction.get("error"),
                })

                sample_result["sample_totals"]["entities"] += num_entities
                sample_result["sample_totals"]["relations"] += num_relations
                sample_result["sample_totals"]["time_ms"] += time_ms

            chunk_result["samples"].append(sample_result)
            chunk_result["totals"]["total_entities"] += sample_result["sample_totals"]["entities"]
            chunk_result["totals"]["total_relations"] += sample_result["sample_totals"]["relations"]
            chunk_result["totals"]["total_time_ms"] += sample_result["sample_totals"]["time_ms"]
            chunk_result["totals"]["total_chunks"] += len(chunks)

        results["chunk_results"].append(chunk_result)

        print(f"\n  CHUNK SIZE {chunk_size} TOTALS:")
        print(f"    Entities: {chunk_result['totals']['total_entities']}")
        print(f"    Relations: {chunk_result['totals']['total_relations']}")
        print(f"    Time: {chunk_result['totals']['total_time_ms']/1000:.1f}s")

    return results


def print_summary(results: dict):
    """Print summary table of results."""
    print("\n" + "="*90)
    print(f"BENCHMARK SUMMARY: {results['model']}")
    print("="*90)
    print(f"{'Chunk Size':>12} | {'Chunks':>8} | {'Entities':>10} | {'Relations':>10} | {'Time (s)':>12} | {'Ent/Chunk':>10}")
    print("-"*90)

    for cr in results["chunk_results"]:
        t = cr["totals"]
        ent_per_chunk = t["total_entities"] / t["total_chunks"] if t["total_chunks"] > 0 else 0
        print(f"{cr['chunk_size']:>12} | {t['total_chunks']:>8} | {t['total_entities']:>10} | {t['total_relations']:>10} | {t['total_time_ms']/1000:>12.1f} | {ent_per_chunk:>10.1f}")

    print("-"*90)


def main():
    parser = argparse.ArgumentParser(description="Benchmark model with different chunk sizes")
    parser.add_argument("--model", type=str, default="gemma3:4b",
                       choices=["gemma3:4b", "qwen2.5:7b", "parallel"],
                       help="Model to benchmark")
    parser.add_argument("--samples", type=int, default=10,
                       help="Number of samples to use (max 10)")
    args = parser.parse_args()

    # Chunk sizes: 500-4000 (step 500) + 10000
    chunk_sizes = list(range(500, 4001, 500)) + [10000]

    print("="*70)
    print("MODEL CHUNK SIZE BENCHMARK")
    print("="*70)
    print(f"Model: {args.model}")
    print(f"Samples: {min(args.samples, 10)}")
    print(f"Chunk sizes: {chunk_sizes}")

    samples = RAGAS_SAMPLES[:args.samples]

    # Run benchmark
    results = run_benchmark_for_model(args.model, samples, chunk_sizes)

    # Print summary
    print_summary(results)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_safe = args.model.replace(":", "_").replace("(", "").replace(")", "").replace("+", "_")
    output_file = Path(f"reports/benchmark_{model_safe}_{timestamp}.json")
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()
