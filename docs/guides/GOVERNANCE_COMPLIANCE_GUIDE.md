# Governance & Compliance Guide

**Last Updated:** 2026-01-15 (Sprint 98 Plan)
**Status:** Planned - Sprint 98
**Audience:** Compliance officers, System administrators, Legal teams, Data protection officers (DPOs)
**Legal Basis:** GDPR (EU 2016/679), EU AI Act (2024/1689), Data protection regulations

---

## Overview

The Governance & Compliance UI implements EU legal requirements for data protection and AI transparency. This guide covers:

- **GDPR Compliance** - Consent management, data subject rights (Art. 15-22)
- **Audit Trail** - Immutable event logging with integrity verification (AI Act Art. 12)
- **Explainability Dashboard** - Decision transparency and source attribution (AI Act Art. 13)
- **Skill Certification** - 3-tier validation framework for trustworthiness

**Why This Matters:**
Organizations operating in the EU must comply with GDPR and the AI Act. Non-compliance risks fines up to 4% of global revenue (GDPR) and loss of AI deployment permits. This UI automates compliance workflows.

---

## 1. GDPR Consent Management

### 1.1 Overview

**GDPR Article 6** - Legal basis requirements:
Your organization must document the legal basis for processing each user's data. Six bases exist; most systems use Consent (Art. 6(1)(a)) or Contract (Art. 6(1)(b)).

**GDPR Article 7** - Consent management:
Users have the right to withdraw consent at any time.

**This section helps you:**
- Record consent with legal basis
- Track what data categories are authorized
- Manage consent withdrawal
- Apply skill restrictions (only use certain skills for consented data)
- Handle data subject rights requests (erasure, rectification, portability)

### 1.2 Accessing GDPR Consent Manager

Navigate to **Admin Dashboard > Governance > GDPR Consent**.

```
┌─────────────────────────────────────────────────────────────┐
│ GDPR Consent Management                           [+ Add]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Tabs: [Consents] [Data Subject Rights] [Processing Activities]
│                                                             │
│ ┌───────────────────────────────────────────────────────┐  │
│ │ Active Consents (3 of 47)                             │  │
│ │ ───────────────────────────────────────────────────── │  │
│ │                                                       │  │
│ │ ✅ user_123 - Customer Support                        │  │
│ │    Legal Basis: Contract (Art. 6(1)(b))              │  │
│ │    Data Categories: [identifier, contact]            │  │
│ │    Granted: 2025-12-01 | Expires: 2026-12-01         │  │
│ │    Skill Restrictions: [customer_support]            │  │
│ │    [Revoke] [Edit] [View Details]                    │  │
│ │                                                       │  │
│ │ ✅ user_456 - Marketing Communications               │  │
│ │    Legal Basis: Consent (Art. 6(1)(a))               │  │
│ │    Data Categories: [contact, behavioral]            │  │
│ │    Granted: 2026-01-10 | Expires: Never              │  │
│ │    Skill Restrictions: None                          │  │
│ │    [Revoke] [Edit] [View Details]                    │  │
│ │                                                       │  │
│ │ ⚠️ user_789 - Research Participation                 │  │
│ │    Legal Basis: Consent (Art. 6(1)(a))               │  │
│ │    Data Categories: [identifier, health, behavioral] │  │
│ │    Granted: 2025-06-15 | Expires: 2026-06-15 (soon!) │  │
│ │    Skill Restrictions: [research, analysis]          │  │
│ │    [Renew] [Revoke] [View Details]                   │  │
│ │                                                       │  │
│ └───────────────────────────────────────────────────────┘  │
│                                                             │
│ [1] [2] [3] [4] [>]                                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 Creating Consent Records

Click **[+ Add Consent]** to create a new consent record.

```
┌─────────────────────────────────────────────────────────────┐
│ Create Consent Record                                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ User Information                                            │
│ ─────────────────                                           │
│ User ID/Email: [user@example.com______________________]    │
│ User Name: [John Doe________________________]               │
│                                                             │
│ Legal Basis (required)                                      │
│ ──────────────────────                                      │
│ Select one:                                                 │
│ ◉ Consent (Art. 6(1)(a))                                    │
│ ○ Contract (Art. 6(1)(b))                                   │
│ ○ Legal Obligation (Art. 6(1)(c))                           │
│ ○ Vital Interests (Art. 6(1)(d))                            │
│ ○ Public Task (Art. 6(1)(e))                                │
│ ○ Legitimate Interests (Art. 6(1)(f))                       │
│                                                             │
│ Data Categories (required)                                  │
│ ─────────────────────────                                   │
│ ☑ identifier (names, IDs, passport)                        │
│ ☑ contact (email, phone, address)                          │
│ ☐ behavioral (search history, preferences)                 │
│ ☐ health (medical records, fitness data)                   │
│ ☐ biometric (fingerprints, face data)                      │
│ ☐ financial (bank accounts, transactions)                  │
│ ☐ device (IP address, user agent, cookies)                 │
│ [Other: ___________________]                               │
│                                                             │
│ Validity Period                                             │
│ ────────────────                                            │
│ Start Date: [2026-01-15___________]                         │
│ ○ No expiration                                             │
│ ○ Expires on: [2026-07-15_____________]  (6-month review)  │
│ ○ Expires on: [2027-01-15_____________]  (1-year review)   │
│                                                             │
│ Skill Restrictions (optional)                              │
│ ──────────────────────────────                              │
│ Leave empty = skill can use this data                      │
│ [+ Add restriction] [research] [analysis] [X]              │
│                                                             │
│ Notes (optional)                                            │
│ ────────────────                                            │
│ [Consent given via opt-in form on mobile app]             │
│                                                             │
│ [Create] [Cancel]                                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Field explanations:**

