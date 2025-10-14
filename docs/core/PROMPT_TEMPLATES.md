# Claude Code Prompt Templates
## Systematische Subagenten-Delegation

Nutze diese Templates für konsistente Subagenten-Delegation in Claude Code.

---

## Template 1: Sprint Start (Wochenanfang)

```
Sprint {N} Start - {Sprint Name}

📋 KONTEXT:
- Sprint-Ziel: {aus SPRINT_PLAN.md kopieren}
- Dauer: 5 Arbeitstage
- Team-Kapazität: {Story Points}

📖 REFERENZEN:
- CLAUDE.md: Projekt-Context
- SPRINT_PLAN.md: Sprint {N} Deliverables
- SUBAGENTS.md: Delegation Strategy
- ADR_INDEX.md: Relevante ADRs

🎯 AUFGABEN DIESER WOCHE:
{Liste aus SPRINT_PLAN.md}

🤝 SUBAGENTEN-DELEGATION:
Bitte plane die optimale Subagenten-Verteilung:
1. Analysiere alle Tasks
2. Identifiziere Abhängigkeiten
3. Schlage vor: Parallel vs. Sequential
4. Definiere Handoff-Punkte

WICHTIG:
- Nutze SUBAGENTS.md für Responsibilities
- Beachte File Ownership
- Plane Kontext-Sharing
```

---

## Template 2: Feature Implementation (Standard Task)

```
Feature: {Feature Name}

📋 KONTEXT:
- Sprint: {N}
- Component: {z.B. Vector Search, Graph RAG, Memory}
- Referenz: CLAUDE.md Section "{relevante Section}"

🎯 REQUIREMENTS:
{Detaillierte Anforderungen}

🔗 ABHÄNGIGKEITEN:
- Benötigt: {andere Module/Services}
- Blockiert: {andere Tasks}

👥 SUBAGENTEN-ASSIGNMENT (OBLIGATORISCH):

**Backend Agent:**
- Implementiere Core Logic
- File: src/components/{component}/{module}.py
- Standards: NAMING_CONVENTIONS.md
- Tests: >80% Coverage erforderlich

**API Agent:**
- Endpoint: POST /api/v1/{endpoint}
- Request/Response Models
- OpenAPI Documentation
- Rate Limiting: 10/min per user

**Testing Agent:**
- Unit Tests: tests/unit/components/{component}/
- Integration Tests: tests/integration/
- Fixtures in conftest.py
- Mock External Dependencies

**Infrastructure Agent:**
- Docker: Neue Services falls erforderlich
- Environment Variables in .env.template
- CI Pipeline: Update falls neue Dependencies

**Documentation Agent:**
- API Docs: docs/api/{endpoint}.md
- Code Examples
- README.md Update falls nötig

⚠️ ADR-CHECK:
- Ist dies eine Architektur-Entscheidung? {Ja/Nein}
- Falls JA: ADR-XXX erstellen vor Implementation

🎯 SUCCESS CRITERIA:
- Alle Tests grün
- Coverage >80%
- Dokumentation vollständig
- Keine Pre-commit Errors
- Performance Targets erfüllt: {Latency/Throughput}
```

---

## Template 3: Bug Fix (Fokussierte Aufgabe)

```
Bug Fix: {Issue #XXX - Bug Title}

🐛 PROBLEM:
{Beschreibung des Bugs}

📋 KONTEXT:
- Affected Component: {Component}
- Severity: {Low/Medium/High/Critical}
- User Impact: {Beschreibung}

🔍 ROOT CAUSE ANALYSIS:
{Falls bekannt, sonst: "Zu ermitteln"}

👥 SUBAGENTEN-ASSIGNMENT:

**Backend Agent:**
- Debugge Root Cause
- Implementiere Fix in {betroffene Files}
- Folge NAMING_CONVENTIONS.md

**Testing Agent:**
- Regression Test für diesen Bug
- Existierende Tests erweitern
- Edge Cases abdecken

**Documentation Agent:**
- Update CLAUDE.md "Common Issues" falls recurring
- Update QUICK_START.md Troubleshooting falls Setup-Issue

⚠️ KEIN ADR erforderlich (Bug Fix, keine Design-Änderung)

✅ DEFINITION OF DONE:
- Bug nicht mehr reproduzierbar
- Test verhindert Regression
- Root Cause dokumentiert
```

---

## Template 4: ADR-pflichtige Änderung

