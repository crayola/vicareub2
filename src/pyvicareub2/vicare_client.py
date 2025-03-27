import logging
from datetime import datetime
from typing import Any

from PyViCare.PyViCare import PyViCare

from .config import settings

logger = logging.getLogger("ViCareUB2")


class ViCareClient:
    def __init__(self):
        self.vicare = None
        self.device = None

    def connect(self) -> None:
        """Initialize connection to ViCare device"""
        try:
            self.vicare = PyViCare()
            self.vicare.initWithCredentials(
                settings.email,
                settings.password,
                settings.client_id,
                settings.token_file,
            )
            logger.info("Successfully authenticated with ViCare")

            devices = self.vicare.devices
            if not devices:
                raise ValueError("No ViCare devices found")

            self.device = devices[1].asGazBoiler()
            logger.info("Successfully connected to ViCare device")

        except Exception as e:
            logger.error(f"Failed to connect to ViCare: {e}")
            raise

    def get_device_data(self) -> dict[str, Any]:
        """Collect data from the ViCare device"""
        if not self.device:
            self.connect()
        if not self.device:
            raise ValueError("No ViCare device found")

        try:
            burner = self.device.burners[0]
            circuit = self.device.circuits[0]

            return {
                "timestamp": int(datetime.now().timestamp()),
                "active": 1 if burner.getActive() else 0,
                "modulation": burner.getModulation(),
                "hours": burner.getHours(),
                "starts": burner.getStarts(),
                "temp_out": self.device.getOutsideTemperature(),
                "temp_boiler": self.device.getBoilerTemperature(),
                "temp_hotwater": self.device.getDomesticHotWaterStorageTemperature(),
                "temp_hotwater_target": self.device.getDomesticHotWaterConfiguredTemperature(),
                "temp_solcollector": self.device.getSolarCollectorTemperature(),
                "temp_solstorage": self.device.getSolarStorageTemperature(),
                "solar_production": self.device.getSolarPowerProductionToday(),
                "solar_pump": 1 if self.device.getSolarPumpActive() else 0,
                "temp_heating": circuit.getSupplyTemperature(),
                "circulation_pump": 1
                if self.device.getDomesticHotWaterCirculationPumpActive()
                else 0,
                "dhw_pump": 1 if self.device.getDomesticHotWaterPumpActive() else 0,
            }
        except Exception as e:
            logger.error(f"Failed to collect device data: {e}")
            raise

    def get_device_data_json(self) -> dict[str, Any]:
        """Collect data from the ViCare device"""
        if not self.vicare or not self.vicare.devices[1]:
            return {}

        try:
            raw_dict: dict[str, Any] = self.vicare.devices[1].get_raw_json()
            return raw_dict

        except Exception as e:
            logger.error(f"Failed to collect device data: {e}")
            return {}
