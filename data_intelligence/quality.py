"""
Aethera AI — Stage 4: Data Quality Scoring

Scores datasets on completeness, accuracy, consistency, and timeliness.
Overall score is a weighted average of the four dimensions.
"""

import logging
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional

from .context import DataPipelineContext
from .stages import DataPipelineStage

logger = logging.getLogger("aethera.data_intelligence.quality")

# Default weights for overall score
DEFAULT_WEIGHTS = {
    "completeness": 0.30,
    "accuracy": 0.30,
    "consistency": 0.25,
    "timeliness": 0.15,
}


class DataQualityScoringStage(DataPipelineStage):
    """Score data quality on completeness, accuracy, consistency, timeliness."""

    name = "quality"

    @property
    def depends_on(self) -> list:
        return ["curation"]

    async def execute(self, context: DataPipelineContext) -> DataPipelineContext:
        rows = context.cleaned_rows or context.rows
        if not rows:
            logger.warning("Quality: no rows to score")
            return context

        headers = context.headers or (list(rows[0].keys()) if rows else [])

        # Compute individual scores
        completeness = self._score_completeness(rows, headers)
        accuracy = self._score_accuracy(rows, headers)
        consistency = self._score_consistency(rows, headers)
        timeliness = self._score_timeliness(rows, headers)

        # Overall weighted score
        weights = context.options.get("quality_weights", DEFAULT_WEIGHTS)
        overall = (
            completeness * weights.get("completeness", 0.30)
            + accuracy * weights.get("accuracy", 0.30)
            + consistency * weights.get("consistency", 0.25)
            + timeliness * weights.get("timeliness", 0.15)
        )

        # Build details
        details = {
            "completeness": self._completeness_details(rows, headers),
            "accuracy": self._accuracy_details(rows, headers),
            "consistency": self._consistency_details(rows, headers),
            "timeliness": self._timeliness_details(rows, headers),
            "row_count": len(rows),
            "column_count": len(headers),
        }

        context.quality_scores = {
            "completeness": round(completeness, 4),
            "accuracy": round(accuracy, 4),
            "consistency": round(consistency, 4),
            "timeliness": round(timeliness, 4),
            "overall": round(overall, 4),
        }
        context.quality_details = details

        # Persist to store (non-fatal — scores are still computed in context)
        store = self._get_store()
        if store and context.dataset_id:
            try:
                version_id = context.version_id or None
                store.store_quality_score(
                    dataset_id=context.dataset_id,
                    completeness=completeness,
                    accuracy=accuracy,
                    consistency=consistency,
                    timeliness=timeliness,
                    overall=overall,
                    version_id=version_id,
                    details=details,
                )
            except Exception as e:
                logger.debug(f"Failed to persist quality scores: {e}")

        logger.info(f"Quality: overall={overall:.3f} (C={completeness:.3f} A={accuracy:.3f} "
                     f"Co={consistency:.3f} T={timeliness:.3f})")
        return context

    def _score_completeness(self, rows: List[Dict], headers: List[str]) -> float:
        """Fraction of non-null values across all cells."""
        if not rows or not headers:
            return 0.0

        total_cells = len(rows) * len(headers)
        null_cells = 0

        for row in rows:
            for h in headers:
                if row.get(h) is None or str(row.get(h, "")).strip() == "":
                    null_cells += 1

        return 1.0 - (null_cells / max(total_cells, 1))

    def _completeness_details(self, rows: List[Dict], headers: List[str]) -> Dict:
        """Per-column completeness breakdown."""
        details = {}
        for h in headers:
            null_count = sum(1 for row in rows if row.get(h) is None or str(row.get(h, "")).strip() == "")
            details[h] = {
                "null_count": null_count,
                "total": len(rows),
                "completeness": round(1.0 - null_count / max(len(rows), 1), 4),
            }
        return details

    def _score_accuracy(self, rows: List[Dict], headers: List[str]) -> float:
        """Check type consistency and plausible ranges."""
        if not rows or not headers:
            return 0.0

        column_scores = []
        for h in headers:
            values = [row.get(h) for row in rows if row.get(h) is not None]
            if not values:
                column_scores.append(1.0)  # All-null columns don't penalize accuracy
                continue

            # Check type homogeneity
            types = set()
            for v in values[:100]:
                types.add(type(v).__name__)

            # If all same type, score 1.0; if mixed, score lower
            if len(types) <= 1:
                type_score = 1.0
            elif len(types) == 2 and {"int", "float"} == types:
                type_score = 0.95  # int/float mix is OK
            else:
                type_score = max(0.5, 1.0 - 0.2 * (len(types) - 1))

            # Check numeric range plausibility
            numeric_vals = [v for v in values if isinstance(v, (int, float))]
            range_score = 1.0
            if numeric_vals:
                avg = sum(numeric_vals) / len(numeric_vals)
                std = (sum((x - avg) ** 2 for x in numeric_vals) / len(numeric_vals)) ** 0.5 if len(numeric_vals) > 1 else 0
                outliers = sum(1 for x in numeric_vals if std > 0 and abs(x - avg) > 3 * std)
                outlier_rate = outliers / len(numeric_vals)
                range_score = 1.0 - min(outlier_rate, 1.0)

            column_scores.append(0.6 * type_score + 0.4 * range_score)

        return sum(column_scores) / max(len(column_scores), 1)

    def _accuracy_details(self, rows: List[Dict], headers: List[str]) -> Dict:
        """Per-column accuracy details."""
        details = {}
        for h in headers:
            values = [row.get(h) for row in rows if row.get(h) is not None]
            if not values:
                details[h] = {"type": "null", "type_homogeneity": 1.0}
                continue

            types = Counter(type(v).__name__ for v in values[:100])
            dominant_type = types.most_common(1)[0][0]
            type_homogeneity = types.most_common(1)[0][1] / max(len(values[:100]), 1)

            details[h] = {
                "type": dominant_type,
                "type_homogeneity": round(type_homogeneity, 4),
                "unique_values": len(set(str(v) for v in values[:100])),
            }
        return details

    def _score_consistency(self, rows: List[Dict], headers: List[str]) -> float:
        """Check format consistency and duplicate keys."""
        if not rows or not headers:
            return 0.0

        scores = []

        # Format consistency: check if string columns have consistent casing/format
        for h in headers:
            str_values = [str(row.get(h, "")) for row in rows if isinstance(row.get(h), str)]
            if len(str_values) < 2:
                continue

            # Casing consistency
            lower_count = sum(1 for v in str_values[:200] if v and v[0].islower())
            upper_count = sum(1 for v in str_values[:200] if v and v[0].isupper())
            total = lower_count + upper_count

            if total > 0:
                casing_consistency = max(lower_count, upper_count) / total
                scores.append(casing_consistency)

        # Duplicate primary key check (first column as candidate)
        if headers:
            key_values = [str(row.get(headers[0], "")) for row in rows]
            unique_keys = len(set(key_values))
            total_keys = len(key_values)
            if total_keys > 0:
                key_uniqueness = unique_keys / total_keys
                scores.append(key_uniqueness)

        return sum(scores) / max(len(scores), 1) if scores else 1.0

    def _consistency_details(self, rows: List[Dict], headers: List[str]) -> Dict:
        """Consistency details."""
        details = {}

        # Key uniqueness
        if headers:
            key_values = [str(row.get(headers[0], "")) for row in rows]
            details["key_uniqueness"] = len(set(key_values)) / max(len(key_values), 1)
            details["duplicate_keys"] = len(key_values) - len(set(key_values))

        return details

    def _score_timeliness(self, rows: List[Dict], headers: List[str]) -> float:
        """Check date column freshness."""
        if not rows or not headers:
            return 1.0  # No data = no penalty for timeliness

        # Find date-like columns
        date_cols = []
        for h in headers:
            sample = rows[0].get(h) if rows else None
            if isinstance(sample, str) and self._looks_like_date(sample):
                date_cols.append(h)

        if not date_cols:
            return 1.0  # No date columns = assume timely

        now = datetime.now()
        max_age_days = 0

        for col in date_cols:
            dates = []
            for row in rows:
                val = row.get(col)
                if isinstance(val, str):
                    try:
                        dates.append(datetime.strptime(val[:10], "%Y-%m-%d"))
                    except ValueError:
                        continue

            if dates:
                most_recent = max(dates)
                age_days = (now - most_recent).days
                max_age_days = max(max_age_days, age_days)

        # Timeliness degrades after 30 days, reaches 0 after 365 days
        if max_age_days <= 30:
            return 1.0
        elif max_age_days >= 365:
            return 0.1
        else:
            return 1.0 - (max_age_days - 30) / 335 * 0.9

    def _timeliness_details(self, rows: List[Dict], headers: List[str]) -> Dict:
        """Timeliness details."""
        details = {"date_columns_found": 0, "most_recent_date": None, "age_days": None}

        for h in headers:
            sample = rows[0].get(h) if rows else None
            if isinstance(sample, str) and self._looks_like_date(sample):
                details["date_columns_found"] += 1
                dates = []
                for row in rows:
                    val = row.get(h)
                    if isinstance(val, str):
                        try:
                            dates.append(datetime.strptime(val[:10], "%Y-%m-%d"))
                        except ValueError:
                            continue
                if dates:
                    most_recent = max(dates)
                    if details["most_recent_date"] is None or most_recent > details["most_recent_date"]:
                        details["most_recent_date"] = most_recent.isoformat()

        if details["most_recent_date"]:
            most_recent = datetime.fromisoformat(details["most_recent_date"])
            details["age_days"] = (datetime.now() - most_recent).days

        return details

    def _looks_like_date(self, value: str) -> bool:
        """Check if a string looks like a date."""
        import re
        return bool(re.match(r'^\d{4}[-/]\d{1,2}[-/]\d{1,2}', value) or
                    re.match(r'^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}', value))

    def _get_store(self):
        """Lazy-load the dataset store."""
        try:
            from .store import get_dataset_store
            return get_dataset_store()
        except Exception:
            return None