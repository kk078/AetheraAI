"""
Aethera AI — Stage 3: Data Preprocessing

Normalize, transform, and engineer features on cleaned data.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from .context import DataPipelineContext
from .stages import DataPipelineStage

logger = logging.getLogger("aethera.data_intelligence.preprocessing")


class DataPreprocessingStage(DataPipelineStage):
    """Normalize, transform, and engineer features on cleaned data."""

    name = "preprocessing"

    @property
    def depends_on(self) -> list:
        return ["curation"]

    async def execute(self, context: DataPipelineContext) -> DataPipelineContext:
        rows = context.cleaned_rows or context.rows
        if not rows:
            logger.warning("Preprocessing: no rows to process")
            return context

        options = context.options
        transformations = []

        # 1. Normalize strings
        if options.get("normalize_strings", True):
            rows = self._normalize_strings(rows)
            transformations.append("normalize_strings")

        # 2. Normalize dates
        if options.get("normalize_dates", True):
            rows, count = self._normalize_dates(rows)
            if count > 0:
                transformations.append(f"normalize_dates({count})")

        # 3. One-hot encode categorical columns
        categorical_cols = options.get("one_hot_encode", [])
        if categorical_cols:
            rows = self._one_hot_encode(rows, categorical_cols)
            transformations.append(f"one_hot_encode({len(categorical_cols)})")

        # 4. Bin numeric columns
        bin_cols = options.get("bin_columns", {})
        if bin_cols:
            rows = self._bin_columns(rows, bin_cols)
            transformations.append(f"bin_columns({len(bin_cols)})")

        # 5. Feature engineering
        if options.get("feature_engineering", True):
            rows, features = self._engineer_features(rows)
            transformations.extend(features)

        context.cleaned_rows = rows
        context.transformations_applied = transformations
        logger.info(f"Preprocessing: {len(transformations)} transformations applied")
        return context

    def _normalize_strings(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Strip whitespace, lowercase text columns, standardize casing."""
        for row in rows:
            for key, value in row.items():
                if isinstance(value, str):
                    # Trim whitespace
                    row[key] = value.strip()
        return rows

    def _normalize_dates(self, rows: List[Dict[str, Any]]) -> tuple:
        """Try to normalize date-like strings to ISO format."""
        date_patterns = [
            (re.compile(r'(\d{1,2})/(\d{1,2})/(\d{4})'), r'\3-\1-\2'),   # MM/DD/YYYY
            (re.compile(r'(\d{4})-(\d{1,2})-(\d{1,2})'), None),            # Already ISO
        ]

        normalized = 0
        for row in rows:
            for key, value in row.items():
                if not isinstance(value, str) or not value:
                    continue

                # Try parsing as a date
                for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
                    try:
                        dt = datetime.strptime(value.strip(), fmt)
                        row[key] = dt.strftime("%Y-%m-%d")
                        normalized += 1
                        break
                    except ValueError:
                        continue

        return rows, normalized

    def _one_hot_encode(
        self, rows: List[Dict[str, Any]], columns: List[str]
    ) -> List[Dict[str, Any]]:
        """One-hot encode specified categorical columns."""
        # Find unique values per column
        unique_values = {}
        for col in columns:
            values = set()
            for row in rows:
                if col in row and row[col] is not None:
                    values.add(str(row[col]))
            unique_values[col] = sorted(values)

        # Create new columns
        for row in rows:
            for col in columns:
                if col in unique_values:
                    for val in unique_values[col]:
                        new_col = f"{col}_{val}"
                        row[new_col] = 1 if str(row.get(col)) == val else 0

        return rows

    def _bin_columns(
        self, rows: List[Dict[str, Any]], bin_config: Dict[str, Dict]
    ) -> List[Dict[str, Any]]:
        """Bin numeric columns into discrete categories."""
        for col, config in bin_config.items():
            bins = config.get("bins", 5)
            labels = config.get("labels", None)

            # Get numeric values
            values = []
            for row in rows:
                try:
                    val = float(row.get(col, 0))
                    values.append(val)
                except (ValueError, TypeError):
                    values.append(None)

            # Compute bin edges
            numeric_values = [v for v in values if v is not None]
            if not numeric_values:
                continue

            min_val = min(numeric_values)
            max_val = max(numeric_values)
            bin_width = (max_val - min_val) / bins if bins > 0 else 1

            # Assign bins
            new_col = f"{col}_bin"
            for i, row in enumerate(rows):
                if values[i] is not None:
                    bin_idx = min(int((values[i] - min_val) / bin_width), bins - 1)
                    if labels and bin_idx < len(labels):
                        row[new_col] = labels[bin_idx]
                    else:
                        row[new_col] = f"bin_{bin_idx}"
                else:
                    row[new_col] = None

        return rows

    def _engineer_features(
        self, rows: List[Dict[str, Any]]
    ) -> tuple:
        """Add derived features: text length, word count, date components, numeric ratios."""
        features_applied = []
        headers = list(rows[0].keys()) if rows else []

        # Text length features
        for key in headers:
            sample = rows[0].get(key) if rows else None
            if isinstance(sample, str) and len(sample) > 20:
                new_col = f"{key}_length"
                for row in rows:
                    val = row.get(key, "")
                    row[new_col] = len(str(val)) if val else 0
                features_applied.append(f"text_length({key})")

                # Word count
                word_col = f"{key}_word_count"
                for row in rows:
                    val = row.get(key, "")
                    row[word_col] = len(str(val).split()) if val else 0
                features_applied.append(f"word_count({key})")

        # Date component features
        for key in headers:
            sample = rows[0].get(key) if rows else None
            if isinstance(sample, str) and re.match(r'^\d{4}-\d{2}-\d{2}', str(sample)):
                for row in rows:
                    val = row.get(key, "")
                    try:
                        dt = datetime.strptime(str(val)[:10], "%Y-%m-%d")
                        row[f"{key}_year"] = dt.year
                        row[f"{key}_month"] = dt.month
                    except (ValueError, TypeError):
                        pass
                features_applied.append(f"date_components({key})")

        # Numeric ratio features (between pairs of numeric columns)
        numeric_cols = []
        for key in headers:
            has_numeric = False
            for row in rows[:10]:
                val = row.get(key)
                if val is not None and isinstance(val, (int, float)):
                    has_numeric = True
                    break
            if has_numeric:
                numeric_cols.append(key)

        if len(numeric_cols) >= 2:
            for i in range(min(len(numeric_cols), 3)):
                for j in range(i + 1, min(len(numeric_cols), 4)):
                    col_a, col_b = numeric_cols[i], numeric_cols[j]
                    ratio_col = f"{col_a}_per_{col_b}"
                    for row in rows:
                        a, b = row.get(col_a), row.get(col_b)
                        if a is not None and b is not None and b != 0:
                            try:
                                row[ratio_col] = round(float(a) / float(b), 4)
                            except (TypeError, ValueError):
                                row[ratio_col] = None
                        else:
                            row[ratio_col] = None
                    features_applied.append(f"ratio({col_a}/{col_b})")

        return rows, features_applied