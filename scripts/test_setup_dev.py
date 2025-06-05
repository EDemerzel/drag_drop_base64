import base64
import zipfile
from io import BytesIO
import pytest
from drag_drop_zip_b64.drag_drop_zip_b64_threaded import DragDropZipBase64Window
from drag_drop_zip_b64.window import create_window


@pytest.fixture
def window(tmp_path, monkeypatch) -> DragDropZipBase64Window:
    # Ensure working dir is tmp_path for file outputs
    monkeypatch.chdir(tmp_path)
    return DragDropZipBase64Window()


def test_get_encryption_key_consistency(window: DragDropZipBase64Window) -> None:
    salt = b"0" * 16
    k1 = window.get_encryption_key("password", salt)
    k2 = window.get_encryption_key("password", salt)
    assert k1 == k2
    # different salt => different key
    k3 = window.get_encryption_key("password", b"1" * 16)
    assert k1 != k3


def test_encrypt_decrypt_roundtrip(window: DragDropZipBase64Window) -> None:
    data = b"Secret data"
    password = "testpass"
    encrypted, salt = window.encrypt_data(data, password)
    assert encrypted != data
    decrypted = window.decrypt_data(encrypted, salt, password)
    assert decrypted == data
    # wrong password raises
    with pytest.raises(ValueError):
        window.decrypt_data(encrypted, salt, "wrongpass")


def test_is_base64_data_true_false(window: DragDropZipBase64Window) -> None:
    raw = b"hello world"
    b64 = base64.b64encode(raw)
    assert window.is_base64_data(b64)
    assert not window.is_base64_data(b"not_base64$$")


def test_compress_to_zip_file_and_folder(tmp_path, window: DragDropZipBase64Window) -> None:
    # file
    f = tmp_path / "a.txt"
    f.write_text("foo")
    zip_data = window.compress_to_zip(f)
    with zipfile.ZipFile(BytesIO(zip_data), "r") as zf:
        assert "a.txt" in zf.namelist()
        assert zf.read("a.txt") == b"foo"

    # folder
    d = tmp_path / "dir"
    d.mkdir()
    (d / "b.txt").write_text("bar")
    zip_data2 = window.compress_to_zip(d)
    with zipfile.ZipFile(BytesIO(zip_data2), "r") as zf:
        assert "b.txt" in zf.namelist()
        assert zf.read("b.txt") == b"bar"


def test_zip_and_encode_and_decode_without_encryption(
        tmp_path,
        window: DragDropZipBase64Window) -> None:
    f = tmp_path / "file.txt"
    f.write_text("data")
    # zip+encode
    window.zip_and_encode(f)
    out = tmp_path / "file.txt.zip.b64"
    assert out.exists()
    b64 = out.read_bytes()
    # decode+extract
    window.decode_and_extract(out, b64)
    # extracted folder
    extracted = tmp_path / "file.txt.zip"
    assert extracted.exists()
    assert (extracted / "file.txt").read_text() == "data"


def test_zip_and_encode_and_decode_with_encryption(
        tmp_path,
        window: DragDropZipBase64Window) -> None:
    f = tmp_path / "secret.txt"
    f.write_text("topsecret")
    # enable encryption
    window.encryption_enabled.setChecked(True)
    window.toggle_encryption(True)
    window.password_input.setText("mypwd")

    window.zip_and_encode(f)
    out = tmp_path / "secret.txt.encrypted.zip.b64"
    assert out.exists()

    b64 = out.read_bytes()
    raw = base64.b64decode(b64)
    assert raw.startswith(b"ENCRYPTED:")

    # decode+extract
    window.decode_and_extract(out, b64)
    extracted = tmp_path / "secret.txt.encrypted.zip"
    assert extracted.exists()
    folder = tmp_path / "secret.txt.encrypted"
    assert (folder / "secret.txt").read_text() == "topsecret"


def test_create_window_importable() -> None:
    w = create_window()
    assert isinstance(w, DragDropZipBase64Window)


# New edge-case tests for large files, empty folders, or invalid base64 input

def test_large_file_compression(tmp_path, window: DragDropZipBase64Window) -> None:
    """
    Test compressing and encoding a relatively large file.
    (Here, we simulate large content by repeating a string many times.)
    """
    large_file = tmp_path / "bigfile.txt"
    large_file.write_text("A" * 2_000_000)  # ~2MB text
    window.zip_and_encode(large_file)
    out = tmp_path / "bigfile.txt.zip.b64"
    assert out.exists(), "Output for large file was not created properly"


def test_empty_folder_compression(tmp_path, window: DragDropZipBase64Window) -> None:
    """
    Test compressing and encoding an empty folder.
    """
    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir()
    window.zip_and_encode(empty_dir)
    out = tmp_path / "empty_dir.zip.b64"
    assert out.exists(), "Output for empty folder was not created properly"
    # decode+extract
    b64 = out.read_bytes()
    window.decode_and_extract(out, b64)
    extracted = tmp_path / "empty_dir.zip"
    assert extracted.exists(), "Empty folder zip was not extracted"


def test_invalid_base64_input(tmp_path, window: DragDropZipBase64Window) -> None:
    """
    Test decoding and extracting invalid base64 data.
    The code should handle it gracefully (not crash).
    """
    # write a bogus .b64 file
    out = tmp_path / "invalid.zip.b64"
    out.write_text("ThisIsNotBase64!!@@##")
    # attempt decode+extract
    b64 = out.read_bytes()
    # Expecting an error message but no crash
    window.decode_and_extract(out, b64)
    # There's no assertion needed; we just ensure it doesn't raise an unhandled exception.
