# Sprint 20: Foundation - Auth & Multi-Tenancy

**Status:** 📋 PLANNED
**Goal:** Establish foundation for Org/User/Project hierarchy with authentication
**Duration:** 5 days (estimated)
**Prerequisites:** Sprint 19 complete (Frontend stabilized)
**Story Points:** 16 SP

---

## 🎯 Sprint Objectives

### **Primary Goals:**
1. Implement PostgreSQL database with multi-tenancy schema
2. Build JWT-based authentication system
3. Establish user/organization management
4. Create Redis namespace strategy for project isolation
5. Implement authorization middleware for all endpoints

### **Success Criteria:**
- ✅ Users can register and login
- ✅ JWT tokens secure all API endpoints
- ✅ Organizations exist with user membership
- ✅ Redis keys namespaced by org/user/project
- ✅ All endpoints enforce authentication
- ✅ 100% test coverage for auth flows

---

## 📦 Sprint Features

### Feature 20.1: Database Schema & Models (5 SP)
**Priority:** HIGH - Foundation for everything
**Duration:** 1.5 days

#### **Problem:**
Currently, all data is anonymous and global. No concept of users, organizations, or ownership. This violates DSGVO and prevents multi-user deployment.

#### **Solution:**
PostgreSQL database with complete multi-tenancy schema including organizations, users, projects, and relationships.

#### **Database Architecture:**

**Entity-Relationship Model:**
```
Organizations (1) ──── (N) Users
     │                      │
     │                      │
     └──── (N) Projects (N) ┘
              │
              ├── (N) ProjectMembers
              ├── (N) Sessions
              └── (N) ProjectDocuments
```

#### **Tasks:**
- [ ] **Infrastructure Setup**
  - Docker Compose PostgreSQL service
  - Environment variables (DB URL, credentials)
  - Connection pooling configuration
  - Health check endpoint

- [ ] **Alembic Migrations**
  - Initialize Alembic (`alembic init migrations`)
  - Create base migration script
  - Version control for schema changes
  - Rollback procedures

- [ ] **Database Schema**
  ```sql
  -- Core tables (in dependency order)
  1. organizations
  2. users
  3. projects
  4. project_members (junction table)
  5. sessions (updated with project_id)
  6. messages (updated with project_id)
  7. project_documents
  ```

- [ ] **SQLAlchemy Models**
  - Base model with common fields (id, created_at, updated_at)
  - Organization model with tier/features
  - User model with auth fields
  - Project model with settings/metadata
  - ProjectMember model with roles
  - Session model (updated)
  - ProjectDocument model with processing status

- [ ] **Repository Pattern**
  - BaseRepository with CRUD operations
  - OrganizationRepository
  - UserRepository (with email lookup, auth checks)
  - ProjectRepository (with access control)
  - ProjectMemberRepository
  - SessionRepository (project-scoped)
  - DocumentRepository

- [ ] **Database Indexes**
  - Foreign key indexes for joins
  - Email unique index for users
  - Composite index (project_id, user_id) for members
  - Session lookup indexes

#### **Database Schema (Detailed):**

