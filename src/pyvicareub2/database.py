"""
Database service for ViCareUB2.
Provides connection management and data access functions.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pandas as pd
from pytz import utc
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import settings
from .models import Base, HeatingData, RawDeviceData

logger = logging.getLogger("ViCareUB2")


class DatabaseService:
    """Provides database operations for the application."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize the database service.

        Args:
            db_path: Optional path to the SQLite database file.
                    If not provided, uses the path from settings.
        """
        self.db_path = db_path or settings.database_path
        self._engine: Optional[Engine] = None
        self._session_factory = None

        # Ensure the database directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    @property
    def engine(self) -> Engine:
        """Get the SQLAlchemy engine."""
        if self._engine is None:
            self._engine = create_engine(f"sqlite:///{self.db_path}", echo=False)
            Base.metadata.create_all(self._engine)
            self._session_factory = sessionmaker(bind=self._engine)
        return self._engine

    def get_session(self) -> Session:
        """Get a new database session."""
        if self._session_factory is None:
            _ = self.engine  # Initialize engine and session factory
        return self._session_factory()

    def save_heating_data(self, data: Dict[str, Any]) -> None:
        """Save heating data to the database.

        Args:
            data: Dictionary containing heating system data.
        """
        try:
            # Convert boolean fields
            active = bool(int(data.get("active", 0)))
            solar_pump = bool(int(data.get("solar_pump", 0))) if "solar_pump" in data else None
            circulation_pump = (
                bool(int(data.get("circulation_pump", 0))) if "circulation_pump" in data else None
            )
            dhw_pump = bool(int(data.get("dhw_pump", 0))) if "dhw_pump" in data else None

            # Create new HeatingData object
            heating_data = HeatingData(
                timestamp=int(data["timestamp"]),
                datetime=datetime.fromtimestamp(int(data["timestamp"])),
                active=active,
                modulation=float(data.get("modulation")) if "modulation" in data else None,
                hours=float(data.get("hours")) if "hours" in data else None,
                starts=int(data.get("starts")) if "starts" in data else None,
                temp_out=float(data.get("temp_out")) if "temp_out" in data else None,
                temp_boiler=float(data.get("temp_boiler")) if "temp_boiler" in data else None,
                temp_hotwater=float(data.get("temp_hotwater")) if "temp_hotwater" in data else None,
                temp_hotwater_target=float(data.get("temp_hotwater_target"))
                if "temp_hotwater_target" in data
                else None,
                temp_heating=float(data.get("temp_heating")) if "temp_heating" in data else None,
                temp_solcollector=float(data.get("temp_solcollector"))
                if "temp_solcollector" in data
                else None,
                temp_solstorage=float(data.get("temp_solstorage"))
                if "temp_solstorage" in data
                else None,
                solar_production=float(data.get("solar_production"))
                if "solar_production" in data
                else None,
                solar_pump=solar_pump,
                circulation_pump=circulation_pump,
                dhw_pump=dhw_pump,
            )

            with self.get_session() as session:
                session.add(heating_data)
                session.commit()

            logger.debug(
                f"Successfully saved heating data at {datetime.fromtimestamp(data['timestamp'])}"
            )
        except Exception as e:
            logger.error(f"Failed to save heating data: {e}")
            raise

    def save_raw_device_data(self, data: Dict[str, Any]) -> None:
        """Save raw device data to the database.

        Args:
            data: Dictionary containing raw device data.
        """
        try:
            timestamp = int(datetime.now().timestamp())

            raw_data = RawDeviceData(
                timestamp=timestamp,
                datetime=datetime.fromtimestamp(timestamp),
                data=json.dumps(data),
            )

            with self.get_session() as session:
                session.add(raw_data)
                session.commit()

            logger.debug(f"Successfully saved raw device data at {datetime.now()}")
        except Exception as e:
            logger.error(f"Failed to save raw device data: {e}")
            raise

    def get_data_for_plotting(self, days: int = 2) -> pd.DataFrame:
        """Get and prepare data for plotting.

        Args:
            days: Number of days of data to retrieve.

        Returns:
            DataFrame ready for plotting.
        """
        try:
            with self.get_session() as session:
                # Get data from the last 'days' days
                cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
                stmt = (
                    select(HeatingData)
                    .where(HeatingData.timestamp >= cutoff_time)
                    .order_by(HeatingData.timestamp)
                )
                result = session.execute(stmt).scalars().all()

                if not result:
                    logger.warning(f"No data found for the last {days} days")
                    return pd.DataFrame()

                # Convert to DataFrame
                data = []
                for row in result:
                    data.append(
                        {
                            "timestamp": row.timestamp,
                            "time": row.datetime,
                            "active": int(row.active),
                            "modulation": row.modulation,
                            "hours": row.hours,
                            "starts": row.starts,
                            "temp_out": row.temp_out,
                            "temp_boiler": row.temp_boiler,
                            "temp_hotwater": row.temp_hotwater,
                            "temp_hotwater_target": row.temp_hotwater_target,
                            "temp_heating": row.temp_heating,
                            "temp_solcollector": row.temp_solcollector,
                            "temp_solstorage": row.temp_solstorage,
                            "solar_production": row.solar_production,
                            "solar_pump": int(row.solar_pump)
                            if row.solar_pump is not None
                            else None,
                            "circulation_pump": int(row.circulation_pump)
                            if row.circulation_pump is not None
                            else None,
                            "dhw_pump": int(row.dhw_pump) if row.dhw_pump is not None else None,
                        }
                    )

                bdf = pd.DataFrame(data)
                bdf["time"] = bdf["time"].dt.tz_localize(tz=utc)

                # Normalize data
                if not bdf.empty:
                    if "hours" in bdf.columns and not bdf["hours"].isna().all():
                        bdf["hours"] = bdf["hours"] - bdf["hours"].min()

                    if "modulation" in bdf.columns and not bdf["modulation"].isna().all():
                        bdf["modulation"] = 2 + bdf["modulation"] / 50

                    if (
                        "starts" in bdf.columns
                        and not bdf["starts"].isna().all()
                        and bdf["starts"].max() > 0
                    ):
                        bdf["starts"] = bdf["starts"] - bdf["starts"].min()
                        bdf["starts"] = 10 * (bdf["starts"] / bdf["starts"].max())

                # Clean data
                bdf = bdf[~bdf.temp_heating.isna()]
                if not isinstance(bdf, pd.DataFrame):
                    raise ValueError("Invalid DataFrame")

                # Melt for plotting
                return bdf.melt(id_vars="time")

        except Exception as e:
            logger.exception(f"Failed to prepare data for plotting: {e}")
            raise

    def import_from_csv(self, csv_path: str) -> Tuple[int, int]:
        """Import data from CSV file to the database.

        Args:
            csv_path: Path to the CSV file.

        Returns:
            Tuple of (total_rows, imported_rows)
        """
        try:
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

            df = pd.read_csv(csv_path, names=colnames, low_memory=False)
            total_rows = len(df)

            # Check for existing data to avoid duplicates
            existing_timestamps = set()
            with self.get_session() as session:
                result = session.execute(select(HeatingData.timestamp)).scalars().all()
                existing_timestamps = set(result)

            # Filter out rows that already exist in the database
            df = df[~df["timestamp"].isin(existing_timestamps)]

            imported_rows = 0
            with self.get_session() as session:
                for _, row in df.iterrows():
                    try:
                        # Convert values as needed
                        active = bool(int(row.get("active", 0)))
                        solar_pump = (
                            bool(int(row.get("solar_pump", 0)))
                            if pd.notna(row.get("solar_pump"))
                            else None
                        )
                        circulation_pump = (
                            bool(int(row.get("circulation_pump", 0)))
                            if pd.notna(row.get("circulation_pump"))
                            else None
                        )
                        dhw_pump = (
                            bool(int(row.get("dhw_pump", 0)))
                            if pd.notna(row.get("dhw_pump"))
                            else None
                        )

                        data = HeatingData(
                            timestamp=int(row["timestamp"]),
                            datetime=datetime.fromtimestamp(int(row["timestamp"])),
                            active=active,
                            modulation=float(row["modulation"])
                            if pd.notna(row["modulation"])
                            else None,
                            hours=float(row["hours"]) if pd.notna(row["hours"]) else None,
                            starts=int(row["starts"]) if pd.notna(row["starts"]) else None,
                            temp_out=float(row["temp_out"]) if pd.notna(row["temp_out"]) else None,
                            temp_boiler=float(row["temp_boiler"])
                            if pd.notna(row["temp_boiler"])
                            else None,
                            temp_hotwater=float(row["temp_hotwater"])
                            if pd.notna(row["temp_hotwater"])
                            else None,
                            temp_hotwater_target=float(row["temp_hotwater_target"])
                            if pd.notna(row["temp_hotwater_target"])
                            else None,
                            temp_heating=float(row["temp_heating"])
                            if pd.notna(row["temp_heating"])
                            else None,
                            temp_solcollector=float(row["temp_solcollector"])
                            if pd.notna(row["temp_solcollector"])
                            else None,
                            temp_solstorage=float(row["temp_solstorage"])
                            if pd.notna(row["temp_solstorage"])
                            else None,
                            solar_production=float(row["solar_production"])
                            if pd.notna(row["solar_production"])
                            else None,
                            solar_pump=solar_pump,
                            circulation_pump=circulation_pump,
                            dhw_pump=dhw_pump,
                        )
                        session.add(data)
                        imported_rows += 1

                        # Commit in batches to improve performance
                        if imported_rows % 100 == 0:
                            session.commit()
                    except Exception as e:
                        logger.error(f"Error importing row {row['timestamp']}: {e}")

                # Final commit for any remaining rows
                session.commit()

            logger.info(f"Imported {imported_rows} rows from CSV (total rows: {total_rows})")
            return total_rows, imported_rows

        except Exception as e:
            logger.error(f"Failed to import from CSV: {e}")
            raise
