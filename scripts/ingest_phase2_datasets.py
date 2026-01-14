#!/usr/bin/env python3
"""Sprint 88 Pre-Validation: Ingest T2-RAGBench and Code QA Samples.

Downloads 5 samples each from:
- T2-RAGBench (FinQA subset): Financial tables
- Code-RAG-Bench: Code understanding Q&A

Ingests via Frontend API and prepares for RAGAS evaluation.

Usage:
    poetry run python scripts/ingest_phase2_datasets.py

Output:
    - data/evaluation/phase2_t2ragbench/: 5 table documents
    - data/evaluation/phase2_codeqa/: 5 code documents
    - docs/ragas/RAGAS_JOURNEY.md: Updated with experiment results
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog

logger = structlog.get_logger(__name__)

# Configuration
API_BASE_URL = "http://localhost:8000"
AUTH_URL = f"{API_BASE_URL}/api/v1/auth/login"
UPLOAD_URL = f"{API_BASE_URL}/api/v1/retrieval/upload"
NAMESPACE_T2RAG = "ragas_phase2_t2ragbench"
NAMESPACE_CODE = "ragas_phase2_codeqa"
OUTPUT_DIR = Path("data/evaluation/phase2_samples")


async def get_auth_token() -> str | None:
    """Get authentication token from API."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                AUTH_URL,
                json={"username": "admin", "password": "admin123"},
            )
            if response.status_code == 200:
                token = response.json().get("access_token")
                logger.info("Authentication successful", token_prefix=token[:20] + "...")
                return token
            else:
                logger.error("Authentication failed", status=response.status_code)
                return None
        except Exception as e:
            logger.error("Authentication error", error=str(e))
            return None


async def download_t2ragbench_samples(n_samples: int = 5) -> list[dict[str, Any]]:
    """Download samples from T2-RAGBench FinQA subset."""
    from datasets import load_dataset

    logger.info("Downloading T2-RAGBench FinQA samples", n_samples=n_samples)

    try:
        # Load FinQA subset from T2-RAGBench
        ds = load_dataset("G4KMU/t2-ragbench", "FinQA", split="test", streaming=True)

        samples = []
        for i, record in enumerate(ds):
            if i >= n_samples:
                break

            # Extract table and context
            table_data = record.get("table", [])
            context = record.get("context", "")
            question = record.get("question", "")
            answer = record.get("program_answer") or record.get("original_answer", "")

            # Convert table to markdown
            table_md = table_to_markdown(table_data) if table_data else ""

            # Combine into document
            doc_text = f"""# Financial Document

## Context
{context}

## Financial Data Table
{table_md}

---

**Question:** {question}

**Answer:** {answer}
"""

            samples.append({
                "id": f"t2rag_{i:04d}",
                "text": doc_text,
                "question": question,
                "answer": str(answer),
                "source": "t2-ragbench-finqa",
                "doc_type": "table",
                "metadata": {
                    "table_rows": len(table_data) if table_data else 0,
                    "table_cols": len(table_data[0]) if table_data and table_data[0] else 0,
                }
            })
            logger.info(f"Downloaded T2-RAGBench sample {i+1}/{n_samples}", sample_id=f"t2rag_{i:04d}")

        return samples

    except Exception as e:
        logger.error("Failed to download T2-RAGBench", error=str(e))
        return []


