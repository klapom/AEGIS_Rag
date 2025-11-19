# AegisRAG Startup Script - Sprint 30
# Starts all required services: Backend API + Frontend UI

$ErrorActionPreference = "Stop"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "                        AegisRAG System Startup - Sprint 30                     " -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the correct directory
$projectRoot = "C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag"
if (!(Test-Path $projectRoot)) {
    Write-Host "[ERROR] Project root not found: $projectRoot" -ForegroundColor Red
    exit 1
}

Set-Location $projectRoot
Write-Host "[INFO] Working directory: $projectRoot" -ForegroundColor Green
Write-Host ""

# ============================================================================
# Step 1: Check Prerequisites
# ============================================================================

Write-Host "[1/5] Checking Prerequisites..." -ForegroundColor Yellow
Write-Host "-------------------------------------------------" -ForegroundColor Gray

# Check Poetry
try {
    $poetryVersion = poetry --version
    Write-Host "[OK] Poetry installed: $poetryVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Poetry not found. Install: https://python-poetry.org/docs/#installation" -ForegroundColor Red
    exit 1
}

# Check Docker
try {
    $dockerVersion = docker --version
    Write-Host "[OK] Docker installed: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Docker not found. Docling container will not be available." -ForegroundColor Yellow
}

# Check Node.js (for frontend)
try {
    $nodeVersion = node --version
    Write-Host "[OK] Node.js installed: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Node.js not found. Frontend will not be available." -ForegroundColor Yellow
}

Write-Host ""

# ============================================================================
# Step 2: Start Infrastructure Services (Docker)
# ============================================================================

Write-Host "[2/5] Starting Infrastructure Services (Docker)..." -ForegroundColor Yellow
Write-Host "-------------------------------------------------" -ForegroundColor Gray

try {
    Write-Host "[INFO] Starting Docker Compose services..." -ForegroundColor Cyan
    docker compose up -d

    Write-Host "[OK] Docker services started:" -ForegroundColor Green
    Write-Host "  - Qdrant:  http://localhost:6333/dashboard" -ForegroundColor White
    Write-Host "  - Neo4j:   http://localhost:7474 (neo4j/neo4j)" -ForegroundColor White
    Write-Host "  - Redis:   localhost:6379" -ForegroundColor White
    Write-Host "  - Ollama:  http://localhost:11434" -ForegroundColor White
} catch {
    Write-Host "[WARN] Docker Compose failed. Ensure Docker Desktop is running." -ForegroundColor Yellow
    Write-Host "       You can continue without Docker (some features will be disabled)" -ForegroundColor Yellow
}

Write-Host ""
Start-Sleep -Seconds 3

# ============================================================================
# Step 3: Start Backend API
# ============================================================================

Write-Host "[3/5] Starting Backend API..." -ForegroundColor Yellow
Write-Host "-------------------------------------------------" -ForegroundColor Gray

Write-Host "[INFO] Backend will start on: http://localhost:8000" -ForegroundColor Cyan
Write-Host "[INFO] OpenAPI docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "[INFO] Logs will appear below..." -ForegroundColor Cyan
Write-Host ""

# Start backend in new terminal window
$backendCmd = "cd '$projectRoot'; poetry run uvicorn src.api.main:app --reload --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

Write-Host "[OK] Backend API starting in new window..." -ForegroundColor Green
Start-Sleep -Seconds 5

# ============================================================================
# Step 4: Start Frontend UI
# ============================================================================

Write-Host "[4/5] Starting Frontend UI..." -ForegroundColor Yellow
Write-Host "-------------------------------------------------" -ForegroundColor Gray

$frontendDir = Join-Path $projectRoot "frontend"

