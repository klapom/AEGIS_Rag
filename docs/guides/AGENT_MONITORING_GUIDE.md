# Agent Monitoring Guide

**Last Updated:** 2026-01-15 (Sprint 98 Plan)
**Status:** Planned - Sprint 98
**Audience:** DevOps engineers, System administrators, ML engineers
**Prerequisite Knowledge:** LangGraph, multi-agent systems, distributed systems

---

## Overview

The Agent Monitoring UI provides real-time visibility into AegisRAG's multi-agent system. This guide covers:

- **Agent Communication Dashboard** - Monitor inter-agent MessageBus and Blackboard state
- **Agent Hierarchy Visualizer** - Visualize Executive→Manager→Worker delegation chains
- **Performance Metrics** - Track latency, success rates, resource usage per agent
- **Troubleshooting** - Debug coordination issues and identify bottlenecks

**Why This Matters:**
AegisRAG uses a hierarchical agent architecture where the Executive agent (coordinator) delegates tasks to Manager agents, which delegate to Worker agents. Monitoring ensures efficient task routing, early detection of failures, and system-wide performance optimization.

---

## 1. Multi-Agent Architecture Overview

### 1.1 Agent Hierarchy

```
                    ┌────────────────────┐
                    │ Executive Director │ (Coordinator)
                    │   (Main orchestrator)
                    └─────────┬──────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
    ┌─────▼────────┐  ┌──────▼──────┐  ┌────────▼──────┐
    │Research      │  │Analysis     │  │Synthesis      │
    │Manager       │  │Manager      │  │Manager        │
    │(retrieval,   │  │(analysis,   │  │(generation,   │
    │web_search)   │  │validation)  │  │summarization) │
    └─────┬────────┘  └──────┬──────┘  └────────┬──────┘
          │                   │                   │
    ┌─────▼─────┬─────┐  ┌───▼──┐  ┌─────┬──────▼──┐
    │W1: Vector │W2: │W3:Graph│W4: │W5:  │W6: LLM  │
    │Search    │Web  │Query   │Eval│Rank │Gen      │
    └───────────┴─────┘  └──────┘  └─────┴─────────┘

Worker agents = specific tools/skills (leaf level)
Manager agents = supervise workers, handle retries
Executive = main coordinator, handles routing
```

**Agent types:**

| Level | Role | Example | Responsibilities |
|-------|------|---------|------------------|
| **Executive** | Coordinator | Director | Route queries, manage phases, orchestrate managers |
| **Manager** | Supervisor | ResearchManager | Supervise workers, retry on failure, aggregate results |
| **Worker** | Tool executor | VectorSearch | Execute single skill/tool, report results |

### 1.2 Communication Patterns

**MessageBus:**
Agents communicate via async messages. Each message includes:
- Sender agent ID
- Recipient agent ID (or broadcast)
- Message type (SKILL_REQUEST, SKILL_RESPONSE, ERROR, etc.)
- Payload (query, results, etc.)
- Timestamp and trace ID (for debugging)

**Blackboard (Shared Memory):**
Agents read/write to shared memory organized by namespace:
- `retrieval` - Documents retrieved so far
- `synthesis` - Intermediate answers
- `reflection` - Quality checks and criticisms
- `execution_plan` - Current phase and tasks

---

## 2. Agent Communication Dashboard

### 2.1 Overview

Real-time monitor of MessageBus traffic and Blackboard state.

### 2.2 Accessing the Dashboard

Navigate to **Admin Dashboard > Agents > Communication**.

