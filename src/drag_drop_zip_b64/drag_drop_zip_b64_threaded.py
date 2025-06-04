"""
Drag & Drop tool for ZIP compression and Base64 encoding/decoding with optional encryption.

This module provides a PyQt5 GUI that accepts drag-and-drop operations for files
and folders, automatically detecting Base64 content for decoding or compressing
non-Base64 content into ZIP+Base64 format with optional AES encryption.
"""
import base64
import io
import logging
import os
import sys
import zipfile
from pathlib import Path
from typing import Optional, Tuple

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
    QCheckBox,
    QLineEdit,
    QGroupBox,
    QPushButton,
)

# Module-level logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ProcessWorker(QThread):
    """Worker thread to process a single file/folder path so the UI remains responsive."""

    finished = pyqtSignal(str)
    error = pyqtSignal(str, str)

    def __init__(self, path: Path, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.path: Path = path

    def run(self) -> None:
        """Executes the file/folder processing on a background thread."""
        try:
            parent = self.parent()
            if isinstance(parent, DragDropZipBase64Window):
                parent.process_path(self.path)
            self.finished.emit(str(self.path))
        except (OSError, RuntimeError, zipfile.BadZipFile, ValueError) as e:
            logger.exception("Error processing %s", self.path)
            self.error.emit(str(self.path), str(e))
        except Exception as e:
            logger.exception("Unexpected error processing %s", self.path)
            self.error.emit(str(self.path), f"Unexpected error: {str(e)}")


class DragDropZipBase64Window(QWidget):
    """
    A PyQt5 window that allows drag-and-drop for files or folders with optional encryption.

    Features:
    - Detects Base64 content and decodes to ZIP + extracts
    - Compresses non-Base64 content to ZIP + Base64 encodes
    - Optional AES encryption/decryption with password protection
    - Secure ZIP extraction with path traversal protection
    """

    def __init__(self) -> None:
        super().__init__()
        self.init_ui()

    def init_ui(self) -> None:
        """Sets up the window UI with encryption options."""
        self.setWindowTitle(
            'Drag & Drop Ultra Compress & Base64 with Encryption')
        self.setAcceptDrops(True)

        main_layout = QVBoxLayout()

        # Main instruction label
        self.label = QLabel(
            'Drag and drop files or folders here.\n'
            '• If it is not Base64, it will be compressed into a .zip and then encoded as .b64.\n'
            '• If it is already Base64 (and ends with .b64), it will be decoded back to a .zip'
            ' and extracted.\n'
            '• Enable encryption below for password protection.'
        )
        self.label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.label)

        # Encryption options group
        encryption_group = QGroupBox("Encryption Options")
        encryption_layout = QVBoxLayout()

        # Enable encryption checkbox
        self.encryption_enabled = QCheckBox("Enable AES Encryption")
        self.encryption_enabled.toggled.connect(self.toggle_encryption)
        encryption_layout.addWidget(self.encryption_enabled)

        # Password input
        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel("Password:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Enter encryption password")
        self.password_input.setEnabled(False)
        password_layout.addWidget(self.password_input)

        # Show/Hide password button
        self.show_password_btn = QPushButton("Show")
        self.show_password_btn.setEnabled(False)
        self.show_password_btn.clicked.connect(self.toggle_password_visibility)
        password_layout.addWidget(self.show_password_btn)

        encryption_layout.addLayout(password_layout)

        # Encryption status label
        self.encryption_status = QLabel("Encryption: Disabled")
        self.encryption_status.setStyleSheet("color: red; font-weight: bold;")
        encryption_layout.addWidget(self.encryption_status)

        encryption_group.setLayout(encryption_layout)
        main_layout.addWidget(encryption_group)

        self.setLayout(main_layout)
        self.resize(700, 400)

    def toggle_encryption(self, enabled: bool) -> None:
        """Enable/disable encryption controls based on checkbox state."""
        self.password_input.setEnabled(enabled)
        self.show_password_btn.setEnabled(enabled)

        if enabled:
            self.encryption_status.setText("Encryption: Enabled")
            self.encryption_status.setStyleSheet(
                "color: green; font-weight: bold;")
        else:
            self.encryption_status.setText("Encryption: Disabled")
            self.encryption_status.setStyleSheet(
                "color: red; font-weight: bold;")
            self.password_input.clear()

    def toggle_password_visibility(self) -> None:
        """Toggle password field visibility."""
        if self.password_input.echoMode() == QLineEdit.Password:
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.show_password_btn.setText("Hide")
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.show_password_btn.setText("Show")

    def get_encryption_key(self, password: str, salt: bytes) -> bytes:
        """
        Derive an encryption key from password and salt using PBKDF2.

        Args:
            password: User-provided password
            salt: Random salt bytes

        Returns:
            32-byte encryption key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    def encrypt_data(self, data: bytes, password: str) -> Tuple[bytes, bytes]:
        """
        Encrypt data using AES encryption with password-derived key.

        Args:
            data: Data to encrypt
            password: Encryption password

        Returns:
            Tuple of (encrypted_data, salt)
        """
        # Generate random salt
        salt = os.urandom(16)

        # Derive key from password
        key = self.get_encryption_key(password, salt)

        # Encrypt data
        fernet = Fernet(key)
        encrypted_data = fernet.encrypt(data)

        return encrypted_data, salt

    def decrypt_data(self, encrypted_data: bytes, salt: bytes, password: str) -> bytes:
        """
        Decrypt data using AES decryption with password-derived key.

        Args:
            encrypted_data: Data to decrypt
            salt: Salt used during encryption
            password: Decryption password

        Returns:
            Decrypted data

        Raises:
            ValueError: If password is incorrect or data is corrupted
        """
        # Derive same key from password and salt
        key = self.get_encryption_key(password, salt)

        # Decrypt data
        fernet = Fernet(key)
        try:
            return fernet.decrypt(encrypted_data)
        except Exception as e:
            raise ValueError(
                f"Decryption failed - incorrect password or corrupted data: {e}") from e

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accepts the drag if it contains URLs (files/folders)."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        """
        Called when the user drops files/folders onto the widget.
        Each path is handed off to a background worker (QThread).
        """
        # Validate encryption settings
        if self.encryption_enabled.isChecked():
            password = self.password_input.text().strip()
            if not password:
                QMessageBox.warning(
                    self,
                    "Password Required",
                    "Please enter a password when encryption is enabled."
                )
                return

        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            worker = ProcessWorker(path, parent=self)
            worker.finished.connect(self.on_finished)
            worker.error.connect(self.on_error)
            worker.start()

    def on_finished(self, path_str: str) -> None:
        """Logs completion of processing for a given path."""
        logger.info("Finished processing %s", path_str)

    def on_error(self, path_str: str, err: str) -> None:
        """Shows a detailed error message if processing fails."""
        logger.error("Failed to process %s: %s", path_str, err)

        # Show error dialog with details button
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("Processing Error")
        msg.setText(f"Failed to process: {Path(path_str).name}")
        msg.setDetailedText(f"Path: {path_str}\nError: {err}")
        msg.exec_()

    def process_path(self, path: Path) -> None:
        """
        Public API: Determines if 'path' is Base64 or not.

        If not Base64, compress and encode (with optional encryption).
        If Base64, decode and extract the resulting ZIP (with optional decryption).

        Args:
            path: File or directory path to process

        Raises:
            OSError: If file operations fail
            RuntimeError: If ZIP extraction encounters security issues
            zipfile.BadZipFile: If ZIP file is corrupted
            ValueError: If encryption/decryption fails
        """
        if not path.exists():
            raise OSError(f"Path does not exist: {path}")

        # If it's a directory, skip base64 check and zip+encode
        if path.is_dir():
            logger.info(
                "Detected a directory, skipping Base64 check -> Zipping and encoding: %s", path
            )
            self.zip_and_encode(path)
            return

        # It's a file, so we can safely read bytes
        try:
            data: bytes = path.read_bytes()
        except OSError as e:
            raise OSError(f"Cannot read file {path}: {e}") from e

        if self.is_base64_data(data):
            self.decode_and_extract(path, data)
        else:
            self.zip_and_encode(path)

    def is_base64_data(self, data: bytes) -> bool:
        """
        Checks if 'data' is valid Base64 by trying a full decode + re-encode comparison.

        Args:
            data: Bytes to validate

        Returns:
            True if the data is valid Base64, otherwise False.
        """
        try:
            decoded: bytes = base64.b64decode(data, validate=True)
            return base64.b64encode(decoded).strip() == data.strip()
        except Exception:
            return False

    def decode_and_extract(self, path: Path, b64data: bytes) -> None:
        """
        Decodes Base64 data to a ZIP file, then extracts that ZIP.
        Handles both encrypted and non-encrypted data.

        Args:
            path: Original file path
            b64data: Base64 encoded data to decode

        Raises:
            OSError: If file write operations fail
            zipfile.BadZipFile: If decoded data is not a valid ZIP
            RuntimeError: If ZIP contains unsafe paths
            ValueError: If decryption fails
        """
        try:
            decoded_data: bytes = base64.b64decode(b64data)
        except Exception as e:
            raise RuntimeError(f"Invalid Base64 data: {e}") from e

        # Check if this is encrypted data (starts with our encryption marker)
        if decoded_data.startswith(b"ENCRYPTED:"):
            if not self.encryption_enabled.isChecked():
                raise ValueError(
                    "This file appears to be encrypted, but encryption is not enabled. "
                    "Please enable encryption and enter the correct password."
                )

            password = self.password_input.text().strip()
            if not password:
                raise ValueError("Password required for encrypted file")

            # Extract salt and encrypted data
            try:
                # Format: b"ENCRYPTED:" + 16-byte salt + encrypted_data
                salt = decoded_data[10:26]  # bytes 10-25 (16 bytes)
                # rest is encrypted data
                encrypted_zip_data = decoded_data[26:]

                # Decrypt the ZIP data
                zip_data = self.decrypt_data(
                    encrypted_zip_data, salt, password)
                logger.info("Successfully decrypted file")

            except Exception as e:
                raise ValueError(f"Decryption failed: {e}") from e
        else:
            # Not encrypted, use as-is
            zip_data = decoded_data

        # Decide on output ZIP path
        if path.suffix == '.b64':
            zip_path: Path = path.with_suffix('')
        else:
            zip_path = path.with_name(path.name + '_decoded.zip')

        # Write the decoded ZIP file
        try:
            zip_path.write_bytes(zip_data)
            logger.info("Decoded ZIP written to: %s", zip_path)
        except OSError as e:
            raise OSError(f"Cannot write ZIP file {zip_path}: {e}") from e

        # Extract the ZIP
        self.extract_zip(zip_path)

    def extract_zip(self, zip_path: Path) -> None:
        """
        Extracts the ZIP to a folder with security checks.

        Args:
            zip_path: Path to ZIP file to extract

        Raises:
            zipfile.BadZipFile: If ZIP file is corrupted
            RuntimeError: If ZIP contains paths that would escape extraction directory
            OSError: If extraction fails
        """
        extract_folder: Path = zip_path.with_suffix('')
        if extract_folder.exists():
            extract_folder = extract_folder.with_name(
                extract_folder.name + '_extracted')

        try:
            with zipfile.ZipFile(str(zip_path), 'r') as zf:
                # Security check against Zip Slip attacks
                for member in zf.namelist():
                    dest = (extract_folder / member).resolve()
                    if not str(dest).startswith(str(extract_folder.resolve()) + os.sep):
                        raise RuntimeError(
                            f"Unsafe path in ZIP file: {member}")

                zf.extractall(str(extract_folder))

        except zipfile.BadZipFile as e:
            raise zipfile.BadZipFile(f"Corrupted ZIP file {zip_path}: {e}")
        except OSError as e:
            raise OSError(f"Failed to extract {zip_path}: {e}") from e

        logger.info("Extracted to folder: %s", extract_folder)

    def zip_and_encode(self, path: Path) -> None:
        """
        Compresses the given file/folder into an in-memory ZIP,
        optionally encrypts it, then Base64-encodes it and writes out '<path>.zip.b64'.

        Args:
            path: File or directory to compress and encode

        Raises:
            OSError: If file operations fail
            RuntimeError: If compression fails
            ValueError: If encryption fails
        """
        try:
            zip_data: bytes = self.compress_to_zip(path)

            # Encrypt if enabled
            if self.encryption_enabled.isChecked():
                password = self.password_input.text().strip()
                if not password:
                    raise ValueError(
                        "Password required when encryption is enabled")

                encrypted_data, salt = self.encrypt_data(zip_data, password)

                # Prepend encryption marker and salt
                # Format: b"ENCRYPTED:" + 16-byte salt + encrypted_data
                final_data = b"ENCRYPTED:" + salt + encrypted_data
                logger.info("Successfully encrypted data")
            else:
                final_data = zip_data

            # Base64 encode the final data
            b64data: bytes = base64.b64encode(final_data)

            # Determine output filename
            if self.encryption_enabled.isChecked():
                output_path: Path = path.with_suffix(
                    path.suffix + '.encrypted.zip.b64')
            else:
                output_path: Path = path.with_suffix(path.suffix + '.zip.b64')

            output_path.write_bytes(b64data)

            logger.info("Zipped and encoded -> %s", output_path)

        except OSError as e:
            raise OSError(f"Failed to create encoded file: {e}") from e

    def compress_to_zip(self, path: Path) -> bytes:
        """
        Returns the compressed (zipped) data of a file/folder in memory.

        Args:
            path: File or directory to compress

        Returns:
            Compressed ZIP data as bytes

        Raises:
            OSError: If file access fails during compression
            RuntimeError: If compression fails
        """
        buffer: io.BytesIO = io.BytesIO()

        # Use modern compression level if available (Python 3.7+)
        params = {
            'mode': 'w',
            'compression': zipfile.ZIP_DEFLATED
        }
        if sys.version_info >= (3, 7):
            params['compresslevel'] = 9

        try:
            with zipfile.ZipFile(buffer, **params) as zf:
                if path.is_file():
                    zf.write(str(path), arcname=path.name)
                else:
                    for root, dirs, files in os.walk(str(path)):
                        for file in files:
                            full_path = Path(root) / file
                            arcname = full_path.relative_to(path)
                            zf.write(str(full_path), arcname=str(arcname))

        except OSError as e:
            raise OSError(f"Failed to read files for compression: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Compression failed: {e}") from e

        return buffer.getvalue()
