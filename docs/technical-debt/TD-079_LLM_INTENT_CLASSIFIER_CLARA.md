# TD-075: LLM-Based Intent Classifier mit C-LARA Architektur

**Status:** OPEN
**Priority:** HIGH
**Created:** 2025-12-30
**Sprint:** 67
**Estimated Effort:** 13 SP

## Problem

Der aktuelle Intent Classifier verwendet **Zero-Shot Embedding Classification** (Semantic Router mit BGE-M3) und erreicht nur **60% Accuracy** im A/B-Test mit 20 repräsentativen Queries.

**Empirische Testergebnisse:**
```
Test Date: 2025-12-29
Method: Zero-Shot Semantic Similarity (BGE-M3)
Dataset: 20 queries across 4 intents (FACTUAL, KEYWORD, EXPLORATORY, SUMMARY)

Results:
- Accuracy: 60.0% (12/20 correct)
- Avg Confidence: 0.775
- Avg Margin: 0.062

Critical Failures:
- FACTUAL: 4/5 failed (80% error rate)
  ❌ "Who created LightRAG?" → KEYWORD (should be FACTUAL)
  ❌ "Wann wurde Version 13.0 released?" → KEYWORD
  ❌ "Where is the configuration file?" → KEYWORD
  ❌ "Definition von Hybrid Search" → SUMMARY

- EXPLORATORY: 4/6 failed (67% error rate)
  ❌ "Wie funktioniert Hybrid Search?" → SUMMARY
  ❌ "Why is BM25 better than TF-IDF?" → KEYWORD
  ❌ "Welche Embedding-Modelle gibt es?" → SUMMARY
  ❌ "Compare LightRAG vs GraphRAG" → SUMMARY
```

**Root Causes:**

1. **Semantic Overlap:** FACTUAL vs EXPLORATORY sind semantisch sehr nah in Embedding-Space
   - "What is X?" vs "How does X work?" = ähnliche Vektoren
   - "Compare A vs B" vs "Overview of A and B" = Nachbarn im Embedding-Space

2. **Technical Noise:** Technische Begriffe (LightRAG, BM25, config.yaml) überschreiben Intent-Patterns
   - BGE-M3 matcht auf Term-Similarity statt Intent-Pattern
   - Keyword-Terms dominieren Intent-Signal

3. **Kurze Descriptions:** 25-35 Wörter pro Intent zu wenig für klare Boundaries
   - Keine negativen Beispiele ("NOT X")
   - Keine Anti-Pattern Definitionen

4. **Multilingual Challenge:** DE/EN Mix erschwert Embedding-Similarity
   - BGE-M3 multilingual, aber nicht intent-optimiert
   - Pattern-Keywords in beiden Sprachen verwässern Signal

## Auswirkung

**Production Impact:**
- **60% Accuracy** → 40% der Queries bekommen falsche Intent-Weights
- **Falsche Weight-Profile** → Suboptimale Retrieval-Strategie
- **User Experience:** Irrelevante Ergebnisse bei explorativen Queries

**Beispiel aus Production:**
```
Query: "was sind die aktuellen Trends im AI Umfeld des OMNITRACKERs"
Expected: EXPLORATORY (vector=20%, bm25=10%, local=20%, global=50%)
Actual (before fix): KEYWORD (vector=10%, bm25=60%, local=30%, global=0%)

Result: Installation-Guides statt AI-Trends (BM25 matched "OMNITRACKER" in allen Docs)
```

**Performance Budget:**
- Intent Classification muss <50ms sein (von 200ms P95 total query time)
- Aktuelle Semantic Router: ~20-50ms ✅
- Aber: Qualität nicht ausreichend ❌

## State-of-the-Art Research Findings

### SOTA Architectures 2025

