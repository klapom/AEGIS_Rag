# Sprint 22: Project Collaboration System

**Status:** 📋 PLANNED
**Goal:** Implement full project-based collaboration with document management + Project Memory (optional)
**Duration:** 6-7 days (estimated)
**Prerequisites:** Sprint 21 complete (Auth + Multi-Tenancy + mem0 User Preferences)
**Story Points:** 29-34 SP (29 SP base + optional 5 SP for Feature 22.5)

---

## 🎯 Sprint Objectives

### **Primary Goals:**
1. Implement complete project management API
2. Build project member collaboration system
3. Create document upload & processing pipeline
4. Implement project-scoped sessions
5. Build project-aware RAG (Qdrant + Graphiti)
6. Deliver polished frontend project UI
7. **OPTIONAL: Extend mem0 with project-level memory**

### **Success Criteria:**
- ✅ Users can create and manage projects
- ✅ Users can invite team members to projects
- ✅ Users can upload documents to projects (all members can access)
- ✅ All sessions belong to projects
- ✅ RAG searches only project documents
- ✅ Knowledge graph isolated per project
- ✅ Intuitive project UI with drag-and-drop
- ✅ **OPTIONAL: Project-specific preferences learned (Feature 22.5)**

---

## 📦 Sprint Features

### Feature 22.1: Project Management API (8 SP)
**Priority:** HIGH - Foundation for collaboration
**Duration:** 2 days

#### **Problem:**
No concept of projects exists. Users need to organize their work into separate knowledge domains that can be shared with colleagues.

#### **Solution:**
Complete CRUD API for projects with role-based member management.

#### **Project Hierarchy:**
```
Organization
  └── Users (colleagues)
       └── Projects (shared workspaces)
            ├── Owner (creator)
            ├── Members (collaborators with roles)
            ├── Documents (shared knowledge base)
            ├── Sessions (conversations)
            └── Knowledge Graph (shared entities)
```

#### **Tasks:**
- [ ] **Project CRUD API**
  ```
  POST   /api/v1/projects              - Create project
  GET    /api/v1/projects              - List user's projects
  GET    /api/v1/projects/{id}         - Get project details
  PATCH  /api/v1/projects/{id}         - Update project
  DELETE /api/v1/projects/{id}         - Delete project (soft)
  POST   /api/v1/projects/{id}/archive - Archive project
  ```

- [ ] **Project Member Management**
  ```
  POST   /api/v1/projects/{id}/members           - Add member
  GET    /api/v1/projects/{id}/members           - List members
  PATCH  /api/v1/projects/{id}/members/{user_id} - Update role
  DELETE /api/v1/projects/{id}/members/{user_id} - Remove member
  ```

- [ ] **Project Statistics**
  ```
  GET /api/v1/projects/{id}/stats - Get project stats
  ```

- [ ] **Authorization Layer**
  - Owner can do everything
  - Editor can add documents, create sessions
  - Viewer can only read
  - Commenter can add messages

- [ ] **Activity Logging**
  - Track all project changes
  - Member additions/removals
  - Document uploads
  - Session creation

#### **API Implementation:**

