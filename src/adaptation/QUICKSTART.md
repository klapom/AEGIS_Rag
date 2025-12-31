# C-LARA Data Generator - Quick Start

**Sprint 67 Feature 67.10**: Generate intent classification training data

---

## Prerequisites

```bash
# Ensure Qwen2.5:7b is available
ollama pull qwen2.5:7b

# Verify Ollama is running
curl http://localhost:11434/api/tags
```

---

## Quick Test (20 examples)

```bash
poetry run python scripts/test_intent_classifier.py
```

**Expected Output:**
```
=== C-LARA Intent Data Generator Test ===

Generating 20 test examples (4 per intent class)...

Generated 20 examples
Stats: {...}

=== Sample Examples ===
1. [factual] (en) What is RAG?... (conf: 0.95)
2. [procedural] (en) How to install Docker?... (conf: 0.92)
...

=== Validation Report ===
{
  "valid": true,
  "total_examples": 20,
  ...
}

✅ SUCCESS: Data generation working correctly!
```

---

## Full Dataset Generation (1000 examples)

```bash
# Generate 1000 labeled examples
python -m src.adaptation.intent_data_generator \
  --model qwen2.5:7b \
  --examples 1000 \
  --batch-size 10 \
  --output data/intent_training_v1.jsonl
```

**Duration:** ~30 minutes
**Output:** `data/intent_training_v1.jsonl` (1000 lines)

---

## Python API

```python
from src.adaptation import CLARADataGenerator

# Initialize generator
generator = CLARADataGenerator(
    model="qwen2.5:7b",
    target_examples=1000,
    examples_per_batch=10
)

# Generate examples
examples = await generator.generate_examples()

# Validate quality
report = generator.validate_dataset(examples)
if report["valid"]:
    print(f"✅ Dataset valid: {report['total_examples']} examples")
else:
    print(f"⚠️  Issues: {report['issues']}")

# Save to JSONL
await generator.save_dataset(examples, "data/intent_training_v1.jsonl")
```

---

## Intent Classes

| Intent | Description | Example |
|--------|-------------|---------|
| **factual** | Specific fact lookups | "What is RAG?" |
| **procedural** | Step-by-step instructions | "How to install Docker?" |
| **comparison** | Compare entities | "REST vs GraphQL?" |
| **recommendation** | Best practices | "Best database for time-series?" |
| **navigation** | Find location | "Where is API documentation?" |

---

## Quality Metrics

| Metric | Target | Validation |
|--------|--------|------------|
| Total Examples | 1000 | Generated count |
| Class Balance | 20% each (200/class) | 15-25% acceptable |
| High Confidence | 90% with ≥0.8 | Confidence distribution |
| Duplicates | <5% | Unique query count |
| Language Split | 50% DE, 50% EN | Language distribution |

---

## Output Format

**JSONL** (one JSON per line):
```jsonl
{"query": "What is RAG?", "intent": "factual", "confidence": 0.95, "language": "en", "domain": "software"}
```

---

## Troubleshooting

### Ollama Not Running
```bash
# Start Ollama
ollama serve

# Verify
curl http://localhost:11434/api/tags
```

### Model Not Found
```bash
# Pull Qwen2.5:7b
ollama pull qwen2.5:7b

# Verify
ollama list | grep qwen
```

### Slow Generation
- Reduce batch size: `--batch-size 5`
- Reduce examples: `--examples 100`
- Check Ollama GPU usage: `nvidia-smi`

### Low Quality
- Increase confidence threshold in validation
- Regenerate with different random seed
- Manual review of sample examples

---

## Next Steps

1. **Generate Data**: Run full 1000 example generation
2. **Validate Quality**: Review validation report
3. **Manual Review**: Sample 100 random examples
4. **Train Model**: Feature 67.11 - SetFit training
5. **Integrate**: Feature 67.12 - Replace Semantic Router
6. **A/B Test**: Feature 67.13 - Production validation

---

## Files

| File | Purpose |
|------|---------|
| `data/intent_training_v1.jsonl` | Generated training data |
| `models/intent_classifier_v1/` | Trained model (Feature 67.11) |
| `src/adaptation/intent_data_generator.py` | Generator implementation |
| `tests/unit/adaptation/test_intent_data_generator.py` | Unit tests |
| `scripts/test_intent_classifier.py` | Integration test |

---

**Documentation:** [README.md](README.md) | [TD-079](../../docs/technical-debt/TD-079_LLM_INTENT_CLASSIFIER_CLARA.md)
**Sprint Plan:** [SPRINT_67_PLAN.md](../../docs/sprints/SPRINT_67_PLAN.md)
