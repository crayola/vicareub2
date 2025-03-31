import logging
from datetime import datetime
from typing import Any, Dict

from .database import DatabaseService

logger = logging.getLogger("ViCareUB2")


class DataCollector:
    def __init__(self):
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

    def write_to_db(self, data: Dict[str, Any]) -> None:
        """Write data to CSV file and SQLite database"""
        try:
            data_to_write = data.copy()
            self.database.save_heating_data(data_to_write)
            logger.debug(
                f"Successfully wrote data point at {datetime.fromtimestamp(data['timestamp'])}"
            )

        except Exception as e:
            logger.error(f"Failed to write data: {e}")
            raise
