import sys
import base64
import os
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
from PyQt5.QtCore import Qt, QUrl


class DragDropBase64Window(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Drag & Drop Base64 Encoder/Decoder')
        self.setAcceptDrops(True)

        layout = QVBoxLayout()

        self.label = QLabel(
            'Drag and drop files or folders here.\n'
            'If a file is already Base64, it will be decoded.\n'
            'Otherwise, it will be Base64-encoded.\n\n'
            'Encoded files will have a .b64 extension. '
            'If an encoded file ends with .b64, it will be decoded back to its original extension.'
        )
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        self.setLayout(layout)
        self.resize(500, 300)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """
        Accept the drag if it contains URLs (files/folders).
        """
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """
        When the user drops files/folders onto the widget, process them.
        """
        urls = event.mimeData().urls()
        if urls:
            for url in urls:
                local_path = url.toLocalFile()
                if os.path.isdir(local_path):
                    # Recursively process the entire folder
                    self.processFolder(local_path)
                else:
                    # Process a single file
                    self.processFile(local_path)

    def processFolder(self, folder_path: str):
        """
        Recursively process a folder, encoding/decoding all files within it.
        """
        for root, dirs, files in os.walk(folder_path):
            for f in files:
                file_path = os.path.join(root, f)
                self.processFile(file_path)

    def processFile(self, file_path: str):
        """
        Check if the file is Base64 encoded; if so, decode it;
        otherwise, encode it. Output is written in the same directory.
        """
        with open(file_path, 'rb') as f:
            data = f.read()

        # Attempt to decode as Base64
        try:
            decoded_data = base64.b64decode(data, validate=True)
            reencoded = base64.b64encode(decoded_data)

            # If re-encoded data matches the original (minus optional whitespace),
            # we treat it as valid Base64.
            if reencoded == data.strip():
                # It's valid Base64. Decide how to name the decoded file.
                if file_path.endswith('.b64'):
                    # Remove the ".b64" extension and decode to the original name
                    output_path = file_path[:-4]  # remove the trailing ".b64"
                else:
                    # If there's no ".b64" extension, just append "_decoded"
                    output_path = f"{file_path}_decoded"

                with open(output_path, 'wb') as out_f:
                    out_f.write(decoded_data)

                print(f'Decoded file written to: {output_path}')
                return
            else:
                # Not valid or fully matching Base64 -> treat as normal file to encode
                raise ValueError(
                    'Decoded data did not match reencoded content')
        except Exception:
            # Not Base64, so let's encode
            encoded_data = base64.b64encode(data)

            # If the file is not already .b64, we add .b64
            if not file_path.endswith('.b64'):
                output_path = file_path + '.b64'
            else:
                # Very unlikely scenario, but if it already ended with .b64
                # and wasn't valid base64, just use "_encoded" fallback
                output_path = f"{file_path}_encoded"

            with open(output_path, 'wb') as out_f:
                out_f.write(encoded_data)

            print(f'Encoded file written to: {output_path}')


def main():
    app = QApplication(sys.argv)
    window = DragDropBase64Window()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
