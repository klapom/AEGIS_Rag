# Sprint 79: RAGAS 0.4 Evaluation + Optional DSPy Optimization + Frontend UI

**Status:** 🟡 Planned
**Sprint Dauer:** 2026-01-08 bis 2026-01-12 (5 Tage)
**Story Points:** 31 SP (2 SP RAGAS Upgrade + 21 SP DSPy [CONDITIONAL] + 8 SP Frontend UI)
**Assignee:** Claude + Team

---

## Sprint Ziele

**Primär (PHASE 1):** Upgrade auf RAGAS 0.4.2 und Prüfung ob neue Framework-Features (GPT-5/o-Series Support, Universal Provider) die Timeout-Probleme bereits beheben.

**Sekundär (PHASE 2 - CONDITIONAL):** NUR wenn RAGAS 0.4.2 Timeouts nicht behebt → DSPy Prompt-Optimierung für lokale LLMs (GPT-OSS:20b, Nemotron3 Nano).

**Tertiär:** Vervollständigung der Frontend UI für Sprint 76-78 Backend-Features (Graph Expansion Settings aus Sprint 78, Community Summarization aus Sprint 77).

---

## Problem Statement

**Aktueller Zustand (Sprint 78 mit RAGAS 0.3.9):**
- RAGAS Context Precision: 85.76s pro Evaluation (GPT-OSS:20b)
- Nemotron3 Nano: >600s pro Evaluation (11m26s für simple Yes/No)
- 15 Evaluationen (3 Fragen × 5 Kontexte): 1286s → **Timeout bei 300s**
- Few-Shot Prompts (2903 chars) zu komplex für lokale Modelle

**Root Cause Analysis:**
1. **RAGAS 0.3.9 Prompts:** 3 vollständige Few-Shot Beispiele (2903 chars)
2. **Lokale Inference:** Ollama 10-100x langsamer als Cloud APIs
3. **Kleine Modelle:** Nemotron Nano extrem langsam trotz weniger Parameter

**Solution Strategy (2-Phase Approach):**
1. **PHASE 1 (Feature 79.8):** Upgrade RAGAS 0.3.9 → 0.4.2
   - Neue Features: GPT-5/o-Series Support, Universal Provider, Function-Based Prompts
   - Hypothese: Optimierte Prompts in 0.4.x könnten Timeouts bereits beheben
   - **Entscheidungspunkt:** Wenn Timeouts behoben → Skip Phase 2 (21 SP gespart)

2. **PHASE 2 (Features 79.1-79.5 - CONDITIONAL):** DSPy Optimization
   - Nur ausführen wenn RAGAS 0.4.2 Timeouts NICHT behebt
   - Ziel: <20s pro Evaluation (4x schneller als GPT-OSS:20b)
   - Methode: BootstrapFewShot + MIPROv2 Prompt-Kompression

---

## Features

### Feature 79.8: RAGAS 0.4.2 Upgrade & Performance Evaluation (2 SP) 🎯 **PHASE 1 - FIRST**

**Beschreibung:**
Upgrade von RAGAS 0.3.9 auf RAGAS 0.4.2 mit API-Migration und Performance-Evaluierung. Prüfung ob neue Framework-Features die Timeout-Probleme beheben, bevor DSPy-Optimierung gestartet wird.

**RAGAS 0.4.2 Breaking Changes:**
1. **API-Änderungen:**
   ```python
   # OLD (0.3.9)
   from ragas.metrics import context_precision
   sample = SingleTurnSample(
       user_input="question",
       response="answer",
       ground_truths=["correct answer"]  # List
   )

   # NEW (0.4.2)
   sample = SingleTurnSample(
       user_input="question",
       response="answer",
       reference="correct answer"  # String
   )
   result = await metric.ascore(sample)
   score = result.value  # Access score via .value
   ```

2. **Entfernte Features:**
   - `AspectCritic` (kein Ersatz)
   - `SimpleCriteriaScore` (kein Ersatz)
   - `instructor_llm_factory()` → `llm_factory()`

**Neue Features in 0.4.2:**
- **GPT-5 & o-Series Support:** Automatisches Constraint Handling für neueste OpenAI-Modelle
- **Universal Provider Support:** Ein `llm_factory()` für alle Provider (Anthropic, Google, Azure, Ollama)
- **Function-Based Prompts:** Flexiblere Prompt-Definitionen
- **Metric Decorators:** `@discrete_metric`, `@numeric_metric`, `@ranking_metric`
- **Experiment-Based Architecture:** Bessere Integration von Evaluation & Iteration

**Implementierung:**
1. **Dependency Update:**
   ```bash
   poetry add ragas@^0.4.2
   poetry lock --no-update
   poetry install
   ```

2. **Code Migration (`scripts/run_ragas_evaluation.py`):**
   - Update `SingleTurnSample` API (`ground_truths` → `reference`)
   - Update metric score access (`result.value`)
   - Update `llm_factory()` calls

