#!/usr/bin/env pwsh
# Anthropic-to-OpenRouter Proxy Server Startup Script

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Anthropic-to-OpenRouter Proxy Server" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 加载 .env 文件到当前会话（如果不存在则忽略）
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^([^#][^=]*)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            # 仅在环境变量不存在时才设置（系统环境变量优先级更高）
            if (-not [Environment]::GetEnvironmentVariable($key)) {
                [Environment]::SetEnvironmentVariable($key, $value, "Process")
            }
        }
    }
}

# 检查 API Key - 现在优先使用系统环境变量（如果存在），否则使用 .env 中的值
$apiKey = [Environment]::GetEnvironmentVariable("OPENROUTER_API_KEY")

if (-not $apiKey -or $apiKey -eq "your_openrouter_api_key_here") {
    Write-Host "[ERROR] OPENROUTER_API_KEY not configured!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please set OPENROUTER_API_KEY using one of these methods:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "1. System Environment Variable (Recommended):" -ForegroundColor Green
    Write-Host "   [Current Session]  `$env:OPENROUTER_API_KEY = 'sk-or-v1-...'" -ForegroundColor Gray
    Write-Host "   [User Permanent]   [Environment]::SetEnvironmentVariable('OPENROUTER_API_KEY', 'sk-or-v1-...', 'User')" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. .env file:" -ForegroundColor Green
    Write-Host "   Create .env file with: OPENROUTER_API_KEY=sk-or-v1-..." -ForegroundColor Gray
    Write-Host ""
    Write-Host "Get API Key: https://openrouter.ai/keys" -ForegroundColor Cyan
    exit 1
}

# 显示已加载的 API Key（脱敏）
$maskedKey = $apiKey.Substring(0, [Math]::Min(10, $apiKey.Length)) + "..." + $apiKey.Substring([Math]::Max(0, $apiKey.Length - 4))
Write-Host "[OK] API Key loaded: $maskedKey" -ForegroundColor Green

# 检查虚拟环境
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[INFO] Creating virtual environment..." -ForegroundColor Green
    uv sync
}

# 获取配置 - 优先使用系统环境变量，然后是 .env 加载的值
$host_ip = [Environment]::GetEnvironmentVariable("PROXY_HOST")
if (-not $host_ip) { $host_ip = "127.0.0.1" }

$port = [Environment]::GetEnvironmentVariable("PROXY_PORT")
if (-not $port) { $port = "8080" }

Write-Host "[INFO] Starting proxy server..." -ForegroundColor Green
Write-Host "       URL: http://${host_ip}:${port}" -ForegroundColor Gray
Write-Host "       Forwarding to: https://openrouter.ai/api/v1" -ForegroundColor Gray
Write-Host ""
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

& ".venv\Scripts\python.exe" "start_proxy.py"
