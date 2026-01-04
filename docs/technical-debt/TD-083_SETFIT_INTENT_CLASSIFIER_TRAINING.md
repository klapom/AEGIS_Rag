# TD-083: SetFit Intent Classifier Training

**Status:** Open
**Priority:** Low
**Effort:** Medium (1-2 hours)
**Sprint:** 76+
**Category:** Machine Learning / Performance Optimization

---

## Problem

The IntentClassifier currently uses an **embedding-based cosine similarity fallback** instead of the planned **SetFit fine-tuned model**. While the fallback works successfully (0.7 confidence, 0.38ms latency), a trained SetFit model would provide:

1. **Higher accuracy** for edge cases
2. **Better calibrated confidence scores**
3. **Fewer false positives** in ambiguous queries

**Current Warning:**
```
intent_classifier_init
  classifier_type=embedding-based
  setfit_model_exists=False
  setfit_model_path=models/intent_classifier
  embedding_fallback=True
```

**Root Cause:**
- `models/intent_classifier/` directory doesn't exist
- No SetFit model has been trained yet
- Fallback is working but suboptimal

---

## Current Workaround

**File:** `/home/admin/projects/aegisrag/AEGIS_Rag/.env`

```bash
# Sprint 75 Fix: Document that SetFit model is not trained yet
# IntentClassifier uses embedding-based fallback (works fine, 0.7 confidence)
USE_SETFIT_CLASSIFIER=false
```

This disables the warning and documents the current state.

---

## Proposed Solution

### Training Process

1. **Use Sprint 67 Training Dataset** (available at `data/datasets/intent_training_sprint67.jsonl`)
   - Contains ~500+ labeled examples
   - Covers all 4 intent classes: `vector`, `graph`, `hybrid`, `metadata`
   - High-quality labels from C-LARA classifier

2. **Training Script** (create new):
   ```python
   # scripts/train_setfit_intent_classifier.py
   from setfit import SetFitModel, Trainer, TrainingArguments
   from datasets import load_dataset

   # Load Sprint 67 dataset
   dataset = load_dataset("json", data_files="data/datasets/intent_training_sprint67.jsonl")

   # Initialize SetFit model
   model = SetFitModel.from_pretrained("sentence-transformers/paraphrase-mpnet-base-v2")

   # Training arguments
   args = TrainingArguments(
       batch_size=16,
       num_epochs=4,
       evaluation_strategy="epoch",
       save_strategy="epoch",
       output_dir="models/intent_classifier",
   )

   # Train
   trainer = Trainer(
       model=model,
       args=args,
       train_dataset=dataset["train"],
       eval_dataset=dataset["test"],
   )

   trainer.train()
   model.save_pretrained("models/intent_classifier")
   ```

3. **Update `.env`**:
   ```bash
   USE_SETFIT_CLASSIFIER=true
   INTENT_CLASSIFIER_MODEL_PATH=models/intent_classifier
   ```

4. **Expose in Admin UI** (Feature 76.X):
   - **Status Display**: Show "SetFit Model Active" vs "Embedding Fallback"
   - **Training Button**: Trigger training job from UI
   - **Progress Tracking**: Show training progress (epoch, loss, accuracy)
   - **Model Metrics**: Display validation accuracy, F1 score
   - **Quick Compare**: A/B test SetFit vs Embedding on test queries

---

## Admin UI Integration

**Component:** `frontend/src/pages/AdminPage.tsx`

```tsx
// New section: Intent Classifier
<Card>
  <CardHeader>
    <CardTitle>Intent Classifier</CardTitle>
  </CardHeader>
  <CardContent>
    <div className="space-y-4">
      {/* Status */}
      <div>
        <Label>Current Model</Label>
        <Badge variant={intentClassifierStatus.is_setfit ? "success" : "warning"}>
          {intentClassifierStatus.is_setfit ? "SetFit Active" : "Embedding Fallback"}
        </Badge>
      </div>

      {/* Metrics */}
      {intentClassifierStatus.is_setfit && (
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>Accuracy</Label>
            <p>{intentClassifierStatus.accuracy}%</p>
          </div>
          <div>
            <Label>F1 Score</Label>
            <p>{intentClassifierStatus.f1_score}</p>
          </div>
        </div>
      )}

      {/* Training */}
      {!intentClassifierStatus.is_setfit && (
        <Button
          onClick={handleTrainSetFit}
          disabled={trainingInProgress}
        >
          {trainingInProgress ? "Training..." : "Train SetFit Model"}
        </Button>
      )}

      {/* Progress */}
      {trainingInProgress && (
        <Progress value={trainingProgress} />
      )}
    </div>
  </CardContent>
</Card>
```

**API Endpoint:** `POST /api/v1/admin/intent-classifier/train`

```python
@router.post("/intent-classifier/train")
async def train_intent_classifier(background_tasks: BackgroundTasks):
    """Train SetFit intent classifier in background."""
    task_id = str(uuid.uuid4())

    background_tasks.add_task(
        train_setfit_model,
        task_id=task_id,
        dataset_path="data/datasets/intent_training_sprint67.jsonl",
        output_path="models/intent_classifier",
    )

    return {
        "task_id": task_id,
        "status": "training_started",
        "estimated_duration_minutes": 90,
    }
```

---

## Acceptance Criteria

- [ ] Training script created (`scripts/train_setfit_intent_classifier.py`)
- [ ] SetFit model trained on Sprint 67 dataset
- [ ] Model saved to `models/intent_classifier/`
- [ ] Validation accuracy > 95% (better than C-LARA's 89.5%)
- [ ] Admin UI shows model status (SetFit vs Fallback)
- [ ] Admin UI has "Train Model" button
- [ ] Training progress visible in UI
- [ ] Model metrics displayed (accuracy, F1, confusion matrix)
- [ ] `.env` updated with `USE_SETFIT_CLASSIFIER=true`
- [ ] Warning eliminated from logs

---

## Related Work

- **Sprint 67 Feature 67.3**: C-LARA Intent Classifier (achieved 89.5% accuracy)
- **Sprint 67 Feature 67.5**: Intent training dataset generation (500+ samples)
- **TD-079**: LLM Intent Classifier C-LARA (current implementation)
- **ADR-067**: Intent classification evolution (Embedding → C-LARA → SetFit)

---

## Estimated Effort

| Task | Time |
|------|------|
| Create training script | 30 min |
| Train SetFit model | 60-90 min |
| Admin UI integration | 30 min |
| Testing & validation | 20 min |
| **Total** | **2-3 hours** |

---

## Notes

- SetFit is lightweight (~100MB model) and fast to train
- No GPU required for training (CPU is fine for small dataset)
- Can be trained on DGX Spark in background
- Backward compatible - falls back to embeddings if model missing
- Training can be exposed as self-service feature for domain-specific tuning

---

**Created:** Sprint 75 (2025-01-04)
**Discovered During:** RAGAS evaluation infrastructure fixes
**Tracking:** docs/technical-debt/TD_INDEX.md
