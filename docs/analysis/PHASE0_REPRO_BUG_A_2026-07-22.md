# Phase 0 Repro: Bug A (0 Entities Cold-Cache) — 2026-07-22

**Executor:** Sonnet-5 (background diagnostic session)
**Mandate:** `CRITIC_GATE_ADR_066_2026-07-22.md` Section E-0 (Fable-5), executed literally.
**Branch:** `sprint130/bug-a-qwen-prompt` (this worktree). ~35 min, one live upload,
no vLLM restart, no container recreate.

---

## A) Repro procedure executed

1. **Forensic log preservation (D-9)**, twice, before touching anything:
   `docker logs aegis-api > ...pre-phase0-*.log` (12,408 lines), repeated right before upload.
2. **Container inventory.** Found `aegis-qdrant` crash-looping (1059 restarts, WAL panic
   `Os{code:11,WouldBlock}`) — investigated, ruled out as confound: `aegis-api` (host
   network) actually talks to the *separate* `qdrant` container on `localhost:6333`
   (healthy, `documents_v1` populated). `aegis-qdrant` is unrelated/stale. Not touched.
3. **Attempted D-3 instrumentation** (traceback at `extraction_pipeline.py:236` + DEBUG
   bump, scoped to the two named modules) — edited and verified in the worktree. **Could
   not be deployed live**: `docker inspect aegis-api` shows `/app/src` is a **read-only
   bind mount** (`RW=false`) from `/home/admin/projects/aegisrag/AEGIS_Rag/src` (the main
   copy, off-limits). `docker cp` failed (`mounted volume is marked read-only`).
   Deploying would need either a container recreate (forbidden) or writing the forbidden
   main copy. **Patch exists only in this worktree.** See D/E for the consequence.
4. Fell back to the **live, unpatched** system + direct network diagnostics (sufficient,
   see B). `/health` already showed `ollama_health_check_failed` /
   `docling_health_check_failed`, both `[Errno -3] Temporary failure in name resolution`.
5. Code confirms (`aegis_llm_proxy.py:203,1006-1024`, `config.py:1076-1083`) `_call_vllm`
   posts to `f"{settings.vllm_base_url}/v1/chat/completions"`.
