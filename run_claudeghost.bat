@echo off
if "%~1"=="" (
    echo Usage: run_claudeghost.bat "Your task here"
    exit /b 1
)
echo ClaudeGhost - Task: %~1
set CLAUDECODE=
python -m src "%~1"
