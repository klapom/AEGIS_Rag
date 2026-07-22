# ADR-067: docker-compose.dgx-spark.yml an tatsächlichen Runtime-Stand angleichen (Bug-A-Fix)

**Status:** Proposed — Option X (aus [[Sprint-130 Bug A Diagnose-Kette]])
**Datum:** 2026-07-22
**Autor:** Opus 4.7 (Sonnet-Phase-0-Repro als Beleg-Basis)
**Ersetzt:** ADR-066-Draft (verworfen nach Fable Critic-Gate 🔴, siehe `docs/analysis/CRITIC_GATE_ADR_066_2026-07-22.md`)

## Kontext

Bug A (Qwen produziert 0 Entities cold-cache) hat sich als **Netzwerk-Konfigurations-Fehler** herausgestellt, nicht als Prompt-Inkompatibilität. Vollständiger Diagnose-Pfad:

1. Ausgangs-Vermutung (ADR-066-Draft, verworfen): DSPy-Prompts sind Nemotron-only, JSON-Parser hat `<think>`-Bypass. **Alle drei R1/R2/R3 empirisch refuted** von Fable via Live-Probes.
2. Fable-Neu-Suspect: swallowed exception bei `extraction_pipeline.py:236`
3. Phase-0-Repro (Sonnet, `docs/analysis/PHASE0_REPRO_BUG_A_2026-07-22.md`): Root Cause = `aegis-api` läuft mit `network_mode: host`, aber `VLLM_BASE_URL=http://vllm:8001` — ein compose-DNS-Name der unter host-networking nicht existiert. Ollama-Fallback ebenso. Alle LLM-Calls scheitern bei DNS-Resolution.

**Wiederholte Verifikation heute:**
```
Host → 192.168.178.10:32000/v1/models     HTTP 200 in 1ms  (Qwen aktiv)
aegis-api INTERN → 192.168.178.10:32000   HTTP 200 in 0.8ms (direkt erreichbar)
aegis-api INTERN → vllm:8001              NXDOMAIN, HTTP 000 (DNS-fail)
```

Der Container **kann Qwen direkt erreichen**. Nur die env var zeigt auf den falschen Hostnamen.

**Weiterer Runtime-Realitäts-Delta zum `docker-compose.dgx-spark.yml`:**

| Container | Compose sagt | Realität | Konflikt |
|---|---|---|---|
| `aegis-qdrant` | v1.11.0, `qdrant_data`-Volume | Restart-Loop | manueller `qdrant:v1.17.1` (seit 2026-07-13) hält dasselbe Volume — WAL-File-Lock; Downgrade wäre potenziell datenverlustträchtig |
| `aegis-vllm` | Service definiert, `profiles: [ingestion]` | nie gestartet | echter Qwen läuft als `secretary-vllm-qwen36` auf externer IP (nicht im aegis-network) |
| `aegis-api` | `VLLM_BASE_URL=http://vllm:8001` hardcoded (keine env-Substitution) | `.env` will `http://192.168.178.10:32000` | Compose ignoriert `.env` weil kein `${VAR}`-Placeholder |

## Optionen

### Option X — Compose an Realität angleichen (empfohlen)

**Compose-Änderungen:**
1. `aegis-qdrant` bekommt `profiles: [managed-qdrant]` → wird nur explizit gestartet. Der manuelle `qdrant:v1.17.1` bleibt Prod-Container.
2. `aegis-api` env: `VLLM_BASE_URL=${VLLM_BASE_URL:-http://vllm:8001}` und `VLLM_MODEL=${VLLM_MODEL:-...}` — env-Substitution einführen.
3. `aegis-vllm` bleibt unverändert (`profiles: [ingestion]` ist bereits korrekt).

**Runtime-Aktionen:**
4. Manueller `qdrant`-Container zusätzlich ins `aegis_rag_aegis-network` einhängen (mit Alias `qdrant` UND `aegis-qdrant`) — dann kennt aegis-api ihn per compose-DNS ohne dass qdrant sein bestehendes Netz verliert.
5. Toten `aegis-qdrant`-Container (Restart-Loop) entfernen (`docker rm aegis-qdrant`) — er hält kein Volume-Lock mehr, nur die Verwirrung.
6. `aegis-api` recreate: `docker compose up -d aegis-api --no-deps --force-recreate` — nimmt neue env aus `.env`, kommt ins aegis-network, DNS zu qdrant + IP zu Qwen funktioniert.

**Aufwand:** ~30 min inklusive Test. **Datenverlust-Risiko:** nein.

### Option Y — Compose-Sollzustand durchsetzen (v1.11.0)
Manuellen qdrant stoppen, aegis-qdrant starten. **Risiko:** Qdrant v1.17.1 → v1.11.0 ist Downgrade über 6 Minor-Versions; Data-Format-Kompatibilität nicht garantiert. Betroffen wäre u.a. `suki_memories` (Persona-Daten pommer-agents).

### Option Z — Backup + Migration
Vollständiger Volume-Snapshot vor Y. Sicherer, aber 1-2h Aufwand. Nur nötig wenn wir aus anderen Gründen zwingend auf v1.11.0 müssen (unbekannt).

## Entscheidung

