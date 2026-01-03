# Memory Management Guide

**Document:** Feature 72.3 - Memory Management UI
**Status:** Complete
**Last Updated:** 2026-01-03

---

## Overview

The Memory Management page (`/admin/memory`) provides a comprehensive debugging and administration interface for the 3-layer memory system without requiring direct database access. This guide covers memory statistics, searching, consolidation, and troubleshooting.

### Architecture Overview

AegisRAG uses a 3-layer memory system:

| Layer | Storage | Latency | Purpose | Retention |
|-------|---------|---------|---------|-----------|
| **Layer 1: Fast** | Redis | <10ms | Session state, working memory | 1-24 hours (TTL) |
| **Layer 2: Semantic** | Qdrant | <50ms | Long-term semantic memory | Permanent |
| **Layer 3: Episodic** | Graphiti + Neo4j | <200ms | Temporal relationships | Versioned (time-aware) |

The Memory Management UI gives you visibility into all three layers with search and consolidation capabilities.

---

## Navigation

### Accessing the Memory Management Page

1. **From Admin Dashboard:**
   - Navigate to `https://your-domain/admin`
   - Click the **"Memory"** tab in the navigation bar
   - Or click **"Manage Memory"** button

2. **Direct URL:**
   - `https://your-domain/admin/memory`

3. **Mobile Access:**
   - Same URL works on mobile with responsive tab interface
   - Tabs: "Statistics" | "Search" | "Consolidation"

### Layout Overview

