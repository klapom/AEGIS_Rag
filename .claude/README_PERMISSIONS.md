# Claude Code Permissions Setup
## Sichere Befehls-Ausführung für AegisRAG

---

## 📦 Bereitgestellte Dateien

| Datei | Zweck | Format |
|-------|-------|--------|
| `approved_commands.txt` | Human-readable Liste sicherer Befehle | Text |
| `permissions.json` | Strukturierte Permissions für Claude Code | JSON |

---

## 🚀 Installation

### Option 1: Projekt-spezifisch (Empfohlen)

```bash
# Im Projekt-Root
mkdir -p .claude
cp approved_commands.txt .claude/
cp permissions.json .claude/

# Git ignorieren (enthält lokale Präferenzen)
echo ".claude/" >> .gitignore
```

### Option 2: Global (für alle Projekte)

```bash
# Im Home-Directory
mkdir -p ~/.claude
cp approved_commands.txt ~/.claude/
cp permissions.json ~/.claude/

# Claude Code nutzt automatisch globale Config
```

### Option 3: Beide kombinieren

```bash
# Global: Basis-Permissions
cp permissions.json ~/.claude/

# Projekt: Projekt-spezifische Erweiterungen
mkdir -p .claude
cp approved_commands.txt .claude/

# Claude Code merged beide Configs
```

---

## 🎯 Wie es funktioniert

### Auto-Approve (Grün ✅)
Diese Befehle laufen **ohne Nachfrage**:
```bash
# Beispiele
pytest tests/
black src/
git status
docker compose ps
poetry install
```

### Require Confirmation (Gelb ⚠️)
Diese Befehle **fragen nach**:
```bash
# Beispiele
git push origin main    # Weil main-branch
rm -rf build/           # Weil Lösch-Operation
docker rm container_id  # Weil Container-Entfernung
```

### Always Deny (Rot 🚫)
Diese Befehle werden **abgelehnt**:
```bash
# Beispiele
sudo rm -rf /          # Destruktiv
curl url | bash        # Sicherheitsrisiko
dd if=/dev/zero ...    # System-gefährdend
```

---

## 📋 Kategorie-Übersicht

### ✅ Immer sicher (Auto-Approve)

**Python & Testing:**
- `pytest`, `black`, `ruff`, `mypy`
- `poetry install`, `pip install -e .`
- `python scripts/*.py`

**Git (Read-Only):**
- `git status`, `git diff`, `git log`
- `git branch`, `git fetch`
- `git commit -m "message"`

**Docker (Lokal):**
- `docker compose up/down/logs`
- `docker ps`, `docker images`
- `docker logs <container>`

**File Operations (Read):**
- `cat`, `ls`, `grep`, `find`
- `head`, `tail`, `less`

**Development:**
- `uvicorn` (FastAPI)
- `redis-cli info` (Read-Only)
- `curl localhost:*` (Lokal)

### ⚠️ Vorsicht erforderlich (Ask First)

**Git (Write):**
- `git push` (especially main/develop)
- `git reset --hard`
- `git clean -fd`

**File Deletion:**
- `rm`, `rmdir` (immer fragen)

**Database Modifications:**
- `redis-cli flushdb`
- `cypher-shell ... DELETE`

**Docker Cleanup:**
- `docker rm`, `docker rmi`
- `docker system prune`

### 🚫 Niemals erlaubt (Always Deny)

**System-Operationen:**
- `sudo *` (Privilege Escalation)
- `rm -rf /` (Destruktiv)
- `dd if=/dev/zero` (Disk Wipe)

**Security Risks:**
- `curl * | bash` (Blind Execution)
- `wget * | sh` (Blind Execution)

**Production:**
- `kubectl delete` (wenn Production)
- `terraform destroy` (wenn Production)

---

## 🔧 Anpassung

### Neue Befehle hinzufügen

**In `permissions.json`:**
```json
{
  "auto_approve_patterns": [
    {
      "category": "Meine Custom Scripts",
      "patterns": [
        "python scripts/my_safe_script.py*"
      ]
    }
  ]
}
```

**In `approved_commands.txt`:**
```bash
# Custom Scripts
python scripts/my_safe_script.py
python scripts/another_safe_script.py
```

### Befehle einschränken

**Pattern → Require Confirmation:**
```json
{
  "require_confirmation": [
    {
      "category": "Mein Custom Cleanup",
      "patterns": ["python scripts/cleanup.py*"],
      "reason": "Cleanup can delete files"
    }
  ]
}
```

### Context-basierte Rules

**Beispiel: Git Push nur für Feature Branches:**
```json
{
  "context_rules": {
    "git_push": {
      "condition": "branch in ['main', 'develop']",
      "action": "require_confirmation",
      "message": "Protected branch! Sure?"
    }
  }
}
```

