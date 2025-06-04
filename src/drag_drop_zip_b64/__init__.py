"""Drag & Drop ZIP and Base64 encoding/decoding package with encryption and secure upload."""

from .drag_drop_zip_b64_threaded import DragDropZipBase64Window
from .main import main

__version__ = "1.1.0"  # Updated to match pyproject.toml
__all__ = ["main", "DragDropZipBase64Window"]
