# Enforcement-Mechanismen - Kompletter Überblick
## So stellst du Qualität, ADRs und Subagenten sicher

---

## 🎯 Drei kritische Fragen - Drei Lösungen

### 1️⃣ Wie stelle ich sicher, dass ADRs erzeugt werden?

**Antwort:** 4-stufiger Prozess

#### Stufe 1: Pre-commit Hook (Warnung)
```bash
# Installiert via .pre-commit-config.yaml
# Script: scripts/check_adr.py

Bei Commit wird automatisch geprüft:
- Commit Message enthält Architektur-Keywords?
- Änderungen in ADR-relevanten Files (pyproject.toml, docker-compose.yml)?

Falls JA → ⚠️ Warnung mit ADR-Prozess-Hinweis
Falls NEIN → ✅ Commit erlaubt
```

**Ergebnis:** Entwickler wird an ADR erinnert, aber nicht blockiert.

#### Stufe 2: Pull Request Template (Pflicht-Checklist)
```markdown
# .github/pull_request_template.md

ADR-Checklist muss ausgefüllt werden:
- [ ] Ist dies eine Architektur-Entscheidung?
- [ ] ADR-Dokument erstellt?
- [ ] ADR_INDEX.md aktualisiert?
- [ ] Alternativen dokumentiert?
- [ ] Team-Review abgeschlossen?

Reviewer prüft Checklist vor Approval.
```

**Ergebnis:** Kein Merge ohne ADR-Checklist-Completion.

#### Stufe 3: CI Pipeline (Automatische Prüfung)
```yaml
# .github/workflows/ci.yml

Job: adr-validation
- Prüft ob PR ADR-relevante Änderungen enthält
- Warnt wenn kein ADR im PR
- Blockiert nicht, aber sichtbar für Reviewer
```

**Ergebnis:** CI zeigt deutlich an wenn ADR fehlt.

#### Stufe 4: Code Review Kultur (Team)
```
Reviewer Guidelines:
- Bei Architektur-Änderungen: ADR verlangen
- Bei fehlenden ADRs: "Request Changes"
- Bei unklar ob ADR nötig: Im PR diskutieren
```

**Ergebnis:** Team-Kultur setzt ADR-Standard durch.

---

### 2️⃣ Wie stelle ich sicher, dass Subagenten aufgerufen werden?

**Antwort:** Strukturierte Prompt-Templates + CODEOWNERS

#### Mechanismus A: Feature-basierte Sprint-Entwicklung ✅
```
🎯 NEUE REGEL ab Sprint 2:
Jeder Sprint wird in einzelne Features heruntergebrochen:

Vorteile:
✅ Granulare Git-Commits (1 Commit = 1 Feature)
✅ Bessere Nachvollziehbarkeit und Code-Review
✅ Atomic Rollbacks bei Problemen
✅ Parallele Entwicklung mehrerer Features

Beispiel Sprint 2:
- Feature 2.1: Qdrant Client Foundation
- Feature 2.2: Document Ingestion Pipeline
- Feature 2.3: Embedding Service
- Feature 2.4: Text Chunking Strategy
- Feature 2.5: BM25 Search Engine
- Feature 2.6: Hybrid Search (Vector + BM25)
- Feature 2.7: Retrieval API Endpoints
- Feature 2.8: Security Hardening (P0/P1/P2)

Git Commit Convention:
feat(scope): brief description
Beispiel: feat(qdrant): implement client wrapper with connection pooling
```

#### Mechanismus B: Prompt-Templates (PROMPT_TEMPLATES.md)
```
8 vordefinierte Templates für jeden Task-Typ:
1. Sprint Start (mit Feature-Breakdown!)
2. Feature Implementation
3. Bug Fix
4. ADR-pflichtige Änderung
5. Sprint Review
6. Emergency Hotfix
7. Dependency Update
8. Code Review Feedback

Jedes Template enthält:
- Explizite Subagenten-Assignment
- File Ownership per Subagent
- Success Criteria
- Handoff-Protokoll
```

**Nutzung in Claude Code:**
```
Hey Claude!

Task: Implementiere Hybrid Search

Bitte nutze "Template 2: Feature Implementation" aus PROMPT_TEMPLATES.md.
Delegiere an:
- Backend Agent (Core Logic)
- API Agent (Endpoint)
- Testing Agent (Tests >80%)
- Documentation Agent (API Docs)
```