3. **Performance Baseline (CRITICAL):**
   ```python
   # Test with RAGAS 0.4.2 on same dataset (15 HotpotQA contexts)
   import time
   from ragas.metrics import context_precision

   start = time.time()
   results = []
   for sample in test_samples:
       result = await context_precision.ascore(sample)
       results.append(result.value)
   elapsed = time.time() - start

   print(f"RAGAS 0.4.2 Performance:")
   print(f"  Total: {elapsed:.2f}s")
   print(f"  Avg per eval: {elapsed/len(test_samples):.2f}s")
   print(f"  Baseline (0.3.9): 85.76s per eval")
   print(f"  Speedup: {85.76 / (elapsed/len(test_samples)):.2f}x")
   ```

**Acceptance Criteria:**
- [ ] RAGAS 0.4.2 installiert (`poetry show ragas | grep version`)
- [ ] `scripts/run_ragas_evaluation.py` migriert (alle Tests passing)
- [ ] Performance Baseline erstellt (15 Evaluationen durchgeführt)
- [ ] **Entscheidung dokumentiert:** Timeouts behoben JA/NEIN
- [ ] **IF Timeouts behoben:** Features 79.1-79.5 als "SKIPPED" markieren
- [ ] **IF Timeouts NICHT behoben:** Features 79.1-79.5 starten

**Performance Hypothesis:**
- **Optimistisch:** RAGAS 0.4.2 Universal Provider + Function-Based Prompts → 2-3x Speedup → <30s/eval → Timeouts behoben
- **Pessimistisch:** Keine wesentliche Verbesserung → Weiter mit DSPy (Features 79.1-79.5)

**Risiken:**
- Breaking Changes könnten zusätzliche Code-Anpassungen erfordern
- Neue Bugs in RAGAS 0.4.2 (erst Oktober 2024 released)

---

### Feature 79.1: DSPy Integration für RAGAS (8 SP) 🔀 **PHASE 2 - CONDITIONAL**
**⚠️ CONDITIONAL: Nur ausführen wenn Feature 79.8 zeigt, dass RAGAS 0.4.2 Timeouts NICHT behebt**

**Beschreibung:**
Integration von DSPy (Stanford NLP) für automatische Prompt-Optimierung der RAGAS Metriken. DSPy optimiert Few-Shot Examples und Instruction-Wording für lokale Modelle.

**Technischer Ansatz:**
```python
import dspy

# Define RAGAS Context Precision as DSPy Signature
class ContextPrecisionSignature(dspy.Signature):
    """Verify if context was useful in arriving at the answer."""
    question: str = dspy.InputField()
    context: str = dspy.InputField()
    answer: str = dspy.InputField()
    reason: str = dspy.OutputField(desc="Reason for verdict")
    verdict: int = dspy.OutputField(desc="Binary verdict (0/1)")

# Compile optimized prompt with DSPy
class OptimizedContextPrecision(dspy.Module):
    def __init__(self):
        super().__init__()
        self.prog = dspy.ChainOfThought(ContextPrecisionSignature)

    def forward(self, question, context, answer):
        return self.prog(question=question, context=context, answer=answer)

# Train/optimize with BootstrapFewShot
optimizer = dspy.BootstrapFewShot(
    metric=verdict_accuracy,
    max_bootstrapped_demos=2,  # Reduce from 3 to 2
    max_labeled_demos=4,
)
optimized_prog = optimizer.compile(OptimizedContextPrecision(), trainset=ragas_examples)
```

**Implementierung:**
- `src/evaluation/dspy_ragas/` - Neues Modul
  - `__init__.py`
  - `signatures.py` - DSPy Signatures für alle 4 RAGAS Metriken
  - `optimizers.py` - Prompt Optimizer (BootstrapFewShot, MIPROv2)
  - `compiled_metrics.py` - Optimierte Metriken
- `src/evaluation/dspy_ragas/training/` - Training Data
  - `context_precision_examples.json` - 20 gelabelte Beispiele
  - `context_recall_examples.json`
  - `faithfulness_examples.json`
  - `answer_relevancy_examples.json`

**Acceptance Criteria:**
- [ ] DSPy installiert und konfiguriert (`poetry add dspy-ai`)
- [ ] 4 DSPy Signatures für RAGAS Metriken definiert
- [ ] Optimizer mit 20 Trainingsbeispielen pro Metrik
- [ ] Compiled Prompts gespeichert in `data/dspy_cache/`
- [ ] Unit Tests für optimierte Metriken

**Technische Details:**
- DSPy Version: 2.5+
- LM Backend: Ollama (gpt-oss:20b, nemotron-3-nano)
- Optimizer: BootstrapFewShot (schnell) + MIPROv2 (präzise)
- Training Set: 20 Beispiele pro Metrik (aus RAGAS Dokumentation)

**Risiken:**
- DSPy braucht auch Zeit für Optimierung (einmalig)
- Qualitätsverlust durch Prompt-Kompression möglich

---

### Feature 79.2: Optimierte Context Precision für GPT-OSS:20b (5 SP) 🔀 **PHASE 2 - CONDITIONAL**
**⚠️ CONDITIONAL: Nur ausführen wenn Feature 79.8 zeigt, dass RAGAS 0.4.2 Timeouts NICHT behebt**

**Beschreibung:**
Optimierung der Context Precision Metrik mit DSPy speziell für GPT-OSS:20b. Ziel: <20s pro Evaluation (aktuell 85.76s).

