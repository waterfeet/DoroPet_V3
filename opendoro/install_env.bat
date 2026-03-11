@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "RUNTIME_DIR=runtime"
set "PYTHON_VER=3.12.10"
set "PYTHON_ZIP=python-%PYTHON_VER%-embed-amd64.zip"
set "PYTHON_URL_1=https://npmmirror.com/mirrors/python/%PYTHON_VER%/%PYTHON_ZIP%"
set "PYTHON_URL_2=https://mirrors.huaweicloud.com/python/%PYTHON_VER%/%PYTHON_ZIP%"
set "PYTHON_URL_3=https://www.python.org/ftp/python/%PYTHON_VER%/%PYTHON_ZIP%"
set "GET_PIP_URL_1=https://bootstrap.pypa.io/get-pip.py"
set "GET_PIP_URL_2=https://mirror.ghproxy.com/https://github.com/pypa/get-pip/raw/main/public/get-pip.py"

echo ========================================================
echo      DoroPet Environment Installer (Portable)
echo ========================================================

echo [1/7] Checking Python environment...
if exist "%RUNTIME_DIR%\python.exe" (
    echo Python %PYTHON_VER% already installed in %RUNTIME_DIR%.
) else (
    echo Downloading Python %PYTHON_VER% Embeddable Package...
    if not exist "%RUNTIME_DIR%" mkdir "%RUNTIME_DIR%"
    
    powershell -ExecutionPolicy Bypass -File "tools\download_with_fallback.ps1" -OutFile "%RUNTIME_DIR%\%PYTHON_ZIP%" -Urls "%PYTHON_URL_1%,%PYTHON_URL_2%,%PYTHON_URL_3%"
    if errorlevel 1 (
        echo Failed to download Python from all mirrors.
        pause
        exit /b 1
    )
    
    if exist "%RUNTIME_DIR%\%PYTHON_ZIP%" (
        echo Extracting Python...
        powershell -Command "Expand-Archive -Path '%RUNTIME_DIR%\%PYTHON_ZIP%' -DestinationPath '%RUNTIME_DIR%' -Force"
        del "%RUNTIME_DIR%\%PYTHON_ZIP%"
    ) else (
        echo Failed to download Python. Please check your internet connection.
        pause
        exit /b 1
    )
)

echo [2/7] Configuring python._pth for pip support...
set "PTH_FILE=%RUNTIME_DIR%\python312._pth"
:: This enables site-packages, required for pip
powershell -Command "if (Test-Path '%PTH_FILE%') { (Get-Content '%PTH_FILE%') -replace '#import site', 'import site' | Set-Content '%PTH_FILE%' }"

echo [3/7] Checking pip...
if not exist "%RUNTIME_DIR%\Scripts\pip.exe" (
    echo Downloading get-pip.py...
    powershell -ExecutionPolicy Bypass -File "tools\download_with_fallback.ps1" -OutFile "%RUNTIME_DIR%\get-pip.py" -Urls "%GET_PIP_URL_1%,%GET_PIP_URL_2%"
    if errorlevel 1 (
        echo Failed to download get-pip.py from all mirrors.
        pause
        exit /b 1
    )
    
    echo Installing pip...
    "%RUNTIME_DIR%\python.exe" "%RUNTIME_DIR%\get-pip.py" -i https://pypi.tuna.tsinghua.edu.cn/simple --no-warn-script-location
)

REM =================== 新增修复开始 ===================
echo [3.5/7] Installing build essentials (Fix for BackendUnavailable)...
"%RUNTIME_DIR%\python.exe" -m pip install --upgrade setuptools wheel -i https://pypi.tuna.tsinghua.edu.cn/simple --no-warn-script-location
REM =================== 新增修复结束 ===================

REM =================== 新增sherpa-onnx修复开始 ===================
echo [3.8/7] Manually installing sherpa-onnx (Fix for installation failure)...
"%RUNTIME_DIR%\python.exe" -m pip install "https://hf-mirror.com/csukuangfj2/sherpa-onnx-wheels/resolve/main/cpu/1.12.23/sherpa_onnx-1.12.23-cp312-cp312-win_amd64.whl" --no-warn-script-location
if errorlevel 1 (
    echo Failed to install sherpa-onnx manually. Continuing with requirements.txt...
)
REM =================== 新增sherpa-onnx修复结束 ===================

echo [4/7] Installing dependencies from requirements.txt...
"%RUNTIME_DIR%\python.exe" -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --no-warn-script-location

echo [5/7] Skipping local pylive2d (now using live2d-py from PyPI)...

echo [6/7] Skipping voice models download (Use Voice Settings to download)...
if not exist "models\voice" mkdir "models\voice"


echo [7/7] Setup complete!
echo.
powershell -Command "Write-Host '环境安装完成！即将启动 Doro Pet...' -ForegroundColor Green"
powershell -Command "Write-Host '程序将在 3 秒后自动启动，按 Ctrl+C 取消...' -ForegroundColor Yellow"
timeout /t 3 /nobreak >nul
powershell -Command "Write-Host '正在启动 Doro Pet...' -ForegroundColor Green"
call start_app_background.bat