def table_to_markdown(table_data: list[list[str]]) -> str:
    """Convert table data to markdown format."""
    if not table_data:
        return ""

    # First row is header
    header = table_data[0]
    separator = ["---" for _ in header]
    rows = table_data[1:]

    lines = [
        "| " + " | ".join(str(h) for h in header) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")

    return "\n".join(lines)


async def download_code_qa_samples(n_samples: int = 5) -> list[dict[str, Any]]:
    """Download samples from code-related QA datasets."""
    from datasets import load_dataset

    logger.info("Downloading Code QA samples", n_samples=n_samples)

    samples = []

    # Try multiple code-related datasets
    datasets_to_try = [
        ("code-rag-bench/code-rag-bench", "programming_1", "test"),
        ("mbpp", None, "test"),  # Mostly Bash/Python Programming Problems
        ("bigcode/the-stack-github-issues", None, "train"),
    ]

    for ds_name, config, split in datasets_to_try:
        try:
            logger.info(f"Trying dataset: {ds_name}")
            if config:
                ds = load_dataset(ds_name, config, split=split, streaming=True, trust_remote_code=True)
            else:
                ds = load_dataset(ds_name, split=split, streaming=True, trust_remote_code=True)

            for i, record in enumerate(ds):
                if len(samples) >= n_samples:
                    break

                # Handle different dataset schemas
                if ds_name == "code-rag-bench/code-rag-bench":
                    code = record.get("context", record.get("code", ""))
                    question = record.get("question", record.get("query", ""))
                    answer = record.get("answer", record.get("response", ""))
                    language = "python"
                elif ds_name == "mbpp":
                    code = record.get("code", "")
                    question = record.get("text", "")  # Problem description
                    answer = code  # The solution is the code
                    language = "python"
                else:
                    code = record.get("content", record.get("code", ""))[:2000]  # Limit size
                    question = f"What does this code do?"
                    answer = "See code snippet"
                    language = record.get("language", "python")

                if not code or not question:
                    continue

                # Format as document
                doc_text = f"""# Code Documentation

## Problem/Question
{question}

## Code Solution
```{language}
{code}
```

## Expected Output/Answer
{answer}
"""

                samples.append({
                    "id": f"code_{len(samples):04d}",
                    "text": doc_text,
                    "question": question,
                    "answer": str(answer)[:500],  # Limit answer length
                    "source": ds_name,
                    "doc_type": "code_config",
                    "metadata": {
                        "language": language,
                        "code_length": len(code),
                    }
                })
                logger.info(f"Downloaded Code QA sample {len(samples)}/{n_samples}", sample_id=f"code_{len(samples)-1:04d}")

            if len(samples) >= n_samples:
                break

        except Exception as e:
            logger.warning(f"Dataset {ds_name} failed", error=str(e)[:100])
            continue

    return samples


async def save_samples_as_files(samples: list[dict], output_dir: Path, prefix: str) -> list[Path]:
    """Save samples as text files for ingestion."""
    output_dir.mkdir(parents=True, exist_ok=True)

    file_paths = []
    for sample in samples:
        file_path = output_dir / f"{sample['id']}.txt"
        file_path.write_text(sample["text"])
        file_paths.append(file_path)
        logger.debug(f"Saved {file_path}")

    # Also save metadata
    metadata_path = output_dir / f"{prefix}_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(
            {
                "samples": [
                    {
                        "id": s["id"],
                        "question": s["question"],
                        "answer": s["answer"],
                        "source": s["source"],
                        "doc_type": s["doc_type"],
                        "metadata": s["metadata"],
                    }
                    for s in samples
                ],
                "generated_at": datetime.now().isoformat(),
            },
            f,
            indent=2,
        )

    logger.info(f"Saved {len(file_paths)} files to {output_dir}")
    return file_paths


