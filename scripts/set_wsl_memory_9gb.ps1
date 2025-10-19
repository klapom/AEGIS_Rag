# Set WSL2 Memory to 9GB

$wslConfigPath = "$env:USERPROFILE\.wslconfig"

# Backup if exists
if (Test-Path $wslConfigPath) {
    $backup = "$wslConfigPath.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Copy-Item $wslConfigPath $backup
    Write-Host "[BACKUP] $backup"
}

# Create new config
$config = @"
# WSL 2 Configuration
# Memory allocation (9 GB for Docker)
[wsl2]
memory=9GB
processors=4
swap=2GB
pageReporting=false
localhostForwarding=true
"@

$config | Out-File -FilePath $wslConfigPath -Encoding UTF8 -Force

Write-Host "[SUCCESS] WSL2 Memory set to 9GB"
Write-Host ""
Get-Content $wslConfigPath
