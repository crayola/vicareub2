import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytz
from flask import Flask, jsonify, render_template_string

from .config import settings

logger = logging.getLogger("ViCareUB2")

app = Flask(__name__, static_url_path="", static_folder=str(Path("static").absolute()))


@app.route("/")
def index():
    """Serve the main page with the plots"""
    try:
        # Get the last data point timestamp from the CSV directly
        df = pd.read_csv(
            settings.data_file,
            names=[
                "timestamp",
                "active",
                "modulation",
                "hours",
                "starts",
                "temp_out",
                "temp_boiler",
                "temp_hotwater",
                "temp_hotwater_target",
                "temp_heating",
                "temp_solcollector",
                "temp_solstorage",
                "solar_production",
                "solar_pump",
                "circulation_pump",
                "dhw_pump",
            ],
        )
        last_data_point = (
            (pd.to_datetime(df.iloc[-1]["timestamp"], unit="s", utc=True))
            .tz_convert(settings.timezone)
            .strftime("%Y-%m-%d %H:%M:%S")
        )
    except Exception as e:
        logger.error(f"Error reading last data point: {e}")
        last_data_point = "Error reading data"

    template = """
    <html>
        <head>
            <title>ViCare Monitoring</title>
            <meta http-equiv="refresh" content="300">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet" href="/css/style.css">
        </head>
        <body>
            <div class="container">
                <div class="page-container">
                    <div class="header-container">
                        <h1>ViCare Monitoring</h1>
                        <div class="timestamps">
                            <div class="timestamp">Page updated: {{ timestamp }}</div>
                            <div class="timestamp">Last data point: {{ last_data_point }}</div>
                            <div class="timezone">Timezone: {{ settings.timezone }}</div>
                        </div>
                    </div>
                    <div class="plots-container">
                        <div class="plot-container">
                            <img src="/system_metrics.png?t={{ timestamp }}" alt="System Metrics Plot"
                                 onerror="this.parentElement.innerHTML += '<div class=\'error\'>Failed to load System Metrics plot</div>'">
                        </div>
                        <div class="plot-container">
                            <img src="/temperature_metrics.png?t={{ timestamp }}" alt="Temperature Metrics Plot"
                                 onerror="this.parentElement.innerHTML += '<div class=\'error\'>Failed to load Temperature Metrics plot</div>'">
                        </div>
                    </div>
                </div>
            </div>
        </body>
    </html>
    """
    return render_template_string(
        template,
        timestamp=datetime.now(pytz.timezone(settings.timezone)).strftime("%Y-%m-%d %H:%M:%S"),
        last_data_point=last_data_point,
    )


@app.route("/health")
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy"})
