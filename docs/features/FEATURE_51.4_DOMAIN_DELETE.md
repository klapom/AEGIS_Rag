# Feature 51.4: Domain DELETE Endpoint

**Sprint:** 51
**Status:** Implemented
**Date:** 2025-12-18

## Overview

Implemented a comprehensive domain deletion endpoint that performs cascading cleanup across all storage backends (Qdrant, Neo4j, BM25).

## Implementation

### Endpoint

```
DELETE /api/v1/admin/domains/{domain_name}
```

### Request

- **Path Parameter**: `domain_name` - Name of the domain to delete

### Response

**Status Code:** `200 OK`

**Response Model:** `DomainDeletionResponse`

```json
{
  "message": "Domain 'tech_docs' and all associated data deleted successfully",
  "domain_name": "tech_docs",
  "deleted_counts": {
    "qdrant_points": 150,
    "neo4j_entities": 75,
    "neo4j_chunks": 0,
    "neo4j_relationships": 120,
    "bm25_documents": 50
  },
  "warnings": []
}
```

### Deletion Process

The endpoint performs a cascading deletion across all storage backends:

1. **Validate Domain Exists**
   - Check if domain exists in Neo4j
   - Return 404 if not found

2. **Check Training Status**
   - Prevent deletion if domain is currently training
   - Return 409 CONFLICT if training in progress

3. **Delete Namespace Data** (via NamespaceManager)
   - Delete all Qdrant points with matching `namespace_id`
   - Delete all Neo4j nodes (entities, chunks) with matching `namespace_id`
   - Delete all Neo4j relationships associated with deleted nodes

4. **Clean BM25 Index**
   - Filter out documents from BM25 corpus with matching `namespace_id`
   - Rebuild BM25 index if corpus changed

5. **Delete Domain Configuration**
   - Delete Domain node from Neo4j
   - Delete all associated TrainingLog nodes

### Error Handling

| Status Code | Condition |
|-------------|-----------|
| 200 | Success - domain and all data deleted |
| 400 | Attempting to delete default 'general' domain |
| 404 | Domain not found |
| 409 | Domain is currently training |
| 500 | Internal server error during deletion |

### Partial Failure Handling

If cleanup of namespace data or BM25 index fails, the endpoint:
- Still deletes the domain configuration
- Returns warnings in the response
- Returns 200 status code
- Logs errors for monitoring

This ensures that even if external services (Qdrant, Neo4j) have issues, the domain can still be removed.

## Files Modified

### API Layer
- `src/api/v1/domain_training.py`
  - Added `DomainDeletionResponse` model
  - Enhanced `delete_domain()` endpoint with cascading cleanup
  - Updated module docstring

### Tests
- `tests/integration/api/test_domain_training_api.py`
  - Enhanced `test_delete_domain_success()` with namespace cleanup verification
  - Added `test_delete_domain_training_in_progress()` for 409 conflict
  - Added `test_delete_domain_partial_cleanup_warnings()` for partial failures
  - Added `test_delete_domain_empty_namespace()` for empty domains
  - Updated `test_delete_domain_returns_deletion_stats()` to expect 200 instead of 204

## Dependencies

The implementation leverages existing components:

- `src.core.namespace.NamespaceManager` - Handles Qdrant and Neo4j cleanup
- `src.components.domain_training.DomainRepository` - Handles domain configuration deletion
- `src.components.vector_search.bm25_retrieval.BM25Retrieval` - BM25 corpus cleanup

## Security Considerations

1. **Protected Domain**: The default 'general' domain cannot be deleted
2. **Training Lock**: Domains cannot be deleted while training is in progress
3. **Atomic-ish**: Domain configuration is only deleted after namespace cleanup succeeds or generates warnings

## Performance Characteristics

| Operation | Expected Time | Notes |
|-----------|--------------|-------|
| Namespace deletion (Qdrant) | <500ms | Depends on number of points |
| Namespace deletion (Neo4j) | <1s | Depends on number of entities/chunks |
| BM25 cleanup | <100ms | In-memory operation |
| Domain deletion | <50ms | Single Neo4j transaction |

**Total Expected Time:** <2s for typical domains with <1000 documents

## Usage Example

### Success Case

```bash
curl -X DELETE http://localhost:8000/api/v1/admin/domains/tech_docs
```

**Response:**
```json
{
  "message": "Domain 'tech_docs' and all associated data deleted successfully",
  "domain_name": "tech_docs",
  "deleted_counts": {
    "qdrant_points": 150,
    "neo4j_entities": 75,
    "neo4j_chunks": 0,
    "neo4j_relationships": 120,
    "bm25_documents": 50
  },
  "warnings": []
}
```

### Error: Training In Progress

```bash
curl -X DELETE http://localhost:8000/api/v1/admin/domains/tech_docs
```

**Response:**
```json
{
  "detail": "Cannot delete domain 'tech_docs' while training is in progress"
}
```

**Status Code:** 409 CONFLICT

### Error: Protected Domain

```bash
curl -X DELETE http://localhost:8000/api/v1/admin/domains/general
```

**Response:**
```json
{
  "detail": "Cannot delete default 'general' domain"
}
```

**Status Code:** 400 BAD REQUEST

## Testing

All tests pass with comprehensive coverage:

1. **Successful deletion** - Verifies all storage backends are cleaned
2. **Domain not found** - Returns 404
3. **Protected general domain** - Returns 400
4. **Training in progress** - Returns 409
5. **Partial cleanup failure** - Returns 200 with warnings
6. **Empty domain** - Handles domains with no documents

Run tests:
```bash
pytest tests/integration/api/test_domain_training_api.py -k "delete_domain" -v
```

## Frontend Integration

The frontend can call this endpoint using the existing `apiClient`:

```typescript
// In src/hooks/useDomainTraining.ts
export function useDeleteDomain() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutateAsync = useCallback(async (domainName: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.delete<DomainDeletionResponse>(
        `/admin/domains/${domainName}`
      );
      return response;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to delete domain');
      setError(error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { mutateAsync, isLoading, error };
}
```

## Future Enhancements

1. **Confirmation Dialog**: Add frontend confirmation dialog before deletion
2. **Soft Delete**: Implement soft delete with restoration capability
3. **Batch Delete**: Support deleting multiple domains at once
4. **Audit Log**: Log domain deletions for compliance
5. **Background Cleanup**: For large domains, run cleanup in background task

## References

- ADR-041: Namespace Isolation Layer
- Feature 45.4: Domain Training Admin UI
- `src/core/namespace.py` - NamespaceManager implementation
