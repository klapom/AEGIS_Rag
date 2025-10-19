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
