# PowerShell Scripts Validation Report - Sprint 19

**Date**: 2025-10-30
**Validated By**: Claude (Sprint 19 cleanup)

---

## Validation Summary

| Category | Total | ✅ Valid | ⚠️ Updated | 🗄️ Archived |
|----------|-------|----------|------------|-------------|
| **Model Setup** | 3 | 3 | 3 | 0 |
| **Infrastructure** | 2 | 2 | 0 | 1 |
| **Workflow** | 1 | 1 | 0 | 0 |
| **Bash Duplicates** | 2 | - | - | 2 |
| **TOTAL** | 8 | 6 | 3 | 3 |

---

## Detailed Validation Results

### ✅ Model Setup Scripts (3/3 - All Updated)

#### 1. `setup_ollama_models.ps1` ✅ UPDATED
- **Status**: ✅ Valid (Sprint 19 update applied)
- **Purpose**: Download all required Ollama models with health checks
- **Updates Applied**:
  - Changed from `llama3.1:8b` → `gemma-3-4b-it-Q8_0` (entity extraction)
  - Changed from `nomic-embed-text` → `bge-m3` (embeddings, 1024D)
  - Updated download size: ~7GB → ~8.7GB
  - Updated .env instructions to reflect current models
- **Current Models**:
  - `llama3.2:3b` (2GB) - Fast chat responses
  - `gemma-3-4b-it-Q8_0` (4.5GB) - LightRAG entity/relation extraction
  - `bge-m3` (2.2GB) - Text embeddings (1024D)
- **Usage**: `.\scripts\setup_ollama_models.ps1`
- **Features**:
  - Checks Ollama connectivity before download
  - Shows download progress for each model
  - Verifies installed models after download
  - Provides next steps (update .env, test setup)

#### 2. `download_all_models.ps1` ✅ UPDATED
- **Status**: ✅ Valid (Sprint 19 update applied)
- **Purpose**: Simple sequential model download script
- **Updates Applied**:
  - Changed from `llama3.1:8b` → `gemma-3-4b-it-Q8_0`
  - Changed from `nomic-embed-text` → `bge-m3`
  - Added Sprint 19 update note
- **Usage**: `.\scripts\download_all_models.ps1`
- **Notes**: Simplified version of `setup_ollama_models.ps1` without health checks

#### 3. `check_ollama_health.ps1` ✅ UPDATED
- **Status**: ✅ Valid (Sprint 19 update applied)
- **Purpose**: Comprehensive Ollama health check with model verification
- **Updates Applied**:
  - Updated required models list (line 11)
  - Changed from `llama3.1:8b` and `nomic-embed-text` to current models
  - Updated startup command to use `poetry run`
  - Added Sprint 19 note about bge-m3 upgrade