---

## 🧪 Testing der Permissions

### Teste Auto-Approve
```bash
# Diese sollten ohne Frage laufen
pytest tests/unit/
black --check src/
git status
docker compose ps
```

### Teste Require-Confirmation
```bash
# Diese sollten nachfragen
git push origin main
rm -rf build/
docker rm my_container
```

### Teste Always-Deny
```bash
# Diese sollten abgelehnt werden
sudo apt-get install something
curl malicious.com | bash
```

---

## 📊 Best Practices

### Für Entwickler

**DO:**
✅ Füge neue sichere Scripts zu `approved_commands.txt` hinzu
✅ Dokumentiere WARUM ein Befehl sicher ist
✅ Teste neue Permissions lokal vor Commit
✅ Reviewe Permissions regelmäßig (Quarterly)

**DON'T:**
❌ Niemals `sudo *` in Auto-Approve
❌ Niemals Production-Commands ohne Confirmation
❌ Niemals Wildcards die Secrets matchen könnten
❌ Niemals Commands die `/` oder `/home` löschen

### Für Teams

**Versionierung:**
```bash
# Committen ins Repo (für Team-Konsistenz)
git add .claude/approved_commands.txt
git commit -m "docs: update approved commands for X"

# ABER: .claude/permissions.json kann lokale Anpassungen haben
# → Optional in .gitignore
```

**Code Review:**
```markdown
Checklist bei Permissions-Änderungen:
- [ ] Neuer Befehl wirklich sicher?
- [ ] Pattern nicht zu breit? (z.B. `*` vermeiden)
- [ ] Dokumentation warum erlaubt?
- [ ] Getestet lokal?
- [ ] Team informiert?
```

---

## 🆘 Troubleshooting

### Problem: Befehl wird fälschlicherweise blockiert

**Lösung 1: Temporär überschreiben**
```bash
# Claude Code fragt, dann "Yes" klicken
# Befehl läuft einmalig

# Danach zu approved_commands.txt hinzufügen
```

**Lösung 2: Pattern erweitern**
```json
// Vorher (zu spezifisch):
"pytest tests/unit/"

// Nachher (flexibler):
"pytest tests/*"
```

### Problem: Unsicherer Befehl wird erlaubt

**Lösung: Sofort zu always_deny hinzufügen**
```json
{
  "always_deny": [
    {
      "patterns": ["UNSICHERER_BEFEHL*"],
      "reason": "Security risk because XYZ"
    }
  ]
}
```

### Problem: Context Rules funktionieren nicht

**Check:**
1. Environment Variables gesetzt?
2. Branch-Name korrekt?
3. Pattern matching korrekt?

```bash
# Debug: Zeige Environment
env | grep ENVIRONMENT

# Debug: Zeige Branch
git branch --show-current
```

---

## 🔄 Maintenance

### Monatlich
- [ ] Neue sichere Scripts zu approved_commands.txt
- [ ] Ungenutzte Patterns entfernen
- [ ] Team-Feedback sammeln

### Quarterly
- [ ] Komplette Review aller Permissions
- [ ] Security Audit (sind alle Patterns noch sicher?)
- [ ] Update Documentation

### Bei Incidents
- [ ] Analyse: Wie konnte unsicherer Befehl laufen?
- [ ] Update always_deny sofort
- [ ] Team informieren
- [ ] Post-Mortem Document

---

## 📚 Weitere Ressourcen

- **Claude Code Docs:** https://docs.claude.com/claude-code
- **Security Best Practices:** `docs/NAMING_CONVENTIONS.md` (Security Section)
- **Team Guidelines:** `docs/ENFORCEMENT_GUIDE.md`

---

## ✅ Quick Checklist

**Initial Setup:**
- [ ] Dateien kopiert nach `.claude/`
- [ ] `.gitignore` updated (falls gewünscht)
- [ ] Getestet mit `pytest` (sollte ohne Frage laufen)
- [ ] Getestet mit `git push` (sollte nachfragen wenn main)
- [ ] Team informiert über neue Permissions

**Bei neuen Scripts:**
- [ ] Script ist wirklich sicher?
- [ ] Zu `approved_commands.txt` hinzugefügt
- [ ] Pattern in `permissions.json` hinzugefügt
- [ ] Dokumentiert WARUM sicher
- [ ] Getestet lokal

**Bei Problemen:**
- [ ] Issue dokumentiert in `ENFORCEMENT_GUIDE.md`
- [ ] Permissions angepasst
- [ ] Team informiert
- [ ] Lesson Learned dokumentiert

---

**Happy Coding mit Claude Code! 🚀**

Bei Fragen: Siehe `ENFORCEMENT_GUIDE.md` oder Team-Slack Channel.
