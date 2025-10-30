# Download all Ollama models sequentially
# Sprint 19 Update: Current production models

Write-Host "Downloading llama3.2:3b..." -ForegroundColor Cyan
ollama pull llama3.2:3b

Write-Host "`nDownloading gemma-3-4b-it-Q8_0 (LightRAG extraction)..." -ForegroundColor Cyan
ollama pull gemma-3-4b-it-Q8_0

Write-Host "`nDownloading bge-m3 (embeddings 1024D)..." -ForegroundColor Cyan
ollama pull bge-m3

Write-Host "`n✓ All models downloaded!" -ForegroundColor Green
Write-Host "Sprint 19: Uses bge-m3 (1024D) instead of nomic-embed-text (768D)" -ForegroundColor Yellow
