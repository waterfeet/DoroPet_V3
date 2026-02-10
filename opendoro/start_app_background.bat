@echo off
cd /d "%~dp0"

if not exist "runtime\pythonw.exe" (
    echo Python runtime not found!
    echo Please run 'install_env.bat' first to set up the environment.
    pause
    exit /b 1
)

echo Starting DoroPet in background...
start "" "runtime\pythonw.exe" "main.py"
exit