6. Live: `docker exec aegis-api env` → `VLLM_BASE_URL=http://vllm:8001`
   (`.env.dgx-spark` doesn't define it at all — baked-in default). `getent hosts vllm` →
   empty. `curl http://vllm:8001/v1/models` → **exit 6, "Couldn't resolve host"**.
   Nothing listens on host port 8001. The real Qwen endpoint (`192.168.178.10:32000`)
   **is** reachable from inside the container.
7. Container's own startup log (`aegis_llm_proxy_initialized`, `20:55:46`, well inside
   Fable's fail-run window) already shows this same `vllm_base_url` — no drift since.
8. Flushed `prompt_cache*` in `aegis-redis` (0 keys — already cold).
9. Built a fresh, never-seen ~8.9 KB doc (`fresh_doc_phase0.txt`, ~40 named entities) —
   "Variante B" per E-0.
10. Registered a throwaway user (`phase0_repro_bug_a`, via `/api/v1/auth/register` — the
    ragas scripts' default `admin/admin123` doesn't exist here), logged in for a JWT.
11. **Uploaded via `/api/v1/retrieval/upload`** (not `/admin/upload-fast`), namespace
    `phase0_repro_bug_a_20260722_095639`:
    ```
    HTTP_STATUS:200  TIME_TOTAL:15.79s
    {"status":"success","chunks_created":2,"embeddings_generated":2,
     "duration_seconds":15.78,"neo4j_entities":0,"neo4j_relationships":0}
    ```
    **Reproduced Bug A on the first live attempt**, cold cache, correct endpoint.
12. Pulled `docker logs aegis-api --since 2m` (249 lines), ran E-0's exact greps (B).
13. **Cleanup:** no Neo4j nodes existed under our namespace (0 entities → nothing
    written; Neo4j only stores graph data, not raw chunks). Qdrant: response's
    `collection_name` field (`aegis_rag_docs`) matched no real collection — points
    actually landed in `documents_v1` (real `QDRANT_COLLECTION` value; separate cosmetic
    bug). Deleted both points via namespace filter, verified empty.
14. Final forensic log capture (D-9) after the run.

---

## B) Key log excerpts (verbatim)

**E-0 decision-tree counters:**
```
(i)   vllm_request_complete             : 0
(ii)  parsing_llm_response              : 0
(iii) json_parse_failed_all_strategies  : 0
(iv)  chunk_extraction_failed           : 2   (= all chunks)
```
Per E-0: **(i)=0 → "Request erreicht vLLM nie → Routing/Infra-Bug → ADR-Optionen A/D
obsolet, neuer RCA-Abschnitt."** This branch fired exactly.

**Causal chain, both chunks, identical pattern:**
```
07:57:49 ...aegis_llm_proxy WARNING vllm_health_check_failed
   base_url=http://vllm:8001 error=[Errno -3] Temporary failure in name resolution

07:57:49 ...aegis_llm_proxy ERROR provider_error_fallback
   error=ConnectionError('Failed to connect to Ollama. Please check that Ollama is
   downloaded, running and accessible. https://ollama.com/download')
   fallback=local_ollama provider=local_ollama task_id=217e9b03-...

07:57:49 ...aegis_llm_proxy CRITICAL all_providers_failed
   last_provider=local_ollama
   local_error=Failed to connect to Ollama. Please check that Ollama is downloaded,
   running and accessible. https://ollama.com/download

07:57:56 ...extraction_service ERROR all_cascade_ranks_failed
   document_id=ee56010011040dae#0
   error=All LLM providers failed for task 217e9b03-98cc-4405-a5b0-ed20e954f0b1

07:57:56 ...extraction_pipeline ERROR chunk_extraction_failed
   chunk_id=6a863e75-beab-535d-94cd-d41c314da83f
   error=All LLM providers failed for task 217e9b03-98cc-4405-a5b0-ed20e954f0b1
```
(Second chunk, same pattern, 07:57:56–07:58:02.)

**Independent corroboration, not induced by me:**
```
07:56:39 health_module ERROR ollama_health_check_failed
   error=[Errno -3] Temporary failure in name resolution
07:56:39 health_module ERROR docling_health_check_failed
   error=[Errno -3] Temporary failure in name resolution
```

**Aggregate metrics (whole doc):**
```
extraction_metrics_low_ratio entities_llm=0 entities_spacy=0 entities_total=0
gleaning_rounds=0 llm_latency_ms=12622.48 relations_total=0
```
`gleaning_rounds=0` → D-7 gleaning-prompt concern not in play here.

**Retry-timing reconciliation:** `_call_vllm` retries via `stop_after_attempt(3),
wait_exponential(multiplier=5,min=5,max=30)`, and `httpx.ConnectError` is retryable
(`aegis_llm_proxy.py:106-112`). Two waits (5s+10s)≈15s ≈ observed `duration_seconds=15.78`
for the whole upload (chunks appear to run the fallback chain concurrently).

**Network diagnostics (reproducible, not log-dependent):**
```
$ docker exec aegis-api getent hosts vllm                     → (empty)
$ docker exec aegis-api curl http://vllm:8001/v1/models       → curl: (6) Could not resolve host
$ docker exec aegis-api curl http://192.168.178.10:32000/v1/models → {"id":"qwen36-35b",...}
$ docker inspect aegis-api --format '{{.HostConfig.NetworkMode}}'  → host
$ docker inspect aegis-api ... | grep src → bind .../AEGIS_Rag/src -> /app/src (RW=false)
```

---

## C) Confirmed root cause

**`aegis-api` runs with `network_mode: host`. `VLLM_BASE_URL=http://vllm:8001` and
Ollama's compose-service hostname are both docker-compose-only DNS names that don't
resolve under host networking. Every vLLM call and its Ollama fallback fail at DNS
resolution before a single byte reaches any LLM. Pure infra/routing defect — not a
prompt-compatibility issue.**

1. `_vllm_base_url = settings.vllm_base_url` (`aegis_llm_proxy.py:202`) from env
   `VLLM_BASE_URL=http://vllm:8001`.
2. `_call_vllm` posts to `f"{self._vllm_base_url}/v1/chat/completions"` (`:1006-1007`) —
   unreachable under host networking.
3. Proxy's own health check falls back to Tier-1 `local_ollama` (ADR-033) — equally
   unresolvable (same error class, confirmed independently via `/health`).
4. No further fallback fires → `all_providers_failed` (CRITICAL).
5. Raises through the cascade (`all_cascade_ranks_failed`) into the **per-chunk
   exception swallow at `extraction_pipeline.py:236`** — confirmed the key
   symptom-hiding line, exactly as Fable flagged, though the cause it hides is network
   routing, not parser/prompt.
6. Every chunk fails identically → `entities_total=0`, `relations_total=0` for the whole
   doc — the historical Bug A signature, exactly.

**Not on Fable's B7 list verbatim, but a confirmed instantiation of B7 candidate #3**
("Ablation-Setup-Artefakt: `network_mode: host`, httpx-Verhalten") — Fable named it as a
candidate, didn't chase it. This also explains **why Fable's byte-exact probes
succeeded**: those scripts hit `192.168.178.10:32000` directly, bypassing
`AegisLLMProxy`'s routing/health-check/fallback logic entirely. Routing and endpoint are
decoupled; only routing is broken.

Directly answers **F-5**: prod-compose baseline ("Compose lokal auf Baseline-Config")
has **not** been restored — `network_mode: host` + stale service-hostname env is still
live in what's nominally "prod."

**Footnote, unrelated to Bug A:** upload response's `collection_name:"aegis_rag_docs"`
matches no real collection; actual writes go to `documents_v1`. Cosmetic bug, separate
ticket, not investigated further.

---

## D) Fable's predictions vs. findings

| Hypothesis (B7/B8) | Status |
|---|---|
| **#1: exception swallow at `:236`** | **Confirmed as symptom-hiding mechanism**, exactly as predicted — but the exception is `"All LLM providers failed"` (infra), not parse/prompt as B7 left open. Fable found *where*; this session found *what*. |
| B7.1 Größeneffekt | **Not the cause** — fails before any request is sent, independent of size; real 8.9 KB/2-chunk doc gives identical 0-requests-reach-vLLM result. |
| B7.2 `prompt_cache` bypass | **Moot** — cache already empty (0 keys). |
| **B7.3 Ablation-Setup (`network_mode: host`)** | **Confirmed as root cause**, candidate → demonstrated fact. |
| B7.4 Gleaning aktiv | **Ruled out**: `gleaning_rounds=0`. |
| B7.5 Prompt-shape at real sizes | **Still untested** — no request ever reached the LLM; remains open once routing is fixed. |
| R1/R2/R3 (already refuted by Fable) | **Independently corroborated irrelevant** — requests never left the container. |
| F-5 (prod-compose baseline) | **Answered: not restored.** |

**Net:** Fable's #1 hypothesis was directionally confirmed as the right place to look;
the specific exception wasn't literally on the B7 list but falls under B7.3, which Fable
had already flagged unresolved. A validation of the Critic-Gate process, not a
refutation.

---

## E) Confidence level

**🟢 CONFIRMED**, one caveat below.

Basis: (1) unambiguous live log chain (`vllm_health_check_failed` →
`provider_error_fallback` → `all_providers_failed` → `all_cascade_ranks_failed` →
`chunk_extraction_failed`), consistent for both chunks; (2) independent
network-level proof not dependent on log interpretation (`getent` empty, `curl` exit 6,
working direct connection to the real endpoint); (3) exact code-path confirmation this
value is actually used; (4) reproduced on the **first live attempt**, cold cache,
correct endpoint.

**Caveat:** the D-3 traceback instrumentation could **not be deployed** (`/app/src`
read-only, mounted from the forbidden main copy). Root cause was established from the
**unpatched** system's existing logs + network diagnostics instead — sufficient here
because `aegis_llm_proxy.py` already logs its own fallback chain in detail, but Fable's
exact instrumentation spec was substituted for, not executed literally.
**What would remove all doubt:** (a) get write access to redeploy the prepared patch, or
(b) simpler — temporarily fix `VLLM_BASE_URL` to `http://192.168.178.10:32000` in a
throwaway test and confirm `entities > 0` on the same doc. Intentionally not done here
to stay inside Phase 0's diagnostic-only scope.

---

## F) Recommended next step

**Do not start ADR-066-v2 as a prompt-compatibility fix — that fixes a non-bug.**

1. **Cheapest remaining confirmation:** override `VLLM_BASE_URL` to
   `http://192.168.178.10:32000` in a throwaway test, re-run the identical upload,
   confirm `neo4j_entities > 0`. Converts 🟢 to closed-loop.
2. **Open a new ADR** targeting the real defect: restore `network_mode` away from
   `host` (or fix service DNS aliases) for `aegis-api`, audit
   `VLLM_BASE_URL`/`OLLAMA_BASE_URL`/`DOCLING_*` consistency. Ties directly to Klaus's
   own pending memory item ("Cleanup pending: Compose lokal auf Baseline-Config") — very
   likely the same unresolved cleanup, now with production-impact proof.
3. **ADR-066:** down-scope to just R3′ parser hardening (G7/Option D) as
   defense-in-depth; remove it as the fix for Bug A's "0 entities."
4. Re-run **F-1–F-5** with Klaus once routing is fixed; F-1 (Legacy-Cascade vs
   SpaCy-First) and F-3 (cold-cache protocol) are unaffected by this finding.
5. Once routing is fixed, still run the deferred **B7.5 check** (real chunk sizes,
   800–1800 tokens, against the actual Qwen endpoint) before declaring prompt
   compatibility fully clear.

---

## Appendix: artifacts

- Instrumentation patch (prepared, not deployed): `extraction_pipeline.py` (traceback
  at :236 + DEBUG bump), `extraction_service.py` (DEBUG bump).
- Test fixture: scratchpad `fresh_doc_phase0.txt` (~8.9 KB, never previously ingested).
- Raw logs: scratchpad `phase0_logs/` — pre/post D-9 captures, `phase0_run.log`,
  `upload_response.json`.
- Namespace used and fully cleaned up: `phase0_repro_bug_a_20260722_095639`.
