# Sprint 67: Agentic Capabilities & Tool Adaptation

**Status:** PLANNED
**Branch:** `sprint-67-agentic-adaptation`
**Start Date:** 2025-12-31
**Estimated Duration:** 10-12 Tage
**Total Story Points:** 75 SP

---

## Sprint Overview

Sprint 67 transformiert AEGIS RAG in ein **production-ready Agentic System** mit drei strategischen Initiativen:

1. **Secure Shell Sandbox (deepagents)** - LangChain-native Agent Harness mit Bubblewrap Isolation
2. **Agents Adaptation (Paper 2512.16301)** - Tool-level Adaptation für Retriever/Reranker/Query-Rewriter
3. **LLM Intent Classifier (C-LARA)** - 60% → 85-92% Accuracy Improvement

**Architektur-Leitplanken:**
- Agent Core bleibt deterministisch & auditierbar
- Tool-Adaptation (T1/T2) vor Agent-Adaptation (A1/A2)
- Reproduzierbar: versionierte Datasets, feste Seeds, Eval-Gates
- Sicherheit: Sandbox Isolation, keine silent regressions

**Voraussetzung:**
Sprint 66 abgeschlossen (E2E tests stabilized, OMNITRACKER docs indexed)

---

## Feature Overview

| # | Feature | SP | Priority | Dependencies |
|---|---------|-----|----------|--------------|
| 67.1 | BubblewrapSandboxBackend | 5 | P0 | - |
| 67.2 | deepagents Integration | 4 | P0 | 67.1 |
| 67.3 | Multi-Language CodeAct (Bash+Python) | 3 | P0 | 67.2 |
| 67.4 | Sandbox Testing & Documentation | 3 | P0 | 67.3 |
| 67.5 | Unified Trace & Telemetry (FEAT-001) | 8 | P0 | - |
| 67.6 | Eval Harness (FEAT-002) | 10 | P0 | 67.5 |
| 67.7 | Dataset Builder (FEAT-003) | 8 | P1 | 67.5, 67.6 |
| 67.8 | Adaptive Reranker v1 (FEAT-004) | 13 | P1 | 67.7 |
| 67.9 | Query Rewriter v1 (FEAT-005) | 10 | P1 | 67.7 |
| 67.10 | C-LARA Data Generation (TD-075 Phase 1) | 3 | P1 | - |
| 67.11 | C-LARA Model Training (TD-075 Phase 2) | 3 | P1 | 67.10 |
| 67.12 | C-LARA Integration (TD-075 Phase 3) | 5 | P1 | 67.11 |
| 67.13 | C-LARA A/B Testing (TD-075 Phase 4) | 2 | P2 | 67.12 |

**Total: 77 SP** (reduced to 75 SP with parallel execution)

---

## Epic 1: Secure Shell Sandbox (deepagents) - 15 SP

### Feature 67.1: BubblewrapSandboxBackend (5 SP)

**Priority:** P0
**Ziel:** Custom Sandbox Backend für deepagents mit Bubblewrap Isolation

**Scope:**
- Implementierung von `SandboxBackendProtocol` (deepagents)
- Bubblewrap Command Builder mit Security Restrictions
- Filesystem Isolation (read-only repo + tmpfs workspace)
- Network Isolation (unshare-net + egress proxy)
- Seccomp Profile (syscall whitelist)

**Neue Dateien:**
```
src/domains/agents/sandbox/
├── bubblewrap_backend.py
├── seccomp_profile.json
├── egress_proxy.py
└── __init__.py
```

**Implementation:**
```python
from deepagents.backends.protocol import (
    SandboxBackendProtocol,
    ExecuteResult,
    WriteResult
)

class BubblewrapSandboxBackend(SandboxBackendProtocol):
    """Bubblewrap-based sandbox for secure command execution."""

    def __init__(
        self,
        repo_path: str,
        allowed_domains: list[str] = None,
        timeout: int = 30,
        seccomp_profile: str = None
    ):
        self.repo_path = Path(repo_path).resolve()
        self.workspace = Path("/tmp/aegis-workspace")
        self.allowed_domains = allowed_domains or []
        self.timeout = timeout
        self.seccomp_profile = seccomp_profile

    def execute(self, command: str) -> ExecuteResult:
        """Execute command in Bubblewrap sandbox."""
        ...
```