#### Desktop (≥768px width)
```
┌─────────────────────────────────────────────────────────┐
│  Tab Navigation: Statistics | Search | Consolidation   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  [Active Tab Content]                                   │
│                                                         │
│  - Statistics: Memory layer dashboards & metrics        │
│  - Search: Find data by user/session/keywords           │
│  - Consolidation: Trigger & monitor consolidation       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### Mobile (<768px width)
```
┌──────────────────────────────────────┐
│  [Tab Button] [Tab Button] [Tab...]   │
├──────────────────────────────────────┤
│                                      │
│  [Active Tab Content - Responsive]   │
│                                      │
└──────────────────────────────────────┘
```

---

## Tab 1: Statistics

The Statistics tab displays real-time metrics for all three memory layers.

### Layer 1: Redis (Fast Memory)

**Purpose:** Session state, working memory, short-term context

**Card Display:**
```
┌─────────────────────────────────────┐
│ Redis (Layer 1: Fast Memory)        │
│ Status: ✓ Healthy                   │
├─────────────────────────────────────┤
│ Connected Clients: 12               │
│ Total Keys: 2,847                   │
│ Memory Used: 125 MB                 │
│ Memory Limit: 512 MB (24% used)     │
│ Hit Rate: 87.3%                     │
│ Avg Latency: 3.2ms                  │
│ TTL Avg: 2h 15m                     │
│                                     │
│ [Refresh] [Clear] [Settings]        │
└─────────────────────────────────────┘
```

**Metrics Explained:**

| Metric | Normal Range | Warning | Critical |
|--------|--------------|---------|----------|
| **Connected Clients** | 1-20 | >30 | >50 |
| **Total Keys** | 100-10K | >50K | >100K |
| **Memory Used** | <50% limit | 70-90% | >90% |
| **Hit Rate** | >85% | 70-85% | <70% |
| **Avg Latency** | <10ms | 10-50ms | >50ms |

**Key Actions:**

- **[Refresh]:** Update metrics immediately (default: auto-refresh every 10s)
- **[Clear]:** Remove ALL expired keys manually (usually automatic)
- **[Settings]:** Configure TTL, memory limits, eviction policy

### Layer 2: Qdrant (Semantic Memory)

**Purpose:** Long-term semantic embeddings, permanent knowledge storage

**Card Display:**
```
┌─────────────────────────────────────┐
│ Qdrant (Layer 2: Semantic Memory)   │
│ Status: ✓ Healthy                   │
├─────────────────────────────────────┤
│ Collections: 3                      │
│ Points (Vectors): 45,832            │
│ Memory Used: 1.2 GB                 │
│ Search Latency: 23ms                │
│ Replication Factor: 1               │
│ Avg Score: 0.76                     │
│ Latest Update: 2 mins ago           │
│                                     │
│ [View Collections] [Optimize]       │
└─────────────────────────────────────┘
```

**Collections Breakdown:**

Click **[View Collections]** to see:

| Collection | Purpose | Vector Dim | Points | Size |
|-----------|---------|-----------|--------|------|
| `memories_v1` | User conversations | 1024 | 28,450 | 650MB |
| `embeddings` | Document chunks | 1024 | 15,200 | 420MB |
| `entities` | Extracted entities | 1024 | 2,182 | 65MB |

**Key Actions:**

- **[View Collections]:** Browse detailed collection statistics
- **[Optimize]:** Trigger index optimization (may take 5-10 minutes)
- **[Reindex]:** Rebuild indices from scratch (rare)

### Layer 3: Graphiti (Episodic Memory)

**Purpose:** Temporal relationships, entity history, time-aware queries

**Card Display:**
```
┌─────────────────────────────────────┐
│ Graphiti (Layer 3: Episodic Memory) │
│ Status: ✓ Healthy                   │
├─────────────────────────────────────┤
│ Neo4j Backend: ✓ Connected          │
│ Total Nodes: 12,847                 │
│ Total Relationships: 34,521         │
│ Memory Used: 780 MB                 │
│ Query Latency: 45ms                 │
│ Last Consolidation: 1h 23m ago      │
│ Temporal Scope: 90 days             │
│                                     │
│ [View Nodes] [Cleanup] [Timeline]   │
└─────────────────────────────────────┘
```

**Node Types Breakdown:**

| Type | Count | Purpose |
|------|-------|---------|
| MEMORY | 8,234 | Conversation memories |
| ENTITY | 2,892 | Extracted entities |
| INTERACTION | 1,721 | User interactions |

**Key Actions:**

- **[View Nodes]:** Explore node types and relationships
- **[Cleanup]:** Remove entities older than retention period (90 days default)
- **[Timeline]:** View temporal evolution of knowledge

### Memory Summary Card

```
┌─────────────────────────────────────┐
│ Memory Summary                      │
├─────────────────────────────────────┤
│ Total Capacity: 2.8 GB              │
│ Used: 2.1 GB (75%)                  │
│ Available: 700 MB                   │
│                                     │
│ Status: ⚠ Warning - Consider       │
│         consolidation               │
│                                     │
│ Data Across Layers:                 │
│ ├─ Fast Layer: 125 MB   (4%)        │
│ ├─ Semantic Layer: 1.2 GB (43%)     │
│ └─ Episodic Layer: 780 MB (28%)     │
│                                     │
│ [View Breakdown] [Consolidate]      │
└─────────────────────────────────────┘
```

---

## Tab 2: Search

The Search tab allows finding data across all memory layers by user, session, keywords, or date range.

### Search Interface

```
┌─────────────────────────────────────┐
│ SEARCH FILTERS                      │
├─────────────────────────────────────┤
│                                     │
│ Search Type: ◯ All ◉ Fast ◯ Semantic │
│              ◯ Episodic             │
│                                     │
│ User ID: [___________________]      │
│          (leave empty for all)      │
│                                     │
│ Session ID: [___________________]   │
│            (leave empty for all)    │
│                                     │
│ Keywords: [___________________]     │
│          (comma-separated)          │
│                                     │
│ Date Range:                         │
│ From: [2026-01-01]  To: [2026-01-03]│
│                                     │
│ [Search] [Clear Filters] [Export]   │
│                                     │
└─────────────────────────────────────┘

Results: 347 memories found

