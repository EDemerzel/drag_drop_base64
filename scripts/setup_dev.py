#!/usr/bin/env python3
"""Development environment setup script with SSL bypass options."""
import subprocess
import sys
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
        print(f"❌ Package installation failed: {e}")
        print(f"   Return code: {e.returncode}")
        if e.output:
            print(f"   Output: {e.output}")
        print("\n🔧 Troubleshooting tips:")
        print("   • Check your internet connection")
        print("   • Try running with administrator privileges")
        print("   • Verify Python and pip are properly installed")
        print("   • Check if pyproject.toml exists and is valid")
        sys.exit(1)

    except FileNotFoundError as e:
        print(f"❌ Python or pip not found: {e}")
        print("🔧 Please ensure Python and pip are installed and in your PATH")
        sys.exit(1)

    except PermissionError as e:
        print(f"❌ Permission denied: {e}")
        print("🔧 Try running with administrator/sudo privileges")
        sys.exit(1)

    except OSError as e:
        print(f"❌ System error: {e}")
        print("🔧 Check your system configuration and try again")
        sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️  Installation interrupted by user")
        print("🔧 Run the script again to complete setup")
        sys.exit(130)  # Standard exit code for SIGINT

    except Exception as e:
        # Keep a final catch-all but log it properly for debugging
        print(f"❌ Unexpected error during setup: {type(e).__name__}: {e}")
        print("🔧 This is an unexpected error. Please report this issue with the following details:")
        print(f"   • Python version: {sys.version}")
        print(f"   • Operating system: {os.name}")
        print(f"   • Working directory: {os.getcwd()}")
        print(f"   • Error type: {type(e).__name__}")
        print(f"   • Error message: {e}")

        # In development, you might want to see the full traceback
        import traceback
        print("\n🐛 Full traceback for debugging:")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
