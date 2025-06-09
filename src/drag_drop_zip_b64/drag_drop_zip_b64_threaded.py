"""
Drag & Drop tool for ZIP compression and Base64 encoding/decoding with optional
encryption and secure network features.

This module provides a PyQt5 GUI that accepts drag-and-drop operations for files
and folders, automatically detecting Base64 content for decoding or compressing
non-Base64 content into ZIP+Base64 format with optional AES encryption and
secure upload capabilities.
"""

import base64
import io
import logging
import os
import ssl
import sys
import zipfile
from pathlib import Path
from typing import Optional, Tuple

import requests
import urllib3
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
from PyQt5.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Module-level logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Disable SSL warnings for self-signed certificates (if needed)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SecureHTTPAdapter(HTTPAdapter):
    """Custom HTTP adapter with enhanced SSL/TLS security."""

    def __init__(self, ssl_context=None, **kwargs) -> None:
        self.ssl_context = ssl_context
        super().__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs) -> None:
        kwargs["ssl_context"] = self.ssl_context or self._create_secure_ssl_context()
        return super().init_poolmanager(*args, **kwargs)

    def _create_secure_ssl_context(self) -> ssl.SSLContext:
        """Create a secure SSL context with modern settings."""
        context = ssl.create_default_context()

        # Enhanced security settings
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.maximum_version = ssl.TLSVersion.TLSv1_3

        # Disable weak cipher suites
        context.set_ciphers(
            "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS")

        # Enhanced verification
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED

        return context


