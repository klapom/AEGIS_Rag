# Start Frontend (React + Vite)
# Sprint 15: Frontend startup script

Write-Host "🎨 Starting AegisRAG Frontend..." -ForegroundColor Green
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path ".\frontend\package.json")) {
    Write-Host "❌ Error: Not in AegisRAG root directory!" -ForegroundColor Red
    Write-Host "Please run this script from: C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag" -ForegroundColor Yellow
    exit 1
}

# Change to frontend directory
Set-Location .\frontend

# Check if node_modules exists
if (-not (Test-Path ".\node_modules")) {
    Write-Host "📦 Installing dependencies..." -ForegroundColor Cyan
    npm install
    Write-Host ""
}

Write-Host "🚀 Starting Vite dev server..." -ForegroundColor Cyan
Write-Host "Frontend will be available at: http://localhost:5173" -ForegroundColor Yellow
Write-Host ""

# Start frontend
npm run dev
