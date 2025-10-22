# AEGIS RAG - Dokumentation

Willkommen zur AEGIS RAG Dokumentation! Diese Übersicht hilft dir, dich in der Dokumentationsstruktur zurechtzufinden.

## 📖 Dokumentationsstruktur

### Core Dokumentation (`/docs/core/`)

Die Kern-Dokumentation enthält alle wichtigen Informationen zum Projekt:

#### Einstieg & Übersicht
1. **[PROJECT_SUMMARY.md](core/PROJECT_SUMMARY.md)** ⭐ **START HIER!**
   - Gesamtübersicht des AEGIS RAG Systems
   - Vision, Ziele, Architektur
   - Schneller Einstieg ins Projekt

2. **[QUICK_START.md](core/QUICK_START.md)**
   - Tag-1-Setup für Entwickler
   - Schritt-für-Schritt Installation
   - Erste Schritte mit dem Code

#### Entwicklungs-Guidelines
3. **[NAMING_CONVENTIONS.md](core/NAMING_CONVENTIONS.md)**
   - Code-Namenskonventionen
   - File-Struktur Standards
   - Best Practices für Python, TypeScript, etc.

4. **[TECH_STACK.md](core/TECH_STACK.md)**
   - Vollständiger Technology Stack
   - Backend, Frontend, Infrastructure
   - Tool-Versionen und Dependencies

#### Projektplanung
5. **[SPRINT_PLAN.md](core/SPRINT_PLAN.md)**
   - 10-Sprint Roadmap (20 Wochen)
   - Detaillierte Sprint-Ziele
   - Milestones und Deliverables

#### Claude Code Integration
6. **[CLAUDE.md](core/CLAUDE.md)**
   - Hauptkontext für Claude Code
   - Projekt-Richtlinien für KI-Assistenz
   - Best Practices für AI-gestützte Entwicklung

7. **[SUBAGENTS.md](core/SUBAGENTS.md)**
   - 5 spezialisierte Subagenten-Definitionen
   - Use Cases und Workflows
   - Prompt Engineering Guidelines

8. **[PROMPT_TEMPLATES.md](core/PROMPT_TEMPLATES.md)**
   - 8 vordefinierte Claude Code Templates
   - Sofort einsetzbare Prompts
   - Anwendungsbeispiele

#### Quality & Enforcement
9. **[ENFORCEMENT_GUIDE.md](core/ENFORCEMENT_GUIDE.md)**
   - Quality Gates Übersicht
   - Enforcement-Strategien
   - Tooling-Integration

### Architecture Decision Records (`/docs/adr/`)

Dokumentation aller wichtigen Architekturentscheidungen:

10. **[ADR_INDEX.md](adr/ADR_INDEX.md)**
    - Index aller 8 ADRs
    - Architekturentscheidungen und deren Begründungen
    - Technology Choices
    - Security Patterns

## 🎯 Schnelleinstieg nach Rolle

### Für neue Entwickler
1. Lies [PROJECT_SUMMARY.md](core/PROJECT_SUMMARY.md) für Kontext
2. Folge [QUICK_START.md](core/QUICK_START.md) für Setup
3. Studiere [NAMING_CONVENTIONS.md](core/NAMING_CONVENTIONS.md) vor dem ersten Code

### Für Architekten
1. Beginne mit [PROJECT_SUMMARY.md](core/PROJECT_SUMMARY.md)
2. Prüfe [ADR_INDEX.md](adr/ADR_INDEX.md) für Architekturentscheidungen
3. Siehe [TECH_STACK.md](core/TECH_STACK.md) für technische Details

### Für Product Owner / PM
1. [PROJECT_SUMMARY.md](core/PROJECT_SUMMARY.md) - Vision & Ziele
2. [SPRINT_PLAN.md](core/SPRINT_PLAN.md) - Zeitplan & Milestones
3. [ENFORCEMENT_GUIDE.md](core/ENFORCEMENT_GUIDE.md) - Quality Assurance

