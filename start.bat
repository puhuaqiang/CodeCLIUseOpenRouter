@echo off
chcp 65001 >nul
echo.
echo ============================================================
echo   Anthropic-to-OpenRouter Proxy Server
echo ============================================================
echo.

REM Check API Key - prioritize system environment variable
if "%OPENROUTER_API_KEY%"=="" (
    REM Try to load from .env file
    if exist ".env" (
        for /f "tokens=1,2 delims==" %%a in (.env) do (
            if "%%a"=="OPENROUTER_API_KEY" (
                set "OPENROUTER_API_KEY=%%b"
            )
        )
    )
)

REM Validate API Key
if "%OPENROUTER_API_KEY%"=="" (
    echo [ERROR] OPENROUTER_API_KEY not configured!
    echo.
    echo Please set OPENROUTER_API_KEY using one of these methods:
    echo.
    echo 1. System Environment Variable ^(Recommended^):
    echo    [CMD]        set OPENROUTER_API_KEY=sk-or-v1-...
    echo    [PowerShell] $env:OPENROUTER_API_KEY = 'sk-or-v1-...'
    echo.
    echo 2. .env file:
    echo    Create .env file with: OPENROUTER_API_KEY=sk-or-v1-...
    echo.
    echo Get API Key: https://openrouter.ai/keys
    exit /b 1
)

if "%OPENROUTER_API_KEY%"=="your_openrouter_api_key_here" (
    echo [ERROR] OPENROUTER_API_KEY not configured!
    echo.
    echo Please update OPENROUTER_API_KEY with your actual API key.
    echo Get API Key: https://openrouter.ai/keys
    exit /b 1
)

echo [OK] API Key loaded

REM Check virtual environment
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Creating virtual environment...
    uv sync
)

REM Get configuration - prioritize system environment variable
if "%PROXY_HOST%"=="" set PROXY_HOST=127.0.0.1
if "%PROXY_PORT%"=="" set PROXY_PORT=8080

echo [INFO] Starting proxy server...
echo        URL: http://%PROXY_HOST%:%PROXY_PORT%
echo        Forwarding to: https://openrouter.ai/api/v1
echo.
echo Press Ctrl+C to stop
echo.

.venv\Scripts\python start_proxy.py
