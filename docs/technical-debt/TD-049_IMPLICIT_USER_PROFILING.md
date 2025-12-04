# TD-049: Implicit User Profiling (Sprint 17)

**Status:** OPEN
**Priority:** MEDIUM (Strategic)
**Severity:** Feature Gap
**Original Sprint:** Sprint 17 (Feature 17.4)
**Story Points:** 21 SP
**Created:** 2025-12-04

---

## Problem Statement

AegisRAG currently treats all users identically, missing the opportunity to personalize responses based on user behavior patterns. There is no implicit user profiling, no conversation search capability, and no way to build understanding of user preferences over time.

**Current State:**
- No user profile tracking
- No conversation search
- No preference-based personalization
- Each session is independent

---

## Strategic Value

### Business Impact
- **Personalization:** Tailor responses to user expertise level
- **Efficiency:** Reduce repeated explanations for known users
- **Insights:** Understand user interests and common queries
- **Engagement:** Build long-term user relationships

### Technical Value
- Foundation for multi-user environments
- Enable conversation search and analytics
- Support for user-specific document access (RBAC preparation)

---

## Solution Architecture

### 1. User Profile Graph (Neo4j)

```cypher
// User Profile Node
CREATE (u:UserProfile {
    user_id: "user_123",
    created_at: datetime(),
    last_active: datetime(),
    total_queries: 42,
    expertise_level: "intermediate",  // Inferred from queries
    preferred_topics: ["kubernetes", "monitoring"]
})

// User Interest Relationships
MATCH (u:UserProfile {user_id: $user_id})
MATCH (t:Topic {name: $topic})
CREATE (u)-[:INTERESTED_IN {
    weight: 0.85,
    query_count: 15,
    last_query: datetime()
}]->(t)

// Conversation Nodes
CREATE (c:Conversation {
    conversation_id: "conv_abc",
    user_id: "user_123",
    title: "Kubernetes Monitoring Setup",
    created_at: datetime(),
    query_count: 5
})
```

### 2. Profile Building Pipeline

```python
# src/components/user/profile_builder.py

class UserProfileBuilder:
    """Build implicit user profile from behavior."""

    async def update_profile_from_query(
        self,
        user_id: str,
        query: str,
        topics: List[str],
        entities: List[str]
    ) -> None:
        """Update user profile based on query."""
        # Extract topics from query
        # Update interest weights
        # Infer expertise level from terminology
        # Update last_active timestamp

    async def get_user_context(
        self,
        user_id: str
    ) -> UserContext:
        """Get user context for personalization."""
        return UserContext(
            expertise_level=...,
            preferred_topics=...,
            recent_conversations=...,
            total_interactions=...
        )
```

### 3. Conversation Search (Qdrant)

```python
# src/components/memory/conversation_search.py

class ConversationSearch:
    """Semantic search over conversation history."""

    async def search_conversations(
        self,
        user_id: str,
        query: str,
        limit: int = 10
    ) -> List[ConversationResult]:
        """Search user's conversation history."""
        # Embed query
        # Search in user's conversation collection
        # Return relevant past conversations
```

### 4. API Endpoints

```python
# src/api/v1/user.py

@router.get("/api/v1/user/profile")
async def get_user_profile(user_id: str) -> UserProfile:
    """Get user profile with interests and stats."""

@router.get("/api/v1/user/conversations/search")
async def search_conversations(
    user_id: str,
    query: str,
    limit: int = 10
) -> List[ConversationSummary]:
    """Semantic search over user's conversations."""

@router.get("/api/v1/user/topics")
async def get_user_topics(user_id: str) -> List[TopicInterest]:
    """Get user's top topics of interest."""
```

---

## Implementation Tasks

### Phase 1: User Profile Schema (5 SP)
- [ ] Create UserProfile Pydantic model
- [ ] Add Neo4j schema for UserProfile nodes
- [ ] Add INTERESTED_IN relationship type
- [ ] Create UserProfileService class
- [ ] Unit tests for profile operations

### Phase 2: Profile Building (8 SP)
- [ ] Implement topic extraction from queries
- [ ] Build interest weight calculation
- [ ] Implement expertise level inference
- [ ] Integrate with chat endpoint
- [ ] Integration tests

### Phase 3: Conversation Search (5 SP)
- [ ] Create conversation embeddings collection in Qdrant
- [ ] Implement ConversationSearch service
- [ ] Add search API endpoint
- [ ] Frontend search integration

### Phase 4: Frontend Integration (3 SP)
- [ ] User profile display component
- [ ] Conversation search UI
- [ ] Topic visualization

---

## Acceptance Criteria

- [ ] User profiles created implicitly from behavior
- [ ] Interest topics tracked and weighted
- [ ] Expertise level inferred (beginner/intermediate/expert)
- [ ] Conversation search returns relevant past discussions
- [ ] Profile accessible via API
- [ ] Frontend shows user profile and interests
- [ ] 80%+ test coverage for new components

---

## Affected Files

```
src/components/user/                    # NEW directory
├── profile_builder.py                  # Profile building logic
├── profile_service.py                  # Profile CRUD operations
├── conversation_search.py              # Conversation search
└── models.py                           # Pydantic models

src/api/v1/user.py                      # NEW: User API endpoints
src/components/graph_rag/neo4j_client.py  # Add profile queries
frontend/src/components/user/           # NEW: User UI components
```

---

## Dependencies

- **TD-043:** Follow-up Questions Redis Fix (conversation persistence)
- **Sprint 35 Feature 35.4:** Auto-Generated Conversation Titles

---

## Privacy Considerations

- User profiles stored locally (no external tracking)
- Profile data can be exported/deleted (GDPR compliance)
- No PII in profile (only behavioral data)
- Opt-out mechanism available

---

## Estimated Effort

**Story Points:** 21 SP

**Breakdown:**
- Phase 1 (Schema): 5 SP
- Phase 2 (Building): 8 SP
- Phase 3 (Search): 5 SP
- Phase 4 (Frontend): 3 SP

---

## References

- [SPRINT_PLAN.md - Sprint 17 Feature 17.4](../sprints/SPRINT_PLAN.md#sprint-17)

---

## Target Sprint

**Recommended:** Sprint 39 (strategic feature, lower priority than core fixes)

---

**Last Updated:** 2025-12-04