┌─────────────────────────────────────┐
│ Search Results                      │
├─────────────────────────────────────┤
│ 1. Fast Memory (125 matches)        │
│    ├─ [user123:query] "weather..."  │
│    ├─ [user456:state] "location..." │
│    └─ 123 more...                   │
│                                     │
│ 2. Semantic Memory (156 matches)    │
│    ├─ "climate" [0.92]              │
│    ├─ "temperature" [0.88]          │
│    └─ 154 more...                   │
│                                     │
│ 3. Episodic Memory (66 matches)     │
│    ├─ Discussion about weather      │
│    ├─ Entity: "Climate Change"      │
│    └─ 64 more...                    │
└─────────────────────────────────────┘
```

### Search Types

#### All Layers
Searches across all three layers simultaneously, returns results grouped by layer

**Use Case:** Finding any data related to a topic without knowing storage layer

#### Fast Layer (Redis)
Searches current session state and working memory only

**Use Case:** Debugging current user session or temporary state issues

**Search Field:** Key patterns (e.g., `user:123:*` or `session:abc:`)

#### Semantic Layer (Qdrant)
Full-text and vector similarity search

**Use Case:** Finding relevant context by meaning, not exact keywords

**Search Field:** Free-form text (automatically vectorized for similarity)

#### Episodic Layer (Graphiti)
Graph traversal and temporal queries

**Use Case:** Understanding how knowledge changed over time

**Search Field:** Entity names or relationship types

### Search Examples

**Example 1: Find all memories for a user**

```
Search Type: All
User ID: user_abc123
Session ID: (empty)
Keywords: (empty)
Date Range: Last 30 days

Results:
✓ Fast Memory: 3 active sessions
✓ Semantic Memory: 47 related embeddings
✓ Episodic Memory: 12 temporal relationships
```

**Example 2: Find discussions about a specific topic**

```
Search Type: Semantic
User ID: (empty)
Session ID: (empty)
Keywords: machine learning, neural networks, deep learning
Date Range: Last 90 days

Results:
[Results ranked by semantic relevance, newest first]
```

**Example 3: Trace entity evolution**

```
Search Type: Episodic
User ID: (empty)
Session ID: (empty)
Keywords: "Product Launch"
Date Range: Last 180 days

Results:
Timeline view showing how "Product Launch" concept
changed over time with relationships
```

### Search Result Actions

For each result, available actions:

| Action | Purpose | Details |
|--------|---------|---------|
| **View** | See full content | Opens detailed view |
| **Copy** | Copy ID/content | For use in other tools |
| **Delete** | Remove from memory | Requires confirmation |
| **Export** | Download as JSON | For backup/analysis |
| **Tag** | Add metadata | For organization |

---

## Tab 3: Consolidation

Memory consolidation moves data from fast layers to slower but more durable layers. This tab monitors and controls the consolidation process.

### Consolidation Overview

**What is Consolidation?**

Consolidation is the process of:
1. Taking transient data from Redis (fast, volatile)
2. Converting to embeddings
3. Storing in Qdrant (durable) and Graphiti (temporal)
4. Removing from Redis to free memory

**Why Consolidate?**
- Free up fast memory for new sessions
- Preserve important context permanently
- Create temporal snapshots
- Improve query performance

### Consolidation Status

```
┌─────────────────────────────────────┐
│ Consolidation Status                │
├─────────────────────────────────────┤
│                                     │
│ Last Consolidation: 1h 23m ago      │
│ Status: ✓ Completed                 │
│                                     │
│ Progress:                           │
│ ████████████████░░░░░  82%         │
│                                     │
│ Consolidated Items:                 │
│ ├─ From Redis: 342 items            │
│ ├─ To Qdrant: 342 items             │
│ ├─ To Graphiti: 289 items           │
│ └─ Discarded (expired): 53 items    │
│                                     │
│ Performance:                        │
│ ├─ Duration: 2m 34s                 │
│ ├─ Throughput: 2.2 items/sec        │
│ └─ Errors: 0                        │
│                                     │
│ Next Scheduled: 2026-01-03 15:00   │
│ Interval: Every 1 hour              │
│                                     │
│ [Consolidate Now] [Settings]        │
│                                     │
└─────────────────────────────────────┘
```

### Manual Consolidation

**When to Consolidate Manually:**
- After large document ingestion
- When Redis memory is high (>80%)
- Before system maintenance
- To create a temporal snapshot

**Steps:**

1. **Click [Consolidate Now] button**
2. **Confirm the action** (dialog appears)
   - Shows estimated items to consolidate
   - Estimated duration
3. **Monitor progress bar**
   - Real-time percentage
   - Item count
   - Current operation
4. **View results:**
   - Success summary
   - Items consolidated
   - Any errors or warnings

**Example Execution:**

```
[Consolidate Now] clicked

