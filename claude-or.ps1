#!/usr/bin/env pwsh
# Launch Claude Code CLI with OpenRouter proxy settings

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$env:ANTHROPIC_API_KEY = "dummy-key-for-openrouter"
$env:ANTHROPIC_BASE_URL = "http://127.0.0.1:8080"

# Check if proxy is running
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8080/" -TimeoutSec 2 -UseBasicParsing
    $status = $response.Content | ConvertFrom-Json
    if ($status.status -ne "ok") {
        throw "Invalid response"
    }
} catch {
    Write-Host "[ERROR] Proxy server is not running!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please start the proxy first:" -ForegroundColor Yellow
    Write-Host "  .\start.ps1" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

Write-Host "[INFO] Launching Claude Code with OpenRouter proxy..." -ForegroundColor Green
Write-Host "[INFO] API Base: http://127.0.0.1:8080" -ForegroundColor Gray
Write-Host ""

& claude @args
