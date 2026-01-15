# Skill Management Guide

**Last Updated:** 2026-01-15 (Sprint 97 Plan)
**Status:** Planned - Sprint 97
**Audience:** System administrators, DevOps engineers
**Prerequisite Knowledge:** Anthropic Agent Skills, YAML configuration

---

## Overview

The Skill Management UI provides comprehensive visual control over AegisRAG's modular skill ecosystem. This guide covers:

- **Skill Registry Browser** - Discover and inspect all available skills
- **Skill Configuration Editor** - Modify YAML configs via UI without file access
- **Tool Authorization Manager** - Control skill-tool permissions and rate limits
- **Skill Lifecycle Dashboard** - Monitor activation, performance, and usage
- **SKILL.md Visual Editor** - Edit skill metadata and instructions

**Why This Matters:**
In AegisRAG's agentic architecture, skills are self-contained capability modules that can be dynamically discovered, configured, and composed. The UI eliminates manual file editing and provides real-time validation.

---

## 1. Skill Registry Browser

### 1.1 Overview

The Skill Registry Browser displays all available skills in a visual card grid. Use it to:

- **Search** for skills by name or description
- **Filter** by status (active/inactive) or type
- **Inspect** skill metadata (version, tools, triggers, dependencies)
- **Activate/Deactivate** skills with one click
- **Access** skill configuration and logs

### 1.2 Accessing the Registry

Navigate to **Admin Dashboard > Skills** in the AegisRAG UI.

```
┌─────────────────────────────────────────────────────────────┐
│ AegisRAG Admin > Skills                          [+ Add Skill]│
├─────────────────────────────────────────────────────────────┤
│ Search: [________________]  Filter: [All ▼]  Status: [Any ▼]│
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│ │ 🔍 retrieval │  │ 🤔 reflection │  │ 🌐 web_search│      │
│ │ v1.2.0       │  │ v1.0.0       │  │ v1.1.0       │       │
│ │ Vector & ...  │  │ Self-critique │  │ Web browsing │      │
│ │              │  │              │  │              │       │
│ │ Tools: 3     │  │ Tools: 1     │  │ Tools: 2     │       │
│ │ [🟢 Active]  │  │ [⚪ Inactive] │  │ [🟢 Active]  │       │
│ │ [Config]     │  │ [Config]     │  │ [Config]     │       │
│ └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                             │
│ Showing 6 of 12 skills                  [1] [2] [>]        │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 Card Elements Explained

| Element | Meaning | Action |
|---------|---------|--------|
| Emoji + Name | Skill identifier | Click to view full details |
| v1.2.0 | Semantic version | Indicates feature compatibility |
| Description | 2-line summary | What the skill does |
| Tools: N | Tool count | How many tools this skill can use |
| Triggers: N | Trigger count | How many activation keywords |
| 🟢 Active / ⚪ Inactive | Current status | Click to toggle (requires save) |
| [Config] | Configuration button | Opens editor (see Section 2) |
| [Logs] | Logs button | View activation history |

### 1.4 Search and Filter

**Search by name:**
```
Search: "retrieval"  →  Shows: retrieval, research, web_retrieval
```

**Filter by status:**
```
Status: [Active ▼]  →  Shows: 🟢 Active skills only
Status: [Inactive ▼]  →  Shows: ⚪ Inactive skills only
Status: [Any ▼]  →  Shows: All skills (default)
```

**Filter by type (custom tags, coming in Sprint 98):**
```
Filter: [Research ▼]  →  research, web_search, synthesis
Filter: [Utility ▼]  →  file_ops, logging, monitoring
```

### 1.5 Activating and Deactivating Skills

**To activate a skill:**

1. Click the skill card to view details
2. Click **[🟢 Activate]** button
3. System validates:
   - ✅ All dependencies are available (Qdrant, Neo4j, etc.)
   - ✅ YAML config is valid
   - ✅ Required tools are authorized
4. On success: Skill loads into memory, metrics collection starts
5. On failure: Error message explains the issue (see Section 7 Troubleshooting)

**To deactivate a skill:**

1. Click **[⚪ Deactivate]** on an active skill
2. System:
   - Stops accepting new invocations
   - Completes in-progress tasks (graceful shutdown)
   - Archives metrics for that session
3. Skill remains in registry but unavailable

> **💡 Tip:** Deactivate skills during maintenance (e.g., updating vector index) to prevent errors.

### 1.6 Viewing Skill Details

Click on any skill card or search result to expand full details:

```
┌─────────────────────────────────────────────────────────────┐
│ Skill: retrieval (v1.2.0) - Full Details                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Description:                                                │
│ Vector & graph retrieval skill with hybrid search support  │
│                                                             │
│ Author: AegisRAG Core                                       │
│ Status: [🟢 Active] [Config] [Logs]                         │
│                                                             │
│ Metrics:                                                    │
│ • Activation Count: 1,247                                   │
│ • Last Activated: 2026-01-15 14:23:45                       │
│ • Success Rate: 98.7%                                       │
│ • Avg Duration: 120ms                                       │
│                                                             │
│ Tools (3):                                                  │
│ • vector_search (status: ✅ authorized)                     │
│ • graph_query (status: ✅ authorized)                       │
│ • reranking (status: ✅ authorized)                         │
│                                                             │
│ Triggers (4):                                               │
│ • search                                                    │
│ • find                                                      │
│ • lookup                                                    │
│ • retrieve                                                  │
│                                                             │
│ Dependencies:                                               │
│ • qdrant (v1.11.0) ✅                                       │
│ • neo4j (v5.24) ✅                                          │
│ • embedding_service (v1.0.5) ✅                             │
│                                                             │
│ Permissions:                                                │
│ • Read vectors: ✅                                          │
│ • Query graph: ✅                                           │
│ • Access embeddings: ✅                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Skill Configuration Editor

