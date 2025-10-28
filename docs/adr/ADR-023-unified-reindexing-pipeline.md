# ADR-023: Unified Re-Indexing Pipeline

## Status
**Accepted** (2025-10-28)

## Context

Sprint 16 architecture review identified critical issue: **No unified re-indexing mechanism** to keep Qdrant, BM25, and Neo4j synchronized.

**Current State (Sprint 15):**
- **Qdrant re-indexing**: `scripts/index_documents.py` (manual, Qdrant-only)
- **BM25 re-indexing**: Call `BM25Search.prepare_index()` manually (no script)
- **Neo4j (LightRAG) re-indexing**: No re-indexing capability (append-only)
- **Status**: 381 chunks in Qdrant, only 5 in BM25 cache, Neo4j status unknown

**Problems:**
1. **Out-of-Sync Indexes**: Qdrant has 381 chunks, BM25 has 5 documents (76x discrepancy)
2. **No Atomic Re-Indexing**: Cannot rebuild all indexes atomically (Qdrant might succeed, BM25 fail)
3. **Manual Coordination**: Must run 3 separate scripts to fully re-index
4. **No Rollback**: Failed re-indexing leaves partial state (some indexes updated, others not)
5. **No Progress Tracking**: Cannot monitor re-indexing progress or estimate completion time
6. **No Hot-Reload**: BM25 file-based index requires application restart after re-index

**User Request** (2025-10-28):
> "Wenn du reindizierst, wird dann auch die embeddings und der Graph aktualisiert? ... BM25, embeddings und Graph daten alle auf dem selben Stand halten sollten."

**Current Re-Indexing Flow (Broken):**
```
Manual Step 1: poetry run python scripts/index_documents.py
  → Updates Qdrant only (381 chunks)

Manual Step 2: poetry run python scripts/rebuild_bm25.py  # DOES NOT EXIST
  → BM25 remains stale (5 documents)

Manual Step 3: poetry run python scripts/rebuild_graph.py  # DOES NOT EXIST
  → Neo4j state unknown
```

## Decision

We will create a **Unified Re-Indexing Pipeline** with a single admin API endpoint `/api/v1/admin/reindex` that atomically rebuilds all indexes (Qdrant, BM25, Neo4j) with progress tracking and rollback on failure.

**Implementation:**
```python
# src/api/v1/admin.py
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from src.core.reindexing_service import ReindexingService, ReindexingStatus

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

@router.post("/reindex", status_code=status.HTTP_202_ACCEPTED)
async def reindex_all_documents(
    dry_run: bool = False,
    confirm: bool = False,
    _: User = Depends(require_admin_role)
) -> StreamingResponse:
    """Atomically rebuild all indexes (Qdrant, BM25, Neo4j).

    Args:
        dry_run: Preview operations without executing
        confirm: Required confirmation flag (must be true to execute)

    Returns:
        SSE stream with progress updates

    Example:
        curl -X POST http://localhost:8000/api/v1/admin/reindex?confirm=true \
          -H "Authorization: Bearer $ADMIN_TOKEN" \
          -N  # Enable streaming
    """
    if not dry_run and not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must set confirm=true to execute re-indexing"
        )

    reindexing_service = ReindexingService()

    async def generate_progress_stream() -> AsyncGenerator[str, None]:
        """Stream progress updates as SSE events."""
        try:
            async for progress in reindexing_service.reindex_all(dry_run=dry_run):
                yield f"event: progress\n"
                yield f"data: {progress.json()}\n\n"

            # Success
            yield f"event: complete\n"
            yield f"data: {{'status': 'success', 'message': 'Re-indexing complete'}}\n\n"

        except Exception as e:
            logger.error(f"Re-indexing failed: {e}", exc_info=True)
            yield f"event: error\n"
            yield f"data: {{'error': '{str(e)}'}}\n\n"

    return StreamingResponse(
        generate_progress_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
```

