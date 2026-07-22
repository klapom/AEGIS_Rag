# Rollback Drill: ADR-067 — 2026-07-22

**Executor:** Sonnet-5, live prod (DGX Spark). Klaus-authorized destructive drill.
**Window:** ~20:11–20:24 CEST (18:11–18:22 UTC, matches container log timestamps).
**Result:** 🟡 Rollback commands work, but AC-5 as literally documented is **incomplete** —
it produces a *harder* failure than the original Bug A signature unless decomposed.

---

## A) Executed commands, verbatim, in order

```bash
# 1. Snapshot fixed compose
cp docker-compose.dgx-spark.yml /tmp/adr067_drill_compose_before.yml
md5sum ... # 312dec23...  before and after — byte-identical, confirmed at end too

# 2. Revert compose to origin/main (pre-ADR-067)
git -C AEGIS_Rag show origin/main:docker-compose.dgx-spark.yml > docker-compose.dgx-spark.yml
# diff confirmed exactly the 4 ADR-067 changes reverted: qdrant profile, redis
# expose->ports, prometheus/api depends_on:qdrant restored, VLLM_BASE_URL/MODEL
# hardcoded again. No syntax errors on revert.

# 3. Undo qdrant network attach (per AC-5)
docker network disconnect aegis_rag_aegis-network qdrant   # exit 0

# 4. Recreate aegis-api on reverted compose
docker compose -f docker-compose.dgx-spark.yml --profile chat up -d api --no-deps --force-recreate
# Container aegis-api Recreated/Started — NO validation error despite qdrant
# depends_on referencing a service moved out of default profile scope.
```

**Result of step 4, immediately:** `network_mode` stayed `aegis_rag_aegis-network`
(NOT `host`). **Deviation #1**: `network_mode: host` was never a compose setting in
either version of `docker-compose.dgx-spark.yml` — it was a manual runtime artifact
from the 2026-07-21 ablation session (`docker run`/`docker update`-style override
outside compose). AC-5's reverse commands cannot and do not reproduce it. The env
var still flips to `VLLM_BASE_URL=http://vllm:8001` as documented, and that alone is
sufficient to break extraction (see C).

## B) Verify-broken probes

```
$ docker exec aegis-api getent hosts vllm            → (empty, exit 2)
$ docker exec aegis-api curl ...vllm:8001/v1/models  → HTTP_CODE:000
$ docker exec aegis-api curl ...192.168.178.10:32000 → HTTP_CODE:200  (still reachable)
$ docker exec aegis-api getent hosts qdrant           → (empty, exit 2 — disconnected)
```
AC-1/AC-2 style probes confirm exactly the predicted DNS-fail / direct-IP-reachable
split for vLLM.