### 2.1 Overview

Edit skill behavior without touching the filesystem. The editor provides:

- **YAML editor** with syntax highlighting and validation
- **Live preview** showing parsed configuration
- **Validation warnings** for common issues
- **Dependency checks** ensuring all dependencies are available
- **Save and reload** with automatic skill restart

### 2.2 Accessing the Editor

Click **[Config]** on any skill card to open the editor.

```
┌─────────────────────────────────────────────────────────────┐
│ Skill: retrieval > Configuration                 [Save][Reset]│
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌──────────────────────────┐  ┌──────────────────────────┐ │
│ │ config.yaml              │  │ Preview                  │ │
│ │                          │  │ ─────────────────────── │ │
│ │ embedding:               │  │ ✅ Valid YAML           │ │
│ │   model: bge-m3          │  │                          │ │
│ │   dimension: 1024        │  │ Settings:                │ │
│ │                          │  │ ──────────────────      │ │
│ │ search:                  │  │ • Embedding: bge-m3     │ │
│ │   top_k: 10              │  │ • Top-K: 10             │ │
│ │   modes:                 │  │ • Modes: vector, hybrid │ │
│ │     - vector             │  │ • RRF k: 60             │ │
│ │     - hybrid             │  │                          │ │
│ │                          │  │ Triggers:                │ │
│ │ neo4j:                   │  │ ──────────────────      │ │
│ │   max_hops: 2            │  │ • search                │ │
│ │                          │  │ • find                  │ │
│ └──────────────────────────┘  │ • lookup                │ │
│                               │ • retrieve              │ │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ Validation                                           │ │
│ │ ─────────────────────────────────────────────────── │ │
│ │ ✅ YAML syntax valid                                 │ │
│ │ ✅ Required fields present: embedding.model, ...    │ │
│ │ ✅ Dependencies available: qdrant, neo4j             │ │
│ │ ⚠️  Warning: top_k > 20 may impact latency           │ │
│ └──────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 Common Configuration Patterns

#### Pattern 1: Adjust Top-K for Recall vs Latency

```yaml
search:
  top_k: 5      # Latency-optimized (100ms)
  # OR
  top_k: 15     # Recall-optimized (350ms)