```sql
-- =====================================================
-- ORGANIZATIONS TABLE
-- =====================================================
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,

    -- Subscription tier
    tier VARCHAR(50) NOT NULL DEFAULT 'free',
    CHECK (tier IN ('free', 'professional', 'enterprise')),

    -- Quotas
    max_users INT NOT NULL DEFAULT 5,
    max_projects INT NOT NULL DEFAULT 3,
    max_storage_gb INT NOT NULL DEFAULT 10,
    max_documents_per_project INT NOT NULL DEFAULT 50,

    -- Feature flags (JSON)
    features JSONB DEFAULT '{
        "advanced_rag": false,
        "custom_models": false,
        "sso_enabled": false,
        "api_access": false,
        "priority_support": false
    }'::jsonb,

    -- Settings
    settings JSONB DEFAULT '{
        "default_search_mode": "hybrid",
        "retention_days": 90,
        "enable_analytics": true
    }'::jsonb,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Soft delete
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_organizations_tier ON organizations(tier);
CREATE INDEX idx_organizations_deleted ON organizations(deleted_at) WHERE deleted_at IS NULL;

-- =====================================================
-- USERS TABLE
-- =====================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    -- Authentication
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255),  -- NULL for SSO users
    auth_provider VARCHAR(50) NOT NULL DEFAULT 'local',
    CHECK (auth_provider IN ('local', 'entra_id', 'okta', 'google', 'github')),

    -- Profile
    name VARCHAR(255) NOT NULL,
    avatar_url VARCHAR(1000),

    -- Authorization
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    CHECK (role IN ('admin', 'user', 'guest')),

    -- Status
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_email_verified BOOLEAN NOT NULL DEFAULT false,
    email_verified_at TIMESTAMP WITH TIME ZONE,

    -- Preferences (JSON)
    preferences JSONB DEFAULT '{
        "default_search_mode": "hybrid",
        "theme": "light",
        "language": "de",
        "notifications_enabled": true,
        "email_notifications": true
    }'::jsonb,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE,

    -- Soft delete
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_organization ON users(organization_id);
CREATE INDEX idx_users_active ON users(is_active) WHERE is_active = true;
CREATE INDEX idx_users_deleted ON users(deleted_at) WHERE deleted_at IS NULL;

-- =====================================================
-- PROJECTS TABLE
-- =====================================================
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Basic info
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- UI customization
    color VARCHAR(7) NOT NULL DEFAULT '#3B82F6',
    emoji VARCHAR(10) NOT NULL DEFAULT '📁',

    -- Access control
    visibility VARCHAR(50) NOT NULL DEFAULT 'team',
    CHECK (visibility IN ('private', 'team', 'organization')),

    -- Settings (JSON)
    settings JSONB DEFAULT '{
        "default_search_mode": "hybrid",
        "auto_title_sessions": true,
        "enable_citations": true,
        "max_documents": 100,
        "retention_days": 180
    }'::jsonb,

    -- Statistics (denormalized for performance)
    session_count INT NOT NULL DEFAULT 0,
    document_count INT NOT NULL DEFAULT 0,
    message_count INT NOT NULL DEFAULT 0,
    member_count INT NOT NULL DEFAULT 0,
    storage_bytes BIGINT NOT NULL DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_activity_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Soft delete
    deleted_at TIMESTAMP WITH TIME ZONE,

    -- Full-text search
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B')
    ) STORED
);

-- Indexes
CREATE INDEX idx_projects_organization ON projects(organization_id);
CREATE INDEX idx_projects_owner ON projects(owner_id);
CREATE INDEX idx_projects_visibility ON projects(visibility);
CREATE INDEX idx_projects_last_activity ON projects(last_activity_at DESC);
CREATE INDEX idx_projects_deleted ON projects(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX idx_projects_search ON projects USING GIN(search_vector);

-- =====================================================
-- PROJECT_MEMBERS TABLE (Junction)
-- =====================================================
CREATE TABLE project_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Role in project
    role VARCHAR(50) NOT NULL DEFAULT 'editor',
    CHECK (role IN ('owner', 'editor', 'viewer', 'commenter')),

    -- Membership metadata
    added_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    added_by UUID NOT NULL REFERENCES users(id),

    -- User preferences for this project
    is_favorite BOOLEAN NOT NULL DEFAULT false,
    notifications_enabled BOOLEAN NOT NULL DEFAULT true,
    last_viewed_at TIMESTAMP WITH TIME ZONE,

    -- Ensure unique membership
    UNIQUE(project_id, user_id)
);

-- Indexes
CREATE INDEX idx_project_members_project ON project_members(project_id);
CREATE INDEX idx_project_members_user ON project_members(user_id);
CREATE INDEX idx_project_members_role ON project_members(role);
CREATE INDEX idx_project_members_favorite ON project_members(user_id, is_favorite) WHERE is_favorite = true;

-- =====================================================
-- SESSIONS TABLE (UPDATED with project_id)
-- =====================================================
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    created_by UUID NOT NULL REFERENCES users(id),

    -- Session info
    title VARCHAR(500),  -- Auto-generated from first message

    -- Collaboration (optional)
    is_shared BOOLEAN NOT NULL DEFAULT false,
    participants UUID[] DEFAULT ARRAY[]::UUID[],

    -- Settings (can override project defaults)
    settings JSONB DEFAULT '{
        "search_mode": null,
        "model": null,
        "temperature": null
    }'::jsonb,

    -- Statistics
    message_count INT NOT NULL DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_message_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Archival
    is_archived BOOLEAN NOT NULL DEFAULT false,
    archived_at TIMESTAMP WITH TIME ZONE,

    -- Soft delete
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_sessions_project ON sessions(project_id);
CREATE INDEX idx_sessions_created_by ON sessions(created_by);
CREATE INDEX idx_sessions_last_message ON sessions(last_message_at DESC);
CREATE INDEX idx_sessions_archived ON sessions(is_archived);
CREATE INDEX idx_sessions_deleted ON sessions(deleted_at) WHERE deleted_at IS NULL;

-- =====================================================
-- MESSAGES TABLE (kept in Postgres for auditing)
-- =====================================================
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    project_id UUID NOT NULL,  -- Denormalized for faster queries

    -- Authorship
    created_by UUID NOT NULL REFERENCES users(id),
    role VARCHAR(50) NOT NULL,
    CHECK (role IN ('user', 'assistant', 'system')),

    -- Content
    content TEXT NOT NULL,

    -- Provenance (JSON)
    sources JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Reactions (optional collaboration feature)
    reactions JSONB DEFAULT '{}'::jsonb  -- {"👍": ["user1", "user2"]}
);

-- Indexes
CREATE INDEX idx_messages_session ON messages(session_id);
CREATE INDEX idx_messages_project ON messages(project_id);
CREATE INDEX idx_messages_created_by ON messages(created_by);
CREATE INDEX idx_messages_created_at ON messages(created_at DESC);
CREATE INDEX idx_messages_role ON messages(role);

-- =====================================================
-- PROJECT_DOCUMENTS TABLE
-- =====================================================
CREATE TABLE project_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    uploaded_by UUID NOT NULL REFERENCES users(id),

    -- File info
    filename VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,

    -- Processing status
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    CHECK (status IN ('pending', 'processing', 'ready', 'error')),

    -- RAG integration
    chunk_count INT DEFAULT 0,
    embedding_model VARCHAR(100),
    qdrant_collection VARCHAR(255),  -- project_{project_id}

    -- Metadata (JSON)
    metadata JSONB DEFAULT '{
        "language": "de",
        "page_count": null,
        "extraction_method": "llama_parse",
        "processing_time_seconds": null,
        "error_message": null
    }'::jsonb,

    -- Timestamps
    uploaded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,

    -- Soft delete
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_documents_project ON project_documents(project_id);
CREATE INDEX idx_documents_uploaded_by ON project_documents(uploaded_by);
CREATE INDEX idx_documents_status ON project_documents(status);
CREATE INDEX idx_documents_uploaded_at ON project_documents(uploaded_at DESC);
CREATE INDEX idx_documents_deleted ON project_documents(deleted_at) WHERE deleted_at IS NULL;

-- =====================================================
-- TRIGGERS for updated_at
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- TRIGGERS for statistics
-- =====================================================
-- Update project.session_count when session added/deleted
CREATE OR REPLACE FUNCTION update_project_session_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE projects SET session_count = session_count + 1 WHERE id = NEW.project_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE projects SET session_count = session_count - 1 WHERE id = OLD.project_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_project_session_count
AFTER INSERT OR DELETE ON sessions
FOR EACH ROW EXECUTE FUNCTION update_project_session_count();

-- Similar triggers for document_count, member_count, etc.
```

