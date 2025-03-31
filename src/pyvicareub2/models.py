"""
Database models for the ViCareUB2 application.
"""

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class HeatingData(Base):
    """Model for heating system data points."""
    
    __tablename__ = "heating_data"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(Integer, index=True, nullable=False)
    datetime = Column(DateTime, index=True, nullable=False)
    active = Column(Boolean, nullable=False, default=False)
    modulation = Column(Float, nullable=True)
    hours = Column(Float, nullable=True)
    starts = Column(Integer, nullable=True)
    temp_out = Column(Float, nullable=True)
    temp_boiler = Column(Float, nullable=True)
    temp_hotwater = Column(Float, nullable=True)
    temp_hotwater_target = Column(Float, nullable=True)
    temp_heating = Column(Float, nullable=True)
    temp_solcollector = Column(Float, nullable=True)
    temp_solstorage = Column(Float, nullable=True)
    solar_production = Column(Float, nullable=True)
    solar_pump = Column(Boolean, nullable=True)
    circulation_pump = Column(Boolean, nullable=True)
    dhw_pump = Column(Boolean, nullable=True)
    
    def __repr__(self) -> str:
        return f"<HeatingData(timestamp={self.timestamp}, active={self.active})>"


class RawDeviceData(Base):
    """Model for storing raw JSON device data."""
    
    __tablename__ = "raw_device_data"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(Integer, index=True, nullable=False)
    datetime = Column(DateTime, index=True, nullable=False)
    data = Column(String, nullable=False)
    
    def __repr__(self) -> str:
        return f"<RawDeviceData(timestamp={self.timestamp})>" 