**Acceptance Criteria:**
- [ ] `SandboxBackendProtocol` vollständig implementiert
- [ ] Bubblewrap auf DGX Spark (ARM64) getestet
- [ ] Filesystem-Isolation funktional (read-only + tmpfs)
- [ ] Network-Isolation via unshare-net
- [ ] Seccomp-Profile erstellt (strace-basiert)
- [ ] Timeout-Handling (<30s default)
- [ ] Output-Truncation (max 32KB)

---

### Feature 67.2: deepagents Integration (4 SP)

**Priority:** P0
**Ziel:** Agent Harness mit deepagents + Custom Backend

**Scope:**
- `create_deep_agent()` mit BubblewrapSandboxBackend
- System Prompt für AegisRAG Code-Analyse
- TodoListMiddleware für Planning
- FilesystemMiddleware für File Operations
- interrupt_on Konfiguration für gefährliche Commands

**Implementation:**
```python
from deepagents import create_deep_agent
from deepagents.middleware import TodoListMiddleware, FilesystemMiddleware
from langchain.chat_models import init_chat_model

# LLM (austauschbar)
model = init_chat_model("ollama:qwen2.5:7b")

# Custom Backend
backend = BubblewrapSandboxBackend(
    repo_path="/path/to/analyzed/repo",
    allowed_domains=["github.com"],
    timeout=30
)

# Agent erstellen
agent = create_deep_agent(
    model=model,
    backend=backend,
    system_prompt=AEGIS_ANALYSIS_PROMPT,
    interrupt_on={
        "execute_bash": {
            "patterns": ["rm -rf", "curl", "wget", "> /"],
            "allowed_decisions": ["approve", "reject"]
        }
    }
)
```

**Acceptance Criteria:**
- [ ] Agent läuft mit Custom Backend
- [ ] TodoListMiddleware funktional (Planning)
- [ ] FilesystemMiddleware funktional (read/write/grep)
- [ ] Human-in-the-Loop für gefährliche Commands
- [ ] Token-Limit Konfiguration
- [ ] LLM-Wechsel funktioniert (Ollama ↔ Anthropic ↔ OpenAI)

---

### Feature 67.3: Multi-Language CodeAct (3 SP)

**Priority:** P0
**Ziel:** Bash + Python Execution mit Shared Workspace

**Scope:**
- `execute_bash` Tool mit Bubblewrap-Backend
- `execute_python` Tool mit Pyodide-Backend (langchain-sandbox)
- CompositeBackend für Shared Workspace
- State Persistence zwischen beiden Sandboxes

**Architecture:**
```
┌─────────────────────────────────────────┐
│            deepagents Agent             │
│  ┌─────────────────────────────────┐    │
│  │     CompositeBackend            │    │
│  │  ┌───────────┬───────────────┐  │    │
│  │  │ /bash/*   │ /python/*     │  │    │
│  │  │ Bubblewrap│ Pyodide       │  │    │
│  │  │ Sandbox   │ Sandbox       │  │    │
│  │  └───────────┴───────────────┘  │    │
│  │         ▲           ▲           │    │
│  │         └─────┬─────┘           │    │
│  │        Shared Workspace         │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

**Use Cases:**
| Bash | Python |
|------|--------|
| `find . -name "*.py"` | DataFrame-Analyse |
| `grep -r "TODO"` | JSON/YAML Parsing |
| `git log --oneline` | Embedding-Generierung |
| `wc -l src/**/*.py` | Entity Extraction |

**Acceptance Criteria:**
- [ ] Bash-Skript-Execution funktional
- [ ] Python-Code-Execution funktional
- [ ] Dateien zwischen Sandboxes teilbar (/workspace)
- [ ] Agent wählt situativ passende Sprache

---

### Feature 67.4: Sandbox Testing & Documentation (3 SP)

**Priority:** P0
**Ziel:** Security Tests, Performance Benchmarks, Documentation

**Scope:**
- Unit Tests für Backend-Protocol
- Integration Tests mit deepagents
- Security Tests (Path Traversal, Network Escape, Sandbox Escape)
- Performance Benchmarks (<200ms Overhead)
- Dokumentation (ADR, User Guide, API Reference)

**Test Cases:**
```python
# Security Tests
test_path_traversal_blocked()
test_network_isolation()
test_sandbox_escape_prevention()
test_dangerous_commands_require_approval()

