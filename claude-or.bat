@echo off
chcp 65001 >nul
REM Launch Claude Code CLI with OpenRouter proxy settings

set ANTHROPIC_API_KEY=dummy-key-for-openrouter
set ANTHROPIC_BASE_URL=http://127.0.0.1:8080

REM Check if proxy is running
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8080/' -TimeoutSec 2 -UseBasicParsing; exit 0 } catch { exit 1 }"
if errorlevel 1 (
    echo [ERROR] Proxy server is not running!
    echo.
    echo Please start the proxy first:
    echo   start.bat
    echo.
    pause
    exit /b 1
)

echo [INFO] Launching Claude Code with OpenRouter proxy...
echo [INFO] API Base: http://127.0.0.1:8080
echo.

claude %*