**Optimierungen:**
1. **Few-Shot Reduction**: 3 Examples → 1-2 Examples
2. **Prompt Compression**: 2903 chars → ~1000 chars
3. **Chain-of-Thought Optimization**: Kürzere Reasoning Chains
4. **Output Format**: Simplified JSON (nur `verdict`, ohne `reason`)

**Baseline Messung:**
```
Current: 85.76s per evaluation (2903 chars, 3 examples, full reasoning)
Target:  <20s per evaluation (~1000 chars, 1-2 examples, simplified)
```

**Implementierung:**
```python
# src/evaluation/dspy_ragas/compiled_metrics.py
@dataclass
class OptimizedContextPrecisionGPTOSS:
    """Optimized for GPT-OSS:20b via DSPy."""

    compiled_program: dspy.Module
    prompt_length: int  # Target: ~1000 chars
    avg_inference_time_s: float  # Target: <20s

    async def evaluate(self, question: str, context: str, answer: str) -> dict:
        start = time.time()
        result = self.compiled_program(
            question=question,
            context=context,
            answer=answer
        )
        elapsed = time.time() - start

        return {
            "verdict": result.verdict,
            "inference_time_s": elapsed,
            "prompt_tokens": self.prompt_length,
        }
```

**Acceptance Criteria:**
- [ ] DSPy Optimizer trainiert mit 20 Beispielen
- [ ] Prompt-Länge <1200 chars (Reduktion 60%)
- [ ] Inference-Zeit <20s pro Evaluation (75% schneller)
- [ ] Accuracy ≥90% vs. Original RAGAS
- [ ] Benchmarking mit 30 Test-Samples

---

### Feature 79.3: Optimierte Metrics für Nemotron3 Nano (5 SP) 🔀 **PHASE 2 - CONDITIONAL**
**⚠️ CONDITIONAL: Nur ausführen wenn Feature 79.8 zeigt, dass RAGAS 0.4.2 Timeouts NICHT behebt**

**Beschreibung:**
Spezielle Prompt-Optimierung für Nemotron3 Nano (extrem kleine Modell). Fokus auf Zero-Shot oder 1-Shot statt Few-Shot.

**Challenge:**
Nemotron3 Nano braucht 686s für "Is the sky blue?" → Extrem langsam bei Few-Shot.

**Optimierungen:**
1. **Zero-Shot first**: Keine Examples, nur Instruction
2. **Minimaler Prompt**: <500 chars
3. **Binary Output**: Nur `0` oder `1`, kein JSON, kein Reasoning
4. **Optimierte Instruction**: DSPy findet kürzeste effektive Formulierung

**Baseline:**
```
Current: >600s per evaluation (2903 chars, 3 examples)
Target:  <60s per evaluation (<500 chars, 0 examples)
```

**DSPy Optimizer Config:**
```python
# Für Nemotron: Fokus auf Prompt-Länge Reduktion
optimizer = dspy.MIPROv2(
    metric=verdict_accuracy,
    num_candidates=10,
    init_temperature=1.0,
    prompt_model=dspy.OllamaLocal(model="gpt-oss:20b"),  # Verwende größeres Modell für Optimization
    task_model=dspy.OllamaLocal(model="nemotron-3-nano"),  # Target: Nemotron
)
```

**Acceptance Criteria:**
- [ ] Zero-Shot Prompt <500 chars
- [ ] Inference <60s pro Evaluation (10x Verbesserung)
- [ ] Accuracy ≥80% (niedrigere Erwartung für kleines Modell)
- [ ] Funktionierender RAGAS Run ohne Timeouts

---

### Feature 79.4: Performance Benchmarking (2 SP) 🔀 **PHASE 2 - CONDITIONAL**
**⚠️ CONDITIONAL: Nur ausführen wenn Feature 79.8 zeigt, dass RAGAS 0.4.2 Timeouts NICHT behebt**

**Beschreibung:**
Systematisches Benchmarking der optimierten Prompts vs. Original RAGAS.

**Metriken:**
1. **Inference Time** (Hauptmetrik)
   - Original RAGAS vs. DSPy Optimized
   - GPT-OSS:20b vs. Nemotron3 Nano
2. **Accuracy** (Qualität)
   - Verdict Accuracy (Binary Match)
   - Reasoning Quality (Human Evaluation, 10 Samples)
3. **Prompt Efficiency**
   - Chars per Prompt
   - Tokens per Prompt
   - Few-Shot Examples Count

**Benchmark Suite:**
```bash
scripts/benchmark_dspy_ragas.py \
  --models gpt-oss:20b,nemotron-3-nano \
  --metrics context_precision,context_recall,faithfulness,answer_relevancy \
  --test-samples 30 \
  --output-dir data/benchmarks/sprint79/
```

**Output:**
```
╔════════════════════════════════════════════════════════════════╗
║  RAGAS DSPy Optimization Benchmark Results                     ║
╠════════════════════════════════════════════════════════════════╣
║ Model: GPT-OSS:20b                                             ║
║ Metric: Context Precision                                      ║
║                                                                ║
║ Original RAGAS:                                                ║
║   - Avg Inference Time: 85.76s                                 ║
║   - Prompt Length: 2903 chars                                  ║
║   - Accuracy: 95%                                              ║
║                                                                ║
║ DSPy Optimized:                                                ║
║   - Avg Inference Time: 18.42s (78% faster ✅)                 ║
║   - Prompt Length: 987 chars (66% shorter)                     ║
║   - Accuracy: 92% (3% drop, acceptable)                        ║
║                                                                ║
║ Verdict: ✅ PASSED (4.6x speedup, <5% accuracy loss)           ║
╚════════════════════════════════════════════════════════════════╝
```

