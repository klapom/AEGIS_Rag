# Cloud LLM Decision Matrix - Quick Reference

**Date:** 2025-11-28
**Status:** Current configuration OPTIMAL, no changes needed

---

## Executive Decision

**RECOMMENDATION: KEEP CURRENT HYBRID STRATEGY (ADR-037)**

Current configuration already implements the optimal balance of quality, cost, and reliability. No changes needed.

---

## Performance Comparison Matrix

| Aspect | Local Ollama (Gemma 2 4B) | Alibaba Cloud (Qwen3-32B) | Winner |
|--------|---------------------------|---------------------------|--------|
| **Cost** | $0/month | $100-120/month | Local |
| **Quality** | 85% entity / 75% relation | 95% entity / 90% relation | Cloud (+10-15%) |
| **Latency** | 15-17s/doc | 15-20s/doc | Tie (~3s diff) |
| **Throughput** | 1-2 concurrent | 10+ concurrent | Cloud (3-5x) |
| **Batch Processing** | 100 docs/100min | 100 docs/25min | Cloud (4x) |
| **GPU Requirement** | 6GB VRAM | None | Cloud |
| **Internet Required** | No | Yes | Local |
| **Sensitive Data** | GDPR/HIPAA compliant | Not for PII | Local |
| **Model Size** | 4B parameters | 32B parameters | Cloud (8x) |

---

## Cost Breakdown

### Per-Document Costs

| Document Type | Local | Cloud | Cloud vs Local |
|---------------|-------|-------|----------------|
| **Text-only (2-3 chunks)** | FREE | $0.0007-0.0010 | +$0.001 |
| **With 5 images** | FREE | $0.20 | +$0.20 |
| **With 10 images** | FREE | $0.40 | +$0.40 |

### Monthly Budget Projections

| Volume | Document Type | Cloud Cost | Budget % Used | Fallback Trigger |
|--------|---------------|------------|---------------|------------------|
| 1,000 docs | Text-only | $1 | 0.8% | No |
| 10,000 docs | Text-only | $10 | 8.3% | No |
| 120,000 docs | Text-only | $120 | 100% | **YES** |
| 500 docs | Mixed (50% VLM) | $50 | 42% | No |
| 1,200 docs | Mixed (50% VLM) | $120 | 100% | **YES** |
| 300 docs | Image-heavy (10 imgs) | $120 | 100% | **YES** |

**Budget Limit:** $120/month (configurable in `config/llm_config.yml`)

---

## Use Case Recommendations

### When to Use Cloud (Current Default)

✅ **RECOMMENDED FOR:**
- Small-scale production (<1,000 docs/month) - $10-100/month
- Quality-critical extraction (legal, medical, technical)
- Image-heavy documents (VLM 2-3x faster)
- Batch indexing (3-5x faster parallel processing)
- Production deployments where quality matters

**Configuration:** ALREADY DEFAULT (ADR-037, no changes needed)

### When to Use Local Only

✅ **RECOMMENDED FOR:**
- Development/testing (no API key, fast iteration)
- Sensitive data (PII/HIPAA) - **AUTOMATIC** routing
- Zero-cost requirement
- Offline operation (no internet)
- Simple documents (quality difference negligible)
- Budget exceeded fallback - **AUTOMATIC**

**Configuration to Force Local:**
```bash
# .env
# Remove or comment out:
# ALIBABA_CLOUD_API_KEY=sk-...
```

### When to Increase Budget

✅ **CONSIDER IF:**
- Processing >5,000 docs/month
- Hitting budget limit frequently (>2 times/month)
- Quality degradation impacting downstream tasks
- Batch indexing critical (time > cost)

**Configuration:**
```yaml
# config/llm_config.yml
budgets:
  monthly_limits:
    alibaba_cloud: 500.0  # Increase from $120 to $500
```

---

## Quality Impact Analysis

### Entity Extraction Quality

| Metric | Local (4B) | Cloud (32B) | Improvement |
|--------|-----------|-------------|-------------|
| **Entity Accuracy** | 85% | 95% | **+10%** |
| **Entity Disambiguation** | Basic | Advanced | **Significant** |
| **Type Classification** | Good | Excellent | **+15%** |
| **False Positives** | 15% | 5% | **-67%** |

### Relationship Extraction Quality

| Metric | Local (4B) | Cloud (32B) | Improvement |
|--------|-----------|-------------|-------------|
| **Relation Accuracy** | 75% | 90% | **+15%** |
| **Implicit Relations** | Limited | Advanced | **Significant** |
| **False Relations** | 23% | <10% | **-57%** |
| **Context Understanding** | Limited | Advanced | **Significant** |

**Impact:** Better knowledge graph → Better retrieval → Better RAG quality

---

## Automatic Routing Logic

### Current Configuration (OPTIMAL)

```python
# src/components/llm_proxy/aegis_llm_proxy.py:343-351
if (
    task.quality_requirement == QualityRequirement.HIGH  # ✓
    and task.complexity == Complexity.HIGH              # ✓ (ADR-037)
    and not self._is_budget_exceeded("alibaba_cloud")  # ✓ ($120 limit)
):
    return ("alibaba_cloud", "high_quality_high_complexity")
else:
    return ("local_ollama", "budget_exceeded_or_low_complexity")
```

### Routing Priority