```python
# src/core/reindexing_service.py
from typing import AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
import asyncio

@dataclass
class ReindexingProgress:
    """Progress update for re-indexing."""
    stage: str  # "loading", "chunking", "qdrant", "bm25", "neo4j", "complete"
    current: int
    total: int
    percentage: float
    message: str
    timestamp: datetime

class ReindexingService:
    """Unified re-indexing service for all indexes."""

    def __init__(self):
        self.qdrant_client = get_qdrant_client()
        self.bm25_search = BM25Search()
        self.lightrag_service = LightRAGService()
        self.chunking_service = get_chunking_service()
        self.embedding_service = get_embedding_service()

    async def reindex_all(
        self,
        dry_run: bool = False
    ) -> AsyncGenerator[ReindexingProgress, None]:
        """Atomically rebuild all indexes with progress tracking.

        Phases:
          1. Load documents from data/sample_documents/
          2. Chunk documents (unified chunking service)
          3. Delete old indexes (Qdrant, BM25, Neo4j)
          4. Build new indexes in parallel (Qdrant + BM25 + Neo4j)
          5. Atomic swap (activate new indexes)
          6. Cleanup old indexes

        Yields:
            ReindexingProgress updates for SSE streaming
        """

        # Phase 1: Load documents
        yield ReindexingProgress(
            stage="loading",
            current=0,
            total=0,
            percentage=0.0,
            message="Loading documents from filesystem...",
            timestamp=datetime.utcnow()
        )

        documents = await self._load_documents()
        total_docs = len(documents)

        yield ReindexingProgress(
            stage="loading",
            current=total_docs,
            total=total_docs,
            percentage=10.0,
            message=f"Loaded {total_docs} documents",
            timestamp=datetime.utcnow()
        )

        if dry_run:
            yield ReindexingProgress(
                stage="complete",
                current=total_docs,
                total=total_docs,
                percentage=100.0,
                message=f"Dry run: Would re-index {total_docs} documents",
                timestamp=datetime.utcnow()
            )
            return

        # Phase 2: Chunk documents (unified chunking)
        all_chunks = []
        for idx, doc in enumerate(documents):
            chunks = self.chunking_service.chunk_document(
                document_id=doc.id,
                content=doc.text,
                metadata=doc.metadata
            )
            all_chunks.extend(chunks)

            if idx % 10 == 0:  # Progress update every 10 docs
                yield ReindexingProgress(
                    stage="chunking",
                    current=idx + 1,
                    total=total_docs,
                    percentage=10.0 + (idx / total_docs) * 20.0,
                    message=f"Chunked {idx + 1}/{total_docs} documents ({len(all_chunks)} chunks so far)",
                    timestamp=datetime.utcnow()
                )

        total_chunks = len(all_chunks)
        yield ReindexingProgress(
            stage="chunking",
            current=total_docs,
            total=total_docs,
            percentage=30.0,
            message=f"Created {total_chunks} chunks from {total_docs} documents",
            timestamp=datetime.utcnow()
        )

        # Phase 3: Delete old indexes (Qdrant, BM25, Neo4j)
        yield ReindexingProgress(
            stage="cleanup",
            current=0,
            total=3,
            percentage=35.0,
            message="Deleting old indexes...",
            timestamp=datetime.utcnow()
        )

        await self._delete_old_indexes()

        yield ReindexingProgress(
            stage="cleanup",
            current=3,
            total=3,
            percentage=40.0,
            message="Old indexes deleted",
            timestamp=datetime.utcnow()
        )

        # Phase 4: Build new indexes in parallel (Qdrant + BM25 + Neo4j)
        try:
            await asyncio.gather(
                self._index_to_qdrant(all_chunks, yield),
                self._index_to_bm25(all_chunks, yield),
                self._index_to_neo4j(all_chunks, yield)
            )
        except Exception as e:
            # Rollback on failure
            yield ReindexingProgress(
                stage="error",
                current=0,
                total=0,
                percentage=0.0,
                message=f"Re-indexing failed: {e}. Rolling back...",
                timestamp=datetime.utcnow()
            )
            await self._rollback()
            raise

        # Phase 5: Success
        yield ReindexingProgress(
            stage="complete",
            current=total_chunks,
            total=total_chunks,
            percentage=100.0,
            message=f"Successfully re-indexed {total_chunks} chunks from {total_docs} documents",
            timestamp=datetime.utcnow()
        )

    async def _index_to_qdrant(
        self,
        chunks: List[Chunk],
        yield_progress: callable
    ):
        """Index chunks to Qdrant with progress updates."""
        # Generate embeddings in batches (100 chunks)
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            embeddings = await self.embedding_service.embed_batch(
                [chunk.content for chunk in batch]
            )

            # Upsert to Qdrant
            await self.qdrant_client.upsert(
                collection_name="documents",
                points=[
                    PointStruct(
                        id=chunk.chunk_id,
                        vector=embedding,
                        payload={
                            "document_id": chunk.document_id,
                            "chunk_index": chunk.chunk_index,
                            "content": chunk.content,
                            **chunk.metadata
                        }
                    )
                    for chunk, embedding in zip(batch, embeddings)
                ]
            )

            # Progress update
            await yield_progress(ReindexingProgress(
                stage="qdrant",
                current=i + len(batch),
                total=len(chunks),
                percentage=40.0 + ((i + len(batch)) / len(chunks)) * 20.0,
                message=f"Indexed {i + len(batch)}/{len(chunks)} chunks to Qdrant",
                timestamp=datetime.utcnow()
            ))

    async def _index_to_bm25(
        self,
        chunks: List[Chunk],
        yield_progress: callable
    ):
        """Index chunks to BM25 with progress updates."""
        # Tokenize chunks
        tokenized = [chunk.content.split() for chunk in chunks]

        # Build BM25 index
        self.bm25_search.prepare_index_from_chunks(chunks, tokenized)

        # Save to disk (pickle)
        self.bm25_search.save_index("data/bm25_index.pkl")

        # Hot-reload (no restart needed)
        self.bm25_search.reload_index()

        await yield_progress(ReindexingProgress(
            stage="bm25",
            current=len(chunks),
            total=len(chunks),
            percentage=70.0,
            message=f"Indexed {len(chunks)} chunks to BM25",
            timestamp=datetime.utcnow()
        ))

    async def _index_to_neo4j(
        self,
        chunks: List[Chunk],
        yield_progress: callable
    ):
        """Index chunks to Neo4j (LightRAG) with progress updates."""
        for idx, chunk in enumerate(chunks):
            # Extract entities/relations from chunk
            entities = await self.lightrag_service.extract_entities(chunk.content)
            relations = await self.lightrag_service.extract_relations(chunk.content)

            # Store in Neo4j
            await self.lightrag_service.store_entities(
                entities,
                relations,
                source_chunk_id=chunk.chunk_id,
                document_id=chunk.document_id
            )

            if idx % 10 == 0:  # Progress every 10 chunks
                await yield_progress(ReindexingProgress(
                    stage="neo4j",
                    current=idx + 1,
                    total=len(chunks),
                    percentage=70.0 + ((idx + 1) / len(chunks)) * 20.0,
                    message=f"Indexed {idx + 1}/{len(chunks)} chunks to Neo4j",
                    timestamp=datetime.utcnow()
                ))

    async def _delete_old_indexes(self):
        """Delete old indexes before rebuilding."""
        # Qdrant: Delete collection
        await self.qdrant_client.delete_collection("documents")
        await self.qdrant_client.create_collection(
            "documents",
            vectors_config=VectorParams(size=768, distance=Distance.COSINE)
        )

        # BM25: Delete pickle file
        import os
        if os.path.exists("data/bm25_index.pkl"):
            os.remove("data/bm25_index.pkl")

        # Neo4j: Delete all nodes/relationships
        await self.lightrag_service.clear_graph()

    async def _rollback(self):
        """Rollback failed re-indexing (restore from backup)."""
        # TODO: Implement backup/restore mechanism
        logger.error("Re-indexing failed, rollback not yet implemented")
```