**Load-bearing test, attempt 1** (`rollback_drill_broken_<ts>`, full AC-5 reverse:
compose reverted + qdrant disconnected):
```json
{"error":{"code":"INTERNAL_SERVER_ERROR",
 "message":"Failed to process file: RetryError[<Future ... raised VectorSearchError>]"}}
HTTP_STATUS:500  TIME_TOTAL:5.8s
```
Log: `DNS resolution failed for qdrant:6334: C-ares status is not ARES_SUCCESS`.
**Deviation #2 (the real finding):** upload fails *before reaching LLM extraction at
all* — hard 500, zero chunks stored. This is **not** the historical Bug A signature
(soft failure: chunks stored, 0 entities). Root cause: in the original bug,
`network_mode: host` gave `aegis-api` access to qdrant via `localhost:6333`
(host-published port); AC-5's reverse disconnects qdrant from the compose network but
has no equivalent fallback path since `network_mode` was never reverted (can't be,
it's not in compose). The two rollback actions (env revert + network disconnect),
applied together as documented, compound into a worse failure than history ever
produced.

**Isolation test** (reconnected qdrant, kept `VLLM_BASE_URL=http://vllm:8001` reverted)
— confirms the *actual* Bug A causal chain is the env var alone:
```json
{"status":"success","chunks_created":2,"embeddings_generated":2,"points_indexed":2,
 "neo4j_entities":0,"neo4j_relationships":0}
HTTP_STATUS:200  TIME_TOTAL:116.35s
```
Log chain (exact match to `PHASE0_REPRO_BUG_A_2026-07-22.md`):
```
all_cascade_ranks_failed  error=Provider vllm failed in INGESTION mode.
  Ollama is not available. Error: [Errno -3] Temporary failure in name resolution
chunk_extraction_failed   (both chunks)
extraction_metrics_low_ratio entities_total=0 relations_total=0 gleaning_rounds=0
```
**Confirmed: 0 entities, 0 relations, chunks_created=2/points_indexed=2** — byte-for-byte
the historical Bug A signature. Duration 116s vs Phase0's 15.8s: more retry/backoff
cycles because Ollama fallback is *reachable* here (unlike host-mode) yet still fails
for INGESTION-mode routing reasons — a secondary, previously-undocumented detail, not
chased further (out of scope; extraction still nets 0 entities either way).

## C) Root cause reconfirmed

`VLLM_BASE_URL=http://vllm:8001` hardcoded (no `${VAR}` substitution) is sufficient,
on its own, to reproduce Bug A exactly — independent of `network_mode`. This is good
news for the ADR: the *documented* fix (env-substitution) is the right and minimal
fix. The bad news is scoped to AC-5's rollback recipe, not the fix itself.

## D) Restore + verify-fixed

```bash
cp /tmp/adr067_drill_compose_before.yml docker-compose.dgx-spark.yml   # byte-identical, confirmed md5
docker network connect --alias qdrant --alias aegis-qdrant aegis_rag_aegis-network qdrant  # (already done in isolation test)
docker compose -f docker-compose.dgx-spark.yml --profile chat up -d api --no-deps --force-recreate
```
Health: `starting` → `healthy` in ~10s. Env restored exactly:
`VLLM_BASE_URL=http://192.168.178.10:32000`, `VLLM_MODEL=qwen36-35b`,
`QDRANT_HOST=qdrant`, `NEO4J_URI=bolt://neo4j:7687`.

Fresh 13.4 KB doc, `rollback_drill_fixed_<ts>`:
```
extraction_metrics_success entities_total=89 relations_total=219
  top_entity_types=[LOCATION:41, PERSON:26, ORGANIZATION:14, EVENT:4, CONCEPT:3]
  cascade_rank_used=1  gleaning_rounds=0
```
Real `vllm_request_complete` log lines throughout (18 chunks × real token counts),
confirming genuine Qwen round-trips, not a cached/fallback path. **89 entities / 219
relations — fix verified working end-to-end**, consistent in kind with the earlier
AC-4 baseline (41/183 on a different random doc).

## E) Cleanup

- Neo4j: 62 nodes (`rollback_drill_fixed_...`) found and `DETACH DELETE`d, verified 0
  remaining. No nodes existed for either broken-state namespace (0 entities → nothing
  written, as expected).
- Qdrant `documents_v1`: 2 points each for `rollback_drill_fixed_...` and
  `rollback_drill_broken_isolate2_...` (the one successful-upload broken-state run),
  deleted by namespace filter, verified 0 remaining in all four namespaces used.
- Test user `rollback_drill_user` left in place (not requested for cleanup, harmless).

## F) Final state verification

`aegis-api` healthy, on `aegis_rag_aegis-network`, env matches pre-drill exactly.
`docker-compose.dgx-spark.yml` byte-identical (md5) to pre-drill snapshot and to
worktree HEAD. Qdrant back on both `bridge` and `aegis_rag_aegis-network`. No other
container touched (`aegis-neo4j` 9d uptime unchanged, `aegis-redis`/`aegis-ollama`
untouched, `secretary-vllm-qwen36` never restarted).

**Noted, unrelated to this drill:** `git status` on the main working copy shows
`frontend/vite.config.ts` modified (`allowedHosts: 'aegis...' → 'app-aegis...'`) — not
made by this session; flagging for visibility only, not reverted, out of scope.

## G) Verdict

🟡 **Rollback docs work, with one gap worth fixing in the ADR text.**

- The **compose-level reverse** (env var hardcoding) is accurate and sufficient on its
  own to reproduce Bug A exactly (0 entities, chunks stored, identical log chain).
- The **network-disconnect step in AC-5**, when combined with the compose revert
  *without* also restoring `network_mode: host` (which AC-5 cannot do — it was never
  compose-managed), produces a different and harder failure (hard 500 pre-extraction,
  no chunks stored) than the historical bug. Anyone running AC-5 literally to
  "prove the rollback" would see a *different* symptom than Bug A and could
  misdiagnose it as a new/separate defect.
- **Recommended ADR-067 fix:** either (a) note in AC-5 that the qdrant-disconnect
  step is optional/only meaningful if `network_mode: host` is also manually
  reapplied, or (b) drop the qdrant-disconnect line from AC-5 entirely since it does
  not participate in Bug A's actual causal chain (confirmed here: the env-var-only
  reverse fully reproduces Bug A without it).

## Appendix: artifacts

- Compose snapshot: `/tmp/adr067_drill_compose_before.yml` (md5 `312dec23...`, used to
  restore byte-exact).
- Full log capture: scratchpad `broken_isolate_full.log`.
- Test fixtures: scratchpad `rollback_drill_broken.txt` (13.3 KB), `rollback_drill_fixed.txt`
  (13.4 KB).
- Namespaces used and fully cleaned: `rollback_drill_broken_<ts>`,
  `rollback_drill_broken_isolate_<ts>`, `rollback_drill_broken_isolate2_<ts>`,
  `rollback_drill_fixed_<ts>` (ts = `20260722_201344`).
