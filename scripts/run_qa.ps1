<#
.SYNOPSIS
    Integrated Q&A Workflow Script for AEGIS RAG

.DESCRIPTION
    Comprehensive workflow script that:
    1. Checks if API is running, starts it if needed
    2. Opens logging window with real-time API logs
    3. Launches interactive Q&A client (ask_question.py)

    This provides a complete development/testing workflow in one command.

.PARAMETER ApiPort
    Port for the API server (default: 8000)

.PARAMETER BaseUrl
    Base URL for API (default: http://localhost:8000)

.PARAMETER LogDir
    Directory for log files (default: logs)

.PARAMETER LogFile
    Log file path (default: logs/api.log)

.PARAMETER RestartApi
    Force restart of API even if already running

.EXAMPLE
    .\scripts\run_qa.ps1
    Standard workflow: Check API, open logs, start Q&A

.EXAMPLE
    .\scripts\run_qa.ps1 -RestartApi
    Force restart API with fresh logging, then start Q&A

.EXAMPLE
    .\scripts\run_qa.ps1 -ApiPort 8001 -BaseUrl http://localhost:8001
    Use custom port and URL

.OUTPUTS
    - API server window (PowerShell with uvicorn)
    - Logging window (tailing logs/api.log)
    - Q&A client window (interactive Python script)

.NOTES
    Sprint Context: Sprint 7-10 - Development Workflow Automation

    Workflow Steps:
    [1/3] API Check/Start
          - Tests $BaseUrl/api/v1/health/
          - Starts uvicorn in separate window if not running
          - Waits up to 120s for API to become ready

    [2/3] Logging Window
          - Opens PowerShell window with Get-Content -Wait
          - Real-time log monitoring (logs/api.log)

    [3/3] Q&A Client
          - Launches scripts/ask_question.py
          - Interactive query interface
          - Type 'exit', 'quit', or ':q' to quit

    Prerequisites:
    - Poetry environment configured
    - Docker services running (docker compose up -d)
    - All Ollama models downloaded

    Exit Codes:
    0 - Success (workflow completed)
    1 - Failure (API startup failed)

.LINK
    scripts/ask_question.py
    scripts/check_ollama_health.ps1
#>

Param(
  [int]$ApiPort = 8000,
  [string]$BaseUrl = "http://localhost:8000",
  [string]$LogDir = "logs",
  [string]$LogFile = "logs/api.log",
  [switch]$RestartApi
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Section($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }

function Test-Api {
  try { (Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/api/v1/health/" -TimeoutSec 5).StatusCode -eq 200 } catch { $false }
}

function Start-Api($Port){
  New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
  $repoRoot = (Resolve-Path "$PSScriptRoot\..\").Path
  if (Get-Command poetry -ErrorAction SilentlyContinue) {
    # Start uvicorn in new window, redirect stdout/stderr to log
    Start-Process -WindowStyle Normal -FilePath "powershell" -ArgumentList @(
      "-NoExit","-NoProfile","-Command",
      "Set-Location `"$repoRoot`"; `
       `$env:AEGIS_BASE_URL='$BaseUrl'; `
       poetry run uvicorn src.api.main:app --host 0.0.0.0 --port $Port *>> `"$LogFile`""
    ) | Out-Null
  } else {
    Start-Process -WindowStyle Normal -FilePath "powershell" -ArgumentList @(
      "-NoExit","-NoProfile","-Command",
      "Set-Location `"$repoRoot`"; `
       python -m uvicorn src.api.main:app --host 0.0.0.0 --port $Port *>> `"$LogFile`""
    ) | Out-Null
  }
}

function Wait-ApiReady($timeoutSec=90){
  $start = Get-Date
  while (((Get-Date)-$start).TotalSeconds -lt $timeoutSec){ if (Test-Api) { return $true } Start-Sleep -Seconds 2 }
  return $false
}

Write-Section "1) API prüfen/starten"
$apiRunning = Test-Api
if (-not $apiRunning) {
  Write-Host "API nicht erreichbar – starte neuen API-Prozess in separatem Fenster …" -ForegroundColor Yellow
  Start-Api -Port $ApiPort
  if (-not (Wait-ApiReady 120)) { throw "API nicht erreichbar" }
} else {
  Write-Host "API läuft bereits ($BaseUrl)" -ForegroundColor Green
  if ($RestartApi) {
    Write-Host "-RestartApi gesetzt: beende laufende API und starte neu mit Logging …" -ForegroundColor Yellow
    Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*uvicorn*' -or $_.ProcessName -like 'uvicorn*' } | Stop-Process -Force
    Start-Api -Port $ApiPort
    if (-not (Wait-ApiReady 120)) { throw "API nicht erreichbar nach Neustart" }
  }
}

Write-Section "2) Logging-Fenster öffnen"
if (Test-Path $LogFile) {
  Start-Process -WindowStyle Normal -FilePath "powershell" -ArgumentList @(
    "-NoExit","-NoProfile","-Command",
    "Get-Content `"$LogFile`" -Wait"
  ) | Out-Null
  Write-Host "Log-Tailing gestartet: $LogFile" -ForegroundColor Green
} else {
  Write-Host "Achtung: $LogFile existiert noch nicht. Logging startet, sobald die API in dieses File schreibt." -ForegroundColor Yellow
  if ($apiRunning -and -not $RestartApi) {
    Write-Host "Tipp: Für Log-Datei API mit -RestartApi neu starten." -ForegroundColor Yellow
  }
}

Write-Section "3) Interaktive Q&A starten"
$askScript = Join-Path $PSScriptRoot 'ask_question.py'
if (Get-Command poetry -ErrorAction SilentlyContinue) {
  & poetry run python "$askScript"
} else {
  & python "$askScript"
}

Write-Host "Fertig." -ForegroundColor Green
