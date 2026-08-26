# ==========================================
# Discord Bot - AWS EC2 Deployment Script
# ==========================================
param (
    [string]$KeyPath = "C:\Users\manga\Downloads\vortex.pem",
    [string]$HostIp = "54.83.90.208",
    [string]$User = "ubuntu",
    [string]$RemoteDir = "/home/ubuntu",
    [string]$ProcessName = "discord-bot"
)

$ErrorActionPreference = "Stop"

Write-Host "[1/3] Uploading modular code to AWS EC2 ($HostIp)..." -ForegroundColor Cyan

# Upload root files
$filesToUpload = @("main.py", "utils.py", "requirements.txt")
foreach ($file in $filesToUpload) {
    if (Test-Path $file) {
        Write-Host "  -> Uploading $file..." -ForegroundColor Gray
        scp -i "$KeyPath" -o StrictHostKeyChecking=accept-new "$file" "${User}@${HostIp}:${RemoteDir}/"
    }
}

# Upload cogs directory recursively
if (Test-Path "cogs") {
    Write-Host "  -> Uploading cogs/ modules directory..." -ForegroundColor Gray
    scp -i "$KeyPath" -r -o StrictHostKeyChecking=accept-new "cogs" "${User}@${HostIp}:${RemoteDir}/"
}

# Upload templates directory recursively
if (Test-Path "templates") {
    Write-Host "  -> Uploading templates/ view directory..." -ForegroundColor Gray
    scp -i "$KeyPath" -r -o StrictHostKeyChecking=accept-new "templates" "${User}@${HostIp}:${RemoteDir}/"
}

# Upload static directory recursively
if (Test-Path "static") {
    Write-Host "  -> Uploading static/ asset directory..." -ForegroundColor Gray
    scp -i "$KeyPath" -r -o StrictHostKeyChecking=accept-new "static" "${User}@${HostIp}:${RemoteDir}/"
}

Write-Host "[2/3] Restarting bot service with PM2 on AWS..." -ForegroundColor Cyan
ssh -i "$KeyPath" "${User}@${HostIp}" "pm2 restart $ProcessName"

Write-Host "[3/3] Checking PM2 Status and Recent Logs..." -ForegroundColor Cyan
ssh -i "$KeyPath" "${User}@${HostIp}" "pm2 status; pm2 logs $ProcessName --lines 20 --nostream"

Write-Host "`nDeployment complete! Your 300+ command bot is live on AWS EC2." -ForegroundColor Green
