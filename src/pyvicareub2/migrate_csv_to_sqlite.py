#!/usr/bin/env python3
"""
Migration script to import CSV data into SQLite database.
"""
import argparse
import logging
import sys
from pathlib import Path

from .config import settings
from .database import DatabaseService

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)
logger = logging.getLogger("ViCareUB2")


def migrate_csv_to_sqlite(csv_path: str = None, db_path: str = None) -> None:
    """Migrate data from CSV to SQLite.
    
    Args:
        csv_path: Path to CSV file. If None, uses settings.data_file.
        db_path: Path to SQLite database. If None, uses settings.database_path.
    """
    csv_path = csv_path or settings.data_file
    db_path = db_path or settings.database_path
    
    # Check if CSV file exists
    if not Path(csv_path).exists():
        logger.error(f"CSV file not found: {csv_path}")
        return
    
    logger.info(f"Starting migration from {csv_path} to {db_path}")
    
    # Initialize database service
    db_service = DatabaseService(db_path)
    
    try:
        # Import data
        total_rows, imported_rows = db_service.import_from_csv(csv_path)
        
        logger.info(f"Migration completed. Processed {total_rows} rows, imported {imported_rows} rows.")
        
        # Check if any rows were imported
        if imported_rows == 0:
            logger.warning("No rows were imported. All rows may already exist in the database.")
    
    except Exception as e:
        logger.error(f"Migration failed: {e}")


def main():
    """Main function for CLI usage."""
    parser = argparse.ArgumentParser(description="Migrate CSV data to SQLite database")
    parser.add_argument(
        "--csv", help="Path to CSV file (default: from settings)", default=None
    )
    parser.add_argument(
        "--db", help="Path to SQLite database (default: from settings)", default=None
    )
    
    args = parser.parse_args()
    
    migrate_csv_to_sqlite(args.csv, args.db)


if __name__ == "__main__":
    main() 