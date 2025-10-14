# Context Refresh nach Session-Kompaktierung
## Wie Claude Code wieder "alles auf dem Schirm" hat

---

## ⚠️ Wann ist ein Context Refresh nötig?

**Trigger-Signale:**
- Claude Code sagt "I don't have access to..." (obwohl Datei im Projekt)
- Subagenten-Delegation wird vergessen
- Naming Conventions werden nicht mehr befolgt
- ADRs werden nicht mehr referenziert
- Projekt-spezifische Patterns werden ignoriert

**Ursache:** Session wurde kompaktiert → wichtiger Context verloren.

---

## 🔄 Drei Context Refresh Strategien

### Strategy 1: Quick Refresh (1 Minute)

**Nutze diesen Prompt:**
```
🔄 CONTEXT REFRESH

Bitte lies folgende Dateien zur Reaktivierung des Projekt-Kontexts:

1. CLAUDE.md (Hauptkontext)
2. SPRINT_PLAN.md (aktueller Sprint: {Sprint-Nummer})
3. SUBAGENTS.md (Delegation Strategy)
4. NAMING_CONVENTIONS.md (Code Standards)

Bestätige mit:
- ✅ Projekt-Name & Architektur verstanden
- ✅ Aktueller Sprint & Ziele klar
- ✅ Subagenten-Responsibilities präsent
- ✅ Naming Conventions aktiviert

Danach: Weiter mit vorheriger Task.
```

**Wann nutzen:** Nach kompakter Kompaktierung, Task-Continuity wichtig.

---

### Strategy 2: Deep Refresh (3 Minuten)

**Nutze diesen Prompt:**
```
🔄 DEEP CONTEXT REFRESH

Session wurde kompaktiert. Bitte vollständigen Projekt-Context reaktivieren:

📖 CORE CONTEXT:
1. CLAUDE.md - Projekt-Übersicht, Architektur, Tech Stack
2. SPRINT_PLAN.md - Sprint {N} Ziele & Deliverables
3. SUBAGENTS.md - 5 Subagenten & File Ownership
4. NAMING_CONVENTIONS.md - Code Standards & Best Practices

📚 DECISIONS:
5. ADR_INDEX.md - 8 Architecture Decision Records
6. TECH_STACK.md - Technology Choices & Versionen

🛠️ WORKFLOW:
7. PROMPT_TEMPLATES.md - Template für aktuellen Task-Typ
8. ENFORCEMENT_GUIDE.md - Quality Gates

🎯 AKTUELLER STAND:
- Sprint: {N}
- Task: {Current Task Description}
- Letzte Completion: {Was zuletzt abgeschlossen}
- Nächster Schritt: {Was als nächstes}

WICHTIG:
- Beachte ALLE ADRs bei Implementierung
- Nutze korrekte Subagenten (siehe SUBAGENTS.md)
- Folge Naming Conventions strikt
- Referenziere TECH_STACK.md für Versionen

Bestätige Verständnis mit 1-2 Sätzen pro Dokument.
```

**Wann nutzen:** Nach größerer Kompaktierung, vor kritischen Tasks.

---

### Strategy 3: Sprint Refresh (5 Minuten)

**Nutze am Sprint-Start oder nach mehreren Kompaktierungen:**
```
🔄 SPRINT CONTEXT REFRESH

Neue Session, vollständiger Sprint-Context benötigt:

📋 PROJEKT FOUNDATION:
Lies in dieser Reihenfolge:
1. PROJECT_SUMMARY.md - Gesamtübersicht
2. CLAUDE.md - Vollständiger Projekt-Context
3. SPRINT_PLAN.md - Sprint {N} Planung
4. ADR_INDEX.md - Alle 8 ADRs

👥 WORKFLOW & STANDARDS:
5. SUBAGENTS.md - Delegation Strategy
6. PROMPT_TEMPLATES.md - Templates für alle Task-Typen
7. NAMING_CONVENTIONS.md - Complete Code Standards
8. ENFORCEMENT_GUIDE.md - Quality Gates

🔧 TECHNICAL REFERENCE:
9. TECH_STACK.md - Alle Versionen & Configs
10. QUICK_START.md - Setup & Troubleshooting

📊 SPRINT STATUS:
Checke SPRINT_PLAN.md Sprint {N}:
- [ ] Deliverable 1: {Status}
- [ ] Deliverable 2: {Status}
- [ ] ...

🎯 NÄCHSTE SCHRITTE:
Basierend auf Sprint Status, was ist Priorität?

Gib mir einen Executive Summary (5 Bulletpoints):
- Projekt-Ziel
- Aktuelle Sprint-Phase
- Kritische ADRs für nächste Tasks
- Subagenten-Plan für diese Woche
- Top 3 Priorities
```

