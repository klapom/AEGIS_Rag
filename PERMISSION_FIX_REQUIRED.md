# ⚠️ Permission Fix Required - Graph Extraction Failing

**Status:** 🔴 CRITICAL - Graph extraction failing on all documents
**Discovered:** 2025-12-29 Sprint 66
**Impact:** Documents upload and chunk successfully, but graph extraction fails

---

## Problem

LightRAG cannot write to `/app/data/lightrag/` inside the container because files are owned by `ubuntu:ubuntu` but the container runs as user `aegis` (UID 1001).

### Error Messages

```
[Errno 13] Permission denied: 'data/lightrag/kv_store_text_chunks.json'
[Errno 13] Permission denied: 'data/lightrag/vdb_entities.json'
[Errno 13] Permission denied: 'data/lightrag/vdb_relationships.json'
[Errno 13] Permission denied: 'data/lightrag/vdb_chunks.json'
```

### Current Ownership

```bash
$ docker exec aegis-api ls -la /app/data/lightrag/
drwxr-xr-x  2 ubuntu ubuntu    4096 Dec 17 12:52 .
-rw-r--r--  1 ubuntu ubuntu  333051 Dec 24 08:06 kv_store_text_chunks.json
-rw-r--r--  1 ubuntu ubuntu  717140 Dec 24 08:06 vdb_chunks.json
-rw-r--r--  1 ubuntu ubuntu 2745199 Dec 24 08:06 vdb_entities.json
```

Container user: `aegis` (UID 1001, GID 1001)
File owner: `ubuntu` (read-only for `aegis`)

---

## Fix (Requires sudo)

Run from the DGX Spark host:

```bash
cd /home/admin/projects/aegisrag/AEGIS_Rag
sudo chown -R 1001:1001 data/lightrag/
```

Verify:

```bash
docker exec aegis-api ls -la /app/data/lightrag/
# Should show: aegis aegis instead of ubuntu ubuntu
```

---

## Alternative: Recreate Files

If you prefer not to use sudo, you can delete the old files and let the container recreate them:

```bash
cd /home/admin/projects/aegisrag/AEGIS_Rag
rm -f data/lightrag/*.json
docker restart aegis-api
```

**⚠️ Warning:** This will delete existing graph data! Only do this if you're okay losing previous graph extractions.

---

## Verification

After fixing permissions, re-run the document upload to verify graph extraction works:

1. Upload test document via Admin Indexing page
2. Check backend logs for graph extraction:
   ```bash
   docker logs aegis-api 2>&1 | grep graph_extraction | tail -20
   ```
3. Should see: `TIMING_lightrag_insert_complete` without permission errors

---

## Root Cause

The `data/lightrag/` directory was likely created by a previous container or user with different ownership. The container user was recently changed to `aegis` (UID 1001) but the data directory ownership wasn't updated.

---

## Prevention

Add to `docker-compose.dgx-spark.yml` to ensure correct ownership on container startup:

```yaml
services:
  api:
    entrypoint: >
      sh -c "
        chown -R aegis:aegis /app/data/lightrag || true &&
        exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000
      "
```

Or set proper volume permissions in the Dockerfile:

```dockerfile
RUN mkdir -p /app/data/lightrag && chown -R aegis:aegis /app/data
```

---

**Created:** 2025-12-29
**Author:** Claude Code
