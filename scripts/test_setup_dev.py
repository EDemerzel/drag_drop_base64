"""
Unit tests for the DragDropZipBase64Window class and related functionality.

This module contains tests for encryption, compression, Base64 encoding/decoding,
and drag-and-drop functionality provided by the DragDropZipBase64Window class.
"""

import base64
import zipfile
from io import BytesIO
import pytest
from drag_drop_zip_b64.drag_drop_zip_b64_threaded import DragDropZipBase64Window
from drag_drop_zip_b64.window import create_window


@pytest.fixture
def window(tmp_path, monkeypatch) -> DragDropZipBase64Window:
    """
    Fixture to create a DragDropZipBase64Window instance for testing.

    Args:
        tmp_path: Temporary directory for file outputs.
        monkeypatch: Pytest utility to modify environment or behavior.

    Returns:
        DragDropZipBase64Window: A new instance of the window class.
    """
    # Ensure working dir is tmp_path for file outputs
    monkeypatch.chdir(tmp_path)
    return DragDropZipBase64Window()


def test_get_encryption_key_consistency(drag_drop_window: DragDropZipBase64Window) -> None:
    """
    Test that encryption keys derived from the same password and salt are consistent.

    Args:
        window: The DragDropZipBase64Window instance.
    """
    salt = b"0" * 16
    k1 = drag_drop_window.get_encryption_key("password", salt)
    k2 = drag_drop_window.get_encryption_key("password", salt)
    assert k1 == k2
    # different salt => different key
    k3 = drag_drop_window.get_encryption_key("password", b"1" * 16)
    assert k1 != k3


def test_encrypt_decrypt_roundtrip(drag_drop_window: DragDropZipBase64Window) -> None:
    """
    Test that data encrypted with a password can be successfully decrypted.

    Args:
        drag_drop_window: The DragDropZipBase64Window instance.
    """
    data = b"Secret data"
    password = "testpass"
    encrypted, salt = drag_drop_window.encrypt_data(data, password)
    assert encrypted != data
    decrypted = drag_drop_window.decrypt_data(encrypted, salt, password)
    assert decrypted == data
    # wrong password raises
    with pytest.raises(ValueError):
        drag_drop_window.decrypt_data(encrypted, salt, "wrongpass")


def test_is_base64_data_true_false(drag_drop_window: DragDropZipBase64Window) -> None:
    """
    Test the is_base64_data method for valid and invalid Base64 data.

    Args:
        window: The DragDropZipBase64Window instance.
    """
    raw = b"hello world"
    b64 = base64.b64encode(raw)
    assert drag_drop_window.is_base64_data(b64)
    assert not drag_drop_window.is_base64_data(b"not_base64$$")


def test_compress_to_zip_file_and_folder(
        tmp_path,
        drag_drop_window: DragDropZipBase64Window) -> None:
    """
    Test compressing a file and a folder into ZIP format.

    Args:
        tmp_path: Temporary directory for file outputs.
        drag_drop_window: The DragDropZipBase64Window instance.
    """
    # file
    f = tmp_path / "a.txt"
    f.write_text("foo")
    zip_data = drag_drop_window.compress_to_zip(f)
    with zipfile.ZipFile(BytesIO(zip_data), "r") as zf:
        assert "a.txt" in zf.namelist()
        assert zf.read("a.txt") == b"foo"

    # folder
    d = tmp_path / "dir"
    d.mkdir()
    (d / "b.txt").write_text("bar")
    zip_data2 = drag_drop_window.compress_to_zip(d)
    with zipfile.ZipFile(BytesIO(zip_data2), "r") as zf:
        assert "b.txt" in zf.namelist()
        assert zf.read("b.txt") == b"bar"


