@echo off
setlocal
cd /d "%~dp0"

set "RUNTIME_DIR=runtime"
set "PYTHON_VER=3.12.10"
set "PYTHON_ZIP=python-%PYTHON_VER%-embed-amd64.zip"
set "PYTHON_URL_1=https://npmmirror.com/mirrors/python/%PYTHON_VER%/%PYTHON_ZIP%"
set "PYTHON_URL_2=https://mirrors.huaweicloud.com/python/%PYTHON_VER%/%PYTHON_ZIP%"
set "PYTHON_URL_3=https://www.python.org/ftp/python/%PYTHON_VER%/%PYTHON_ZIP%"
set "GET_PIP_URL_1=https://mirror.ghproxy.com/https://github.com/pypa/get-pip/raw/main/public/get-pip.py"
set "GET_PIP_URL_2=https://bootstrap.pypa.io/get-pip.py"

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
        exit /b 1
    )
    
    echo Installing pip...
    "%RUNTIME_DIR%\python.exe" "%RUNTIME_DIR%\get-pip.py" -i https://pypi.tuna.tsinghua.edu.cn/simple --no-warn-script-location
)

echo [4/7] Installing dependencies from requirements.txt...
"%RUNTIME_DIR%\python.exe" -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --no-warn-script-location

echo [5/7] Installing local pylive2d...
:: Using the specific wheel found in your project
if exist "live2dpy\Live2D-Python\whls\pylive2d-1.3-cp312-cp312-win_amd64.whl" (
    "%RUNTIME_DIR%\python.exe" -m pip install "live2dpy\Live2D-Python\whls\pylive2d-1.3-cp312-cp312-win_amd64.whl" --no-warn-script-location
) else (
    echo Warning: pylive2d wheel not found! Please ensure live2dpy folder is present.
)

echo [6/7] Downloading voice models...
if not exist "models\voice" mkdir "models\voice"

set "KWS_MODEL=sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01"
set "ASR_MODEL=sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20"

:: Using mirror proxies for acceleration (GitHub Proxy)
set "GH_PROXY_1=https://mirror.ghproxy.com/"
set "GH_PROXY_2=https://ghproxy.net/"
set "GH_PROXY_3=https://moeyy.cn/gh-proxy/"

set "KWS_URL_BASE=https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/%KWS_MODEL%.tar.bz2"
set "ASR_URL_BASE=https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/%ASR_MODEL%.tar.bz2"

if exist "models\voice\%KWS_MODEL%\tokens.txt" (
    echo KWS model already exists.
) else (
    echo Downloading KWS model...
    "%RUNTIME_DIR%\python.exe" "tools\download_model.py" "models\voice\%KWS_MODEL%.tar.bz2" "%GH_PROXY_1%%KWS_URL_BASE%" "%GH_PROXY_2%%KWS_URL_BASE%" "%GH_PROXY_3%%KWS_URL_BASE%"
    if errorlevel 1 (
        echo Failed to download KWS model.
        exit /b 1
    )
    
    if exist "models\voice\%KWS_MODEL%.tar.bz2" (
        echo Extracting KWS model...
        "%RUNTIME_DIR%\python.exe" -c "import tarfile, sys; tarfile.open(sys.argv[1], 'r:bz2').extractall(sys.argv[2])" "models\voice\%KWS_MODEL%.tar.bz2" "models\voice"
        del "models\voice\%KWS_MODEL%.tar.bz2"
    )
)

if exist "models\voice\%ASR_MODEL%\tokens.txt" (
    echo ASR model already exists.
) else (
    echo Downloading ASR model...
    echo Note: This file is large ~500MB . Using download accelerator...
    "%RUNTIME_DIR%\python.exe" "tools\download_model.py" "models\voice\%ASR_MODEL%.tar.bz2" "%GH_PROXY_1%%ASR_URL_BASE%" "%GH_PROXY_2%%ASR_URL_BASE%" "%GH_PROXY_3%%ASR_URL_BASE%"
    if errorlevel 1 (
        echo Failed to download ASR model.
        exit /b 1
    )
    
    if exist "models\voice\%ASR_MODEL%.tar.bz2" (
        echo Extracting ASR model...
        "%RUNTIME_DIR%\python.exe" -c "import tarfile, sys; tarfile.open(sys.argv[1], 'r:bz2').extractall(sys.argv[2])" "models\voice\%ASR_MODEL%.tar.bz2" "models\voice"
        del "models\voice\%ASR_MODEL%.tar.bz2"
    )
)

echo [7/7] Setup complete!
echo.
echo Starting DoroPet...
call start_app_background.bat

