@echo off
cd /d "%~dp0"

if not exist "runtime\python.exe" (
    echo Python runtime not found!
    echo Please run 'install_env.bat' first to set up the environment.
    pause
    exit /b 1
)

set "QT_PLUGIN_PATH=%~dp0runtime\Lib\site-packages\PyQt5\Qt5\plugins"

echo Starting DoroPet...
:: Using python.exe to ensure console logs are captured by your LogInterface
"runtime\python.exe" "main.py" --create-shortcut
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Program exited with error code %ERRORLEVEL%.
    pause
)