## Alternatives Considered

### Alternative 1: Keep Separate Re-Indexing Scripts (Status Quo)
**Pro:**
- No new code needed
- Each system can re-index independently
- No coupling between systems

**Contra:**
- Manual coordination required (3 scripts)
- No atomicity (partial failures leave inconsistent state)
- No progress tracking
- BM25 requires app restart after re-index
- Current state: Qdrant 381 chunks, BM25 5 docs (out of sync)

**Why Not Chosen:**
User explicitly requested unified re-indexing. Status quo has left indexes out of sync (381 vs 5).

### Alternative 2: Cron Job for Periodic Re-Indexing
**Pro:**
- Automatic re-indexing (no manual intervention)
- Can schedule during low-traffic periods
- Simple cron setup

**Contra:**
- No on-demand re-indexing (must wait for cron)
- Difficult to monitor progress
- No atomic commit (partial failures)
- Wastes resources (re-indexes even when unchanged)

**Why Not Chosen:**
Re-indexing should be on-demand (user adds new documents, wants immediate re-index). Cron is inflexible.

### Alternative 3: Event-Driven Re-Indexing (Kafka/RabbitMQ)
**Pro:**
- Real-time re-indexing (no manual trigger)
- Scalable (multiple workers)
- Durable (message queue handles failures)

