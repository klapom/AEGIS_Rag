# Data Directory

This directory contains generated data files that are **not** committed to Git.

## BM25 Index

### Location
- **File:** `bm25_index.pkl`
- **Size:** ~2.1 MB (for 933 documents)
- **Format:** Python pickle

### Generation

The BM25 index must be generated before using BM25 or Hybrid search:

#### Method 1: Using the init script
```bash
poetry run python scripts/init_bm25_index.py
```

#### Method 2: Via API endpoint
```bash
# Start the server
poetry run uvicorn src.api.main:app --reload

# Trigger BM25 index creation
curl -X POST http://localhost:8000/api/v1/bm25/prepare
```

#### Method 3: Programmatically
```python
from src.components.vector_search.bm25_search import BM25Search
from src.components.vector_search.qdrant_client import QdrantClientWrapper

# Initialize
bm25 = BM25Search()
qdrant = QdrantClientWrapper()

# Get documents from Qdrant
points = await qdrant.list_all_points(collection_name="aegis-rag")
documents = [{"text": p.payload["text"], **p.payload} for p in points]

# Fit BM25 index
bm25.fit(documents, text_field="text")

# Save index
bm25.save_index("data/bm25_index.pkl")
```

### Verification

Check if index exists and is valid:

```bash
poetry run python -c "
from src.components.vector_search.bm25_search import BM25Search
import os

index_path = 'data/bm25_index.pkl'
if os.path.exists(index_path):
    bm25 = BM25Search()
    bm25.load_index(index_path)
    print(f'✅ BM25 Index loaded: {bm25.get_corpus_size()} documents')
else:
    print('❌ BM25 Index not found. Run: poetry run python scripts/init_bm25_index.py')
"
```

### Regeneration

The index should be regenerated when:
- New documents are added to Qdrant
- Documents are updated in Qdrant
- After running document ingestion

**Note:** The index is automatically regenerated when calling `/api/v1/bm25/prepare` endpoint.

## Qdrant Data

Qdrant data is stored in Docker volumes, not in this directory:
- **Vector Store:** Docker volume `aegis_qdrant_data`
- **Location:** Managed by Docker
- **Persistence:** Survives container restarts

To inspect Qdrant data:
```bash
docker exec -it aegis-qdrant qdrant-cli collection info aegis-rag
```

## Other Data Files

This directory may also contain:
- `logs/` - Application logs (if file logging enabled)
- `exports/` - Exported data or reports
- `temp/` - Temporary processing files

All files in this directory are ignored by Git via `.gitignore`.