**Acceptance Criteria:**
- [ ] Benchmark Script implementiert
- [ ] 30 Test Samples (aus Amnesty QA Dataset)
- [ ] Vergleich Original vs. Optimized für beide Modelle
- [ ] HTML Report generiert (`data/benchmarks/sprint79/report.html`)

---

### Feature 79.5: RAGAS Evaluation mit optimierten Prompts (1 SP) 🔀 **PHASE 2 - CONDITIONAL**
**⚠️ CONDITIONAL: Nur ausführen wenn Feature 79.8 zeigt, dass RAGAS 0.4.2 Timeouts NICHT behebt**

**Beschreibung:**
Finale RAGAS Evaluation mit DSPy-optimierten Prompts auf dem Amnesty QA Dataset (3 Fragen, 15 Kontexte).

**Execution:**
```bash
poetry run python scripts/run_ragas_evaluation.py \
  --namespace amnesty_qa \
  --mode graph \
  --dataset data/amnesty_qa_contexts/ragas_amnesty_tiny.jsonl \
  --output-dir data/evaluation/results \
  --use-dspy-optimized \
  --llm gpt-oss:20b \
  --max-questions 3
```

**Expected Results:**
```
================================================================================
RAGAS EVALUATION - Sprint 79 (DSPy Optimized)
================================================================================
Dataset: amnesty_qa (3 questions, 15 contexts)
Mode: graph
LLM: gpt-oss:20b (DSPy Optimized Prompts)

Query Phase: 3/3 questions (38s total)
Metrics Phase: 48/48 evaluations (4m 26s total) ✅ NO TIMEOUTS

RAGAS METRICS:
┌─────────────────────┬──────────┬──────────┬──────────┐
│ Metric              │ Score    │ Avg Time │ Accuracy │
├─────────────────────┼──────────┼──────────┼──────────┤
│ Context Precision   │ 0.7234   │ 17.2s    │ 91%      │
│ Context Recall      │ 0.8123   │ 16.8s    │ 89%      │
│ Faithfulness        │ 0.8901   │ 19.4s    │ 93%      │
│ Answer Relevancy    │ 0.9012   │ 18.1s    │ 94%      │
└─────────────────────┴──────────┴──────────┴──────────┘

Total Time: 4m 26s (Original: 21+ minutes)
Speedup: 4.7x faster ✅
```

**Acceptance Criteria:**
- [ ] RAGAS läuft ohne Timeouts (300s Limit)
- [ ] Alle 4 Metriken vollständig
- [ ] Ergebnisse vergleichbar mit Cloud APIs (±10%)
- [ ] Gespeichert in `data/evaluation/results/sprint79_dspy_optimized.json`

---

### Feature 79.6: Frontend UI für Graph Expansion Settings (5 SP) 🎯 **Sprint 78 Follow-Up**

**Beschreibung:**
Frontend UI für die 4 neuen Graph-Expansion-Einstellungen aus Sprint 78 Feature 78.5. Ermöglicht Admin-Usern die UI-basierte Konfiguration der 3-Stage Entity Expansion Pipeline.

**Problem Statement:**
Sprint 78 implementierte 4 Backend-Settings für semantische Graph-Suche, aber keine Frontend UI:
- `graph_expansion_hops` (1-3): Tiefe der Graph-Traversierung
- `graph_min_entities_threshold` (5-20): Schwellwert für LLM Synonym-Fallback
- `graph_max_synonyms_per_entity` (1-5): Max. Synonyme pro Entity
- `graph_semantic_reranking_enabled` (bool): BGE-M3 Reranking aktivieren

Aktuell nur via `.env` Datei konfigurierbar → Schlechte UX für Admins!

**Technische Lösung:**

