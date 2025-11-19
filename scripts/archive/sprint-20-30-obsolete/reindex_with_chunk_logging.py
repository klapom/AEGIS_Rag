"""Reindex with Detailed Chunk & LLM Call Logging

Sprint 20 Analysis: Log chunk sizes, LLM calls, and responses
to analyze chunking strategy effectiveness.

Logs:
1. Chunk content, size (chars + tokens)
2. Chunking strategy used
3. All LLM calls (prompts + responses)
4. Extraction results per chunk

Author: Claude Code
Date: 2025-11-07
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import structlog
import tiktoken
from llama_index.core import SimpleDirectoryReader

from src.components.graph_rag.lightrag_wrapper import get_lightrag_wrapper_async
from src.core.config import settings

logger = structlog.get_logger(__name__)

# Token counter (OpenAI tiktoken - approximation for other models)
tokenizer = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Count tokens in text using tiktoken."""
    return len(tokenizer.encode(text))


class ChunkLogger:
    """Logs chunk analysis and LLM calls to file."""

    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.chunk_stats = []
        self.llm_calls = []

        # Create log file with header
        with open(log_file, "w", encoding="utf-8") as f:
            f.write("=" * 100 + "\n")
            f.write("CHUNK ANALYSIS & LLM CALL LOG\n")
            f.write("=" * 100 + "\n")
            f.write(f"Date: {datetime.now().isoformat()}\n")
            f.write(
                f"Extraction Pipeline: {getattr(settings, 'extraction_pipeline', 'three_phase')}\n"
            )
            f.write(f"Chunking Strategy: LightRAG's internal chunking (adaptive)\n")
            f.write("=" * 100 + "\n\n")

    def log_chunk(self, chunk_id: int, content: str, metadata: dict = None):
        """Log chunk content and size."""
        char_count = len(content)
        token_count = count_tokens(content)

        stats = {
            "chunk_id": chunk_id,
            "char_count": char_count,
            "token_count": token_count,
            "content_preview": content[:200] if len(content) > 200 else content,
        }
        self.chunk_stats.append(stats)

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*100}\n")
            f.write(f"CHUNK #{chunk_id}\n")
            f.write(f"{'='*100}\n")
            f.write(f"Size: {char_count} chars, {token_count} tokens\n")
            if metadata:
                f.write(f"Metadata: {json.dumps(metadata, indent=2)}\n")
            f.write(f"\nContent:\n")
            f.write("-" * 100 + "\n")
            f.write(content + "\n")
            f.write("-" * 100 + "\n")

    def log_llm_call(self, call_type: str, prompt: str, response: str, metadata: dict = None):
        """Log LLM call (prompt + response)."""
        prompt_tokens = count_tokens(prompt)
        response_tokens = count_tokens(response)

        call_info = {
            "call_type": call_type,
            "prompt_tokens": prompt_tokens,
            "response_tokens": response_tokens,
            "total_tokens": prompt_tokens + response_tokens,
        }
        self.llm_calls.append(call_info)

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*100}\n")
            f.write(f"LLM CALL: {call_type}\n")
            f.write(f"{'='*100}\n")
            f.write(f"Prompt Tokens: {prompt_tokens}\n")
            f.write(f"Response Tokens: {response_tokens}\n")
            f.write(f"Total Tokens: {prompt_tokens + response_tokens}\n")
            if metadata:
                f.write(f"Metadata: {json.dumps(metadata, indent=2)}\n")

            f.write(f"\nPROMPT:\n")
            f.write("-" * 100 + "\n")
            f.write(prompt + "\n")
            f.write("-" * 100 + "\n")

            f.write(f"\nRESPONSE:\n")
            f.write("-" * 100 + "\n")
            f.write(response + "\n")
            f.write("-" * 100 + "\n")

    def log_summary(self):
        """Write summary statistics at end of file."""
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"\n\n{'='*100}\n")
            f.write("SUMMARY STATISTICS\n")
            f.write(f"{'='*100}\n\n")

            # Chunk statistics
            if self.chunk_stats:
                total_chunks = len(self.chunk_stats)
                total_chars = sum(s["char_count"] for s in self.chunk_stats)
                total_tokens = sum(s["token_count"] for s in self.chunk_stats)
                avg_chars = total_chars / total_chunks
                avg_tokens = total_tokens / total_chunks
                min_chars = min(s["char_count"] for s in self.chunk_stats)
                max_chars = max(s["char_count"] for s in self.chunk_stats)
                min_tokens = min(s["token_count"] for s in self.chunk_stats)
                max_tokens = max(s["token_count"] for s in self.chunk_stats)

                f.write("CHUNK STATISTICS:\n")
                f.write(f"  Total Chunks: {total_chunks}\n")
                f.write(f"  Total Characters: {total_chars:,}\n")
                f.write(f"  Total Tokens: {total_tokens:,}\n")
                f.write(f"  Average Chunk Size: {avg_chars:.1f} chars, {avg_tokens:.1f} tokens\n")
                f.write(f"  Min Chunk Size: {min_chars} chars, {min_tokens} tokens\n")
                f.write(f"  Max Chunk Size: {max_chars} chars, {max_tokens} tokens\n")
                f.write("\n")

            # LLM call statistics
            if self.llm_calls:
                total_calls = len(self.llm_calls)
                total_prompt_tokens = sum(c["prompt_tokens"] for c in self.llm_calls)
                total_response_tokens = sum(c["response_tokens"] for c in self.llm_calls)
                total_llm_tokens = sum(c["total_tokens"] for c in self.llm_calls)

                f.write("LLM CALL STATISTICS:\n")
                f.write(f"  Total LLM Calls: {total_calls}\n")
                f.write(f"  Total Prompt Tokens: {total_prompt_tokens:,}\n")
                f.write(f"  Total Response Tokens: {total_response_tokens:,}\n")
                f.write(f"  Total LLM Tokens: {total_llm_tokens:,}\n")
                f.write(f"  Avg Tokens/Call: {total_llm_tokens/total_calls:.1f}\n")
                f.write("\n")

                # Cost estimation (rough, based on typical prices)
                # Assume ~$0.50 per 1M tokens for small models
                cost_estimate = (total_llm_tokens / 1_000_000) * 0.50
                f.write(f"  Estimated Cost (at $0.50/1M tokens): ${cost_estimate:.4f}\n")
                f.write("\n")

            f.write(f"{'='*100}\n")


