"""
PostgreSQL Database Connector for Aethera

Provides PostgreSQL database operations: query, insert, update, delete,
schema management, and transactions via asyncpg.
"""
import asyncio
import json
from typing import Any, Dict, List, Optional, Tuple

import aiohttp


class PostgresConnector:
    """PostgreSQL database plugin using asyncpg for async operations."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "postgres",
        username: str = "postgres",
        password: str = "",
        ssl: str = "prefer",
        min_connections: int = 2,
        max_connections: int = 10,
    ):
        """
        Args:
            host:            PostgreSQL server hostname.
            port:            PostgreSQL server port.
            database:        Database name.
            username:        Authentication username.
            password:        Authentication password.
            ssl:            SSL mode: disable, prefer, require, verify-ca, verify-full.
            min_connections: Minimum pool connections.
            max_connections: Maximum pool connections.
        """
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.ssl = ssl
        self.min_connections = min_connections
        self.max_connections = max_connections
        self._pool = None

    # -- Connection lifecycle ------------------------------------------------

    async def connect(self) -> None:
        """Create a connection pool to PostgreSQL."""
        try:
            import asyncpg
        except ImportError:
            raise ImportError("asyncpg is required for PostgreSQL support. Install with: pip install asyncpg")

        dsn = f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        self._pool = await asyncpg.create_pool(
            dsn=dsn,
            ssl=self.ssl if self.ssl != "disable" else None,
            min_size=self.min_connections,
            max_size=self.max_connections,
        )

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def _ensure_connected(self):
        if self._pool is None:
            await self.connect()
        return self._pool

    # -- Query Execution -----------------------------------------------------

    async def execute(self, query: str, *args: Any) -> str:
        """Execute a single SQL statement.

        Args:
            query: SQL statement.
            *args: Query parameters.

        Returns:
            Status string from PostgreSQL.
        """
        pool = await self._ensure_connected()
        async with pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch_all(self, query: str, *args: Any) -> List[Dict]:
        """Execute a query and fetch all results.

        Returns:
            List of row dicts.
        """
        pool = await self._ensure_connected()
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]

    async def fetch_one(self, query: str, *args: Any) -> Optional[Dict]:
        """Execute a query and fetch a single result.

        Returns:
            Single row dict or None.
        """
        pool = await self._ensure_connected()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None

    async def fetch_value(self, query: str, *args: Any) -> Any:
        """Execute a query and fetch a single value.

        Returns:
            The first column of the first row, or None.
        """
        pool = await self._ensure_connected()
        async with pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    # -- Convenience CRUD ----------------------------------------------------

    async def insert(self, table: str, data: Dict[str, Any]) -> Dict:
        """Insert a row into a table.

        Args:
            table: Table name.
            data:  Dict mapping column names to values.

        Returns:
            Dict with inserted row data.
        """
        columns = list(data.keys())
        values = list(data.values())
        placeholders = ", ".join(f"${i+1}" for i in range(len(columns)))
        col_names = ", ".join(columns)
        query = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) RETURNING *"
        result = await self.fetch_one(query, *values)
        return result or {"inserted": True}

    async def update(self, table: str, data: Dict[str, Any], where: str, *where_args: Any) -> Dict:
        """Update rows in a table.

        Args:
            table:      Table name.
            data:       Dict mapping column names to new values.
            where:      WHERE clause string (use $N placeholders for where_args).
            *where_args: Parameters for the WHERE clause.

        Returns:
            Dict with affected row count.
        """
        offset = len(where_args)
        set_parts = []
        values = list(data.values())
        for i, col in enumerate(data.keys()):
            set_parts.append(f"{col} = ${i + offset + 1}")
        values.extend(where_args)

        set_clause = ", ".join(set_parts)
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"
        status = await self.execute(query, *values)
        # Parse affected rows from status string like "UPDATE 3"
        affected = int(status.split()[-1]) if status else 0
        return {"affected_rows": affected}

    async def delete(self, table: str, where: str, *args: Any) -> Dict:
        """Delete rows from a table.

        Returns:
            Dict with affected row count.
        """
        query = f"DELETE FROM {table} WHERE {where}"
        status = await self.execute(query, *args)
        affected = int(status.split()[-1]) if status else 0
        return {"affected_rows": affected}

    async def upsert(self, table: str, data: Dict[str, Any], conflict_columns: List[str]) -> Dict:
        """Insert a row or update on conflict.

        Args:
            table:            Table name.
            data:             Dict mapping column names to values.
            conflict_columns: List of columns that define the conflict.

        Returns:
            Dict with upsert result.
        """
        columns = list(data.keys())
        values = list(data.values())
        placeholders = ", ".join(f"${i+1}" for i in range(len(columns)))
        col_names = ", ".join(columns)
        conflict = ", ".join(conflict_columns)
        update_cols = [c for c in columns if c not in conflict_columns]
        update_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)

        query = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) ON CONFLICT ({conflict})"
        if update_clause:
            query += f" DO UPDATE SET {update_clause}"
        else:
            query += " DO NOTHING"
        query += " RETURNING *"

        result = await self.fetch_one(query, *values)
        return result or {"upserted": True}

    # -- Table Management ----------------------------------------------------

    async def list_tables(self) -> List[str]:
        """List all user tables in the database.

        Returns:
            List of table names.
        """
        rows = await self.fetch_all(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
            "ORDER BY table_name"
        )
        return [row["table_name"] for row in rows]

    async def get_schema(self, table_name: str) -> List[Dict]:
        """Get column information for a table.

        Returns:
            List of column info dicts.
        """
        return await self.fetch_all(
            "SELECT column_name, data_type, is_nullable, column_default, character_maximum_length "
            "FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = $1 "
            "ORDER BY ordinal_position",
            table_name,
        )

    async def table_exists(self, table_name: str) -> bool:
        """Check if a table exists.

        Returns:
            True if the table exists.
        """
        result = await self.fetch_value(
            "SELECT EXISTS ("
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = $1"
            ")",
            table_name,
        )
        return bool(result)

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
        await self.execute(f"DROP TABLE {exists_clause} {table_name}")
        return {"table": table_name, "status": "dropped"}

    # -- Transactions --------------------------------------------------------

    async def transaction(self, operations: List[Tuple[str, List[Any]]]) -> Dict:
        """Execute multiple operations in a single transaction.

        Args:
            operations: List of (query, args) tuples.

        Returns:
            Dict with results.
        """
        pool = await self._ensure_connected()
        results = []

        async with pool.acquire() as conn:
            async with conn.transaction():
                for query, args in operations:
                    result = await conn.execute(query, *args)
                    results.append(result)

        return {"results": results, "count": len(results)}

    # -- Database Info ------------------------------------------------------

    async def get_database_info(self) -> Dict:
        """Get database information.

        Returns:
            Dict with database metadata.
        """
        tables = await self.list_tables()
        version = await self.fetch_value("SELECT version()")

        size_result = await self.fetch_one(
            "SELECT pg_database_size(current_database()) as size_bytes"
        )
        size_bytes = size_result.get("size_bytes", 0) if size_result else 0

        return {
            "database": self.database,
            "host": self.host,
            "port": self.port,
            "tables": tables,
            "table_count": len(tables),
            "size_bytes": size_bytes,
            "version": version,
        }

    async def export_to_json(self, table_name: str) -> str:
        """Export a table to JSON.

        Returns:
            JSON string of the table data.
        """
        rows = await self.fetch_all(f"SELECT * FROM {table_name}")

        # Convert non-serializable types
        def default_serializer(obj):
            if hasattr(obj, "isoformat"):
                return obj.isoformat()
            if isinstance(obj, (bytes, bytearray)):
                return obj.hex()
            return str(obj)

        return json.dumps(rows, indent=2, default=default_serializer)

    async def import_from_json(self, table_name: str, json_data: str) -> Dict:
        """Import data from JSON into a table.

        Returns:
            Dict with import stats.
        """
        rows = json.loads(json_data)
        inserted = 0
        for row in rows:
            await self.insert(table_name, row)
            inserted += 1
        return {"table": table_name, "rows_imported": inserted}

    # -- Connection test ----------------------------------------------------

    async def test_connection(self) -> Dict:
        """Test the database connection.

        Returns:
            Dict with connection status.
        """
        try:
            result = await self.fetch_value("SELECT 1")
            return {"connected": True, "result": result}
        except Exception as e:
            return {"connected": False, "error": str(e)}