```python
# src/api/v1/projects.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from uuid import UUID

from src.core.auth import get_current_user, require_project_access
from src.core.database import get_db
from src.models.database import User, Project, ProjectMember, ProjectRole, ProjectVisibility
from src.repositories.project import ProjectRepository
from src.repositories.project_member import ProjectMemberRepository

router = APIRouter(prefix="/projects", tags=["projects"])

# =====================================================
# REQUEST/RESPONSE MODELS
# =====================================================

class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    color: str = Field(default="#3B82F6", pattern="^#[0-9A-Fa-f]{6}$")
    emoji: str = Field(default="📁", max_length=10)
    visibility: ProjectVisibility = ProjectVisibility.TEAM

class UpdateProjectRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    emoji: Optional[str] = Field(None, max_length=10)
    visibility: Optional[ProjectVisibility] = None
    settings: Optional[dict] = None

class AddMemberRequest(BaseModel):
    user_id: UUID
    role: ProjectRole = ProjectRole.EDITOR

class UpdateMemberRequest(BaseModel):
    role: ProjectRole

class ProjectResponse(BaseModel):
    id: UUID
    organization_id: UUID
    owner_id: UUID
    name: str
    description: Optional[str]
    color: str
    emoji: str
    visibility: ProjectVisibility
    session_count: int
    document_count: int
    message_count: int
    member_count: int
    storage_bytes: int
    created_at: datetime
    updated_at: datetime
    last_activity_at: datetime

    # User's role in this project
    user_role: Optional[ProjectRole] = None

class ProjectMemberResponse(BaseModel):
    id: UUID
    user_id: UUID
    user_name: str
    user_email: str
    user_avatar_url: Optional[str]
    role: ProjectRole
    added_at: datetime
    added_by: UUID
    is_favorite: bool
    last_viewed_at: Optional[datetime]

# =====================================================
# PROJECT CRUD ENDPOINTS
# =====================================================

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: CreateProjectRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create new project.

    User automatically becomes owner and first member.
    """
    project_repo = ProjectRepository(Project, db)
    member_repo = ProjectMemberRepository(ProjectMember, db)

    # Check organization project quota
    org_projects = await project_repo.count_by_organization(user.organization_id)
    if org_projects >= user.organization.max_projects:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Organization project limit reached ({user.organization.max_projects})"
        )

    # Create project
    project = Project(
        organization_id=user.organization_id,
        owner_id=user.id,
        name=request.name,
        description=request.description,
        color=request.color,
        emoji=request.emoji,
        visibility=request.visibility,
        member_count=1,
    )
    project = await project_repo.create(project)

    # Add owner as member
    member = ProjectMember(
        project_id=project.id,
        user_id=user.id,
        role=ProjectRole.OWNER,
        added_by=user.id,
    )
    await member_repo.create(member)

    logger.info(
        "Project created",
        project_id=str(project.id),
        owner_id=str(user.id),
        name=project.name,
    )

    return ProjectResponse(**project.model_dump(), user_role=ProjectRole.OWNER)

@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
    favorites_only: bool = False,
):
    """List user's projects.

    Includes:
    - Projects where user is member
    - Org-wide visible projects
    """
    project_repo = ProjectRepository(Project, db)

    projects = await project_repo.list_for_user(
        user_id=user.id,
        org_id=user.organization_id,
        favorites_only=favorites_only,
        limit=limit,
        offset=offset,
    )

    # Enrich with user's role
    member_repo = ProjectMemberRepository(ProjectMember, db)
    results = []

    for project in projects:
        member = await member_repo.get_by_project_and_user(project.id, user.id)
        user_role = member.role if member else None

        results.append(
            ProjectResponse(**project.model_dump(), user_role=user_role)
        )

    return results

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project: Project = Depends(require_project_access),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get project details."""
    member_repo = ProjectMemberRepository(ProjectMember, db)
    member = await member_repo.get_by_project_and_user(project.id, user.id)

    return ProjectResponse(**project.model_dump(), user_role=member.role if member else None)

@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    request: UpdateProjectRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update project (owner/editor only)."""
    project_repo = ProjectRepository(Project, db)

    # Check access (editor or higher)
    project = await require_project_access(
        project_id=project_id,
        user=user,
        db=db,
        required_role=ProjectRole.EDITOR,
    )

    # Update fields
    update_data = request.model_dump(exclude_unset=True)
    if update_data:
        project = await project_repo.update(UUID(project_id), **update_data)

    logger.info(
        "Project updated",
        project_id=project_id,
        user_id=str(user.id),
        changes=list(update_data.keys()),
    )

    member_repo = ProjectMemberRepository(ProjectMember, db)
    member = await member_repo.get_by_project_and_user(project.id, user.id)

    return ProjectResponse(**project.model_dump(), user_role=member.role)

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete project (owner only).

    Soft delete - marks project and all children as deleted.
    """
    project_repo = ProjectRepository(Project, db)

    # Check ownership
    project = await project_repo.get_by_id(UUID(project_id))
    if not project or project.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project owner can delete"
        )

    # Soft delete
    await project_repo.delete(UUID(project_id), soft=True)

    logger.warning(
        "Project deleted",
        project_id=project_id,
        owner_id=str(user.id),
    )

# =====================================================
# PROJECT MEMBER MANAGEMENT
# =====================================================

@router.post("/{project_id}/members", response_model=ProjectMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_project_member(
    project_id: str,
    request: AddMemberRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add member to project (owner/editor only)."""
    project_repo = ProjectRepository(Project, db)
    member_repo = ProjectMemberRepository(ProjectMember, db)
    user_repo = UserRepository(User, db)

    # Check access (editor or higher can invite)
    project = await require_project_access(
        project_id=project_id,
        user=user,
        db=db,
        required_role=ProjectRole.EDITOR,
    )

    # Check target user exists and same org
    target_user = await user_repo.get_by_id(request.user_id)
    if not target_user:
        raise HTTPException(404, "User not found")

    if target_user.organization_id != user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only add users from same organization"
        )

    # Check not already member
    existing = await member_repo.get_by_project_and_user(UUID(project_id), request.user_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member"
        )

    # Add member
    member = ProjectMember(
        project_id=UUID(project_id),
        user_id=request.user_id,
        role=request.role,
        added_by=user.id,
    )
    member = await member_repo.create(member)

    # Update project member count
    await project_repo.update(
        UUID(project_id),
        member_count=project.member_count + 1
    )

    # TODO: Send notification to new member

    logger.info(
        "Project member added",
        project_id=project_id,
        user_id=str(request.user_id),
        role=request.role,
        added_by=str(user.id),
    )

    return ProjectMemberResponse(
        **member.model_dump(),
        user_name=target_user.name,
        user_email=target_user.email,
        user_avatar_url=target_user.avatar_url,
    )

@router.get("/{project_id}/members", response_model=list[ProjectMemberResponse])
async def list_project_members(
    project: Project = Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
):
    """List project members."""
    member_repo = ProjectMemberRepository(ProjectMember, db)
    user_repo = UserRepository(User, db)

    members = await member_repo.list_by_project(project.id)

    results = []
    for member in members:
        user = await user_repo.get_by_id(member.user_id)
        results.append(
            ProjectMemberResponse(
                **member.model_dump(),
                user_name=user.name,
                user_email=user.email,
                user_avatar_url=user.avatar_url,
            )
        )

    return results

@router.patch("/{project_id}/members/{user_id}", response_model=ProjectMemberResponse)
async def update_project_member(
    project_id: str,
    user_id: str,
    request: UpdateMemberRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update member role (owner only)."""
    project_repo = ProjectRepository(Project, db)
    member_repo = ProjectMemberRepository(ProjectMember, db)

    # Check ownership
    project = await project_repo.get_by_id(UUID(project_id))
    if not project or project.owner_id != current_user.id:
        raise HTTPException(403, "Only owner can change roles")

    # Cannot change owner's role
    if UUID(user_id) == project.owner_id:
        raise HTTPException(400, "Cannot change owner's role")

    # Update role
    member = await member_repo.get_by_project_and_user(UUID(project_id), UUID(user_id))
    if not member:
        raise HTTPException(404, "Member not found")

    await member_repo.update(member.id, role=request.role)

    logger.info(
        "Project member role updated",
        project_id=project_id,
        user_id=user_id,
        new_role=request.role,
    )

    user = await user_repo.get_by_id(UUID(user_id))
    return ProjectMemberResponse(
        **member.model_dump(),
        user_name=user.name,
        user_email=user.email,
        user_avatar_url=user.avatar_url,
    )

@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project_member(
    project_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove member from project (owner only or self-removal)."""
    project_repo = ProjectRepository(Project, db)
    member_repo = ProjectMemberRepository(ProjectMember, db)

    project = await project_repo.get_by_id(UUID(project_id))

    # Allow self-removal or owner removal
    if UUID(user_id) != current_user.id and project.owner_id != current_user.id:
        raise HTTPException(403, "Only owner can remove other members")

    # Cannot remove owner
    if UUID(user_id) == project.owner_id:
        raise HTTPException(400, "Cannot remove project owner")

    # Remove member
    member = await member_repo.get_by_project_and_user(UUID(project_id), UUID(user_id))
    if not member:
        raise HTTPException(404, "Member not found")

    await member_repo.delete(member.id)

    # Update member count
    await project_repo.update(
        UUID(project_id),
        member_count=project.member_count - 1
    )

    logger.info(
        "Project member removed",
        project_id=project_id,
        user_id=user_id,
        removed_by=str(current_user.id),
    )

# =====================================================
# PROJECT STATISTICS
# =====================================================

@router.get("/{project_id}/stats")
async def get_project_stats(
    project: Project = Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
):
    """Get project statistics."""
    session_repo = SessionRepository(Session, db)
    document_repo = DocumentRepository(ProjectDocument, db)
    message_repo = MessageRepository(Message, db)

    # Get counts
    sessions = await session_repo.count_by_project(project.id)
    documents = await document_repo.count_by_project(project.id)
    messages = await message_repo.count_by_project(project.id)

    # Get recent activity
    recent_sessions = await session_repo.list_by_project(
        project.id,
        limit=5,
        order_by="last_message_at"
    )

    recent_documents = await document_repo.list_by_project(
        project.id,
        limit=5,
        order_by="uploaded_at"
    )

    return {
        "counts": {
            "sessions": sessions,
            "documents": documents,
            "messages": messages,
            "members": project.member_count,
        },
        "storage": {
            "bytes": project.storage_bytes,
            "mb": round(project.storage_bytes / (1024 * 1024), 2),
            "gb": round(project.storage_bytes / (1024 * 1024 * 1024), 2),
        },
        "recent_activity": {
            "sessions": [s.model_dump() for s in recent_sessions],
            "documents": [d.model_dump() for d in recent_documents],
        },
        "last_activity_at": project.last_activity_at,
    }
```

