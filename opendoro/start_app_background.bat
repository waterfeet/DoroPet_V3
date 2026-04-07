@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

:: 获取脚本所在目录（支持中文路径）
set "SCRIPT_DIR=%~dp0"

:::: 移除末尾的反斜杠（如果有）
if "!SCRIPT_DIR:~-1!"=="\" set "SCRIPT_DIR=!SCRIPT_DIR:~0,-1!"

:: 切换到脚本目录
cd /d "!SCRIPT_DIR!" >nul 2>&1

if not exist "!SCRIPT_DIR!\runtime\pythonw.exe" (
    if exist "runtime\pythonw.exe" (
        set "PYTHON_PATH=runtime\pythonw.exe"
    ) else (
        msg * "DoroPet 启动失败：Python runtime not found. Please run 'install_env.bat' first." 2>nul
        exit /b 1
    )
)

set "PYTHON_PATH=!SCRIPT_DIR!\runtime\pythonw.exe"

set "QT_PLUGIN_PATH=!SCRIPT_DIR!\runtime\Lib\site-packages\PyQt5\Qt5\plugins"

:: 后台启动应用，使用 start 命令静默启动
start "" /min "!PYTHON_PATH!" "!SCRIPT_DIR!\main.py"
exit /b
