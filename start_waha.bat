@echo off
REM WAHA Server Launcher for Windows
REM ClaudeGhost - WhatsApp HTTP API Server Manager

echo.
echo  ====================================
echo   WAHA Server Launcher (Windows)
echo  ====================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Install Python from: https://python.org
    pause
    exit /b 1
)

REM Get the directory of this script
set SCRIPT_DIR=%~dp0

REM Run the Python script with all arguments
python "%SCRIPT_DIR%start_waha.py" %*

if errorlevel 1 (
    echo.
    echo [ERROR] WAHA startup failed
    pause
    exit /b 1
)

exit /b 0