| Field | Meaning | Example |
|-------|---------|---------|
| User ID | Who this consent applies to | user_123, john@example.com |
| Legal Basis | Why we can process this data | Consent, Contract, Legitimate Interest |
| Data Categories | What types of data | identifier, contact, health, financial |
| Validity Period | How long consent is valid | Start: Jan 15, Expires: Jul 15 |
| Skill Restrictions | Which skills can't access this data | research, analysis (deny list) |

**Legal basis guidance:**

| Basis | Used When | Example |
|-------|-----------|---------|
| **Consent** | User explicitly agrees | "Sign up for newsletter" |
| **Contract** | Data needed to fulfill service | Customer payment info (required) |
| **Legal Obligation** | Law requires processing | Tax records, fraud detection |
| **Vital Interests** | Life or death situation | Emergency medical data |
| **Public Task** | Government function | Public health surveillance |
| **Legitimate Interests** | Organization's interests (documented) | Fraud prevention, security |

> **🔒 Important:** Choose the most specific basis. "Consent" requires explicit opt-in. "Contract" requires the data for service delivery. "Legitimate Interests" requires documented balancing test.

### 1.4 Managing Consent Lifecycle

**Withdraw consent (Art. 7):**

1. Click **[Revoke]** on consent record
2. Confirmation: "Withdraw all consent from user_123?"
3. On confirm:
   - Consent marked as withdrawn
   - All skills lose access to this user's data
   - Audit log records withdrawal
   - User notified (if configured)

**Renew expiring consent:**

1. Click **[Renew]** on expiring consent record
2. Extend expiration date
3. Optional: Update data categories if no longer needed
4. Click [Save]

**Edit consent (change data categories or restrictions):**

1. Click **[Edit]** on consent record
2. Modify data categories (e.g., add "health" if newly authorized)
3. Modify skill restrictions
4. Click [Save]

### 1.5 Data Subject Rights (GDPR Articles 15-22)

#### Right to Access (Art. 15)

**User request:** "Give me all data you have about me"

**System response:**
1. User submits request via UI
2. System generates export (JSON/CSV):
   ```json
   {
     "user_id": "user_123",
     "identifier": {
       "name": "John Doe",
       "email": "john@example.com"
     },
     "processing_records": [
       {
         "date": "2026-01-15",
         "skill": "retrieval",
         "query": "What is quantum computing?",
         "result": "[3 documents retrieved]"
       }
     ]
   }
   ```
3. User downloads export (encrypted link, 30-day expiration)

**Implementation in UI:**

Click **[Data Subject Rights] > [Access Request]**:

```
┌─────────────────────────────────────────────────────────────┐
│ Right to Access (GDPR Art. 15)                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ User: [user_123_____________________]                       │
│                                                             │
│ Include in export:                                          │
│ ☑ Personal data (name, email, phone, address)              │
│ ☑ Processing history (queries, results)                    │
│ ☑ Device information (IP, user agent)                      │
│ ☑ Skill invocations (which skills ran)                     │
│                                                             │
│ Export format:                                              │
│ ◉ JSON (structured, machine-readable)                      │
│ ○ CSV (spreadsheet format)                                 │
│ ○ PDF (human-readable report)                              │
│                                                             │
│ [Generate Export] [Cancel]                                 │
│                                                             │
│ ──────────────────────────────────────────────────────────│
│ Export Status:                                              │
│ Request #1247: user_123 (created 2 hours ago)              │
│ Status: ✅ Complete                                         │
│ Download: [📥 user_123_export_2026-01-15.json]             │
│ Expires: 2026-02-14 (30 days)                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Right to Rectification (Art. 16)

**User request:** "Fix incorrect information about me"

**System response:**
1. User submits correction (e.g., "Email should be john.doe@example.com")
2. System:
   - Updates personal data
   - Logs change in audit trail (who changed what, when)
   - Notifies all recipients (skills, services that have copy of data)
3. Confirmation sent to user

#### Right to Erasure (Art. 17 - "Right to be forgotten")

**User request:** "Delete all data about me"

**System response:**
1. User submits erasure request
2. UI collects scope:
   - All data, or specific data categories?
   - Delete immediately or complete current tasks first?
3. On approval:
   - All personal data deleted
   - Caches cleared
   - Deleted from vector store, graph DB, Redis
   - Audit log records what was deleted (legal hold)
4. Verification report generated

**UI implementation:**

```
┌─────────────────────────────────────────────────────────────┐
│ Right to Erasure (GDPR Art. 17)                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Request #789: user_123 - Pending Review                    │
│ Submitted: 2026-01-14 14:30                                │
│                                                             │
│ Scope:                                                      │
│ - Revoke all consents                                       │
│ - Delete all processing records                             │
│ - Purge cached data (Redis)                                │
│ - Delete from vector DB (Qdrant)                           │
│ - Delete from graph DB (Neo4j)                             │
│ - Clear session data                                        │
│                                                             │
│ Estimated impact:                                           │
│ • Data records: 42 (personal info)                         │
│ • Processing records: 156 (queries, interactions)          │
│ • Total data: 12.3 MB                                      │
│                                                             │
│ Execution plan:                                             │
│ 1. ⏳ Disable user account (5 min)                         │
│ 2. ⏳ Complete in-flight requests (wait up to 5 min)       │
│ 3. ⏳ Delete from Qdrant (2-5 min)                         │
│ 4. ⏳ Delete from Neo4j (1-2 min)                          │
│ 5. ⏳ Clear Redis cache (30 sec)                           │
│ 6. ⏳ Archive deleted data (encrypted, 7 years) (1 min)     │
│                                                             │
│ [Approve & Execute] [Reject] [Request More Info]          │
│                                                             │
│ Note: Cannot be reversed. Requires legal approval.         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Right to Data Portability (Art. 20)

**User request:** "Give me my data in a portable format so I can move to another service"

**System response:**
1. User submits portability request
2. System exports all personal data in machine-readable format (JSON preferred)
3. User downloads encrypted file
4. Can import to competing service (must support same format)

#### Right to Object (Art. 21)

**User request:** "Stop using my data for marketing / profiling"

**System response:**
1. User submits objection
2. System stops the specific processing activity
3. Audit trail records objection
4. User notified of confirmation

### 1.6 Managing Data Subject Requests

Click **[Data Subject Rights]** tab to see all pending requests:

```
┌─────────────────────────────────────────────────────────────┐
│ Data Subject Rights Requests (5 pending)                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Request #789: Right to Erasure (user_123)                  │
│ Submitted: 2026-01-14 14:30                                │
│ Status: ⏳ Pending Review (23 hours remaining of 30-day SLA)│
│ Actions: [Approve] [Reject] [Request Info]                 │
│                                                             │
│ Request #788: Right to Access (user_456)                   │
│ Submitted: 2026-01-14 10:15                                │
│ Status: ✅ Complete - [📥 Download]                         │
│                                                             │
│ Request #787: Right to Rectification (user_789)            │
│ Submitted: 2026-01-13 16:45                                │
│ Status: ✅ Complete - Email corrected                       │
│                                                             │
│ Request #786: Right to Portability (user_101)              │
│ Submitted: 2026-01-13 09:00                                │
│ Status: ✅ Complete - [📥 Download]                         │
│                                                             │
│ Request #785: Right to Object (user_202)                   │
│ Submitted: 2026-01-12 14:30                                │
│ Status: ✅ Complete - Marketing disabled                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Key metrics:**
- **SLA:** 30 days to respond to data subject rights requests (GDPR mandate)
- **Status:** Track progress toward deadline
- **Audit:** All approvals/rejections logged

---

## 2. Audit Trail Management

### 2.1 Overview

**EU AI Act Article 12** requires:
> "High-risk AI systems shall keep automatically generated logs of events... to ensure full traceability"

**This section covers:**
- Viewing immutable audit logs
- Verifying integrity (cryptographic chain)
- Generating compliance reports
- Exporting logs for external audits

### 2.2 Accessing Audit Trail

Navigate to **Admin Dashboard > Governance > Audit Trail**.

```
┌─────────────────────────────────────────────────────────────┐
│ Audit Trail Viewer                       [Verify Integrity] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Filters:                                                    │
│ Event Type: [All ▼] Actor: [All ▼] Time: [Last 24h ▼]     │
│ Search: [________________] [Apply]                         │
│                                                             │
│ ┌───────────────────────────────────────────────────────┐  │
│ │ Audit Events (Latest 50)                              │  │
│ │ ───────────────────────────────────────────────────── │  │
│ │                                                       │  │
│ │ 🟢 2026-01-15 14:25:32 | SKILL_EXECUTED               │  │
│ │    Actor: user_123 → retrieval skill                  │  │
│ │    Resource: query_7a3f9b                             │  │
│ │    Outcome: ✅ success, 120ms                          │  │
│ │    Hash: 7a3f9b... (chain verified ✓)                │  │
│ │    [View Details]                                     │  │
│ │                                                       │  │
│ │ 🟡 2026-01-15 14:25:30 | DATA_READ                     │  │
│ │    Actor: retrieval skill → document_7f3a             │  │
│ │    Resource: document_7f3a                            │  │
│ │    Outcome: ✅ success                                 │  │
│ │    Data Categories: [identifier, contact]             │  │
│ │    Hash: 5d2c8a... (chain verified ✓)                │  │
│ │    [View Details]                                     │  │
│ │                                                       │  │
│ │ 🔴 2026-01-15 14:24:10 | POLICY_VIOLATION              │  │
│ │    Actor: user_456 → shell tool                       │  │
│ │    Resource: shell_exec                               │  │
│ │    Outcome: ❌ blocked (insufficient permissions)      │  │
│ │    Hash: 3c7d2a... (chain verified ✓)                │  │
│ │    [View Details]                                     │  │
│ │                                                       │  │
│ └───────────────────────────────────────────────────────┘  │
│                                                             │
│ [Generate GDPR Report] [Export to CSV] [Export to JSON]    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 Event Types