**1. Frontend Component (`frontend/src/components/admin/GraphExpansionSettings.tsx`):**
```tsx
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Settings as SettingsIcon } from "lucide-react";

interface GraphExpansionSettings {
  graph_expansion_hops: number;              // 1-3
  graph_min_entities_threshold: number;       // 5-20
  graph_max_synonyms_per_entity: number;      // 1-5
  graph_semantic_reranking_enabled: boolean;
}

export function GraphExpansionSettingsCard() {
  const [settings, setSettings] = useState<GraphExpansionSettings>({
    graph_expansion_hops: 1,
    graph_min_entities_threshold: 10,
    graph_max_synonyms_per_entity: 3,
    graph_semantic_reranking_enabled: true,
  });

  const handleSave = async () => {
    await fetch("/api/v1/admin/graph/expansion/config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <SettingsIcon className="h-5 w-5" />
          Graph Entity Expansion Settings
          <Badge variant="outline">Sprint 78</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Graph Expansion Hops */}
        <div className="space-y-2">
          <div className="flex justify-between">
            <Label>Graph Expansion Hops</Label>
            <span className="text-sm text-muted-foreground">
              {settings.graph_expansion_hops} hop{settings.graph_expansion_hops > 1 ? "s" : ""}
            </span>
          </div>
          <Slider
            min={1}
            max={3}
            step={1}
            value={[settings.graph_expansion_hops]}
            onValueChange={(v) => setSettings({ ...settings, graph_expansion_hops: v[0] })}
          />
          <p className="text-xs text-muted-foreground">
            Controls depth of graph traversal (1-3 hops). Higher values = more related entities, but slower.
          </p>
        </div>

        {/* Min Entities Threshold */}
        <div className="space-y-2">
          <div className="flex justify-between">
            <Label>Min Entities Threshold</Label>
            <span className="text-sm text-muted-foreground">{settings.graph_min_entities_threshold}</span>
          </div>
          <Slider
            min={5}
            max={20}
            step={1}
            value={[settings.graph_min_entities_threshold]}
            onValueChange={(v) => setSettings({ ...settings, graph_min_entities_threshold: v[0] })}
          />
          <p className="text-xs text-muted-foreground">
            Minimum entities before LLM synonym fallback. Lower = more LLM calls (slower, better recall).
          </p>
        </div>

        {/* Max Synonyms Per Entity */}
        <div className="space-y-2">
          <div className="flex justify-between">
            <Label>Max Synonyms Per Entity</Label>
            <span className="text-sm text-muted-foreground">{settings.graph_max_synonyms_per_entity}</span>
          </div>
          <Slider
            min={1}
            max={5}
            step={1}
            value={[settings.graph_max_synonyms_per_entity]}
            onValueChange={(v) => setSettings({ ...settings, graph_max_synonyms_per_entity: v[0] })}
          />
          <p className="text-xs text-muted-foreground">
            Maximum LLM-generated synonyms per entity (1-5). Higher = better recall, risk of semantic drift.
          </p>
        </div>

        {/* Semantic Reranking Toggle */}
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label>Semantic Reranking (BGE-M3)</Label>
            <p className="text-xs text-muted-foreground">
              Rerank expanded entities by semantic similarity to query (GPU-accelerated).
            </p>
          </div>
          <Switch
            checked={settings.graph_semantic_reranking_enabled}
            onCheckedChange={(checked) =>
              setSettings({ ...settings, graph_semantic_reranking_enabled: checked })
            }
          />
        </div>

        {/* Save Button */}
        <Button onClick={handleSave} className="w-full">
          Save Graph Expansion Settings
        </Button>
      </CardContent>
    </Card>
  );
}
```

**2. Backend API Endpoint (`src/api/v1/admin_graph.py`):**
```python
@router.get(
    "/graph/expansion/config",
    response_model=GraphExpansionConfigResponse,
    summary="Get graph expansion configuration",
)
async def get_graph_expansion_config() -> GraphExpansionConfigResponse:
    """Get current graph expansion settings from config."""
    from src.core.config import settings

    return GraphExpansionConfigResponse(
        graph_expansion_hops=settings.graph_expansion_hops,
        graph_min_entities_threshold=settings.graph_min_entities_threshold,
        graph_max_synonyms_per_entity=settings.graph_max_synonyms_per_entity,
        graph_semantic_reranking_enabled=settings.graph_semantic_reranking_enabled,
    )


@router.put(
    "/graph/expansion/config",
    response_model=GraphExpansionConfigResponse,
    summary="Update graph expansion configuration",
)
async def update_graph_expansion_config(
    config: GraphExpansionConfigRequest,
) -> GraphExpansionConfigResponse:
    """Update graph expansion settings (persisted to Redis)."""
    from src.core.config import settings

    # Update settings (will be persisted via Redis config backend)
    settings.graph_expansion_hops = config.graph_expansion_hops
    settings.graph_min_entities_threshold = config.graph_min_entities_threshold
    settings.graph_max_synonyms_per_entity = config.graph_max_synonyms_per_entity
    settings.graph_semantic_reranking_enabled = config.graph_semantic_reranking_enabled

    # Persist to Redis (similar to LLM config persistence from Sprint 64)
    await persist_settings_to_redis(settings)

    logger.info(
        "graph_expansion_config_updated",
        hops=config.graph_expansion_hops,
        threshold=config.graph_min_entities_threshold,
        synonyms=config.graph_max_synonyms_per_entity,
        reranking=config.graph_semantic_reranking_enabled,
    )

    return GraphExpansionConfigResponse(**config.model_dump())
```

**3. Integration in Advanced Settings Page:**
```tsx
// frontend/src/pages/admin/AdvancedSettingsPage.tsx
import { GraphExpansionSettingsCard } from "@/components/admin/GraphExpansionSettings";

export function AdvancedSettingsPage() {
  return (
    <div className="space-y-6 p-6">
      <h1>Advanced Settings</h1>

      {/* Existing Settings */}
      <LLMConfigCard />
      <RetrievalMethodCard />

      {/* NEW: Graph Expansion Settings (Sprint 79) */}
      <GraphExpansionSettingsCard />
    </div>
  );
}
```

