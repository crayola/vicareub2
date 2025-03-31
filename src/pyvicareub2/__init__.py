"""
PyViCareUB2 - A monitoring tool for ViCare heating systems
"""

from .config import settings
from .data_collector import DataCollector
from .database import DatabaseService
from .models import HeatingData, RawDeviceData
from .vicare_client import ViCareClient

__version__ = "0.1.0"
__all__ = [
    "settings",
    "ViCareClient",
    "DataCollector",
    "DatabaseService",
    "HeatingData",
    "RawDeviceData",
]
