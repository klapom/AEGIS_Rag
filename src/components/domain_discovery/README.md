# Domain Auto-Discovery Component

**Sprint 117 - Feature 117.3**

Automatic domain discovery from sample documents using document clustering and LLM analysis.

---

## Quick Start

```python
from src.components.domain_discovery import get_domain_discovery_service

# Initialize service
service = get_domain_discovery_service()

# Discover domains from sample documents
result = await service.discover_domains(
    sample_documents=[
        "Patient with diabetes and hypertension.",
        "Stock price of AAPL increased 3%.",
        "Legal contract for service agreement."
    ],
    suggested_count=3
)

# Print discovered domains
for domain in result.discovered_domains:
    print(f"Domain: {domain.name}")
    print(f"Confidence: {domain.confidence}")
    print(f"Entity Types: {domain.entity_types}")
    print(f"Relation Types: {domain.relation_types}")
    print()
```

---

## Architecture

```
Sample Documents (3-10)
    ↓
BGE-M3 Embeddings (1024D)
    ↓
K-means Clustering
    ↓
Parallel LLM Analysis (per cluster)
    ↓
Domain Suggestions
    - name
    - entity_types
    - relation_types (includes MENTIONED_IN)
    - intent_classes
    - confidence
```

---

## API Endpoint

**POST** `/api/v1/admin/domains/discover`

### Request

```json
{
  "sample_documents": [
    "Document 1 text",
    "Document 2 text",
    "Document 3 text"
  ],
  "min_samples": 3,
  "max_samples": 10,
  "suggested_count": 5
}
```

### Response

```json
{
  "discovered_domains": [
    {
      "name": "medical",
      "suggested_description": "Medical domain...",
      "confidence": 0.92,
      "entity_types": ["Disease", "Treatment"],
      "relation_types": ["TREATS", "MENTIONED_IN"],
      "intent_classes": ["symptom_inquiry"],
      "sample_entities": {"Disease": ["diabetes"]},
      "recommended_model_family": "medical",
      "reasoning": "Documents contain clinical terminology"
    }
  ],
  "processing_time_ms": 5420,
  "documents_analyzed": 3,
  "clusters_found": 1
}
```

---

## Features

- ✅ **BGE-M3 Embeddings**: Dense 1024D vectors for semantic clustering
- ✅ **K-means Clustering**: Automatic grouping of similar documents
- ✅ **Parallel LLM Analysis**: Concurrent cluster processing
- ✅ **Entity/Relation Discovery**: Automatic type extraction
- ✅ **MENTIONED_IN Guarantee**: Always included for provenance
- ✅ **Confidence Scoring**: Based on cluster cohesion
- ✅ **LangSmith Tracing**: Full observability

---

## Performance

| Operation | Time |
|-----------|------|
| Embedding (per doc) | ~120ms |
| Clustering (10 docs) | ~5ms |
| LLM Analysis (per cluster) | ~8s |
| **Total (3 docs, 1 cluster)** | **~10s** |
| **Total (6 docs, 2 clusters)** | **~18s** |

---

## Configuration

```python
service = DomainDiscoveryService(
    llm_model="qwen3:32b",        # LLM for analysis
    ollama_base_url="http://localhost:11434",
    min_samples=3,                # Minimum documents required
    max_samples=10                # Maximum documents to analyze
)
```

---

## Testing

```bash
# Run unit tests
pytest tests/unit/components/domain_discovery/ -v

# Run integration tests
pytest tests/integration/api/test_domain_discovery_api.py -v
```

---

## Dependencies

- `httpx` - Ollama API calls
- `numpy` - Embeddings
- `scikit-learn` - K-means clustering
- `langsmith` - Tracing
- `pydantic` - Models

---

## Files

- `discovery_service.py` - Core discovery logic
- `__init__.py` - Public API
- `README.md` - This file

---

## Related Documentation

- [Sprint 117 Plan](../../../docs/sprints/SPRINT_117_PLAN.md)
- [Implementation Summary](../../../docs/sprints/SPRINT_117_FEATURE_3_IMPLEMENTATION.md)
- [Unit Tests](../../../tests/unit/components/domain_discovery/)
- [Integration Tests](../../../tests/integration/api/test_domain_discovery_api.py)