↓ Confirmation Dialog ↓

Consolidate Memory Now?

This will:
- Move 342 items from Redis to Qdrant/Graphiti
- Free ~95 MB from memory
- Take approximately 2-3 minutes
- Cannot be undone (consolidation is permanent)

[Cancel]  [Consolidate]

↓ Progress ↓

Consolidating...
████████████████████░░░░░░░░░░ 67%
342 items processed

Duration: 1m 45s
Current: Storing in Graphiti...

↓ Completion ↓

✓ Consolidation Complete

Consolidated:
  - Redis → Qdrant: 342 items
  - Redis → Graphiti: 289 items (temporal)
  - Expired & removed: 53 items

Memory Freed: 95 MB
Errors: 0
```

### Consolidation Settings

Click **[Settings]** to configure:

| Setting | Default | Range | Purpose |
|---------|---------|-------|---------|
| **Interval** | 1 hour | 15min - 24h | Auto-consolidation frequency |
| **Threshold** | 80% | 60-95% | Trigger consolidation when Redis > X% |
| **Retention** | 90 days | 7-365 days | Keep data in Graphiti for X days |
| **Batch Size** | 100 items | 10-1000 | Items consolidated per batch |
| **Auto Enable** | ON | ON/OFF | Enable automatic consolidation |

**Advanced Settings:**

- **Parallel Processing:** Use multiple workers (default: 4)
- **Compression:** Compress stored embeddings (default: ON)
- **Deduplication:** Remove duplicate memories before storing (default: ON)

### Consolidation History

Click **[View History]** to see past consolidations:

```
┌─────────────────────────────────────┐
│ Consolidation History (Last 30 days)│
├─────────────────────────────────────┤
│                                     │
│ 2026-01-03 14:00 ✓ SUCCESS          │
│ Items: 342 → Qdrant: 342            │
│ Duration: 2m 34s                    │
│                                     │
│ 2026-01-03 13:00 ✓ SUCCESS          │
│ Items: 287 → Qdrant: 287            │
│ Duration: 2m 08s                    │
│                                     │
│ 2026-01-03 12:00 ⚠ PARTIAL FAILURE   │
│ Items: 156 → Qdrant: 154            │
│ Failures: 2 (will retry)            │
│ Duration: 1m 45s                    │
│                                     │
│ 2026-01-02 11:00 ✓ SUCCESS          │
│ Items: 401 → Qdrant: 401            │
│ Duration: 3m 22s                    │
│                                     │
│ [View Details] [Retry Failed]       │
│                                     │
└─────────────────────────────────────┘
```

---

## Common Use Cases

### Use Case 1: Monitor Memory Usage Before Maintenance

**Scenario:** Planning system maintenance, need to free memory

**Steps:**

1. **Go to Statistics tab**
2. **Review memory breakdown:**
   - Check if any layer is >90% full
3. **Go to Consolidation tab**
4. **Click [Consolidate Now]**
5. **Monitor progress**
6. **Verify memory freed**

**Expected Outcome:**
Redis usage drops from 85% to <30%, system ready for maintenance

### Use Case 2: Investigate User Session

**Scenario:** Debug why a user's session has stale data

**Steps:**

1. **Go to Search tab**
2. **Enter User ID:** `user_xyz789`
3. **Click [Search]**
4. **Review results across layers:**
   - Fast: Current session state
   - Semantic: Related embeddings
   - Episodic: Historical context
5. **[View] individual items** to inspect content
6. **Identify stale data** and [Delete] if needed

**Expected Outcome:**
Clear understanding of data across all layers for this user

### Use Case 3: Prepare for Data Export/Backup

**Scenario:** Want to export all memory before major update

**Steps:**

1. **Go to Consolidation tab**
2. **Click [Consolidate Now]** to create clean state
3. **Go to Search tab**
4. **Search: All layers, empty filters**
5. **Click [Export]** on results
6. **Choose format:** JSON, CSV, or Parquet
7. **Download backup file**

**Expected Outcome:**
Complete snapshot of all memory layers in portable format

---

## Troubleshooting

### Issue: Redis Memory Usage High (>90%)

**Problem:** Redis card shows red indicator, >90% memory used

**Diagnosis:**

```
Check:
1. Connected clients count (should be <30)
2. Total keys (should be <10,000)
3. Hit rate (should be >85%)
4. TTL average (should be >1 hour)
```

**Solutions:**

**Option 1: Manual Consolidation (Fastest)**
```
1. Go to Consolidation tab
2. Click [Consolidate Now]
3. Wait for completion
4. Should free 30-60% memory
```

**Option 2: Reduce TTL**
```
1. Statistics tab → Redis card
2. Click [Settings]
3. Reduce TTL average (default: 2h → try 1h)
4. Saves memory by expiring data faster
```

**Option 3: Clear Specific Sessions**
```
1. Search tab → Search Type: Fast Layer
2. Enter User ID or Session ID
3. For each result: [Delete]
4. Repeat until memory acceptable
```

**Option 4: Increase Consolidation Frequency**
```
1. Consolidation tab → [Settings]
2. Reduce Interval (1h → 30min)
3. Enable Auto Consolidation if disabled
```

### Issue: Qdrant Search Latency High (>100ms)

**Problem:** Semantic layer showing yellow/red latency

**Causes:**
- Index fragmented
- Collection too large
- Network latency

**Solutions:**

1. **Optimize Qdrant:**
   ```
   Statistics → Qdrant card → [Optimize]
   (Takes 5-10 minutes, may spike latency)
   ```

2. **Check network:**
   ```bash
   # From admin server
   ping qdrant-host
   curl -s http://qdrant:6333/health
   ```

3. **Review collection size:**
   ```
   Statistics → Qdrant → [View Collections]
   If single collection >1GB, consider archiving old data
   ```

### Issue: Consolidation Keeps Failing

**Problem:** Consolidation shows errors or doesn't complete

**Causes:**
- Qdrant or Neo4j offline
- Network connectivity issue
- Insufficient disk space

**Diagnosis:**

```
1. Check Consolidation History for error details
2. Verify Qdrant status: Statistics → Qdrant card
3. Verify Graphiti status: Statistics → Graphiti card
4. Check system resources: free disk space, network
```

**Solutions:**

1. **Restart affected service:**
   ```bash
   docker restart aegis-rag-qdrant
   docker restart neo4j
   ```

2. **Check backend logs:**
   ```bash
   docker logs aegis-rag-api | grep consolidat
   ```

3. **Manually retry:**
   ```
   Consolidation History → [Retry Failed]
   ```

4. **Check disk space:**
   ```bash
   df -h  # Should have >10% free
   ```

### Issue: Search Results Empty

**Problem:** Search finds no results when data should exist

**Causes:**
- Search filters too restrictive
- User ID/Session ID misspelled
- Data in different layer than expected

**Solutions:**

1. **Broaden search:**
   - Clear User ID filter
   - Clear Date Range (or expand)
   - Try "All Layers" instead of specific layer

2. **Verify data exists:**
   - Go to Statistics tab
   - Confirm layer has data (not all empty)
   - Check "Points" or "Total Keys"

3. **Try exact match:**
   - Search for specific ID, exact format
   - No wildcards (auto-complete helps)

### Issue: Memory Export Takes Too Long

**Problem:** [Export] button hangs or times out

**Causes:**
- Too much data selected
- Network issues
- Browser memory limit

**Solutions:**

1. **Export smaller subset:**
   - Use Date Range to limit data (last 7 days)
   - Export by User ID
   - Choose CSV instead of JSON (smaller)

2. **Try direct API:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/memory/export \
     -H "Authorization: Bearer TOKEN" \
     -d '{"date_from": "2026-01-01", "limit": 1000}' \
     > memory_export.json
   ```

