# Drag and Drop Zip and Base64 Encoder with Encryption

A PyQt5 GUI application for drag-and-drop ZIP compression and Base64 encoding/decoding with optional AES encryption.

## Features

- **Drag & Drop Interface**: Simply drag files or folders onto the window
- **Auto-detection**: Automatically detects Base64 content for decoding
- **Compression**: Compresses files/folders to ZIP then encodes as Base64
- **Extraction**: Decodes Base64 back to ZIP and extracts contents
- **🔐 AES Encryption**: Optional password-based encryption for secure file storage
- **Security**: Protected against Zip Slip attacks during extraction

## New Encryption Features

- **Toggle Encryption**: Easy on/off switch in the UI
- **Password Protection**: PBKDF2-based key derivation with random salt
- **AES-256 Encryption**: Industry-standard encryption using cryptography library
- **Secure File Format**: Encrypted files are clearly marked and require the correct password

## Installation

```bash
pip install .
```

## Development Setup

For development, clone the repository and run the setup script:

```bash
git clone <your-repo-url>
cd drag_drop_base64
python scripts/setup_dev.py
```

This will install the package in development mode with all development dependencies.

## Development Tools

- **Testing**: `pytest`
- **Code formatting**: `black src/ tests/`
- **Import sorting**: `isort src/ tests/`
- **Type checking**: `mypy src/`

## Usage

### GUI Application

Launch the graphical interface:

```bash
drag-drop-zip-b64
```

Then:

1. **Optional**: Enable encryption and enter a password
2. Drag and drop files or folders onto the window
3. Files will be processed according to your encryption settings

### Programmatic Usage

```python
from drag_drop_zip_b64 import DragDropZipBase64Window
from PyQt5.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)
window = DragDropZipBase64Window()
window.show()
sys.exit(app.exec_())
```

## File Processing

### Without Encryption

- **Non-Base64 files/folders** → Compressed to `.zip.b64` format
- **Base64 files (`.b64`)** → Decoded to ZIP and extracted

### With Encryption

- **Non-Base64 files/folders** → Compressed to `.encrypted.zip.b64` format (password-protected)
- **Encrypted Base64 files** → Require correct password for decoding and extraction

## Security Notes

- **Password Storage**: Passwords are never stored, only used for key derivation
- **Salt Generation**: Each encryption uses a unique random salt
- **Key Derivation**: PBKDF2 with 100,000 iterations and SHA-256
- **Encryption Algorithm**: AES-256 in CBC mode with HMAC authentication

## Testing

```bash
pip install pytest
pytest
```

## Dependencies

- **PyQt5**: GUI framework
- **cryptography**: Encryption library for secure file protection