#### **SQLAlchemy Models:**

```python
# src/models/database.py
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, BigInteger,
    String, Text, func, CheckConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

class SoftDeleteMixin:
    """Mixin for soft delete functionality."""
    deleted_at = Column(DateTime(timezone=True), nullable=True)

class Organization(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "organizations"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    tier = Column(String(50), nullable=False, default="free")

    # Quotas
    max_users = Column(Integer, nullable=False, default=5)
    max_projects = Column(Integer, nullable=False, default=3)
    max_storage_gb = Column(Integer, nullable=False, default=10)
    max_documents_per_project = Column(Integer, nullable=False, default=50)

    # JSON fields
    features = Column(JSONB, nullable=False, default={})
    settings = Column(JSONB, nullable=False, default={})

    # Relationships
    users = relationship("User", back_populates="organization")
    projects = relationship("Project", back_populates="organization")

    __table_args__ = (
        CheckConstraint("tier IN ('free', 'professional', 'enterprise')"),
        Index("idx_organizations_tier", "tier"),
    )

class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id = Column(PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)

    # Authentication
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)
    auth_provider = Column(String(50), nullable=False, default="local")

    # Profile
    name = Column(String(255), nullable=False)
    avatar_url = Column(String(1000), nullable=True)

    # Authorization
    role = Column(String(50), nullable=False, default="user")

    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    is_email_verified = Column(Boolean, nullable=False, default=False)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # JSON fields
    preferences = Column(JSONB, nullable=False, default={})

    # Relationships
    organization = relationship("Organization", back_populates="users")
    owned_projects = relationship("Project", foreign_keys="Project.owner_id", back_populates="owner")
    project_memberships = relationship("ProjectMember", back_populates="user")
    sessions = relationship("Session", back_populates="creator")

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'user', 'guest')"),
        CheckConstraint("auth_provider IN ('local', 'entra_id', 'okta', 'google', 'github')"),
        Index("idx_users_email", "email"),
        Index("idx_users_organization", "organization_id"),
    )

class Project(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "projects"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id = Column(PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    owner_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Basic info
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # UI
    color = Column(String(7), nullable=False, default="#3B82F6")
    emoji = Column(String(10), nullable=False, default="📁")

    # Access
    visibility = Column(String(50), nullable=False, default="team")

    # JSON fields
    settings = Column(JSONB, nullable=False, default={})

    # Statistics
    session_count = Column(Integer, nullable=False, default=0)
    document_count = Column(Integer, nullable=False, default=0)
    message_count = Column(Integer, nullable=False, default=0)
    member_count = Column(Integer, nullable=False, default=0)
    storage_bytes = Column(BigInteger, nullable=False, default=0)

    last_activity_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="projects")
    owner = relationship("User", foreign_keys=[owner_id], back_populates="owned_projects")
    members = relationship("ProjectMember", back_populates="project")
    sessions = relationship("Session", back_populates="project")
    documents = relationship("ProjectDocument", back_populates="project")

    __table_args__ = (
        CheckConstraint("visibility IN ('private', 'team', 'organization')"),
        Index("idx_projects_organization", "organization_id"),
        Index("idx_projects_owner", "owner_id"),
        Index("idx_projects_last_activity", "last_activity_at"),
    )

class ProjectMember(Base):
    __tablename__ = "project_members"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    role = Column(String(50), nullable=False, default="editor")
    added_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    added_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    is_favorite = Column(Boolean, nullable=False, default=False)
    notifications_enabled = Column(Boolean, nullable=False, default=True)
    last_viewed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    project = relationship("Project", back_populates="members")
    user = relationship("User", foreign_keys=[user_id], back_populates="project_memberships")

    __table_args__ = (
        CheckConstraint("role IN ('owner', 'editor', 'viewer', 'commenter')"),
        Index("idx_project_members_project", "project_id"),
        Index("idx_project_members_user", "user_id"),
    )

class Session(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "sessions"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    created_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    title = Column(String(500), nullable=True)
    is_shared = Column(Boolean, nullable=False, default=False)
    participants = Column(ARRAY(PGUUID(as_uuid=True)), default=[])

    settings = Column(JSONB, nullable=False, default={})
    message_count = Column(Integer, nullable=False, default=0)

    last_message_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    is_archived = Column(Boolean, nullable=False, default=False)
    archived_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    project = relationship("Project", back_populates="sessions")
    creator = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session")

    __table_args__ = (
        Index("idx_sessions_project", "project_id"),
        Index("idx_sessions_created_by", "created_by"),
        Index("idx_sessions_last_message", "last_message_at"),
    )

class ProjectDocument(Base, SoftDeleteMixin):
    __tablename__ = "project_documents"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    uploaded_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    mime_type = Column(String(100), nullable=False)

    status = Column(String(50), nullable=False, default="pending")
    chunk_count = Column(Integer, default=0)
    embedding_model = Column(String(100), nullable=True)
    qdrant_collection = Column(String(255), nullable=True)

    metadata = Column(JSONB, nullable=False, default={})

    uploaded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    project = relationship("Project", back_populates="documents")
    uploader = relationship("User")

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'processing', 'ready', 'error')"),
        Index("idx_documents_project", "project_id"),
        Index("idx_documents_status", "status"),
    )
```