**Acceptance Criteria:**
- [ ] 4 Sliders/Switches implementiert (hops, threshold, synonyms, reranking)
- [ ] GET /api/v1/admin/graph/expansion/config funktioniert
- [ ] PUT /api/v1/admin/graph/expansion/config funktioniert
- [ ] Werte in Redis persistiert (ähnlich LLM Config Sprint 64)
- [ ] UI zeigt aktuelle Werte beim Laden
- [ ] Validierung: hops ∈ [1,3], threshold ∈ [5,20], synonyms ∈ [1,5]
- [ ] Toast-Notification bei erfolgreicher Speicherung
- [ ] 5 E2E Tests (Playwright): Load, Update, Persist, Validation, Reset

**Effort:** 5 SP (3 SP Frontend + 2 SP Backend API)

---

### Feature 79.7: Admin Graph Operations UI (3 SP) 🎯 **Sprint 77 Follow-Up**

**Beschreibung:**
Frontend UI für Sprint 77 Community Summarization Batch Job (Feature 77.4). Ermöglicht Admin-Usern das Triggern der Community-Zusammenfassung via UI statt CLI Script.

**Problem Statement:**
Sprint 77.4 implementierte POST /api/v1/admin/graph/communities/summarize, aber kein UI Button:
- Aktuell nur via `scripts/generate_community_summaries.py` CLI Script
- Keine Progress-Anzeige in der UI
- Admin muss SSH + Terminal verwenden

**Technische Lösung:**

**1. Community Summarization Card (`frontend/src/components/admin/CommunitySummarizationCard.tsx`):**
```tsx
import { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, CheckCircle, Loader2, Sparkles } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface SummarizationStatus {
  status: "idle" | "running" | "complete" | "error";
  total_communities: number;
  summaries_generated: number;
  failed: number;
  total_time_s: number;
  avg_time_per_summary_s: number;
  message: string;
}

export function CommunitySummarizationCard() {
  const [status, setStatus] = useState<SummarizationStatus>({ status: "idle", total_communities: 0, ... });
  const { toast } = useToast();

  const handleSummarize = async () => {
    setStatus({ ...status, status: "running" });

    try {
      const response = await fetch("/api/v1/admin/graph/communities/summarize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          namespace: null,  // All namespaces
          force: false,     // Only missing summaries
          batch_size: 10,
        }),
      });

      const data = await response.json();

      setStatus({
        status: data.status === "complete" ? "complete" : "error",
        total_communities: data.total_communities,
        summaries_generated: data.summaries_generated,
        failed: data.failed,
        total_time_s: data.total_time_s,
        avg_time_per_summary_s: data.avg_time_per_summary_s,
        message: data.message,
      });

      toast({
        title: "Community Summarization Complete",
        description: data.message,
        variant: data.failed > 0 ? "warning" : "success",
      });
    } catch (error) {
      setStatus({ ...status, status: "error", message: error.message });
      toast({
        title: "Summarization Failed",
        description: error.message,
        variant: "destructive",
      });
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="h-5 w-5" />
          Community Summarization
          <Badge variant="outline">Sprint 77</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Generate LLM-powered summaries for all graph communities. Enables Graph-Global search mode (LightRAG).
        </p>

        {/* Status Display */}
        {status.status !== "idle" && (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              {status.status === "running" && <Loader2 className="h-4 w-4 animate-spin" />}
              {status.status === "complete" && <CheckCircle className="h-4 w-4 text-green-600" />}
              {status.status === "error" && <AlertCircle className="h-4 w-4 text-red-600" />}
              <span className="text-sm font-medium">{status.message}</span>
            </div>

            {status.total_communities > 0 && (
              <>
                <Progress value={(status.summaries_generated / status.total_communities) * 100} />
                <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                  <div>Total: {status.total_communities}</div>
                  <div>Generated: {status.summaries_generated}</div>
                  <div>Failed: {status.failed}</div>
                  <div>Time: {status.total_time_s.toFixed(1)}s</div>
                </div>
              </>
            )}
          </div>
        )}
      </CardContent>
      <CardFooter>
        <Button
          onClick={handleSummarize}
          disabled={status.status === "running"}
          className="w-full"
        >
          {status.status === "running" ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Generating Summaries...
            </>
          ) : (
            <>
              <Sparkles className="mr-2 h-4 w-4" />
              Generate Community Summaries
            </>
          )}
        </Button>
      </CardFooter>
    </Card>
  );
}
```

**2. Integration in Graph Analytics Page:**
```tsx
// frontend/src/pages/admin/GraphAnalyticsPage.tsx
import { CommunitySummarizationCard } from "@/components/admin/CommunitySummarizationCard";

export function GraphAnalyticsPage() {
  return (
    <div className="space-y-6 p-6">
      <h1>Graph Analytics</h1>

      {/* Existing Cards */}
      <GraphStatsCard />
      <EntityDistributionCard />

      {/* NEW: Community Summarization (Sprint 79) */}
      <CommunitySummarizationCard />
    </div>
  );
}
```

**Acceptance Criteria:**
- [ ] Button triggert POST /api/v1/admin/graph/communities/summarize
- [ ] Progress-Anzeige während Batch-Job läuft
- [ ] Success/Error Toast-Notifications
- [ ] Statistiken anzeigen (total, generated, failed, time)
- [ ] Status-Badges (idle, running, complete, error)
- [ ] 3 E2E Tests (Playwright): Trigger, Progress, Complete