# Performance Tests
test_command_execution_latency()  # Target: <200ms overhead
test_concurrent_executions()      # Target: 10+ parallel agents
```

**Acceptance Criteria:**
- [ ] 100% Protocol-Coverage
- [ ] Security Tests bestanden (kein Escape)
- [ ] Performance: <200ms Overhead pro Command
- [ ] ADR-067: Secure Shell Sandbox erstellt
- [ ] User Guide mit Examples

---

## Epic 2: Agents Adaptation (Paper 2512.16301) - 45 SP

### Feature 67.5: Unified Trace & Telemetry (FEAT-001) - 8 SP

**Priority:** P0
**Ziel:** Einheitliches Trace-Format über alle RAG-Stufen

**Scope:**
- Trace-Schema (`trace_v1.jsonschema`)
- Logger Hooks in Retriever/Graph/Memory/Answerer
- Persistenz in `runs/traces/` mit Versionierung
- CLI Viewer zum Filtern nach `request_id`

**Trace Format:**
```json
{
  "trace_version": "v1",
  "request_id": "req_abc123",
  "timestamp": "2025-12-31T10:00:00Z",
  "query": {
    "original": "Was sind die neuen Features?",
    "rewritten": "OMNITRACKER 2025 neue Features Liste",
    "intent": "exploratory",
    "intent_confidence": 0.95
  },
  "retrieval": {
    "vector": {
      "top_k": 10,
      "results": [{"chunk_id": "c1", "score": 0.89, "document_id": "d1"}]
    },
    "bm25": {"top_k": 10, "results": [...]},
    "graph_local": {"top_k": 5, "results": [...]},
    "graph_global": {"top_k": 5, "results": [...]}
  },
  "rrf": {
    "weights": {"vector": 0.2, "bm25": 0.1, "local": 0.2, "global": 0.5},
    "fused_results": [{"chunk_id": "c1", "weighted_rrf_score": 0.92, "rank": 1}]
  },
  "rerank": {
    "method": "cross_encoder",
    "model": "bge-reranker-v2-m3",
    "top_k": 5,
    "results": [{"chunk_id": "c1", "rerank_score": 0.94, "rank": 1}]
  },
  "evidence": {
    "selected_chunks": 5,
    "total_tokens": 1500,
    "citations": ["c1", "c3", "c7"]
  },
  "answer": {
    "text": "Die neuen Features in OMNITRACKER 2025 sind...",
    "latency_ms": 450,
    "model": "qwen2.5:7b",
    "tokens": 250
  },
  "metrics": {
    "total_latency_ms": 680,
    "retrieval_latency_ms": 180,
    "rerank_latency_ms": 50,
    "answer_latency_ms": 450
  }
}
```

**Acceptance Criteria:**
- [ ] Trace-Schema definiert + dokumentiert
- [ ] Logger Hooks in allen Komponenten
- [ ] Traces persistent in `runs/traces/`
- [ ] CLI Viewer: `aegis-trace show --request-id req_abc123`
- [ ] Mind. 10 Beispiel-Traces im Repo

---

### Feature 67.6: Eval Harness (FEAT-002) - 10 SP

**Priority:** P0
**Ziel:** Automatische Qualitätschecks als CI/CD Gates

**Scope:**
- Groundedness-Check (Heuristik oder Judge-Model)
- Citation-Coverage (Zitate zeigen auf passende Evidenz)
- Format-Compliance (JSON-Schema / Pflichtfelder)
- Canary-Suite (20-50 Queries) im Repo
- Eval-Runner mit Scorecards

**Metriken:**
```python
@dataclass
class EvalMetrics:
    grounding_score: float        # 0.0-1.0, wie gut ist Answer in Evidenz verankert?
    citation_coverage: float      # 0.0-1.0, % der Claims mit Citations
    format_pass_rate: float       # 0.0-1.0, % der Outputs mit korrektem Format
    retrieval_hit_at_k: float     # 0.0-1.0, % relevanter Chunks in Top-K
    answer_latency_p95: float     # ms, P95 Latenz
    total_latency_p95: float      # ms, P95 End-to-End