**Option X.** Der manuelle `qdrant:v1.17.1` läuft seit 9 Tagen stabil und ist de facto Prod. Compose-Sollzustand (Y/Z) würde eine gelaufene Migration rückwärts abwickeln ohne Nutzen. X ist verlustfrei, minimal invasiv, und macht `.env` zur autoritativen Source-of-Truth für Model-Endpoints.

## Änderungs-Diff (verbindliche Spec für den Fix-Commit)

### `docker-compose.dgx-spark.yml`

**Change 1 — aegis-qdrant profile:**
```diff
   qdrant:
     image: qdrant/qdrant:v1.11.0
     container_name: aegis-qdrant
+    profiles:
+      - managed-qdrant
     # Sprint 122: Prevent "Too many open files" error during E2E test runs
```

**Change 2 — aegis-api VLLM env-Substitution:**
```diff
       - VLLM_ENABLED=${VLLM_ENABLED:-false}
-      - VLLM_BASE_URL=http://vllm:8001
-      - VLLM_MODEL=nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4
+      - VLLM_BASE_URL=${VLLM_BASE_URL:-http://vllm:8001}
+      - VLLM_MODEL=${VLLM_MODEL:-nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4}
```

### Runtime-Kommandos (nicht im compose)

```bash
# 1. Manuellen qdrant ins aegis-network einhängen (behält bridge-network)
docker network connect --alias qdrant --alias aegis-qdrant \
  aegis_rag_aegis-network qdrant

# 2. Toten aegis-qdrant compose-Container entfernen
docker rm -f aegis-qdrant

# 3. aegis-api mit Prod-config recreaten (im AEGIS_Rag/ working copy)
cd /home/admin/projects/aegisrag/AEGIS_Rag
docker compose -f docker-compose.dgx-spark.yml \
  up -d aegis-api --no-deps --force-recreate
```

## Akzeptanz-Kriterien

**AC-1 (Netzwerk):** `docker exec aegis-api getent hosts qdrant` liefert IP im aegis-network (nicht NXDOMAIN).

**AC-2 (LLM-Endpoint):** `docker exec aegis-api curl -s -o /dev/null -w "%{http_code}" http://192.168.178.10:32000/v1/models` = 200.

**AC-3 (env):** `docker inspect aegis-api --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -E "VLLM_BASE_URL|QDRANT_HOST|NEO4J_URI"` liefert:
```
VLLM_BASE_URL=http://192.168.178.10:32000
VLLM_MODEL=qwen36-35b
QDRANT_HOST=qdrant
NEO4J_URI=bolt://neo4j:7687
```

**AC-4 (Ingestion — der eigentliche Fix-Beleg):** Frisches 13 KB Doc via `POST /api/v1/retrieval/upload` mit Test-Namespace `adr_067_verify_<timestamp>`. Response body meldet `entities_count > 0` (Baseline war 60–100 auf 13 KB). Bei `= 0` ist die Diagnose falsch und der ADR ist zurückzurollen.

**AC-5 (Rollback):** Reverse-Kommandos dokumentiert:
```bash
docker network disconnect aegis_rag_aegis-network qdrant
git revert <compose-commit-sha>
docker compose -f docker-compose.dgx-spark.yml up -d aegis-api --no-deps --force-recreate
```

## Blast-Radius

- **aegis-api:** ~30s Downtime während recreate. Wird nur aegis-api recreated (`--no-deps`), keine anderen Services angefasst.
- **qdrant (v1.17.1):** unverändert, bekommt nur zusätzliches Netzwerk-Interface (aegis-network). Kein Datenzugriff-Wechsel.
- **aegis-neo4j:** unverändert.
- **secretary-vllm-qwen36:** unverändert. Kein Restart. Pommer-agents ungestört.
- **mcp-gateway-redis-1:** unverändert, aber aegis-api spricht nach recreate wieder mit `aegis-redis` (compose-DNS), nicht mehr mit dem gateway-Redis. Der prompt_cache dort ist ohnehin geleert.

## Referenzen

- Diagnose-Kette: [[ADR-066-Draft]] → `CRITIC_GATE_ADR_066_2026-07-22.md` → `PHASE0_REPRO_BUG_A_2026-07-22.md`
- Ablation-Session: `BASELINE_ROUND2_ABLATION_2026-07-21.md`
- Aegis-Compose: `docker-compose.dgx-spark.yml` (Basis: HEAD von `origin/main`)
- Memory: [[bug_qwen_produces_zero_entities_cold_cache]], [[cleanup_pending]]

## Follow-ups (out of scope für ADR-067)

- **PR-2 zu ADR-064 (Round 2 hart löschen):** entblockt sobald AC-4 grün. Separate PR.
- **ADR für Bug B (`model_hint`-Sourcing im Proxy):** Sprint 131 (Task #3).
- **`aegis-vllm` service ganz entfernen ODER als Dokumentation behalten:** wenn du externen Qwen dauerhaft nutzt, könnte man den compose-Block löschen oder auf `profiles: [never]` setzen. Zurückgestellt bis externer Qwen als Prod-Standard bestätigt ist.
- **`aegis-qdrant` v1.11.0 → v1.17.1 im compose-file gleichziehen:** wenn du den compose-managed Weg zukünftig aktivieren willst, muss die Image-Version passen. Zurückgestellt bis dahin.
