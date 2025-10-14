#!/usr/bin/env python3
"""
Pre-commit hook: Detektiert Commits die ADRs benötigen könnten.

Trigger Keywords in Commit Message:
- architecture, design, decision, choose, select, framework, database, etc.

Falls Trigger gefunden: Warnung mit Hinweis auf ADR-Prozess.
"""
import re
import sys
from pathlib import Path

# Keywords die auf Architektur-Entscheidung hindeuten
ARCHITECTURE_KEYWORDS = [
    r'\b(architecture|architectural)\b',
    r'\b(design decision|design choice)\b',
    r'\b(choose|chose|select|selected)\b.{0,30}\b(framework|library|database|tool)\b',
    r'\b(migrate|migration)\b.{0,30}\b(from|to)\b',
    r'\b(replace|replacing)\b.{0,30}\b(with)\b',
    r'\b(new technology|new framework|new approach)\b',
    r'\b(alternatives considered|alternatives evaluated)\b',
]

# Files die ADR-relevante Änderungen enthalten könnten
ADR_RELEVANT_FILES = [
    'pyproject.toml',
    'requirements.txt',
    'docker-compose.yml',
    'Dockerfile',
    '.github/workflows/',
    'src/core/config.py',
]

def check_commit_message(commit_msg: str) -> bool:
    """Prüft ob Commit Message auf Architektur-Entscheidung hindeutet."""
    for pattern in ARCHITECTURE_KEYWORDS:
        if re.search(pattern, commit_msg, re.IGNORECASE):
            return True
    return False

def check_staged_files(staged_files: list[str]) -> bool:
    """Prüft ob gestaged Files ADR-relevant sind."""
    for file in staged_files:
        for relevant in ADR_RELEVANT_FILES:
            if relevant in file:
                return True
    return False

def get_commit_message() -> str:
    """Liest Commit Message aus .git/COMMIT_EDITMSG."""
    commit_msg_file = Path('.git/COMMIT_EDITMSG')
    if commit_msg_file.exists():
        return commit_msg_file.read_text()
    return ""

def get_staged_files() -> list[str]:
    """Liest gestaged Files aus git."""
    import subprocess
    result = subprocess.run(
        ['git', 'diff', '--cached', '--name-only'],
        capture_output=True,
        text=True
    )
    return result.stdout.strip().split('\n') if result.stdout else []

def check_adr_exists_for_commit() -> bool:
    """Prüft ob neues ADR im Commit enthalten ist."""
    staged_files = get_staged_files()
    return any('docs/ADR/ADR-' in f and f.endswith('.md') for f in staged_files)

def main():
    commit_msg = get_commit_message()
    staged_files = get_staged_files()
    
    # Check ob ADR-relevant
    needs_adr = (
        check_commit_message(commit_msg) or 
        check_staged_files(staged_files)
    )
    
    if needs_adr:
        # Check ob ADR bereits im Commit
        has_adr = check_adr_exists_for_commit()
        
        if not has_adr:
            print("\n⚠️  WARNING: Dieser Commit könnte ein ADR benötigen!")
            print("─" * 60)
            print("Erkannt:")
            if check_commit_message(commit_msg):
                print("  • Commit Message enthält Architektur-Keywords")
            if check_staged_files(staged_files):
                print("  • ADR-relevante Files geändert:")
                for f in staged_files:
                    for rel in ADR_RELEVANT_FILES:
                        if rel in f:
                            print(f"    - {f}")
            print()
            print("Fragen zum ADR-Prozess:")
            print("  1. Ist dies eine neue Architektur-Entscheidung?")
            print("  2. Wurden Alternativen evaluiert?")
            print("  3. Hat die Entscheidung langfristige Auswirkungen?")
            print()
            print("Falls JA → Erstelle ADR:")
            print("  cd docs/ADR/")
            print("  cp ADR_TEMPLATE.md ADR-XXX-title.md")
            print("  # Editiere ADR-XXX-title.md")
            print("  git add docs/ADR/ADR-XXX-title.md")
            print("  # Update ADR_INDEX.md")
            print()
            print("Falls NEIN → Commit mit Flag überspringen:")
            print("  git commit --no-verify -m 'message'")
            print("─" * 60)
            
            # Nicht blocken, nur warnen
            return 0
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
