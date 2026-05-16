"""
SQLite Database Connector for Aethera

Provides SQLite database operations: query, insert, update, delete,
schema management, and transactions.
"""
import asyncio
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class SQLiteConnector:
    """SQLite database plugin with async support."""

    def __init__(self, database_path: str = ":memory:", timeout: float = 10.0):
        """
        Args:
            database_path: Path to the SQLite database file. Use ":memory:" for in-memory.
            timeout:       Connection timeout in seconds.
        """
        self.database_path = database_path
        self.timeout = timeout
        self._connection: Optional[sqlite3.Connection] = None

    # -- Connection lifecycle ------------------------------------------------

    async def connect(self) -> None:
        """Open a connection to the SQLite database."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._connect_sync)

    def _connect_sync(self) -> None:
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(
            self.database_path,
            timeout=self.timeout,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA foreign_keys=ON")

    async def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._close_sync)

    def _close_sync(self) -> None:
        if self._connection:
            self._connection.close()
            self._connection = None

    async def _ensure_connected(self) -> sqlite3.Connection:
        if self._connection is None:
            await self.connect()
        return self._connection

    # -- Query Execution -----------------------------------------------------

    async def execute(self, query: str, params: Optional[Tuple] = None) -> Dict:
        """Execute a single SQL statement.

        Args:
            query: SQL statement.
            params: Query parameters.

        Returns:
            Dict with keys: affected_rows, lastrowid.
        """
        conn = await self._ensure_connected()
        loop = asyncio.get_event_loop()

        def _exec():
            cursor = conn.execute(query, params or ())
            conn.commit()
            return cursor.rowcount, cursor.lastrowid

        affected, lastrowid = await loop.run_in_executor(None, _exec)
        return {"affected_rows": affected, "lastrowid": lastrowid}

    async def execute_many(self, query: str, params_list: List[Tuple]) -> Dict:
        """Execute a SQL statement with multiple parameter sets.

        Args:
            query:      SQL statement with placeholders.
            params_list: List of parameter tuples.

        Returns:
            Dict with keys: affected_rows.
        """
        conn = await self._ensure_connected()
        loop = asyncio.get_event_loop()

        def _exec():
            cursor = conn.executemany(query, params_list)
            conn.commit()
            return cursor.rowcount

        affected = await loop.run_in_executor(None, _exec)
        return {"affected_rows": affected}

    async def fetch_all(self, query: str, params: Optional[Tuple] = None) -> List[Dict]:
        """Execute a query and fetch all results.

        Args:
            query:  SQL SELECT statement.
            params: Query parameters.

        Returns:
            List of row dicts.
        """
        conn = await self._ensure_connected()
        loop = asyncio.get_event_loop()

        def _fetch():
            cursor = conn.execute(query, params or ())
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        return await loop.run_in_executor(None, _fetch)

    async def fetch_one(self, query: str, params: Optional[Tuple] = None) -> Optional[Dict]:
        """Execute a query and fetch a single result.

        Returns:
            Single row dict or None.
        """
        conn = await self._ensure_connected()
        loop = asyncio.get_event_loop()

        def _fetch():
            cursor = conn.execute(query, params or ())
            row = cursor.fetchone()
            return dict(row) if row else None

        return await loop.run_in_executor(None, _fetch)

    async def fetch_value(self, query: str, params: Optional[Tuple] = None) -> Any:
        """Execute a query and fetch a single value.

        Returns:
            The first column of the first row, or None.
        """
        result = await self.fetch_one(query, params)
        if result:
            return list(result.values())[0]
        return None

    # -- Table Management ----------------------------------------------------

    async def list_tables(self) -> List[str]:
        """List all tables in the database.

        Returns:
            List of table names.
        """
        rows = await self.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        return [row["name"] for row in rows]

    async def get_schema(self, table_name: str) -> List[Dict]:
        """Get the schema for a table.

        Returns:
            List of column dicts with keys: cid, name, type, notnull, dflt_value, pk.
        """
        return await self.fetch_all(f"PRAGMA table_info({table_name})")

    async def table_exists(self, table_name: str) -> bool:
        """Check if a table exists.

        Returns:
            True if the table exists.
        """
        result = await self.fetch_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        return result is not None

    async def create_table(self, table_name: str, columns: Dict[str, str], if_not_exists: bool = True) -> Dict:
        """Create a table.

        Args:
            table_name:     Table name.
            columns:        Dict mapping column names to SQL type strings.
            if_not_exists:  Add IF NOT EXISTS clause.

        Returns:
            Dict with table name and status.
        """
        exists_clause = "IF NOT EXISTS " if if_not_exists else ""
        cols = ", ".join(f"{name} {type_str}" for name, type_str in columns.items())
        query = f"CREATE TABLE {exists_clause}{table_name} ({cols})"
        await self.execute(query)
        return {"table": table_name, "status": "created"}

    async def drop_table(self, table_name: str, if_exists: bool = True) -> Dict:
        """Drop a table.

        Returns:
            Dict with table name and status.
        """
        exists_clause = "IF EXISTS " if if_exists else ""
        await self.execute(f"DROP TABLE {exists_clause}{table_name}")
        return {"table": table_name, "status": "dropped"}

    # -- Convenience CRUD ----------------------------------------------------

    async def insert(self, table: str, data: Dict[str, Any]) -> Dict:
        """Insert a row into a table.

        Args:
            table: Table name.
            data:  Dict mapping column names to values.

        Returns:
            Dict with lastrowid.
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        values = tuple(data.values())
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        return await self.execute(query, values)

    async def update(self, table: str, data: Dict[str, Any], where: str, where_params: Optional[Tuple] = None) -> Dict:
        """Update rows in a table.

        Args:
            table:         Table name.
            data:          Dict mapping column names to new values.
            where:         WHERE clause string.
            where_params:  Parameters for the WHERE clause.

        Returns:
            Dict with affected_rows.
        """
        set_clause = ", ".join(f"{col} = ?" for col in data.keys())
        values = tuple(data.values())
        if where_params:
            values = values + where_params
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"
        return await self.execute(query, values)

    async def delete(self, table: str, where: str, params: Optional[Tuple] = None) -> Dict:
        """Delete rows from a table.

        Args:
            table:  Table name.
            where: WHERE clause string.
            params: Parameters for the WHERE clause.

        Returns:
            Dict with affected_rows.
        """
        query = f"DELETE FROM {table} WHERE {where}"
        return await self.execute(query, params)

    # -- Transactions --------------------------------------------------------

    async def begin_transaction(self) -> None:
        """Begin a transaction."""
        conn = await self._ensure_connected()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: conn.execute("BEGIN"))

    async def commit(self) -> None:
        """Commit the current transaction."""
        conn = await self._ensure_connected()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, conn.commit)

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        conn = await self._ensure_connected()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, conn.rollback)

    async def transaction(self, operations: List[Tuple[str, Optional[Tuple]]]) -> Dict:
        """Execute multiple operations in a single transaction.

        Args:
            operations: List of (query, params) tuples.

        Returns:
            Dict with total affected_rows and results.
        """
        conn = await self._ensure_connected()
        loop = asyncio.get_event_loop()

        def _transaction():
            total_affected = 0
            results = []
            try:
                conn.execute("BEGIN")
                for query, params in operations:
                    cursor = conn.execute(query, params or ())
                    total_affected += cursor.rowcount
                    results.append({"affected_rows": cursor.rowcount, "lastrowid": cursor.lastrowid})
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e
            return total_affected, results

        total, results = await loop.run_in_executor(None, _transaction)
        return {"total_affected_rows": total, "results": results}

    # -- Database Info ------------------------------------------------------

    async def get_database_info(self) -> Dict:
        """Get database information.

        Returns:
            Dict with database metadata.
        """
        tables = await self.list_tables()
        page_count = await self.fetch_value("PRAGMA page_count")
        page_size = await self.fetch_value("PRAGMA page_size")
        size_bytes = (page_count or 0) * (page_size or 0)

        return {
            "database_path": self.database_path,
            "tables": tables,
            "table_count": len(tables),
            "size_bytes": size_bytes,
            "journal_mode": await self.fetch_value("PRAGMA journal_mode"),
            "foreign_keys_enabled": bool(await self.fetch_value("PRAGMA foreign_keys")),
        }

    async def export_to_json(self, table_name: str) -> str:
        """Export a table to JSON.

        Returns:
            JSON string of the table data.
        """
        rows = await self.fetch_all(f"SELECT * FROM {table_name}")
        return json.dumps(rows, indent=2, default=str)

    async def import_from_json(self, table_name: str, json_data: str) -> Dict:
        """Import data into a table from JSON.

        Args:
            table_name: Target table name.
            json_data:  JSON string of row dicts.

        Returns:
            Dict with import stats.
        """
        rows = json.loads(json_data)
        inserted = 0
        for row in rows:
            await self.insert(table_name, row)
            inserted += 1
        return {"table": table_name, "rows_imported": inserted}