#### **Deliverables:**
```bash
src/api/v1/projects.py
src/repositories/project.py
src/repositories/project_member.py
tests/api/test_projects.py
tests/api/test_project_members.py
docs/api/PROJECT_API.md
```

#### **Acceptance Criteria:**
- ✅ Users can create projects
- ✅ Users can list their projects
- ✅ Users can update project details
- ✅ Users can delete projects (soft delete)
- ✅ Users can add/remove members
- ✅ Role-based access control works
- ✅ Member count updated automatically
- ✅ Activity timestamps tracked
- ✅ Statistics API accurate

---

### Feature 22.2: Project Documents (8 SP)
**Priority:** HIGH - Core collaboration feature
**Duration:** 2 days

#### **Problem:**
No file upload system. Users cannot add documents to projects for RAG.

#### **Solution:**
Complete document management system with async processing, Qdrant indexing, and project-scoped collections.

#### **Document Lifecycle:**
```
1. UPLOAD
   User uploads file → Validate → Save to disk → Create DB record

2. PROCESSING
   Background job → Extract text (LlamaParse) → Chunk → Embed → Index Qdrant

3. READY
   Document searchable in project → All sessions can use it

4. DELETE
   Remove from disk → Remove from Qdrant → Delete DB record
```

#### **Tasks:**
- [ ] **File Upload API**
  ```
  POST   /api/v1/projects/{id}/documents/upload
  GET    /api/v1/projects/{id}/documents
  GET    /api/v1/projects/{id}/documents/{doc_id}
  DELETE /api/v1/projects/{id}/documents/{doc_id}
  ```