| Event | Meaning | Logged Data |
|-------|---------|-------------|
| **SKILL_EXECUTED** | Skill was invoked | skill name, query, result, duration |
| **DATA_READ** | Personal data accessed | user_id, data categories, context |
| **DATA_WRITTEN** | Personal data modified | user_id, old value, new value |
| **DATA_DELETED** | Personal data removed | user_id, what was deleted |
| **CONSENT_CREATED** | Consent record created | user_id, legal basis, data categories |
| **CONSENT_WITHDRAWN** | User revoked consent | user_id, when revoked |
| **AUTH_SUCCESS** | User authentication succeeded | user_id, method, IP address |
| **AUTH_FAILURE** | User authentication failed | attempted user_id, IP, reason |
| **POLICY_VIOLATION** | Security/rate limit breach | what rule, who violated, action taken |
| **SKILL_ACTIVATED** | Skill turned on | skill name, who activated |
| **SKILL_CONFIG_CHANGED** | Skill config was modified | skill name, old config, new config |

### 2.4 Cryptographic Integrity Verification

Each audit event is linked to the previous one using cryptographic hashing (SHA-256), creating an immutable chain.

**How it works:**

```
Event 1: [SKILL_EXECUTED]
Hash: 7a3f9b...

Event 2: [DATA_READ]
Hash of previous + Event 2 data: 5d2c8a...

Event 3: [AUTH_SUCCESS]
Hash of previous + Event 3 data: 9e1b4f...

If someone tries to modify Event 2:
- Previous hash no longer matches
- Chain integrity check FAILS
- Audit trail notifies administrators
```

**To verify integrity:**

1. Click **[Verify Integrity]** at top
2. System checks all hashes from oldest to newest
3. Results shown:
   ```
   ✅ Integrity Verified
   Chain: 14,247 events checked
   Oldest: 2023-01-15 (3 years, legally compliant)
   Newest: 2026-01-15
   Status: ✅ All hashes match (no tampering detected)
   ```

> **🔒 Security Note:** Integrity verification ensures audit logs haven't been modified. This is a core EU AI Act requirement.

### 2.5 Generating Compliance Reports

#### GDPR Report (Article 30 - Records of Processing Activities)

Click **[Generate GDPR Report]**:

```
Generates: GDPR_Article30_ProcessingActivities.pdf

Contents:
- Processing activity description
- Legal basis for processing (Art. 6)
- Data categories processed
- Data subjects affected
- Retention periods
- Technical/organizational safeguards
- Sub-processors (if applicable)
- Audit events summary
- Dates covered: [date range]
```

**Use case:** Show GDPR compliance to data subjects or regulators

#### Security Report

Click **[Export] > [Security Report]**:

```
Contents:
- Failed authentication attempts
- Policy violations
- Rate limit exceedances
- Unauthorized access attempts
- Skill configuration changes
- Time period: Last 30/90/365 days
```