#### **Repository Pattern:**

```python
# src/repositories/base.py
from typing import Generic, TypeVar, Type, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from src.models.database import Base

ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations."""

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def create(self, obj: ModelType) -> ModelType:
        """Create new object."""
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def get_by_id(self, id: UUID) -> Optional[ModelType]:
        """Get by ID."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalars().first()

    async def list(self, limit: int = 100, offset: int = 0) -> List[ModelType]:
        """List objects."""
        result = await self.session.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return result.scalars().all()

    async def update(self, id: UUID, **kwargs) -> Optional[ModelType]:
        """Update object."""
        await self.session.execute(
            update(self.model).where(self.model.id == id).values(**kwargs)
        )
        await self.session.commit()
        return await self.get_by_id(id)

    async def delete(self, id: UUID, soft: bool = True) -> bool:
        """Delete object (soft or hard)."""
        if soft:
            await self.update(id, deleted_at=datetime.now(timezone.utc))
        else:
            await self.session.execute(
                delete(self.model).where(self.model.id == id)
            )
            await self.session.commit()
        return True

# src/repositories/project.py
class ProjectRepository(BaseRepository[Project]):
    """Project repository with access control."""

    async def list_for_user(
        self,
        user_id: UUID,
        org_id: UUID,
        limit: int = 50
    ) -> List[Project]:
        """List projects accessible to user."""
        query = select(Project).join(ProjectMember).where(
            (ProjectMember.user_id == user_id) |
            ((Project.visibility == 'organization') & (Project.organization_id == org_id))
        ).distinct().order_by(Project.last_activity_at.desc()).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def check_user_access(
        self,
        project_id: UUID,
        user_id: UUID,
        required_role: Optional[str] = None
    ) -> bool:
        """Check if user has access to project."""
        query = select(ProjectMember).where(
            (ProjectMember.project_id == project_id) &
            (ProjectMember.user_id == user_id)
        )

        if required_role:
            role_hierarchy = {'viewer': 1, 'commenter': 2, 'editor': 3, 'owner': 4}
            query = query.where(
                ProjectMember.role.in_([
                    role for role, level in role_hierarchy.items()
                    if level >= role_hierarchy[required_role]
                ])
            )

        result = await self.session.execute(query)
        return result.scalars().first() is not None
```

