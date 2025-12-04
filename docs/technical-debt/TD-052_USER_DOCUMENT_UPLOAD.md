# TD-052: User Document Upload Interface (Sprint 10)

**Status:** OPEN
**Priority:** MEDIUM
**Severity:** Feature Gap
**Original Sprint:** Sprint 10
**Story Points:** 13 SP
**Created:** 2025-12-04

---

## Problem Statement

While Admin document indexing exists (AdminIndexingPage), there is no user-facing document upload interface for user-specific documents. End users cannot upload their own documents for personal knowledge bases.

**Current State:**
- Admin can index directories via AdminIndexingPage
- Documents are indexed into shared knowledge base
- **Missing:** User-specific document upload
- **Missing:** Personal document collections
- **Missing:** Document access control (user-owned documents)

---

## Use Cases

### UC-1: Personal Document Upload
A user wants to upload a PDF report for personal reference and querying.

### UC-2: Project-Specific Knowledge
A team wants to create a project-specific document collection.

### UC-3: Temporary Document Analysis
A user wants to analyze a document without permanently storing it.

---

## Solution Architecture

### 1. User Document Collections

```python
# Data Model
class UserDocument(BaseModel):
    document_id: str
    user_id: str
    filename: str
    file_type: str
    file_size: int
    upload_timestamp: datetime
    collection_id: Optional[str]  # For grouping
    is_temporary: bool = False
    ttl_hours: Optional[int] = None

class DocumentCollection(BaseModel):
    collection_id: str
    user_id: str
    name: str
    document_count: int
    created_at: datetime
```

### 2. Upload Pipeline

```python
# src/api/v1/documents.py

@router.post("/api/v1/documents/upload")
async def upload_document(
    file: UploadFile,
    user_id: str = Depends(get_current_user),
    collection_id: Optional[str] = None,
    is_temporary: bool = False,
    ttl_hours: Optional[int] = 24
) -> DocumentUploadResponse:
    """Upload a document for personal use."""
    # 1. Validate file type and size
    validate_upload(file)

    # 2. Store file temporarily
    file_path = await store_temp_file(file)

    # 3. Parse with Docling
    parsed = await docling_client.parse_document(file_path)

    # 4. Index to user's namespace in Qdrant
    await index_to_user_namespace(
        user_id=user_id,
        document=parsed,
        collection_id=collection_id
    )

    # 5. Track in user's document list
    doc = await create_user_document(
        user_id=user_id,
        filename=file.filename,
        collection_id=collection_id,
        is_temporary=is_temporary,
        ttl_hours=ttl_hours
    )

    return DocumentUploadResponse(
        document_id=doc.document_id,
        status="indexed",
        chunks_created=parsed.chunk_count
    )
```

### 3. User Namespace Isolation (Qdrant)

```python
# src/components/vector_search/user_namespace.py

class UserNamespaceManager:
    """Manage user-specific document namespaces."""

    def get_user_collection(self, user_id: str) -> str:
        """Get or create user's Qdrant collection."""
        collection_name = f"user_{user_id}_documents"
        if not self.qdrant.collection_exists(collection_name):
            self.qdrant.create_collection(
                collection_name,
                vectors_config=VectorParams(
                    size=1024,  # BGE-M3
                    distance=Distance.COSINE
                )
            )
        return collection_name

    async def search_user_documents(
        self,
        user_id: str,
        query: str,
        limit: int = 10
    ) -> List[SearchResult]:
        """Search only in user's documents."""
        collection = self.get_user_collection(user_id)
        return await self.qdrant.search(
            collection_name=collection,
            query_vector=await self.embed(query),
            limit=limit
        )
```

### 4. Frontend Upload Component