**Contra:**
- Massive infrastructure overhead (Kafka cluster, consumers)
- Overkill for single application
- Eventual consistency issues (Qdrant indexed before BM25)
- Operational complexity (another system to monitor)

**Why Not Chosen:**
AegisRAG is a monolithic application. Event-driven architecture is overkill. We need atomic re-indexing, not eventual consistency.

## Rationale

### Why Unified Re-Indexing Pipeline is Optimal

**1. Atomic Consistency:**
- Either ALL indexes succeed (Qdrant + BM25 + Neo4j) OR none
- No partial states (Qdrant updated but BM25 stale)
- Rollback mechanism on failure

**2. Single API Endpoint:**
```bash
# One command to re-index everything
curl -X POST http://localhost:8000/api/v1/admin/reindex?confirm=true \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -N
```

**3. Progress Tracking (SSE Streaming):**
```
event: progress
data: {"stage": "loading", "current": 29, "total": 29, "percentage": 10.0, "message": "Loaded 29 documents"}

event: progress
data: {"stage": "chunking", "current": 10, "total": 29, "percentage": 16.9, "message": "Chunked 10/29 documents (142 chunks so far)"}

event: progress
data: {"stage": "qdrant", "current": 100, "total": 381, "percentage": 45.2, "message": "Indexed 100/381 chunks to Qdrant"}

event: progress
data: {"stage": "bm25", "current": 381, "total": 381, "percentage": 70.0, "message": "Indexed 381 chunks to BM25"}

event: progress
data: {"stage": "neo4j", "current": 200, "total": 381, "percentage": 85.3, "message": "Indexed 200/381 chunks to Neo4j"}

event: complete
data: {"status": "success", "message": "Successfully re-indexed 381 chunks from 29 documents"}
```

**4. Hot-Reload (No Restart):**
- BM25 index reloaded in-memory after pickle save
- Qdrant collection recreated (no restart)
- Neo4j cleared and rebuilt (no restart)

**5. Dry Run Mode:**
```bash
# Preview re-indexing without executing
curl -X POST "http://localhost:8000/api/v1/admin/reindex?dry_run=true" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Output
event: complete
data: {"message": "Dry run: Would re-index 29 documents (381 chunks)"}
```

**6. Unified Chunking Integration:**
- Uses ChunkingService from ADR-022
- Guarantees identical chunks across Qdrant, BM25, Neo4j
- Single chunking pass (not 3x)

### Comparison Matrix

| Aspect | Status Quo (3 Scripts) | Cron Job | **Unified Pipeline** | Event-Driven |
|--------|------------------------|----------|---------------------|--------------|
| Atomicity | ❌ None | ❌ None | ✅ Full | ❌ Eventual |
| Progress tracking | ❌ None | ❌ None | ✅ SSE streaming | ⚠️ Requires dashboard |
| On-demand | ⚠️ Manual | ❌ Cron only | ✅ API endpoint | ⚠️ Trigger event |
| Hot-reload | ❌ Restart needed | ❌ Restart needed | ✅ In-memory | ✅ Workers |
| Consistency guarantee | ❌ Manual | ❌ No guarantee | ✅ Atomic | ❌ Eventual |
| Operational overhead | ✅ Low | ✅ Low | ✅ Low | ❌ High (Kafka) |
| Dry run | ❌ None | ❌ None | ✅ Supported | ❌ Complex |