### Für DevOps Engineers
1. [QUICK_START.md](core/QUICK_START.md) - Setup & Installation
2. [TECH_STACK.md](core/TECH_STACK.md) - Infrastructure Details
3. Siehe `/.github/workflows/ci.yml` für CI/CD Pipeline

### Für Claude Code Nutzer
1. [CLAUDE.md](core/CLAUDE.md) - Hauptkontext laden
2. [SUBAGENTS.md](core/SUBAGENTS.md) - Spezialisierte Agenten nutzen
3. [PROMPT_TEMPLATES.md](core/PROMPT_TEMPLATES.md) - Templates verwenden

## 📋 Dokument-Typen

| Typ | Beschreibung | Beispiele |
|-----|--------------|-----------|
| **Overview** | Gesamtüberblick | PROJECT_SUMMARY |
| **Guide** | Step-by-Step Anleitungen | QUICK_START, ENFORCEMENT_GUIDE |
| **Reference** | Nachschlagewerke | NAMING_CONVENTIONS, TECH_STACK |
| **Plan** | Roadmaps & Zeitpläne | SPRINT_PLAN |
| **ADR** | Architekturentscheidungen | ADR_INDEX |
| **Templates** | Wiederverwendbare Vorlagen | PROMPT_TEMPLATES |

## 🔄 Dokumentation aktualisieren

### Wann aktualisieren?
- **Architekturänderungen** → ADR erstellen in `/docs/adr/`
- **Neue Features** → PROJECT_SUMMARY & SPRINT_PLAN updaten
- **Tech Stack Änderungen** → TECH_STACK.md aktualisieren
- **Neue Conventions** → NAMING_CONVENTIONS.md erweitern
- **Claude Code Updates** → CLAUDE.md, SUBAGENTS.md oder PROMPT_TEMPLATES.md anpassen

### Dokumentations-Workflow
1. Änderungen in entsprechender Datei vornehmen
2. Konsistenz mit anderen Dokumenten prüfen
3. ADR erstellen bei signifikanten Änderungen
4. PR mit Dokumentation-Label erstellen

## 🔍 Suche & Navigation

### Empfohlene Lesereihenfolge für Neueinsteiger
```
1. PROJECT_SUMMARY.md    (15 min) - Gesamtkontext
2. QUICK_START.md        (30 min) - Setup durchführen
3. NAMING_CONVENTIONS.md (20 min) - Standards lernen
4. CLAUDE.md             (10 min) - Claude Code konfigurieren
5. SPRINT_PLAN.md        (15 min) - Roadmap verstehen
```

### Häufige Fragen → Dokumente

| Frage | Dokument |
|-------|----------|
| Was macht AEGIS RAG? | [PROJECT_SUMMARY.md](core/PROJECT_SUMMARY.md) |
| Wie starte ich? | [QUICK_START.md](core/QUICK_START.md) |
| Welche Technologien? | [TECH_STACK.md](core/TECH_STACK.md) |
| Wie benenne ich Code? | [NAMING_CONVENTIONS.md](core/NAMING_CONVENTIONS.md) |
| Was ist der Plan? | [SPRINT_PLAN.md](core/SPRINT_PLAN.md) |
| Warum Technology X? | [ADR_INDEX.md](adr/ADR_INDEX.md) |
| Wie nutze ich Claude Code? | [CLAUDE.md](core/CLAUDE.md), [PROMPT_TEMPLATES.md](core/PROMPT_TEMPLATES.md) |
| Welche Quality Gates? | [ENFORCEMENT_GUIDE.md](core/ENFORCEMENT_GUIDE.md) |

## 📞 Support

Bei Fragen oder Unklarheiten:
1. Durchsuche zuerst diese Dokumentation
2. Prüfe relevante ADRs
3. Kontaktiere das Team

---

**Dokumentations-Version**: 1.0.0
**Letzte Aktualisierung**: Oktober 2024
**Maintainer**: AEGIS RAG Team