async def upload_files(
    file_paths: list[Path], namespace: str, token: str, domain: str = "research",
    delay_between_uploads: float = 7.0  # Sprint 88: Delay to avoid rate limit (10/min = 6s min)
) -> dict[str, Any]:
    """Upload files via Frontend API with rate limit protection."""
    results = {
        "success": [],
        "failed": [],
        "total_time_ms": 0,
    }

    # Sprint 88: Heavy processing (graph extraction, community summarization)
    # Sprint 100 Fix: SpaCy-First Pipeline can take 10-15 minutes per document
    # Increased timeout from 600s (10min) to 1800s (30min) to prevent premature failures
    async with httpx.AsyncClient(timeout=1800.0) as client:
        for i, file_path in enumerate(file_paths):
            # Add delay between uploads to avoid rate limiting (10 requests/minute)
            if i > 0:
                logger.debug(f"Waiting {delay_between_uploads}s between uploads (rate limit protection)")
                await asyncio.sleep(delay_between_uploads)
            start_time = time.time()
            try:
                with open(file_path, "rb") as f:
                    response = await client.post(
                        UPLOAD_URL,
                        files={"file": (file_path.name, f, "text/plain")},
                        data={"namespace": namespace, "domain": domain},
                        headers={"Authorization": f"Bearer {token}"},
                    )

                elapsed_ms = (time.time() - start_time) * 1000
                results["total_time_ms"] += elapsed_ms

                if response.status_code == 200:
                    result = response.json()
                    results["success"].append({
                        "file": file_path.name,
                        "document_id": result.get("document_id"),
                        "status": result.get("status"),
                        "elapsed_ms": elapsed_ms,
                    })
                    logger.info(
                        f"Uploaded {file_path.name}",
                        document_id=result.get("document_id"),
                        elapsed_ms=f"{elapsed_ms:.0f}ms",
                    )
                else:
                    results["failed"].append({
                        "file": file_path.name,
                        "status_code": response.status_code,
                        "error": response.text[:200],
                    })
                    logger.error(f"Upload failed for {file_path.name}", status=response.status_code)

            except Exception as e:
                results["failed"].append({
                    "file": file_path.name,
                    "error": str(e),
                })
                logger.error(f"Upload error for {file_path.name}", error=str(e))

    return results