**Use case:** Security audits, incident response

#### Skill Usage Report

Click **[Export] > [Skill Usage]**:

```
Contents per skill:
- Total invocations
- Success rate
- Error rate (with error types)
- Performance metrics (P50, P95, P99 latency)
- Resource consumption (memory, CPU)
```

**Use case:** Capacity planning, performance analysis

### 2.6 Exporting Logs

Click **[Export]** to download audit logs:

**Options:**

1. **Export to CSV** - Spreadsheet format
   ```csv
   timestamp,event_type,actor,resource,outcome,hash,verified
   2026-01-15 14:25:32,SKILL_EXECUTED,user_123,query_7a3f9b,success,7a3f9b...,true
   ```

2. **Export to JSON** - Structured format
   ```json
   {
     "events": [
       {
         "timestamp": "2026-01-15T14:25:32Z",
         "event_type": "SKILL_EXECUTED",
         "actor": "user_123",
         "data_categories": ["identifier", "contact"]
       }
     ]
   }
   ```

3. **Export to PDF** - Compliance report format

**Usage:**
- Send to external auditors
- Archive for legal holds (7-year retention)
- Analyze with external tools
- Generate evidence for data protection authorities

---

## 3. Explainability Dashboard

### 3.1 Overview

**EU AI Act Article 13** requires:
> "High-risk AI systems shall be designed to... make available to users... information about the AI system"

**This section covers:**
- Decision trace visualization (how AI arrived at answer)
- Multi-level explanations (User/Expert/Audit)
- Source attribution (which documents support answer)
- Hallucination risk assessment

### 3.2 Accessing Explainability

Navigate to **Admin Dashboard > Governance > Explainability**.

```
┌─────────────────────────────────────────────────────────────┐
│ Explainability Dashboard                [Recent Traces ▼]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Query: "What are the latest quantum computing trends?"     │
│ Trace ID: trace_1737052332_decision.routed                │
│ Timestamp: 2026-01-15 14:25:32                            │
│                                                             │
│ Explanation Level:  ◉ User View  ○ Expert View  ○ Audit   │
│                                                             │
│ ┌───────────────────────────────────────────────────────┐  │
│ │ USER VIEW (Non-technical explanation)                 │  │
│ │ ───────────────────────────────────────────────────── │  │
│ │                                                       │  │
│ │ This response was created with **high confidence**   │  │
│ │ (87%) using information from:                        │  │
│ │                                                       │  │
│ │ • quantum_computing_2025.pdf (relevance: 94%)        │  │
│ │ • arxiv_2501_trends.pdf (relevance: 89%)             │  │
│ │ • nature_qc_review.pdf (relevance: 82%)              │  │
│ │                                                       │  │
│ │ The system used **3 specialized capabilities**        │  │
│ │ (retrieval, web_search, synthesis) to find and       │  │
│ │ combine the relevant information.                     │  │
│ │                                                       │  │
│ │ **Hallucination Risk:** Low (8%)                      │  │
│ │ **Data Freshness:** Current as of Jan 2026            │  │
│ │                                                       │  │
│ │ [Switch to Expert View for technical details]        │  │
│ │                                                       │  │
│ └───────────────────────────────────────────────────────┘  │
│                                                             │
│ ┌───────────────────────────────────────────────────────┐  │
│ │ DECISION FLOW (How answer was generated)              │  │
│ │ ───────────────────────────────────────────────────── │  │
│ │                                                       │  │
│ │ 1. Intent Classification                             │  │
│ │    ✓ RESEARCH (confidence: 92%)                      │  │
│ │    → Triggers: [research, web_search, synthesis]     │  │
│ │                                                       │  │
│ │ 2. Skill Selection                                   │  │
│ │    ✓ retrieval (explicit trigger match)              │  │
│ │    ✓ web_search (intent-based routing)               │  │
│ │    ✓ synthesis (auto-activated for multi-source)     │  │
│ │                                                       │  │
│ │ 3. Retrieval Phase                                   │  │
│ │    Mode: Hybrid (vector + lexical)                   │  │
│ │    Retrieved: 15 chunks, Used: 8 chunks              │  │
│ │    Time: 340ms                                        │  │
│ │                                                       │  │
│ │ 4. Response Generation                               │  │
│ │    Model: Nemotron3 Nano (30B)                       │  │
│ │    Tokens: 487 output                                │  │
│ │    Time: 1,200ms                                     │  │
│ │    Confidence: 87%                                   │  │
│ │                                                       │  │
│ └───────────────────────────────────────────────────────┘  │
│                                                             │
│ ┌───────────────────────────────────────────────────────┐  │
│ │ SOURCE ATTRIBUTION                                    │  │
│ │ ───────────────────────────────────────────────────── │  │
│ │ [quantum_computing_2025.pdf] Page 12-14              │  │
│ │   "Recent advances in topological qubits..."         │  │
│ │   Relevance: 94% | Confidence: High                  │  │
│ │   [Show context] [Verify source]                     │  │
│ │                                                       │  │
│ │ [arxiv_2501_trends.pdf] Page 3-5                     │  │
│ │   "Industry adoption of quantum annealing..."        │  │
│ │   Relevance: 89% | Confidence: High                  │  │
│ │                                                       │  │
│ └───────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Understanding the Three Explanation Levels

#### Level 1: User View (Non-technical)

**Audience:** End users who want to understand why they got this answer

**Content:**
- Overall confidence (0-100%)
- Top sources (documents, links)
- High-level process (3-5 steps)
- Risk assessment (hallucination risk)
- Data freshness (when was data last updated)

**Language:** Plain English, no jargon

**Example:**
```
"This response comes from 3 research papers about quantum computing,
retrieved using semantic search and verified by web search.
The system has 87% confidence in this answer."
```

#### Level 2: Expert View (Technical)

**Audience:** Data scientists, ML engineers, compliance officers

**Content:**
- All Level 1 information, plus:
- Model name and parameters
- Embedding model and vector space
- Retrieval mode (vector/hybrid/graph)
- Reranking score
- Per-source confidence scores
- LLM prompting strategy

**Language:** Technical jargon acceptable

**Example:**
```
Model: Nemotron3 Nano (30B parameters)
Embeddings: BGE-M3 (1024-dim dense)
Retrieval: Hybrid search (RRF fusion)
Top-k: 8 contexts
Reranking: Cross-encoder (ms-marco)

