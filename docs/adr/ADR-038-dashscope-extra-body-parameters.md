# ADR-038: DashScope Custom Parameters via OpenAI SDK extra_body

**Status:** ACCEPTED
**Date:** 2025-11-19
**Sprint:** 30 (Feature 30.6)
**Related ADRs:** ADR-033 (ANY-LLM Integration), ADR-037 (Alibaba Cloud Extraction)

## Context

During Sprint 30, we enabled Alibaba Cloud (DashScope) routing for entity/relation extraction by changing `Complexity.MEDIUM` to `Complexity.HIGH` in `extraction_service.py`. While the routing logic worked correctly, Alibaba Cloud API calls failed with:

```json
{
  "error": {
    "code": "invalid_parameter_error",
    "message": "parameter.enable_thinking must be set to false for non-streaming calls"
  }
}
```

### Initial Hypothesis

We initially believed ANY-LLM was filtering `**kwargs` and not passing `enable_thinking` to the provider. However, detailed code analysis revealed a different root cause.

## Investigation & Root Cause Analysis

### Code Path Analysis (2025-11-19)

We traced the complete code path from `acompletion()` to the DashScope API:

1. **`any_llm/api.py:190`**
   ```python
   return await llm.acompletion(**all_args, **kwargs)
   ```
   ✅ `**kwargs` are forwarded (no filtering)

2. **`any_llm/providers/openai/base.py:138`**
   ```python
   completion_kwargs = self._convert_completion_params(params, **kwargs)
   ```
   ✅ kwargs are added to `completion_kwargs`

3. **`any_llm/providers/openai/base.py:48-52`**
   ```python
   @staticmethod
   def _convert_completion_params(params: CompletionParams, **kwargs: Any) -> dict[str, Any]:
       converted_params = params.model_dump(exclude_none=True, exclude={"model_id", "messages"})
       converted_params.update(kwargs)  # ← kwargs added here
       return converted_params
   ```
   ✅ kwargs are merged into the params dictionary

4. **`any_llm/providers/openai/base.py:151`**
   ```python
   response = await self.client.chat.completions.create(
       model=params.model_id,
       messages=cast("Any", params.messages),
       **completion_kwargs,  # ← Contains our kwargs
   )
   ```
   ❌ **OpenAI SDK filters unknown parameters!**

5. **`openai/resources/chat/completions/completions.py:279`**
   ```python
   def create(
       self,
       *,
       model: Union[str, ChatModel],
       messages: Iterable[ChatCompletionMessageParam],
       # ... standard parameters ...
       extra_body: Body | None = None,  # ← ONLY mechanism for custom params!
   ) -> ChatCompletion:
   ```

### Root Cause

**The OpenAI Python SDK only accepts custom parameters via `extra_body`.**

When ANY-LLM passes `enable_thinking=False` as a direct kwarg to `create()`, the OpenAI SDK raises:

```python
TypeError: AsyncCompletions.create() got an unexpected keyword argument 'enable_thinking'
```

### Why This Affects DashScope

DashScope uses an OpenAI-compatible API endpoint, so ANY-LLM maps it to `LLMProvider.OPENAI` and uses the OpenAI Python SDK client. The SDK's strict parameter validation prevents custom DashScope parameters from being passed through.

## Decision

**Use `extra_body` parameter to pass DashScope-specific parameters.**

### Implementation

```python
# In aegis_llm_proxy.py _execute_with_any_llm()
if provider == "alibaba_cloud" and not stream:
    extra_body = {}
    if "thinking" in model:
        # Thinking models (qwen3-vl-30b-a3b-thinking)
        extra_body["enable_thinking"] = True
    else:
        # Non-thinking models (qwen3-32b, qwen-turbo)
        extra_body["enable_thinking"] = False

    completion_kwargs["extra_body"] = extra_body
```

### Why This Works

1. **OpenAI SDK accepts `extra_body`** as a legitimate parameter
2. **`extra_body` is passed to the HTTP request body** without validation
3. **DashScope API receives the custom parameters** in the request body
4. **No changes needed to ANY-LLM** (it correctly forwards all kwargs)

## Consequences

### Positive

1. ✅ **Alibaba Cloud extraction works end-to-end**
   - qwen3-32b successfully extracts entities/relations
   - 7 entities extracted vs 5 with local model (better quality)
   - Cost: ~$0.00008 per extraction task

2. ✅ **Correct understanding of ANY-LLM architecture**
   - ANY-LLM does NOT filter kwargs
   - OpenAI SDK is the bottleneck, not ANY-LLM
   - Solution is provider-specific, not framework-specific

