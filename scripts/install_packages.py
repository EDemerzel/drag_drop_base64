#!/usr/bin/env python3
"""Package installation script with SSL bypass for development."""
import subprocess
import sys
import os
from pathlib import Path


def install_with_ssl_bypass(packages=None):
    """Install packages with SSL verification disabled."""
    if packages is None:
        packages = []

    # SSL bypass environment variables
    env = os.environ.copy()
    env.update({
        'PYTHONHTTPSVERIFY': '0',
        'CURL_CA_BUNDLE': '',
        'REQUESTS_CA_BUNDLE': '',
    })

    # Base pip command with SSL bypass flags
    base_cmd = [
        sys.executable, "-m", "pip", "install",
        "--trusted-host", "pypi.org",
        "--trusted-host", "pypi.python.org",
        "--trusted-host", "files.pythonhosted.org",
        "--disable-pip-version-check",
        "--no-cache-dir"
    ]

    try:
        if packages:
            # Install specific packages
            cmd = base_cmd + packages
            print(f"📦 Installing packages: {', '.join(packages)}")
        else:
            # Install from requirements.txt
            project_root = Path(__file__).parent.parent
            requirements_file = project_root / "requirements.txt"

            if requirements_file.exists():
                cmd = base_cmd + ["-r", str(requirements_file)]
                print("📦 Installing from requirements.txt")
            else:
                print("❌ No requirements.txt found and no packages specified")
                return False

        subprocess.run(cmd, check=True, env=env)
        print("✅ Package installation successful!")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Package installation failed: {e}")
        print(f"   Return code: {e.returncode}")
        if e.stderr:
            print(f"   Error output: {e.stderr}")
        return False

    except FileNotFoundError as e:
        print(f"❌ Python or pip not found: {e}")
        print("🔧 Please ensure Python and pip are installed and in your PATH")
        return False

    except PermissionError as e:
        print(f"❌ Permission denied: {e}")
        print("🔧 Try running with administrator/sudo privileges")
        return False

    except KeyboardInterrupt:
        print("\n⚠️  Installation interrupted by user")
        return False

    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}: {e}")
        print("🔧 Please check your configuration and try again")
        return False


def main():
    """Main entry point for package installation."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Install packages with SSL bypass")
    parser.add_argument("packages", nargs="*", help="Packages to install")
    parser.add_argument("--requirements", "-r", action="store_true",
                        help="Install from requirements.txt")

    args = parser.parse_args()

    try:
        if args.requirements or not args.packages:
            success = install_with_ssl_bypass()
        else:
            success = install_with_ssl_bypass(args.packages)

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(130)


if __name__ == "__main__":
    main()