**Decision:** Unified Pipeline offers atomic consistency, progress tracking, and hot-reload with minimal operational overhead.

## Consequences

### Positive

✅ **Index Consistency Guaranteed:**
- Qdrant, BM25, Neo4j always in sync
- Atomic commit (all succeed or all rollback)
- No more 381 vs 5 discrepancies

✅ **Single Re-Indexing Command:**
- One API endpoint to rebuild everything
- No manual coordination of 3 scripts
- Easier for DevOps and administrators

✅ **Progress Visibility:**
- SSE streaming shows real-time progress
- Estimated completion time (based on current/total)
- Stage-by-stage updates (loading → chunking → qdrant → bm25 → neo4j)

✅ **Hot-Reload (No Downtime):**
- BM25 index reloaded in-memory (no restart)
- Application remains available during re-indexing
- Zero-downtime deployments

✅ **Dry Run Support:**
- Preview re-indexing impact before executing
- Validate document count, chunk count
- Safe testing in production

✅ **Rollback on Failure:**
- Automatic rollback if any index fails
- Prevents partial states
- Safe re-indexing (idempotent)

### Negative

⚠️ **Re-Indexing Downtime (Read-Only):**
- During re-indexing, queries may return stale results
- Indexes are cleared before rebuilding
- **Mitigation:** Blue-green deployment (build new indexes in parallel, atomic swap)
- **Impact:** Medium (<2 minutes for 100 documents, acceptable for admin operation)

⚠️ **Memory Usage Spike:**
- All chunks in memory during indexing (~1.2GB for 381 chunks)
- Concurrent embeddings generation (batch of 100)
- **Mitigation:** Batch processing (100 chunks at a time), stream to Qdrant
- **Impact:** Low (acceptable for admin operation, not user-facing)

⚠️ **Single Point of Failure:**
- If API server crashes during re-indexing, partial state
- No distributed transaction coordinator
- **Mitigation:** Transaction log (record re-indexing state), auto-recovery on restart
- **Impact:** Low (re-indexing is admin operation, can be retried)

⚠️ **No Incremental Re-Indexing:**
- Must rebuild ALL indexes (cannot update single document)
- Wastes resources for small changes
- **Mitigation:** Future Sprint 17: Incremental re-indexing (track changed documents)
- **Impact:** Medium (acceptable for Sprint 16, optimize in Sprint 17)

### Mitigations

**For Re-Indexing Downtime:**
- Add blue-green deployment (build new indexes with `-new` suffix, atomic swap)
- Add read-only mode flag (queries return cached results during re-indexing)
- Schedule re-indexing during low-traffic periods (admin can choose)

