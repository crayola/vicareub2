#! python

import pandas as pd
import seaborn as sns
from datetime import datetime, timedelta
import logging
from PyViCare.PyViCare import PyViCare
from matplotlib import pyplot as plt
import fire
import dotenv
import os

dotenv.load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

def get_device():
    client_id = os.getenv("CLIENT_ID")
    email = os.getenv("EMAIL")
    password = os.getenv("PASSWORD")
    vicare = PyViCare()
    vicare.initWithCredentials(email, password, client_id, "token.save")
    device = vicare.devices[0]
    t = device.asAutoDetectDevice()
    return t


def write_data(t):
    burner = t.getBurner(0)  # select burner
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
    bdf["time"] = pd.to_datetime(bdf["timestamp"], unit="s") + timedelta(hours=2)
    #bdf = bdf[bdf["time"].between(datetime.now() + timedelta(days=-2), datetime.now())]
    bdf = bdf[bdf["time"] > datetime.now() + timedelta(days=-2)]
    bdf["hours"] = bdf["hours"] - bdf["hours"].min()
    bdf["modulation"] = 2 + bdf["modulation"] / 50
    bdf["starts"] = bdf["starts"] - bdf["starts"].min()
    bdf["starts"] = 10 * (bdf["starts"] / bdf["starts"].max())
    bdf = bdf[~bdf.temp_heating.isna()]
    bdf = bdf.drop_duplicates(
        colnames[1:],
        keep="first",
    )
    melted = bdf.melt(id_vars="time")
    return melted


def make_plot(melted):
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
    return plt


def main(plot_only=False):
    logging.log(logging.INFO, "starting")
    if not plot_only:
        logging.log(logging.INFO, "getting data")
        t = get_device()
        write_data(t)
    logging.log(logging.INFO, "plotting")
    melted = get_data_for_plotting()
    make_plot(melted)
    logging.log(logging.INFO, "saving")
    plt.savefig("/home/tim/projects/flarum-docker/assets/ub2/fig.png")


if __name__ == "__main__":
    fire.Fire(main)
