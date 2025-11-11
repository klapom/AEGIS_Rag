# LM Studio Installation & Setup Guide

**Version:** 1.0
**Date:** 2025-10-30
**Purpose:** Sprint 20 Feature 20.2 (LM Studio Parameter Evaluation)

---

## 📋 Overview

LM Studio ist ein Desktop-Tool für lokale LLM-Inferenz mit fortgeschrittenen Parameter-Tuning-Optionen. Es nutzt dieselbe Backend-Technologie wie Ollama (llama.cpp), bietet aber eine grafische Oberfläche und mehr Konfigurationsmöglichkeiten.

### Warum LM Studio zusätzlich zu Ollama?

| Feature | Ollama | LM Studio |
|---------|--------|-----------|
| Backend | llama.cpp | llama.cpp (identisch) |
| API | REST API | OpenAI-compatible API |
| GUI | ❌ CLI only | ✅ Grafische Oberfläche |
| Parameter Tuning | Basis-Parameter | Erweiterte Parameter |
| Monitoring | Logs only | Live-Monitoring (VRAM, tokens/sec) |
| Model Management | CLI | Drag & Drop |
| Development | ⭐ Optimal | ⭐⭐ Sehr gut (visuelle Analysen) |
| Production | ⭐⭐ Optimal (headless) | ⚠️ Nicht empfohlen (GUI-App) |

**Empfehlung aus LMSTUDIO_VS_OLLAMA_ANALYSIS.md:**
- **Development:** LM Studio für Parameter-Tuning und visuelle Analyse
- **Production:** Ollama für Docker-Deployment und CI/CD

---

## 🚀 Installation (Windows 11)

### Schritt 1: Download

1. Besuche: https://lmstudio.ai/
2. Klicke auf **"Download LM Studio"**
3. Wähle **Windows (x64)** Version
4. Download: `LMStudio-0.2.x-Setup.exe` (~100 MB)

**System Requirements:**
- Windows 10/11 (64-bit)
- 16 GB RAM (32 GB empfohlen)
- NVIDIA GPU mit 8+ GB VRAM (für Gemma 3 4B Q8)
- ~20 GB freier Speicherplatz

### Schritt 2: Installation

1. Führe `LMStudio-0.2.x-Setup.exe` aus
2. Wähle Installationspfad (Standard: `C:\Users\<USER>\AppData\Local\Programs\LM Studio`)
3. Akzeptiere Lizenz (MIT License)
4. Warte auf Installation (~2 Minuten)
5. **Wichtig:** Lasse "Start LM Studio" aktiviert

### Schritt 3: Erster Start

Beim ersten Start:
1. LM Studio öffnet sich mit Welcome Screen
2. Akzeptiere Telemetry-Einstellungen (optional)
3. Du siehst das Hauptfenster mit 4 Tabs:
   - **Chat:** Interaktive Chat-Oberfläche
   - **Models:** Model Management (Download, Löschen)
   - **Local Server:** API-Server (OpenAI-compatible)
   - **Settings:** Konfiguration

---

## 📦 Model Download

### Gemma 3 4B Instruct Q8 herunterladen

Für Sprint 20 Feature 20.2 benötigen wir das gleiche Modell wie in Ollama:

1. **Wechsle zum "Models" Tab**
2. **Suche nach "gemma"** in der Suchleiste
3. **Finde:** `google/gemma-2-2b-it-GGUF` oder ähnliche Varianten
4. **Wichtig:** Wähle **Q8_0 Quantisierung** (höchste Qualität)
   - `gemma-2-2b-it.Q8_0.gguf` (~4 GB)

   **Alternative (falls Gemma 3 4B nicht verfügbar):**
   - Verwende `gemma-2-2b-it` (2B Parameter, kleiner)
   - Oder lade GGUF-File manuell von Hugging Face

5. **Download starten:** Klicke auf Download-Button
6. **Fortschritt:** Wird unten im Fenster angezeigt
7. **Warte:** Download dauert 5-15 Minuten (abhängig von Internet-Geschwindigkeit)

### Manueller GGUF-Download (falls nötig)

Falls Gemma 3 4B nicht in LM Studio verfügbar:

1. Besuche: https://huggingface.co/models
2. Suche nach: `gemma-3-4b-it GGUF`
3. Finde Repository mit `.gguf` Files
4. Download: `gemma-3-4b-it.Q8_0.gguf` (~5 GB)
5. **Verschiebe File nach:**
   ```
   C:\Users\<USER>\.cache\lm-studio\models\
   ```