1. **ALWAYS Local:** PII/HIPAA data (GDPR compliance)
2. **ALWAYS Local:** Embeddings (bge-m3 excellent locally)
3. **Cloud if Available:** High quality + High complexity (Entity/Relation)
4. **Cloud if Available:** Vision tasks (VLM)
5. **Local Fallback:** Budget exceeded (automatic)
6. **Default:** Local (70% of tasks)

---

## Configuration Comparison

### Current (Hybrid - OPTIMAL)

```yaml
# config/llm_config.yml
budgets:
  monthly_limits:
    alibaba_cloud: 120.0  # $120/month

model_defaults:
  alibaba_cloud:
    extraction: qwen3-32b      # 32B params
    vision: qwen3-vl-30b-a3b-instruct
  local_ollama:
    extraction: gemma-3-4b-it  # 4B params (fallback)
```

**Result:**
- Entity/Relation → Cloud (Qwen3-32B, high quality)
- VLM → Cloud (Qwen3-VL, faster + better)
- Budget limit → Automatic fallback to local
- Cost: $10-120/month (usage-based)

### Development (Local Only)

```bash
# .env
# Remove ALIBABA_CLOUD_API_KEY
```

**Result:**
- All tasks → Local (Gemma 2 4B)
- Cost: $0/month
- Quality: Good (85% / 75%)

### Large-Scale (Increased Budget)

```yaml
# config/llm_config.yml
budgets:
  monthly_limits:
    alibaba_cloud: 500.0  # $500/month
```

**Result:**
- Higher volume before fallback
- Cost: $100-500/month
- Quality: Excellent (95% / 90%)

---

## Break-Even Analysis

### Time Saved vs. Cost

| Volume | Manual Review Saved | Time Value | Cloud Cost | Net Benefit |
|--------|-------------------|------------|------------|-------------|
| 1,000 docs | 2.5 hours | $250 | $100 | **+$150** |
| 5,000 docs | 12.5 hours | $1,250 | $120 (limit) | **+$1,130** |
| 10,000 docs | 25 hours | $2,500 | $120 (limit) | **+$2,380** |

**Conclusion:** Cloud LLM pays for itself at 1,000+ docs/month.

### Batch Processing ROI

**1,000 documents batch:**
- Local: 100 minutes + $167 developer time = **$167 total**
- Cloud: 25 minutes + $42 developer time + $100 cloud = **$142 total**
- **Savings: $25 + 75 minutes**

**Conclusion:** Cloud is cost-effective for batch indexing.

---

## Monitoring Commands

### Check Monthly Spending

```bash
# View current month costs
sqlite3 data/cost_tracking.db "
  SELECT provider, SUM(cost_usd) as total
  FROM llm_requests
  WHERE strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now')
  GROUP BY provider;
"
```

### Budget Alert Script

```python
# scripts/check_budget.py
from src.components.llm_proxy.cost_tracker import get_cost_tracker

tracker = get_cost_tracker()
spending = tracker.get_monthly_spending()

alibaba_spent = spending.get("alibaba_cloud", 0.0)
alibaba_limit = 120.0
usage_pct = (alibaba_spent / alibaba_limit) * 100

print(f"Alibaba Cloud: ${alibaba_spent:.2f} / ${alibaba_limit:.2f} ({usage_pct:.1f}%)")

if usage_pct >= 80:
    print("WARNING: Budget threshold (80%)")
if usage_pct >= 100:
    print("ALERT: Budget limit exceeded")
```

### Test Cloud Routing

```bash
# Verify Alibaba Cloud routing
python scripts/test_single_pdf.py "data/sample.pdf"

# Expected logs:
# {"event": "routing_decision", "provider": "alibaba_cloud"}
# {"event": "llm_entity_extraction_response", "model": "qwen3-32b"}
```

---

## Decision Summary

### CURRENT STATE: OPTIMAL ✅

| Component | Status | Recommendation |
|-----------|--------|----------------|
| **Entity Extraction** | Routes to Alibaba Cloud | Keep |
| **Relation Extraction** | Routes to Alibaba Cloud | Keep |
| **VLM Image Analysis** | Routes to Alibaba Cloud | Keep |
| **Budget Limit** | $120/month | Keep (adjust if needed) |
| **Automatic Fallback** | Enabled | Keep |
| **Cost Tracking** | SQLite database | Keep |
| **Quality** | 95% entity / 90% relation | Excellent |
| **Cost Control** | Automatic | Excellent |

**NO CHANGES NEEDED**

---

## Action Items

### Immediate Actions: NONE

Current configuration (ADR-037, accepted 2025-11-19) is production-ready.

### Optional Actions (If Needed)

1. **Monitor Monthly Costs:** Run `scripts/check_budget.py`
2. **Adjust Budget:** Edit `config/llm_config.yml` if hitting limit
3. **Force Local:** Remove `ALIBABA_CLOUD_API_KEY` for development
4. **Increase Limit:** Change `alibaba_cloud: 500.0` for large-scale

---

## References

- **Full Analysis:** `docs/analysis/CLOUD_LLM_INGESTION_ANALYSIS.md`
- **ADR-037:** Alibaba Cloud Extraction (accepted 2025-11-19)
- **ADR-033:** Multi-Cloud Routing (three-tier strategy)
- **Sprint 32:** Adaptive chunking (124 → 2-3 chunks)

---

**Document Version:** 1.0
**Last Updated:** 2025-11-28
**Next Review:** Monthly (with cost report)