#### **Database Connection:**

```python
# src/core/database.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from src.core.config import settings

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db() -> AsyncSession:
    """Dependency for database session."""
    async with AsyncSessionLocal() as session:
        yield session
```

#### **Deliverables:**
```bash
docs/sprints/SPRINT_20_DATABASE_SCHEMA.md
src/models/database.py
src/repositories/base.py
src/repositories/user.py
src/repositories/organization.py
src/repositories/project.py
migrations/versions/001_initial_schema.py
tests/repositories/test_project_repository.py
```

#### **Acceptance Criteria:**
- ✅ All tables created with correct schema
- ✅ Foreign keys and indexes in place
- ✅ SQLAlchemy models match database schema
- ✅ Repository pattern implemented for all entities
- ✅ Database migrations work (up and down)
- ✅ Connection pooling configured
- ✅ 100% test coverage for repositories

---

### Feature 20.2: JWT Authentication (5 SP)
**Priority:** HIGH - Secures all endpoints
**Duration:** 1.5 days

#### **Problem:**
No authentication exists. All API endpoints are publicly accessible. Cannot identify users or enforce access control.

#### **Solution:**
JWT-based authentication with password hashing, token issuance, and refresh logic.

#### **Authentication Flow:**

```
1. REGISTRATION
   User → POST /api/v1/auth/register → Hash password → Create User → Issue JWT

2. LOGIN
   User → POST /api/v1/auth/login → Verify password → Issue JWT → Return token

3. AUTHENTICATED REQUEST
   User → GET /api/v1/projects (with JWT in header) → Verify JWT → Extract user → Execute

4. TOKEN REFRESH
   User → POST /api/v1/auth/refresh (with refresh token) → Issue new access token
```

#### **Tasks:**
- [ ] **Dependencies**
  ```bash
  poetry add python-jose[cryptography] passlib[bcrypt] python-multipart
  ```

- [ ] **JWT Utilities**
  - Token creation (access + refresh)
  - Token verification
  - Token expiration handling
  - Signature validation

- [ ] **Password Security**
  - Bcrypt hashing
  - Salt generation
  - Password verification
  - Minimum password requirements

- [ ] **Auth Endpoints**
  ```
  POST /api/v1/auth/register
  POST /api/v1/auth/login
  POST /api/v1/auth/logout
  POST /api/v1/auth/refresh
  GET  /api/v1/auth/me
  ```

- [ ] **Dependencies**
  - `get_current_user` - Extract user from JWT
  - `require_admin` - Require admin role
  - `require_active` - Require active account

- [ ] **Frontend Integration**
  - Token storage (localStorage with XSS protection)
  - Auto token refresh (before expiry)
  - Logout cleanup
  - Axios interceptors

#### **Implementation:**

```python
# src/core/auth.py
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_db
from src.models.database import User
from src.repositories.user import UserRepository

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT config
SECRET_KEY = settings.jwt_secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Security scheme
security = HTTPBearer()

def hash_password(password: str) -> str:
    """Hash password with bcrypt."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(user: User) -> str:
    """Create JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user.id),
        "email": user.email,
        "org_id": str(user.organization_id),
        "role": user.role,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(user: User) -> str:
    """Create JWT refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": str(user.id),
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate user from JWT token."""
    token = credentials.credentials

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Check token type
        if payload.get("type") != "access":
            raise credentials_exception

        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception

        # Load user from database
        user_repo = UserRepository(User, db)
        user = await user_repo.get_by_id(UUID(user_id))

        if user is None or not user.is_active or user.deleted_at is not None:
            raise credentials_exception

        # Update last login
        await user_repo.update(user.id, last_login_at=datetime.now(timezone.utc))

        return user

    except JWTError:
        raise credentials_exception

async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Require admin role."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user

async def require_active(user: User = Depends(get_current_user)) -> User:
    """Require active account."""
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    return user
```

