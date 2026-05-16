"""
CSV File Database Connector for Aethera

Provides CSV file operations as a lightweight database: read, write,
filter, sort, aggregate, and join CSV files.
"""
import asyncio
import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class CSVConnector:
    """CSV file database plugin with query-like capabilities."""

    def __init__(self, base_directory: str = ".", delimiter: str = ",", encoding: str = "utf-8"):
        """
        Args:
            base_directory: Default directory for CSV files.
            delimiter:      CSV field delimiter.
            encoding:       File encoding.
        """
        self.base_directory = base_directory
        self.delimiter = delimiter
        self.encoding = encoding

    # -- File I/O ------------------------------------------------------------

    def _resolve_path(self, filename: str) -> str:
        """Resolve a filename to an absolute path."""
        if os.path.isabs(filename):
            return filename
        return os.path.join(self.base_directory, filename)

    async def read_csv(self, filename: str, delimiter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Read a CSV file and return rows as dicts.

        Args:
            filename:  CSV file path (relative to base_directory or absolute).
            delimiter: Override default delimiter.

        Returns:
            List of row dicts (keys from header row).
        """
        path = self._resolve_path(filename)
        delim = delimiter or self.delimiter
        loop = asyncio.get_event_loop()

        def _read():
            with open(path, "r", encoding=self.encoding, newline="") as f:
                reader = csv.DictReader(f, delimiter=delim)
                return [dict(row) for row in reader]

        return await loop.run_in_executor(None, _read)

    async def write_csv(
        self,
        filename: str,
        data: List[Dict[str, Any]],
        delimiter: Optional[str] = None,
        write_header: bool = True,
        mode: str = "w",
    ) -> Dict:
        """Write data to a CSV file.

        Args:
            filename:     CSV file path.
            data:         List of row dicts.
            delimiter:    Override default delimiter.
            write_header: Whether to write the header row.
            mode:         File mode ("w" for overwrite, "a" for append).

        Returns:
            Dict with write stats.
        """
        path = self._resolve_path(filename)
        delim = delimiter or self.delimiter
        loop = asyncio.get_event_loop()

        # Ensure parent directory exists
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        def _write():
            fieldnames = list(data[0].keys()) if data else []
            with open(path, mode, encoding=self.encoding, newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delim)
                if write_header and mode == "w":
                    writer.writeheader()
                writer.writerows(data)
            return len(data)

        count = await loop.run_in_executor(None, _write)
        return {"filename": filename, "rows_written": count}

    # -- Query-like Operations -----------------------------------------------

    async def select(
        self,
        filename: str,
        columns: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        ascending: bool = True,
        limit: int = 0,
        offset: int = 0,
        delimiter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Select rows from a CSV file with filtering and sorting.

        Args:
            filename:  CSV file path.
            columns:   List of column names to select (None = all).
            where:     Dict of column name to value for equality filtering.
            order_by:  Column name to sort by.
            ascending: Sort direction.
            limit:     Maximum rows to return (0 = no limit).
            offset:    Number of rows to skip.
            delimiter: Override default delimiter.

        Returns:
            List of filtered/sorted row dicts.
        """
        rows = await self.read_csv(filename, delimiter)

        # Filter
        if where:
            rows = [
                row for row in rows
                if all(self._compare_values(row.get(k), v) for k, v in where.items())
            ]

        # Sort
        if order_by:
            rows.sort(key=lambda r: self._sort_key(r.get(order_by, "")), reverse=not ascending)

        # Offset and limit
        if offset:
            rows = rows[offset:]
        if limit > 0:
            rows = rows[:limit]

        # Select columns
        if columns:
            rows = [{k: row.get(k) for k in columns if k in row} for row in rows]

        return rows

    async def count(
        self,
        filename: str,
        where: Optional[Dict[str, Any]] = None,
        delimiter: Optional[str] = None,
    ) -> int:
        """Count rows in a CSV file, optionally with filtering.

        Returns:
            Row count.
        """
        rows = await self.select(filename, where=where, delimiter=delimiter)
        return len(rows)

    async def aggregate(
        self,
        filename: str,
        group_by: Optional[str] = None,
        aggregations: Optional[Dict[str, Dict[str, str]]] = None,
        where: Optional[Dict[str, Any]] = None,
        delimiter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Perform aggregation operations on CSV data.

        Args:
            filename:      CSV file path.
            group_by:       Column name to group by.
            aggregations:   Dict mapping output column name to {"column": "...", "function": "sum|avg|min|max|count"}.
            where:          Filter conditions.
            delimiter:      Override default delimiter.

        Returns:
            List of aggregated result dicts.
        """
        rows = await self.select(filename, where=where, delimiter=delimiter)
        if not aggregations:
            return rows

        if not group_by:
            # Aggregate all rows
            result = {}
            for out_name, spec in aggregations.items():
                col = spec["column"]
                func = spec["function"]
                values = [self._to_number(row.get(col, 0)) for row in rows if row.get(col) is not None]
                result[out_name] = self._apply_aggregate(func, values)
            return [result]

        # Group by
        groups: Dict[Any, List[Dict]] = {}
        for row in rows:
            key = row.get(group_by, "")
            if key not in groups:
                groups[key] = []
            groups[key].append(row)

        results = []
        for key, group_rows in groups.items():
            result = {group_by: key}
            for out_name, spec in aggregations.items():
                col = spec["column"]
                func = spec["function"]
                values = [self._to_number(row.get(col, 0)) for row in group_rows if row.get(col) is not None]
                result[out_name] = self._apply_aggregate(func, values)
            results.append(result)

        return results

    async def join(
        self,
        left_filename: str,
        right_filename: str,
        on_column: str,
        join_type: str = "inner",
        left_delimiter: Optional[str] = None,
        right_delimiter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Join two CSV files on a common column.

        Args:
            left_filename:  Left CSV file path.
            right_filename: Right CSV file path.
            on_column:      Column name to join on (must exist in both files).
            join_type:      Join type: "inner", "left", "right", "full".
            left_delimiter:  Delimiter for the left file.
            right_delimiter: Delimiter for the right file.

        Returns:
            List of joined row dicts.
        """
        left_rows = await self.read_csv(left_filename, left_delimiter)
        right_rows = await self.read_csv(right_filename, right_delimiter)

        # Build index on right file
        right_index: Dict[Any, List[Dict]] = {}
        for row in right_rows:
            key = row.get(on_column, "")
            if key not in right_index:
                right_index[key] = []
            right_index[key].append(row)

        results: List[Dict[str, Any]] = []

        # Build left column names (prefix duplicates)
        left_cols = set(left_rows[0].keys()) if left_rows else set()
        right_cols = set(right_rows[0].keys()) if right_rows else set()
        common_cols = left_cols & right_cols - {on_column}

        def merge_rows(left: Dict, right: Optional[Dict]) -> Dict:
            merged = dict(left)
            if right:
                for k, v in right.items():
                    if k == on_column:
                        continue
                    if k in common_cols:
                        merged[f"right_{k}"] = v
                    else:
                        merged[k] = v
            return merged

        # Inner / Left join
        if join_type in ("inner", "left", "full"):
            for left_row in left_rows:
                key = left_row.get(on_column, "")
                if key in right_index:
                    for right_row in right_index[key]:
                        results.append(merge_rows(left_row, right_row))
                elif join_type in ("left", "full"):
                    results.append(merge_rows(left_row, None))

        # Right join: include right rows not matched
        if join_type in ("right", "full"):
            left_keys = {row.get(on_column, "") for row in left_rows}
            for right_row in right_rows:
                key = right_row.get(on_column, "")
                if key not in left_keys:
                    # Merge with empty left
                    merged = {on_column: right_row.get(on_column, "")}
                    for k, v in right_row.items():
                        if k != on_column:
                            merged[k] = v
                    results.append(merged)

        return results

    # -- File Management ----------------------------------------------------

    async def list_files(self, extension: str = ".csv") -> List[Dict[str, Any]]:
        """List CSV files in the base directory.

        Returns:
            List of file info dicts.
        """
        loop = asyncio.get_event_loop()

        def _list():
            result = []
            for f in Path(self.base_directory).glob(f"*{extension}"):
                stat = f.stat()
                result.append({
                    "name": f.name,
                    "path": str(f),
                    "size_bytes": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
            return result

        return await loop.run_in_executor(None, _list)

    async def get_file_info(self, filename: str) -> Dict[str, Any]:
        """Get information about a CSV file.

        Returns:
            Dict with file metadata.
        """
        path = self._resolve_path(filename)
        loop = asyncio.get_event_loop()

        def _info():
            stat = os.stat(path)
            # Count rows
            with open(path, "r", encoding=self.encoding, newline="") as f:
                reader = csv.reader(f, delimiter=self.delimiter)
                header = next(reader, None)
                row_count = sum(1 for _ in reader)
            return {
                "filename": filename,
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "columns": header if header else [],
                "column_count": len(header) if header else 0,
                "row_count": row_count,
            }

        return await loop.run_in_executor(None, _info)

    # -- Import/Export -------------------------------------------------------

    async def to_json(self, filename: str, pretty: bool = True) -> str:
        """Convert a CSV file to JSON.

        Returns:
            JSON string.
        """
        rows = await self.read_csv(filename)
        indent = 2 if pretty else None
        return json.dumps(rows, indent=indent, default=str)

    async def from_json(self, filename: str, json_data: str, delimiter: Optional[str] = None) -> Dict:
        """Convert JSON data to a CSV file.

        Returns:
            Dict with write stats.
        """
        data = json.loads(json_data)
        return await self.write_csv(filename, data, delimiter=delimiter)

    # -- Helper methods -----------------------------------------------------

    @staticmethod
    def _compare_values(row_value: Any, filter_value: Any) -> bool:
        """Compare a row value with a filter value, with type coercion."""
        if row_value == filter_value:
            return True
        # Try numeric comparison
        try:
            return float(row_value) == float(filter_value)
        except (ValueError, TypeError):
            pass
        # String comparison (case-insensitive)
        return str(row_value).strip().lower() == str(filter_value).strip().lower()

    @staticmethod
    def _sort_key(value: Any) -> Any:
        """Create a sort key that handles mixed types."""
        try:
            return float(value)
        except (ValueError, TypeError):
            return str(value)

    @staticmethod
    def _to_number(value: Any) -> float:
        """Convert a value to a number for aggregation."""
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _apply_aggregate(func: str, values: List[float]) -> Optional[float]:
        """Apply an aggregate function to a list of values."""
        if not values:
            return None
        if func == "sum":
            return round(sum(values), 2)
        elif func == "avg":
            return round(sum(values) / len(values), 2)
        elif func == "min":
            return min(values)
        elif func == "max":
            return max(values)
        elif func == "count":
            return float(len(values))
        else:
            raise ValueError(f"Unknown aggregate function: {func}")