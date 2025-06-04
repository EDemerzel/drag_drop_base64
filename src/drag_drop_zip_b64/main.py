"""Main entry point for the drag-drop-zip-b64 application."""
import sys
import logging
from PyQt5.QtWidgets import QApplication
from .drag_drop_zip_b64_threaded import DragDropZipBase64Window


def main() -> None:
    """Launch the drag and drop GUI application."""
    # Configure logging for the application
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("drag_drop_zip_b64.log")
        ]
    )

    app = QApplication(sys.argv)
    window = DragDropZipBase64Window()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
