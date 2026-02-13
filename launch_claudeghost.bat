@echo off
REM ClaudeGhost Launcher
REM Usage: launch_claudeghost.bat "your task" [level] [budget]
REM Example: launch_claudeghost.bat "Create a Python app" 3 10.00

set CLAUDEGHOST_DIR=%~dp0

if "%~1"=="" (
    echo Starting ClaudeGhost in interactive mode...
    python "%CLAUDEGHOST_DIR%claudeghost.py"
) else (
    set TASK=%~1
    set LEVEL=%~2
    set BUDGET=%~3
    
    if "%LEVEL%"=="" set LEVEL=3
    if "%BUDGET%"=="" set BUDGET=10.00
    
    echo Starting ClaudeGhost...
    echo Task: %TASK%
    echo Level: %LEVEL%
    echo Budget: $%BUDGET%
    echo.
    python "%CLAUDEGHOST_DIR%claudeghost.py" "%TASK%" --level %LEVEL% --budget %BUDGET%
)