- [ ] **File Storage**
  - Directory structure: `/uploads/{org_id}/{project_id}/{doc_id}/`
  - Support: PDF, DOCX, TXT, MD, CSV
  - Max file size check
  - MIME type validation

- [ ] **Async Processing**
  - Celery task or FastAPI BackgroundTasks
  - LlamaParse text extraction
  - Chunking strategy (semantic or fixed-size)
  - BGE-M3 embeddings
  - Qdrant indexing

- [ ] **Qdrant Integration**
  - Collection per project: `project_{project_id}`
  - Point payload: `{text, document_id, chunk_index, metadata}`
  - User filtering in searches

- [ ] **Quota Management**
  - Check project storage limit
  - Check org storage limit
  - Update storage_bytes on upload/delete

#### **Implementation:**

```python
# src/api/v1/documents.py
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from pathlib import Path
import shutil

from src.core.auth import get_current_user, require_project_access
from src.models.database import ProjectDocument, Project, User
from src.repositories.document import DocumentRepository
from src.components.document_processing import process_document

router = APIRouter()

UPLOAD_DIR = Path("./uploads")
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # DOCX
    "text/plain",
    "text/markdown",
    "text/csv",
}

@router.post("/projects/{project_id}/documents/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    project_id: str,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks,
    project: Project = Depends(require_project_access),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload document to project.

    Requires editor role or higher.
    """
    # Validate file
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(400, f"File type {file.content_type} not supported")

    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(413, "File too large (max 100MB)")

    # Check project storage quota
    if project.storage_bytes + file_size > project.settings.get("max_storage_bytes", 1024**3):
        raise HTTPException(507, "Project storage quota exceeded")

    # Create document directory
    doc_id = str(uuid4())
    doc_dir = UPLOAD_DIR / str(project.organization_id) / project_id / doc_id
    doc_dir.mkdir(parents=True, exist_ok=True)

    # Save file
    file_path = doc_dir / file.filename
    with file_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    # Create database record
    document = ProjectDocument(
        project_id=UUID(project_id),
        uploaded_by=user.id,
        filename=file.filename,
        file_path=str(file_path),
        file_size_bytes=file_size,
        mime_type=file.content_type,
        status="pending",
        qdrant_collection=f"project_{project_id}",
    )

    doc_repo = DocumentRepository(ProjectDocument, db)
    document = await doc_repo.create(document)

    # Update project storage
    project_repo = ProjectRepository(Project, db)
    await project_repo.update(
        UUID(project_id),
        storage_bytes=project.storage_bytes + file_size,
        document_count=project.document_count + 1,
    )

    # Process document in background
    background_tasks.add_task(
        process_document,
        document_id=str(document.id),
        project_id=project_id,
    )

    logger.info(
        "Document uploaded",
        document_id=str(document.id),
        project_id=project_id,
        filename=file.filename,
        size_mb=round(file_size / (1024 * 1024), 2),
    )

    return document

@router.get("/projects/{project_id}/documents")
async def list_project_documents(
    project: Project = Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
    status: Optional[str] = None,
):
    """List project documents."""
    doc_repo = DocumentRepository(ProjectDocument, db)

    documents = await doc_repo.list_by_project(
        project.id,
        status_filter=status,
    )

    return documents

@router.delete("/projects/{project_id}/documents/{doc_id}", status_code=204)
async def delete_document(
    project_id: str,
    doc_id: str,
    project: Project = Depends(require_project_access),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete document (uploader or owner only)."""
    doc_repo = DocumentRepository(ProjectDocument, db)

    document = await doc_repo.get_by_id(UUID(doc_id))
    if not document:
        raise HTTPException(404, "Document not found")

    # Check permission (uploader or owner)
    if document.uploaded_by != user.id and project.owner_id != user.id:
        raise HTTPException(403, "Only uploader or project owner can delete")

    # Delete from Qdrant
    from src.components.vector_search import get_qdrant_client
    qdrant = get_qdrant_client()
    await qdrant.delete_document_chunks(
        collection_name=document.qdrant_collection,
        document_id=str(document.id),
    )

    # Delete file from disk
    Path(document.file_path).unlink(missing_ok=True)

    # Update project storage
    project_repo = ProjectRepository(Project, db)
    await project_repo.update(
        UUID(project_id),
        storage_bytes=max(0, project.storage_bytes - document.file_size_bytes),
        document_count=max(0, project.document_count - 1),
    )

    # Delete from database
    await doc_repo.delete(UUID(doc_id))

    logger.info(
        "Document deleted",
        document_id=doc_id,
        project_id=project_id,
    )
```