```
Architecture Decision: {Entscheidungs-Titel}

📋 KONTEXT:
- Current State: {Was ist aktuell}
- Problem: {Warum ändern}
- Impact: {Wer/Was ist betroffen}

🤔 ALTERNATIVEN:
1. {Option 1}
   Pro: ...
   Contra: ...
2. {Option 2}
   Pro: ...
   Contra: ...
3. {Gewählte Option}
   Pro: ...
   Contra: ...
   Rationale: {Warum gewählt}

⚠️ ADR ERFORDERLICH - ERSTELLE ZUERST:

**Documentation Agent:**
1. Erstelle docs/ADR/ADR-{XXX}-{title}.md
2. Nutze ADR_TEMPLATE aus ADR_INDEX.md
3. Dokumentiere alle 3 Alternativen
4. Fülle Rationale + Consequences aus
5. Update ADR_INDEX.md

**Team Review des ADR:**
- [ ] Tech Lead Approval
- [ ] Team Consensus
- [ ] Consequences verstanden
- [ ] Mitigations definiert

NUR DANN Implementation:

**Backend Agent:**
- Implementiere gewählte Option
- Referenziere ADR-XXX in Code Comments

**Infrastructure Agent:**
- Setup neue Infrastruktur falls erforderlich
- Update docker-compose.yml, CI/CD

**Testing Agent:**
- Teste neue Implementation
- Performance Benchmarks vor/nach

**Documentation Agent:**
- Update TECH_STACK.md
- Update CLAUDE.md mit neuen Patterns
```

---

## Template 5: Sprint Review (Wochenende)

```
Sprint {N} Review & Retrospective

📊 DELIVERABLES CHECK:
Gemäß SPRINT_PLAN.md Sprint {N}:
- [ ] Deliverable 1: {Status}
- [ ] Deliverable 2: {Status}
- [ ] ...

✅ SUCCESS CRITERIA:
- [ ] Alle Tests grün
- [ ] Coverage >80%
- [ ] CI Pipeline grün
- [ ] Documentation vollständig
- [ ] Demo erfolgreich

👥 SUBAGENTEN PERFORMANCE:
**Backend Agent:**
- Tasks completed: {Anzahl}
- Rework rate: {Prozent}
- Code quality: {Score}

**Infrastructure Agent:**
- Deployment successful: {Ja/Nein}
- Incidents: {Anzahl}

{... für alle Subagenten}

🔄 RETROSPECTIVE:
**What went well:**
- ...

**What needs improvement:**
- ...

**Action Items für nächsten Sprint:**
- [ ] Action 1
- [ ] Action 2

📋 DOCUMENTATION UPDATES:
- [ ] SPRINT_PLAN.md: Sprint {N} als "completed" markieren
- [ ] CLAUDE.md: "Common Issues" erweitern falls neue gefunden
- [ ] TECH_STACK.md: Update falls Dependencies geändert
- [ ] ADR_INDEX.md: Neue ADRs hinzufügen

🚀 SPRINT {N+1} VORBEREITUNG:
- Lies SPRINT_PLAN.md Sprint {N+1}
- Identifiziere Blockers
- Plane Subagenten-Delegation
```

---

## Template 6: Emergency Hotfix

```
HOTFIX: {Critical Issue}

🚨 SEVERITY: CRITICAL
- Production down: {Ja/Nein}
- User impact: {Beschreibung}
- Time since incident: {Minuten}

🎯 IMMEDIATE ACTION:

**Backend Agent (PRIORITY):**
- Schnellste Lösung implementieren
- Code Quality temporär zweitrangig
- Fokus: System stabilisieren

**Testing Agent:**
- Minimale Tests für Hotfix
- Full Test Suite später

**Infrastructure Agent:**
- Deploy Hotfix ASAP
- Rollback-Plan bereit

⚠️ POST-HOTFIX (nach Stabilisierung):
- [ ] Root Cause Analysis dokumentieren
- [ ] Proper Fix mit Tests implementieren
- [ ] ADR falls Architektur-Änderung
- [ ] Post-Mortem Document erstellen
```

---

## Template 7: Dependency Update

```
Dependency Update: {Package Name} {Old Version} → {New Version}

📋 KONTEXT:
- Package: {Name}
- Change Type: {Patch/Minor/Major}
- Reason: {Security/Feature/Bug Fix}

🔍 BREAKING CHANGES:
{Aus Changelog/Migration Guide}

👥 SUBAGENTEN-ASSIGNMENT:

**Infrastructure Agent:**
- Update pyproject.toml / requirements.txt
- Update docker-compose.yml falls Image Update
- Test Docker Build

**Backend Agent:**
- Code-Änderungen für Breaking Changes
- Update Imports falls API geändert

**Testing Agent:**
- Komplette Test Suite ausführen
- Integration Tests fokussieren
- Performance Regression prüfen

**Documentation Agent:**
- Update TECH_STACK.md mit neuer Version
- Migration Notes falls Major Update

⚠️ ADR-CHECK:
- Major Version Update? → Erwäge ADR
- Breaking Changes? → ADR erforderlich
```