async def wait_for_processing(document_ids: list[str], token: str, max_wait_s: int = 300):
    """Wait for documents to finish processing."""
    logger.info(f"Waiting for {len(document_ids)} documents to process...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        start_time = time.time()
        while time.time() - start_time < max_wait_s:
            all_done = True
            for doc_id in document_ids:
                try:
                    response = await client.get(
                        f"{API_BASE_URL}/api/v1/admin/upload-status/{doc_id}",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    if response.status_code == 200:
                        status = response.json().get("status")
                        if status not in ["completed", "failed"]:
                            all_done = False
                except Exception:
                    pass

            if all_done:
                logger.info("All documents processed!")
                return True

            await asyncio.sleep(5)

    logger.warning("Timeout waiting for document processing")
    return False


def generate_ragas_journey_entry(
    t2rag_results: dict,
    code_results: dict,
    t2rag_samples: list,
    code_samples: list,
) -> str:
    """Generate RAGAS Journey markdown entry."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    entry = f"""
---

## Sprint 88 Pre-Validation: Phase 2 Dataset Ingestion

**Date:** {timestamp}
**Objective:** Ingest structured data samples (tables, code) for RAGAS Phase 2 baseline

### Datasets Ingested

| Dataset | Type | Samples | Success | Failed | Avg Time |
|---------|------|---------|---------|--------|----------|
| T2-RAGBench (FinQA) | table | {len(t2rag_samples)} | {len(t2rag_results['success'])} | {len(t2rag_results['failed'])} | {t2rag_results['total_time_ms']/max(len(t2rag_results['success']),1):.0f}ms |
| Code QA | code_config | {len(code_samples)} | {len(code_results['success'])} | {len(code_results['failed'])} | {code_results['total_time_ms']/max(len(code_results['success']),1):.0f}ms |

### Sample Details

**T2-RAGBench (FinQA) Samples:**
"""

    for sample in t2rag_samples[:5]:
        entry += f"- `{sample['id']}`: {sample['question'][:60]}...\n"

    entry += "\n**Code QA Samples:**\n"
    for sample in code_samples[:5]:
        entry += f"- `{sample['id']}`: {sample['question'][:60]}...\n"

    entry += f"""
### Ingestion Results

**T2-RAGBench:**
- Namespace: `{NAMESPACE_T2RAG}`
- Total time: {t2rag_results['total_time_ms']:.0f}ms
- Document IDs: {[r['document_id'] for r in t2rag_results['success']]}

**Code QA:**
- Namespace: `{NAMESPACE_CODE}`
- Total time: {code_results['total_time_ms']:.0f}ms
- Document IDs: {[r['document_id'] for r in code_results['success']]}

### Next Steps

1. **Run RAGAS Evaluation:** Evaluate retrieval quality on these samples
2. **Compare with Phase 1:** Baseline comparison with clean_text (HotpotQA)
3. **Identify Bottlenecks:** Measure CP, CR, F, AR for structured data

### Files Created

- `data/evaluation/phase2_samples/t2ragbench/`: {len(t2rag_samples)} table documents
- `data/evaluation/phase2_samples/codeqa/`: {len(code_samples)} code documents
- Metadata JSON files with questions/answers for RAGAS evaluation

---
"""

    return entry


async def main():
    """Main execution flow."""
    print("\n" + "=" * 60)
    print("SPRINT 88 PRE-VALIDATION: Phase 2 Dataset Ingestion")
    print("=" * 60 + "\n")

    # Step 1: Authenticate
    print("📝 Step 1: Authenticating...")
    token = await get_auth_token()
    if not token:
        print("❌ Authentication failed! Is the backend running?")
        return 1

    # Step 2: Download T2-RAGBench samples
    print("\n📥 Step 2: Downloading T2-RAGBench (FinQA) samples...")
    t2rag_samples = await download_t2ragbench_samples(n_samples=5)
    if not t2rag_samples:
        print("⚠️  T2-RAGBench download failed, continuing with Code QA only...")

    # Step 3: Download Code QA samples
    print("\n📥 Step 3: Downloading Code QA samples...")
    code_samples = await download_code_qa_samples(n_samples=5)
    if not code_samples:
        print("⚠️  Code QA download failed!")

    if not t2rag_samples and not code_samples:
        print("❌ No samples downloaded! Check network/dataset availability.")
        return 1

    # Step 4: Save samples as files
    print("\n💾 Step 4: Saving samples as files...")
    t2rag_dir = OUTPUT_DIR / "t2ragbench"
    code_dir = OUTPUT_DIR / "codeqa"

    t2rag_files = []
    code_files = []

    if t2rag_samples:
        t2rag_files = await save_samples_as_files(t2rag_samples, t2rag_dir, "t2ragbench")
    if code_samples:
        code_files = await save_samples_as_files(code_samples, code_dir, "codeqa")

    # Step 5: Upload via Frontend API
    print("\n🚀 Step 5: Uploading via Frontend API...")

    t2rag_results = {"success": [], "failed": [], "total_time_ms": 0}
    code_results = {"success": [], "failed": [], "total_time_ms": 0}

    if t2rag_files:
        print(f"   Uploading {len(t2rag_files)} T2-RAGBench files...")
        t2rag_results = await upload_files(t2rag_files, NAMESPACE_T2RAG, token, domain="finance")

    if code_files:
        print(f"   Uploading {len(code_files)} Code QA files...")
        code_results = await upload_files(code_files, NAMESPACE_CODE, token, domain="programming")

    # Step 6: Wait for processing
    print("\n⏳ Step 6: Waiting for document processing...")
    all_doc_ids = [r["document_id"] for r in t2rag_results["success"] + code_results["success"]]
    if all_doc_ids:
        await wait_for_processing(all_doc_ids, token)

    # Step 7: Generate RAGAS Journey entry
    print("\n📝 Step 7: Generating RAGAS Journey entry...")
    journey_entry = generate_ragas_journey_entry(
        t2rag_results, code_results, t2rag_samples, code_samples
    )

    # Append to RAGAS_JOURNEY.md
    journey_path = Path("docs/ragas/RAGAS_JOURNEY.md")
    with open(journey_path, "a") as f:
        f.write(journey_entry)

    print(f"   Updated {journey_path}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"T2-RAGBench: {len(t2rag_results['success'])}/{len(t2rag_samples)} uploaded successfully")
    print(f"Code QA: {len(code_results['success'])}/{len(code_samples)} uploaded successfully")
    print(f"\nNamespaces:")
    print(f"  - T2-RAGBench: {NAMESPACE_T2RAG}")
    print(f"  - Code QA: {NAMESPACE_CODE}")
    print(f"\nNext: Run RAGAS evaluation on these namespaces")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