6. Starte LM Studio neu → Modell erscheint in "Models" Tab

---

## ⚙️ Konfiguration für Sprint 20

### Local Server einrichten

1. **Wechsle zum "Local Server" Tab**
2. **Wähle Modell:** `gemma-3-4b-it-Q8_0` aus Dropdown
3. **Konfiguriere Server-Settings:**

   ```yaml
   Server Configuration:
     Port: 1234 (Standard)
     CORS: Enabled
     API Format: OpenAI Compatible
   ```

4. **GPU Settings:**
   ```yaml
   GPU Offload: 100% (alle Layers auf GPU)
   Context Length: 8192 tokens
   Thread Count: 8 (match WSL2 CPU cores)
   Batch Size: 512
   ```

5. **Starte Server:** Klicke "Start Server"
6. **Verifiziere:** Grüner Status "Server Running" erscheint

### API-Endpoint testen

Öffne PowerShell und teste:

```powershell
# Test health endpoint
Invoke-RestMethod -Uri "http://localhost:1234/v1/models" -Method Get

# Expected output:
# {
#   "data": [
#     {
#       "id": "gemma-3-4b-it-Q8_0",
#       "object": "model",
#       "owned_by": "local"
#     }
#   ]
# }
```

Falls Fehler: Überprüfe, ob Server läuft (grüner Status in LM Studio)

---

## 🔧 Advanced Parameter Configuration

### Parameter-Kategorien in LM Studio

LM Studio bietet Parameter, die in Ollama nicht verfügbar sind:

#### 1. Sampling Parameters (Qualität)

**In LM Studio UI verfügbar:**

```yaml
Temperature: 0.7
  → Kreativität (0.0 = deterministisch, 1.0 = sehr kreativ)

Top P: 0.9
  → Nucleus Sampling (0.9 = nur top 90% Tokens)

Top K: 40
  → Anzahl betrachteter Tokens (40 = top 40 Kandidaten)

Min P: 0.05 ⭐ NEU (nicht in Ollama)
  → Minimum Probability Threshold

Typical P: 1.0 ⭐ NEU (nicht in Ollama)
  → Typical Sampling (Alternative zu Top-P)

Mirostat: Off / 1.0 / 2.0 ⭐ NEU (nicht in Ollama)
  → Adaptive Sampling für konsistente Perplexity
  → Mirostat Tau: 5.0 (Target Entropy)
  → Mirostat Eta: 0.1 (Learning Rate)
```

#### 2. Context Management (Speicher)

```yaml
Context Length: 8192
  → Max. Tokens im Kontext-Fenster

RoPE Frequency Base: 10000 ⭐ NEU
  → Rotary Position Embeddings Basis

RoPE Frequency Scale: 1.0 ⭐ NEU
  → RoPE Skalierung für längere Kontexte

Cache Type: f16 / q8_0 / q4_0
  → KV-Cache Quantisierung für VRAM-Optimierung
```

#### 3. Performance Tuning (Geschwindigkeit)

```yaml
Threads: 8
  → CPU-Threads (match WSL2: 8 cores)

Batch Size: 512
  → Prompt Processing Batch Size

GPU Layers: -1 (all)
  → Anzahl Layers auf GPU (-1 = alle)

Use mlock: false ⭐ NEU
  → Lock model in RAM (verhindert Swapping)

Use mmap: true ⭐ NEU
  → Memory-map model file (schnelleres Laden)
```

### Wo Parameter in LM Studio setzen?

**Option 1: Local Server Tab (für API-Nutzung)**
1. Wechsle zu "Local Server" Tab
2. Klicke "Server Options" (⚙️ Icon)
3. Setze Parameter in GUI
4. Klicke "Apply" → Server neu starten

**Option 2: Chat Tab (für interaktive Tests)**
1. Wechsle zu "Chat" Tab
2. Lade Modell oben
3. Klicke "Model Settings" (⚙️ Icon rechts)
4. Setze Parameter
5. Teste direkt im Chat