**Effort:** 3 SP (2 SP Frontend + 1 SP E2E Tests)

---

## Technische Anforderungen

### DSPy Setup

```bash
# Installation
poetry add dspy-ai

# Ollama Backend Config
export DSPY_CACHEDIR=data/dspy_cache/
export OLLAMA_BASE_URL=http://localhost:11434
```

### Trainingsdata Vorbereitung

```python
# data/dspy_training/context_precision_examples.json
[
    {
        "question": "What can you tell me about Albert Einstein?",
        "context": "Albert Einstein (14 March 1879 – 18 April 1955) was a German-born theoretical physicist...",
        "answer": "Albert Einstein was a German-born theoretical physicist who received the 1921 Nobel Prize...",
        "verdict": 1,
        "reason": "Context provides key biographical information reflected in answer"
    },
    # 19 weitere Beispiele...
]
```

### DSPy Optimizer Training

```python
# scripts/train_dspy_ragas_optimizers.py
import dspy
from src.evaluation.dspy_ragas.signatures import ContextPrecisionSignature
from src.evaluation.dspy_ragas.optimizers import train_optimizer

# 1. Load training examples
trainset = load_training_examples("data/dspy_training/context_precision_examples.json")

# 2. Configure LM
lm = dspy.OllamaLocal(model="gpt-oss:20b", base_url="http://localhost:11434")
dspy.settings.configure(lm=lm)

# 3. Train optimizer
optimizer = dspy.BootstrapFewShot(
    metric=verdict_accuracy,
    max_bootstrapped_demos=2,
    max_labeled_demos=4,
)

# 4. Compile program
program = dspy.ChainOfThought(ContextPrecisionSignature)
optimized_program = optimizer.compile(program, trainset=trainset)

# 5. Save compiled program
optimized_program.save("data/dspy_cache/context_precision_gptoss20b.json")
```

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/evaluation/test_dspy_ragas_optimized.py
class TestDSPyOptimizedContextPrecision:
    def test_inference_time_improvement(self):
        """Verify <20s inference for GPT-OSS:20b."""
        optimized = load_optimized_metric("context_precision", "gpt-oss:20b")

        start = time.time()
        result = optimized.evaluate(
            question="What is RAG?",
            context="RAG stands for Retrieval Augmented Generation...",
            answer="RAG is a technique combining retrieval and generation..."
        )
        elapsed = time.time() - start

        assert elapsed < 20.0, f"Too slow: {elapsed}s"
        assert result["verdict"] in [0, 1]

    def test_prompt_length_reduction(self):
        """Verify prompt compression to <1200 chars."""
        optimized = load_optimized_metric("context_precision", "gpt-oss:20b")
        prompt = optimized.get_compiled_prompt()

        assert len(prompt) < 1200, f"Prompt too long: {len(prompt)} chars"
```

### Integration Tests

```bash
# Test mit echtem Ollama
pytest tests/integration/test_dspy_ragas_integration.py -v