**Ergebnis:** Systematische Delegation, kein Subagent vergessen.

#### Mechanismus B: CODEOWNERS File
```
# .github/CODEOWNERS

src/agents/**           @backend-team
src/components/**       @backend-team
src/api/**              @api-team
tests/**                @testing-team
docs/**                 @documentation-team
docker/**               @infrastructure-team

docs/ADR/**             @tech-lead @backend-team
```

**Ergebnis:** Automatische Reviewer-Zuweisung = richtige Expertise.

#### Mechanismus C: Task Checkliste (Täglich)
```
JEDEN TAG vor Claude Code Session:
[ ] Welches Template passt?
[ ] Welche Subagenten benötigt?
[ ] Delegation-Reihenfolge klar?
[ ] Handoff-Punkte definiert?

JEDEN TAG nach Session:
[ ] Alle Subagenten eingesetzt?
[ ] File Ownership respektiert?
[ ] Handoffs dokumentiert?
```

**Ergebnis:** Gewohnheit etabliert, Subagenten werden Routine.

---

### 3️⃣ Wie stelle ich sicher, dass Design-Vorgaben eingehalten werden?

**Antwort:** 3-schichtige Automatisierung

#### Schicht 1: Pre-commit Hooks (Lokal, vor Commit)
```yaml
# .pre-commit-config.yaml

14 Hooks laufen automatisch:
1. Ruff Linter (Auto-Fix)
2. Ruff Formatter
3. Black Formatter
4. MyPy Type Checker (Strict)
5. Bandit Security Scanner
6. Safety Dependency Scanner
7. Detect Secrets
8. YAML/JSON/TOML Validation
9. Custom Naming Checker (scripts/check_naming.py)
10. ADR Detection (scripts/check_adr.py)
11. isort Import Sorting
12. Pydocstyle Docstring Checker
13. Conventional Commit Message
14. Markdown/Dockerfile Linting

Installation:
pip install pre-commit
pre-commit install

Danach: JEDER Commit wird automatisch geprüft!
```

**Ergebnis:** 99% der Violations bereits lokal gefangen.

#### Schicht 2: CI Pipeline (Remote, bei Push/PR)
```yaml
# .github/workflows/ci.yml

10 Jobs parallel:
1. Code Quality (Ruff, Black, MyPy, Bandit)
2. Naming Conventions (Custom Script)
3. ADR Validation (Warnung falls fehlt)
4. Unit Tests (Coverage >80% required)
5. Integration Tests (mit Docker Services)
6. Security Scan (Safety, Trivy)
7. Docker Build (Image muss builden)
8. Documentation (Links, Docstrings)
9. Quality Gate (Aggregiert alle Jobs)
10. Performance Benchmarks (nur main branch)

Merge nur möglich wenn alle Jobs ✅
```

**Ergebnis:** Absolute Qualitäts-Garantie vor Merge.

#### Schicht 3: Pull Request Template (Review Checklist)
```markdown
# .github/pull_request_template.md

Autor muss checken:
- [ ] Tests >80% Coverage
- [ ] Black Formatting
- [ ] Ruff Linting
- [ ] MyPy Type Checking
- [ ] Naming Conventions
- [ ] Docstrings vollständig
- [ ] Keine Secrets committed

Reviewer muss checken:
- [ ] Code Quality Gates alle grün
- [ ] Naming Conventions eingehalten
- [ ] Documentation vollständig
- [ ] Performance Targets erfüllt
```

**Ergebnis:** Doppelte Prüfung (Automatisch + Manuell).

---

## 📊 Gesamtübersicht: Enforcement-Matrix

