import logging
from datetime import datetime, timedelta
from typing import Any, Dict

import pandas as pd

from .config import settings
from .database import DatabaseService

logger = logging.getLogger("ViCareUB2")


class DataCollector:
    def __init__(self):
        self.data_file = settings.data_file
        self.data_file_json = settings.data_file_json
        self.database = DatabaseService()
        self.dtypes = {
            "timestamp": "int64",
            "active": "int",
            "modulation": "float64",
            "hours": "float64",
            "starts": "int64",
            "temp_out": "float64",
            "temp_boiler": "float64",
            "temp_hotwater": "float64",
            "temp_hotwater_target": "float64",
            "temp_heating": "float64",
            "temp_solcollector": "float64",
            "temp_solstorage": "float64",
            "solar_production": "float64",
            "solar_pump": "int",
        }

    def write_csv(self, data: Dict[str, Any]) -> None:
        """Write data to CSV file and SQLite database"""
        try:
            # Convert boolean values to integers for CSV storage
            data_to_write = data.copy()

            # Convert data to CSV line
            csv_line = ",".join(
                str(data_to_write[key])
                for key in [
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
                ]
            )

            # For backward compatibility, still write to CSV
            with open(self.data_file, "a") as f:
                f.write(f"{csv_line}\n")

            # Store data in SQLite database
            self.database.save_heating_data(data_to_write)

            logger.debug(
                f"Successfully wrote data point at {datetime.fromtimestamp(data['timestamp'])}"
            )

        except Exception as e:
            logger.error(f"Failed to write data: {e}")
            raise

    def write_json(self, data: Dict[str, Any]) -> None:
        """Write data to JSON file and SQLite database"""
        try:
            # For backward compatibility, still write to JSON file
            with open(self.data_file_json, "a") as f:
                f.write(f"{data}\n")
            
            # Store raw data in SQLite database
            self.database.save_raw_device_data(data)

        except Exception as e:
            logger.error(f"Failed to write data: {e}")
            raise

    def get_data_for_plotting(self) -> pd.DataFrame:
        """Get and prepare data for plotting from SQLite database"""
        try:
            # Get data from database
            return self.database.get_data_for_plotting()
        except Exception as e:
            logger.error(f"Failed to prepare data for plotting from database, falling back to CSV: {e}")
            
            # Fall back to CSV if database fails
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
                "circulation_pump",
                "dhw_pump",
            ]

            # Read last 1000 rows with proper data types
            bdf = pd.read_csv(
                self.data_file,
                names=colnames,  # dtype=self.dtypes,
                low_memory=False,
            ).tail(10000)

            # Convert timestamp to datetime
            bdf["time"] = pd.to_datetime(bdf["timestamp"], unit="s") + timedelta(hours=1)

            # Filter last 2 days
            bdf = bdf[pd.to_datetime(bdf["time"]) > datetime.now() + timedelta(days=-2)]

            # Normalize data
            bdf["hours"] = bdf["hours"] - bdf["hours"].min()
            bdf["modulation"] = 2 + bdf["modulation"] / 50
            bdf["starts"] = bdf["starts"] - bdf["starts"].min()
            bdf["starts"] = 10 * (bdf["starts"] / bdf["starts"].max())

            # Clean data
            bdf = bdf[~bdf.temp_heating.isna()]
            if not isinstance(bdf, pd.DataFrame):
                raise ValueError("Invalid DataFrame")
            bdf = bdf.drop_duplicates(colnames[1:], keep="first")

            # Melt for plotting
            return bdf.melt(id_vars="time")
