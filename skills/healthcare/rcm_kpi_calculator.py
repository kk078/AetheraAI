"""
Aethera AI - RCM KPI Calculator Skill

Compute the standard revenue-cycle KPIs from raw figures and grade each against
industry benchmarks: days in AR, clean claim rate, gross/net collection rate,
denial rate, and AR > 90 days.
"""

from typing import Any, Dict, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill

# (target, "higher_is_better"). Used to grade results.
BENCHMARKS = {
    "days_in_ar": (40.0, False),
    "clean_claim_rate": (95.0, True),
    "gross_collection_rate": (None, True),
    "net_collection_rate": (96.0, True),
    "denial_rate": (5.0, False),
    "ar_over_90_pct": (15.0, False),
}


def _grade(metric: str, value: float) -> str:
    target, higher_better = BENCHMARKS.get(metric, (None, True))
    if target is None or value is None:
        return "n/a"
    if higher_better:
        if value >= target:
            return "good"
        return "warning" if value >= target * 0.9 else "poor"
    else:
        if value <= target:
            return "good"
        return "warning" if value <= target * 1.2 else "poor"


def _safe_div(n: Optional[float], d: Optional[float]) -> Optional[float]:
    try:
        n = float(n); d = float(d)
        return n / d if d else None
    except (TypeError, ValueError):
        return None


@skill(name="rcm_kpi_calculator", category="healthcare")
class RCMKPICalculatorSkill(AetheraSkill):

    @property
    def name(self) -> str:
        return "rcm_kpi_calculator"

    @property
    def description(self) -> str:
        return (
            "Calculate revenue-cycle KPIs (days in AR, clean claim rate, gross/net "
            "collection rate, denial rate, AR>90 days) from raw figures and grade "
            "each against industry benchmarks. Only the metrics whose inputs are "
            "provided are returned."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "total_ar": {"type": "number", "description": "Total accounts receivable ($)"},
                "average_daily_charges": {"type": "number", "description": "Average daily gross charges ($)"},
                "total_charges": {"type": "number"},
                "total_payments": {"type": "number"},
                "contractual_adjustments": {"type": "number"},
                "total_claims": {"type": "integer"},
                "clean_claims": {"type": "integer", "description": "Claims accepted on first submission"},
                "denied_claims": {"type": "integer"},
                "ar_over_90": {"type": "number", "description": "AR aged over 90 days ($)"},
            },
        }

    async def execute(self, **kwargs) -> SkillResult:
        try:
            results: Dict[str, Any] = {}

            dia = _safe_div(kwargs.get("total_ar"), kwargs.get("average_daily_charges"))
            if dia is not None:
                results["days_in_ar"] = round(dia, 1)

            ccr = _safe_div(kwargs.get("clean_claims"), kwargs.get("total_claims"))
            if ccr is not None:
                results["clean_claim_rate"] = round(ccr * 100, 1)

            gcr = _safe_div(kwargs.get("total_payments"), kwargs.get("total_charges"))
            if gcr is not None:
                results["gross_collection_rate"] = round(gcr * 100, 1)

            charges = kwargs.get("total_charges")
            adj = kwargs.get("contractual_adjustments")
            if charges is not None and adj is not None:
                ncr = _safe_div(kwargs.get("total_payments"), float(charges) - float(adj))
                if ncr is not None:
                    results["net_collection_rate"] = round(ncr * 100, 1)

            dr = _safe_div(kwargs.get("denied_claims"), kwargs.get("total_claims"))
            if dr is not None:
                results["denial_rate"] = round(dr * 100, 1)

            ar90 = _safe_div(kwargs.get("ar_over_90"), kwargs.get("total_ar"))
            if ar90 is not None:
                results["ar_over_90_pct"] = round(ar90 * 100, 1)

            if not results:
                return SkillResult(
                    success=False,
                    error="Insufficient inputs — provide figures for at least one KPI.",
                )

            graded = {
                metric: {
                    "value": value,
                    "benchmark": BENCHMARKS.get(metric, (None,))[0],
                    "status": _grade(metric, value),
                }
                for metric, value in results.items()
            }
            poor = [m for m, v in graded.items() if v["status"] == "poor"]
            return SkillResult(success=True, data={
                "kpis": graded,
                "needs_attention": poor,
            })
        except Exception as e:
            return SkillResult(success=False, error=str(e))
