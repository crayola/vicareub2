#!/usr/bin/env python3
"""
Command-line interface for database management.
"""
import argparse
import logging
import sys
from pathlib import Path

from .config import settings
from .database import DatabaseService
from .migrate_csv_to_sqlite import migrate_csv_to_sqlite

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)
logger = logging.getLogger("ViCareUB2")


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(description="ViCareUB2 Database Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Migrate command
    migrate_parser = subparsers.add_parser("migrate", help="Migrate data from CSV to SQLite")
    migrate_parser.add_argument(
        "--csv", help="Path to CSV file (default: from settings)", default=None
    )
    migrate_parser.add_argument(
        "--db", help="Path to SQLite database (default: from settings)", default=None
    )
    
    # Info command
    info_parser = subparsers.add_parser("info", help="Show database information")
    info_parser.add_argument(
        "--db", help="Path to SQLite database (default: from settings)", default=None
    )
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export data from SQLite to CSV")
    export_parser.add_argument(
        "--output", help="Path to output CSV file", required=True
    )
    export_parser.add_argument(
        "--db", help="Path to SQLite database (default: from settings)", default=None
    )
    
    args = parser.parse_args()
    
    if args.command == "migrate":
        migrate_csv_to_sqlite(args.csv, args.db)
    
    elif args.command == "info":
        db_path = args.db or settings.database_path
        if not Path(db_path).exists():
            logger.error(f"Database file not found: {db_path}")
            return
        
        db = DatabaseService(db_path)
        with db.get_session() as session:
            from sqlalchemy import func, select
            from .models import HeatingData, RawDeviceData
            
            # Get row counts
            heating_count = session.scalar(select(func.count()).select_from(HeatingData))
            raw_count = session.scalar(select(func.count()).select_from(RawDeviceData))
            
            # Get date range
            if heating_count > 0:
                min_date = session.scalar(select(func.min(HeatingData.datetime)).select_from(HeatingData))
                max_date = session.scalar(select(func.max(HeatingData.datetime)).select_from(HeatingData))
                date_range = f"from {min_date} to {max_date}"
            else:
                date_range = "N/A"
            
            print(f"Database: {db_path}")
            print(f"Heating data records: {heating_count}")
            print(f"Raw device data records: {raw_count}")
            print(f"Date range: {date_range}")
    
    elif args.command == "export":
        db_path = args.db or settings.database_path
        if not Path(db_path).exists():
            logger.error(f"Database file not found: {db_path}")
            return
        
        output_path = args.output
        logger.info(f"Exporting data from {db_path} to {output_path}")
        
        try:
            db = DatabaseService(db_path)
            with db.get_session() as session:
                from sqlalchemy import select
                from .models import HeatingData
                
                # Get all heating data
                result = session.execute(select(HeatingData).order_by(HeatingData.timestamp)).scalars().all()
                
                # Prepare CSV headers
                headers = [
                    "timestamp", "datetime", "active", "modulation", "hours", "starts",
                    "temp_out", "temp_boiler", "temp_hotwater", "temp_hotwater_target",
                    "temp_heating", "temp_solcollector", "temp_solstorage",
                    "solar_production", "solar_pump", "circulation_pump", "dhw_pump"
                ]
                
                # Write to CSV
                with open(output_path, "w") as f:
                    # Write header
                    f.write(",".join(headers) + "\n")
                    
                    # Write data
                    for row in result:
                        values = [
                            str(row.timestamp),
                            str(row.datetime),
                            "1" if row.active else "0",
                            str(row.modulation) if row.modulation is not None else "",
                            str(row.hours) if row.hours is not None else "",
                            str(row.starts) if row.starts is not None else "",
                            str(row.temp_out) if row.temp_out is not None else "",
                            str(row.temp_boiler) if row.temp_boiler is not None else "",
                            str(row.temp_hotwater) if row.temp_hotwater is not None else "",
                            str(row.temp_hotwater_target) if row.temp_hotwater_target is not None else "",
                            str(row.temp_heating) if row.temp_heating is not None else "",
                            str(row.temp_solcollector) if row.temp_solcollector is not None else "",
                            str(row.temp_solstorage) if row.temp_solstorage is not None else "",
                            str(row.solar_production) if row.solar_production is not None else "",
                            "1" if row.solar_pump else "0" if row.solar_pump is not None else "",
                            "1" if row.circulation_pump else "0" if row.circulation_pump is not None else "",
                            "1" if row.dhw_pump else "0" if row.dhw_pump is not None else ""
                        ]
                        f.write(",".join(values) + "\n")
                
                logger.info(f"Exported {len(result)} records to {output_path}")
        
        except Exception as e:
            logger.error(f"Export failed: {e}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()