Context 1: quantum_computing_2025.pdf (relevance: 0.94)
Context 2: arxiv_2501_trends.pdf (relevance: 0.89)
...
```

#### Level 3: Audit View (Fully Transparent)

**Audience:** Auditors, regulators, compliance systems

**Content:**
- Everything in Levels 1-2, plus:
- Complete LLM input/output (full prompts and responses)
- Embedding vectors (numerical)
- Database queries executed
- Configuration at time of query
- Raw scores before normalization

**Language:** Machine-readable (JSON/structured data)

**Use case:** Generate evidence for auditors, replay decision for verification

### 3.4 Source Attribution

Click **[Show context]** to see exact excerpt from source document:

```
┌─────────────────────────────────────────────────────────────┐
│ Source Context: quantum_computing_2025.pdf                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Page 12-14 (excerpt)                                        │
│                                                             │
│ "Recent advances in topological qubits represent a major    │
│ breakthrough in quantum error correction. Unlike previous   │
│ approaches, topological qubits encode information in the    │
│ global properties of a system, making them resistant to     │
│ local perturbations. This property is particularly valuable │
│ for NISQ-era devices where decoherence remains a critical   │
│ limiting factor."                                            │
│                                                             │
│ Relevance: 94% (matches query "latest quantum trends")      │
│ Confidence: High                                            │
│ Document quality: ⭐⭐⭐⭐⭐ (peer-reviewed, 2025)             │
│                                                             │
│ [Verify Source URL]                                         │
│ [Check Document Authenticity]                              │
│ [View Full Document]                                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.5 Hallucination Risk Assessment

The system calculates hallucination risk (probability the answer is fabricated):

| Risk Level | Confidence Range | Meaning |
|-----------|-----------------|---------|
| **Low** | 85-100% | Answer strongly supported by sources |
| **Medium** | 60-85% | Answer partially supported, some inference |
| **High** | <60% | Answer may not be supported by sources |

**Factors that decrease confidence:**
- Few/weak sources
- Contradictory sources
- LLM inference (not direct quote)
- Low retrieval scores
- Out-of-distribution query

**Factors that increase confidence:**
- Multiple strong sources
- Consistent information across sources
- Direct quotes (not paraphrased)
- High retrieval scores
- Recent data

---

## 4. Skill Certification Dashboard

### 4.1 Overview

The certification framework ensures skills meet compliance requirements:

**3 certification tiers:**
1. **Basic** - Skill registered, YAML valid, basic tests pass
2. **Standard** - Enhanced validation, security checks, GDPR compliance
3. **Enterprise** - Full compliance (GDPR, AI Act), security audit, formal approval

### 4.2 Accessing Certification Dashboard

Navigate to **Admin Dashboard > Governance > Skill Certification**.