class NetworkWorker(QThread):
    """
    Worker thread for secure network operations with progress tracking.

    This class handles file uploads to remote servers using HTTPS with SSL/TLS verification.
    It provides real-time progress tracking through a custom file wrapper that monitors
    bytes read during the upload process.

    Features:
    - Secure HTTPS uploads with SSL/TLS verification
    - Real-time progress tracking via Qt signals
    - Automatic retry logic for failed connections
    - Custom SSL adapter with enhanced security settings
    - Proper file handling with context managers

    Attributes:
        progress (pyqtSignal): Emits upload progress percentage (0-100)
        finished (pyqtSignal): Emits success message when upload completes
        error (pyqtSignal): Emits error message if upload fails

    Args:
        file_path (Path): Path to the file to upload
        url (str): Target URL for file upload (should be HTTPS)
        ssl_verify (bool, optional): Whether to verify SSL certificates. Defaults to True.
        parent (QObject, optional): Parent Qt object. Defaults to None.

    Example:
        >>> worker = NetworkWorker(Path("file.zip"), "https://example.com/upload")
        >>> worker.progress.connect(progress_bar.setValue)
        >>> worker.finished.connect(lambda msg: print(f"Success: {msg}"))
        >>> worker.error.connect(lambda err: print(f"Error: {err}"))
        >>> worker.start()

    Note:
        This worker should be used in a Qt application context as it emits Qt signals
        for progress tracking and status updates. The upload uses a custom file wrapper
        that implements the file-like interface required by the requests library while
        providing progress callbacks.

    Security:
        - Uses TLS 1.2+ with secure cipher suites
        - Validates SSL certificates by default
        - Includes retry logic for network resilience
        - Sets appropriate security headers
    """

    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, file_path: Path, url: str, ssl_verify: bool = True, parent=None) -> None:
        """
        Initialize the NetworkWorker for secure file uploads.

        Args:
            file_path (Path): Path to the file to upload
            url (str): Target URL for file upload (preferably HTTPS)
            ssl_verify (bool, optional): Enable SSL certificate verification. Defaults to True.
            parent (QObject, optional): Parent Qt object for memory management. Defaults to None.
        """
        super().__init__(parent)
        self.file_path = file_path
        self.url = url
        self.ssl_verify = ssl_verify

    def run(self) -> None:
        """
        Execute the file upload operation on a background thread.

        This method performs the actual file upload with progress tracking.
        It creates a secure session, configures retry logic, and uses a custom
        file wrapper to provide real-time progress updates.

        The upload process:
        1. Creates a secure HTTP session with retry logic
        2. Wraps the file with a progress-tracking wrapper
        3. Uploads the file using multipart form data
        4. Emits progress signals during upload
        5. Emits success or error signals upon completion

        Signals Emitted:
            - progress(int): Upload progress percentage (0-100)
            - finished(str): Success message with HTTP status code
            - error(str): Error message if upload fails

        Raises:
            No exceptions are raised directly; all errors are caught and
            emitted via the error signal for proper Qt error handling.
        """
        try:
            # Create secure session
            session = requests.Session()

            # Configure retries
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )

            # Mount secure adapter
            adapter = SecureHTTPAdapter(max_retries=retry_strategy)
            session.mount("https://", adapter)
            session.mount("http://", adapter)

            # Get file size for progress tracking
            file_size = self.file_path.stat().st_size

            # Create a custom file-like object with progress tracking
            class ProgressFileWrapper:
                """
                File-like wrapper that provides progress tracking for file uploads.

                This class wraps a file object and provides progress callbacks during
                read operations, making it compatible with the requests library's
                file upload interface while enabling real-time progress tracking.

                The wrapper implements the necessary file-like interface methods
                (read, seek, tell) required by requests for file uploads, while
                intercepting read operations to track bytes transferred.

                Attributes:
                    file_path (Path): Path to the file being wrapped
                    progress_callback (callable): Function to call with progress updates
                    file_size (int): Total size of the file in bytes
                    bytes_read (int): Number of bytes read so far

                Args:
                    file_path (Path): Path to the file to wrap
                    progress_callback (callable): Function that accepts progress percentage (0-100)

                Example:
                    >>> def progress_handler(percent):
                    ...     print(f"Upload progress: {percent}%")
                    >>>
                    >>> with ProgressFileWrapper(Path("file.txt"), progress_handler) as wrapper:
                    ...     # Use wrapper with requests or other file upload mechanisms
                    ...     requests.post(url, files={'file': ('file.txt', wrapper, 'text/plain')})

                Note:
                    This class is designed to be used as a context manager to ensure
                    proper file resource cleanup. It maintains compatibility with the
                    requests library's expected file-like interface.
                """

                def __init__(self, file_path: Path, progress_callback) -> None:
                    self.file_path = file_path
                    self.progress_callback = progress_callback
                    self.file_size = file_path.stat().st_size
                    self._file = None
                    self.bytes_read = 0

                def __enter__(self) -> "ProgressFileWrapper":
                    self._file = open(self.file_path, "rb")
                    return self

                def __exit__(self, exc_type, exc_val, exc_tb) -> None:
                    if self._file:
                        self._file.close()

                def read(self, size: int = -1) -> bytes:
                    """
                    Read data from the file and update progress.

                    Args:
                        size (int, optional): Number of bytes to read. Defaults to -1.

                    Returns:
                        bytes: Data read from the file.
                    """
                    if self._file is None:
                        return b""

                    data = self._file.read(size)
                    if data:
                        self.bytes_read += len(data)
                        if self.file_size > 0:
                            progress_percent = int(
                                (self.bytes_read / self.file_size) * 100
                            )
                            self.progress_callback(progress_percent)
                    return data

                def seek(self, offset: int, whence: int = 0) -> int:
                    """
                    Seek to a specific position in the file.

                    Args:
                        offset (int): Offset to seek to.
                        whence (int, optional): Reference point for seeking. Defaults to 0.

                    Returns:
                        int: New file position.
                    """
                    if self._file is None:
                        return 0
                    return self._file.seek(offset, whence)

                def tell(self) -> int:
                    """
                    Get the current file position.

                    Returns:
                        int: Current file position.
                    """
                    if self._file is None:
                        return 0
                    return self._file.tell()

            # Use the progress wrapper for file upload
            with ProgressFileWrapper(self.file_path, self.progress.emit) as file_wrapper:
                # Prepare files for upload - using correct format
                files = {
                    "file": (
                        self.file_path.name,  # filename
                        file_wrapper,  # file-like object
                        "application/octet-stream",  # content type
                    )
                }

                # Perform secure upload
                response = session.post(
                    self.url,
                    files=files,
                    verify=self.ssl_verify,
                    timeout=(30, 300),  # (connect, read) timeout
                    headers={
                        "User-Agent": "DragDropZipB64/1.1.0",
                        "X-Requested-With": "XMLHttpRequest",
                    },
                )

                response.raise_for_status()
                self.finished.emit(
                    f"Upload successful: {response.status_code}")

        except requests.exceptions.SSLError as e:
            logger.exception("SSL/TLS error during upload")
            self.error.emit(f"SSL/TLS error: {str(e)}")
        except requests.exceptions.ConnectionError as e:
            logger.exception("Connection error during upload")
            self.error.emit(f"Connection error: {str(e)}")
        except requests.exceptions.Timeout as e:
            logger.exception("Timeout error during upload")
            self.error.emit(f"Timeout error: {str(e)}")
        except Exception as e:
            logger.exception("Unexpected error during upload")
            self.error.emit(f"Upload failed: {str(e)}")


