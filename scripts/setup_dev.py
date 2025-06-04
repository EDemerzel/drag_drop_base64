#!/usr/bin/env python3
"""Development environment setup script."""
import subprocess
import sys
from pathlib import Path


def main():
    """Set up development environment."""
    # Fix: Go up two levels to reach project root
    project_root = Path(__file__).parent.parent.parent

    # Install in development mode
    subprocess.run([sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
                   cwd=project_root, check=True)

    print("✅ Development environment setup complete!")
    print("Run 'pytest' to test or 'drag-drop-zip-b64' to launch the GUI.")


if __name__ == "__main__":
    main()
