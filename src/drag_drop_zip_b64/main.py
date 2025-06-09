"""Main entry point for the drag-drop-zip-b64 application."""

import logging
import os
import ssl
import sys
import urllib3

from PyQt5.QtWidgets import QApplication

from .drag_drop_zip_b64_threaded import DragDropZipBase64Window


def configure_ssl_bypass() -> None:
    """Configure SSL bypass for runtime network operations if needed."""
    # Only bypass SSL in development/problematic networks
    if os.getenv("DRAG_DROP_BYPASS_SSL", "").lower() in ("1", "true", "yes"):

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Create unverified SSL context
        ssl._create_default_https_context = ssl._create_unverified_context

        logging.getLogger(__name__).warning(
            "SSL verification disabled via DRAG_DROP_BYPASS_SSL environment variable"
        )


def main() -> None:
    """Launch the drag and drop GUI application with enhanced logging."""
    # Configure SSL bypass if requested
    configure_ssl_bypass()

    # Configure logging for the application
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(
            sys.stdout), logging.FileHandler("drag_drop_zip_b64.log")],
    )

    # Log startup
    logger = logging.getLogger(__name__)
    logger.info("Starting Drag & Drop ZIP Base64 application v1.1.0")
    logger.info("SSL/TLS encryption support enabled")

    # Log SSL bypass status
    if os.getenv("DRAG_DROP_BYPASS_SSL"):
        logger.warning("SSL verification bypassed for network operations")
    else:
        logger.info("SSL verification enabled for secure network operations")

    try:
        app = QApplication(sys.argv)
        app.setApplicationName("Drag & Drop ZIP Base64")
        app.setApplicationVersion("1.1.0")
        app.setOrganizationName("EDemerzel")

        window = DragDropZipBase64Window()
        window.show()

        logger.info("Application GUI launched successfully")
        sys.exit(app.exec_())

    except Exception as e:
        logger.exception("Failed to start application: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