```

> **Trade-off:** Higher top_k retrieves more context (better recall) but slows queries.
> Recommendation: Start with 10, increase if answers are incomplete.

#### Pattern 2: Enable/Disable Hybrid Search

```yaml
search:
  modes:
    - vector       # Dense vectors (fast, semantic)
    - hybrid       # Vector + sparse (slower, better keyword match)

  # To disable hybrid (vector-only):
  modes:
    - vector
```

> **When to use each:**
> - **Vector-only:** Fast queries, semantic understanding required
> - **Hybrid:** Keyword precision + semantic understanding (recommended)

#### Pattern 3: Configure Reranking

```yaml
reranking:
  enabled: true
  model: cross-encoder/ms-marco-MiniLM-L-12-v2
  top_n: 5      # Rerank top-5 results from retrieval
```

> **Recommendation:** Enable reranking for complex queries, disable for speed-critical paths.

#### Pattern 4: Neo4j Graph Depth

```yaml
neo4j:
  max_hops: 2           # Follow relationships up to 2 levels
  entity_limit: 50      # Return max 50 entities per query
```

> **Understanding hops:**
> - 1 hop: Direct relationships (fastest)
> - 2 hops: Friend-of-friend relationships (balanced)
> - 3+ hops: Deep connections (slow, many false positives)

### 2.4 Validation Rules

The editor automatically validates your configuration:

| Issue | Validation | Fix |
|-------|-----------|-----|
| Invalid YAML syntax | ❌ YAML syntax invalid | Check brackets, colons, indentation |
| Missing required fields | ❌ embedding.model required | Add all required top-level sections |
| Invalid model reference | ❌ Model not available | Verify model name in embeddings service |
| Dependency unavailable | ❌ Qdrant unavailable | Start Qdrant service, or remove from config |
| Performance warning | ⚠️ top_k > 20 may be slow | Reduce top_k or increase timeout |

### 2.5 Saving Configuration

1. **Click [Save]** at top right
2. System validates configuration
3. On success:
   - Configuration written to disk
   - Skill reloaded (brief interruption)
   - Metrics reset for this session
   - Message: "✅ Configuration saved and skill reloaded"
4. On failure:
   - Error displayed with fix suggestion
   - No changes written
   - Skill continues using old config

### 2.6 Resetting Configuration

Click **[Reset]** to revert to the skill's default configuration:

1. Click **[Reset]**
2. Confirmation dialog: "Revert to default configuration?"
3. On confirm:
   - All your changes discarded
   - Default config restored
   - Skill reloaded
4. On cancel:
   - No changes made

> **⚠️ Important:** Reset discards all unsaved changes. Save first if you might want to revert!

---

## 3. Tool Authorization Manager

### 3.1 Overview

Control which tools each skill can access. This prevents unauthorized tool use and enforces security policies.

**Example scenario:**
- `research` skill can use: web_search, browser, python_exec
- `assistant` skill can use: web_search, file_read (no python_exec - security constraint)

### 3.2 Accessing the Manager

Click **[Config] > [Tool Authorization]** on any skill card.

```
┌─────────────────────────────────────────────────────────────┐
│ Skill: automation > Tool Authorization               [Save]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Authorized Tools                                            │
│ ─────────────────────────────────────────────────────────── │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Tool          │ Access    │ Rate Limit │ Domains │ Actions│
│ ├──────────────┼───────────┼────────────┼────────┼────────┤ │
│ │ 🌐 browser    │ Standard▼ │ 30/min    │ [Edit] │ [🗑️]   │ │
│ │ 🐍 python_ex │ Elevated▼ │ 10/min    │ N/A    │ [🗑️]   │ │
│ │ 📁 file_write │ Elevated▼ │ 20/min    │ N/A    │ [🗑️]   │ │
│ │ 🔍 web_search │ Standard▼ │ 60/min    │ [Edit] │ [🗑️]   │ │
│ │ 📝 llm_sum... │ Standard▼ │ ∞         │ N/A    │ [🗑️]   │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ [+ Add Tool]                                                │
│                                                             │
│ ─────────────────────────────────────────────────────────── │
│                                                             │
│ Domain Restrictions (browser, web_search)                   │
│                                                             │
│ Allowed Domains:          │ Blocked Domains:               │
│ ┌────────────────────┐    │ ┌─────────────────────┐         │
│ │ *.wikipedia.org    │    │ │ *.malware.com       │         │
│ │ *.github.com       │    │ │ *.phishing.net      │         │
│ │ *.arxiv.org        │    │ │                     │         │
│ │ [+ Add domain]     │    │ │ [+ Add domain]      │         │
│ └────────────────────┘    │ └─────────────────────┘         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Access Levels