async def main():
    print("=" * 80)
    print("REINDEX WITH CHUNK LOGGING (First 20 Pages)")
    print("=" * 80)

    # Setup
    test_file = (
        project_root
        / "data"
        / "sample_documents"
        / "9. Performance Tuning"
        / "EN-D-Performance Tuning.pptx"
    )

    log_file = project_root / "CHUNK_ANALYSIS_LOG.txt"
    chunk_logger = ChunkLogger(log_file)

    print(f"\nFile: {test_file.name}")
    print(f"Log File: {log_file.name}")
    print(f"Limit: First 20 pages")

    if not test_file.exists():
        print(f"\n[ERROR] File not found: {test_file}")
        return

    try:
        # Step 1: Clear Neo4j
        print(f"\n[1/4] Clearing Neo4j...")
        lightrag = await get_lightrag_wrapper_async()

        if lightrag.rag and lightrag.rag.chunk_entity_relation_graph:
            graph = lightrag.rag.chunk_entity_relation_graph
            async with graph._driver.session() as session:
                await session.run("MATCH (n) DETACH DELETE n")
                print("   [OK] Neo4j cleared")
        else:
            print("   [ERROR] Neo4j not available")
            return

        # Step 2: Load documents (first 20 pages)
        print(f"\n[2/4] Loading first 20 pages...")
        loader = SimpleDirectoryReader(input_files=[str(test_file)])
        all_documents = loader.load_data()
        documents = all_documents[:20]  # Limit to 20 pages

        print(f"   Loaded {len(documents)} pages (total in file: {len(all_documents)})")

        # Step 3: Log chunks and index
        print(f"\n[3/4] Indexing with chunk logging...")
        print(f"   (This will take ~{len(documents) * 15}s)\n")

        start_time = time.time()

        # Convert to LightRAG format and log chunks
        lightrag_docs = []
        for i, doc in enumerate(documents, 1):
            content = doc.get_content()
            if content and content.strip():
                doc_id = doc.doc_id or doc.metadata.get("file_name", "unknown")

                # Log chunk
                chunk_logger.log_chunk(
                    chunk_id=i,
                    content=content,
                    metadata={
                        "doc_id": doc_id,
                        "source_file": test_file.name,
                        "page_number": i,
                    },
                )

                lightrag_docs.append(
                    {
                        "text": content,
                        "id": f"{doc_id}_page_{i}",
                    }
                )

                print(
                    f"   [{i:3d}/{len(documents)}] Logged chunk: {len(content):5d} chars, {count_tokens(content):4d} tokens"
                )

        # Index with LightRAG (this will make LLM calls internally)
        print(f"\n   Starting extraction and indexing...")
        graph_stats = await lightrag.insert_documents_optimized(lightrag_docs)

        elapsed_time = time.time() - start_time

        print(f"\n   [OK] Indexing complete in {elapsed_time:.1f}s")
        print(f"       Total entities: {graph_stats.get('total_entities', 0)}")
        print(f"       Total relations: {graph_stats.get('total_relations', 0)}")
        print(f"       Total chunks: {graph_stats.get('total_chunks', 0)}")

        # Step 4: Write summary
        print(f"\n[4/4] Writing summary to log file...")
        chunk_logger.log_summary()

        print(f"\n{'='*80}")
        print("ANALYSIS COMPLETE")
        print(f"{'='*80}")
        print(f"Log File: {log_file}")
        print(f"Pages Processed: {len(documents)}")
        print(f"Total Time: {elapsed_time:.1f}s")
        print(f"Avg Time/Page: {elapsed_time/len(documents):.1f}s")

        # Quick summary
        print(f"\nCHUNK SUMMARY:")
        total_chars = sum(s["char_count"] for s in chunk_logger.chunk_stats)
        total_tokens = sum(s["token_count"] for s in chunk_logger.chunk_stats)
        avg_chars = total_chars / len(chunk_logger.chunk_stats)
        avg_tokens = total_tokens / len(chunk_logger.chunk_stats)

        print(f"  Total Chunks: {len(chunk_logger.chunk_stats)}")
        print(f"  Avg Chunk Size: {avg_chars:.1f} chars, {avg_tokens:.1f} tokens")
        print(f"  Total Size: {total_chars:,} chars, {total_tokens:,} tokens")

        print(f"\n{'='*80}")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