- **Usage**: `.\scripts\check_ollama_health.ps1`
- **Health Checks**:
  1. Ollama connectivity (http://localhost:11434)
  2. Required models installation (llama3.2:3b, gemma-3-4b-it-Q8_0, bge-m3)
  3. Model inference test (generates response)
- **Outputs**:
  - Model sizes in GB
  - Load/inference duration metrics
  - Total model size summary

---

### ✅ Infrastructure Scripts (2/2 - Still Valid)

#### 4. `configure_wsl2_memory.ps1` ✅ VALID
- **Status**: ✅ Valid (no changes needed)
- **Purpose**: Configure WSL2 with 12GB memory for Docker
- **Usage**: `.\scripts\configure_wsl2_memory.ps1`
- **Configuration**:
  - Memory: 12GB (sufficient for LightRAG + Neo4j + Qdrant)
  - CPUs: 4 cores
  - Swap: 2GB
  - Page reporting: Disabled (performance)
- **Features**:
  - Backs up existing `.wslconfig` with timestamp
  - Creates new configuration at `$env:USERPROFILE\.wslconfig`
  - Shows configuration and restart instructions
- **Notes**: Requires WSL2 restart: `wsl --shutdown`

#### 5. `increase_docker_memory.ps1` ✅ VALID
- **Status**: ✅ Valid (no changes needed)
- **Purpose**: Set Docker Desktop memory to 12GB via settings.json
- **Usage**: `.\scripts\increase_docker_memory.ps1`
- **Configuration**:
  - Updates Docker Desktop settings.json
  - Sets `memoryMiB` to 12288 (12GB)
  - Creates timestamped backup before changes
- **Features**:
  - Validates settings.json exists
  - Shows current vs new memory allocation
  - Provides rollback on failure
  - Shows Docker restart instructions
- **Notes**: Requires Docker Desktop restart to apply

---

### ✅ Workflow Scripts (1/1 - Still Valid)

#### 6. `run_qa.ps1` ✅ VALID
- **Status**: ✅ Valid (no changes needed)
- **Purpose**: One-command workflow to start API + logging + interactive Q&A
- **Usage**: `.\scripts\run_qa.ps1`
- **Parameters**:
  - `-ApiPort` (default: 8000)
  - `-BaseUrl` (default: http://localhost:8000)
  - `-LogDir` (default: logs)
  - `-LogFile` (default: logs/api.log)
  - `-RestartApi` (switch: force API restart)
- **Workflow**:
  1. Check if API is running, start if needed
  2. Open log-tailing window (PowerShell)
  3. Launch interactive Q&A (`ask_question.py`)
- **Features**:
  - Auto-detects poetry vs python
  - Creates log directory if missing
  - Waits for API readiness (90s timeout)
  - Opens separate windows for logs and Q&A
- **Notes**: Uses `ask_question.py` (validated in Python scripts)

---

## 🗄️ Archived Scripts (3 total)

### Bash Duplicates (2 scripts)

**Archived to**: `scripts/archive/bash-duplicates/`

1. **check_ollama_health.sh**: Bash version of PowerShell script
2. **setup_ollama_models.sh**: Bash version of PowerShell script

**Reason**: Development primarily on Windows, PowerShell scripts more actively maintained

### Old Memory Config (1 script)

**Archived to**: `scripts/archive/old-memory-config/`

1. **set_wsl_memory_9gb.ps1**: Configured 9GB WSL2 memory

**Reason**: Production now requires 12GB for Docker + LightRAG + Neo4j workloads

---

## Key Changes in Sprint 19

### Model Upgrades

**Before Sprint 19**:
- Embeddings: `nomic-embed-text` (768-dimensional)
- Generation: `llama3.1:8b` (8B parameter model)
- Extraction: No dedicated model

**After Sprint 19**:
- Embeddings: `bge-m3` (1024-dimensional, improved semantic understanding)
- Generation: `llama3.2:3b` (3B parameter model, faster inference)
- Extraction: `gemma-3-4b-it-Q8_0` (4B model, LightRAG entity/relation extraction)

### Why These Changes?

1. **bge-m3 (1024D)**:
   - Better semantic understanding (1024D vs 768D)
   - SOTA performance on MTEB benchmarks
   - Aligned with Qdrant collection (1024D vectors)

2. **gemma-3-4b-it-Q8_0**:
   - Dedicated entity/relation extraction for LightRAG
   - Three-phase extraction: SpaCy NER → Semantic Dedup → Gemma relations
   - Better graph quality than generic generation models

3. **llama3.2:3b**:
   - Faster inference for chat responses (3B vs 8B)
   - 128K context window (same as llama3.1:8b)
   - Lower VRAM usage (better for RTX 3060)

---

## Environment Variables

Update your `.env` file with Sprint 19 models:

```bash
# Ollama Models (Sprint 19)
OLLAMA_MODEL_QUERY=llama3.2:3b
OLLAMA_MODEL_GENERATION=llama3.2:3b
OLLAMA_MODEL_EMBEDDING=bge-m3
OLLAMA_LIGHTRAG_EXTRACTION_MODEL=gemma-3-4b-it-Q8_0

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TIMEOUT=120
```

---

## Testing Commands

```powershell
# Download all models (Sprint 19 versions)
.\scripts\setup_ollama_models.ps1

# Verify models are working
.\scripts\check_ollama_health.ps1

# Configure WSL2 memory (12GB)
.\scripts\configure_wsl2_memory.ps1

# Increase Docker memory (12GB)
.\scripts\increase_docker_memory.ps1

# Start API + logging + Q&A workflow
.\scripts\run_qa.ps1
```

---

## Troubleshooting

### Models Not Found

**Symptom**: `check_ollama_health.ps1` reports missing models
**Solution**:
```powershell
# Re-download models
.\scripts\setup_ollama_models.ps1

# Verify Ollama is running
docker compose ps ollama
docker compose logs ollama
```

### Insufficient Memory

**Symptom**: Docker containers crash, OOM errors
**Solution**:
```powershell
# Configure WSL2 (12GB)
.\scripts\configure_wsl2_memory.ps1
wsl --shutdown
# Wait 10 seconds, restart Docker Desktop

# Verify memory
docker info | Select-String "Total Memory"
```

### API Not Starting

**Symptom**: `run_qa.ps1` fails to start API
**Solution**:
```powershell
# Check Docker services
docker compose up -d

# Check API logs
Get-Content logs/api.log -Wait

# Manually start API
poetry run uvicorn src.api.main:app --reload
```

---

## Validation Methodology

1. **Model List Review**:
   - Checked all model references in PowerShell scripts
   - Updated from old models (llama3.1:8b, nomic-embed-text) to current production models
   - Verified model sizes are correct

2. **Configuration Review**:
   - Confirmed 12GB memory is sufficient for production workloads
   - Verified WSL2 and Docker scripts target correct configuration files
   - Checked backup mechanisms work correctly

3. **Workflow Review**:
   - Verified `run_qa.ps1` uses current Python scripts (`ask_question.py`)
   - Confirmed auto-detection of poetry vs python works
   - Checked log directory creation and tailing

4. **Archival Decision**:
   - Archived Bash duplicates (PowerShell preferred on Windows)
   - Archived old 9GB memory config (12GB now required)
   - Created README documentation for archived scripts

---

## Recommendations

### Immediate Actions: Complete ✅

All PowerShell scripts are now up-to-date with Sprint 19 production models.

### Future Maintenance

1. **When upgrading models**:
   - Update `setup_ollama_models.ps1` model list (lines 25-41)
   - Update `download_all_models.ps1` model downloads (lines 4-11)
   - Update `check_ollama_health.ps1` required models (line 11)
   - Update `scripts/README.md` with new model info

2. **When changing memory requirements**:
   - Update `configure_wsl2_memory.ps1` memory value (line 27)
   - Update `increase_docker_memory.ps1` memory value (line 48)
   - Document reason for change in sprint completion report

3. **When adding new PowerShell scripts**:
   - Add entry to `scripts/README.md`
   - Document in this validation report
   - Follow naming convention: `verb_noun.ps1`

---

## Summary

**Validation Complete**: All 6 production PowerShell scripts are up-to-date ✅

**Scripts Updated**: 3 (setup_ollama_models.ps1, download_all_models.ps1, check_ollama_health.ps1)

**Scripts Archived**: 3 (2 bash duplicates, 1 old memory config)

**Current Models**:
- llama3.2:3b (chat, 2GB)
- gemma-3-4b-it-Q8_0 (extraction, 4.5GB)
- bge-m3 (embeddings, 2.2GB, 1024D)

**Last Updated**: Sprint 19 (2025-10-30)
**Next Review**: Sprint 20 or when upgrading models
