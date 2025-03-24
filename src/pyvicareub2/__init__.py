"""
PyViCareUB2 - A monitoring tool for ViCare heating systems
"""

from .config import settings
from .data_collector import DataCollector
from .plot_generator import PlotGenerator
from .vicare_client import ViCareClient
from .web_server import app

__version__ = "0.1.0"
__all__ = ["settings", "ViCareClient", "DataCollector", "PlotGenerator", "app"]