3. **Check browser memory:**
   - Close other tabs
   - Try different browser
   - Use incognito mode

---

## Best Practices

### Memory Management

1. **Monitor Regularly**
   - Check Statistics tab daily
   - Set alert if any layer >80% full
   - Review trends over time

2. **Consolidate Proactively**
   - Enable automatic consolidation
   - Run manual consolidation during low-traffic hours
   - Keep history for audit trail

3. **Archive Old Data**
   - Regularly export data >90 days old
   - Delete archived data from Graphiti
   - Maintain backup copies offline

4. **Optimize Storage**
   - Use Qdrant compression features
   - Deduplicate similar memories
   - Clean up temporary session state

### Troubleshooting Workflow

1. **Observe:** Check Statistics tab metrics
2. **Diagnose:** Note which layer has issues
3. **Investigate:** Use Search tab to drill down
4. **Resolve:** Apply targeted fix
5. **Verify:** Confirm metrics improved

### Performance Tuning

| Goal | Action | Impact |
|------|--------|--------|
| Lower latency | Optimize Qdrant indices | 10-20% faster |
| Save memory | Reduce TTL, consolidate | 20-40% reduction |
| Improve reliability | Enable replication | Prevents data loss |
| Speed up search | Increase batch size | 15-30% faster |

---