# Output:
test_context_precision_gptoss_performance PASSED (18.3s)
test_context_precision_nemotron_performance PASSED (52.1s)
test_ragas_eval_no_timeouts PASSED (4m 12s)
```

---

## Success Metrics

| Metric | Baseline (Sprint 78) | Target (Sprint 79) | Status |
|--------|---------------------|-------------------|--------|
| Context Precision Time (GPT-OSS) | 85.76s | <20s | 🎯 |
| Context Precision Time (Nemotron) | >600s | <60s | 🎯 |
| Prompt Length | 2903 chars | <1200 chars | 🎯 |
| Accuracy vs Original | 100% | ≥90% | 🎯 |
| Total RAGAS Time (3Q) | Timeout (>21m) | <5m | 🎯 |
| Few-Shot Examples | 3 | 1-2 | 🎯 |

---

## Deliverables

1. **Code:**
   - [ ] `src/evaluation/dspy_ragas/` Modul (6 Dateien)
   - [ ] `scripts/train_dspy_ragas_optimizers.py`
   - [ ] `scripts/benchmark_dspy_ragas.py`
   - [ ] 20 Unit Tests, 5 Integration Tests

2. **Data:**
   - [ ] `data/dspy_training/` - 80 Trainingsbeispiele (4 Metriken × 20)
   - [ ] `data/dspy_cache/` - 8 Compiled Programs (4 Metriken × 2 Modelle)
   - [ ] `data/benchmarks/sprint79/` - Benchmark Results

3. **Dokumentation:**
   - [ ] `docs/evaluation/DSPY_RAGAS_OPTIMIZATION.md`
   - [ ] ADR-041: DSPy for RAGAS Prompt Optimization
   - [ ] Update `docs/TECH_STACK.md` (DSPy 2.5+)

4. **Results:**
   - [ ] RAGAS Evaluation mit optimierten Prompts (JSON + HTML Report)
   - [ ] Performance Comparison Chart (Original vs. DSPy)

---

## Risiken & Mitigationen

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| DSPy Training dauert zu lange | Mittel | Hoch | Verwende BootstrapFewShot (schneller als MIPROv2) |
| Qualitätsverlust >10% | Mittel | Hoch | Iterative Optimierung mit mehr Trainingsbeispielen |
| Nemotron Nano bleibt zu langsam | Hoch | Mittel | Akzeptiere 60s statt 20s, dokumentiere Limitation |
| DSPy Ollama Integration Probleme | Niedrig | Mittel | Fallback: Manuelle Prompt Engineering |

---

## Dependencies

**Externe:**
- DSPy 2.5+ (`poetry add dspy-ai`)
- Ollama mit GPT-OSS:20b und Nemotron3 Nano
- 80 gelabelte Trainingsbeispiele (aus RAGAS Docs + eigene)

**Interne:**
- Sprint 78 abgeschlossen (Entity→Chunk Expansion funktioniert)
- RAGAS 0.3.9 installiert (wird auf 0.4.2 upgraded)
- Amnesty QA Dataset verfügbar

---

## Timeline

**Tag 1 (2026-01-08): PHASE 1 - RAGAS 0.4.2 Upgrade**
- Feature 79.8: RAGAS 0.4.2 Upgrade & Performance Evaluation (2 SP)
  - Dependency Update (`poetry add ragas@^0.4.2`)
  - API Migration (`scripts/run_ragas_evaluation.py`)
  - Performance Baseline (15 Evaluationen)
  - **ENTSCHEIDUNGSPUNKT:** Timeouts behoben JA/NEIN?

**CONDITIONAL - NUR wenn Feature 79.8 Timeouts NICHT behebt:**

**Tag 2-3 (2026-01-09 bis 2026-01-10): PHASE 2 - DSPy Optimization**
- Feature 79.1: DSPy Integration (Setup + Signatures)
- Trainingsdata Vorbereitung (20 Beispiele pro Metrik)
- Feature 79.2: GPT-OSS:20b Optimierung
- Feature 79.3: Nemotron3 Nano Optimierung
- Feature 79.4: Benchmarking
- Feature 79.5: RAGAS Evaluation

**Tag 2-3 (2026-01-09 bis 2026-01-10) ODER Tag 4-5 (2026-01-11 bis 2026-01-12): Frontend UI**
- Feature 79.6: Graph Expansion Settings UI (5 SP)
- Feature 79.7: Community Summarization UI (3 SP)
- E2E Tests (8 neue Tests: 5 + 3)
- Dokumentation
- Sprint Review

**Note:** Wenn Feature 79.8 erfolgreich (Timeouts behoben), dann:
- Tag 2-5: Nur Frontend UI (Features 79.6-79.7)
- Sprint endet nach Tag 3 (21 SP gespart)

---

## Sprint Review Criteria

**PHASE 1: RAGAS 0.4.2 Upgrade (Feature 79.8 - MANDATORY):**
- [ ] RAGAS 0.4.2 installiert und verifiziert
- [ ] `scripts/run_ragas_evaluation.py` API-Migration abgeschlossen
- [ ] Performance Baseline erstellt (15 Evaluationen)
- [ ] Entscheidung dokumentiert: Timeouts behoben JA/NEIN
- [ ] Unit Tests angepasst und passing

**PHASE 2: DSPy Optimization (Features 79.1-79.5 - CONDITIONAL):**
**⚠️ NUR ausführen wenn Feature 79.8 zeigt, dass RAGAS 0.4.2 Timeouts NICHT behebt**
- [ ] Alle 5 DSPy Features completed
- [ ] RAGAS läuft ohne Timeouts (<5 Minuten für 3 Fragen)
- [ ] Speedup ≥4x vs. RAGAS 0.3.9 Baseline (85.76s → <20s)
- [ ] Accuracy ≥90% vs. Original RAGAS
- [ ] Unit Tests: 20/20 passing
- [ ] Integration Tests: 5/5 passing
- [ ] DSPy cache artifacts gespeichert

**Frontend UI Completion (Features 79.6-79.7 - MANDATORY):**
- [ ] Graph Expansion Settings UI funktioniert (Feature 79.6)
- [ ] Community Summarization UI funktioniert (Feature 79.7)
- [ ] GET/PUT /api/v1/admin/graph/expansion/config implementiert
- [ ] Redis Persistence für Graph Settings funktioniert
- [ ] E2E Tests: 8/8 passing (5 Graph Settings + 3 Community Summarization)
- [ ] Toast-Notifications und Progress-Anzeigen funktionieren

**Dokumentation:**
- [ ] Dokumentation vollständig
- [ ] ADR-042: RAGAS 0.4.2 Upgrade erstellt (MANDATORY)
- [ ] ADR-043: DSPy RAGAS Optimization erstellt (CONDITIONAL - nur wenn Phase 2 ausgeführt)
- [ ] TECH_STACK.md mit RAGAS 0.4.2 aktualisiert
- [ ] TECH_STACK.md mit DSPy 2.5+ ergänzt (CONDITIONAL)

---

## Follow-up für Sprint 80

Nach erfolgreicher DSPy Optimierung:
- Feature 80.1: DSPy Optimization für andere LLMs (Llama 3.2, Qwen 2.5)
- Feature 80.2: Production RAGAS Integration (automatische Evaluation nach jedem Sprint)
- Feature 80.3: RAGAS Dashboard (Streamlit App für Metrik-Tracking)