```
┌─────────────────────────────────────────────────────────────┐
│ Skill Certification Dashboard            [Validate All]     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Certification Overview                                      │
│ 🟢 Enterprise: 8 skills | 🟡 Standard: 12 | ⚪ Basic: 5     │
│ ⚠️ Expiring Soon: 2 skills (within 30 days)                 │
│                                                             │
│ Filter: [All Levels ▼] [Status ▼] [Search: ___________]    │
│                                                             │
│ ┌───────────────────────────────────────────────────────┐  │
│ │ Skill Certifications                                  │  │
│ │ ───────────────────────────────────────────────────── │  │
│ │                                                       │  │
│ │ 🟢 retrieval                           ENTERPRISE     │  │
│ │    Version: 1.2.0                                     │  │
│ │    Valid until: 2027-01-15                            │  │
│ │    Last validated: 2026-01-15                         │  │
│ │    Checks: ✅ GDPR ✅ Security ✅ Audit ✅ Explain.  │  │
│ │    [View Report] [Re-validate]                        │  │
│ │                                                       │  │
│ │ 🟡 web_search                          STANDARD       │  │
│ │    Version: 1.0.5                                     │  │
│ │    Valid until: 2026-12-20 (11 months remaining)     │  │
│ │    Last validated: 2025-12-20                         │  │
│ │    Issues: ⚠️ GDPR purpose declaration incomplete    │  │
│ │    [View Report] [Upgrade to Enterprise]              │  │
│ │                                                       │  │
│ │ 🔴 experimental_tool                  BASIC           │  │
│ │    Version: 0.9.0                                     │  │
│ │    Valid until: 2026-03-15 (EXPIRING IN 15 DAYS!)   │  │
│ │    Last validated: 2025-03-15                         │  │
│ │    Issues: ❌ No audit integration                     │  │
│ │            ❌ Security: blocked eval() found          │  │
│ │    [View Report] [Fix Issues] [Upgrade]               │  │
│ │                                                       │  │
│ └───────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 Certification Tiers

#### Basic (1 year validity)

**Requirements:**
- ✅ Skill metadata complete (name, version, author)
- ✅ YAML configuration valid
- ✅ No security anti-patterns
- ✅ Unit tests pass

**Does NOT require:**
- GDPR compliance checks
- Audit trail integration
- Explainability
- Formal security review

**Use case:** Experimental skills, development

#### Standard (1 year validity)

**Requirements:**
- ✅ All Basic checks
- ✅ GDPR compliance:
  - Data categories documented
  - Purpose declaration filled
  - Retention periods defined
- ✅ Security review (no hardcoded secrets, SQL injection, etc.)
- ✅ Tool rate limits configured
- ✅ Integration tests pass

**Does NOT require:**
- Formal security audit
- Explainability implementation

**Use case:** Production skills, internal use

#### Enterprise (2 year validity)

**Requirements:**
- ✅ All Standard checks
- ✅ Formal security audit (external review recommended)
- ✅ Explainability fully implemented
- ✅ Audit trail integration verified
- ✅ Performance benchmarks documented
- ✅ Disaster recovery plan
- ✅ SLA agreement defined

**Use case:** Customer-facing skills, regulated industries

### 4.4 Re-validating Skills

Click **[Re-validate]** to run certification checks:

```
Validating: retrieval (Enterprise)...

1. GDPR Compliance Check            ✅ Pass
   - Data categories documented
   - Purpose declaration present
   - Retention period: 90 days

2. Security Review                  ✅ Pass
   - No hardcoded secrets
   - No SQL injection patterns
   - Rate limits configured

3. Audit Integration                ✅ Pass
   - Audit logging enabled
   - 7-year retention configured
   - Hash verification working

4. Explainability Check             ✅ Pass
   - Decision traces enabled
   - Source attribution working
   - Confidence scores calibrated

5. Performance Benchmarks           ✅ Pass
   - P95 latency: 340ms (target: <500ms)
   - Success rate: 98.7% (target: >95%)
   - Memory: 234MB (target: <500MB)

✅ Validation Passed
Certificate updated: Valid until 2027-01-15
```

### 4.5 Upgrading Certification Level

Click **[Upgrade to Enterprise]** to raise certification tier:

1. System re-runs all checks at new level
2. If checks pass: Certificate upgraded, validity extended
3. If checks fail: Error report explains what needs fixing

**Typical upgrade path:**
```
Basic (experimental) → Standard (production) → Enterprise (customer-facing)
     Month 1              Month 6                   Year 1