```python
# src/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    verify_password,
)
from src.core.database import get_db
from src.models.database import User, Organization
from src.repositories.user import UserRepository
from src.repositories.organization import OrganizationRepository

router = APIRouter(prefix="/auth", tags=["authentication"])

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=2)
    organization_name: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict

@router.post("/register", response_model=TokenResponse)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register new user and organization."""
    user_repo = UserRepository(User, db)
    org_repo = OrganizationRepository(Organization, db)

    # Check if email already exists
    existing_user = await user_repo.get_by_email(request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create organization if provided, else join default
    if request.organization_name:
        org = Organization(
            name=request.organization_name,
            tier="free",
        )
        org = await org_repo.create(org)
        role = "admin"
    else:
        org = await org_repo.get_default()
        role = "user"

    # Hash password
    hashed_password = hash_password(request.password)

    # Create user
    user = User(
        email=request.email,
        name=request.name,
        hashed_password=hashed_password,
        organization_id=org.id,
        role=role,
        is_active=True,
    )
    user = await user_repo.create(user)

    # Create tokens
    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user.model_dump(exclude={"hashed_password"}),
    )

@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """User login."""
    user_repo = UserRepository(User, db)

    # Get user by email
    user = await user_repo.get_by_email(request.email)

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not user.is_active or user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    # Create tokens
    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user.model_dump(exclude={"hashed_password"}),
    )

@router.get("/me")
async def get_current_user_info(
    user: User = Depends(get_current_user),
):
    """Get current user info."""
    return user.model_dump(exclude={"hashed_password"})

@router.post("/refresh")
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token."""
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != "refresh":
            raise HTTPException(401, "Invalid token type")

        user_id = UUID(payload.get("sub"))
        user_repo = UserRepository(User, db)
        user = await user_repo.get_by_id(user_id)

        if not user or not user.is_active:
            raise HTTPException(401, "Invalid token")

        new_access_token = create_access_token(user)

        return {"access_token": new_access_token, "token_type": "bearer"}

    except JWTError:
        raise HTTPException(401, "Invalid or expired refresh token")
```

#### **Frontend Integration:**

```typescript
// src/stores/authStore.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, name: string, orgName?: string) => Promise<void>
  logout: () => void
  refreshAccessToken: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,

      login: async (email, password) => {
        const response = await fetch('/api/v1/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password }),
        })

        if (!response.ok) {
          throw new Error('Login failed')
        }

        const data = await response.json()
        set({
          user: data.user,
          accessToken: data.access_token,
          refreshToken: data.refresh_token,
        })
      },

      register: async (email, password, name, orgName) => {
        const response = await fetch('/api/v1/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email,
            password,
            name,
            organization_name: orgName,
          }),
        })

        if (!response.ok) {
          throw new Error('Registration failed')
        }

        const data = await response.json()
        set({
          user: data.user,
          accessToken: data.access_token,
          refreshToken: data.refresh_token,
        })
      },

      logout: () => {
        set({ user: null, accessToken: null, refreshToken: null })
      },

      refreshAccessToken: async () => {
        const { refreshToken } = get()
        if (!refreshToken) throw new Error('No refresh token')

        const response = await fetch('/api/v1/auth/refresh', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        })

        if (!response.ok) {
          get().logout()
          throw new Error('Token refresh failed')
        }

        const data = await response.json()
        set({ accessToken: data.access_token })
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
      }),
    }
  )
)

// Auto-refresh token before expiry
setInterval(() => {
  const { accessToken, refreshAccessToken } = useAuthStore.getState()
  if (accessToken) {
    // Refresh 5 minutes before expiry
    refreshAccessToken().catch(() => {
      // Token refresh failed, logout
      useAuthStore.getState().logout()
    })
  }
}, 25 * 60 * 1000) // Every 25 minutes
```

```typescript
// src/utils/axios.ts
import axios from 'axios'
import { useAuthStore } from '../stores/authStore'

const api = axios.create({
  baseURL: '/api/v1',
})

// Request interceptor: Add JWT to headers
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor: Handle 401 with token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        await useAuthStore.getState().refreshAccessToken()

        // Retry original request with new token
        const token = useAuthStore.getState().accessToken
        originalRequest.headers.Authorization = `Bearer ${token}`
        return api(originalRequest)
      } catch (refreshError) {
        // Refresh failed, logout
        useAuthStore.getState().logout()
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)

export default api
```

#### **Deliverables:**
```bash
src/core/auth.py
src/api/v1/auth.py
src/stores/authStore.ts
src/utils/axios.ts
src/pages/LoginPage.tsx
src/pages/RegisterPage.tsx
tests/api/test_auth.py
```

