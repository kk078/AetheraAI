"""
Aethera AI — Stage 5: Auto-Schema Detection

Infers column types, primary keys, foreign keys, nullable columns,
and constraints from data. Optionally indexes schema profiles
into ChromaDB for similarity search.
"""

import logging
import re
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .context import DataPipelineContext
from .stages import DataPipelineStage
from .llm import DataIntelligenceLLM

logger = logging.getLogger("aethera.data_intelligence.schema_detect")

# Type detection thresholds
TYPE_PATTERNS = {
    "email": re.compile(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'),
    "url": re.compile(r'^https?://'),
    "phone": re.compile(r'^\+?\d[\d\s\-\(\)]{7,}$'),
    "zip_code": re.compile(r'^\d{5}(-\d{4})?$'),
}


class AutoSchemaDetectionStage(DataPipelineStage):
    """Infer schema from data: column types, keys, constraints."""

    name = "schema_detect"

    @property
    def depends_on(self) -> list:
        return ["curation"]

    async def execute(self, context: DataPipelineContext) -> DataPipelineContext:
        rows = context.cleaned_rows or context.rows
        if not rows:
            logger.warning("Schema detection: no rows to analyze")
            return context

        headers = context.headers or list(rows[0].keys())
        sample_size = context.options.get("schema_sample_size", 1000)
        sample = rows[:sample_size]

        # Detect column types
        columns = []
        for header in headers:
            col_info = self._detect_column_type(header, sample)
            columns.append(col_info)

        # Detect primary key candidates
        primary_keys = self._detect_primary_keys(headers, rows, columns)

        # Detect foreign key candidates
        foreign_keys = self._detect_foreign_keys(headers, rows, columns)

        # Build schema info
        schema_info = {
            "columns": columns,
            "primary_key_candidates": primary_keys,
            "foreign_key_hints": foreign_keys,
            "total_rows": len(rows),
            "total_columns": len(headers),
        }

        # LLM-assisted schema detection (optional)
        use_llm = context.options.get("use_llm_for_schema", False)
        if use_llm:
            llm_schema = await self._llm_schema_detect(sample, headers)
            if llm_schema:
                # Merge LLM results with heuristic results
                for i, col in enumerate(schema_info["columns"]):
                    if i < len(llm_schema.get("columns", [])):
                        llm_col = llm_schema["columns"][i]
                        if llm_col.get("description"):
                            col["description"] = llm_col["description"]
                if llm_schema.get("primary_key_candidates"):
                    schema_info["primary_key_candidates"] = llm_schema["primary_key_candidates"]

        context.schema_info = schema_info
        context.detected_primary_key = primary_keys[0] if primary_keys else None
        context.detected_foreign_keys = foreign_keys

        # Update dataset store with schema
        store = self._get_store()
        if store and context.dataset_id:
            store.update_dataset(
                context.dataset_id,
                schema_json=schema_info,
                column_count=len(headers),
                row_count=len(rows),
            )

        # Optionally index in VectorStore
        if context.options.get("index_in_vectorstore", False):
            self._index_schema(context, schema_info)

        logger.info(f"Schema detection: {len(columns)} columns, "
                     f"primary_keys={primary_keys}, foreign_keys={len(foreign_keys)}")
        return context

    def _detect_column_type(self, header: str, rows: List[Dict]) -> Dict[str, Any]:
        """Detect the type and properties of a single column."""
        values = [row.get(header) for row in rows if row.get(header) is not None]
        total = len(rows)
        non_null = len(values)
        null_count = total - non_null
        nullable = null_count > 0

        if not values:
            return {
                "name": header,
                "type": "null",
                "nullable": True,
                "null_count": null_count,
                "unique_values": 0,
                "sample_values": [],
            }

        # Type inference
        type_counts = Counter()
        for v in values[:200]:
            type_counts[self._infer_type(v)] += 1

        # Dominant type
        dominant_type = type_counts.most_common(1)[0][0] if type_counts else "string"

        # Check for special types
        if dominant_type == "string" and values:
            email_count = sum(1 for v in values[:100] if TYPE_PATTERNS["email"].match(str(v)))
            url_count = sum(1 for v in values[:100] if TYPE_PATTERNS["url"].match(str(v)))
            phone_count = sum(1 for v in values[:100] if TYPE_PATTERNS["phone"].match(str(v)))

            if email_count > len(values[:100]) * 0.5:
                dominant_type = "email"
            elif url_count > len(values[:100]) * 0.5:
                dominant_type = "url"
            elif phone_count > len(values[:100]) * 0.5:
                dominant_type = "phone"

        # Check for categorical (low cardinality relative to row count)
        unique_values = len(set(str(v) for v in values))
        is_categorical = dominant_type == "string" and unique_values <= min(20, len(values) * 0.05)

        # Sample values
        sample_values = list(set(str(v) for v in values[:5]))[:5]

        # Default value (most common)
        most_common = Counter(str(v) for v in values).most_common(1)
        default_value = most_common[0][0] if most_common else None

        return {
            "name": header,
            "type": "categorical" if is_categorical else dominant_type,
            "nullable": nullable,
            "null_count": null_count,
            "unique_values": unique_values,
            "sample_values": sample_values,
            "default_value": default_value,
        }

    def _infer_type(self, value: Any) -> str:
        """Infer the type of a single value."""
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "float"

        s = str(value).strip()

        # Try integer
        try:
            int(s)
            return "integer"
        except ValueError:
            pass

        # Try float
        try:
            float(s)
            return "float"
        except ValueError:
            pass

        # Try date
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y"):
            try:
                datetime.strptime(s[:10], fmt)
                return "date"
            except ValueError:
                continue

        # Try boolean
        if s.lower() in ("true", "false", "yes", "no", "1", "0"):
            return "boolean"

        return "string"

    def _detect_primary_keys(
        self, headers: List[str], rows: List[Dict], columns: List[Dict]
    ) -> List[str]:
        """Find columns that could serve as primary keys (unique + non-null)."""
        candidates = []
        for col in columns:
            if col["null_count"] > 0:
                continue  # Primary keys must be non-null
            if col["unique_values"] == len(rows):
                candidates.append(col["name"])
        return candidates

    def _detect_foreign_keys(
        self, headers: List[str], rows: List[Dict], columns: List[Dict]
    ) -> List[Dict[str, str]]:
        """Find columns whose values are a subset of another column's values (foreign key hints)."""
        foreign_keys = []

        # Build value sets for each column
        value_sets = {}
        for col in columns:
            values = set(str(row.get(col["name"], "")) for row in rows if row.get(col["name"]) is not None)
            value_sets[col["name"]] = values

        # Check if one column's values are a subset of another
        for i, col_a in enumerate(columns):
            if col_a["unique_values"] < 5 or col_a["unique_values"] > len(rows) * 0.5:
                continue  # Skip low/high cardinality

            for j, col_b in enumerate(columns):
                if i >= j:
                    continue
                if col_b["unique_values"] < 5:
                    continue

                set_a = value_sets[col_a["name"]]
                set_b = value_sets[col_b["name"]]

                # If smaller set is mostly a subset of larger set
                if len(set_a) < len(set_b):
                    overlap = len(set_a & set_b) / max(len(set_a), 1)
                    if overlap > 0.9:
                        foreign_keys.append({
                            "column": col_a["name"],
                            "references": col_b["name"],
                            "confidence": round(overlap, 3),
                        })
                elif len(set_b) < len(set_a):
                    overlap = len(set_a & set_b) / max(len(set_b), 1)
                    if overlap > 0.9:
                        foreign_keys.append({
                            "column": col_b["name"],
                            "references": col_a["name"],
                            "confidence": round(overlap, 3),
                        })

        return foreign_keys[:5]  # Limit to top 5

    async def _llm_schema_detect(
        self, sample: List[Dict], headers: List[str]
    ) -> Optional[Dict]:
        """Use LLM for schema detection."""
        llm = DataIntelligenceLLM()
        try:
            return await llm.detect_schema(sample, headers)
        except Exception as e:
            logger.warning(f"LLM schema detection failed: {e}")
            return None

    def _index_schema(self, context: DataPipelineContext, schema_info: Dict):
        """Optionally index the schema profile into ChromaDB."""
        try:
            from memory.vector_store import get_vector_store
            vs = get_vector_store()
            # Store schema as a searchable document
            schema_text = f"Dataset: {context.name}. Columns: "
            schema_text += ", ".join(
                f"{col['name']}({col['type']})" for col in schema_info.get("columns", [])
            )
            vs.add_document(
                collection="data_schemas",
                content=schema_text,
                metadata={
                    "dataset_id": context.dataset_id,
                    "dataset_name": context.name,
                    "column_count": len(schema_info.get("columns", [])),
                    "row_count": schema_info.get("total_rows", 0),
                    "primary_keys": ",".join(schema_info.get("primary_key_candidates", [])),
                },
                doc_id=f"schema_{context.dataset_id}",
            )
        except Exception as e:
            logger.debug(f"Schema indexing failed (non-critical): {e}")

    def _get_store(self):
        """Lazy-load the dataset store."""
        try:
            from .store import get_dataset_store
            return get_dataset_store()
        except Exception:
            return None