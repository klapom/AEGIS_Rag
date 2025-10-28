# Start Backend (FastAPI + Uvicorn)
# Sprint 15: Backend startup script

Write-Host "🚀 Starting AegisRAG Backend..." -ForegroundColor Green
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path ".\src\api\main.py")) {
    Write-Host "❌ Error: Not in AegisRAG root directory!" -ForegroundColor Red
    Write-Host "Please run this script from: C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag" -ForegroundColor Yellow
    exit 1
}

Write-Host "📦 Using Poetry environment..." -ForegroundColor Cyan
Write-Host ""

# Start backend with poetry
poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