#### **Acceptance Criteria:**
- ✅ Users can register with email/password
- ✅ Users can login and receive JWT
- ✅ JWT tokens include user context (id, org, role)
- ✅ Passwords hashed with bcrypt (min 8 chars)
- ✅ Token refresh works before expiry
- ✅ Invalid tokens return 401
- ✅ Inactive users cannot login
- ✅ Frontend auto-refreshes tokens
- ✅ Logout clears all tokens

---

### Feature 20.3: Redis Multi-Tenancy (3 SP)
**Priority:** MEDIUM
**Duration:** 1 day

#### **Problem:**
Redis keys are currently global. No namespace isolation for organizations, users, or projects.

#### **Solution:**
Implement project-scoped Redis namespaces with key pattern: `project:{project_id}:*`

#### **Tasks:**
- [ ] Update RedisMemoryManager with namespace support
- [ ] Implement project-scoped session storage
- [ ] Migrate existing session data (if any)
- [ ] Add key expiration policies

#### **Implementation:**

```python
# src/components/memory/redis_memory.py (UPDATED)

class RedisMemoryManager:
    """User and project-scoped Redis memory."""

    def _build_key(
        self,
        project_id: str,
        resource_type: str,
        resource_id: str,
    ) -> str:
        """Build namespaced Redis key.

        Pattern: project:{project_id}:{resource_type}:{resource_id}

        Examples:
            project:abc123:session:xyz789
            project:abc123:entity:entity001
            project:abc123:document:doc001
        """
        return f"project:{project_id}:{resource_type}:{resource_id}"

    async def store_session_messages(
        self,
        project_id: str,
        session_id: str,
        messages: list[Message],
        ttl_seconds: int = 86400,  # 24 hours
    ) -> bool:
        """Store session messages with project isolation."""
        key = self._build_key(project_id, "session", session_id)

        data = {
            "project_id": project_id,
            "session_id": session_id,
            "messages": [msg.model_dump() for msg in messages],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        await self.client.setex(key, ttl_seconds, json.dumps(data))
        return True

    async def get_session_messages(
        self,
        project_id: str,
        session_id: str,
    ) -> list[Message]:
        """Retrieve session messages."""
        key = self._build_key(project_id, "session", session_id)

        data = await self.client.get(key)
        if not data:
            return []

        parsed = json.loads(data)
        return [Message(**msg) for msg in parsed["messages"]]

    async def list_project_sessions(
        self,
        project_id: str,
        limit: int = 50,
    ) -> list[str]:
        """List all session IDs for a project."""
        pattern = f"project:{project_id}:session:*"

        keys = []
        cursor = 0

        while True:
            cursor, batch = await self.client.scan(
                cursor=cursor,
                match=pattern,
                count=100
            )
            keys.extend(batch)

            if cursor == 0:
                break

        # Extract session IDs from keys
        session_ids = [
            key.split(":")[-1] for key in keys
        ]

        return session_ids[:limit]
```

#### **Deliverables:**
```bash
src/components/memory/redis_memory.py (updated)
scripts/migrate_redis_namespaces.py
tests/memory/test_redis_multi_tenancy.py
```

#### **Acceptance Criteria:**
- ✅ All Redis keys use project namespace
- ✅ Sessions isolated per project
- ✅ Key expiration policies enforced
- ✅ Migration script for existing data

---

### Feature 20.4: Protected Routes & Middleware (3 SP)
**Priority:** HIGH
**Duration:** 1 day

#### **Problem:**
All API endpoints are unprotected. Need to enforce authentication and authorization on every request.

#### **Solution:**
Apply authentication dependencies to all endpoints, implement project access control.

#### **Tasks:**
- [ ] Update all endpoints to require authentication
- [ ] Implement `require_project_access` dependency
- [ ] Add authorization checks to existing endpoints
- [ ] Frontend: Protected route wrapper
- [ ] Auto-redirect to login if unauthorized

#### **Implementation:**

```python
# src/core/auth.py (ADDITIONAL)

async def require_project_access(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    required_role: Optional[str] = None,
) -> Project:
    """Require user to have access to project.

    Args:
        project_id: Project ID
        user: Current authenticated user
        required_role: Minimum role required (viewer, editor, owner)

    Returns:
        Project if user has access

    Raises:
        HTTPException 404 if project not found or no access
        HTTPException 403 if insufficient permissions
    """
    project_repo = ProjectRepository(Project, db)
    project = await project_repo.get_by_id(UUID(project_id))

    if not project or project.deleted_at is not None:
        raise HTTPException(404, "Project not found")

    # Check if user is owner
    if project.owner_id == user.id:
        return project

    # Check if user is member with sufficient role
    has_access = await project_repo.check_user_access(
        project_id=UUID(project_id),
        user_id=user.id,
        required_role=required_role,
    )

    if not has_access:
        raise HTTPException(403, "Insufficient project permissions")

    return project

# Example usage:
@router.get("/projects/{project_id}/sessions")
async def list_project_sessions(
    project: Project = Depends(require_project_access),
    user: User = Depends(get_current_user),
):
    """List sessions (requires project access)."""
    # User already validated by dependency
    return await session_repo.list_by_project(project.id)
```

