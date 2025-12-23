## AEGIS_RAG — Copilot / AI Agent Quick Instructions

This file gives a compact, actionable orientation for AI coding agents working in this repository.

- **First reading (single-shot):** [CLAUDE.md](CLAUDE.md), [README.md](README.md), [.clinerules](.clinerules)

- **Big picture (where to look):**
  - Orchestration & agents: `src/agents/` and `src/domains/` (LangGraph-based agents and domain modules).
  - API surface: `src/api/` (FastAPI routers; see `src/api/v1/chat.py` for how citations are built).
  - Core services: Qdrant (vector), Neo4j (graph), Redis (memory) — configuration & runtime notes in [CLAUDE.md](CLAUDE.md).
  - LLM routing: [config/llm_config.yml](config/llm_config.yml) and the `AegisLLMProxy` integration (see `src/domains/llm_integration/`).

- **Project-specific developer flows (commands/examples):**
  - Install deps: `poetry install` (project uses Poetry defined in `pyproject.toml`).
  - Start backend (dev): `poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000`.
  - Start frontend (dev): `cd frontend && npm install && npm run dev`.
  - Bring up local infra (when needed): `docker compose up` (see `docker/` and Docker Compose files for DGX compose variants).

- **Testing workflows:**
  - Unit tests (fast, mocked): `poetry run pytest tests/unit`.
  - Integration tests (requires services): `docker compose up qdrant neo4j redis && poetry run pytest tests/integration`.
  - E2E (Playwright): start backend+frontend, then `cd frontend && npx playwright test` or use the frontend npm script.

- **Important conventions & patterns to follow:**
  - Naming: `snake_case` for files/functions, `PascalCase` for classes, constants SCREAMING_SNAKE_CASE — enforced in `.clinerules` and `CONVENTIONS.md`.
  - Formatting + linting: `black` (line-length=100), `ruff`, `mypy (strict)` — run `poetry run ruff check` / `poetry run mypy`.
  - Lazy import patching: patch the source module, not the caller. Example from CLAUDE.md: prefer `patch("src.components.memory.get_redis_memory")` over `patch("src.api.v1.chat.get_redis_memory")`.

- **Integration edges & where to look for behavior:**
  - Citation provenance: `src/api/v1/chat.py` constructs citation maps referencing `docs/CLAUDE.md` and related docs.
  - LLM provider routing & budget: `config/llm_config.yml` (provider preferences, fallbacks, and budgets).
  - DGX Spark / GPU specifics and workarounds (FlashAttention, CUDA arch) are documented in [CLAUDE.md](CLAUDE.md).

- **Permissions & safety for automated agents:**
  - See `.clinerules` for allowed/denied shell commands and `require_confirmation` list — follow it strictly when running destructive operations.
  - Always ask before `git push`, `git clean`, `docker rm`, or any `rm`/destructive operation (these are in `.clinerules`).

- **When to propose an ADR:**
  - Any change to core frameworks, DB schemas, API design, or architecture patterns must include an ADR (see `docs/adr/` and `.clinerules: adr_required_for`).

- **Quick file references (most useful):**
  - [CLAUDE.md](CLAUDE.md) — single-source project context & DGX notes
  - [.clinerules](.clinerules) — agent permissions, coding standards reminders
  - [config/llm_config.yml](config/llm_config.yml) — LLM routing and provider config
  - [src/api/v1/chat.py](src/api/v1/chat.py) — example of endpoint + citation construction
  - [docs/CONVENTIONS.md](docs/CONVENTIONS.md) — code conventions enforced by CI

If any section is unclear or you want more depth (examples of common PR tasks, CI checks, or debugging recipes), tell me which area to expand.
