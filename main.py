#! python
import atexit
import logging
import os
import threading
import time
from datetime import datetime, timedelta

import dotenv
import pandas as pd
import seaborn as sns
from flask import Flask, jsonify, send_file, render_template_string, url_for
from PyViCare.PyViCare import PyViCare
from zoneinfo import ZoneInfo
import matplotlib
matplotlib.use('Agg')  # Set the backend to non-interactive 'Agg'
from matplotlib import pyplot as plt
import pytz

tz = pytz.timezone('Europe/Amsterdam')

dotenv.load_dotenv()

# Check if we're running in local mode
LOCAL_MODE = os.getenv("LOCAL_MODE", "false").lower() == "true"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("ViCareUB2")

# Global flag to control the background thread
running = True

app = Flask(__name__, static_url_path='', static_folder='static')


def get_device():
    client_id = os.getenv("CLIENT_ID")
    email = os.getenv("EMAIL")
    password = os.getenv("PASSWORD")
    if (
        not isinstance(email, str)
        or not isinstance(password, str)
        or not isinstance(client_id, str)
    ):
        raise ValueError("Invalid email, password, or client_id")
    vicare = PyViCare()
    vicare.initWithCredentials(email, password, client_id, "token.save")
    logger.info("authenticated")
    devices = vicare.devices
    device = devices[1]
    t = device.asAutoDetectDevice()
    return t, vicare


def write_data(t):
    burner = t.burners[0]  # select burner
    circuit = t.circuits[0]  # select heating circuit

    temp_out = t.getOutsideTemperature()
    temp_boiler = t.getBoilerTemperature()
    temp_hotwater = t.getDomesticHotWaterStorageTemperature()
    temp_hotwater_target = t.getDomesticHotWaterConfiguredTemperature()
    temp_solar_collector = t.getSolarCollectorTemperature()
    temp_solar_storage = t.getSolarStorageTemperature()
    solar_production = t.getSolarPowerProductionToday()
    solar_pump = t.getSolarPumpActive()
    temp_heating = circuit.getSupplyTemperature()
    b_active = burner.getActive()
    b_mod = burner.getModulation()
    b_starts = burner.getStarts()
    b_hours = burner.getHours()
    b_time = int(datetime.now().timestamp())
    with open("./burner_data.csv", "a") as f:
        f.write(
            f"{b_time},{1 if b_active else 0},{b_mod},{b_hours},{b_starts},{temp_out},{temp_boiler},{temp_hotwater},{temp_hotwater_target},{temp_heating},{temp_solar_collector},{temp_solar_storage},{solar_production},{1 if solar_pump else 0}\n"
        )
    return None


def get_data_for_plotting():
    colnames = [
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
    ]
    bdf = pd.read_csv("burner_data.csv", names=colnames)[-1000:]
    if not isinstance(bdf, pd.DataFrame):
        raise ValueError("Invalid data type")
    bdf["time"] = pd.to_datetime(bdf["timestamp"], unit="s") + timedelta(hours=1)
    bdf = bdf[pd.to_datetime(bdf["time"]) > datetime.now() + timedelta(days=-2)]
    bdf["hours"] = bdf["hours"] - bdf["hours"].min()
    bdf["modulation"] = 2 + bdf["modulation"] / 50
    bdf["starts"] = bdf["starts"] - bdf["starts"].min()
    bdf["starts"] = 10 * (bdf["starts"] / bdf["starts"].max())
    bdf = bdf[~bdf.temp_heating.isna()]
    if not isinstance(bdf, pd.DataFrame):
        raise ValueError("Invalid data type")
    bdf = bdf.drop_duplicates(
        colnames[1:],
        keep="first",
    )
    melted = bdf.melt(id_vars="time")
    return melted