```
┌─────────────────────────────────────────────────────────────┐
│ Agent Communication Dashboard          Last: 12:34:56 (live)│
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ [MessageBus Monitor] [Blackboard] [Orchestrations] [Metrics]│
│                                                             │
│ ┌───────────────────────────────────────────────────────┐  │
│ │ Real-time MessageBus (Live)            [Pause] [Clear]│  │
│ │ ───────────────────────────────────────────────────── │  │
│ │                                                       │  │
│ │ 14:23:45.203 ResearchMgr → W1 (VectorSearch)         │  │
│ │   Type: SKILL_REQUEST                                │  │
│ │   Query: "What is quantum computing?"                │  │
│ │   Context budget: 2000 tokens                         │  │
│ │   [View Details]                                     │  │
│ │                                                       │  │
│ │ 14:23:45.524 W1 → ResearchMgr (VectorSearch)         │  │
│ │   Type: SKILL_RESPONSE                               │  │
│ │   Results: 8 documents retrieved                      │  │
│ │   Duration: 321ms                                     │  │
│ │   [View Details]                                     │  │
│ │                                                       │  │
│ │ 14:23:45.612 Executive → ALL (broadcast)             │  │
│ │   Type: PHASE_UPDATE                                 │  │
│ │   Phase: 2/3 (Aggregation)                           │  │
│ │   Status: In progress                                │  │
│ │   [View Details]                                     │  │
│ │                                                       │  │
│ │ 14:23:46.150 SynthesisMgr → W6 (LLMGen)             │  │
│ │   Type: SKILL_REQUEST                                │  │
│ │   Input contexts: 8 documents                         │  │
│ │   [View Details]                                     │  │
│ │                                                       │  │
│ └───────────────────────────────────────────────────────┘  │
│                                                             │
│ ┌───────────────────────────────────────────────────────┐  │
│ │ Blackboard State                                      │  │
│ │ ───────────────────────────────────────────────────── │  │
│ │ retrieval:                                            │  │
│ │   documents: 8 retrieved                              │  │
│ │   total_tokens: 1,847 / 2000                          │  │
│ │   confidence: 0.89                                    │  │
│ │   [View Full State]                                   │  │
│ │                                                       │  │
│ │ synthesis:                                            │  │
│ │   partial_answer: "Quantum computing is..."           │  │
│ │   confidence: 0.87                                    │  │
│ │   [View Full State]                                   │  │
│ │                                                       │  │
│ │ reflection:                                           │  │
│ │   issues: []                                          │  │
│ │   quality_score: 0.92                                 │  │
│ │   [View Full State]                                   │  │
│ │                                                       │  │
│ └───────────────────────────────────────────────────────┘  │
│                                                             │
│ ┌───────────────────────────────────────────────────────┐  │
│ │ Performance Metrics (Live)                            │  │
│ │ ───────────────────────────────────────────────────── │  │
│ │ Message Latency:        P50: 8ms, P95: 42ms           │  │
│ │ Message Throughput:     1,247 msg/hour                │  │
│ │ Orchestration Duration: 1,200ms (avg, last hour)     │  │
│ │ Blackboard Writes:      342 (last hour)               │  │
│ │ MessageBus Queue Depth: 2 (should be <10)            │  │
│ │                                                       │  │
│ └───────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 MessageBus Monitor

#### Message Types

| Type | Sender | Receiver | Meaning | Payload |
|------|--------|----------|---------|---------|
| **SKILL_REQUEST** | Manager | Worker | Invoke a skill | query, context_budget, parameters |
| **SKILL_RESPONSE** | Worker | Manager | Skill result | result, duration_ms, success/error |
| **PHASE_UPDATE** | Executive | All | Phase transition | phase_number, phase_name, status |
| **BLACKBOARD_UPDATE** | Any | All | Shared state changed | namespace, key, value |
| **ERROR** | Any | Sender's manager | Error occurred | error_type, message, recovery_suggestion |
| **RETRY** | Manager | Worker | Retry failed task | task_id, retry_count, modified_params |
| **TIMEOUT** | System | Worker's manager | Task exceeded time limit | task_id, timeout_ms, action_taken |

#### Reading Messages

Click **[View Details]** on any message:

```
┌─────────────────────────────────────────────────────────────┐
│ Message Details                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Timestamp:    2026-01-15 14:23:45.203                      │
│ Trace ID:     trace_req_7a2b3f9                            │
│ From:         ResearchManager (agent_id: mgr_001)         │
│ To:           W1 VectorSearch (agent_id: w1_vector)        │
│ Type:         SKILL_REQUEST                                │
│ Status:       ✅ Delivered                                  │
│ Latency:      8ms (send → receive)                         │
│                                                             │
│ Payload:                                                    │
│ {                                                           │
│   "skill": "retrieval",                                    │
│   "query": "What is quantum computing?",                  │
│   "context_budget": 2000,                                  │
│   "mode": "hybrid",                                        │
│   "top_k": 8                                               │
│ }                                                           │
│                                                             │
│ Response:     (waiting... or click [View Response])        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Filtering Messages

**Filter by:**
- Agent pair: "ResearchManager → VectorSearch"
- Message type: "SKILL_REQUEST", "ERROR", etc.
- Time range: Last 1h, 6h, 24h
- Status: "Success", "Error", "Timeout"

**Example filters:**
```
Show errors only:
Type: [ERROR ▼]  →  All error messages

Show slow messages (>100ms):
Latency: [> 100ms ▼]

Show retries:
Type: [RETRY ▼]
```

