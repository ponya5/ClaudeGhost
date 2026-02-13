@echo off
echo.
echo  ClaudeGhost Setup Wizard
echo.
python wizard.py
if %ERRORLEVEL% EQU 0 (
    echo.
    echo Setup completed!
) else (
    echo.
    echo Setup encountered an error.
)
pause