| Was wird geprüft? | Pre-commit | CI Pipeline | PR Template | Code Review |
|-------------------|------------|-------------|-------------|-------------|
| **Code Formatting** | ✅ Auto-Fix | ✅ Blockiert | ✅ Checklist | ✅ Sichtbar |
| **Type Checking** | ✅ Warnung | ✅ Blockiert | ✅ Checklist | ✅ Sichtbar |
| **Naming Conventions** | ✅ Blockiert | ✅ Blockiert | ✅ Checklist | ✅ Review |
| **Test Coverage** | ❌ | ✅ Blockiert | ✅ Checklist | ✅ Review |
| **Security** | ✅ Warnung | ✅ Warnung | ✅ Checklist | ✅ Review |
| **ADR Required** | ⚠️ Warnung | ⚠️ Warnung | ✅ Pflicht | ✅ Review |
| **Subagent Usage** | ❌ | ❌ | ✅ Checklist | ✅ Review |
| **Documentation** | ✅ Check | ✅ Check | ✅ Checklist | ✅ Review |
| **Secrets** | ✅ Blockiert | ✅ Blockiert | ✅ Checklist | ✅ Review |
| **Performance** | ❌ | ⚠️ Bench | ✅ Check | ✅ Review |

**Legende:**
- ✅ Automatisch geprüft & durchgesetzt
- ⚠️ Automatisch geprüft, aber nur Warnung
- ❌ Nicht automatisch prüfbar

---

## 🚀 Setup: Alle Enforcement-Mechanismen aktivieren

### Schritt 1: Pre-commit Hooks
```bash
cd aegis-rag/

# Copy files
cp /home/claude/.pre-commit-config.yaml .
cp /home/claude/scripts/check_adr.py scripts/
cp /home/claude/scripts/check_naming.py scripts/

# Install
pip install pre-commit
pre-commit install
pre-commit install --hook-type commit-msg

# Test
pre-commit run --all-files
```

### Schritt 2: CI Pipeline
```bash
# Copy workflow
mkdir -p .github/workflows
cp /home/claude/.github/workflows/ci.yml .github/workflows/

# Copy PR template
cp /home/claude/.github/pull_request_template.md .github/

# Commit and push
git add .github/
git commit -m "ci: add quality gates pipeline"
git push
```

### Schritt 3: CODEOWNERS (Optional)
```bash
# Copy CODEOWNERS
cp /home/claude/.github/CODEOWNERS .github/

# Edit with your team handles
nano .github/CODEOWNERS

git add .github/CODEOWNERS
git commit -m "docs: add CODEOWNERS for automatic review assignment"
git push
```

### Schritt 4: Prompt Templates in Projekt
```bash
# Copy templates
cp /home/claude/PROMPT_TEMPLATES.md docs/

# Nutze ab jetzt für JEDE Claude Code Session
```

---

## 🎓 Best Practices

### Für Entwickler

**Vor jedem Commit:**
```bash
# Pre-commit hooks laufen automatisch
# Falls Fehler:
pre-commit run --all-files

# Falls du einen Hook skippen MUSST (Notfall):
SKIP=mypy git commit -m "message"

# Aber: Erkläre WARUM im Commit Message!
```

**Vor jedem PR:**
```
1. Checke PR Template vollständig aus
2. Alle CI Jobs müssen grün sein
3. Falls ADR nötig: ERST ADR, DANN Implementation
4. Selbst-Review: Naming Conventions OK?
```

**In Claude Code:**
```
JEDE Session:
1. Wähle passendes Template (PROMPT_TEMPLATES.md)
2. Delegiere explizit an Subagenten
3. Checke ob ADR erforderlich
4. Verifiziere Success Criteria
```

### Für Code Reviewer

**Review Checklist:**
```
[ ] CI Pipeline alle Jobs grün?
[ ] ADR-Checklist korrekt ausgefüllt?
[ ] Falls ADR erforderlich: ADR im PR?
[ ] Subagenten korrekt eingesetzt?
[ ] Tests >80% Coverage?
[ ] Naming Conventions gefolgt?
[ ] Documentation vollständig?
[ ] Performance Targets erfüllt?
[ ] Keine Secrets committed?
```

**Feedback-Kategorien:**
```
"Request Changes" für:
- Fehlende ADRs bei Architektur-Änderungen
- Tests <80% Coverage
- Naming Convention Violations
- Secrets im Code

"Comment" für:
- Verbesserungsvorschläge
- Optionale Optimierungen
- Diskussionspunkte

"Approve" nur wenn:
- Alle CI Jobs grün
- Alle Review-Kriterien erfüllt
```

### Für Tech Lead

**Weekly:**
```
[ ] Sprint Progress vs. SPRINT_PLAN.md
[ ] ADR_INDEX.md auf Aktualität prüfen
[ ] CI Pipeline Performance checken
[ ] Team Feedback zu Enforcement sammeln
```

