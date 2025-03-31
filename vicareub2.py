#!/usr/bin/env python3
"""
PyViCareUB2 - A monitoring tool for ViCare heating systems
"""

import argparse
import atexit
import logging
import threading
import time

from pyvicareub2 import DataCollector, ViCareClient, settings
from pyvicareub2.run_streamlit import main as run_streamlit

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("ViCareUB2")

# Global flag to control the background thread
running = True


def background_task():
    """Background task that collects data and generates plots every 5 minutes"""
    global running
    vicare_client = ViCareClient()
    data_collector = DataCollector()

    while running:
        try:
            logger.info("Starting background data collection")
            if not settings.local_mode:
                # Collect data from ViCare
                data = vicare_client.get_device_data()
                data_collector.write_to_db(data)

            logger.info("Completed background task")
        except Exception as e:
            logger.error(f"Error in background task: {e}")

        # Wait for configured interval
        for _ in range(settings.background_task_interval):
            if not running:
                break
            time.sleep(1)


def cleanup():
    """Cleanup function to stop the background thread"""
    global running
    running = False
    logger.info("Stopping background task")


def start_data_collection():
    """Start the background data collection thread"""
    # Register cleanup function
    atexit.register(cleanup)

    # Start background thread for data collection
    background_thread = threading.Thread(target=background_task)
    background_thread.daemon = True
    background_thread.start()

    return background_thread


def main():
    """Main entry point for the application"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="ViCareUB2 - ViCare Monitoring Tool")
    parser.add_argument("--streamlit", action="store_true", help="Use Streamlit for visualization")
    parser.add_argument(
        "--local", action="store_true", help="Run in local mode (no device connection)"
    )
    args = parser.parse_args()

    # Update settings based on arguments
    if args.local:
        settings.local_mode = True

    if args.streamlit:
        settings.use_streamlit = True

    if settings.local_mode:
        logger.info("Running in local mode - web server and plotting only")
    else:
        logger.info("Running in full mode with ViCare device connection")

    # Start data collection thread
    start_data_collection()

    # Run the appropriate visualization server
    logger.info("Starting Streamlit visualization server")
    run_streamlit()


if __name__ == "__main__":
    main()
