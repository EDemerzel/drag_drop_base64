"""Tests for the drag-drop-zip-b64 application with encryption."""
import base64
import zipfile
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from drag_drop_zip_b64.drag_drop_zip_b64_threaded import DragDropZipBase64Window
from drag_drop_zip_b64.main import main


def test_password_visibility_toggle():
    """Test password field show/hide functionality."""
    window = DragDropZipBase64Window()
    window.encryption_enabled.setChecked(True)
    window.toggle_encryption(True)

    # Import QLineEdit properly for the test
    # <- This is correct, QLineEdit IS in QtWidgets
    from PyQt5.QtWidgets import QLineEdit
    assert window.password_input.echoMode() == QLineEdit.Password

    # Toggle to show
    window.toggle_password_visibility()
    assert window.password_input.echoMode() == QLineEdit.Normal
    assert window.show_password_btn.text() == "Hide"

    # Toggle back to hide
    window.toggle_password_visibility()
    assert window.password_input.echoMode() == QLineEdit.Password
    assert window.show_password_btn.text() == "Show"
