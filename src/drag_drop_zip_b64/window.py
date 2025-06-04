"""Window module - re-exports the main window class for cleaner imports."""

from .drag_drop_zip_b64_threaded import DragDropZipBase64Window

__all__ = ["DragDropZipBase64Window"]

# Optional: Add convenience function for programmatic use


def create_window():
    """
    Create and return a new DragDropZipBase64Window instance.

    Returns:
        DragDropZipBase64Window: A new window instance ready to be shown

    Example:
        >>> from drag_drop_zip_b64.window import create_window
        >>> window = create_window()
        >>> window.show()
    """
    return DragDropZipBase64Window()