### 2.4 Blackboard State

The Blackboard is shared memory for agents to coordinate. Each namespace holds intermediate results.

#### Namespaces

| Namespace | Owner | Contents | Accessed By |
|-----------|-------|----------|-------------|
| `retrieval` | ResearchMgr | Documents retrieved | SynthesisMgr, ReflectionMgr |
| `synthesis` | SynthesisMgr | Generated answer | ExecutiveMgr, ReflectionMgr |
| `reflection` | ReflectionMgr | Quality scores, issues | ExecutiveMgr (decide next phase) |
| `execution_plan` | Executive | Current phase, tasks | All agents (read-only) |

#### Example: Viewing retrieval Namespace

Click **[Blackboard] > [retrieval]**:

```
┌─────────────────────────────────────────────────────────────┐
│ Blackboard: retrieval                                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ documents: [                                                │
│   {                                                         │
│     "id": "doc_7a3f",                                       │
│     "title": "Introduction to Quantum Computing",          │
│     "score": 0.94,                                         │
│     "content": "Quantum computing uses quantum mechanics..."│
│   },                                                        │
│   {                                                         │
│     "id": "doc_5d2c",                                       │
│     "title": "Quantum Error Correction Advances",          │
│     "score": 0.87,                                         │
│     "content": "Recent advances in topological qubits..."   │
│   },                                                        │
│   ... (8 total documents)                                   │
│ ]                                                           │
│                                                             │
│ metadata:                                                   │
│ {                                                           │
│   "total_tokens": 1847,                                     │
│   "token_budget": 2000,                                     │
│   "confidence": 0.89,                                       │
│   "retrieved_at": "2026-01-15T14:23:45Z",                 │
│   "retrieval_mode": "hybrid"                               │
│ }                                                           │
│                                                             │
│ Last updated: 2026-01-15 14:23:46.150                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Understanding Blackboard Size

**Token tracking:**
```
retrieval namespace uses:
  8 documents × ~230 tokens/doc = 1,847 tokens
  Token budget: 2,000 tokens
  Utilization: 92% (good, using available space)
