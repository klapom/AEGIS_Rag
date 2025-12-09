# TD-056: Project Collaboration System

**Created:** 2025-12-07
**Status:** PLANNED
**Priority:** P2 (Medium)
**Effort:** 34-42 SP (3-4 Sprints)
**Dependencies:** TD-056 requires Sprint 38 (JWT Auth) to be completed first

---

## Summary

Implement a full project-based collaboration system allowing users to:
- Create and manage shared workspaces (Projects)
- Invite team members with role-based permissions
- Upload and share documents within projects
- Isolate knowledge graphs per project
- Enable project-scoped RAG searches

This was originally planned for Sprint 22 but deferred in favor of core RAG functionality.

---

## Problem Statement

Currently, AegisRAG operates in single-user mode:
- All documents are in a global namespace
- All conversations are accessible to everyone
- Knowledge graph is shared across all users
- No concept of teams or workspaces

**User Pain Points:**
1. Cannot organize work into separate domains
2. Cannot share specific conversations with colleagues
3. Cannot restrict document access to specific teams
4. Cross-project knowledge contamination in RAG results

---

## Proposed Solution

### Project Hierarchy

```
Organization (Tenant)
  └── Users (Colleagues)
       └── Projects (Shared Workspaces)
            ├── Owner (Creator)
            ├── Members (Collaborators)
            │   ├── OWNER - Full control
            │   ├── EDITOR - Add docs, create sessions
            │   ├── COMMENTER - Add messages only
            │   └── VIEWER - Read-only access
            ├── Documents (Shared Knowledge Base)
            ├── Sessions (Conversations)
            └── Knowledge Graph (Isolated per Project)
```

### Data Isolation Strategy

| Component | Isolation Method |
|-----------|------------------|
| Qdrant | Collection per project: `project_{project_id}` |
| Neo4j | Namespace property: `project_id` on all nodes |
| Redis | Key prefix: `proj:{project_id}:session:{id}` |
| Graphiti | Namespace: `proj_{project_id}` |

---

## Implementation Plan

### Phase 1: Project Management API (8 SP)

**Endpoints:**
```
POST   /api/v1/projects              - Create project
GET    /api/v1/projects              - List user's projects
GET    /api/v1/projects/{id}         - Get project details
PATCH  /api/v1/projects/{id}         - Update project
DELETE /api/v1/projects/{id}         - Delete project (soft)
POST   /api/v1/projects/{id}/archive - Archive project
```

**Database Schema:**
```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL,
    owner_id UUID NOT NULL REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    color VARCHAR(7) DEFAULT '#3B82F6',
    emoji VARCHAR(10) DEFAULT '📁',
    visibility VARCHAR(20) DEFAULT 'TEAM',  -- PRIVATE, TEAM, ORG
    session_count INTEGER DEFAULT 0,
    document_count INTEGER DEFAULT 0,
    member_count INTEGER DEFAULT 1,
    storage_bytes BIGINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP NULL  -- Soft delete
);

CREATE INDEX idx_projects_owner ON projects(owner_id);
CREATE INDEX idx_projects_org ON projects(organization_id);
```

**Deliverables:**
- `src/api/v1/projects.py`
- `src/repositories/project.py`
- `src/models/database/project.py`
- `tests/api/test_projects.py`

---

### Phase 2: Project Member Management (5 SP)

**Endpoints:**
```
POST   /api/v1/projects/{id}/members           - Add member
GET    /api/v1/projects/{id}/members           - List members
PATCH  /api/v1/projects/{id}/members/{user_id} - Update role
DELETE /api/v1/projects/{id}/members/{user_id} - Remove member
```

**Database Schema:**
```sql
CREATE TABLE project_members (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id),
    user_id UUID NOT NULL REFERENCES users(id),
    role VARCHAR(20) NOT NULL DEFAULT 'EDITOR',
    added_by UUID NOT NULL REFERENCES users(id),
    added_at TIMESTAMP DEFAULT NOW(),
    is_favorite BOOLEAN DEFAULT FALSE,
    last_viewed_at TIMESTAMP NULL,
    UNIQUE(project_id, user_id)
);

CREATE INDEX idx_members_project ON project_members(project_id);
CREATE INDEX idx_members_user ON project_members(user_id);
```

**Deliverables:**
- `src/api/v1/project_members.py`
- `src/repositories/project_member.py`
- `src/core/auth.py` - Add `require_project_access()` dependency
- `tests/api/test_project_members.py`

---

### Phase 3: Project Documents (8 SP)

**Endpoints:**
```
POST   /api/v1/projects/{id}/documents/upload  - Upload document
GET    /api/v1/projects/{id}/documents         - List documents
GET    /api/v1/projects/{id}/documents/{doc_id} - Get document
DELETE /api/v1/projects/{id}/documents/{doc_id} - Delete document
```

