# TD-101: RISE Reasoning Control Integration

**Status:** 🔴 OPEN
**Priority:** P2 (Medium)
**Story Points:** 6 SP
**Created:** 2026-01-15
**Target Sprint:** TBD (Post-Sprint 95)
**Original Feature:** Sprint 94.4

---

## Problem Statement

RISE (Reasoning behavior Interpretability via Sparse auto-Encoder) from Google DeepMind enables fine-grained control over LLM reasoning behaviors by identifying latent dimensions that correspond to specific cognitive patterns (e.g., step-by-step reasoning, creativity, caution).

**Current Gap:**
- No mechanism to control LLM reasoning behavior at inference time
- All skills use same reasoning approach regardless of task requirements
- Cannot adaptively strengthen/weaken reasoning dimensions based on context

**Business Impact:**
- Sub-optimal reasoning for complex multi-step tasks
- Inability to enforce specific reasoning patterns (e.g., cautious reasoning for safety-critical tasks)
- Missed opportunity for reasoning-aware skill orchestration

---

## Technical Details

### Research Foundation

> "RISE (Reasoning behavior Interpretability via Sparse auto-Encoder) von Google DeepMind identifiziert latente Dimensionen für solche Denkverhalten und erlaubt es, sie gezielt zu verstärken oder abzuschwächen."
> — AegisRAG_Agentenframework.docx

**Key Paper:** Zhang et al. 2025 - RISE: Reasoning behavior Interpretability via Sparse auto-Encoder

### Architecture Concept

```
┌─────────────────────────────────────────────────────────────┐
│                  RISE Reasoning Controller                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Task Type: "Complex Multi-Step Problem"                    │
│       ↓                                                     │
│  Identify Required Reasoning Dimensions:                    │
│    - step_by_step: 0.8 (high)                              │
│    - analytical: 0.7 (high)                                 │
│    - creative: 0.2 (low)                                    │
│       ↓                                                     │
│  Sparse Autoencoder Projection:                             │
│    - Extract latent activations from LLM                    │
│    - Identify active reasoning dimensions                   │
│    - Apply steering vectors to strengthen/weaken            │
│       ↓                                                     │
│  LLM with Modified Reasoning Behavior                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Implementation Requirements

1. **Sparse Autoencoder Training:**
   - Train SAE on LLM activations (e.g., Nemotron3, GPT-4)
   - Identify ~100-500 interpretable latent dimensions
   - Map dimensions to reasoning behaviors (step-by-step, analytical, creative, etc.)

2. **Reasoning Dimension Catalog:**
   ```python
   class ReasoningDimension(Enum):
       STEP_BY_STEP = "step_by_step"
       ANALYTICAL = "analytical"
       CREATIVE = "creative"
       CAUTIOUS = "cautious"
       EXPLORATORY = "exploratory"
       FOCUSED = "focused"
   ```

3. **Integration with Skill System:**
   - Skills declare required reasoning dimensions
   - SkillOrchestrator applies reasoning control before LLM invocation
   - Example: `research` skill requires high analytical + exploratory, low caution

4. **Steering Vector Application:**
   - Modify LLM activations at specific layers
   - Apply weighted steering vectors for each dimension
   - Support for OpenAI, Anthropic, Ollama APIs (via activation patching)

### Dependencies

- **Sparse Autoencoder Library:** [sparse_autoencoder](https://github.com/openai/sparse-autoencoder) or custom implementation
- **LLM Access:** Need intermediate activations (requires API support or local models)
- **Research:** RISE paper, interpretability research from DeepMind/Anthropic

---

## Proposed Solution

### Phase 1: Research & Prototyping (2 SP)
1. Review RISE paper and related work
2. Identify suitable SAE library/implementation
3. Create proof-of-concept with Ollama local models
4. Document reasoning dimensions catalog

### Phase 2: SAE Training (2 SP)
1. Collect activation datasets from Nemotron3/GPT-OSS
2. Train sparse autoencoder (100-500 dimensions)
3. Interpret latent dimensions (manual analysis + automated)
4. Validate dimension→behavior mappings

### Phase 3: Integration (2 SP)
1. Create `src/agents/reasoning/rise_controller.py`
2. Integrate with SkillOrchestrator
3. Add skill-level reasoning dimension declarations
4. Implement steering vector application for supported LLMs
5. Unit tests (30+ tests)

---

## Workaround

**Current Approach:**
- Use prompt engineering to guide reasoning behavior
- Example: "Think step-by-step" for analytical tasks
- Limitation: Less fine-grained control, LLM-dependent effectiveness

**Acceptable for MVP:** Yes, prompt engineering covers 70-80% of use cases

---

## Related ADRs

- **ADR-049:** Agentic Framework Architecture (skill system foundation)
- **ADR-055:** LangGraph 1.0 Migration (orchestration patterns)
- **Future ADR-056:** RISE Reasoning Control Architecture (when implemented)

---

## Related Technical Debt

- **TD-085:** DSPy Integration for Prompt Optimization (Sprint 75)
  - RISE could complement DSPy by optimizing reasoning behavior, not just prompts

---

## References

- **RISE Paper:** Zhang et al. 2025 - Reasoning behavior Interpretability via Sparse auto-Encoder
- **Sparse Autoencoders:** Anthropic's work on interpretability
- **Activation Steering:** OpenAI's research on model behavior control
- **AegisRAG Research Doc:** AegisRAG_Agentenframework.docx (RISE discussion)

---

## Acceptance Criteria

- [ ] SAE trained on LLM activations with >100 interpretable dimensions
- [ ] Reasoning dimension catalog documented (10+ dimensions)
- [ ] Integration with SkillOrchestrator for reasoning control
- [ ] Skills can declare required reasoning dimensions
- [ ] Steering vectors applied correctly for 2+ LLMs (Ollama + OpenAI/Anthropic)
- [ ] Unit tests >80% coverage
- [ ] Performance: <50ms overhead per LLM call
- [ ] Documentation: Architecture guide + usage examples

---

## Notes

- **Priority rationale:** P2 because prompt engineering is sufficient for MVP, but RISE enables advanced reasoning control for complex workflows
- **Deferred from Sprint 94:** Originally planned as Feature 94.4, moved to TD due to research uncertainty and time constraints
- **Research risk:** High - requires SAE training expertise and LLM activation access
