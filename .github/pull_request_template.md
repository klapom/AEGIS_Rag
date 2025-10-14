# Pull Request

## Beschreibung
<!-- Kurze Beschreibung der Änderungen -->

## Typ der Änderung
- [ ] Bug Fix (non-breaking change which fixes an issue)
- [ ] New Feature (non-breaking change which adds functionality)
- [ ] Breaking Change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Architecture Decision (new technology, framework, or design pattern)
- [ ] Refactoring (no functional changes)
- [ ] Documentation Update
- [ ] Performance Improvement

## Related Issues
<!-- Links zu Issues: Fixes #123, Related to #456 -->

---

## ⚠️ Architecture Decision Record (ADR) Checklist

**Beantworte diese Fragen bevor du fortsetzt:**

### 1. Ist dies eine neue Architektur-Entscheidung?
- [ ] Ja → **ADR erforderlich** (siehe unten)
- [ ] Nein → Weiter zu Checkliste

**Trigger für ADR (mindestens EINE muss zutreffen):**
- [ ] Neue Technologie/Framework/Library hinzugefügt
- [ ] Datenbank-Schema oder -Typ geändert
- [ ] API-Design oder Kommunikations-Pattern geändert
- [ ] Deployment-Strategie geändert
- [ ] Sicherheits-Architektur geändert
- [ ] Performance-kritische Design-Entscheidung
- [ ] Langfristige Auswirkung auf Codebase (>3 Monate)

### 2. Falls ADR erforderlich:
- [ ] **ADR-Dokument erstellt** in `docs/ADR/ADR-XXX-title.md`
- [ ] **ADR_INDEX.md aktualisiert** mit neuem ADR
- [ ] **Alternativen dokumentiert** (mindestens 2)
- [ ] **Rationale erklärt** (Warum diese Entscheidung?)
- [ ] **Consequences dokumentiert** (Positive + Negative)
- [ ] **Mitigations definiert** für negative Consequences
- [ ] **Team-Review** des ADR abgeschlossen

**Falls kein ADR erforderlich, erkläre warum:**
<!-- z.B. "Nur Bug Fix, keine Design-Änderung" -->

---

## Code Quality Checklist

### Tests
- [ ] Unit Tests hinzugefügt/aktualisiert
- [ ] Integration Tests (falls relevant)
- [ ] Test Coverage >80% für neue Files
- [ ] Alle Tests lokal erfolgreich: `pytest`

### Code Standards (automatisch geprüft via CI)
- [ ] Black Formatting: `black src/`
- [ ] Ruff Linting: `ruff check src/`
- [ ] Type Checking: `mypy src/`
- [ ] Security Scan: `bandit -r src/`

### Documentation
- [ ] Docstrings für neue Functions/Classes
- [ ] README.md aktualisiert (falls nötig)
- [ ] API Documentation aktualisiert (falls Endpoints geändert)
- [ ] CHANGELOG.md aktualisiert

### Naming Conventions
- [ ] Files: `snake_case.py`
- [ ] Classes: `PascalCase`
- [ ] Functions: `snake_case()`
- [ ] Constants: `SCREAMING_SNAKE_CASE`
- [ ] Siehe: `docs/NAMING_CONVENTIONS.md`

---

## Subagent Assignment

**Welche Subagenten waren beteiligt?** (siehe `docs/SUBAGENTS.md`)

- [ ] Backend Agent (Core Logic)
- [ ] Infrastructure Agent (DevOps)
- [ ] API Agent (REST Interface)
- [ ] Testing Agent (QA)
- [ ] Documentation Agent (Docs)

**Falls Subagenten NICHT korrekt eingesetzt:**
- [ ] Erkläre warum manuell implementiert
- [ ] Dokumentiere für zukünftige Referenz

---

## Sprint Context

**Sprint:** <!-- z.B. Sprint 2 -->
**Sprint Goal:** <!-- z.B. Vector Search Foundation -->
**Related Sprint Tasks:** <!-- Link zu SPRINT_PLAN.md Section -->

---

## Performance Impact

- [ ] Kein Performance Impact
- [ ] Performance Improvement (Benchmarks hinzufügen)
- [ ] Möglicher Performance Regression (Begründung notwendig)

**Latency Targets (falls relevant):**
- Vector Search: <200ms ✅/❌
- Graph Query: <500ms ✅/❌
- Memory Retrieval: <100ms ✅/❌

---

## Security Considerations

- [ ] Keine Secrets committed
- [ ] Input Validation implementiert
- [ ] SQL/Cypher Injection verhindert
- [ ] Authentication/Authorization beachtet
- [ ] Rate Limiting (falls API geändert)

---

## Breaking Changes

**Falls Breaking Changes:**
- [ ] Migration Guide erstellt
- [ ] Deprecation Warnings hinzugefügt (1 Sprint vorher)
- [ ] Downstream Services benachrichtigt
- [ ] Version Bump geplant (Major)

---

## Deployment Notes

- [ ] Environment Variables hinzugefügt (`.env.template` aktualisiert)
- [ ] Database Migrations erforderlich? → Script hinzufügen
- [ ] Docker Image Update erforderlich? → Version bumpen
- [ ] Kubernetes Manifests aktualisiert?
- [ ] Rollback-Strategie dokumentiert

---

## Screenshots / Logs (optional)
<!-- Falls UI-Changes oder kritische Logs -->

---

## Reviewer Notes
<!-- Besondere Punkte für Reviewer -->

---

## Post-Merge Tasks
- [ ] Deploy to Staging
- [ ] Smoke Tests in Staging
- [ ] Update Project Documentation
- [ ] Close related Issues
- [ ] Notify Team in Slack/Discord

---

## Checklist für Reviewer

**Reviewer muss prüfen:**
- [ ] ADR-Checklist vollständig (falls relevant)
- [ ] Code Quality Gates alle grün (CI Pipeline)
- [ ] Tests decken neue Funktionalität ab
- [ ] Naming Conventions eingehalten
- [ ] Keine Secrets im Code
- [ ] Performance Targets erfüllt
- [ ] Documentation vollständig

**Falls Reviewer-Feedback:**
- Nutze "Request Changes" für MUSS-Änderungen
- Nutze "Comment" für SOLL-Verbesserungen
- Nutze "Approve" nur wenn alle MUSS-Punkte erfüllt

---

**By submitting this PR, I confirm:**
- [ ] Ich habe die ADR-Checklist durchgegangen
- [ ] Ich habe alle relevanten Subagenten korrekt eingesetzt
- [ ] Ich habe die Naming Conventions befolgt
- [ ] Ich habe alle Tests lokal ausgeführt
- [ ] Ich habe die Documentation aktualisiert