**Document Lifecycle:**
```
1. UPLOAD    → Validate → Save to disk → Create DB record
2. PROCESSING → Extract text → Chunk → Embed → Index Qdrant
3. READY     → Document searchable in project
4. DELETE    → Remove from disk → Remove from Qdrant → Delete DB
```

**Storage Structure:**
```
/uploads/
  └── {org_id}/
       └── {project_id}/
            └── {doc_id}/
                 └── original_filename.pdf
```

**Deliverables:**
- `src/api/v1/documents.py`
- `src/components/document_processing.py` (async background task)
- `src/repositories/document.py`
- `tests/api/test_documents.py`

---

### Phase 4: Project Sessions (5 SP)

**Endpoints:**
```
POST /api/v1/projects/{id}/sessions                    - Create session
GET  /api/v1/projects/{id}/sessions                    - List sessions
POST /api/v1/projects/{id}/sessions/{session_id}/stream - Chat (project-scoped)
```

**RAG Configuration:**
- Qdrant searches only `project_{project_id}` collection
- Graphiti uses namespace `proj_{project_id}`
- Redis keys prefixed with project ID

**Deliverables:**
- `src/api/v1/chat.py` - Update for project-scoped streaming
- `src/agents/coordinator.py` - Add `set_project_context()` method
- `tests/api/test_project_sessions.py`

---

### Phase 5: Frontend Project UI (8 SP)

**Pages:**
- `/projects` - Project list with sidebar
- `/projects/{id}` - Project detail with tabs (Sessions, Documents, Members, Settings)
- `/projects/{id}/sessions/{session_id}` - Project-scoped chat

**Components:**
- `ProjectSidebar.tsx` - Project navigation
- `ProjectDetailPage.tsx` - Tabbed project view
- `DocumentUpload.tsx` - Drag-and-drop file upload
- `MemberList.tsx` - Member management
- `AddMemberDialog.tsx` - Invite modal

**Deliverables:**
- `frontend/src/pages/ProjectListPage.tsx`
- `frontend/src/pages/ProjectDetailPage.tsx`
- `frontend/src/components/project/*.tsx`
- `frontend/src/hooks/useProject.ts`
- `frontend/e2e/tests/projects.spec.ts`

---

## Acceptance Criteria

- [ ] Users can create and manage projects
- [ ] Users can invite team members with different roles
- [ ] Users can upload documents to projects (all members can access)
- [ ] RAG searches only project documents (no cross-project leakage)
- [ ] Knowledge graph isolated per project
- [ ] Sessions belong to projects
- [ ] Intuitive project UI with drag-and-drop uploads
- [ ] Role-based access control enforced on all endpoints
- [ ] Storage quotas enforced per project and organization

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Database schema changes | High | Use migrations, test thoroughly |
| Cross-project data leakage | Critical | Strict namespace filtering, E2E tests |
| Performance with many projects | Medium | Index optimization, pagination |
| Complex frontend state | Medium | Use React Query for caching |

---

## Dependencies

- **Sprint 38**: JWT Authentication must be completed first
- **Database**: PostgreSQL or SQLite with proper schema
- **Qdrant**: Multi-collection support (already available)
- **Neo4j**: Namespace filtering (add `project_id` property)

---

## Effort Estimation

| Phase | Story Points | Duration |
|-------|--------------|----------|
| Phase 1: Project API | 8 SP | 2 days |
| Phase 2: Member Management | 5 SP | 1.5 days |
| Phase 3: Project Documents | 8 SP | 2 days |
| Phase 4: Project Sessions | 5 SP | 1.5 days |
| Phase 5: Frontend UI | 8 SP | 2 days |
| **Total** | **34 SP** | **9 days** |

---

## Related Documents

- `docs/sprints/SPRINT_22_PLAN.md` - Original collaboration plan
- `docs/sprints/SPRINT_27_FRONTEND_FEATURES_PROPOSAL.md` - Share conversation feature
- `src/api/v1/auth.py` - Authentication foundation
- `TD-052_USER_DOCUMENT_UPLOAD.md` - Document upload infrastructure

---

## Notes

Originally planned for Sprint 22 (2025-11-11), this feature set was deferred to focus on:
- Docling Container Integration (Sprint 21)
- Multi-Cloud LLM Execution (Sprint 23)
- Production Readiness (Sprint 25)
- Knowledge Graph Enhancement (Sprint 34)

The foundation is now solid enough to implement collaboration features.
Recommended implementation: Sprint 39-41 after Sprint 38 (Auth + Search + Share Links).
