# Setup Ollama Models for AegisRAG
# This script downloads all required Ollama models for development

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "AegisRAG - Ollama Model Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Ollama is running
Write-Host "Checking Ollama status..." -ForegroundColor Yellow
$ollamaRunning = $false
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -Method GET -TimeoutSec 5 -ErrorAction Stop
    $ollamaRunning = $true
    Write-Host "✓ Ollama is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Ollama is not running or not accessible" -ForegroundColor Red
    Write-Host "  Please start Docker services first: docker compose up -d" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Models to download
$models = @(
    @{
        Name = "llama3.2:3b"
        Description = "Latest 3B model for fast query understanding"
        Size = "~2GB"
    },
    @{
        Name = "llama3.1:8b"
        Description = "Latest 8B model for high-quality generation (128K context)"
        Size = "~4.7GB"
    },
    @{
        Name = "nomic-embed-text"
        Description = "Embedding model (768-dim) for vector search"
        Size = "~274MB"
    }
)

Write-Host "Models to download:" -ForegroundColor Cyan
foreach ($model in $models) {
    Write-Host "  - $($model.Name) ($($model.Size))" -ForegroundColor White
    Write-Host "    $($model.Description)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Total download size: ~7GB" -ForegroundColor Yellow
Write-Host ""

# Download each model
$totalModels = $models.Count
$currentModel = 0

foreach ($model in $models) {
    $currentModel++
    Write-Host "[$currentModel/$totalModels] Pulling $($model.Name)..." -ForegroundColor Cyan
    Write-Host "  $($model.Description)" -ForegroundColor Gray
    Write-Host ""

    # Pull model using Ollama CLI
    $startTime = Get-Date
    ollama pull $model.Name
    $endTime = Get-Date
    $duration = ($endTime - $startTime).TotalSeconds

    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ $($model.Name) downloaded successfully (took $([math]::Round($duration, 1))s)" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to download $($model.Name)" -ForegroundColor Red
        exit 1
    }
    Write-Host ""
}

Write-Host "========================================" -ForegroundColor Green
Write-Host "All models downloaded successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Verify models
Write-Host "Verifying installed models..." -ForegroundColor Yellow
Write-Host ""

try {
    $response = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method GET
    $installedModels = $response.models | Select-Object -ExpandProperty name

    Write-Host "Installed models:" -ForegroundColor Cyan
    foreach ($model in $models) {
        $installed = $installedModels -contains $model.Name
        if ($installed) {
            Write-Host "  ✓ $($model.Name)" -ForegroundColor Green
        } else {
            Write-Host "  ✗ $($model.Name) (not found)" -ForegroundColor Red
        }
    }
} catch {
    Write-Host "Could not verify models" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Update your .env file with these models:" -ForegroundColor White
Write-Host "     OLLAMA_MODEL_QUERY=llama3.2:3b" -ForegroundColor Gray
Write-Host "     OLLAMA_MODEL_GENERATION=llama3.1:8b" -ForegroundColor Gray
Write-Host "     OLLAMA_MODEL_EMBEDDING=nomic-embed-text" -ForegroundColor Gray
Write-Host "  2. Test the setup: .\scripts\check_ollama_health.ps1" -ForegroundColor White
Write-Host "  3. Start the API server: uvicorn src.api.main:app --reload" -ForegroundColor White
Write-Host ""
