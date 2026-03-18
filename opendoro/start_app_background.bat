@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

:: 获取脚本所在目录（支持中文路径）
set "SCRIPT_DIR=%~dp0"

:: 移除末尾的反斜杠（如果有）
if "!SCRIPT_DIR:~-1!"=="\" set "SCRIPT_DIR=!SCRIPT_DIR:~0,-1!"

:: 切换到脚本目录
cd /d "!SCRIPT_DIR!"

:: 调试信息
echo 脚本目录：!SCRIPT_DIR!
echo 当前目录：%CD%
echo.

if not exist "!SCRIPT_DIR!\runtime\pythonw.exe" (
    echo ============================================
    echo Python runtime not found!
    echo ============================================
    echo 脚本目录：!SCRIPT_DIR!
    echo 当前目录：%CD%
    echo.
    echo 尝试使用相对路径检查...
    if exist "runtime\pythonw.exe" (
        echo [成功] 相对路径 runtime\pythonw.exe 存在
        set "PYTHON_PATH=runtime\pythonw.exe"
    ) else (
        echo [失败] 相对路径 runtime\pythonw.exe 也不存在
        echo.
        echo Please run 'install_env.bat' first to set up the environment.
        echo 请先运行 'install_env.bat' 安装环境。
        echo.
        pause
        exit /b 1
    )
) else (
    set "PYTHON_PATH=!SCRIPT_DIR!\runtime\pythonw.exe"
)

set "QT_PLUGIN_PATH=!SCRIPT_DIR!\runtime\Lib\site-packages\PyQt5\Qt5\plugins"

echo ============================================
echo Starting DoroPet in background...
echo 正在后台启动 DoroPet...
echo ============================================
start "" "!PYTHON_PATH!" "!SCRIPT_DIR!\main.py" --create-shortcut
exit
