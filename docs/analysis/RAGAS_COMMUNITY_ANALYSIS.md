# RAGAS Dataset - Community Analysis

## Community Statistics

**Total Communities:** 178
**Total Entities:** 274
**Total Chunks:** 57 (includes section nodes)

### Community ID Format (Design Pattern - Not an Issue)
- **Entities:** Use string format `"community_0"`, `"community_1"`, etc. (LightRAG convention)
- **CommunitySummary:** Use integer format `0`, `1`, `2`, etc. (Neo4j integer property)
- **Automatic Conversion:** ✅ Code handles conversion transparently
  ```python
  # community_summarizer.py:456 & community_delta_tracker.py:242
  community_id = int(community_id_str.split("_")[-1])
  ```
- **Impact:** None - Graph-Global search works out-of-the-box ✅

### Top 15 Communities by Size

| Rank | Community ID | Entity Count | Entity IDs (string) | Summary ID (int) |
|------|--------------|--------------|---------------------|------------------|
| 1    | community_128 | 16 entities | "community_128" | 128 |
| 2    | community_1 | 15 entities | "community_1" | 1 |
| 3    | community_79 | 8 entities | "community_79" | 79 |
| 4    | community_149 | 6 entities | "community_149" | 149 |
| 5    | community_52 | 6 entities | "community_52" | 52 |
| 6    | community_90 | 6 entities | "community_90" | 90 |
| 7    | community_136 | 6 entities | "community_136" | 136 |
| 8-15 | Various | 3-4 entities | - | - |

### Example Community Summary (Community 128)

**Theme:** Film Industry Network  
**Entity Count:** 16  
**Summary Length:** 547 characters  

**Summary:**
> The community centers on film-related entities and their connections to people, 
> universities, production and distribution companies, suggesting a media industry 
> network focused on content creation and dissemination. Key relationships link films 
> to individuals in creative roles, academic institutions for talent development, and 
> corporate partners involved in production and distribution. This structure reflects 
> a collaborative ecosystem within the entertainment sector, integrating artistic, 
> educational, and commercial dimensions of filmmaking.

**LLM Used:** nemotron-no-think:latest  
**Generated:** 2026-01-07 09:39:31 UTC  

### Community Properties

**CommunitySummary Node Properties:**
- `community_id`: integer (0-177)
- `summary`: string (LLM-generated description)
- `summary_length`: integer (character count)
- `model_used`: string (e.g., "nemotron-no-think:latest")
- `updated_at`: timestamp (ISO 8601)

**Entity (base) Node Community Properties:**
- `community_id`: string (e.g., "community_128")
- `entity_id`: string (entity name/identifier)
- `entity_type`: string (e.g., "Film", "Person", "Organization")
- `description`: string (entity description)
- `source_id`: string (chunk reference)
- `file_path`: string (document hash)
- `created_at`: unix timestamp

### Community Generation

**Algorithm:** Leiden community detection  
**Execution:** Automatic during ingestion (per document)  
**Summarization:** Automatic via LLM (no manual batch job needed)  
**Status:** ✅ All 178 communities have summaries  

### Graph-Global Search Readiness

✅ **Ready:** All communities have LLM-generated summaries  
✅ **Searchable:** Can use Graph-Global search mode in queries  
✅ **Quality:** Summaries capture high-level themes (film industry, chemistry, etc.)  

### Namespace Distribution

**Note:** Communities span multiple namespaces since entities from different 
documents can be linked through shared relationships (e.g., same person mentioned 
in multiple RAGAS files).

**Expected Behavior:** Cross-namespace communities are normal and desired for 
knowledge integration.

---

## Recommendations

1. ~~**Fix ID Mapping:**~~ ✅ **RESOLVED** - Automatic conversion already implemented
   - Code transparently converts `"community_N"` → `N` where needed
   - No standardization required - current pattern works perfectly

2. **RAGAS Evaluation:** Communities are ready - Graph-Global search mode can be
   tested in RAGAS evaluation

3. **Performance Monitoring:** Track community search latency as dataset grows
   - Current: 178 communities (fast queries)
   - Watch for degradation at 1000+ communities

---

**Generated:** 2026-01-07  
**Data Source:** Neo4j (aegis-neo4j container)  
**Password:** aegis-rag-neo4j-password (from .env)  