```

---

## 5. Compliance Best Practices

### 5.1 GDPR Compliance Workflow

**Monthly checklist:**

- [ ] Review active consents - are they up-to-date?
- [ ] Check for expiring consents - need renewal?
- [ ] Review data subject rights requests - any overdue?
- [ ] Audit data access logs - any suspicious patterns?
- [ ] Verify deletion/rectification requests processed
- [ ] Check PII redaction is working for restricted data

**Quarterly audit:**

- [ ] Generate GDPR Article 30 report (Records of Processing)
- [ ] Review skill permissions - still appropriate?
- [ ] Audit trail integrity check - no tampering detected?
- [ ] Data retention analysis - keeping data longer than needed?
- [ ] Sub-processor list update (if using external services)

**Annual review:**

- [ ] Data Protection Impact Assessment (DPIA) if new risky processing
- [ ] Update Privacy Policy based on changes
- [ ] Security audit by external firm (recommended)
- [ ] Test data subject rights workflows
- [ ] Breach response plan update

### 5.2 Audit Trail Best Practices

**Data retention:**
- Keep audit logs for **7 years** (GDPR requirement)
- Archive older logs to cold storage
- Verify integrity monthly
- Test recovery procedures quarterly

**Monitoring:**
- Set alerts for policy violations
- Review deleted data (should be rare)
- Monitor for unusual access patterns
- Check for unauthorized tool usage

### 5.3 Explainability Best Practices

**For end users:**
- Always provide User View by default
- Make sources easily accessible
- Show hallucination risk clearly
- Offer "learn more" links to technical details

**For auditors:**
- Maintain Audit View logs for 7 years
- Test Audit View export monthly
- Verify decision traces are complete
- Check confidence scores are calibrated

### 5.4 Skill Certification Strategy

**Development phase:** Basic certification
- Fast iteration, minimal bureaucracy
- No GDPR/audit overhead

**Production launch:** Standard certification
- Full GDPR compliance
- Security review
- Rate limiting active

**Enterprise deployment:** Enterprise certification
- Annual security audit
- Formal SLA with uptime/performance guarantees
- Executive sign-off required for changes

---

## 6. Legal References

### GDPR Articles

| Article | Topic | Reference |
|---------|-------|-----------|
| Art. 4 | Definitions (personal data, processing, etc.) | [EUR-Lex](https://eur-lex.europa.eu/eli/reg/2016/679/oj#d1e1489-1-1) |
| Art. 6 | Lawfulness of processing (legal basis) | [EUR-Lex](https://eur-lex.europa.eu/eli/reg/2016/679/oj#d1e1907-1-1) |
| Art. 7 | Conditions for consent | [EUR-Lex](https://eur-lex.europa.eu/eli/reg/2016/679/oj#d1e2017-1-1) |
| Art. 13 | Information to be provided (transparency) | [EUR-Lex](https://eur-lex.europa.eu/eli/reg/2016/679/oj#d1e2279-1-1) |
| Art. 15 | Right of access | [EUR-Lex](https://eur-lex.europa.eu/eli/reg/2016/679/oj#d1e2542-1-1) |
| Art. 16 | Right to rectification | [EUR-Lex](https://eur-lex.europa.eu/eli/reg/2016/679/oj#d1e2614-1-1) |
| Art. 17 | Right to erasure | [EUR-Lex](https://eur-lex.europa.eu/eli/reg/2016/679/oj#d1e2686-1-1) |
| Art. 20 | Right to data portability | [EUR-Lex](https://eur-lex.europa.eu/eli/reg/2016/679/oj#d1e2783-1-1) |
| Art. 30 | Records of processing activities | [EUR-Lex](https://eur-lex.europa.eu/eli/reg/2016/679/oj#d1e3063-1-1) |

### EU AI Act Articles

| Article | Topic | Reference |
|---------|-------|-----------|
| Art. 12 | Record-keeping and transparency | [EUR-Lex](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) |
| Art. 13 | Transparency and provision of information to users | [EUR-Lex](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) |
| Art. 31 | Risk assessment | [EUR-Lex](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) |

---

## See Also

- **[Skill Management Guide](SKILL_MANAGEMENT_GUIDE.md)** - Configure skills and tools
- **[Agent Monitoring Guide](AGENT_MONITORING_GUIDE.md)** - Monitor multi-agent coordination
- **[API Documentation - Admin](../api/ADMIN_API_REFERENCE.md)** - GDPR/Audit endpoints
- **[ADR-043: Governance Architecture](../adr/ADR-043-governance-architecture.md)** - Design decisions
- **[GDPR Compliance Checklist](../planning/GDPR_COMPLIANCE_CHECKLIST.md)** - Operational checklist

---

**Document:** GOVERNANCE_COMPLIANCE_GUIDE.md
**Last Updated:** 2026-01-15 (Sprint 98 Plan)
**Status:** Planned - Ready for Sprint 98 Implementation
**Audience:** Compliance officers, Legal teams, DPOs, System administrators
**Maintainer:** Documentation Agent

---
