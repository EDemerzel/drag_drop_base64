"""Tests for the drag-drop-zip-b64 application with encryption."""
import base64
import zipfile
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

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
    assert window.windowTitle() == 'Drag & Drop Ultra Compress & Base64 with Encryption'
    assert window.acceptDrops() is True
    assert window.encryption_enabled.isChecked() is False


def test_encryption_toggle():
    """Test encryption UI toggle functionality."""
    window = DragDropZipBase64Window()

    # Initially disabled
    assert window.password_input.isEnabled() is False
    assert window.show_password_btn.isEnabled() is False

    # Enable encryption
    window.encryption_enabled.setChecked(True)
    window.toggle_encryption(True)

    assert window.password_input.isEnabled() is True
    assert window.show_password_btn.isEnabled() is True
    assert "Enabled" in window.encryption_status.text()


def test_password_visibility_toggle():
    """Test password field show/hide functionality."""
    window = DragDropZipBase64Window()
    window.encryption_enabled.setChecked(True)
    window.toggle_encryption(True)

    # Initially hidden
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


def test_encryption_key_derivation():
    """Test encryption key derivation from password."""
    window = DragDropZipBase64Window()

    password = "test_password"
    salt = b"1234567890123456"  # 16 bytes

    key1 = window.get_encryption_key(password, salt)
    key2 = window.get_encryption_key(password, salt)

    # Same password and salt should produce same key
    assert key1 == key2
    assert len(key1) == 44  # base64 encoded 32-byte key

    # Different salt should produce different key
    different_salt = b"6543210987654321"
    key3 = window.get_encryption_key(password, different_salt)
    assert key1 != key3


def test_encryption_decryption():
    """Test data encryption and decryption."""
    window = DragDropZipBase64Window()

    original_data = b"Hello, World! This is test data for encryption."
    password = "test_password_123"

    # Encrypt
    encrypted_data, salt = window.encrypt_data(original_data, password)
    assert encrypted_data != original_data
    assert len(salt) == 16

    # Decrypt
    decrypted_data = window.decrypt_data(encrypted_data, salt, password)
    assert decrypted_data == original_data

    # Wrong password should fail
    with pytest.raises(ValueError, match="Decryption failed"):
        window.decrypt_data(encrypted_data, salt, "wrong_password")


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


def test_zip_and_encode_without_encryption(tmp_path):
    """Test the complete zip and encode process without encryption."""
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


def test_zip_and_encode_with_encryption(tmp_path):
    """Test the complete zip and encode process with encryption."""
    window = DragDropZipBase64Window()

    # Enable encryption
    window.encryption_enabled.setChecked(True)
    window.password_input.setText("test_password")

    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, World!")

    window.zip_and_encode(test_file)

    # Check that .encrypted.zip.b64 file was created
    b64_file = tmp_path / "test.txt.encrypted.zip.b64"
    assert b64_file.exists()

    # Verify it's valid Base64
    b64_data = b64_file.read_bytes()
    decoded = base64.b64decode(b64_data)

    # Should start with encryption marker
    assert decoded.startswith(b"ENCRYPTED:")


def test_decode_and_extract_encrypted(tmp_path):
    """Test Base64 decode and ZIP extraction with encryption."""
    window = DragDropZipBase64Window()

    # Create a test ZIP in memory
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        zf.writestr("test.txt", "Hello, World!")

    zip_data = zip_buffer.getvalue()
    password = "test_password_123"

    # Encrypt the ZIP data
    encrypted_data, salt = window.encrypt_data(zip_data, password)

    # Create the full encrypted format
    encrypted_format = b"ENCRYPTED:" + salt + encrypted_data
    b64_data = base64.b64encode(encrypted_format)

    # Write B64 file
    b64_file = tmp_path / "test.zip.b64"
    b64_file.write_bytes(b64_data)

    # Enable encryption and set password
    window.encryption_enabled.setChecked(True)
    window.password_input.setText(password)

    # Decode and extract
    window.decode_and_extract(b64_file, b64_data)

    # Check extraction results
    extracted_dir = tmp_path / "test.zip"
    assert extracted_dir.exists()
    assert (extracted_dir / "test.txt").exists()
    assert (extracted_dir / "test.txt").read_text() == "Hello, World!"


def test_decode_encrypted_without_password(tmp_path):
    """Test that encrypted files require password."""
    window = DragDropZipBase64Window()

    # Create encrypted data
    zip_data = b"fake zip data"
    encrypted_format = b"ENCRYPTED:" + b"1234567890123456" + b"fake_encrypted_data"
    b64_data = base64.b64encode(encrypted_format)

    b64_file = tmp_path / "test.zip.b64"
    b64_file.write_bytes(b64_data)

    # Try to decode without enabling encryption
    with pytest.raises(ValueError, match="appears to be encrypted"):
        window.decode_and_extract(b64_file, b64_data)