```

**Eval-Suites:**
- **Canary:** 20-50 kritische Queries (Regression Detection)
- **Regression:** 100-200 Queries (Full Coverage)
- **Stress:** 500+ Queries (Load Testing)

**Implementation:**
```python
# eval run --suite canary
eval_runner = EvalRunner(suite="canary")
results = eval_runner.run(
    queries=CANARY_QUERIES,
    metrics=["grounding", "citation", "format", "retrieval_hit@5"]
)

# Output: Scorecard + Fail-Reasons
print(results.scorecard())
# grounding_score: 0.88 (target: 0.85) ✅
# citation_coverage: 0.92 (target: 0.90) ✅
# format_pass_rate: 0.95 (target: 0.95) ✅
# retrieval_hit@5: 0.82 (target: 0.80) ✅
```

**Acceptance Criteria:**
- [ ] Eval-Harness mit 3 Suites (Canary/Regression/Stress)
- [ ] 6 Metriken implementiert
- [ ] Canary-Suite (20-50 Queries) im Repo
- [ ] CI/CD Integration (GitHub Actions)
- [ ] Fail-Reasons transparent

---

### Feature 67.7: Dataset Builder (FEAT-003) - 8 SP

**Priority:** P1
**Ziel:** Aus Traces Trainingsdaten erzeugen

**Scope:**
- Rerank-Daten: (query, pos_chunk, neg_chunk) Triplets
- Rewrite-Daten: (query, rewrite, retrieval_outcome) Pairs
- Sampling-Strategien (hard negatives, in-batch negatives)
- Labeling-Regeln (Hit@k, Eval-Score thresholds)
- Dedup + PII-Filter
- Dataset-Versionierung

**Implementation:**
```python
# dataset build --from runs/traces/ --out data/datasets/v1/
builder = DatasetBuilder(trace_dir="runs/traces/")

# Rerank Pairs
rerank_data = builder.build_rerank_pairs(
    sampling="hard_negatives",  # Top-K miss
    min_score_diff=0.3          # pos vs neg threshold
)
rerank_data.save("data/datasets/v1/rerank_pairs.jsonl")

# Rewrite Supervision
rewrite_data = builder.build_rewrite_supervision(
    success_threshold=0.8  # retrieval_hit@5 >= 0.8
)
rewrite_data.save("data/datasets/v1/rewrite_supervision.jsonl")
```

**Output Formats:**
```jsonl
# rerank_pairs.jsonl
{"query": "Was sind die neuen Features?", "pos_chunk_id": "c1", "neg_chunk_id": "c7", "pos_score": 0.92, "neg_score": 0.45}