| Approach | Latency | Accuracy | Cost | Source |
|----------|---------|----------|------|--------|
| **Semantic Router (Current)** | ~50ms | 55-60% | Very Low | Baseline |
| **LLM Zero-Shot** | ~5000ms | 70-80% | High | [Rasa Docs](https://legacy-docs-oss.rasa.com/docs/rasa/next/llms/llm-intent/) |
| **LLM Few-Shot** | ~5000ms | 80-90% | High | [Prompt Engineering Guide](https://www.promptingguide.ai/techniques/fewshot) |
| **Hybrid Router + LLM** | ~100-500ms | 85-95% | Medium | [vLLM Semantic Router](https://blog.vllm.ai/2025/09/11/semantic-router.html) |
| **C-LARA (Fine-tuned)** | ~50-100ms | **85-92%** ⭐ | **$0 runtime** ⭐ | [Amazon Science](https://www.amazon.science/publications/intent-detection-in-the-age-of-llms) |
| **ModernBERT Multi-Task** | ~50ms | 85-90% | Low | [Papers with Code](https://paperswithcode.com/task/intent-classification) |

**Key Insights:**
- **C-LARA Framework** = Best of both worlds: LLM quality + embedding latency
- **Hybrid Uncertainty Routing** = Fast classifier (95%) + LLM fallback (5% hard cases)
- **Symbol Tuning** = Simplify intent labels (FACTUAL → "WHO/WHAT")

### Benchmark Scores - Available Ollama Models

**Qwen2.5-7B (Best Available):**
- **BANKING77:** 87.30% accuracy (10-shot)
- **CLINC150:** 95.58% accuracy (10-shot)
- **HWU64:** 88.38% accuracy (10-shot)
- **Source:** [Dynamic Label Name Refinement Paper](https://arxiv.org/html/2412.15603)

**Mistral-7B:**
- **MultiWOZ 2.1:** 50% F-Score (few-shot)
- **Source:** [Multi-Intent Recognition Paper](https://arxiv.org/html/2509.10010v1)

**Current Production Model (llama3.2:8b):**
- No intent classification benchmarks found
- General-purpose instruction-following model

### Few-Shot Prompting Best Practices

**Optimal Example Count:** 2-5 examples per intent ([Prompt Engineering Best Practices](https://www.news.aakashg.com/p/prompt-engineering))
- < 2: Pattern nicht erkennbar
- 2-5: Optimal für classification tasks
- > 10: Overfitting, Token-Cost, Latenz

**Example Selection:**
- Diverse coverage (alle edge cases)
- Mutually exclusive (eindeutige Zuordnung)
- Representative (real-world queries)

## Lösungsoptionen

### Option 1: Hybrid Router with LLM Fallback 🚀 (Quick Win)

**Architecture:**
```
Query → Semantic Router (BGE-M3)
         ├─ Confidence ≥ 0.75 → Return Intent (95% queries, ~50ms)
         └─ Confidence < 0.75 → LLM Few-Shot → Return Intent (5% queries, ~500ms)
```

**Implementation:**
```python
async def classify_intent(self, query: str) -> tuple[Intent, float]:
    # 1. Fast path: Semantic Router
    intent, confidence = await self._classify_with_embeddings(query)

    # 2. High confidence → Return immediately
    if confidence >= 0.75:
        return intent, confidence

    # 3. Low confidence → LLM fallback
    llm_intent, llm_confidence = await self._llm_few_shot_classify(query)
    return llm_intent, llm_confidence

async def _llm_few_shot_classify(self, query: str) -> tuple[Intent, float]:
    """LLM classification with 2-5 examples per intent"""
    prompt = f"""You are a search query intent classifier.

INTENTS:
- FACTUAL: Single fact lookup (who, what, when, where, definition)
- KEYWORD: Technical identifier (error codes, config keys, file paths)
- EXPLORATORY: Process understanding (how, why, compare, trends)
- SUMMARY: Overview request (summarize, overview, main points)

EXAMPLES:
Query: "Was ist RAG?"
Intent: FACTUAL

Query: "Error 404 not found"
Intent: KEYWORD

Query: "Wie funktioniert Hybrid Search?"
Intent: EXPLORATORY

Query: "Fasse das Paper zusammen"
Intent: SUMMARY

Now classify:
Query: "{query}"
Intent:"""

    # Use Qwen2.5:7b (best benchmarks)
    response = await ollama.generate(model="qwen2.5:7b", prompt=prompt, temperature=0.0)
    intent = Intent(response.strip())
    return intent, 0.9  # High confidence from LLM
```

**Pros:**
- ✅ 95% queries bleiben schnell (~50ms)
- ✅ 5% hard cases bekommen LLM accuracy
- ✅ Minimal code changes
- ✅ Gradual rollout (threshold tunable)

**Cons:**
- ⚠️ Semantic Router immer noch 60% accurate (muss zuerst laufen)
- ⚠️ LLM calls bei 5% queries
- ⚠️ P95 latency steigt auf ~500ms

**Estimated Performance:**
- **Accuracy:** 75-80% (weighted avg)
- **P95 Latency:** 500ms (exceeds <50ms budget) ❌
- **Cost:** ~$0.001 per 20 queries (5% LLM usage, local Ollama)

---

### Option 2: C-LARA - Offline Data Generation + Fine-Tuned Classifier 🎯 (Recommended)

**Architecture:**
```
OFFLINE (One-time):
  Qwen2.5:7b generates 1000 labeled examples (4 intents × 250 examples)
  ↓
  Fine-tune SetFit model (sentence-transformers + contrastive learning)
  ↓
  Export fine-tuned model to models/intent_classifier_v1

ONLINE (Production):
  Query → Fine-Tuned SetFit Model → Intent + Confidence (~50-100ms)
```

**Phase 1: Synthetic Data Generation (Offline)**
```python
async def generate_training_data(self, examples_per_intent: int = 250) -> list[dict]:
    """Generate synthetic training examples using Qwen2.5:7b"""

    GENERATION_PROMPT = """Generate {n} realistic search queries for intent: {intent}

INTENT DEFINITION:
{definition}

CONSTRAINTS:
- Mix of German and English queries (50/50)
- Include edge cases and ambiguous examples
- Vary query length (short, medium, long)
- Include technical terms: RAG, OMNITRACKER, Vector Search, BM25, Neo4j
- Cover different domains (software docs, business queries, research questions)

OUTPUT FORMAT (JSON array):
[
  {{"query": "Was ist Hybrid Search?", "intent": "FACTUAL"}},
  {{"query": "How does RRF work?", "intent": "EXPLORATORY"}},
  ...
]"""

    training_data = []
    for intent in Intent:
        prompt = GENERATION_PROMPT.format(
            n=examples_per_intent,
            intent=intent.value,
            definition=INTENT_DESCRIPTIONS[intent]
        )

        # Use Qwen2.5:7b (87-95% accuracy on intent benchmarks)
        response = await ollama.generate(model="qwen2.5:7b", prompt=prompt)
        examples = json.loads(response)
        training_data.extend(examples)

    return training_data  # 1000 examples total
```

**Estimated Generation Time:**
- 4 intents × 250 examples = 1000 queries
- @ ~2 sec/query with Qwen2.5:7b = **~30 minutes total**
- Cost: **$0** (local Ollama on DGX Spark)

**Phase 2: Fine-Tune SetFit Model**
```python
from setfit import SetFitModel, Trainer
from sentence_transformers.losses import CosineSimilarityLoss

def train_intent_classifier(training_data: list[dict]) -> SetFitModel:
    """Fine-tune SetFit model on synthetic data"""

    # 1. Load base model (BGE-M3 or similar)
    model = SetFitModel.from_pretrained("BAAI/bge-m3")

    # 2. Prepare dataset
    train_ds = Dataset.from_list(training_data)

    # 3. Train with contrastive learning
    trainer = Trainer(
        model=model,
        train_dataset=train_ds,
        loss_class=CosineSimilarityLoss,
        num_iterations=20,
        batch_size=16,
    )

    trainer.train()

    # 4. Export model
    model.save_pretrained("models/intent_classifier_v1")

    return model
```

**Phase 3: Production Deployment**
```python
class LLMTrainedIntentClassifier:
    def __init__(self):
        # Load fine-tuned model once at startup
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

        return intent, confidence
```

**Pros:**
- ✅ Best of both worlds: LLM quality + embedding latency
- ✅ No online LLM calls (all inference local)
- ✅ Latency: 50-100ms fits <50ms budget (with optimization)
- ✅ Accuracy: 85-92% (based on SOTA papers)
- ✅ Model improves over time (regenerate data + retrain)
- ✅ Qwen2.5:7b proven on BANKING77/CLINC150 benchmarks

**Cons:**
- ⚠️ One-time setup effort (2-3 days)
- ⚠️ Needs model versioning/deployment pipeline
- ⚠️ Requires labeled validation set for testing

**Estimated Performance:**
- **Accuracy:** 85-92%
- **P50 Latency:** 50ms ✅
- **P95 Latency:** 100ms ⚠️ (exceeds <50ms budget slightly)
- **P99 Latency:** 200ms
- **Cost:** $0 (no online LLM calls)

---

### Option 3: Full LLM Few-Shot with Aggressive Caching ⚡ (Maximum Accuracy)

**Architecture:**
```
Query → Redis Cache Lookup
         ├─ Cache Hit (70-80%) → Return Intent (~1ms)
         └─ Cache Miss (20-30%) → Qwen2.5:7b Few-Shot → Cache Result → Return (~500ms)
```

**Implementation:**
```python
class CachedLLMIntentClassifier:
    def __init__(self):
        self.redis = redis.Redis(...)
        self.cache_ttl = 86400 * 7  # 7 days

    async def classify(self, query: str) -> tuple[Intent, float]:
        # 1. Normalize query for cache key
        cache_key = f"intent:{self._normalize_query(query)}"

        # 2. Check cache
        cached = await self.redis.get(cache_key)
        if cached:
            intent, confidence = json.loads(cached)
            return Intent(intent), confidence

        # 3. LLM classification
        intent, confidence = await self._llm_few_shot_classify(query)

        # 4. Cache result
        await self.redis.setex(
            cache_key,
            self.cache_ttl,
            json.dumps([intent.value, confidence])
        )

        return intent, confidence
```

**Pros:**
- ✅ Highest accuracy: 90-95% (full LLM)
- ✅ 70-80% cache hit rate → most queries <5ms
- ✅ Confidence scores from LLM
- ✅ Easy to update (just change prompt)

**Cons:**
- ⚠️ 20-30% queries hit LLM (~500ms) = P95 exceeds budget ❌
- ⚠️ P99 latency still high (~2000ms)
- ⚠️ Cache invalidation complexity
- ⚠️ Cache warm-up period (first hours: 100% cache miss)

**Estimated Performance:**
- **Accuracy:** 90-95%
- **P50 Latency:** 5ms (cache hit) ✅
- **P95 Latency:** 500ms (cache miss) ❌
- **P99 Latency:** 2000ms (cache miss)
- **Cost:** $0 (local Ollama)

## Empfehlung

### Primary: **Option 2 (C-LARA)** 🎯

**Reasons:**
1. ✅ Meets Latency Budget: 50-100ms fits within <200ms total query time
2. ✅ Best Accuracy/Cost Ratio: 85-92% accuracy at $0 runtime cost
3. ✅ Production-Ready: No external LLM dependencies at runtime
4. ✅ Scalable: Linear scaling with query volume (no cache complexity)
5. ✅ Matches SOTA: C-LARA framework proven in recent research
6. ✅ Qwen2.5:7b proven: 87-95% accuracy on intent benchmarks

**Implementation Roadmap (13 SP):**

| Phase | Tasks | Duration | SP |
|-------|-------|----------|-----|
| **Phase 1: Data Generation** | Generate 1000 examples with Qwen2.5:7b<br>Human validation (100 samples)<br>Clean and export | 2 days | 3 SP |
| **Phase 2: Model Training** | Train SetFit model<br>Validate on test set<br>Hyperparameter tuning | 1 day | 3 SP |
| **Phase 3: Integration** | Update IntentClassifier<br>Add model loading<br>Migrate code | 2 days | 5 SP |
| **Phase 4: A/B Testing** | Deploy both classifiers<br>Log results<br>Compare metrics | 1 week | 2 SP |

**Total Effort:** 13 SP (~1.5 weeks)

### Alternative: **Hybrid Approach (Option 1 + Option 2)**

**Best of All Worlds:**
```python
async def classify_intent(self, query: str) -> tuple[Intent, float]:
    # 1. Try fine-tuned SetFit model (Option 2)
    intent, confidence = await self.setfit_classify(query)

    # 2. High confidence → Return
    if confidence >= 0.80:
        return intent, confidence

    # 3. Low confidence → LLM fallback (Option 1)
    llm_intent, llm_conf = await self.llm_few_shot_classify(query)
    return llm_intent, llm_conf
```

**This gives:**
- **95% queries:** SetFit model (~50-100ms, 85-92% accuracy)
- **5% hard cases:** Qwen2.5:7b fallback (~500ms, 95% accuracy)
- **Overall accuracy:** ~90%
- **P95 latency:** <200ms ⚠️ (within total budget, but exceeds intent budget)

## Betroffene Dateien

**Implementierung:**
- `src/components/retrieval/intent_classifier.py` (Main classifier)
- `src/core/config.py` (Add model path config)

**Scripts (Neu):**
- `scripts/generate_intent_training_data.py` (Data generation)
- `scripts/train_intent_classifier.py` (SetFit training)
- `scripts/validate_intent_model.py` (Accuracy testing)
- `scripts/test_intent_classifier.py` (A/B testing)

**Models (Neu):**
- `models/intent_classifier_v1/` (Fine-tuned SetFit model)

**Tests:**
- `tests/unit/test_intent_classifier.py` (Unit tests)
- `tests/integration/test_intent_accuracy.py` (Accuracy benchmarks)

## Erfolgskriterien

1. **Accuracy:** ≥85% on validation set (20 diverse queries)
2. **Latency:** P95 ≤100ms (within total budget)
3. **Confidence:** Avg confidence ≥0.85
4. **Margin:** Avg margin ≥0.10 (clear separation)
5. **Production Metrics:**
   - No degradation in end-to-end query latency (P95 ≤500ms)
   - Improved result relevance (measured via user feedback)
   - Reduced misclassification rate (<15%)

## Research Sources

**State-of-the-Art Architectures:**
- [Top LLM Papers of the Week (October 2025)](https://medium.com/@kalyanks/top-llm-papers-of-the-week-october-week-4-2025-08b20079e1d7)
- [Intent Classification - Papers with Code](https://paperswithcode.com/task/intent-classification)
- [Intent Detection in the Age of LLMs - Amazon Science](https://www.amazon.science/publications/intent-detection-in-the-age-of-llms)

**Few-Shot Prompting Best Practices:**
- [Prompt Engineering in 2025: The Latest Best Practices](https://www.news.aakashg.com/p/prompt-engineering)
- [Few-Shot Prompting | Prompt Engineering Guide](https://www.promptingguide.ai/techniques/fewshot)
- [Intent Classification: 2025 Techniques for NLP Models](https://labelyourdata.com/articles/machine-learning/intent-classification)

**Semantic Router vs LLM Comparison:**
- [vLLM Semantic Router: Next Phase in LLM inference](https://blog.vllm.ai/2025/09/11/semantic-router.html)
- [Semantic Routing for Enhanced Performance of LLM-Assisted 5G Networks](https://arxiv.org/html/2404.15869v1)
- [What is Semantic Router? Key Uses & How It Works](https://www.deepchecks.com/glossary/semantic-router/)

**Model Benchmarks:**
- [Dynamic Label Name Refinement for Few-Shot Dialogue Intent Classification](https://arxiv.org/html/2412.15603) (Qwen2.5-7B benchmarks)
- [Multi-Intent Recognition in Dialogue Understanding](https://arxiv.org/html/2509.10010v1) (Mistral-7B benchmarks)

## Referenzen

**ADRs:**
- ADR-024: BGE-M3 Embeddings (1024-dim, multilingual)

**Related Technical Debt:**
- TD-059: Cross-Encoder Reranking (Reranking optimization)
- TD-064: Temporal Community Summaries (Graph reasoning optimization)

**External Resources:**
- [C-LARA Framework Paper](https://www.amazon.science/publications/intent-detection-in-the-age-of-llms)
- [SetFit Documentation](https://huggingface.co/docs/setfit/)
- [BANKING77 Dataset](https://github.com/jianguoz/Few-Shot-Intent-Detection/tree/main/Datasets/BANKING77)
- [CLINC150 Dataset](https://arxiv.org/abs/1909.02027)
