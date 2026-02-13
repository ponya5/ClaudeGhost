@echo off
echo.
echo ====================================
echo  ClaudeGhost Interactive Setup
echo ====================================
echo.
python setup_interactive.py
if %ERRORLEVEL% EQU 0 (
    echo.
    echo Setup completed successfully!
) else (
    echo.
    echo Setup failed. Check errors above.
)
pause
