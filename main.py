#! python
import logging
import os
import sys
import time
from datetime import datetime, timedelta

import dotenv
import pandas as pd
import seaborn as sns
from PyViCare.PyViCare import PyViCare
from tqdm import tqdm

dotenv.load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("ViCareUB2")


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
    return t


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
    bdf = bdf[bdf["time"] > datetime.now() + timedelta(days=-2)]
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
    from matplotlib import pyplot as plt

    temps = [
        "temp_boiler",
        "temp_hotwater",
        "temp_hotwater_target",
        "temp_solcollector",
        "temp_solstorage",
    ]
    fig, ax = plt.subplots(2, 1, figsize=(12, 16))
    _ = sns.lineplot(
        data=melted[
            melted.variable.isin(
                ["hours", "active", "modulation", "starts", "solar_production","solar_pump"]
            )
        ],
        x="time",
        y="value",
        hue="variable",
        ax=ax[0],
    )
    ax[0].xaxis.set_tick_params(rotation=30)
    _ = sns.lineplot(
        data=melted[melted.variable.isin(temps)],
        x="time",
        y="value",
        hue="variable",
        ax=ax[1],
    )
    ax2 = ax[1].twinx()
    _ = sns.lineplot(
        data=melted[melted.variable == "temp_out"],
        x="time",
        y="value",
        color="violet",
        ax=ax2,
    )
    ax[1].xaxis.set_tick_params(rotation=30)
    now = datetime.now()
    x1 = now.replace(hour=21, minute=30, second=0, microsecond=0) + timedelta(days=-2)
    x2 = x1 + timedelta(hours=8)
    while x1 < now:
        ax[0].axvspan(x1, x2, 0, 10, color="grey", alpha=0.2)
        ax[1].axvspan(x1, x2, 0, 10, color="grey", alpha=0.2)
        x1 = x1 + timedelta(hours=24)
        x2 = x1 + timedelta(hours=8)
        if x2 > now:
            x2 = now
    fig.suptitle(
        f"Last generated {datetime.now().replace(microsecond=0)}; last data point {melted.iloc[-1,0]}"
    )
    plt.savefig("./fig.png")


def main(plot=False, collect=True):
    logger.info("starting")
    if collect:
        logger.info("getting data")
        t = get_device()
        write_data(t)
    if plot:
        logger.info("plotting")
        melted = get_data_for_plotting()
        logger.info("saving")
        make_plot(melted)


if __name__ == "__main__":
    # fire.Fire(main)
    plot = "--plot" in sys.argv
    collect = "--collect" in sys.argv
    once = "--once" in sys.argv

    # If no arguments provided, default collect to True
    if len(sys.argv) <= 1:
        collect = True

    while True and not once:
        logging.info("Starting next iteration of the monitoring loop")
        try:
            main(plot, collect)
        except Exception as e:
            logger.error(f"Error occurred: {e}")
        # Wait for 5 minutes (300 seconds) before running again, with a progress bar
        print("boo")
        for i in tqdm(range(300), desc="Time until next iteration", unit="s"):
            logger.info("")
            time.sleep(1)

    if once:
        main(plot, collect)
    else:
        logging.info("Exiting")