**Option 3: API-Request (für Benchmarking)**
```python
import httpx

response = httpx.post(
    "http://localhost:1234/v1/chat/completions",
    json={
        "model": "gemma-3-4b-it-Q8_0",
        "messages": [{"role": "user", "content": "Hello"}],
        # Advanced parameters (NEU in LM Studio)
        "temperature": 0.7,
        "top_p": 0.9,
        "top_k": 40,
        "min_p": 0.05,           # ⭐ NEU
        "typical_p": 0.9,        # ⭐ NEU
        "mirostat_mode": 2,      # ⭐ NEU (0=off, 1=v1, 2=v2)
        "mirostat_tau": 5.0,     # ⭐ NEU
        "mirostat_eta": 0.1,     # ⭐ NEU
    }
)
```

---

## 🧪 Verwendung für Sprint 20 Feature 20.2

### Evaluation Script ausführen

Nach Installation von LM Studio:

1. **Starte LM Studio**
2. **Wechsle zu "Local Server" Tab**
3. **Lade Modell:** `gemma-3-4b-it-Q8_0`
4. **Starte Server:** Port 1234
5. **Lasse LM Studio laufen** (im Hintergrund)

6. **Öffne neues Terminal (WSL2 oder PowerShell)**
7. **Navigiere zu Projekt:**
   ```bash
   cd AEGIS_Rag
   ```

8. **Führe Evaluation Script aus:**
   ```bash
   poetry run python scripts/evaluate_lm_studio_params.py
   ```

Das Script wird:
- 4 verschiedene Sampling-Configs testen
- Tokens/sec, TTFT, Antwort-Qualität messen
- Ergebnisse in `docs/sprints/SPRINT_20_LM_STUDIO_PARAMS.json` speichern

### Monitoring während der Evaluation

**In LM Studio:**
- Wechsle zu "Local Server" Tab
- Beobachte Live-Statistiken:
  - Tokens/sec (Echtzeit)
  - VRAM Usage (MB)
  - Requests Count
  - Active Connections

**Beispiel-Output:**
```
Server Running: gemma-3-4b-it-Q8_0
VRAM: 4821 MB / 8192 MB (58%)
Tokens/sec: 23.4 t/s
Requests: 12 total, 1 active
```

---

## 🔍 Vergleich: LM Studio vs Ollama API

### Ollama (bisherig)

```bash
# Modell laden
ollama pull gemma-3-4b-it-Q8_0

# API Request
curl http://localhost:11434/api/generate \
  -d '{
    "model": "gemma-3-4b-it-Q8_0",
    "prompt": "Hello",
    "options": {
      "temperature": 0.7,
      "top_p": 0.9,
      "top_k": 40
    }
  }'
```

**Verfügbare Parameter:**
- ✅ temperature
- ✅ top_p
- ✅ top_k
- ✅ repeat_penalty
- ❌ min_p (nicht verfügbar)
- ❌ typical_p (nicht verfügbar)
- ❌ mirostat (nicht verfügbar)

### LM Studio (neu)

```python
import httpx

response = httpx.post(
    "http://localhost:1234/v1/chat/completions",
    json={
        "model": "gemma-3-4b-it-Q8_0",
        "messages": [{"role": "user", "content": "Hello"}],
        "temperature": 0.7,
        "top_p": 0.9,
        "top_k": 40,
        "min_p": 0.05,           # ⭐ ZUSÄTZLICH
        "typical_p": 0.9,        # ⭐ ZUSÄTZLICH
        "mirostat_mode": 2,      # ⭐ ZUSÄTZLICH
        "mirostat_tau": 5.0,     # ⭐ ZUSÄTZLICH
        "mirostat_eta": 0.1,     # ⭐ ZUSÄTZLICH
    }
)
```

**Alle Parameter verfügbar:**
- ✅ temperature
- ✅ top_p
- ✅ top_k
- ✅ repeat_penalty
- ✅ min_p ⭐
- ✅ typical_p ⭐
- ✅ mirostat (mode, tau, eta) ⭐

---

## 🐛 Troubleshooting

### Problem: Server startet nicht

**Symptom:** "Failed to start server" Fehler

**Lösungen:**
1. Prüfe, ob Port 1234 bereits belegt:
   ```powershell
   netstat -ano | findstr :1234
   ```
2. Wähle anderen Port in LM Studio Settings
3. Oder stoppe andere Anwendung auf Port 1234

### Problem: Modell lädt nicht auf GPU

**Symptom:** "Using CPU for inference" Warnung

**Lösungen:**
1. Prüfe NVIDIA Treiber:
   ```powershell
   nvidia-smi
   ```
