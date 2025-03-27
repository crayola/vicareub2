#!/usr/bin/env python3
"""
PyViCareUB2 - A monitoring tool for ViCare heating systems
"""

import atexit
import logging
import threading
import time

from pyvicareub2 import DataCollector, PlotGenerator, ViCareClient, app, settings

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
    plot_generator = PlotGenerator()

    while running:
        try:
            logger.info("Starting background data collection")
            if not settings.local_mode:
                # Collect data from ViCare
                data = vicare_client.get_device_data()
                data_collector.write_csv(data)
                # raw_data = vicare_client.get_device_data_json()
                # data_collector.write_json(raw_data)

            # Generate plots
            logger.info("Generating plots")
            try:
                plot_data = data_collector.get_data_for_plotting()
                plot_generator.generate_plots(plot_data)
                logger.info("Successfully generated plots")
            except Exception as e:
                logger.error(f"Error generating plots: {e}")

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


def main():
    if settings.local_mode:
        logger.info("Running in local mode - web server and plotting only")
    else:
        logger.info("Running in full mode with ViCare device connection")

    # Register cleanup function
    atexit.register(cleanup)

    # Start background thread for data collection
    background_thread = threading.Thread(target=background_task)
    background_thread.daemon = True
    background_thread.start()

    # Run Flask app
    app.run(host=settings.server_host, port=settings.server_port, debug=False)


if __name__ == "__main__":
    main()
