# Ollama Health Check Script for AegisRAG
# Verifies Ollama is running and required models are loaded
# Sprint 19 Update: Updated for current production models

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Ollama Health Check (Sprint 19)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Required models (Sprint 19 production)
$requiredModels = @("llama3.2:3b", "gemma-3-4b-it-Q8_0", "bge-m3")

# Check if Ollama is reachable
Write-Host "[1/3] Checking Ollama connectivity..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method GET -TimeoutSec 5
    Write-Host "✓ Ollama is running on http://localhost:11434" -ForegroundColor Green
} catch {
    Write-Host "✗ Ollama is not reachable" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Check if Docker is running: docker ps" -ForegroundColor White
    Write-Host "  2. Start services: docker compose up -d" -ForegroundColor White
    Write-Host "  3. Check Ollama logs: docker compose logs ollama" -ForegroundColor White
    exit 1
}

Write-Host ""

# Check installed models
Write-Host "[2/3] Checking installed models..." -ForegroundColor Yellow
$installedModels = $response.models | Select-Object -ExpandProperty name

$allModelsPresent = $true
foreach ($model in $requiredModels) {
    $installed = $installedModels -contains $model
    if ($installed) {
        $modelInfo = $response.models | Where-Object { $_.name -eq $model }
        $sizeGB = [math]::Round($modelInfo.size / 1GB, 2)
        Write-Host "  ✓ $model ($sizeGB GB)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $model (not found)" -ForegroundColor Red
        $allModelsPresent = $false
    }
}

if (-not $allModelsPresent) {
    Write-Host ""
    Write-Host "Missing models detected!" -ForegroundColor Yellow
    Write-Host "  Run: .\scripts\setup_ollama_models.ps1" -ForegroundColor White
    exit 1
}

Write-Host ""

# Test model inference
Write-Host "[3/3] Testing model inference..." -ForegroundColor Yellow

$testModel = "llama3.2:3b"
$testPrompt = "Hello! Respond with just 'OK' if you can read this."

try {
    $body = @{
        model = $testModel
        prompt = $testPrompt
        stream = $false
        options = @{
            temperature = 0.1
            num_predict = 10
        }
    } | ConvertTo-Json

    $inferenceResponse = Invoke-RestMethod -Uri "http://localhost:11434/api/generate" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 30

    Write-Host "  ✓ Model inference successful" -ForegroundColor Green
    Write-Host "    Model: $testModel" -ForegroundColor Gray
    Write-Host "    Response: $($inferenceResponse.response.Trim())" -ForegroundColor Gray
    Write-Host "    Load duration: $([math]::Round($inferenceResponse.load_duration / 1000000))ms" -ForegroundColor Gray
    Write-Host "    Total duration: $([math]::Round($inferenceResponse.total_duration / 1000000))ms" -ForegroundColor Gray
} catch {
    Write-Host "  ✗ Model inference failed" -ForegroundColor Red
    Write-Host "    Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "All checks passed! Ollama is healthy ✓" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Show system info
Write-Host "System Information:" -ForegroundColor Cyan
Write-Host "  Ollama URL: http://localhost:11434" -ForegroundColor White
Write-Host "  Installed models: $($installedModels.Count)" -ForegroundColor White
Write-Host "  Required models: $($requiredModels.Count)" -ForegroundColor White

$totalSize = ($response.models | Measure-Object -Property size -Sum).Sum
$totalSizeGB = [math]::Round($totalSize / 1GB, 2)
Write-Host "  Total model size: $totalSizeGB GB" -ForegroundColor White

Write-Host ""
Write-Host "Ready to use! Start the API server:" -ForegroundColor Cyan
Write-Host "  poetry run uvicorn src.api.main:app --reload" -ForegroundColor White
Write-Host ""
Write-Host "Note: Sprint 19 uses bge-m3 (1024D) instead of nomic-embed-text (768D)" -ForegroundColor Yellow
Write-Host ""