```python
# src/components/document_processing.py
async def process_document(document_id: str, project_id: str):
    """Background task: Process uploaded document."""
    from src.core.database import AsyncSessionLocal
    from src.repositories.document import DocumentRepository
    from src.models.database import ProjectDocument

    async with AsyncSessionLocal() as db:
        doc_repo = DocumentRepository(ProjectDocument, db)
        document = await doc_repo.get_by_id(UUID(document_id))

        if not document:
            logger.error("Document not found", document_id=document_id)
            return

        try:
            # Update status
            await doc_repo.update(UUID(document_id), status="processing")

            # 1. Extract text
            logger.info("Extracting text", document_id=document_id)
            from src.components.text_extraction import extract_text
            text = await extract_text(
                file_path=document.file_path,
                mime_type=document.mime_type,
            )

            # 2. Chunk text
            logger.info("Chunking text", document_id=document_id)
            from src.components.chunking import chunk_text
            chunks = await chunk_text(
                text=text,
                chunk_size=512,
                chunk_overlap=50,
            )

            # 3. Generate embeddings
            logger.info("Generating embeddings", document_id=document_id, chunks=len(chunks))
            from src.components.embeddings import get_embedding_model
            embedding_model = get_embedding_model()
            embeddings = await embedding_model.embed_batch([c.text for c in chunks])

            # 4. Index in Qdrant
            logger.info("Indexing in Qdrant", document_id=document_id)
            from src.components.vector_search import get_qdrant_client
            qdrant = get_qdrant_client()

            collection = f"project_{project_id}"
            await qdrant.ensure_collection(collection, embedding_dim=1024)

            points = []
            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                points.append(PointStruct(
                    id=f"{document_id}_{idx}",
                    vector=embedding,
                    payload={
                        "text": chunk.text,
                        "document_id": document_id,
                        "project_id": project_id,
                        "chunk_index": idx,
                        "filename": document.filename,
                        "page_number": chunk.metadata.get("page_number"),
                    }
                ))

            await qdrant.upsert(collection, points)

            # 5. Update document status
            await doc_repo.update(
                UUID(document_id),
                status="ready",
                chunk_count=len(chunks),
                embedding_model="bge-m3",
                processed_at=datetime.now(timezone.utc),
                metadata={
                    "processing_time_seconds": (datetime.now(timezone.utc) - document.uploaded_at).total_seconds(),
                    "language": "de",  # TODO: Detect language
                },
            )

            logger.info(
                "Document processed successfully",
                document_id=document_id,
                chunks=len(chunks),
            )

        except Exception as e:
            logger.error(
                "Document processing failed",
                document_id=document_id,
                error=str(e),
            )
            await doc_repo.update(
                UUID(document_id),
                status="error",
                metadata={"error_message": str(e)},
            )
```

#### **Deliverables:**
```bash
src/api/v1/documents.py
src/components/document_processing.py
src/components/text_extraction.py
src/components/chunking.py
src/repositories/document.py
tests/api/test_documents.py
tests/components/test_document_processing.py
```

#### **Acceptance Criteria:**
- ✅ Users can upload documents to projects
- ✅ File validation works (type, size)
- ✅ Async processing pipeline works
- ✅ Documents indexed in project collection
- ✅ Storage quotas enforced
- ✅ Chunk metadata preserved
- ✅ Deletion cleanup complete

---