if (Test-Path $frontendDir) {
    Write-Host "[INFO] Frontend directory found: $frontendDir" -ForegroundColor Cyan
    Write-Host "[INFO] Frontend will start on: http://localhost:5173" -ForegroundColor Cyan
    Write-Host ""

    # Check if node_modules exists
    $nodeModules = Join-Path $frontendDir "node_modules"
    if (!(Test-Path $nodeModules)) {
        Write-Host "[WARN] node_modules not found. Installing dependencies..." -ForegroundColor Yellow
        Set-Location $frontendDir
        npm install
        Set-Location $projectRoot
    }

    # Start frontend in new terminal window
    $frontendCmd = "cd '$frontendDir'; npm run dev"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

    Write-Host "[OK] Frontend UI starting in new window..." -ForegroundColor Green
} else {
    Write-Host "[WARN] Frontend directory not found: $frontendDir" -ForegroundColor Yellow
    Write-Host "       Skipping frontend startup..." -ForegroundColor Yellow
}

Write-Host ""
Start-Sleep -Seconds 3

# ============================================================================
# Step 5: Health Checks & Summary
# ============================================================================

Write-Host "[5/5] Performing Health Checks..." -ForegroundColor Yellow
Write-Host "-------------------------------------------------" -ForegroundColor Gray

Start-Sleep -Seconds 2

try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 5
    Write-Host "[OK] Backend API is healthy!" -ForegroundColor Green
    Write-Host "     Status: $($health.status)" -ForegroundColor White
} catch {
    Write-Host "[WARN] Backend API not responding yet (may still be starting)" -ForegroundColor Yellow
}

Write-Host ""

# ============================================================================
# Summary & Next Steps
# ============================================================================

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "                              SYSTEM STARTED                                    " -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Services Available:" -ForegroundColor Green
Write-Host "  [Backend API]    http://localhost:8000" -ForegroundColor White
Write-Host "  [API Docs]       http://localhost:8000/docs" -ForegroundColor White
Write-Host "  [Frontend UI]    http://localhost:5173" -ForegroundColor White
Write-Host "  [Qdrant UI]      http://localhost:6333/dashboard" -ForegroundColor White
Write-Host "  [Neo4j Browser]  http://localhost:7474" -ForegroundColor White
Write-Host ""
Write-Host "Monitoring & Observability:" -ForegroundColor Green
Write-Host "  [Prometheus]     http://localhost:9090" -ForegroundColor White
Write-Host "  [Grafana]        http://localhost:3000 (admin/admin)" -ForegroundColor White
Write-Host "  [Cost Tracking]  SQLite DB: data/cost_tracking.db" -ForegroundColor White
Write-Host ""
Write-Host "Sprint 30 Features:" -ForegroundColor Green
Write-Host "  [VLM Indexing]   POST /api/v1/admin/reindex_with_vlm" -ForegroundColor White
Write-Host "  [Admin Stats]    GET  /api/v1/admin/stats" -ForegroundColor White
Write-Host "  [Test Script]    poetry run python scripts/test_vlm_indexing.py" -ForegroundColor White
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Open Frontend:   http://localhost:5173" -ForegroundColor Cyan
Write-Host "  2. Test VLM Indexing:" -ForegroundColor Cyan
Write-Host "     curl -N 'http://localhost:8000/api/v1/admin/reindex_with_vlm?confirm=true' \" -ForegroundColor Gray
Write-Host "       -H 'Accept: text/event-stream'" -ForegroundColor Gray
Write-Host "  3. Check Grafana dashboard for costs: http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop monitoring (services will continue running)" -ForegroundColor Yellow
Write-Host "To stop all services: docker compose down" -ForegroundColor Yellow
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Keep script running to show logs
Write-Host "[INFO] Monitoring logs... (Press Ctrl+C to exit)" -ForegroundColor Cyan
try {
    docker compose logs -f
} catch {
    Write-Host "[INFO] Docker logs not available. Services running in background." -ForegroundColor Yellow
    Write-Host "       Press Ctrl+C to exit." -ForegroundColor Yellow
    while ($true) { Start-Sleep -Seconds 1 }
}