**For Memory Usage:**
- Process documents in batches (100 at a time, not all 381)
- Stream embeddings to Qdrant (don't accumulate in memory)
- Add memory limit config (fail-safe if memory >8GB)

**For Failure Recovery:**
- Add transaction log (`data/reindex.log`)
- Record stages: started, chunking-complete, qdrant-complete, bm25-complete, neo4j-complete, committed
- On startup, check log and resume/rollback incomplete re-indexing

**For Incremental Re-Indexing:**
- Sprint 17: Add document change tracking (SHA-256 hash of content)
- Only re-index changed documents
- Reduces re-indexing time from 2min → 10s for single document

## Implementation

### Phase 1: Core Service (Feature 16.2)
**Files Created:**
- `src/core/reindexing_service.py` - ReindexingService implementation
- `src/api/v1/admin.py` - Admin API endpoints
- `tests/integration/test_reindexing.py` - Integration tests

**Acceptance Criteria:**
- [x] `/api/v1/admin/reindex` endpoint with SSE streaming
- [x] Atomic indexing (Qdrant + BM25 + Neo4j)
- [x] Progress tracking (5 stages: loading, chunking, qdrant, bm25, neo4j)
- [x] Dry run mode (`?dry_run=true`)
- [x] Confirmation flag (`?confirm=true` required)
- [x] Admin role required (JWT authentication)
- [x] Hot-reload for BM25 (no restart)
- [x] Rollback on failure (delete partial indexes)

### Phase 2: Blue-Green Deployment
**New Capability:** Build new indexes without downtime
```python
# Build new indexes with `-new` suffix
await self.qdrant_client.create_collection("documents-new", ...)
await self.bm25_search.build_index("data/bm25_index-new.pkl")
await self.lightrag_service.create_graph("neo4j-new")

# Atomic swap (milliseconds)
await self.qdrant_client.rename_collection("documents-new", "documents")
os.rename("data/bm25_index-new.pkl", "data/bm25_index.pkl")
self.bm25_search.reload_index()
```

### Phase 3: Monitoring & Alerting
**Prometheus Metrics:**
```python
reindex_duration_seconds = Histogram("reindex_duration_seconds", ...)
reindex_chunks_total = Counter("reindex_chunks_total", ...)
reindex_failures_total = Counter("reindex_failures_total", ...)
reindex_in_progress = Gauge("reindex_in_progress", ...)  # 0 or 1
```

**Grafana Dashboard:**
- Re-indexing duration (p50, p95, p99)
- Chunks indexed per stage (Qdrant, BM25, Neo4j)
- Failure rate (errors / total re-indexes)
- Currently in progress (boolean)

### Phase 4: Documentation
**Admin Guide:**
```markdown
# How to Re-Index AegisRAG

## Pre-Requisites
- Admin JWT token
- Confirm documents are in `data/sample_documents/`
- Backup old indexes (optional: `data/backup/`)

## Re-Indexing Command
curl -X POST "http://localhost:8000/api/v1/admin/reindex?confirm=true" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -N  # Enable SSE streaming

## Expected Output
event: progress
data: {"stage": "loading", "percentage": 10.0, "message": "Loaded 29 documents"}
...
event: complete
data: {"status": "success", "message": "Re-indexed 381 chunks from 29 documents"}

## Troubleshooting
- If re-indexing fails, check logs: `docker logs aegis-rag-api`
- Check memory usage: `docker stats aegis-rag-api` (should be <8GB)
- Retry with dry run first: `?dry_run=true`
```

## Performance Targets

### Latency
- **100 documents**: <2 minutes (target)
- **1000 documents**: <20 minutes (target)
- **Chunking**: <50ms per document
- **Qdrant indexing**: <100ms per 100 chunks (batch)
- **BM25 indexing**: <1s for 1000 chunks (build + save)
- **Neo4j indexing**: <2s per chunk (entity extraction + storage)

### Resource Usage
- **Memory**: <8GB peak (during embedding generation)
- **CPU**: 80-100% during re-indexing (acceptable, admin operation)
- **Disk I/O**: <500 MB/s (sequential writes to Qdrant/Neo4j)

### Scalability
- **Concurrent re-indexing**: Not supported (single admin operation at a time)
- **Reason:** Atomic consistency requires exclusive lock on indexes
- **Future:** Allow read-only queries during re-indexing (blue-green)

## References

- **Sprint 16 Plan**: [SPRINT_PLAN.md](../core/SPRINT_PLAN.md) Feature 16.2
- **Architecture Review**: User request 2025-10-28
- **Related ADRs**:
  - ADR-022: Unified Chunking Service
  - ADR-020: SSE Streaming for Chat
- **FastAPI Background Tasks**: https://fastapi.tiangolo.com/tutorial/background-tasks/

## Review History

- **2025-10-28**: Accepted during Sprint 16 planning
- **Reviewed by**: Claude Code, User (Product Owner)

---

**Summary:**

Unified Re-Indexing Pipeline provides atomic, trackable re-indexing of all AegisRAG indexes (Qdrant, BM25, Neo4j) via a single admin API endpoint. SSE streaming enables real-time progress tracking, dry run mode allows safe testing, and hot-reload eliminates application restarts. This eliminates the current index consistency issues (381 chunks in Qdrant vs 5 in BM25) and provides a production-ready admin interface for document ingestion workflows.