class ProcessWorker(QThread):
    """Worker thread to process a single file/folder path so the UI remains responsive."""

    finished = pyqtSignal(str)
    error = pyqtSignal(str, str)

    def __init__(self, path: Path, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the ProcessWorker for file/folder processing.

        Args:
            path (Path): Path to the file or folder to process.
            parent (Optional[QWidget], optional): Parent Qt widget. Defaults to None.
        """
        super().__init__(parent)
        self.path: Path = path

    def run(self) -> None:
        """
        Execute the file/folder processing on a background thread.

        This method processes the given path and emits signals upon completion or error.
        """
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
    A PyQt5 window that allows drag-and-drop for files or folders
    with optional encryption and secure network features.

    Features:
    - Detects Base64 content and decodes to ZIP + extracts.
    - Compresses non-Base64 content to ZIP + Base64 encodes.
    - Optional AES encryption/decryption with password protection.
    - Secure ZIP extraction with path traversal protection.
    - Secure HTTPS upload capabilities with SSL/TLS verification.
    """

    def __init__(self) -> None:
        """
        Initialize the DragDropZipBase64Window with UI components.
        """
        super().__init__()
        self.init_ui()
        self.network_worker = None

    def init_ui(self) -> None:
        """
        Set up the window UI with encryption and network options.
        """
        self.setWindowTitle(
            "Drag & Drop Ultra Compress & Base64 with Encryption & Secure Upload")
        self.setAcceptDrops(True)

        main_layout = QVBoxLayout()

        # Main instruction label
        self.label = QLabel(
            "Drag and drop files or folders here.\n"
            "• If it is not Base64, it will be compressed into a .zip and then encoded as .b64.\n"
            "• If it is already Base64 (and ends with .b64), it will be decoded back to a .zip"
            " and extracted.\n"
            "• Enable encryption below for password protection.\n"
            "• Enable secure upload for HTTPS file sharing."
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

        # Network upload options group
        network_group = QGroupBox("Secure Upload Options")
        network_layout = QVBoxLayout()

        # Enable upload checkbox
        self.upload_enabled = QCheckBox("Enable Secure Upload (HTTPS)")
        self.upload_enabled.toggled.connect(self.toggle_upload)
        network_layout.addWidget(self.upload_enabled)

        # Upload URL input
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("Upload URL:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com/upload")
        self.url_input.setEnabled(False)
        url_layout.addWidget(self.url_input)
        network_layout.addLayout(url_layout)

        # SSL verification checkbox
        self.ssl_verify = QCheckBox(
            "Verify SSL/TLS Certificates (Recommended)")
        self.ssl_verify.setChecked(True)
        self.ssl_verify.setEnabled(False)
        network_layout.addWidget(self.ssl_verify)

        # Upload button
        self.upload_btn = QPushButton("Upload Last Processed File")
        self.upload_btn.setEnabled(False)
        self.upload_btn.clicked.connect(self.start_upload)
        network_layout.addWidget(self.upload_btn)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        network_layout.addWidget(self.progress_bar)

        # Upload status
        self.upload_status = QLabel("Upload: Disabled")
        self.upload_status.setStyleSheet("color: red; font-weight: bold;")
        network_layout.addWidget(self.upload_status)

        network_group.setLayout(network_layout)
        main_layout.addWidget(network_group)

        # Log output
        log_group = QGroupBox("Operation Log")
        log_layout = QVBoxLayout()
        self.log_output = QTextEdit()
        self.log_output.setMaximumHeight(150)
        self.log_output.setReadOnly(True)
        log_layout.addWidget(self.log_output)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)

        self.setLayout(main_layout)
        self.resize(800, 600)

        # Track last processed file for upload
        self.last_processed_file = None

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

    def toggle_upload(self, enabled: bool) -> None:
        """Enable/disable upload controls based on checkbox state."""
        self.url_input.setEnabled(enabled)
        self.ssl_verify.setEnabled(enabled)
        self.upload_btn.setEnabled(
            enabled and self.last_processed_file is not None)

        if enabled:
            self.upload_status.setText("Upload: Enabled")
            self.upload_status.setStyleSheet(
                "color: green; font-weight: bold;")
        else:
            self.upload_status.setText("Upload: Disabled")
            self.upload_status.setStyleSheet("color: red; font-weight: bold;")

    def toggle_password_visibility(self) -> None:
        """Toggle password field visibility."""
        if self.password_input.echoMode() == QLineEdit.Password:
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.show_password_btn.setText("Hide")
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.show_password_btn.setText("Show")

    def start_upload(self) -> None:
        """Start secure file upload."""
        if not self.last_processed_file or not self.last_processed_file.exists():
            QMessageBox.warning(
                self, "No File", "No processed file available for upload.")
            return

        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "URL Required",
                                "Please enter an upload URL.")
            return

        if not url.startswith("https://") and self.ssl_verify.isChecked():
            reply = QMessageBox.question(
                self,
                "Insecure URL",
                "URL is not HTTPS. This will transmit your file unencrypted.\nContinue anyway?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.No:
                return

        # Start upload
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.upload_btn.setEnabled(False)

        self.network_worker = NetworkWorker(
            self.last_processed_file, url, self.ssl_verify.isChecked()
        )
        self.network_worker.progress.connect(self.progress_bar.setValue)
        self.network_worker.finished.connect(self.on_upload_finished)
        self.network_worker.error.connect(self.on_upload_error)
        self.network_worker.start()

    def on_upload_finished(self, message: str) -> None:
        """Handle successful upload completion."""
        self.progress_bar.setVisible(False)
        self.upload_btn.setEnabled(True)
        self.log_output.append(f"✅ {message}")
        logger.info("Upload completed: %s", message)

    def on_upload_error(self, error: str) -> None:
        """Handle upload error."""
        self.progress_bar.setVisible(False)
        self.upload_btn.setEnabled(True)
        self.log_output.append(f"❌ Upload failed: {error}")
        logger.error("Upload failed: %s", error)

        QMessageBox.critical(self, "Upload Failed", f"Upload failed:\n{error}")

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
                f"Decryption failed - incorrect password or corrupted data: {e}"
            ) from e

    # type: ignore[override]
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """
        Accepts the drag if it contains URLs (files/folders).
        """
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    # type: ignore[override]
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
                    self, "Password Required", "Please enter a password when encryption is enabled."
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
        self.log_output.append(f"✅ Processed: {Path(path_str).name}")

    def on_error(self, path_str: str, err: str) -> None:
        """Shows a detailed error message if processing fails."""
        logger.error("Failed to process %s: %s", path_str, err)
        self.log_output.append(
            f"❌ Error processing {Path(path_str).name}: {err}")

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
        if path.suffix == ".b64":
            zip_path: Path = path.with_suffix("")
        else:
            zip_path = path.with_name(path.name + "_decoded.zip")

        # Write the decoded ZIP file
        try:
            zip_path.write_bytes(zip_data)
            logger.info("Decoded ZIP written to: %s", zip_path)
            self.last_processed_file = zip_path

            # Update upload button state
            if self.upload_enabled.isChecked():
                self.upload_btn.setEnabled(True)

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
        extract_folder: Path = zip_path.with_suffix("")
        if extract_folder.exists():
            extract_folder = extract_folder.with_name(
                extract_folder.name + "_extracted")

        try:
            with zipfile.ZipFile(str(zip_path), "r") as zf:
                # Security check against Zip Slip attacks
                for member in zf.namelist():
                    dest = (extract_folder / member).resolve()
                    if not str(dest).startswith(str(extract_folder.resolve()) + os.sep):
                        raise RuntimeError(
                            f"Unsafe path in ZIP file: {member}")

                zf.extractall(str(extract_folder))

        except zipfile.BadZipFile as e:
            raise zipfile.BadZipFile(
                f"Corrupted ZIP file {zip_path}: {e}") from e
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
                    path.suffix + ".encrypted.zip.b64")
            else:
                output_path: Path = path.with_suffix(path.suffix + ".zip.b64")

            output_path.write_bytes(b64data)
            logger.info("Zipped and encoded -> %s", output_path)

            # Track for upload
            self.last_processed_file = output_path

            # Update upload button state
            if self.upload_enabled.isChecked():
                self.upload_btn.setEnabled(True)

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
        params = {"mode": "w", "compression": zipfile.ZIP_DEFLATED}
        if sys.version_info >= (3, 7):
            params["compresslevel"] = 9

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
