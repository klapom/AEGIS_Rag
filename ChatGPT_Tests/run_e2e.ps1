Param(
  [string]$PythonExe = "python",
  [int]$ApiPort = 8000
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Section($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }

Write-Section "1) Docker-Services starten (Ollama, Qdrant, Neo4j, Redis)"
if (Get-Command docker -ErrorAction SilentlyContinue) {
  docker compose up -d
} else {
  Write-Error "Docker nicht gefunden. Bitte Docker Desktop installieren/starten."
}

Write-Section "2) Health-Checks: Ollama/Qdrant/Neo4j/Redis"
function Wait-Http($url, $timeoutSec=300) {
  $start = Get-Date
  while (((Get-Date) - $start).TotalSeconds -lt $timeoutSec) {
    try {
      $r = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 10
      if ($r.StatusCode -eq 200) { return }
    } catch { }
    Start-Sleep -Seconds 3
  }
  throw "Service not healthy after $timeoutSec s: $url"
}

Wait-Http "http://localhost:11434/api/tags"      # Ollama
Wait-Http "http://localhost:6333/health"         # Qdrant
Wait-Http "http://localhost:7474"                 # Neo4j (UI)

Write-Section "3) Ollama-Modelle laden"
$pullFull = $env:AEGIS_PULL_FULL_MODELS
if ([string]::IsNullOrEmpty($pullFull)) { $pullFull = "0" }
if ($pullFull -eq "1" -and (Test-Path "scripts/setup_ollama_models.ps1")) {
  pwsh -NoProfile -ExecutionPolicy Bypass -File "scripts/setup_ollama_models.ps1"
} else {
  Write-Host "Minimal: ziehe benötigte Modelle 'llama3.2:3b' und 'nomic-embed-text'" -ForegroundColor Yellow
  ollama pull llama3.2:3b
  ollama pull nomic-embed-text
}

Write-Section "4) Python-Umgebung vorbereiten (Poetry bevorzugt)"
if (Get-Command poetry -ErrorAction SilentlyContinue) {
  poetry install
} else {
  & $PythonExe -m pip install --upgrade pip
  & $PythonExe -m pip install -e . pytest pytest-asyncio requests
}

Write-Section "5) API starten"
if (Get-Command poetry -ErrorAction SilentlyContinue) {
  $proc = Start-Process -NoNewWindow -PassThru -FilePath "poetry" -ArgumentList @('run','uvicorn','src.api.main:app','--host','0.0.0.0','--port',"$ApiPort")
} else {
  $proc = Start-Process -NoNewWindow -PassThru -FilePath $PythonExe -ArgumentList @('-m','uvicorn','src.api.main:app','--host','0.0.0.0','--port',"$ApiPort")
}

function Stop-Api { if ($proc -and !$proc.HasExited) { $proc | Stop-Process } }
Register-EngineEvent PowerShell.Exiting -Action { Stop-Api }

Write-Section "6) Auf API warten"
Wait-Http "http://localhost:$ApiPort/healthz"

Write-Section "7) E2E-Tests ausführen (ChatGPT_Tests)"
$env:AEGIS_BASE_URL = "http://localhost:$ApiPort"
$env:LIGHRAG_LLM_MODEL = "llama3.2:3b"
$env:OLLAMA_MODEL_EMBEDDING = "nomic-embed-text"
if (Get-Command poetry -ErrorAction SilentlyContinue) {
  poetry run pytest -q ChatGPT_Tests
} else {
  pytest -q ChatGPT_Tests
}

Write-Section "8) API stoppen"
Stop-Api

Write-Host "E2E abgeschlossen." -ForegroundColor Green