def test_zip_and_encode_and_decode_without_encryption(
        tmp_path,
        drag_drop_window: DragDropZipBase64Window) -> None:
    """
    Test the zip_and_encode and decode_and_extract methods without encryption.

    Args:
        tmp_path: Temporary directory for file outputs.
        drag_drop_window: The DragDropZipBase64Window instance.
    """
    f = tmp_path / "file.txt"
    f.write_text("data")
    # zip+encode
    drag_drop_window.zip_and_encode(f)
    out = tmp_path / "file.txt.zip.b64"
    assert out.exists()
    b64 = out.read_bytes()
    # decode+extract
    drag_drop_window.decode_and_extract(out, b64)
    # extracted folder
    extracted = tmp_path / "file.txt.zip"
    assert extracted.exists()
    assert (extracted / "file.txt").read_text() == "data"


def test_zip_and_encode_and_decode_with_encryption(
        tmp_path,
        drag_drop_window: DragDropZipBase64Window) -> None:
    """
    Test the zip_and_encode and decode_and_extract methods with encryption enabled.

    Args:
        tmp_path: Temporary directory for file outputs.
        drag_drop_window: The DragDropZipBase64Window instance.
    """
    f = tmp_path / "secret.txt"
    f.write_text("topsecret")
    # enable encryption
    drag_drop_window.encryption_enabled.setChecked(True)
    drag_drop_window.toggle_encryption(True)
    drag_drop_window.password_input.setText("mypwd")

    drag_drop_window.zip_and_encode(f)
    out = tmp_path / "secret.txt.encrypted.zip.b64"
    assert out.exists()

    b64 = out.read_bytes()
    raw = base64.b64decode(b64)
    assert raw.startswith(b"ENCRYPTED:")

    # decode+extract
    drag_drop_window.decode_and_extract(out, b64)
    extracted = tmp_path / "secret.txt.encrypted.zip"
    assert extracted.exists()
    folder = tmp_path / "secret.txt.encrypted"
    assert (folder / "secret.txt").read_text() == "topsecret"


def test_create_window_importable() -> None:
    """
    Test that the create_window function returns a valid DragDropZipBase64Window instance.
    """
    w = create_window()
    assert isinstance(w, DragDropZipBase64Window)


def test_large_file_compression(tmp_path, drag_drop_window: DragDropZipBase64Window) -> None:
    """
    Test compressing and encoding a relatively large file.

    Args:
        tmp_path: Temporary directory for file outputs.
        drag_drop_window: The DragDropZipBase64Window instance.
    """
    large_file = tmp_path / "bigfile.txt"
    large_file.write_text("A" * 2_000_000)  # ~2MB text
    drag_drop_window.zip_and_encode(large_file)
    out = tmp_path / "bigfile.txt.zip.b64"
    assert out.exists(), "Output for large file was not created properly"


def test_empty_folder_compression(tmp_path, drag_drop_window: DragDropZipBase64Window) -> None:
    """
    Test compressing and encoding an empty folder.

    Args:
        tmp_path: Temporary directory for file outputs.
        drag_drop_window: The DragDropZipBase64Window instance.
    """
    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir()
    drag_drop_window.zip_and_encode(empty_dir)
    out = tmp_path / "empty_dir.zip.b64"
    assert out.exists(), "Output for empty folder was not created properly"
    # decode+extract
    b64 = out.read_bytes()
    drag_drop_window.decode_and_extract(out, b64)
    extracted = tmp_path / "empty_dir.zip"
    assert extracted.exists(), "Empty folder zip was not extracted"


def test_invalid_base64_input(tmp_path, drag_drop_window: DragDropZipBase64Window) -> None:
    """
    Test decoding and extracting invalid Base64 data.

    Args:
        tmp_path: Temporary directory for file outputs.
        drag_drop_window: The DragDropZipBase64Window instance.
    """
    # write a bogus .b64 file
    out = tmp_path / "invalid.zip.b64"
    out.write_text("ThisIsNotBase64!!@@##")
    # attempt decode+extract
    b64 = out.read_bytes()
    # Expecting an error message but no crash
    drag_drop_window.decode_and_extract(out, b64)
    # There's no assertion needed; we just ensure it doesn't raise an unhandled exception.
