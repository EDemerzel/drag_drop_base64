#!/usr/bin/env python3
"""Development environment setup script with SSL bypass options."""
import subprocess
import sys
# import ssl
import os
from pathlib import Path


def main():
    """Set up development environment with SSL bypass for problematic networks."""
    project_root = Path(__file__).parent.parent

    # SSL bypass environment variables for pip
    env = os.environ.copy()
    env.update({
        'PYTHONHTTPSVERIFY': '0',
        'CURL_CA_BUNDLE': '',
        'REQUESTS_CA_BUNDLE': '',
    })

    print("🔧 Setting up development environment...")
    print("⚠️  SSL verification disabled for package installation")

    try:
        # Install in development mode with SSL bypass
        cmd = [
            sys.executable, "-m", "pip", "install",
            "--trusted-host", "pypi.org",
            "--trusted-host", "pypi.python.org",
            "--trusted-host", "files.pythonhosted.org",
            "--disable-pip-version-check",
            "--no-cache-dir",
            "-e", ".[dev]"
        ]

        subprocess.run(cmd, cwd=project_root, check=True, env=env)

        print("✅ Development environment setup complete!")
        print("📋 Available commands:")
        print("   • pytest                    - Run tests")
        print("   • drag-drop-zip-b64         - Launch GUI")
        print("   • black src/ tests/         - Format code")
        print("   • isort src/ tests/         - Sort imports")
        print("   • mypy src/                 - Type checking")

    except subprocess.CalledProcessError as e:
        print(f"❌ Installation failed: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("   • Check your internet connection")
        print("   • Try running with administrator privileges")
        print("   • Verify Python and pip are properly installed")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
