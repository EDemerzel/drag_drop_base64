#!/bin/bash
# Shell script for pip installation with SSL bypass on Linux/Mac

echo "🔧 Installing packages with SSL bypass..."

export PYTHONHTTPSVERIFY=0
export CURL_CA_BUNDLE=""
export REQUESTS_CA_BUNDLE=""

python3 -m pip install \
    --trusted-host pypi.org \
    --trusted-host pypi.python.org \
    --trusted-host files.pythonhosted.org \
    --disable-pip-version-check \
    --no-cache-dir \
    "$@"

if [ $? -eq 0 ]; then
    echo "✅ Installation successful!"
else
    echo "❌ Installation failed!"
    exit 1
fi