# rewrite_supervision.jsonl
{"query": "neue Features", "rewrite": "OMNITRACKER 2025 neue Features Liste", "retrieval_hit@5": 0.9, "label": "positive"}
```

**Acceptance Criteria:**
- [ ] Dataset Builder implementiert
- [ ] 2 Dataset-Typen: Rerank + Rewrite
- [ ] Sampling-Strategien: hard negatives, in-batch
- [ ] Dedup + PII-Filter funktional
- [ ] Dataset-Versionierung (`v1/`, `v2/`, ...)
- [ ] Stats-Report (Anzahl Samples, Distributions)

---

### Feature 67.8: Adaptive Reranker v1 (FEAT-004) - 13 SP

**Priority:** P1
**Ziel:** Reranker als austauschbares Modul, trainierbar auf FEAT-003-Daten

**Scope:**
- Reranker-Interface: `rank(query, candidates) -> sorted`
- Baseline-Reranker (Heuristik: BM25 + Vector Score Weighted Average)
- v1 Modell: Cross-Encoder finetuned on rerank_pairs.jsonl
- Training-Skript + Checkpoint-Handling
- A/B Evaluierung auf Canary + Regression
- Online Flag: `--reranker=v1|baseline`

**Implementation:**
```python
from setfit import SetFitModel

class AdaptiveReranker:
    def __init__(self, model_path: str = "models/reranker_v1"):
        self.model = SetFitModel.from_pretrained(model_path)

    def rank(
        self,
        query: str,
        candidates: list[dict]
    ) -> list[dict]:
        """Rerank candidates by relevance."""
        # Embed (query, chunk) pairs
        pairs = [(query, c["text"]) for c in candidates]
        scores = self.model.predict_proba(pairs)

        # Sort by score
        ranked = sorted(
            zip(candidates, scores),
            key=lambda x: x[1],
            reverse=True
        )
        return [c for c, _ in ranked]
```

**Training:**
```bash
# Train reranker on generated data
python scripts/train_reranker.py \
  --data data/datasets/v1/rerank_pairs.jsonl \
  --base-model BAAI/bge-reranker-v2-m3 \
  --output models/reranker_v1 \
  --epochs 3 \
  --batch-size 16

# Evaluate
python scripts/eval_reranker.py \
  --model models/reranker_v1 \
  --suite canary

# Expected improvement:
# retrieval_hit@5: baseline 0.80 → v1 0.88 (+10%)
```

**Acceptance Criteria:**
- [ ] Reranker-Interface implementiert
- [ ] Baseline-Reranker funktional
- [ ] v1 Modell trainiert auf rerank_pairs.jsonl
- [ ] Offline-Verbesserung: +5-10% retrieval_hit@k
- [ ] Online Flag: `--reranker=v1|baseline`
- [ ] A/B Test auf Canary: v1 besser als baseline

---

### Feature 67.9: Query Rewriter v1 (FEAT-005) - 10 SP

**Priority:** P1
**Ziel:** Rewrite-Agent erzeugt optimierte Queries für Vector+Graph

**Scope:**
- Rewrite-Interface: `rewrite(query) -> {vector_query, graph_intent}`
- Prompt-basierter Rewriter (Teacher Model: qwen2.5:7b)
- Optional: Student Distillation (SetFit für schnellere Inference)
- Graph-Intent: Entity/Relation hints für Traversal
- Integration in Retrieval-Pipeline (vor Vector+Graph)

**Implementation:**
```python
class QueryRewriter:
    def __init__(self, model: str = "qwen2.5:7b"):
        self.model = model

    async def rewrite(self, query: str) -> dict:
        """Rewrite query for optimal retrieval."""
        prompt = f"""Du bist ein Query-Optimizer für Hybrid Vector-Graph Retrieval.

Original Query: "{query}"

Erstelle:
1. vector_query: Präzise, keyword+semantisch optimiert für Vector-Search
2. graph_intent: Entity/Relation hints für Graph-Traversal

Output (JSON):
{{
  "vector_query": "...",
  "graph_intent": {{"entities": [...], "relations": [...]}}
}}
"""

        response = await ollama.generate(model=self.model, prompt=prompt)
        return json.loads(response)