def make_plot(melted):
    # Set the style to dark
    plt.style.use('dark_background')
    
    # First plot - System metrics
    fig1, ax1 = plt.subplots(figsize=(12, 8))
    fig1.patch.set_facecolor('#1a1a1a')
    ax1.set_facecolor('#2d2d2d')
    
    _ = sns.lineplot(
        data=melted[
            melted.variable.isin(
                ["hours", "active", "modulation", "starts", "solar_production", "solar_pump"]
            )
        ],
        x="time",
        y="value",
        hue="variable",
        ax=ax1,
    )
    ax1.xaxis.set_tick_params(rotation=30, colors='white')
    ax1.yaxis.set_tick_params(colors='white')
    ax1.spines['bottom'].set_color('white')
    ax1.spines['top'].set_color('white')
    ax1.spines['left'].set_color('white')
    ax1.spines['right'].set_color('white')
    ax1.grid(True, color='gray', alpha=0.2)
    
    # Add night time spans to first plot
    now = datetime.now()
    x1 = now.replace(hour=21, minute=30, second=0, microsecond=0) + timedelta(days=-2)
    x2 = x1 + timedelta(hours=8)
    while x1 < now:
        ax1.axvspan(x1, x2, 0, 10, color='#404040', alpha=0.3)
        x1 = x1 + timedelta(hours=24)
        x2 = x1 + timedelta(hours=8)
        if x2 > now:
            x2 = now
    
    plt.tight_layout()
    plt.savefig("./static/system_metrics.png", facecolor='#1a1a1a', edgecolor='none', bbox_inches='tight', pad_inches=0.5)
    plt.close(fig1)
    
    # Second plot - Temperature metrics
    fig2, ax2 = plt.subplots(figsize=(12, 8))
    fig2.patch.set_facecolor('#1a1a1a')
    ax2.set_facecolor('#2d2d2d')
    
    temps = [
        "temp_boiler",
        "temp_hotwater",
        "temp_hotwater_target",
        "temp_solcollector",
        "temp_solstorage",
    ]
    
    _ = sns.lineplot(
        data=melted[melted.variable.isin(temps)],
        x="time",
        y="value",
        hue="variable",
        ax=ax2,
    )
    ax2_twin = ax2.twinx()
    _ = sns.lineplot(
        data=melted[melted.variable == "temp_out"],
        x="time",
        y="value",
        color="violet",
        ax=ax2_twin,
    )
    
    # Style second plot and its twin
    ax2.xaxis.set_tick_params(rotation=30, colors='white')
    ax2.yaxis.set_tick_params(colors='white')
    ax2_twin.yaxis.set_tick_params(colors='white')
    ax2.spines['bottom'].set_color('white')
    ax2.spines['top'].set_color('white')
    ax2.spines['left'].set_color('white')
    ax2.spines['right'].set_color('white')
    ax2_twin.spines['bottom'].set_color('white')
    ax2_twin.spines['top'].set_color('white')
    ax2_twin.spines['left'].set_color('white')
    ax2_twin.spines['right'].set_color('white')
    ax2.grid(True, color='gray', alpha=0.2)
    
    # Add night time spans to second plot
    x1 = now.replace(hour=21, minute=30, second=0, microsecond=0) + timedelta(days=-2)
    x2 = x1 + timedelta(hours=8)
    while x1 < now:
        ax2.axvspan(x1, x2, 0, 10, color='#404040', alpha=0.3)
        x1 = x1 + timedelta(hours=24)
        x2 = x1 + timedelta(hours=8)
        if x2 > now:
            x2 = now
    
    plt.tight_layout()
    plt.savefig("./static/temperature_metrics.png", facecolor='#1a1a1a', edgecolor='none', bbox_inches='tight', pad_inches=0.5)
    plt.close(fig2)
    
    return melted.iloc[-1,0]  # Return the last data point timestamp


def background_task():
    """Background task that collects data and generates plots every 5 minutes"""
    global running
    while running:
        try:
            logger.info("Starting background data collection")
            if not LOCAL_MODE:
                main(plot=False, collect=True)
            
            # Generate plots regardless of mode
            logger.info("Generating plots")
            try:
                melted = get_data_for_plotting()
                make_plot(melted)
                logger.info("Successfully generated plots")
            except Exception as e:
                logger.error(f"Error generating plots: {e}")
                
            logger.info("Completed background task")
        except Exception as e:
            logger.error(f"Error in background task: {e}")

        # Wait for 5 minutes
        for _ in range(300):
            if not running:
                break
            time.sleep(1)


@app.route("/")
def index():
    """Serve the main page with the plot"""
    try:
        # Get the last data point timestamp from the CSV directly
        df = pd.read_csv("burner_data.csv", names=[
            "timestamp", "active", "modulation", "hours", "starts",
            "temp_out", "temp_boiler", "temp_hotwater", "temp_hotwater_target",
            "temp_heating", "temp_solcollector", "temp_solstorage",
            "solar_production", "solar_pump"
        ])
        last_data_point = (pd.to_datetime(df.iloc[-1]["timestamp"], unit="s") + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        logger.error(f"Error reading last data point: {e}")
        last_data_point = "Error reading data"

    template = """
    <html>
        <head>
            <title>ViCare Monitoring</title>
            <meta http-equiv="refresh" content="300">
            <link rel="stylesheet" href="/css/style.css">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body>
            <div class="container">
                <div class="header-container">
                    <h1>ViCare Monitoring</h1>
                    <div class="timestamps">
                        <div class="timestamp">Page updated: {{ timestamp }}</div>
                        <div class="timestamp">Last data point: {{ last_data_point }}</div>
                    </div>
                </div>
                <div class="plots-container">
                    <div class="plot-container">
                        <div class="plot-title">System Metrics</div>
                        <img src="/system_metrics.png" alt="System Metrics Plot">
                    </div>
                    <div class="plot-container">
                        <div class="plot-title">Temperature Metrics</div>
                        <img src="/temperature_metrics.png" alt="Temperature Metrics Plot">
                    </div>
                </div>
            </div>
        </body>
    </html>
    """
    return render_template_string(
        template,
        timestamp=datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S"),
        last_data_point=last_data_point
    )


@app.route("/health")
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy"})


def cleanup():
    """Cleanup function to stop the background thread"""
    global running
    running = False
    logger.info("Stopping background task")


def main(plot=False, collect=True):
    logger.info("starting")
    if collect and not LOCAL_MODE:
        logger.info("getting data")
        t, _ = get_device()
        write_data(t)
    if plot:
        logger.info("plotting")
        melted = get_data_for_plotting()
        logger.info("saving")
        make_plot(melted)


if __name__ == "__main__":
    if LOCAL_MODE:
        logger.info("Running in local mode - web server and plotting only")
    else:
        logger.info("Running in full mode with ViCare device connection")

    # Register cleanup function
    atexit.register(cleanup)

    # Start background thread for data collection only
    background_thread = threading.Thread(target=background_task)
    background_thread.daemon = True
    background_thread.start()

    # Run Flask app
    app.run(host="0.0.0.0", port=8000, debug=False)
