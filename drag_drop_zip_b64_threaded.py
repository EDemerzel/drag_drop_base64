"""
drag_drop_zip_b64_threaded_folder_fix.py
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
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QWidget,
    QVBoxLayout,
    QMessageBox,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


class ProcessWorker(QThread):
    """
    Worker thread to process a single file/folder path so the UI remains responsive.
    """
    finished = pyqtSignal(str)
    error = pyqtSignal(str, str)

    def __init__(self, path: Path, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.path: Path = path

    def run(self) -> None:
        """
        Executes the file/folder processing on a background thread.
        """
        try:
            # 'parent()' should be our main window of type DragDropZipBase64Window
            main_window = self.parent()
            if hasattr(main_window, "_process_path") and callable(main_window._process_path):
                main_window._process_path(self.path)
            self.finished.emit(str(self.path))
        except Exception as e:
            logging.exception("Error processing %s", self.path)
            self.error.emit(str(self.path), str(e))


class DragDropZipBase64Window(QWidget):
    """
    A PyQt5 window that allows drag-and-drop for files or folders.
    If dropped content is not Base64, it will be zipped and then Base64-encoded.
    If dropped content is valid Base64, it will be decoded, written to a .zip file, and extracted.
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
            '• If it is already Base64 (and ends with .b64), it will be decoded back to a .zip and extracted.'
        )
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        self.setLayout(layout)
        self.resize(600, 300)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """
        Accepts the drag if it contains URLs (files/folders).
        """
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
        """
        Logs completion of processing for a given path.
        """
        logging.info("Finished processing %s", path_str)

    def on_error(self, path_str: str, err: str) -> None:
        """
        Shows a critical error message if processing fails.
        """
        QMessageBox.critical(
            self,
            "Error",
            f"Failed to process {path_str}:\n{err}"
        )

    def _process_path(self, path: Path) -> None:
        """
        Determines if 'path' is Base64 or not.
        If not Base64, compress and encode.
        If Base64, decode and extract the resulting ZIP.

        NOTE: Directories cannot be checked for Base64 by reading bytes,
        so they are always zipped and encoded.
        """
        # If it's a directory, skip base64 check and zip+encode
        if path.is_dir():
            logging.info(
                "Detected a directory, skipping Base64 check -> Zipping and encoding: %s", path)
            self.zip_and_encode(path)
            return

        # It's a file, so we can safely read bytes
        data: bytes = path.read_bytes()

        if self.is_base64_data(data):
            # If valid Base64, decode + extract
            self.decode_and_extract(path, data)
        else:
            # Otherwise, zip + encode
            self.zip_and_encode(path)

    def is_base64_data(self, data: bytes) -> bool:
        """
        Checks if 'data' is valid Base64 by trying a full decode + re-encode comparison.
        Returns True if the data is valid Base64, otherwise False.
        """
        try:
            decoded: bytes = base64.b64decode(data, validate=True)
            return base64.b64encode(decoded).strip() == data.strip()
        except Exception:
            return False

    def decode_and_extract(self, path: Path, b64data: bytes) -> None:
        """
        Decodes Base64 data to a ZIP file, then extracts that ZIP.
        If the dropped file ends with '.b64', we remove that to form the .zip name.
        Otherwise, we append '_decoded.zip' as a fallback.
        """
        # 1) Decode
        zip_data: bytes = base64.b64decode(b64data)

        # 2) Decide on output ZIP path
        if path.suffix == '.b64':
            # remove .b64 -> yields .zip if original was "something.zip.b64"
            zip_path: Path = path.with_suffix('')
        else:
            # Fallback if no .b64 extension
            zip_path = path.with_name(path.name + '_decoded.zip')

        # 3) Write the decoded ZIP file
        zip_path.write_bytes(zip_data)
        logging.info("Decoded ZIP written to: %s", zip_path)

        # 4) Extract the ZIP
        self.extract_zip(zip_path)

    def extract_zip(self, zip_path: Path) -> None:
        """
        Extracts the ZIP to a folder named after the ZIP file's base name.
        e.g., 'MyDocs.zip' -> 'MyDocs/'.
        If that folder already exists, '_extracted' is appended.
        Includes a security check to prevent Zip Slip attacks.
        """
        extract_folder: Path = zip_path.with_suffix('')
        if extract_folder.exists():
            extract_folder = extract_folder.with_name(
                extract_folder.name + '_extracted')

        with zipfile.ZipFile(str(zip_path), 'r') as zf:
            # Secure extraction check
            for member in zf.namelist():
                dest = (extract_folder / member).resolve()
                if not str(dest).startswith(str(extract_folder.resolve()) + os.sep):
                    raise RuntimeError(f"Illegal path in zip: {member}")

            zf.extractall(str(extract_folder))

        logging.info("Extracted to folder: %s", extract_folder)

    def zip_and_encode(self, path: Path) -> None:
        """
        Compresses the given file/folder into an in-memory ZIP,
        then Base64-encodes it and writes out '<path>.zip.b64'.
        """
        zip_data: bytes = self.compress_to_zip(path)
        b64data: bytes = base64.b64encode(zip_data)

        # Construct output path as e.g. "file.ext.zip.b64" or "folder.zip.b64"
        output_path: Path = path.with_suffix(path.suffix + '.zip.b64')
        output_path.write_bytes(b64data)

        logging.info("Zipped and encoded -> %s", output_path)

    def compress_to_zip(self, path: Path) -> bytes:
        """
        Returns the compressed (zipped) data of a file/folder in memory,
        using maximum deflate compression if available.
        """
        buffer: io.BytesIO = io.BytesIO()

        # Prepare ZipFile parameters
        params = {
            'mode': 'w',
            'compression': zipfile.ZIP_DEFLATED
        }
        # Attempt to specify compresslevel=9 if Python supports it
        try:
            params['compresslevel'] = 9  # type: ignore
        except TypeError:
            pass  # older Python doesn't support compresslevel

        with zipfile.ZipFile(buffer, **params) as zf:
            if path.is_file():
                zf.write(str(path), arcname=path.name)
            else:
                for root, dirs, files in os.walk(str(path)):
                    for file in files:
                        full_path = Path(root) / file
                        arcname = full_path.relative_to(path)
                        zf.write(str(full_path), arcname=str(arcname))

        return buffer.getvalue()


def main() -> None:
    """
    Main entry point to run the PyQt application.
    For older PyQt5 versions, we use app.exec_().
    """
    app: QApplication = QApplication(sys.argv)
    window: DragDropZipBase64Window = DragDropZipBase64Window()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