**Wann nutzen:** Montag-Morgen, nach langer Pause, Major Context Loss.

---

## 📝 Quick Copy-Paste Prompts

### Minimal Refresh
```
Context Refresh: Lies CLAUDE.md, SPRINT_PLAN.md Sprint {N}, SUBAGENTS.md, NAMING_CONVENTIONS.md. Bestätige kurz.
```

### Standard Refresh
```
Context Refresh: Reaktiviere Projekt-Context aus CLAUDE.md, SPRINT_PLAN.md, SUBAGENTS.md, NAMING_CONVENTIONS.md, ADR_INDEX.md. Bestätige mit Zusammenfassung (3-5 Sätze).
```

### Full Refresh
```
Full Context Refresh: Lies alle Core Docs (CLAUDE.md, SPRINT_PLAN.md, SUBAGENTS.md, NAMING_CONVENTIONS.md, ADR_INDEX.md, TECH_STACK.md, PROMPT_TEMPLATES.md). Gib Executive Summary: Projekt-Ziel, Sprint-Status, nächste Prioritäten.
```

---

## 🎯 Context Refresh Checklist

**Nach jedem Refresh, Claude Code sollte bestätigen:**

```
✅ PROJECT CONTEXT:
- [ ] Projekt-Name: AegisRAG
- [ ] 4 Core-Komponenten verstanden (Vector, Graph, Memory, MCP)
- [ ] Aktueller Sprint: {N}
- [ ] Sprint-Ziel verstanden

✅ ARCHITECTURE:
- [ ] Hybrid Vector-Graph Retrieval
- [ ] 3-Layer Memory (Redis, Qdrant, Graphiti)
- [ ] LangGraph Orchestration
- [ ] Alle ADRs präsent

✅ WORKFLOW:
- [ ] 5 Subagenten & Responsibilities klar
- [ ] Naming Conventions aktiviert
- [ ] Quality Gates verstanden
- [ ] Prompt Template für Task-Typ gewählt

✅ TECHNICAL:
- [ ] Tech Stack & Versionen (Python 3.11+, etc.)
- [ ] Docker Services (Qdrant, Neo4j, Redis)
- [ ] Performance Targets (<200ms Vector, <500ms Graph)
```

---

## 🔔 Auto-Reminder Setup

### In CLAUDE.md einfügen (am Anfang):

```markdown
## 🔄 Session Continuity Check

**Falls diese Session kompaktiert wurde:**
1. Lies dieses gesamte CLAUDE.md Dokument
2. Checke SPRINT_PLAN.md für aktuellen Sprint-Status
3. Reaktiviere Subagenten-Context aus SUBAGENTS.md
4. Verifiziere ADR-Awareness aus ADR_INDEX.md
5. Bestätige Naming Conventions aus NAMING_CONVENTIONS.md

**Zeichen für Context Loss:**
- Du kennst Projekt-Struktur nicht mehr
- Du fragst nach bereits beantworteten Architektur-Fragen
- Du nutzt Subagenten nicht mehr systematisch
- Du hältst dich nicht an Naming Conventions

→ Dann: Context Refresh durchführen!
```

---

## 📊 Erkennung von Context Loss

### Symptome & Solutions

| Symptom | Bedeutet | Solution |
|---------|----------|----------|
| "I don't see any files" | File Context verloren | Quick Refresh |
| Keine Subagenten-Delegation | Workflow Context verloren | Strategy 1 |
| PascalCase statt snake_case | Standards verloren | Strategy 1 |
| Fragen nach Tech Stack | Technical Context verloren | Strategy 2 |
| Keine ADR-Referenzen | Architecture Context verloren | Strategy 2 |
| Sprint-Ziel unklar | Planning Context verloren | Strategy 3 |

---

## 🎓 Best Practices

### Für lange Sessions

**Alle 20-30 Nachrichten:**
```
Quick Check: Sprint {N} noch klar? Subagenten-Delegation OK? 
Falls unsicher → Quick Refresh.
```

**Vor kritischen Tasks:**
```
Context Check: Lies nochmal CLAUDE.md Section "{relevante Section}"
und ADR-{XXX} für diese Task.
```

**Nach jeder Kompaktierung:**
```
Minimum: Quick Refresh (Strategy 1)
```

### Für Team-Übergaben

**Developer A → Developer B:**
```
Context Handoff:
1. Developer B startet neue Claude Code Session
2. Nutzt Strategy 3 (Sprint Refresh)
3. Liest zusätzlich: Letzter PR, aktuelle Branch
4. Developer A gibt kurzes Verbal Briefing
```

