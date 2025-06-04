"""
Drag & Drop tool for ZIP compression and Base64 encoding/decoding.

This module provides a PyQt5 GUI that accepts drag-and-drop operations for files
and folders, automatically detecting Base64 content for decoding or compressing
non-Base64 content into ZIP+Base64 format.
"""
import base64
import io
import logging
import os
import sys
import zipfile
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QVBoxLayout,
    QMessageBox,
    QDragEnterEvent,
    QDropEvent,
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
        except (OSError, RuntimeError, zipfile.BadZipFile) as e:
            logger.exception("Error processing %s", self.path)
            self.error.emit(str(self.path), str(e))
        except Exception as e:
            logger.exception("Unexpected error processing %s", self.path)
            self.error.emit(str(self.path), f"Unexpected error: {str(e)}")


class DragDropZipBase64Window(QWidget):
    """
    A PyQt5 window that allows drag-and-drop for files or folders.

    Features:
    - Detects Base64 content and decodes to ZIP + extracts
    - Compresses non-Base64 content to ZIP + Base64 encodes
    - Secure ZIP extraction with path traversal protection
    """

    def __init__(self) -> None:
        super().__init__()
        self.init_ui()

    def init_ui(self) -> None:
        """Sets up the window UI."""
        self.setWindowTitle('Drag & Drop Ultra Compress & Base64')
        self.setAcceptDrops(True)

        layout: QVBoxLayout = QVBoxLayout()
        self.label: QLabel = QLabel(
            'Drag and drop files or folders here.\n'
            '• If it is not Base64, it will be compressed into a .zip and then encoded as .b64.\n'
            '• If it is already Base64 (and ends with .b64), it will be decoded back to a .zip'
            ' and extracted.'
        )
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        self.setLayout(layout)
        self.resize(600, 300)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accepts the drag if it contains URLs (files/folders)."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        """
        Called when the user drops files/folders onto the widget.
        Each path is handed off to a background worker (QThread).
        """
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

        If not Base64, compress and encode.
        If Base64, decode and extract the resulting ZIP.

        Args:
            path: File or directory path to process

        Raises:
            OSError: If file operations fail
            RuntimeError: If ZIP extraction encounters security issues
            zipfile.BadZipFile: If ZIP file is corrupted
        """
        if not path.exists():
            raise OSError(f"Path does not exist: {path}")

        # If it's a directory, skip base64 check and zip+encode
        if path.is_dir():
            logger.info(
                "Detected a directory, skipping Base64 check -> Zipping and encoding: %s", path)
            self.zip_and_encode(path)
            return

        # It's a file, so we can safely read bytes
        try:
            data: bytes = path.read_bytes()
        except OSError as e:
            raise OSError(f"Cannot read file {path}: {e}")

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

        Args:
            path: Original file path
            b64data: Base64 encoded data to decode

        Raises:
            OSError: If file write operations fail
            zipfile.BadZipFile: If decoded data is not a valid ZIP
            RuntimeError: If ZIP contains unsafe paths
        """
        try:
            zip_data: bytes = base64.b64decode(b64data)
        except Exception as e:
            raise RuntimeError(f"Invalid Base64 data: {e}")

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
            raise OSError(f"Cannot write ZIP file {zip_path}: {e}")

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
            raise OSError(f"Failed to extract {zip_path}: {e}")

        logger.info("Extracted to folder: %s", extract_folder)

    def zip_and_encode(self, path: Path) -> None:
        """
        Compresses the given file/folder into an in-memory ZIP,
        then Base64-encodes it and writes out '<path>.zip.b64'.

        Args:
            path: File or directory to compress and encode

        Raises:
            OSError: If file operations fail
            RuntimeError: If compression fails
        """
        try:
            zip_data: bytes = self.compress_to_zip(path)
            b64data: bytes = base64.b64encode(zip_data)

            output_path: Path = path.with_suffix(path.suffix + '.zip.b64')
            output_path.write_bytes(b64data)

            logger.info("Zipped and encoded -> %s", output_path)

        except OSError as e:
            raise OSError(f"Failed to create encoded file: {e}")

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
            raise OSError(f"Failed to read files for compression: {e}")
        except Exception as e:
            raise RuntimeError(f"Compression failed: {e}")

        return buffer.getvalue()
