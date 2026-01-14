# Scripts Directory

Production and utility scripts for AegisRAG.

**Last Updated**: Sprint 87 (2026-01-13)
**Platform**: DGX Spark (Linux ARM64, CUDA 13.0)

---

## Active Scripts (Sprint 82-87)

### RAGAS Benchmark (Sprint 82+)

| Script | Purpose | Usage |
|--------|---------|-------|
| `ragas_benchmark/` | RAGAS 1000-Sample Framework | Phase 1-3 benchmark infrastructure |
| `run_ragas_evaluation.py` | Run RAGAS evaluation | `poetry run python scripts/run_ragas_evaluation.py` |
| `run_ragas_on_namespace.py` | Evaluate specific namespace | `poetry run python scripts/run_ragas_on_namespace.py <ns>` |
| `ingest_ragas_simple.py` | Simple RAGAS ingestion | Quick ingestion for testing |
| `fetch_hotpotqa_questions.py` | Download HotpotQA | Fetch questions from HuggingFace |

### Sprint 87: BGE-M3 Native Hybrid Search

| Script | Purpose | Usage |
|--------|---------|-------|
| `test_flag_embedding.py` | Test FlagEmbedding service | `poetry run python scripts/test_flag_embedding.py` |
| `test_table_routing.py` | Verify CSV/XLSX routing | `poetry run python scripts/test_table_routing.py` |

### Document Upload

| Script | Purpose | Usage |
|--------|---------|-------|
| `upload_ragas_phase1.sh` | Upload RAGAS Phase 1 docs | Bash script for batch upload |
| `upload_ragas_phase1_resume.sh` | Resume interrupted upload | Continue from last uploaded |
| `upload_ragas_frontend.sh` | Upload via frontend API | Uses `/api/v1/retrieval/upload` |

---

## Quick Commands

```bash
# Test table format routing (CSV/XLSX → Docling)
poetry run python scripts/test_table_routing.py

# Test FlagEmbedding service (BGE-M3)
poetry run python scripts/test_flag_embedding.py

# Run RAGAS evaluation
poetry run python scripts/run_ragas_evaluation.py

# Upload documents
./scripts/upload_ragas_frontend.sh
```

---

## Directory Structure

```
scripts/
├── ragas_benchmark/          # Sprint 82+ RAGAS framework
│   ├── adapters/             # Dataset adapters (HotpotQA, RAGBench)
│   ├── build_phase1.py       # Build Phase 1 dataset
│   ├── sampling.py           # Stratified sampling
│   └── unanswerable.py       # Unanswerable question generation
├── test_flag_embedding.py    # Sprint 87: FlagEmbedding test
├── test_table_routing.py     # Sprint 89: Table routing validation
├── run_ragas_evaluation.py   # RAGAS evaluation runner
├── upload_*.sh               # Upload scripts
└── archive/                  # Archived scripts
    ├── docs-sprint30/        # Old documentation
    ├── sprint-20-30-obsolete/
    └── ...
```

---

## Archived Documentation

Old documentation moved to `archive/docs-sprint30/`:
- `DOCUMENTATION_SUMMARY.md` (Sprint 30)
- `POWERSHELL_VALIDATION_REPORT.md` (Windows-specific)
- `VALIDATION_REPORT.md` (Sprint 30)
- `README_PERFORMANCE.md` (Sprint 79)
- `README_PROFILING.md` (Sprint 79)

---

## Platform Notes

**DGX Spark (Current)**:
- All scripts run on DGX Spark (Linux ARM64)
- CUDA 13.0 / GB10 Blackwell GPU
- Docling container: `localhost:8080`
- Backend API: `localhost:8000`

**PowerShell Scripts (Legacy)**:
- Located in root `scripts/` directory
- For Windows development (not used on DGX Spark)
- See `archive/docs-sprint30/POWERSHELL_VALIDATION_REPORT.md`

---

## Adding New Scripts

1. **Naming**: Use `<verb>_<noun>.py` format
2. **Docstring**: Include sprint number and purpose
3. **Update README**: Add to appropriate section
4. **Archive old scripts**: Move to `archive/` when obsolete

---

**Total Active Scripts**: 15
**Archived**: 70+ scripts
**Last Cleanup**: Sprint 87 (2026-01-13)