```tsx
// frontend/src/components/documents/DocumentUpload.tsx

interface DocumentUploadProps {
    onUploadComplete: (doc: UserDocument) => void;
    collectionId?: string;
}

export function DocumentUpload({ onUploadComplete, collectionId }: DocumentUploadProps) {
    const [uploading, setUploading] = useState(false);
    const [progress, setProgress] = useState(0);

    const handleDrop = async (files: File[]) => {
        setUploading(true);
        for (const file of files) {
            const formData = new FormData();
            formData.append('file', file);
            if (collectionId) {
                formData.append('collection_id', collectionId);
            }

            const response = await api.uploadDocument(formData, {
                onUploadProgress: (p) => setProgress(p.loaded / p.total * 100)
            });

            onUploadComplete(response.data);
        }
        setUploading(false);
    };

    return (
        <div
            className="border-2 border-dashed rounded-lg p-8 text-center"
            onDrop={handleDrop}
        >
            <Upload className="mx-auto h-12 w-12 text-gray-400" />
            <p>Drag & drop documents here, or click to browse</p>
            <p className="text-sm text-gray-500">
                Supported: PDF, DOCX, PPTX, TXT (max 50MB)
            </p>
            {uploading && <ProgressBar value={progress} />}
        </div>
    );
}
```

### 5. Document Management UI

```tsx
// frontend/src/pages/DocumentsPage.tsx

export function DocumentsPage() {
    const { documents, collections } = useUserDocuments();

    return (
        <div className="container mx-auto p-6">
            <h1>My Documents</h1>

            {/* Upload Section */}
            <DocumentUpload onUploadComplete={refetch} />

            {/* Collections */}
            <div className="mt-8">
                <h2>Collections</h2>
                <CollectionList collections={collections} />
            </div>

            {/* Recent Documents */}
            <div className="mt-8">
                <h2>Recent Documents</h2>
                <DocumentList documents={documents} />
            </div>
        </div>
    );
}
```

---

## Implementation Tasks

### Phase 1: Backend Upload API (5 SP)
- [ ] Create document upload endpoint
- [ ] File validation (type, size)
- [ ] Temp file storage
- [ ] Docling integration for parsing
- [ ] Unit tests

### Phase 2: User Namespace in Qdrant (3 SP)
- [ ] UserNamespaceManager class
- [ ] User-specific collections
- [ ] Isolated search within user namespace
- [ ] Integration tests

### Phase 3: Frontend Upload UI (3 SP)
- [ ] DocumentUpload component (drag & drop)
- [ ] Progress indicator
- [ ] DocumentsPage with list view
- [ ] Collection management UI

### Phase 4: Document Management (2 SP)
- [ ] Document deletion
- [ ] Temporary document TTL cleanup
- [ ] Document metadata editing
- [ ] E2E tests

---

## Acceptance Criteria

- [ ] User can upload PDF, DOCX, PPTX, TXT files
- [ ] Files are indexed to user's personal namespace
- [ ] User can only search their own documents
- [ ] Drag & drop upload works
- [ ] Progress indicator during upload
- [ ] Documents can be deleted
- [ ] Temporary documents auto-expire
- [ ] File size limit enforced (50MB)
- [ ] 80%+ test coverage

---

## Security Considerations

- **Isolation:** User documents stored in separate Qdrant collections
- **Access Control:** Only document owner can access/delete
- **File Validation:** Check file type, scan for malware
- **Size Limits:** 50MB per file, 500MB total per user
- **Cleanup:** Temporary files deleted after processing

---

## Affected Files

```
src/api/v1/documents.py                 # NEW: Upload endpoints
src/components/vector_search/
├── user_namespace.py                   # NEW: User namespace manager
└── qdrant_client.py                    # Update for multi-collection

frontend/src/
├── pages/DocumentsPage.tsx             # NEW: Documents page
├── components/documents/
│   ├── DocumentUpload.tsx              # NEW: Upload component
│   ├── DocumentList.tsx                # NEW: Document list
│   └── CollectionList.tsx              # NEW: Collections
└── api/documents.ts                    # NEW: Documents API client
```

---

## Dependencies

- Docling Container (document parsing)
- Qdrant (vector storage)
- File storage (local or S3)

---

## Estimated Effort

**Story Points:** 13 SP

**Breakdown:**
- Phase 1 (Backend): 5 SP
- Phase 2 (Namespace): 3 SP
- Phase 3 (Frontend): 3 SP
- Phase 4 (Management): 2 SP

---

## References

- [SPRINT_PLAN.md - Sprint 10](../sprints/SPRINT_PLAN.md#sprint-10)

---

## Target Sprint

**Recommended:** Sprint 39 or 40

---

**Last Updated:** 2025-12-04