# Example Output:
# Original: "neue Features"
# Rewritten:
# {
#   "vector_query": "OMNITRACKER 2025 neue Features Liste Innovationen",
#   "graph_intent": {
#     "entities": ["OMNITRACKER", "Version 2025"],
#     "relations": ["HAS_FEATURE", "INTRODUCED_IN"]
#   }
# }
```

**Acceptance Criteria:**
- [ ] Rewriter-Interface implementiert
- [ ] Prompt-basierter Rewriter funktional
- [ ] Graph-Intent wird im Trace persistiert
- [ ] Graph-Walker nutzt graph_intent
- [ ] Verbesserte Recall: +5-10% retrieval_hit@k
- [ ] Optional: Student Distillation (SetFit) für <50ms Latenz

---

## Epic 3: LLM Intent Classifier (C-LARA) - 13 SP

### Feature 67.10: C-LARA Data Generation (3 SP)

**Priority:** P1
**Ziel:** 1000 Synthetic Examples mit Qwen2.5:7b

**Scope:**
- Data Generation Script mit Qwen2.5:7b (87-95% intent benchmarks)
- 4 intents × 250 examples = 1000 queries
- Mix: 50% German, 50% English
- Include: Technical terms (RAG, OMNITRACKER, Vector Search, BM25)
- Domains: Software docs, business queries, research questions

**Implementation:**
```bash
python scripts/generate_intent_training_data.py \
  --model qwen2.5:7b \
  --examples-per-intent 250 \
  --output data/intent_training_v1.json

# Duration: ~30 minutes (1000 examples @ 2 sec/query)
# Cost: $0 (local Ollama on DGX Spark)
```

**Acceptance Criteria:**
- [ ] 1000 examples generated
- [ ] 50/50 German/English split
- [ ] Technical terms included
- [ ] Human validation (sample 100 examples)
- [ ] Clean and export to JSON

---

### Feature 67.11: C-LARA Model Training (3 SP)

**Priority:** P1
**Ziel:** SetFit model fine-tuned on synthetic data

**Scope:**
- SetFit training on data/intent_training_v1.json
- Base model: BAAI/bge-m3
- Contrastive learning (CosineSimilarityLoss)
- Hyperparameter tuning (iterations, batch_size)
- Validation on test set

**Implementation:**
```bash
python scripts/train_intent_classifier.py \
  --data data/intent_training_v1.json \
  --base-model BAAI/bge-m3 \
  --output models/intent_classifier_v1 \
  --iterations 20 \
  --batch-size 16

# Validate
python scripts/validate_intent_model.py \
  --model models/intent_classifier_v1 \
  --test-data data/intent_test.json

# Target: 85-92% accuracy on test set
```

**Acceptance Criteria:**
- [ ] SetFit model trained
- [ ] Validation accuracy ≥85%
- [ ] Model exported to models/intent_classifier_v1
- [ ] Latency: P95 ≤100ms

---

### Feature 67.12: C-LARA Integration (5 SP)

**Priority:** P1
**Ziel:** Replace Semantic Router with fine-tuned SetFit

**Scope:**
- Update `src/components/retrieval/intent_classifier.py`
- Load fine-tuned model instead of raw BGE-M3
- Add confidence threshold (≥0.80)
- Optional: LLM fallback for low-confidence cases
- Logging & Metrics

**Implementation:**
```python
from setfit import SetFitModel

class LLMTrainedIntentClassifier:
    def __init__(self):
        self.model = SetFitModel.from_pretrained("models/intent_classifier_v1")
        self.intent_mapping = {
            0: Intent.FACTUAL,
            1: Intent.KEYWORD,
            2: Intent.EXPLORATORY,
            3: Intent.SUMMARY
        }

    async def classify(self, query: str) -> tuple[Intent, float]:
        # Single inference, ~50-100ms
        probs = self.model.predict_proba([query])[0]
        best_idx = np.argmax(probs)
        confidence = float(probs[best_idx])
        intent = self.intent_mapping[best_idx]

        # Low confidence → LLM fallback (optional)
        if confidence < 0.80:
            intent, confidence = await self._llm_few_shot_classify(query)

        return intent, confidence