### Feature 22.3: Project Sessions (5 SP)
**Priority:** HIGH
**Duration:** 1.5 days

#### **Problem:**
Sessions are currently global. They need to belong to projects.

#### **Solution:**
Update session API to require project_id, filter searches to project documents.

#### **Tasks:**
- [ ] Update Session API
  ```
  POST /api/v1/projects/{id}/sessions        - Create session
  GET  /api/v1/projects/{id}/sessions        - List project sessions
  GET  /api/v1/sessions/{id}                 - Get session
  DELETE /api/v1/sessions/{id}               - Delete session
  ```

- [ ] Update chat endpoint
  ```
  POST /api/v1/projects/{id}/sessions/{session_id}/stream
  ```

- [ ] Configure RAG to use project context
  - Qdrant: Search only `project_{project_id}` collection
  - Graphiti: Use namespace `proj_{project_id}`
  - Filter by project documents

#### **Implementation:**

```python
# src/api/v1/chat.py (UPDATED for projects)

@router.post("/projects/{project_id}/sessions/{session_id}/stream")
async def stream_chat_project(
    project_id: str,
    session_id: str,
    query: str,
    mode: SearchMode = SearchMode.HYBRID,
    project: Project = Depends(require_project_access),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Stream chat response with project context.

    Only searches documents uploaded to this project.
    """
    # Verify session belongs to project
    session_repo = SessionRepository(Session, db)
    session = await session_repo.get_by_id(UUID(session_id))

    if not session or session.project_id != UUID(project_id):
        raise HTTPException(404, "Session not found in this project")

    # Configure coordinator with project-specific context
    coordinator = get_coordinator()

    # Set project context for RAG
    await coordinator.set_project_context(
        project_id=project_id,
        qdrant_collection=f"project_{project_id}",
        graphiti_namespace=f"proj_{project_id}",
    )

    logger.info(
        "Streaming chat with project context",
        project_id=project_id,
        session_id=session_id,
        query=query,
        mode=mode,
    )

    # Stream response
    async def generate():
        try:
            async for chunk in coordinator.stream(query, mode, session_id):
                yield f"data: {chunk.model_dump_json()}\n\n"

                # Save to Redis (project-scoped)
                if chunk.type == "complete":
                    from src.components.memory import get_redis_memory
                    redis = get_redis_memory()
                    await redis.store_session_messages(
                        project_id=project_id,
                        session_id=session_id,
                        messages=[...],  # Full conversation
                    )

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error("Streaming failed", error=str(e))
            error_chunk = {"type": "error", "error": str(e)}
            yield f"data: {json.dumps(error_chunk)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
```

```python
# src/agents/coordinator.py (UPDATED)

class CoordinatorAgent:
    """Project-aware coordinator agent."""

    async def set_project_context(
        self,
        project_id: str,
        qdrant_collection: str,
        graphiti_namespace: str,
    ):
        """Configure project-specific context for RAG."""
        self.project_id = project_id
        self.qdrant_collection = qdrant_collection
        self.graphiti_namespace = graphiti_namespace

        logger.info(
            "Project context set",
            project_id=project_id,
            collection=qdrant_collection,
            namespace=graphiti_namespace,
        )

    async def stream(self, query: str, mode: SearchMode, session_id: str):
        """Stream response using project-scoped retrieval."""
        # Configure retrieval agents with project context
        self.vector_search_agent.set_collection(self.qdrant_collection)
        self.graph_agent.set_namespace(self.graphiti_namespace)

        # Execute RAG with project documents only
        async for chunk in self._execute_rag(query, mode, session_id):
            yield chunk
```

#### **Deliverables:**
```bash
src/api/v1/chat.py (updated)
src/agents/coordinator.py (updated)
src/agents/vector_search.py (updated with collection support)
src/agents/graph_query.py (updated with namespace support)
tests/api/test_project_sessions.py
```

#### **Acceptance Criteria:**
- ✅ Sessions belong to projects
- ✅ RAG searches only project documents
- ✅ Knowledge graph isolated per project
- ✅ All project members can access sessions
- ✅ Redis keys project-scoped

---

### Feature 22.4: Frontend Project UI (8 SP)
**Priority:** HIGH - User-facing
**Duration:** 2 days

#### **Tasks:**
- [ ] Project list sidebar
- [ ] Project detail view with tabs
- [ ] Document upload UI (drag-and-drop)
- [ ] Member management UI
- [ ] Session list within project
- [ ] Project settings page
- [ ] Responsive design

#### **UI Components:**

