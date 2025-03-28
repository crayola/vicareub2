#!/usr/bin/env python3
"""
Runner script for the ViCareUB2 Streamlit app.
"""

import importlib
import importlib.util
import logging
import subprocess
import sys
from pathlib import Path

from pyvicareub2.config import settings

logger = logging.getLogger("ViCareUB2")


def check_dependencies():
    """Check if Streamlit and Altair are installed, and install if missing"""
    dependencies = {"streamlit": "streamlit>=1.33.0", "altair": "altair>=5.2.0"}

    missing = []
    for package, version in dependencies.items():
        try:
            importlib.import_module(package)
            logger.info(f"Found {package} package")
        except ImportError:
            logger.warning(f"Missing required package: {package}")
            missing.append(version)

    if missing:
        logger.info(f"Installing missing dependencies: {', '.join(missing)}")
        try:
            # Try to install using pip as a module
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
            logger.info("Successfully installed dependencies")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install dependencies using pip: {e}")
            return False

    return True


def main():
    """Run the Streamlit app"""
    # Check and install dependencies
    if not check_dependencies():
        logger.error("Failed to ensure required dependencies")
        return 1

    # Find the streamlit_app.py file
    try:
        # Get the module spec
        module_spec = importlib.util.find_spec("pyvicareub2.streamlit_app")
        if module_spec and module_spec.origin:
            app_path = module_spec.origin
        else:
            # Fallback - find the directory containing this script
            script_dir = Path(__file__).resolve().parent
            app_path = str(script_dir / "streamlit_app.py")

        logger.info(f"Using Streamlit app file: {app_path}")
    except Exception as e:
        logger.error(f"Failed to find streamlit_app.py: {e}")
        return 1

    # Ensure the static directory exists
    static_dir = Path("static")
    static_dir.mkdir(exist_ok=True)

    # Run Streamlit
    cmd = [
        "streamlit",
        "run",
        app_path,
        "--server.port",
        str(settings.streamlit_port),
        "--server.address",
        "0.0.0.0",
        "--browser.serverAddress",
        "localhost",
        "--theme.base",
        "dark",
    ]

    logger.info(f"Starting Streamlit app: {' '.join(cmd)}")

    # Execute Streamlit command
    try:
        # Use check=True to raise an exception if the command fails
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        logger.info("Streamlit app stopped by user")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to start Streamlit: {e}")
        return 1
    except Exception as e:
        logger.error(f"Error running Streamlit app: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
