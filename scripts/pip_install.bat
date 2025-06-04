@echo off
REM Batch script for pip installation with SSL bypass on Windows

echo 🔧 Installing packages with SSL bypass...

set PYTHONHTTPSVERIFY=0
set CURL_CA_BUNDLE=
set REQUESTS_CA_BUNDLE=

python -m pip install ^
    --trusted-host pypi.org ^
    --trusted-host pypi.python.org ^
    --trusted-host files.pythonhosted.org ^
    --disable-pip-version-check ^
    --no-cache-dir ^
    %*

if %ERRORLEVEL% EQU 0 (
    echo ✅ Installation successful!
) else (
    echo ❌ Installation failed!
    exit /b 1
)