```typescript
// src/components/ProtectedRoute.tsx
import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'

interface ProtectedRouteProps {
  children: React.ReactNode
  requireAdmin?: boolean
}

export function ProtectedRoute({ children, requireAdmin = false }: ProtectedRouteProps) {
  const { user, accessToken } = useAuthStore()
  const location = useLocation()

  if (!accessToken || !user) {
    // Redirect to login, save intended destination
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (requireAdmin && user.role !== 'admin') {
    // Redirect to home if admin required but user is not admin
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}

// src/App.tsx (UPDATED)
import { ProtectedRoute } from './components/ProtectedRoute'

<Routes>
  <Route path="/login" element={<LoginPage />} />
  <Route path="/register" element={<RegisterPage />} />

  <Route path="/" element={
    <ProtectedRoute>
      <HomePage />
    </ProtectedRoute>
  } />

  <Route path="/projects/:projectId" element={
    <ProtectedRoute>
      <ProjectDetailPage />
    </ProtectedRoute>
  } />

  <Route path="/admin" element={
    <ProtectedRoute requireAdmin>
      <AdminPage />
    </ProtectedRoute>
  } />
</Routes>
```

#### **Deliverables:**
```bash
src/core/auth.py (updated with require_project_access)
src/api/v1/chat.py (updated with auth)
src/api/v1/admin.py (updated with auth)
src/components/ProtectedRoute.tsx
tests/api/test_authorization.py
```

#### **Acceptance Criteria:**
- ✅ All endpoints require authentication
- ✅ Project endpoints check user access
- ✅ Role-based authorization works
- ✅ Frontend redirects unauthorized users
- ✅ 403 errors for insufficient permissions
- ✅ 401 errors for invalid tokens

---

## Testing Strategy

### Unit Tests
```python
# tests/core/test_auth.py
def test_hash_password():
    hashed = hash_password("test123456")
    assert hashed != "test123456"
    assert verify_password("test123456", hashed)

def test_create_access_token():
    user = User(id=uuid4(), email="test@example.com", role="user")
    token = create_access_token(user)
    assert token is not None

    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == str(user.id)
    assert payload["type"] == "access"

# tests/repositories/test_project_repository.py
async def test_list_for_user():
    # User should see projects where they are member
    projects = await project_repo.list_for_user(user.id, org.id)
    assert len(projects) == 2

async def test_check_user_access():
    # User with editor role should have access
    has_access = await project_repo.check_user_access(
        project.id, user.id, required_role="viewer"
    )
    assert has_access is True
```

### Integration Tests
```python
# tests/api/test_auth_integration.py
async def test_register_and_login(client):
    # Register
    response = await client.post("/api/v1/auth/register", json={
        "email": "newuser@example.com",
        "password": "securepass123",
        "name": "New User",
        "organization_name": "Test Org"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

    # Login with same credentials
    response = await client.post("/api/v1/auth/login", json={
        "email": "newuser@example.com",
        "password": "securepass123",
    })
    assert response.status_code == 200

async def test_protected_endpoint_without_auth(client):
    # Should return 401
    response = await client.get("/api/v1/projects")
    assert response.status_code == 401
```

---

## Documentation

### API Documentation
- OpenAPI schema with authentication examples
- Postman collection with JWT setup
- cURL examples for all endpoints

### Database Documentation
- ER diagram
- Schema documentation
- Index strategy explanation

### Migration Guide
- How to migrate existing sessions
- Database backup procedures
- Rollback instructions

---

## Deployment Checklist

- [ ] PostgreSQL backup configured
- [ ] Environment variables set
- [ ] Database migrations run
- [ ] JWT secret key rotated
- [ ] Connection pool tuned
- [ ] Redis namespaces migrated
- [ ] Health checks passing
- [ ] Smoke tests passing

---

## Sprint 20 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Registration time | <3s | API latency |
| Login time | <1s | API latency |
| Token validation | <10ms | Middleware timing |
| Database query time | <50ms p95 | Query logs |
| Test coverage | >90% | Coverage report |
| Auth failure rate | <1% | Error logs |

---

**Sprint 20 Completion:** Foundation ready for Sprint 21 (Projects)
**Next Sprint:** Sprint 21 - Project Collaboration System
