# Check Current Public IP Address
Write-Host "Checking current public IP address..." -ForegroundColor Cyan
try {
    $ipInfo = Invoke-RestMethod -Uri "https://api.ipify.org?format=json" -TimeoutSec 5
    Write-Host "Your Public IP is: " -NoNewline
    Write-Host $ipInfo.ip -ForegroundColor Yellow
} catch {
    Write-Host "Failed to reach external IP service. You may be offline or blocked." -ForegroundColor Red
}