| Level | Definition | Use Case |
|-------|-----------|----------|
| **Standard** | Tool runs with current user permissions | Safe for web_search, browser, file_read |
| **Elevated** | Tool runs with elevated privileges (if applicable) | file_write, python_exec, system commands |
| **Admin** | Tool runs with admin access | System reboot, network config changes |
| **Sandbox** | Tool runs in restricted environment | Untrusted code execution |

> **🔒 Security Tip:** Only assign Elevated/Admin to trusted skills. Prefer Sandbox for experimental skills.

### 3.4 Rate Limiting

Set per-tool rate limits to prevent resource exhaustion:

```yaml
# Configuration structure
tools:
  web_search:
    rate_limit: 60/min        # 60 requests per minute
  python_exec:
    rate_limit: 10/min        # 10 requests per minute
  file_write:
    rate_limit: 20/min        # 20 requests per minute
  llm_summarize:
    rate_limit: unlimited     # ∞ (use cautiously)
```

**To adjust rate limits:**

1. Click on the rate limit cell (e.g., "60/min")
2. Enter new value: `45/min`, `100/hour`, etc.
3. Click [Save] to apply

**Recommended defaults:**

| Tool | Recommended Limit | Rationale |
|------|-------------------|-----------|
| web_search | 60/min | API quotas |
| browser | 30/min | High resource usage |
| python_exec | 10/min | Security (prevent code bombs) |
| file_write | 20/min | Prevent disk fill-up |
| vector_search | 100/min | Fast, can handle high volume |
| llm_summarize | unlimited | Internally rate-limited |

### 3.5 Domain Restrictions (Network Tools)

For network-capable tools (browser, web_search), define allowed/blocked domains:

**Allowed domains (whitelist):**
```
*.wikipedia.org          # Allow all Wikipedia subdomain
*.github.com             # Allow code repository
*.arxiv.org              # Allow research papers
```

**Blocked domains (blacklist):**
```
*.malware.com            # Explicitly blocked
*.phishing.net           # Explicitly blocked
```