```

**Acceptance Criteria:**
- [ ] IntentClassifier updated
- [ ] Model loading functional
- [ ] Confidence threshold implemented
- [ ] LLM fallback optional
- [ ] Metrics logged (intent, confidence, latency)

---

### Feature 67.13: C-LARA A/B Testing (2 SP)

**Priority:** P2
**Ziel:** Empirical validation on production queries

**Scope:**
- Deploy both classifiers (Semantic Router vs SetFit)
- Log results with request_id
- Compare accuracy, latency, user satisfaction
- Duration: 1 week
- Metrics: Accuracy, Confidence, Margin

**Implementation:**
```python
# A/B Test
if random.random() < 0.5:
    intent_v1, conf_v1 = semantic_router.classify(query)
    log_intent(request_id, "v1_semantic_router", intent_v1, conf_v1)
else:
    intent_v2, conf_v2 = setfit_classifier.classify(query)
    log_intent(request_id, "v2_setfit", intent_v2, conf_v2)

# After 1 week:
# Compare: accuracy, avg_confidence, avg_margin
# Expected: v2 (SetFit) > v1 (Semantic Router) by +25-32 percentage points
```

**Acceptance Criteria:**
- [ ] A/B test deployed
- [ ] 1 week data collection
- [ ] Comparison report generated
- [ ] Decision: Deploy SetFit if accuracy >85%

---

## Parallel Execution Strategy

### Wave 1 (Tag 1-3): Sandbox Foundation
- **Team A (Backend):** 67.1 BubblewrapSandboxBackend (5 SP)
- **Team B (API):** 67.5 Unified Trace & Telemetry (8 SP)
- **Team C (Testing):** 67.10 C-LARA Data Generation (3 SP)

### Wave 2 (Tag 4-6): Agent Integration & Eval
- **Team A:** 67.2 deepagents Integration (4 SP)
- **Team B:** 67.6 Eval Harness (10 SP)
- **Team C:** 67.11 C-LARA Model Training (3 SP)

### Wave 3 (Tag 7-9): Multi-Language & Datasets
- **Team A:** 67.3 Multi-Language CodeAct (3 SP)
- **Team B:** 67.7 Dataset Builder (8 SP)
- **Team C:** 67.12 C-LARA Integration (5 SP)

### Wave 4 (Tag 10-12): Adaptive Tools & Testing
- **Team A:** 67.4 Sandbox Testing (3 SP)
- **Team B:** 67.8 Adaptive Reranker v1 (13 SP) - parallel start in Wave 3
- **Team C:** 67.9 Query Rewriter v1 (10 SP) - parallel start in Wave 3
- **Team D:** 67.13 C-LARA A/B Testing (2 SP)

**Parallelization:**
- Wave 1-2: 3 teams = 13 + 17 = 30 SP in 6 days
- Wave 3-4: 4 teams = 21 + 28 = 49 SP in 6 days
- **Total Duration: 12 days** (with some overlap)

---

## Definition of Done

**Sandbox (Epic 1):**
- [ ] BubblewrapSandboxBackend erfüllt SandboxBackendProtocol
- [ ] Agent läuft mit deepagents auf DGX Spark
- [ ] Multi-Language CodeAct funktional (Bash + Python)
- [ ] Security-Tests bestanden (kein Sandbox-Escape)
- [ ] Performance: <200ms Overhead pro Command
- [ ] ADR-067 dokumentiert

**Adaptation (Epic 2):**
- [ ] Unified Trace & Telemetry produktiv
- [ ] Eval Harness mit 3 Suites (Canary/Regression/Stress)
- [ ] Dataset Builder erzeugt Rerank + Rewrite Daten
- [ ] Adaptive Reranker v1: +5-10% retrieval_hit@k
- [ ] Query Rewriter v1: +5-10% recall

**Intent Classifier (Epic 3):**
- [ ] 1000 synthetic examples generiert
- [ ] SetFit model trainiert (≥85% accuracy)
- [ ] Integration in production
- [ ] A/B Test: SetFit > Semantic Router

---

## Risiken & Mitigationen

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Bubblewrap ARM64-Kompatibilität | Medium | High | Frühzeitig auf DGX Spark testen (Wave 1, Day 1) |
| deepagents API-Änderungen | Low | Medium | Version pinnen (>=0.2.0), Changelog monitoren |
| Tool-Adaptation Overfitting | Medium | Medium | Separate Canary/Regression Splits, zeitbasierte Holdouts |
| LLM Data Generation Quality | Medium | High | Human validation (10% sample), iterative refinement |
| Performance Regression | Low | High | Eval-Gates in CI/CD, Canary deployment |

---

## Success Criteria

**Quantitative:**
- [ ] Intent Classifier: 60% → 85-92% accuracy
- [ ] Reranker: +5-10% retrieval_hit@k vs baseline
- [ ] Query Rewriter: +5-10% recall vs baseline
- [ ] Sandbox Overhead: <200ms per command
- [ ] E2E Latency: No regression (P95 ≤500ms)

**Qualitative:**
- [ ] Traces sind reproduzierbar & auditierbar
- [ ] Eval-Gates verhindern silent regressions
- [ ] Datasets sind versioniert & PII-free
- [ ] Agent ist LLM-agnostisch (Ollama ↔ Anthropic ↔ OpenAI)
- [ ] Dokumentation vollständig (ADRs, User Guides, API Refs)

---

## Abhängigkeiten

### Python Packages
```toml
# pyproject.toml - New Dependencies
[tool.poetry.dependencies]
deepagents = ">=0.2.0"           # Agent Harness
langgraph = ">=0.4.5"            # Graph Orchestration
langgraph-codeact = ">=0.1.3"    # Code Execution
langchain-sandbox = ">=0.0.5"    # Pyodide Sandbox
langchain-anthropic = ">=0.3.9"  # Optional: Anthropic Models
langchain-openai = ">=0.3.0"     # Optional: OpenAI Models
setfit = ">=1.0.0"               # SetFit for Intent/Reranker
sentence-transformers = ">=2.2.0" # Embeddings
networkx = ">=3.0"               # Graph algorithms (for Rewriter)
```

### System Dependencies
```bash
# DGX Spark (ARM64)
sudo apt-get install bubblewrap  # Sandbox isolation
```

---

## Referenzen

### Papers
- [Paper 2512.16301: Tool-Level LLM Adaptation](https://arxiv.org/abs/2512.16301)
- [C-LARA Framework: Intent Detection in the Age of LLMs](https://www.amazon.science/publications/intent-detection-in-the-age-of-llms)

### LangChain/LangGraph
- [deepagents GitHub](https://github.com/langchain-ai/deepagents)
- [deepagents Backends Docs](https://docs.langchain.com/oss/python/deepagents/backends)
- [langgraph-codeact GitHub](https://github.com/langchain-ai/langgraph-codeact)
- [langchain-sandbox GitHub](https://github.com/langchain-ai/langchain-sandbox)

### Anthropic Engineering
- [Writing Tools for Agents](https://www.anthropic.com/engineering/writing-tools-for-agents)
- [Claude Code Sandboxing](https://www.anthropic.com/engineering/claude-code-sandboxing)
- [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)

### Related Sprints & ADRs
- [SPRINT_66_PLAN.md](SPRINT_66_PLAN.md) - E2E Test Stabilization
- [SPRINT_SECURE_SHELL_SANDBOX_v3.md](SPRINT_SECURE_SHELL_SANDBOX_v3.md) - Detailed Sandbox Design
- [SPRINT_AGENTS_ADAPTATION.md](SPRINT_AGENTS_ADAPTATION.md) - Adaptation Framework
- [ADR-024: BGE-M3 Embeddings](../adr/ADR_INDEX.md)
- [TD-075: LLM Intent Classifier (C-LARA)](../technical-debt/TD-075_LLM_INTENT_CLASSIFIER_CLARA.md)

---

**END OF SPRINT 67 PLAN**
