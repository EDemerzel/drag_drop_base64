# Drag and Drop Zip and Base64 Encoder with Encryption & Secure Upload

A PyQt5 GUI application for drag-and-drop ZIP compression and Base64 encoding/decoding with optional AES encryption and secure HTTPS upload capabilities.

## Features

- **Drag & Drop Interface**: Simply drag files or folders onto the window
- **Auto-detection**: Automatically detects Base64 content for decoding
- **Compression**: Compresses files/folders to ZIP then encodes as Base64
- **Extraction**: Decodes Base64 back to ZIP and extracts contents
- **🔐 AES Encryption**: Optional password-based encryption for secure file storage
- **🌐 Secure Upload**: HTTPS file upload with SSL/TLS verification
- **Security**: Protected against Zip Slip attacks during extraction

## Installation

### Standard Installation

```bash
pip install .
```

### Installation with SSL Issues (Corporate Networks)

If you encounter SSL certificate issues during installation:

#### Windows

```bash
scripts\pip_install.bat -e .[dev]
```

#### Linux/Mac

```bash
chmod +x scripts/pip_install.sh
./scripts/pip_install.sh -e .[dev]
```

#### Manual SSL Bypass

```bash
pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -e .[dev]
```

### Development Setup

#### Standard Setup

```bash
python scripts/setup_dev.py
```

#### Setup with SSL Issues

The setup script automatically handles SSL bypass for package installation in corporate/restricted networks.

#### Environment Variables for SSL Bypass

To bypass SSL verification at runtime (for network uploads):

```bash
# Windows
set DRAG_DROP_BYPASS_SSL=1

# Linux/Mac
export DRAG_DROP_BYPASS_SSL=1
```

## Usage

### GUI Application

#### Launch the graphical interface

```bash
drag-drop-zip-b64
```

#### With SSL Bypass (if needed)

```bash
# Windows
set DRAG_DROP_BYPASS_SSL=1 && drag-drop-zip-b64

# Linux/Mac
DRAG_DROP_BYPASS_SSL=1 drag-drop-zip-b64
```

### Troubleshooting SSL Issues

#### Common SSL Problems

- **Corporate Firewalls**: May block SSL connections
- **Outdated Certificates**: System certificates may be outdated
- **Proxy Servers**: May require specific configuration for pip

#### Solutions

- **Use Trusted Hosts**: All installation scripts include `--trusted-host` flags
- **Disable SSL Verification**: Set environment variables to bypass SSL checks
- **Update Certificates**: Ensure your operating system's certificates are up to date

#### Security Note

SSL bypass is only recommended for development in restricted networks. Always use proper SSL verification in production environments.

#### Testing

```bash
pip install pytest
pytest
```

### Dependencies

- **PyQt5**: GUI framework
- **cryptography**: Encryption library for secure file protection
- **requests**: HTTP library with SSL/TLS support
- **urllib3**: Advanced HTTP client with security features

## **Usage Instructions**

### **For Development Setup with SSL Issues:**

```bash
# Run the enhanced setup script
python scripts/setup_dev.py
```

### For Manual Package Installation

```bash
# Windows
scripts\pip_install.bat PyQt5 cryptography requests

# Linux/Mac
./scripts/pip_install.sh PyQt5 cryptography requests
```

### For Runtime SSL Bypass (if uploading to servers with SSL issues)

```bash
# Set environment variable before running
export DRAG_DROP_BYPASS_SSL=1
drag-drop-zip-b64
```