**Rules:**
- Whitelist takes priority (if domain is in both, it's allowed)
- Wildcards supported: `*.example.com` matches `api.example.com`, `docs.example.com`
- Empty whitelist = allow all (except blacklist)
- Empty blacklist = no restrictions

### 3.6 Adding and Removing Tools

**To add a tool:**

1. Click **[+ Add Tool]** button
2. Select tool from dropdown (shows unauthorized tools only)
3. Choose access level: Standard, Elevated, Admin, Sandbox
4. Set rate limit (default: 60/min)
5. Click **[Save]**

**To remove a tool:**

1. Click **[🗑️]** button next to tool
2. Confirmation: "Remove tool_name from skill?"
3. Click **[Confirm]** to proceed

> **⚠️ Warning:** Removing a tool that the skill uses will cause errors. Verify dependencies before removing.

---

## 4. Skill Lifecycle Dashboard

### 4.1 Overview

Monitor skill health, performance, and usage in real-time.

```
┌─────────────────────────────────────────────────────────────┐
│ Skill Lifecycle Dashboard          Last updated: 12:34:56   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌──────────────┐  ┌──────────────┐  ┌────────────────┐    │
│ │ Active Skills │  │ Tool Calls   │  │ Policy Alerts  │    │
│ │      4/12    │  │   (24h)      │  │       3        │    │
│ │ ███████░░░░░ │  │   1,247      │  │ ⚠️  2 warnings  │    │
│ │     33%      │  │ +12% vs prev  │  │ 🔴 1 critical  │    │
│ └──────────────┘  └──────────────┘  └────────────────┘    │
│                                                             │
│ Skill Activation Timeline (Last 24 Hours)                   │
│ ─────────────────────────────────────────────────────────── │
│ retrieval   ████████████████████████████████████████████   │
│ reflection  ░░░░████░░░░████░░░░████░░░░████░░░░████░░░░   │
│ web_search  ░░░░░░░░████████░░░░░░░░░░░░░░░░████████░░░░   │
│ synthesis   ░░░░░░░░░░░░████████████░░░░░░░░████████████   │
│             ────────────────────────────────────────────    │
│             00:00    06:00    12:00    18:00    24:00       │
│                                                             │
│ Top Tool Usage (24h)          Recent Alerts                 │
│ ─────────────────────         ─────────────────────────────│
│ 1. vector_search   412        ⚠️ rate_limit: web_search    │
│ 2. llm_generate    389           (14:23) 60 req/min exceeded│
│ 3. browser         156        ⚠️ rate_limit: browser (13:45)│
│ 4. graph_query     134        🔴 blocked_pattern:           │
│ 5. python_exec      89           python_exec (12:01)       │
│                                "rm -rf" command detected    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Understanding the Metrics

| Metric | Meaning | Healthy Range |
|--------|---------|---------------|
| Active Skills | Number of enabled skills | Depends on workload (3-20 typical) |
| Tool Calls (24h) | Total tool invocations | >100 (indicates active usage) |
| Policy Alerts | Security/rate limit violations | 0-5 per day (investigate if >10) |
| Activation Timeline | When skills were used | Balanced usage across hours |

### 4.3 Skill Performance Metrics

Click on any skill to see detailed metrics:

```
┌─────────────────────────────────────────────────────────────┐
│ Skill Metrics: retrieval                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Availability:                                               │
│ • Uptime: 99.8% (last 24h)                                 │
│ • Last error: 2026-01-15 02:14 (connection timeout)         │
│ • Mean time to recovery: 47 seconds                         │
│                                                             │
│ Performance:                                                │
│ • Avg execution time: 125ms (p50), 340ms (p95)             │
│ • Success rate: 98.7% (123 failures of 9,847 calls)         │
│ • Tool cache hit rate: 65% (reduces latency by 250ms)       │
│                                                             │
│ Resource Usage:                                             │
│ • Memory: 234 MB                                            │
│ • CPU: 3-5% during active queries                           │
│ • Network bandwidth: 42 MB/day                              │
│                                                             │
│ Top Failure Reasons:                                        │
│ • 1. Qdrant timeout (41 occurrences)                        │
│ • 2. Invalid query syntax (34 occurrences)                  │
│ • 3. Neo4j connection pool exhausted (29 occurrences)       │
│                                                             │
│ [Export Metrics] [View Logs] [Reset Stats]                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.4 Responding to Alerts

**Alert: Rate Limit Exceeded**

```
⚠️ web_search exceeded rate limit at 14:23
   Threshold: 60 req/min
   Actual: 67 req/min

Action: Temporarily queued 7 requests
Next: Monitor next hour for sustained violations
```

**Response:**
- If occasional: No action needed (temporary spike)
- If frequent: Increase rate limit OR reduce query frequency
- If sustained: Contact user to reduce load

**Alert: Blocked Pattern Detected**

```
🔴 python_exec blocked dangerous pattern at 12:01
   Pattern: "rm -rf" (file deletion)
   Context: Skill tried to execute system command
   Result: Command blocked, error returned to user

Action: Investigation required
```

**Response:**
1. Review skill logs: Who invoked this skill?
2. Determine intent: Legitimate use or attack?
3. If legitimate: Whitelist pattern (dangerous but needed)
4. If suspicious: Revoke skill access, investigate user

---

## 5. SKILL.md Visual Editor

### 5.1 Overview

Edit skill metadata (name, version, author, triggers, etc.) and instructions using a visual editor. No YAML knowledge needed.

### 5.2 Accessing the Editor

Click **[Edit SKILL.md]** on any skill card.

```
┌─────────────────────────────────────────────────────────────┐
│ SKILL.md Editor: retrieval                      [Save][Reset]│
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌─────────────────────────┐  ┌─────────────────────────────┐
│ │ Metadata Form           │  │ Markdown Editor             │
│ │                         │  │ ─────────────────────────── │
│ │ Name:                   │  │                             │
│ │ [retrieval          ] │  │ # Retrieval Skill           │
│ │                         │  │                             │
│ │ Version:                │  │ Vector & graph retrieval    │
│ │ [1.2.0              ] │  │ with hybrid search support  │
│ │                         │  │                             │
│ │ Author:                 │  │ ## Features                 │
│ │ [AegisRAG Core      ] │  │ - Dense vector search       │
│ │                         │  │ - Sparse lexical search     │
│ │ Description:            │  │ - Graph entity retrieval    │
│ │ [Vector & graph     ] │  │                             │
│ │ [retrieval with...  ] │  │ [Preview]                   │
│ │                         │  │                             │
│ │ Triggers:               │  └─────────────────────────────┘
│ │ [search] [find]         │
│ │ [lookup] [retrieve]     │
│ │ [+ Add trigger]         │
│ │                         │
│ │ Dependencies:           │
│ │ [qdrant] [neo4j]        │
│ │ [+ Add dependency]      │
│ │                         │
│ │ Permissions:            │
│ │ [read_vectors]          │
│ │ [query_graph]           │
│ │ [+ Add permission]      │
│ │                         │
│ └─────────────────────────┘
│                                                             │
│ [Save All] [Reset]                                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 Frontmatter Structure

The metadata section (left side) corresponds to SKILL.md frontmatter:

```yaml
---
name: retrieval
version: 1.2.0
author: AegisRAG Core
description: Vector & graph retrieval with hybrid search support
triggers:
  - search
  - find
  - lookup
  - retrieve
dependencies:
  - qdrant
  - neo4j
  - embedding_service
permissions:
  - read_vectors
  - query_graph
  - access_embeddings
---
```

**Fields:**

| Field | Required | Type | Example |
|-------|----------|------|---------|
| name | Yes | string | "retrieval" |
| version | Yes | string (semver) | "1.2.0" |
| author | No | string | "AegisRAG Core" |
| description | No | string | "Vector search skill..." |
| triggers | Yes | list | ["search", "find"] |
| dependencies | Yes | list | ["qdrant", "neo4j"] |
| permissions | Yes | list | ["read_vectors"] |

### 5.4 Editing Triggers

**Add trigger:**
1. Click **[+ Add trigger]**
2. Type trigger keyword (e.g., "analyze")
3. Press Enter or click [✓]

**Remove trigger:**
- Click **[✕]** next to trigger name

**Example triggers:**
```
search, find, lookup, retrieve    # Retrieval skill
analyze, evaluate, assess          # Analysis skill
web_search, browse, scout          # Web skill
summarize, synthesis, generate     # Generation skill
```

### 5.5 Editing Instructions (Markdown)

The right side is a markdown editor for the skill's instructions.

**Supported markdown:**
```markdown
# Heading 1
## Heading 2
### Heading 3

**Bold text**
*Italic text*
- Bullet list
- Another item

1. Numbered list
2. Another item

[Link text](https://example.com)

```code block```
```

**Tips:**
- **Use clear headings** - "## Features", "## Usage", "## Limitations"
- **Include examples** - Show how to use the skill
- **Document limitations** - What can't this skill do?
- **Note dependencies** - What services/models does it require?

**Example SKILL.md:**
```markdown
# Retrieval Skill

Vector and graph-based document retrieval with hybrid search support.

## Features

- **Dense vector search** - Semantic similarity using BGE-M3
- **Sparse lexical search** - Keyword matching for precision
- **Graph entity search** - Find documents by mentioned entities
- **Hybrid fusion** - Reciprocal Rank Fusion (RRF) of vector + lexical results

## Usage

Invoke with triggers: search, find, lookup, retrieve

Example:
"What are the latest quantum computing trends?"
→ Triggers: search (retrieval skill selected)
→ Returns: 10 most relevant documents

## Configuration

See config.yaml for tuning:
- `top_k` - Number of results (default: 10)
- `modes` - Search modes (vector, hybrid, graph)
- `reranking.enabled` - Use cross-encoder reranker

## Performance

- P50 latency: 120ms (Qdrant vector search)
- P95 latency: 340ms (including Neo4j graph search)
- Success rate: 98.7%

## Limitations

- Maximum query length: 1000 characters
- Graph search limited to 2-hop relationships
- Reranking only available for vector results
```

### 5.6 Saving SKILL.md

1. **Click [Save All]**
2. System validates:
   - ✅ All required fields present
   - ✅ Version is valid semver (e.g., "1.2.0")
   - ✅ Triggers is non-empty
3. On success:
   - Metadata and instructions saved
   - Skill reloaded
   - Message: "✅ SKILL.md saved successfully"
4. On failure:
   - Error message explains issue
   - No changes saved

---

## 6. Best Practices

### 6.1 Configuration Management

**Principle: Versioning and Backups**

Before making significant config changes:

1. Take screenshot of current config
2. Export config to JSON for backup
3. Make changes incrementally (one setting at a time)
4. Test after each change
5. If issues arise: Click [Reset] to revert to default

**Recommended workflow:**

```
1. Document current config (screenshot)
2. Change: embedding model from bge-m3 to bge-m3-zh
3. Save and test with 5 queries
4. If working: Document the change
5. If broken: Click [Reset], debug, retry
```

### 6.2 Tool Authorization Best Practices

**Security principle: Least privilege**

Only grant tools that skill truly needs:

```yaml
# ❌ Bad: skill has access to all tools
tools: [web_search, python_exec, file_write, shell_exec, ...]

# ✅ Good: skill has only required tools
tools: [web_search, browser]  # Just what it needs
```

**Per-skill authorization checklist:**

- [ ] Does this skill need `python_exec`? (high risk)
- [ ] Does this skill need `shell_exec`? (very high risk)
- [ ] Does this skill need `file_write`? (data loss risk)
- [ ] Can I reduce `top_k` rate limit without hurting quality?
- [ ] Should I add domain restrictions (whitelist allowed domains)?

### 6.3 Rate Limiting Strategy

**Start conservative, increase if needed:**

```
Day 1: 10/min (conservative)
↓ Monitor for "rate limit exceeded" errors
Day 2: 30/min (if no errors)
↓ Monitor performance, user feedback
Day 3: 60/min (if satisfied)
```

**Signs you need to increase rate limit:**

- Frequent "rate_limit_exceeded" errors
- User complaints about speed
- Skill is under-utilized (tool calls << configured rate)

**Signs you should decrease rate limit:**

- High CPU/memory usage
- Database connection pool exhaustion
- Other skills starved for resources

### 6.4 Monitoring Performance

**Daily checklist:**

1. **Check skill availability:** Active skills should be > 0
2. **Monitor error rate:** Should stay < 2%
3. **Review alerts:** Respond to rate limit or security alerts
4. **Check resource usage:** Memory, CPU should be reasonable
5. **Scan logs:** Any unusual patterns or errors?

**Weekly audit:**

1. Review top tool usage (is distribution expected?)
2. Check for unused skills (consider deactivating)
3. Verify rate limits are appropriate
4. Check for policy violations (blocked patterns)

---

## 7. Troubleshooting

### 7.1 Activation Fails with "Dependency Not Available"

**Error:**
```
❌ Activation failed: Qdrant service not available
```

**Causes:**
1. Qdrant service is down
2. Network connectivity issue
3. Qdrant hostname/port incorrect in .env

**Solutions:**

Step 1: Check service status
```bash
# SSH to server
ssh admin@aegis-server

# Check if Qdrant is running
docker ps | grep qdrant

# Expected output: qdrant container in RUNNING state
```

Step 2: If Qdrant not running, start it
```bash
docker compose -f docker-compose.yml up -d qdrant
```

Step 3: Verify connectivity
```bash
# Check if Qdrant is responding on port 6333
curl http://localhost:6333/health

# Expected: HTTP 200 with health status
```

Step 4: Retry skill activation in UI

### 7.2 Configuration Save Fails

**Error:**
```
❌ Validation failed: embedding.model is required
```

**Solution:** The YAML is missing a required field.

Check your config has these top-level sections:

```yaml
embedding:          # ← Required
  model: bge-m3
  dimension: 1024

search:             # ← Required
  top_k: 10
  modes:
    - vector
```

### 7.3 Rate Limit Violations Keep Happening

**Symptom:**
```
⚠️ web_search exceeded rate limit
   Exceeded threshold: 60 req/min
   Occurred at: 14:23, 14:28, 14:33, ... (every 5 min)
```

**Root cause:** Actual usage is above configured limit.

**Solutions:**

Option 1: Increase rate limit
- Click on "60/min" in tool authorization table
- Change to "90/min" or "120/min"
- Click [Save]

Option 2: Reduce skill usage
- Advise users to batch queries
- Use result caching for repeated queries
- Distribute load across time

Option 3: Check for stuck processes
- Click [View Logs]
- Look for skill stuck in infinite loop
- Deactivate skill, investigate

### 7.4 Skill Performs Poorly (Slow Queries)

**Symptom:** P95 latency is 800ms, target is 500ms

**Diagnosis steps:**

1. Open Skill Lifecycle Dashboard
2. Find performance metrics
3. Identify bottleneck:
   - Is it retrieval (high P95 for tool calls)?
   - Is it generation (LLM latency)?
   - Is it overhead (other)?

**Solutions by bottleneck:**

| Bottleneck | Solution |
|-----------|----------|
| Retrieval (Qdrant timeout) | Reduce `top_k` from 15 to 10, or increase Qdrant resources |
| Reranking (cross-encoder slow) | Disable reranking, or reduce reranking top_n |
| Graph search (Neo4j timeout) | Reduce `max_hops` from 2 to 1 |
| LLM generation (slow model) | Use faster model, or increase temperature (less thinking) |

**Example config optimization:**
```yaml
# Before (slow)
search:
  top_k: 15           # Too many results to rerank
  modes: [vector, hybrid]
reranking:
  enabled: true
  top_n: 15           # Reranking 15 results is slow

# After (fast)
search:
  top_k: 10           # Smaller result set
  modes: [vector]     # Skip hybrid (save 50ms)
reranking:
  enabled: true
  top_n: 5            # Only rerank top-5 (10x faster)
```

### 7.5 Authorization Manager Shows "No tools available"

**Symptom:** When adding tools, dropdown is empty or only shows 1 tool.

**Possible issues:**
1. Tool system hasn't initialized yet (wait 10 seconds, refresh)
2. All tools are already authorized (try deactivating skill, see available tools)
3. Tools not registered in system

**Check tool registration:**

Navigate to **Admin > System Health > Tool Registry**. You should see 5-20 registered tools.

If no tools shown:
1. Restart backend: `docker restart aegis-api`
2. Check logs: `docker logs aegis-api | grep "Tool registration"`
3. Verify tool definitions are in source code

---

## See Also

- **[Governance & Compliance Guide](GOVERNANCE_COMPLIANCE_GUIDE.md)** - GDPR and audit trail management
- **[Agent Monitoring Guide](AGENT_MONITORING_GUIDE.md)** - Monitor multi-agent coordination
- **[API Documentation - Admin Skills](../api/ADMIN_API_REFERENCE.md)** - REST API for skill management
- **[Architecture: Agent Skills (ADR-049)](../adr/ADR-049-agentic-framework-architecture.md)** - Design decisions
- **[Configuration Reference](../reference/CONFIG_REFERENCE.md)** - All available config options

---

**Document:** SKILL_MANAGEMENT_GUIDE.md
**Last Updated:** 2026-01-15 (Sprint 97 Plan)
**Status:** Planned - Ready for Sprint 97 Implementation
**Audience:** System administrators, DevOps engineers, Operations teams
**Maintainer:** Documentation Agent

---
