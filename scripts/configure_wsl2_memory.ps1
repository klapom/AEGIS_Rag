# PowerShell Script to Configure WSL 2 Memory for Docker
# This creates/updates .wslconfig in user profile

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "WSL 2 Memory Configuration Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$wslConfigPath = "$env:USERPROFILE\.wslconfig"

# Backup existing config if it exists
if (Test-Path $wslConfigPath) {
    $backupPath = "$wslConfigPath.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Copy-Item $wslConfigPath $backupPath
    Write-Host "[INFO] Existing .wslconfig backed up to: $backupPath" -ForegroundColor Yellow
}

# Create new .wslconfig with 12GB memory
$wslConfig = @"
# WSL 2 Configuration
# This file controls resource allocation for WSL 2 (used by Docker Desktop)
# Location: $wslConfigPath
# Created: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

[wsl2]
# Memory allocation (12 GB for Docker + LightRAG)
memory=12GB

# CPU cores (adjust as needed, 4 is recommended)
processors=4

# Swap size
swap=2GB

# Disable page reporting (can improve performance)
pageReporting=false

# Network mode
localhostForwarding=true
"@

# Write config
$wslConfig | Out-File -FilePath $wslConfigPath -Encoding UTF8 -Force

Write-Host "[SUCCESS] .wslconfig created at: $wslConfigPath" -ForegroundColor Green
Write-Host ""
Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  Memory: 12 GB" -ForegroundColor White
Write-Host "  CPUs: 4" -ForegroundColor White
Write-Host "  Swap: 2 GB" -ForegroundColor White
Write-Host ""

# Show content
Write-Host "Contents of .wslconfig:" -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor Gray
Get-Content $wslConfigPath | Write-Host
Write-Host "----------------------------------------" -ForegroundColor Gray
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "IMPORTANT: You must restart WSL 2 for changes to take effect!" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Run these commands in PowerShell (as Administrator):" -ForegroundColor Yellow
Write-Host ""
Write-Host "  wsl --shutdown" -ForegroundColor White
Write-Host "  Start-Sleep -Seconds 5" -ForegroundColor White
Write-Host "  docker info | Select-String 'Total Memory'" -ForegroundColor White
Write-Host ""
Write-Host "Or manually:" -ForegroundColor Yellow
Write-Host "  1. Close Docker Desktop" -ForegroundColor White
Write-Host "  2. Run: wsl --shutdown" -ForegroundColor White
Write-Host "  3. Wait 10 seconds" -ForegroundColor White
Write-Host "  4. Start Docker Desktop" -ForegroundColor White
Write-Host "  5. Verify: docker info | Select-String 'Total Memory'" -ForegroundColor White
Write-Host ""