---

## 🛠️ Automation Möglichkeiten

### GitHub Issue Template für Context Refresh

```markdown
## Context Refresh Needed

**Symptom:** {Was deutet auf Context Loss hin}
**Last Working State:** {Link zu letztem erfolgreichen Commit/PR}
**Current Sprint:** {Sprint Number}

**Refresh Checklist:**
- [ ] CLAUDE.md gelesen
- [ ] SPRINT_PLAN.md Sprint {N} gecheckt
- [ ] SUBAGENTS.md reaktiviert
- [ ] ADRs reviewt
- [ ] Naming Conventions präsent
- [ ] Tech Stack Versionen klar
```

### Pre-Task Context Check Script

```python
# scripts/context_check.py
"""
Checkt ob wichtige Context-Files seit letzter Session geändert wurden.
Falls ja → empfiehlt Context Refresh.
"""

import os
from pathlib import Path
from datetime import datetime, timedelta

CRITICAL_CONTEXT_FILES = [
    'CLAUDE.md',
    'SPRINT_PLAN.md',
    'SUBAGENTS.md',
    'ADR_INDEX.md',
    'NAMING_CONVENTIONS.md',
]

def check_context_freshness():
    """Check if context files changed recently."""
    last_session = Path('.claude/last_session').read_text()
    last_session_time = datetime.fromisoformat(last_session)
    
    changed_files = []
    for file in CRITICAL_CONTEXT_FILES:
        mtime = datetime.fromtimestamp(Path(file).stat().st_mtime)
        if mtime > last_session_time:
            changed_files.append(file)
    
    if changed_files:
        print("⚠️ Context Refresh recommended!")
        print("Changed files since last session:")
        for file in changed_files:
            print(f"  - {file}")
        print("\nRun Context Refresh Strategy 2")
        return False
    else:
        print("✅ Context up-to-date")
        return True

if __name__ == '__main__':
    check_context_freshness()
```

**Usage:**
```bash
# Am Start jeder Claude Code Session
python scripts/context_check.py

# Falls Warnung → Context Refresh durchführen
```

---

## 📈 Tracking Context Quality

### Metrics to Track

```yaml
Session Metrics:
  - context_refreshes_per_session: <count>
  - naming_violations_after_refresh: <count>
  - subagent_delegation_accuracy: <percentage>
  - time_to_first_context_loss: <minutes>

Quality Indicators:
  - Low violations → Good context retention
  - Frequent refreshes → Consider shorter sessions
  - Fast context loss → Improve context docs
```

---

## 🔄 Kontinuierliche Verbesserung

### Feedback Loop

```
Context Loss Event
  ↓
Dokumentiere: Was wurde vergessen?
  ↓
Update CLAUDE.md: Kritische Info prominenter
  ↓
Update Refresh Prompts: Mehr Fokus auf kritisches
  ↓
Test: Tritt Problem noch auf?
  ↓
Repeat
```

### Quarterly Review

```
Review Questions:
- Wie oft Context Refresh nötig? (Ziel: <3x pro Sprint)
- Welche Docs werden am häufigsten vergessen?
- Welche Refresh Strategy wird am meisten genutzt?
- Gibt es Patterns für Context Loss?

Actions:
- Verbessere häufig vergessene Docs
- Streamline am meisten genutzte Refresh Strategy
- Update Context Check Script
```

---

## ✅ Quick Decision Tree

```
Context Loss?
  ├─ Ja
  │   ├─ Leicht (Naming, Subagenten) → Strategy 1 (Quick Refresh)
  │   ├─ Mittel (ADRs, Tech Stack) → Strategy 2 (Deep Refresh)
  │   └─ Schwer (Sprint-Ziel unklar) → Strategy 3 (Sprint Refresh)
  └─ Nein
      └─ Weiter arbeiten
          └─ Alle 20-30 Messages: Quick Check
```

---

## 🎯 Final Recommendations

### DO:
✅ Context Refresh bei JEDEM Zeichen von Context Loss
✅ Quick Check alle 20-30 Nachrichten in langen Sessions
✅ Full Refresh am Montag / Sprint-Start
✅ Dokumentiere was vergessen wurde → Improve Docs

### DON'T:
❌ Weitermachen wenn Naming Conventions ignoriert werden
❌ Hoffen dass Context "von selbst zurückkommt"
❌ Zu viele Details in Refresh (ineffizient)
❌ Vergessen CLAUDE.md zu updaten wenn Context-Probleme häufig

---

**Merke:** Context Refresh ist kein Bug, sondern Feature! 
Lieber 2 Minuten investieren als 30 Minuten mit suboptimalem Context arbeiten. 🚀
