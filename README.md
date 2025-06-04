# Drag and Drop Zip and Base64 Encoder

A PyQt5 GUI application for drag-and-drop ZIP compression and Base64 encoding/decoding.

## Features

- **Drag & Drop Interface**: Simply drag files or folders onto the window
- **Auto-detection**: Automatically detects Base64 content for decoding
- **Compression**: Compresses files/folders to ZIP then encodes as Base64
- **Extraction**: Decodes Base64 back to ZIP and extracts contents
- **Security**: Protected against Zip Slip attacks during extraction

## Installation

```bash
pip install .
```

## Usage

### GUI Application

Launch the graphical interface:

```bash
drag-drop-zip-b64
```

Then drag and drop files or folders onto the window.

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

## Testing

```bash
pip install pytest
pytest
```

## File Processing

- **Non-Base64 files/folders** → Compressed to `.zip.b64` format
- **Base64 files (`.b64`)** → Decoded to ZIP and extracted
