# PowerShell Script to Increase Docker Desktop Memory to 12GB
# Run this script as Administrator

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Docker Desktop Memory Increase Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Docker Desktop settings path
$settingsPath = "$env:APPDATA\Docker\settings.json"

# Check if Docker Desktop is installed
if (-Not (Test-Path $settingsPath)) {
    Write-Host "[ERROR] Docker Desktop settings not found at: $settingsPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please ensure Docker Desktop is installed and has been run at least once." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Manual steps:" -ForegroundColor Yellow
    Write-Host "1. Open Docker Desktop" -ForegroundColor Yellow
    Write-Host "2. Click Settings (gear icon)" -ForegroundColor Yellow
    Write-Host "3. Go to Resources -> Advanced" -ForegroundColor Yellow
    Write-Host "4. Set Memory to 12 GB" -ForegroundColor Yellow
    Write-Host "5. Click 'Apply & Restart'" -ForegroundColor Yellow
    exit 1
}

Write-Host "[INFO] Found Docker Desktop settings at: $settingsPath" -ForegroundColor Green

# Backup current settings
$backupPath = "$settingsPath.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
Copy-Item $settingsPath $backupPath
Write-Host "[INFO] Backup created at: $backupPath" -ForegroundColor Green

# Read current settings
try {
    $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
} catch {
    Write-Host "[ERROR] Failed to parse settings.json: $_" -ForegroundColor Red
    exit 1
}

# Display current memory setting
$currentMemory = $settings.memoryMiB
Write-Host ""
Write-Host "[CURRENT] Memory: $currentMemory MiB ($([math]::Round($currentMemory/1024, 2)) GB)" -ForegroundColor Yellow

# Calculate new memory (12 GB = 12288 MiB)
$newMemory = 12288

Write-Host "[NEW]     Memory: $newMemory MiB (12 GB)" -ForegroundColor Green
Write-Host ""

# Update memory setting
$settings.memoryMiB = $newMemory

# Save updated settings
try {
    $settings | ConvertTo-Json -Depth 32 | Set-Content $settingsPath
    Write-Host "[SUCCESS] Docker Desktop settings updated!" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Failed to save settings: $_" -ForegroundColor Red
    Write-Host "[INFO] Restoring backup..." -ForegroundColor Yellow
    Copy-Item $backupPath $settingsPath -Force
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "IMPORTANT: You must restart Docker Desktop for changes to take effect!" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Options:" -ForegroundColor Cyan
Write-Host "1. Restart Docker Desktop manually via GUI" -ForegroundColor White
Write-Host "2. OR run: Stop-Service 'com.docker.service' -Force; Start-Service 'com.docker.service'" -ForegroundColor White
Write-Host ""
Write-Host "After restart, verify with: docker info | findstr Memory" -ForegroundColor Cyan
Write-Host ""
