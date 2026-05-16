"""
Database Plugin Package for Aethera

Sub-modules:
    sqlite_connector   - SQLite database plugin
    postgres_connector - PostgreSQL database plugin
    csv_connector      - CSV file database plugin
"""

from .sqlite_connector import SQLiteConnector
from .postgres_connector import PostgresConnector
from .csv_connector import CSVConnector

__all__ = [
    "SQLiteConnector",
    "PostgresConnector",
    "CSVConnector",
]

__version__ = "1.0.0"