**Monthly:**
```
[ ] Pre-commit Hooks aktualisieren
[ ] CI Pipeline optimieren
[ ] Enforcement-Metrics reviewen:
  - ADR Coverage: Wie viele Architektur-Entscheidungen haben ADR?
  - Naming Violations: Trend besser/schlechter?
  - Test Coverage: Durchschnitt steigend?
```

---

## 📈 Success Metrics

**Nach 1 Monat solltest du sehen:**
- ADR Coverage: >80% (neue Architektur-Entscheidungen haben ADR)
- Naming Violations: <5 pro Woche
- Test Coverage: >80% durchschnittlich
- Pre-commit Pass Rate: >90%
- CI Pipeline Pass Rate: >85%

**Nach 3 Monaten:**
- ADR Coverage: >95%
- Naming Violations: <2 pro Woche
- Test Coverage: >85%
- Pre-commit Pass Rate: >95%
- CI Pipeline Pass Rate: >90%
- Team: "Enforcement fühlt sich natürlich an"

---

## 🔄 Continuous Improvement

### Feedback Loop
```
Team findet neues Anti-Pattern
  ↓
Dokumentiere in NAMING_CONVENTIONS.md
  ↓
Erweitere check_naming.py Script
  ↓
Update Pre-commit Hooks
  ↓
Team nutzt neue Regel
  ↓
Repeat
```

### Evolution der Enforcement
```
Sprint 1-2: Lerne Enforcement-Tools kennen
Sprint 3-4: Gewöhne dich an Pre-commit Hooks
Sprint 5-6: Nutze Prompt Templates konsequent
Sprint 7-8: ADR-Kultur etabliert
Sprint 9-10: Enforcement ist Gewohnheit
Post-Sprint 10: Team optimiert Enforcement selbst
```

---

## 🆘 Troubleshooting

### Problem: Pre-commit Hooks zu langsam
```bash
# Nur geänderte Files prüfen (default)
pre-commit run

# Bestimmte Hooks deaktivieren (temporär)
SKIP=mypy,bandit git commit -m "message"

# Hook Update
pre-commit autoupdate
```

### Problem: CI Pipeline zu langsam
```yaml
# Jobs parallelisieren (bereits done)
# Cache Dependencies:
- uses: actions/setup-python@v5
  with:
    cache: 'pip'

# Matrix Strategy für Tests:
strategy:
  matrix:
    python-version: [3.11]  # Nur 1 Version für Speed
```

### Problem: Zu viele False Positives bei ADR Detection
```python
# Anpassen in scripts/check_adr.py:
ARCHITECTURE_KEYWORDS = [
    # Entferne zu generische Keywords
    # Füge projekt-spezifische hinzu
]
```

### Problem: Team findet Enforcement zu strikt
```
Option 1: Diskussion → Anpassung der Rules
Option 2: Temporäre Exemptions (SKIP)
Option 3: Schrittweise Einführung (erst Warnings, dann Errors)

NICHT: Enforcement komplett deaktivieren!
```

---

## ✅ Finale Checklist

**Du hast alles richtig gemacht wenn:**
- [ ] Pre-commit Hooks installiert & funktionieren
- [ ] CI Pipeline läuft bei jedem Push/PR
- [ ] PR Template wird von allen genutzt
- [ ] CODEOWNERS zugewiesen
- [ ] Team kennt PROMPT_TEMPLATES.md
- [ ] ADR-Kultur etabliert (>80% Coverage)
- [ ] Naming Violations selten (<5/Woche)
- [ ] Test Coverage >80%
- [ ] Team findet Enforcement hilfreich (nicht nervig)

---

**Zusammenfassung:**

**3 Fragen → 3 Lösungen:**
1. ADRs: Pre-commit Warnung + PR Template + CI + Team Culture
2. Subagenten: Prompt Templates + CODEOWNERS + Tägliche Checklist
3. Design: Pre-commit Hooks + CI Pipeline + PR Template

**Das Ergebnis:**
- 🎯 Konsistente Qualität
- 📚 Vollständige ADR-Dokumentation
- 🤝 Systematische Subagenten-Nutzung
- 🚀 Produktionsreifer Code
- ✅ Happy Team (weil automatisiert)