```typescript
// src/pages/ProjectDetailPage.tsx
export function ProjectDetailPage() {
  const { projectId } = useParams()
  const { user } = useAuthStore()
  const { project, loading } = useProject(projectId)

  if (loading) return <PageSkeleton />
  if (!project) return <NotFound />

  return (
    <div className="flex h-screen bg-gray-50">
      <ProjectSidebar />

      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <ProjectHeader project={project} />

        {/* Tabs */}
        <Tabs defaultValue="sessions" className="flex-1 flex flex-col">
          <TabsList className="border-b px-6">
            <TabsTrigger value="sessions">
              💬 Sessions ({project.session_count})
            </TabsTrigger>
            <TabsTrigger value="documents">
              📄 Dokumente ({project.document_count})
            </TabsTrigger>
            <TabsTrigger value="members">
              👥 Mitglieder ({project.member_count})
            </TabsTrigger>
            <TabsTrigger value="settings">
              ⚙️ Einstellungen
            </TabsTrigger>
          </TabsList>

          <div className="flex-1 overflow-auto p-6">
            <TabsContent value="sessions">
              <SessionList projectId={projectId} />
              <Button onClick={() => createSession(projectId)}>
                <PlusIcon /> Neue Session
              </Button>
            </TabsContent>

            <TabsContent value="documents">
              <DocumentList projectId={projectId} />
              <DocumentUpload projectId={projectId} />
            </TabsContent>

            <TabsContent value="members">
              <MemberList projectId={projectId} />
              {canInvite && <AddMemberDialog projectId={projectId} />}
            </TabsContent>

            <TabsContent value="settings">
              <ProjectSettings project={project} />
            </TabsContent>
          </div>
        </Tabs>
      </main>
    </div>
  )
}

// src/components/DocumentUpload.tsx
export function DocumentUpload({ projectId }: { projectId: string }) {
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    setUploading(true)

    for (const file of acceptedFiles) {
      const formData = new FormData()
      formData.append('file', file)

      try {
        await api.post(`/projects/${projectId}/documents/upload`, formData, {
          onUploadProgress: (progressEvent) => {
            const percentCompleted = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            )
            setProgress(percentCompleted)
          },
        })

        toast.success(`${file.name} hochgeladen`)
      } catch (error) {
        toast.error(`Fehler: ${file.name}`)
      }
    }

    setUploading(false)
    setProgress(0)
  }, [projectId])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
    },
    maxSize: 100 * 1024 * 1024, // 100MB
  })

  return (
    <div
      {...getRootProps()}
      className={`
        border-2 border-dashed rounded-lg p-12 text-center
        transition-colors cursor-pointer
        ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}
      `}
    >
      <input {...getInputProps()} />

      {uploading ? (
        <div className="space-y-4">
          <Spinner className="w-8 h-8 mx-auto" />
          <Progress value={progress} className="w-64 mx-auto" />
          <p>{progress}% hochgeladen</p>
        </div>
      ) : (
        <div className="space-y-4">
          <UploadIcon className="w-12 h-12 mx-auto text-gray-400" />
          <div>
            <p className="text-lg font-medium">
              {isDragActive ? 'Dateien hier ablegen' : 'Dateien hochladen'}
            </p>
            <p className="text-sm text-gray-500">
              PDF, DOCX, TXT, MD (max 100MB)
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
```

#### **Deliverables:**
```bash
src/pages/ProjectDetailPage.tsx
src/components/ProjectSidebar.tsx
src/components/DocumentUpload.tsx
src/components/MemberList.tsx
src/components/AddMemberDialog.tsx
src/hooks/useProject.ts
src/hooks/useProjectDocuments.ts
```

#### **Acceptance Criteria:**
- ✅ Intuitive project navigation
- ✅ Drag-and-drop file upload
- ✅ Real-time upload progress
- ✅ Member management UI
- ✅ Responsive on mobile
- ✅ Loading states for async operations

---

### Feature 22.5: Project-Scoped mem0 Memory - OPTIONAL (5 SP)
**Priority:** LOW - Nice to have, can be deferred
**Duration:** 1 day
**Dependencies:** Feature 21.5 (mem0 User Preferences), Feature 22.1 (Project API)

#### **Problem:**
User preferences (Layer 0) are global across all projects. In multi-project setups, each project may have unique:
- **Team terminology** ("Vertrag" means different things in legal vs tech projects)
- **Communication styles** (formal reports vs quick notes)
- **Domain-specific knowledge** ("Always use Python 3.11 in this project")

#### **Solution:**
Extend mem0 to support **project-level memory** in addition to user-level memory.

#### **Use Cases:**

1. **Project-Specific Terminology:**
   - Project A (Legal): "Vertrag" = detailed contract document
   - Project B (IT): "Vertrag" = SLA agreement
   → mem0 learns project-specific vocabulary

2. **Team Communication Style:**
   - Project A: Formal, detailed, executive summaries
   - Project B: Concise, bullet points, developer-focused
   → mem0 adapts to team preferences

