# OmniRoute AI Gateway Launcher Script (PowerShell)
Write-Host "⚡ OmniRoute Self-Hosted AI Gateway Setup" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkCyan

# Check Node.js
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Node.js is not installed. Please install Node.js 18+ from https://nodejs.org" -ForegroundColor Red
    exit 1
}

# Check if omniroute is installed
if (-not (Get-Command omniroute -ErrorAction SilentlyContinue)) {
    Write-Host "📦 Installing OmniRoute globally via npm..." -ForegroundColor Yellow
    npm install -g omniroute
}

Write-Host "🚀 Starting OmniRoute Local Gateway Proxy on http://localhost:8080..." -ForegroundColor Green
Write-Host "• Base URL: http://localhost:8080/v1" -ForegroundColor Yellow
Write-Host "• OpenAI Compatible Endpoint: http://localhost:8080/v1/chat/completions" -ForegroundColor Yellow
Write-Host "• Press Ctrl+C to stop the gateway" -ForegroundColor Gray

omniroute start --port 8080