## API Reference

### Backend Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/memory/stats` | Get all layer statistics |
| GET | `/api/v1/memory/redis/stats` | Get Redis stats |
| GET | `/api/v1/memory/qdrant/stats` | Get Qdrant stats |
| GET | `/api/v1/memory/graphiti/stats` | Get Graphiti stats |
| GET | `/api/v1/memory/search` | Search across layers |
| POST | `/api/v1/memory/consolidate` | Trigger consolidation |
| GET | `/api/v1/memory/consolidate/history` | Get consolidation history |
| GET | `/api/v1/memory/consolidate/status` | Get current status |
| POST | `/api/v1/memory/export` | Export memory to JSON |

### Example API Calls

```bash
# Get memory statistics
curl -X GET http://localhost:8000/api/v1/memory/stats \
  -H "Authorization: Bearer YOUR_TOKEN"

# Search for user memories
curl -X GET "http://localhost:8000/api/v1/memory/search?user_id=user_123&layer=all" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Trigger consolidation
curl -X POST http://localhost:8000/api/v1/memory/consolidate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"force": true}'

# Export memory data
curl -X POST http://localhost:8000/api/v1/memory/export \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "date_from": "2025-12-01",
    "date_to": "2026-01-03",
    "format": "json",
    "layers": ["all"]
  }' > memory_backup.json
```

---

## FAQ

**Q: How often should I consolidate memory?**
A: Automatic consolidation runs every 1 hour (default). Manual consolidation after large imports or when Redis >80% full.

**Q: Will consolidation delete my data?**
A: No, consolidation preserves all data. It moves from fast to slow storage and removes expired data only.

**Q: What's the difference between delete and consolidation?**
A: Delete removes data permanently. Consolidation moves it to durable storage and frees fast memory.

**Q: Can I recover deleted memories?**
A: Only if you have a backup. Always export before deleting significant data.

**Q: What if consolidation fails mid-way?**
A: The failed items remain in Redis and are retried in the next consolidation. No data is lost.

**Q: How long can I keep data in Graphiti?**
A: Default is 90 days. Adjust in Consolidation Settings (max: 365 days).

**Q: Is exported data encrypted?**
A: No, exports are plain JSON. Encrypt them yourself for sensitive data.

**Q: Can I import data from backups?**
A: Yes, use the Import API endpoint (feature in development).

---

## Related Documentation

- [ARCHITECTURE.md](../ARCHITECTURE.md) - Memory system design
- [TECH_STACK.md](../TECH_STACK.md) - Technology details
- [MCP Tools Admin Guide](./MCP_TOOLS_ADMIN_GUIDE.md)
- [API Documentation](../api/admin.md)
- [Troubleshooting Guide](./TROUBLESHOOTING.md)

---

**Document Version:** 1.0
**Feature:** Sprint 72.3
**Compatibility:** Frontend React 19, Backend FastAPI 0.115+
**Memory System:** Redis 7.x, Qdrant 1.11.0, Graphiti 0.3.0, Neo4j 5.24