3. **Project Standards:**
   - "In diesem Projekt verwenden wir immer TypeScript strict mode"
   - "Alle API calls müssen gegen staging getestet werden"
   → mem0 stores project conventions

#### **Implementation:**

```python
# src/components/memory/mem0_wrapper.py (EXTEND existing from Sprint 21)

class Mem0Wrapper:
    """User + Project Preference Memory Layer."""

    async def add_project_memory(
        self,
        project_id: str,
        messages: list[dict],
        metadata: Optional[dict] = None
    ) -> dict:
        """Store project-level preferences/knowledge.

        Uses mem0's agent_id parameter for projects.
        """
        return self.memory.add(
            messages=messages,
            agent_id=f"project_{project_id}",  # Use agent_id for projects
            metadata=metadata or {}
        )

    async def get_project_preferences(
        self,
        project_id: str,
        query: Optional[str] = None,
        limit: int = 5
    ) -> list[dict]:
        """Retrieve project-level preferences."""
        return self.memory.search(
            query=query or "project conventions and standards",
            agent_id=f"project_{project_id}",
            limit=limit
        )
```

```python
# src/api/v1/chat.py (UPDATE from Sprint 21)

@router.post("/projects/{project_id}/sessions/{session_id}/stream")
async def stream_chat_project(
    project_id: str,
    user: User = Depends(get_current_user),
    project: Project = Depends(require_project_access),
):
    """Stream chat with user + project preferences."""
    mem0 = get_mem0_wrapper()

    # Layer 0A: User preferences (from Sprint 21)
    user_prefs = await mem0.get_user_preferences(
        user_id=str(user.id),
        limit=3
    )

    # Layer 0B: Project preferences (NEW in Sprint 22)
    project_prefs = await mem0.get_project_preferences(
        project_id=project_id,
        limit=3
    )

    # Combine both for system prompt
    system_prompt = build_system_prompt(
        user_name=user.name,
        user_preferences=user_prefs,
        project_preferences=project_prefs,
        project_name=project.name
    )

    # ... rest of chat logic
```

#### **Tasks:**
- [ ] Extend Mem0Wrapper with project memory methods
- [ ] Update chat API to retrieve project preferences
- [ ] Update system prompt builder to include project context
- [ ] Add project memory to background task updates
- [ ] Optional: Project preferences API endpoint
  ```
  GET /api/v1/projects/{id}/preferences
  ```

#### **Deliverables:**
```bash
src/components/memory/mem0_wrapper.py (extended)
src/api/v1/chat.py (updated for project context)
tests/memory/test_mem0_project_memory.py
docs/sprints/SPRINT_22_PROJECT_MEMORY.md
```

#### **Acceptance Criteria:**
- ✅ Project memory stored separately from user memory
- ✅ Project preferences retrieved during chat
- ✅ System prompt includes both user + project context
- ✅ Project memory updates after conversations
- ✅ No cross-project memory leakage

#### **Decision:**
- **IF time allows** after Features 22.1-22.4 → Implement Feature 22.5
- **IF sprint runs late** → Defer to Sprint 23
- **Benefit:** Team-level personalization, project-specific learning
- **Cost:** +5 SP, +1 day

---

## Testing Strategy

### E2E Tests (Playwright)
```typescript
// e2e/projects.spec.ts
test('complete project workflow', async ({ page }) => {
  // Login
  await page.goto('/login')
  await page.fill('input[type=email]', 'test@example.com')
  await page.fill('input[type=password]', 'password123')
  await page.click('button[type=submit]')

  // Create project
  await page.click('text=New Project')
  await page.fill('input[name=name]', 'Test Project')
  await page.click('button:has-text("Create")')

  // Upload document
  await page.click('text=Dokumente')
  const fileInput = await page.locator('input[type=file]')
  await fileInput.setInputFiles('test-document.pdf')

  // Wait for processing
  await page.waitForSelector('text=Ready', { timeout: 30000 })

  // Create session
  await page.click('text=Sessions')
  await page.click('text=Neue Session')

  // Chat
  await page.fill('textarea', 'Was steht in dem Dokument?')
  await page.keyboard.press('Enter')

  // Wait for response
  await page.waitForSelector('[data-testid=streaming-answer]')
})
```

---

## Sprint 22 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Project creation time | <2s | API latency |
| Document upload time | <30s for 10MB | Upload + processing |
| Document processing success rate | >95% | Error logs |
| Search accuracy (project docs only) | 100% | Test queries |
| UI responsiveness | <100ms interactions | Performance monitoring |
| Member invitation success | >98% | API logs |

---

**Sprint 22 Completion:** Full project collaboration system operational
**Next Steps:** Sprint 23 - OAuth2/Entra ID integration or advanced features
