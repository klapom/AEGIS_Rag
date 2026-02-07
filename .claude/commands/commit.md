# /commit — Sprint-Aware Commit, Docs Update & Push

You are performing a complete Sprint-aware commit workflow for AegisRAG. Follow these steps IN ORDER:

## Step 1: Analyze Changes

Run `git status` and `git diff --stat HEAD` to understand what changed.
Identify which Sprint the changes belong to (check commit messages, file paths, SPRINT_PLAN.md).

## Step 2: Update Documentation (if code changes present)

Check EACH of these documents and update if the changes warrant it:

### A. SPRINT_PLAN.md (`docs/sprints/SPRINT_PLAN.md`)
- If current sprint features changed: update feature table, status, SP
- If sprint completed: update "Current Sprint Status" section
- If cumulative SP table is stale: update it

### B. DECISION_LOG.md (`docs/DECISION_LOG.md`)
- If architectural decisions were made: add new entries in Sprint section
- Update "Total Decisions Documented" count and "Last Updated" date at bottom

### C. CLAUDE.md (root)
- If a sprint was completed: add/update the "Sprint X Complete:" one-liner
- Keep it to ONE line, compact format matching existing entries

### D. TECH_STACK.md (`docs/TECH_STACK.md`)
- Only if new technologies, frameworks, or architectural patterns were added
- Update "Last Updated" date if changed

### E. ADR_INDEX.md (`docs/adr/ADR_INDEX.md`)
- Only if new ADR files were created

### F. Root Cleanup
- Check for temp .md files in root directory that should be in `docs/sprints/archive/`

**IMPORTANT:** Skip docs that don't need updating. Don't update docs just for the sake of it.
If only documentation was changed (no code), skip Step 2 entirely.

## Step 3: Create Commit

1. Stage all relevant files with `git add` (list files explicitly, never use `git add -A`)
2. NEVER stage `.env`, `.env.backup`, credentials, or `searxng/` directory
3. Create commit with message format:
   ```
   <type>(<scope>): <subject>

   <body - what changed and why>

   Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
   ```
   Types: feat, fix, docs, style, refactor, test, chore
   Scopes: sprint126, vector, graph, memory, agent, api, infra, frontend

## Step 4: Push

Run `git push origin main` (or current branch).

## Step 5: Confirm

Show a summary:
- Commit hash + message (first line)
- Files changed count
- Docs updated (list which ones)
- Push status
