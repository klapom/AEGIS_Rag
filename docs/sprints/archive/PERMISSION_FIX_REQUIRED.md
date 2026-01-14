# Sprint 68.8: Permission Fixes - RESOLVED

**Status:** RESOLVED - Sprint 68 Feature 68.8
**Date Fixed:** 2025-01-01
**Issue:** Graph extraction failing due to LightRAG data directory permission issues

## Problem (Sprint 66)

LightRAG could not write to `/app/data/lightrag/` inside the Docker container because:
- Files were owned by `ubuntu:ubuntu` from previous builds
- Container runs as user `aegis` (UID 1001 in CUDA, 1000 in standard)
- `aegis` user had insufficient permissions to write to lightrag directory

### Error Messages

```
[Errno 13] Permission denied: 'data/lightrag/kv_store_text_chunks.json'
[Errno 13] Permission denied: 'data/lightrag/vdb_entities.json'
[Errno 13] Permission denied: 'data/lightrag/vdb_relationships.json'
[Errno 13] Permission denied: 'data/lightrag/vdb_chunks.json'
```

## Solution Implemented (Sprint 68.8)

### Dockerfile Changes

Updated all Docker containers to ensure proper directory ownership on build:

1. **docker/Dockerfile.api** (Standard Python 3.11)
   ```dockerfile
   RUN mkdir -p /app/data/lightrag && \
       chown -R aegis:aegis /app/data && \
       chmod -R 755 /app/data
   ```

2. **docker/Dockerfile.api-cuda** (DGX Spark CUDA 13.0)
   ```dockerfile
   RUN mkdir -p /app/data/lightrag && \
       chown -R aegis:aegis /app/data && \
       chmod -R 755 /app/data
   ```

3. **docker/Dockerfile.api-test** (Test container with dev dependencies)
   ```dockerfile
   RUN useradd -m -u 1000 aegis && \
       chown -R aegis:aegis /app && \
       mkdir -p /app/data/lightrag && \
       chown -R aegis:aegis /app/data && \
       chmod -R 755 /app/data
   ```

### Why This Works

1. **Directory Creation**: `mkdir -p /app/data/lightrag` ensures directory exists during build
2. **Ownership**: `chown -R aegis:aegis /app/data` sets correct owner/group for aegis user
3. **Permissions**: `chmod -R 755` grants:
   - Owner (aegis): read/write/execute (7)
   - Group: read/execute (5)
   - Others: read/execute (5)

### Benefits

- No post-deployment permission fixes needed
- Clean separation: data directory owned by container user, not host user
- Consistent across all container variants (standard, CUDA, test)
- Proper security: only aegis user can modify container files

## Verification

After rebuilding Docker containers:

```bash
# Rebuild containers
docker compose -f docker-compose.dgx-spark.yml build --no-cache api

# Verify permissions in running container
docker exec aegis-api ls -la /app/data/lightrag/

# Expected output:
# drwxr-xr-x  2 aegis aegis 4096 Jan  1 12:00 .
```

## Prevention

- All Docker containers now ensure correct permissions at build time
- No more permission errors when LightRAG writes graph extraction data
- Graph extraction tests should pass without deployment issues

## Related Issues

- **Sprint 66**: Initial issue discovery (document upload failures)
- **Sprint 67**: Core implementation (graph extraction via LightRAG)
- **Sprint 68**: Bug fixes and stabilization (this issue)

---

**Resolved by:** Sprint 68 Feature 68.8
**Docker Images Updated:** api, api-cuda, api-test