---

## Template 8: Code Review Feedback

```
Address Review Feedback: PR #{Number}

📋 FEEDBACK SUMMARY:
{Zusammenfassung der Review Comments}

👥 SUBAGENTEN ZUR BEHEBUNG:

**Backend Agent:**
Behebt folgende Code-Issues:
- {Issue 1}
- {Issue 2}

**Testing Agent:**
Erweitert Tests für:
- {Coverage Gap 1}
- {Edge Case 2}

**Documentation Agent:**
Verbessert Documentation für:
- {Missing Docstring 1}
- {Unclear API Doc 2}

✅ RE-REVIEW CRITERIA:
- Alle Reviewer Comments addressed
- Neue Tests für Coverage Gaps
- Documentation vollständig
- Keine neuen Issues introduced
```

---

## Automatisierung: Prompt-Template-Selector

```python
# scripts/select_prompt_template.py
def select_template(task_type: str) -> str:
    """
    Wählt das passende Prompt Template basierend auf Task-Typ.
    
    Usage in Claude Code:
    "Bitte nutze Template für {task_type}"
    """
    templates = {
        "sprint_start": "Template 1: Sprint Start",
        "feature": "Template 2: Feature Implementation",
        "bug": "Template 3: Bug Fix",
        "adr": "Template 4: ADR-pflichtige Änderung",
        "sprint_review": "Template 5: Sprint Review",
        "hotfix": "Template 6: Emergency Hotfix",
        "dependency": "Template 7: Dependency Update",
        "review": "Template 8: Code Review Feedback",
    }
    return templates.get(task_type, "Template 2: Feature Implementation")
```

---

## Enforcement durch CODEOWNERS

```
# .github/CODEOWNERS
# Automatische Reviewer-Zuweisung basierend auf File

# Backend Agent Territory
src/agents/**                 @backend-team
src/components/**             @backend-team
src/core/**                   @backend-team
src/utils/**                  @backend-team

# Infrastructure Agent Territory
docker/**                     @infrastructure-team
k8s/**                        @infrastructure-team
.github/workflows/**          @infrastructure-team
scripts/setup*.sh             @infrastructure-team

# API Agent Territory
src/api/**                    @api-team
src/models/**                 @api-team

# Testing Agent Territory
tests/**                      @testing-team

# Documentation Agent Territory
docs/**                       @documentation-team
README.md                     @documentation-team
*.md                          @documentation-team

# ADRs require Tech Lead
docs/ADR/**                   @tech-lead @backend-team

# Critical configs require multiple approvals
pyproject.toml                @backend-team @infrastructure-team
docker-compose.yml            @infrastructure-team @backend-team
```

---

## Daily Checklist für Claude Code Sessions

**JEDEN TAG vor Start:**
```
[ ] CLAUDE.md gelesen (Project Context aktuell?)
[ ] SPRINT_PLAN.md gecheckt (heutiges Ziel klar?)
[ ] Template ausgewählt (passendes Template für Task?)
[ ] Subagenten geplant (welche Agents heute?)
[ ] ADR-Check (brauche ich ADR heute?)
```

**JEDEN TAG nach Session:**
```
[ ] Alle Subagenten korrekt eingesetzt?
[ ] Tests geschrieben (>80% Coverage)?
[ ] Documentation aktualisiert?
[ ] Commit Message folgt Convention?
[ ] ADR erstellt falls erforderlich?
[ ] SPRINT_PLAN.md Progress aktualisiert?
```

---

## Nutzung in Claude Code

**Beispiel Session-Start:**
```
Hey Claude!

Context: Ich starte heute mit Sprint 2, Tag 1.

Bitte:
1. Lies CLAUDE.md (Project Context)
2. Lies SPRINT_PLAN.md Sprint 2
3. Lies SUBAGENTS.md (Delegation Guide)
4. Nutze "Template 1: Sprint Start"

Plane dann die Woche optimal mit Subagenten-Delegation.
```

**Beispiel Feature Start:**
```
Hey Claude!

Task: Implementiere Hybrid Search (Sprint 2, Tag 2)

Bitte:
1. Nutze "Template 2: Feature Implementation"
2. Delegiere an alle relevanten Subagenten
3. Erstelle ADR falls Architektur-Entscheidung

Kontext ist in CLAUDE.md Section "Hybrid Search Implementation"
```

---

Diese Templates stellen sicher, dass du IMMER systematisch vorgehst und keine Subagenten vergisst!
