# Old Memory Configuration Scripts

**Archived**: Sprint 19 (2025-10-30)

These scripts configured WSL2/Docker with outdated memory limits.

## Archived Scripts (1 total)

1. **set_wsl_memory_9gb.ps1**: Configured WSL2 with 9GB memory

**Reason for Archival**: Production now requires 12GB for Docker + LightRAG + Neo4j workloads

## Current Scripts

Use the current memory configuration scripts in `scripts/`:
- `scripts/configure_wsl2_memory.ps1` - Sets 12GB WSL2 memory
- `scripts/increase_docker_memory.ps1` - Sets 12GB Docker memory

**Why 12GB?**:
- Qdrant vector DB: ~2GB
- Neo4j graph DB: ~2GB
- LightRAG entity extraction: ~5GB (gemma-3-4b-it-Q8_0)
- Ollama base: ~2GB
- System overhead: ~1GB

---

**Archived**: Sprint 19 (2025-10-30)
