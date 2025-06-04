"""Tests for the drag-drop-zip-b64 application."""
import base64
import zipfile
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from drag_drop_zip_b64.drag_drop_zip_b64_threaded import DragDropZipBase64Window
from drag_drop_zip_b64.main import main


def test_smoke(monkeypatch):
    """Test that main() can be called without launching a real GUI."""
    monkeypatch.setattr("drag_drop_zip_b64.main.QApplication",
                        lambda *args: MagicMock())
    monkeypatch.setattr("drag_drop_zip_b64.main.sys.exit", lambda x: None)

    # Should not raise any exceptions
    main()


def test_window_creation():
    """Test that the window can be created without errors."""
    window = DragDropZipBase64Window()
    assert window.windowTitle() == 'Drag & Drop Ultra Compress & Base64'
    assert window.acceptDrops() is True


def test_is_base64_data():
    """Test Base64 detection logic."""
    window = DragDropZipBase64Window()

    # Valid Base64
    valid_b64 = base64.b64encode(b"Hello, World!")
    assert window.is_base64_data(valid_b64) is True

    # Invalid Base64
    assert window.is_base64_data(b"Not base64 content!") is False
    assert window.is_base64_data(b"") is False


def test_compress_to_zip(tmp_path):
    """Test ZIP compression of files and directories."""
    window = DragDropZipBase64Window()

    # Test file compression
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, World!")

    zip_data = window.compress_to_zip(test_file)
    assert len(zip_data) > 0

    # Verify it's a valid ZIP
    with zipfile.ZipFile(BytesIO(zip_data), 'r') as zf:
        assert "test.txt" in zf.namelist()
        assert zf.read("test.txt") == b"Hello, World!"

    # Test directory compression
    test_dir = tmp_path / "testdir"
    test_dir.mkdir()
    (test_dir / "file1.txt").write_text("Content 1")
    (test_dir / "file2.txt").write_text("Content 2")

    zip_data = window.compress_to_zip(test_dir)
    with zipfile.ZipFile(BytesIO(zip_data), 'r') as zf:
        files = zf.namelist()
        assert "file1.txt" in files
        assert "file2.txt" in files


def test_zip_and_encode(tmp_path):
    """Test the complete zip and encode process."""
    window = DragDropZipBase64Window()

    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, World!")

    window.zip_and_encode(test_file)

    # Check that .zip.b64 file was created
    b64_file = tmp_path / "test.txt.zip.b64"
    assert b64_file.exists()

    # Verify it's valid Base64
    b64_data = b64_file.read_bytes()
    decoded = base64.b64decode(b64_data)

    # Verify decoded data is a valid ZIP
    with zipfile.ZipFile(BytesIO(decoded), 'r') as zf:
        assert "test.txt" in zf.namelist()


def test_decode_and_extract(tmp_path):
    """Test Base64 decode and ZIP extraction."""
    window = DragDropZipBase64Window()

    # Create a test ZIP in memory
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        zf.writestr("test.txt", "Hello, World!")

    # Encode as Base64
    zip_data = zip_buffer.getvalue()
    b64_data = base64.b64encode(zip_data)

    # Write B64 file
    b64_file = tmp_path / "test.zip.b64"
    b64_file.write_bytes(b64_data)

    # Decode and extract
    window.decode_and_extract(b64_file, b64_data)

    # Check extraction results
    extracted_dir = tmp_path / "test.zip"
    assert extracted_dir.exists()
    assert (extracted_dir / "test.txt").exists()
    assert (extracted_dir / "test.txt").read_text() == "Hello, World!"
