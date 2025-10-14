# Download all Ollama models sequentially
Write-Host "Downloading llama3.2:3b..." -ForegroundColor Cyan
ollama pull llama3.2:3b

Write-Host "`nDownloading llama3.1:8b..." -ForegroundColor Cyan
ollama pull llama3.1:8b

Write-Host "`nDownloading nomic-embed-text..." -ForegroundColor Cyan
ollama pull nomic-embed-text

Write-Host "`n✓ All models downloaded!" -ForegroundColor Green