2. In LM Studio: Settings → GPU Offload → 100%
3. Verringere Context Length (8192 → 4096) falls VRAM voll

### Problem: Sehr langsame Inferenz (<5 t/s)

**Symptom:** Tokens/sec unter 5 t/s

**Lösungen:**
1. Erhöhe Thread Count auf 8 (match CPU cores)
2. Verringere Batch Size (512 → 256) falls RAM-Problem
3. Prüfe, ob Antivirus LM Studio blockiert
4. Nutze Q4 statt Q8 Quantisierung (kleiner, schneller)

### Problem: "Model not found" API-Fehler

**Symptom:** 404 Not Found bei API-Request

**Lösungen:**
1. Prüfe, ob Server läuft (grüner Status)
2. Prüfe Modell-Name in API-Request:
   ```python
   # Falsch:
   "model": "gemma-3-4b-it"

   # Richtig:
   "model": "gemma-3-4b-it-Q8_0"
   ```
3. Liste verfügbare Modelle:
   ```bash
   curl http://localhost:1234/v1/models
   ```

---

## 📊 Performance Expectations

### Gemma 3 4B Q8 auf RTX 4070 (12 GB VRAM)

**Erwartete Performance:**
- **VRAM Usage:** ~5 GB (bei 8192 Context)
- **Tokens/sec:** 20-30 t/s (CUDA)
- **Time to First Token:** <500ms (warm start)
- **Cold Start:** ~5-10s (Modell-Loading)

**Vergleich zu Ollama:**
- **Identische Geschwindigkeit** (gleicher Backend)
- **+GUI Overhead:** ~100 MB RAM mehr
- **+Monitoring:** Live-Statistiken
- **+Parameter:** Mehr Tuning-Optionen

---

## 🎯 Nächste Schritte nach Installation

### Sprint 20 Feature 20.2 Workflow

1. ✅ **LM Studio installiert** (diese Anleitung)
2. ✅ **Gemma 3 4B Q8 heruntergeladen**
3. ✅ **Local Server läuft auf Port 1234**

4. **Führe Parameter-Evaluation aus:**
   ```bash
   poetry run python scripts/evaluate_lm_studio_params.py
   ```

5. **Analysiere Ergebnisse:**
   - Öffne `docs/sprints/SPRINT_20_LM_STUDIO_PARAMS.json`
   - Vergleiche Sampling-Configs (mirostat vs typical_p vs baseline)
   - Identifiziere beste Config für Qualität + Geschwindigkeit

6. **Human Evaluation:**
   - Lies Antworten in JSON-File
   - Bewerte mit Rubric aus `test_questions.yaml`
   - Dokumentiere in `SPRINT_20_LM_STUDIO_EVALUATION.md`

7. **A/B Test:**
   - Beste LM Studio Config vs Ollama Baseline
   - Gleiche 10 Fragen aus Feature 20.1
   - Vergleiche Qualität + Performance

8. **Finale Empfehlung:**
   - Update `docs/LMSTUDIO_VS_OLLAMA_ANALYSIS.md`
   - Entscheidung: LM Studio-Parameter übernehmen oder bei Ollama-Defaults bleiben

---

## 📚 Weitere Ressourcen

- **LM Studio Dokumentation:** https://lmstudio.ai/docs
- **llama.cpp Parameter:** https://github.com/ggerganov/llama.cpp/blob/master/examples/main/README.md
- **Mirostat Paper:** https://arxiv.org/abs/2007.14966
- **RoPE Scaling:** https://arxiv.org/abs/2104.09864
- **AEGIS_Rag Sprint 20 Plan:** `docs/sprints/SPRINT_20_PLAN.md`

---

## ✅ Installation Complete Checklist

- [ ] LM Studio heruntergeladen und installiert
- [ ] Gemma 3 4B Q8 Modell heruntergeladen (~5 GB)
- [ ] Local Server konfiguriert (Port 1234)
- [ ] Server gestartet (grüner Status)
- [ ] API-Endpoint getestet (`/v1/models` funktioniert)
- [ ] Live-Monitoring funktioniert (VRAM, tokens/sec sichtbar)
- [ ] Bereit für `evaluate_lm_studio_params.py` Script

**Wenn alle Punkte ✅:** Sprint 20 Feature 20.2 kann beginnen!

---

**Version History:**
- v1.0 (2025-10-30): Initial version für Sprint 20 Feature 20.2
