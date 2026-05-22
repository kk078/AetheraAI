"""
Aethera AI - Data Insights Skill

Quick analytics over an array of records (rows of objects): descriptive
statistics for numeric fields, group-by aggregation, and z-score outlier
detection. Complements the file-oriented spreadsheet analyzer.
"""

import statistics
from typing import Any, Dict, List, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill


def _numeric(values: List[Any]) -> List[float]:
    out = []
    for v in values:
        try:
            out.append(float(v))
        except (TypeError, ValueError):
            continue
    return out


@skill(name="data_insights", category="general")
class DataInsightsSkill(AetheraSkill):

    @property
    def name(self) -> str:
        return "data_insights"

    @property
    def description(self) -> str:
        return (
            "Analyze an array of records: 'describe' computes count/mean/median/"
            "min/max/stdev/sum for numeric fields; 'group_by' aggregates a field "
            "(sum/mean/count/min/max) by a key; 'outliers' flags z-score outliers."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["describe", "group_by", "outliers"]},
                "records": {"type": "array", "items": {"type": "object"}},
                "fields": {"type": "array", "items": {"type": "string"}, "description": "Numeric fields for describe"},
                "group_field": {"type": "string"},
                "agg_field": {"type": "string"},
                "agg": {"type": "string", "enum": ["sum", "mean", "count", "min", "max"]},
                "field": {"type": "string", "description": "Numeric field for outliers"},
                "z_threshold": {"type": "number", "description": "Outlier |z| cutoff (default 2.0)"},
            },
            "required": ["action", "records"],
        }

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action")
        records = kwargs.get("records") or []
        if not isinstance(records, list):
            return SkillResult(success=False, error="'records' must be a list")
        try:
            if action == "describe":
                return self._describe(records, kwargs.get("fields"))
            if action == "group_by":
                return self._group_by(records, kwargs.get("group_field"),
                                      kwargs.get("agg_field"), kwargs.get("agg", "count"))
            if action == "outliers":
                return self._outliers(records, kwargs.get("field"),
                                      float(kwargs.get("z_threshold", 2.0) or 2.0))
            return SkillResult(success=False, error=f"Unknown action: {action}")
        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _describe(self, records, fields):
        if not records:
            return SkillResult(success=False, error="No records to describe")
        if not fields:
            # Infer numeric fields from the first record.
            fields = [k for k, v in records[0].items() if isinstance(v, (int, float))]
        stats = {}
        for f in fields:
            nums = _numeric([r.get(f) for r in records if f in r])
            if not nums:
                continue
            stats[f] = {
                "count": len(nums),
                "sum": round(sum(nums), 4),
                "mean": round(statistics.mean(nums), 4),
                "median": round(statistics.median(nums), 4),
                "min": min(nums),
                "max": max(nums),
                "stdev": round(statistics.stdev(nums), 4) if len(nums) > 1 else 0.0,
            }
        return SkillResult(success=True, data={"row_count": len(records), "fields": stats})

    def _group_by(self, records, group_field, agg_field, agg):
        if not group_field:
            return SkillResult(success=False, error="'group_field' is required")
        groups: Dict[Any, List[Any]] = {}
        for r in records:
            key = r.get(group_field, "∅")
            groups.setdefault(key, [])
            if agg != "count" and agg_field is not None:
                groups[key].append(r.get(agg_field))

        results = []
        for key, vals in groups.items():
            if agg == "count":
                value = len([r for r in records if r.get(group_field, "∅") == key])
            else:
                nums = _numeric(vals)
                if not nums:
                    value = None
                elif agg == "sum":
                    value = round(sum(nums), 4)
                elif agg == "mean":
                    value = round(statistics.mean(nums), 4)
                elif agg == "min":
                    value = min(nums)
                elif agg == "max":
                    value = max(nums)
                else:
                    value = None
            results.append({"group": key, "agg": agg, "field": agg_field, "value": value})
        results.sort(key=lambda x: (x["value"] is None, -(x["value"] or 0)))
        return SkillResult(success=True, data={"groups": results, "group_count": len(results)})

    def _outliers(self, records, field, z_threshold):
        if not field:
            return SkillResult(success=False, error="'field' is required")
        nums = _numeric([r.get(field) for r in records if field in r])
        if len(nums) < 2:
            return SkillResult(success=False, error="Need at least 2 numeric values")
        mean = statistics.mean(nums)
        stdev = statistics.stdev(nums)
        outliers = []
        if stdev > 0:
            for r in records:
                try:
                    v = float(r.get(field))
                except (TypeError, ValueError):
                    continue
                z = (v - mean) / stdev
                if abs(z) >= z_threshold:
                    outliers.append({"record": r, "value": v, "z_score": round(z, 3)})
        return SkillResult(success=True, data={
            "field": field, "mean": round(mean, 4), "stdev": round(stdev, 4),
            "z_threshold": z_threshold, "outliers": outliers, "outlier_count": len(outliers),
        })