3. ✅ **Generalizable pattern for other OpenAI-compatible APIs**
   - Can use `extra_body` for other custom parameters
   - Applies to any provider mapped to `LLMProvider.OPENAI`

4. ✅ **No changes to external dependencies**
   - No need to fork/patch ANY-LLM
   - No need to fork/patch OpenAI SDK

### Negative

1. ❌ **Provider-specific code in AegisLLMProxy**
   - Need `if provider == "alibaba_cloud"` block
   - Violates some abstraction principles
   - Mitigated: Well-documented with clear rationale

2. ❌ **Fragile to OpenAI SDK changes**
   - If OpenAI SDK changes `extra_body` handling, this breaks
   - Mitigated: OpenAI SDK is stable (GA release)

3. ❌ **Not discoverable from ANY-LLM docs**
   - ANY-LLM docs say "**kwargs for provider-specific params"
   - Reality: Need `extra_body` for OpenAI-compatible providers
   - Mitigated: Documented in our ADR and code comments

## Alternatives Considered

### Alternative 1: Direct HTTP Calls (like DashScopeVLMClient)

**Approach:** Bypass ANY-LLM for DashScope and use `httpx.AsyncClient`.

**Pros:**
- Full control over request parameters
- No OpenAI SDK limitations
- Consistent with `DashScopeVLMClient` pattern

**Cons:**
- Lose ANY-LLM benefits (budget tracking, fallback, connection pooling)
- Duplicate code for API calls
- More maintenance burden

**Decision:** Rejected. The `extra_body` solution preserves ANY-LLM benefits.

### Alternative 2: Patch ANY-LLM to use extra_body

**Approach:** Modify ANY-LLM's OpenAI provider to detect custom kwargs and move them to `extra_body`.

**Pros:**
- Fixes the issue at the framework level
- Benefits all users of ANY-LLM

**Cons:**
- Requires maintaining a fork of ANY-LLM
- Unclear if upstream would accept the change
- Increases deployment complexity

**Decision:** Rejected. Not worth forking for a simple workaround.

### Alternative 3: Patch OpenAI SDK to accept custom kwargs

**Approach:** Modify OpenAI SDK to be less strict about unknown parameters.

**Pros:**
- Most "correct" solution (SDK should allow custom params)

**Cons:**
- OpenAI SDK is auto-generated from OpenAPI spec
- Changes would be overwritten on updates
- High maintenance burden

**Decision:** Rejected. Unrealistic to maintain a fork of OpenAI SDK.

## Verification

### Test Results (2025-11-19)

```bash
routing_decision: complexity=high provider=alibaba_cloud quality=high
token_usage_parsed: model=qwen3-32b provider=alibaba_cloud tokens=899
llm_request_complete: cost_usd=7.585e-05 fallback_used=False provider=alibaba_cloud
```

**Entities Extracted:**
- United Nations (ORGANIZATION)
- 1945 (EVENT)
- World War II (EVENT) ← NEW (not detected by local model)
- New York City (LOCATION)
- Antonio Guterres (PERSON)
- 2017 (EVENT)
- international peace and security (CONCEPT) ← NEW

**Quality Improvement:** 7 entities vs 5 with local model (+40%)

## Future Considerations

1. **Monitor OpenAI SDK updates** for changes to `extra_body` handling
2. **Consider upstreaming to ANY-LLM** if other users need this pattern
3. **Document pattern for other OpenAI-compatible providers** (Groq, Perplexity, etc.)

## References

- **Sprint 30 Feature 30.6:** DashScope extra_body Parameter Fix
- **Sprint 30 Feature 30.5:** Alibaba Cloud Extraction (Complexity.HIGH routing)
- **ANY-LLM Documentation:** https://mozilla-ai.github.io/any-llm/api/completion/
- **OpenAI SDK Source:** `openai/resources/chat/completions/completions.py:279`
- **DashScope API Docs:** https://www.alibabacloud.com/help/en/model-studio/

## Notes

This ADR documents a critical debugging session where we:
1. Verified routing logic works correctly (Complexity.HIGH → alibaba_cloud)
2. Traced code through 3 layers (ANY-LLM → OpenAI SDK → HTTP)
3. Identified OpenAI SDK parameter validation as the bottleneck
4. Implemented a clean solution using OpenAI SDK's official mechanism

The solution is production-ready and maintains all benefits of ANY-LLM integration (ADR-033).