```

**When to worry:**
- Utilization > 95% → May not fit new documents in synthesis phase
- Utilization = 100% → Subsequent retrieval will evict oldest docs

**How to fix:**
- Reduce `top_k` (fewer documents)
- Reduce `context_length` per document (summary instead of full)

---

## 3. Agent Hierarchy Visualizer

### 3.1 Overview

Interactive tree visualization of the agent hierarchy, showing which agents exist, their relationships, and current task allocation.

### 3.2 Accessing the Visualizer

Navigate to **Admin Dashboard > Agents > Hierarchy**.

```
┌─────────────────────────────────────────────────────────────┐
│ Agent Hierarchy Visualizer            [Reset Zoom] [Export] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────┐                   │
│  │   Hierarchy Tree (D3.js)   │Details  │                   │
│  │                            Panel    │                   │
│  │  ┌──────────────────────┐            │                   │
│  │  │   Executive Director │            │ Research Manager  │
│  │  │   (coordinator)      │            │ Level: MANAGER    │
│  │  │ [planner,orchestrat  │            │ Skills:           │
│  │  └──────────┬───────────┘            │ - retrieval       │
│  │             │                        │ - web_search      │
│  │  ┌──────────┼──────────┐             │ - fact_check      │
│  │  │          │          │             │                   │
│  │  ▼          ▼          ▼             │ Active Tasks: 2   │
│  │┌────────┐┌────────┐┌────────┐        │ ✅ Task #7a2b     │
│  ││Research││Analysis││Synth.  │        │ ✅ Task #9f4c     │
│  ││Manager ││Manager ││Manager │        │                   │
│  └┴────────┘┴────────┘┴────────┘        │ Performance:      │
│             │          │         │       │ ✅ Success: 87%   │
│         ┌───┴──┐   ┌───┴──┐  ┌──┴───┐   │ ✅ Latency: 450ms │
│         ▼  ▼   ▼   ▼  ▼   ▼  ▼  ▼  ▼   │ ✅ Tasks: 142    │
│        W1 W2   W3  W4 W5  W6 W7 W8  W9  │                   │
│                                         │ [View Logs]       │
│  [Zoom In] [Zoom Out] [Center]         │ [View Tasks]      │
│  [Filter by Level: All ▼]               │ [Manage]          │
│  [Filter by Status: All ▼]              │                   │
│                                         │                   │
│  ┌──────────────────────────────────┐   │                   │
│  │ Task Delegation Tracer           │   │                   │
│  │ Select Task: [research_7a2b  ▼] │   │                   │
│  │                                  │   │                   │
│  │ Delegation Chain:                │   │                   │
│  │ Executive → Research Manager → W1│   │                   │
│  │ [Highlight in Tree]              │   │                   │
│  │ [View Task Details]              │   │                   │
│  └──────────────────────────────────┘   │                   │
│                                         │                   │
└─────────────────────────────────────────┴──────────────────┘
```

### 3.3 Tree Navigation

**Click on agent node to:**
- View details (right panel)
- See current tasks
- Check performance metrics
- View recent logs

**Tree controls:**
- **[Zoom In/Out]** - Magnify specific branch
- **[Center]** - Reset view to root (Executive)
- **[Filter by Level]** - Show only Manager/Worker/All
- **[Filter by Status]** - Show only Active/Idle/Error

**Example: Zoom in on Research Manager and workers**

```
After [Zoom In]:

    ┌──────────────────┐
    │Research Manager  │
    │(mgr_001)         │
    │ Tasks: 3         │
    └────┬─────────────┘
         │
    ┌────┼────────┬──────┐
    ▼    ▼        ▼      ▼
  [W1]  [W2]    [W3]   [W4]
 Vector WebSrch Graph  Rank
 (idle) (busy)  (idle) (busy)
```

### 3.4 Understanding Agent Status

| Status | Icon | Meaning | Action |
|--------|------|---------|--------|
| **Active** | 🟢 | Processing task | Monitor progress |
| **Idle** | ⚪ | Waiting for work | Normal (may wake up) |
| **Busy** | 🔵 | In progress | Wait or increase workers |
| **Error** | 🔴 | Failed or stuck | Investigate logs |
| **Stale** | 🟠 | No heartbeat for >30s | May have crashed |

### 3.5 Task Delegation Tracer

**What it does:** Show how a specific task flows through the agent hierarchy.

**To trace a task:**

1. Click **[Task Delegation Tracer]**
2. Select task from dropdown
3. System highlights the path from Executive → Managers → Workers
4. Shows timing at each step

```
Example trace of query "What is quantum computing?":

14:23:45.100  User submits query
              ↓
14:23:45.150  Executive receives query
              └→ Intent: RESEARCH (confidence: 0.92)
              └→ Routes to: ResearchManager
              ↓
14:23:45.200  ResearchManager creates task #7a2b
              └→ Decomposes into:
                 - VectorSearch (W1): Retrieve documents
                 - WebSearch (W2):   Find current info
              ↓
14:23:45.203  Sends SKILL_REQUEST to W1 and W2
              ↓
14:23:45.524  W1 returns: 8 documents (321ms)
14:23:46.050  W2 returns: 3 web results (849ms)
              ↓
14:23:46.150  ResearchManager aggregates results
              └→ Confidence: 0.89
              ↓
14:23:46.200  Routes to SynthesisMgr for answer generation
              ↓
14:23:47.400  Final answer returned (2,250ms total)
```

### 3.6 Performance Metrics Per Agent

Click any agent node to see metrics:

```
┌─────────────────────────────────────────────────────────────┐
│ Agent Metrics: Research Manager (mgr_001)                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Current Status:                                             │
│ • State: Active (processing 2 tasks)                        │
│ • Uptime: 99.8% (last 24h)                                 │
│ • Last error: 2026-01-15 02:14 (connection timeout)         │
│                                                             │
│ Performance:                                                │
│ • Tasks completed: 142                                      │
│ • Success rate: 98.6% (2 failures)                          │
│ • Avg task duration: 1,120ms (p50), 2,340ms (p95)          │
│ • Parallelization: Average 2.3 workers active               │
│                                                             │
│ Worker Delegation:                                          │
│ • VectorSearch (W1): 98 tasks, 98.9% success               │
│ • WebSearch (W2):    45 tasks, 97.7% success               │
│ • GraphQuery (W3):   34 tasks, 100% success                │
│                                                             │
│ Errors (last 24h):                                          │
│ • Timeout (W2 web_search): 1 (rate-limited by API)         │
│ • Connection error (W1 Qdrant): 1 (brief network hiccup)   │
│ • Retry succeeded: 2/2                                      │
│                                                             │
│ Resource Usage:                                             │
│ • Memory: 234 MB                                            │
│ • CPU: 3-5% during active queries                           │
│ • Message queue: 0-2 pending (average 0.8)                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Troubleshooting

### 4.1 Agent Not Responding (Appears Stale)

**Symptom:** Agent shows 🟠 Stale status, no heartbeat for >30s

**Investigation:**

1. Click agent node, check recent logs
2. Look for error messages in last 30 seconds
3. Check if worker agents under this manager are also stale

**Common causes:**

| Cause | Evidence | Fix |
|-------|----------|-----|
| Crashed | No logs, no heartbeat | Restart agent service |
| Stuck in loop | Repeated error, high CPU | Kill process, investigate code |
| Deadlocked | Waiting on resource forever | Restart DB (Qdrant/Neo4j) |
| Network issue | Connection timeouts in logs | Check network connectivity |

**Resolution steps:**

```bash
# 1. Check if service is running
docker ps | grep aegis-agents

# 2. Check agent logs
docker logs aegis-agents | tail -100

# 3. Restart if needed
docker restart aegis-agents

# 4. Verify recovery in UI
# Agent should return to 🟢 Active status within 30 seconds
```

### 4.2 High Latency or Stuck Tasks

**Symptom:** P95 latency is 5,000ms (target: <500ms)

**Investigation:**

1. Open **Communication Dashboard**
2. Filter by message type "SKILL_REQUEST" and "SKILL_RESPONSE"
3. Identify which agent is slow
4. Check that agent's logs and metrics

**Example diagnosis:**

```
Slow requests all from: VectorSearch (W1)
Message: SKILL_REQUEST → W1 takes 2 seconds
        SKILL_RESPONSE ← W1 takes 3 seconds total

Root cause: Qdrant latency
Solution: Check Qdrant service health, or reduce top_k
```

**Quick fixes:**

| Bottleneck | Fix | Expected Improvement |
|-----------|-----|----------------------|
| VectorSearch slow | Reduce `top_k` 15→10 | 200-400ms latency savings |
| WebSearch timeout | Increase timeout or disable web search | Eliminate 1-2s timeouts |
| LLM slow | Use faster model or increase temperature | 300-800ms savings |
| Reranking slow | Disable reranking or reduce top_n | 200-500ms savings |
| Graph query slow | Reduce `max_hops` 2→1 | 100-300ms savings |

### 4.3 Agent Failures and Retries

**Symptom:** Error rate >5%, many RETRY messages

**Investigation:**

1. Filter MessageBus by type: "ERROR" and "RETRY"
2. Identify error patterns (same agent, same error?)
3. Check error details for root cause

**Common errors:**

| Error | Likely Cause | Fix |
|-------|--------------|-----|
| Qdrant timeout | Vector DB overloaded or slow network | Scale Qdrant resources, reduce top_k |
| Neo4j timeout | Graph DB connection pool exhausted | Increase pool size, reduce max_hops |
| Rate limit exceeded | API quota hit (web_search) | Increase rate limit, batch requests |
| Authentication failed | Token expired or wrong credentials | Renew token, check env vars |
| Out of memory | Model or processing too large | Reduce context size, use smaller model |

**Retry strategy:**

AegisRAG uses exponential backoff:
- Retry 1: Wait 100ms
- Retry 2: Wait 200ms
- Retry 3: Wait 400ms
- Retry 4: Wait 800ms
- Give up after 3 retries

**Most failures succeed on retry** (transient issues like network blips).

### 4.4 Unbalanced Task Distribution

**Symptom:** One worker is always busy, others are idle

```
VectorSearch (W1): 🔵 Busy, 95% CPU, queue depth: 10
WebSearch (W2):    ⚪ Idle, 1% CPU, queue depth: 0
GraphQuery (W3):   ⚪ Idle, 1% CPU, queue depth: 0
```

**Root cause:** W1 is slow, so tasks pile up

**Investigation:**

1. Check W1 latency - typically high?
2. Check if W1 tool (Qdrant) is slow
3. Check if W1 rate limit is being hit

**Fix options:**

| Option | Tradeoff | Recommendation |
|--------|----------|-----------------|
| **Scale W1 horizontally** (add more workers) | Higher memory cost | Best if Qdrant can handle more load |
| **Reduce top_k** | Less context, potentially lower quality | Try first (quick, no infra change) |
| **Optimize Qdrant** | May require downtime | Last resort |
| **Route fewer queries to W1** | May miss relevant docs | Change intent routing logic |

---

## 5. Performance Tuning

### 5.1 Agent-Level Tuning

**Parallelization:**
- By default, managers parallelize all workers
- Example: Research Manager runs VectorSearch + WebSearch + GraphQuery concurrently
- Risk: If all workers slow → total time is max(all workers), not sum

**Sequential vs Parallel:**
```
Sequential (one tool at a time):
  VectorSearch: 300ms
  WebSearch:    800ms
  GraphQuery:   200ms
  Total: 1,300ms (slow)

Parallel (all concurrent):
  Max latency: 800ms (WebSearch is slowest)
  Much faster!
```

**Configuration in skill config:**
```yaml
# Not user-configurable currently, but understand the concept
# Future: May expose "parallelization_degree" setting
```

### 5.2 Message Batching

**Current:** Each message is sent individually
**Future optimization:** Group related messages (e.g., multiple documents in one message)

**Watch for:**
- Message throughput: Should be <2,000 msg/hour for normal workloads
- If higher: Consider batching at application level

### 5.3 Blackboard Optimization

**Token budgets per namespace:**
```yaml
retrieval:
  token_budget: 2000     # Max tokens for documents
synthesis:
  token_budget: 1500     # Max tokens for context in synthesis
reflection:
  token_budget: 500      # Small budget for quality scoring
```

**Optimization:**
- Reduce budgets if not using all tokens
- Increase budgets if consistently hitting limits and missing documents

---

## 6. Best Practices

### 6.1 Monitoring Checklist

**Daily (5 minutes):**
- [ ] Check agent availability - all should be 🟢 Active
- [ ] Monitor error rate - should be <2%
- [ ] Check latency P95 - should be <500ms
- [ ] Review top errors - any patterns?

**Weekly (15 minutes):**
- [ ] Check agent success rates - should be >97% each
- [ ] Review slow tasks - any specific patterns?
- [ ] Check resource usage - memory/CPU reasonable?
- [ ] Verify no agents stuck in error state

**Monthly (1 hour):**
- [ ] Generate performance report
- [ ] Review scaling needs - need more workers?
- [ ] Audit configuration - any stale settings?
- [ ] Test failover - restart agent service, verify recovery

### 6.2 Debugging Workflows

**Workflow 1: High latency investigation**
```
1. Open Communication Dashboard
2. Identify slowest message pair (SKILL_REQUEST + SKILL_RESPONSE)
3. Filter by that worker agent
4. Check if all messages from that worker are slow, or just some?
   - All slow: Worker or its dependency is slow
   - Some slow: Intermittent issue (network, queuing)
5. Click on slow message, view details
6. Check that worker's logs
7. Apply fix based on root cause
```

**Workflow 2: Agent crashes**
```
1. Notice stale 🟠 agent in hierarchy view
2. Check MessageBus for ERROR messages from that agent
3. Check agent logs: `docker logs aegis-agents | grep agent_name`
4. Identify error type (connection, memory, etc.)
5. Fix root cause (restart DB, clear cache, etc.)
6. Restart agent: `docker restart aegis-agents`
7. Verify recovery: Agent returns to 🟢 Active
```

**Workflow 3: Task stuck**
```
1. See task not completing in Orchestrations view
2. Click task to see current phase
3. Trace task in "Task Delegation Tracer"
4. Find which agent is stuck
5. Check MessageBus for that agent's last message
6. If last message was SKILL_REQUEST with no SKILL_RESPONSE:
   → Worker is still processing (check its logs)
7. If SKILL_REQUEST but no response after >5 minutes:
   → Likely deadlocked, restart that worker
8. Approve task timeout/cancellation if recovery impossible
```

---

## See Also

- **[Skill Management Guide](SKILL_MANAGEMENT_GUIDE.md)** - Configure agent skills
- **[Governance & Compliance Guide](GOVERNANCE_COMPLIANCE_GUIDE.md)** - Audit agent decisions
- **[API Documentation - Admin](../api/ADMIN_API_REFERENCE.md)** - Agent monitoring endpoints
- **[ADR-049: Agentic Framework](../adr/ADR-049-agentic-framework-architecture.md)** - Architecture details
- **[LangGraph Documentation](https://langchain-ai.github.io/langgraph/)** - Official LangGraph docs

---

**Document:** AGENT_MONITORING_GUIDE.md
**Last Updated:** 2026-01-15 (Sprint 98 Plan)
**Status:** Planned - Ready for Sprint 98 Implementation
**Audience:** DevOps engineers, System administrators, ML engineers
**Maintainer:** Documentation Agent

---
