"""
Aethera AI - Underpayment / Contract Variance Detector Skill

Compare actual payments against contractually-expected amounts per claim line,
flag underpayments beyond a tolerance, and summarize total recoverable variance.
"""

from typing import Any, Dict, List

from skills.skill_base import AetheraSkill, SkillResult, skill

DEFAULT_TOLERANCE = 0.01  # $0.01 — anything below expected is a variance


@skill(name="underpayment_detector", category="healthcare")
class UnderpaymentDetectorSkill(AetheraSkill):

    @property
    def name(self) -> str:
        return "underpayment_detector"

    @property
    def description(self) -> str:
        return (
            "Detect payer underpayments by comparing paid amounts to the "
            "contractually-expected rate for each claim line. Flags lines paid "
            "below expected (beyond a tolerance) and totals the recoverable "
            "variance, with a per-CPT breakdown."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "lines": {
                    "type": "array",
                    "description": "Claim lines to evaluate",
                    "items": {
                        "type": "object",
                        "properties": {
                            "cpt": {"type": "string"},
                            "units": {"type": "number"},
                            "expected_rate": {"type": "number", "description": "Contract rate per unit"},
                            "paid_amount": {"type": "number", "description": "Amount actually paid for the line"},
                        },
                    },
                },
                "tolerance": {"type": "number", "description": "Dollar tolerance before flagging (default 0.01)"},
            },
            "required": ["lines"],
        }

    async def execute(self, **kwargs) -> SkillResult:
        lines = kwargs.get("lines") or []
        if not isinstance(lines, list):
            return SkillResult(success=False, error="'lines' must be a list")
        tolerance = float(kwargs.get("tolerance", DEFAULT_TOLERANCE) or DEFAULT_TOLERANCE)

        try:
            flagged: List[Dict[str, Any]] = []
            by_cpt: Dict[str, float] = {}
            total_expected = 0.0
            total_paid = 0.0
            total_variance = 0.0

            for ln in lines:
                cpt = str(ln.get("cpt", "")).strip() or "UNKNOWN"
                units = float(ln.get("units", 1) or 1)
                rate = float(ln.get("expected_rate", 0) or 0)
                paid = float(ln.get("paid_amount", 0) or 0)
                expected = round(rate * units, 2)
                variance = round(expected - paid, 2)

                total_expected += expected
                total_paid += paid

                if variance > tolerance:
                    total_variance += variance
                    by_cpt[cpt] = round(by_cpt.get(cpt, 0.0) + variance, 2)
                    flagged.append({
                        "cpt": cpt,
                        "units": units,
                        "expected": expected,
                        "paid": round(paid, 2),
                        "variance": variance,
                        "pct_underpaid": round((variance / expected) * 100, 1) if expected else None,
                    })

            flagged.sort(key=lambda x: x["variance"], reverse=True)
            return SkillResult(success=True, data={
                "summary": {
                    "lines_evaluated": len(lines),
                    "lines_underpaid": len(flagged),
                    "total_expected": round(total_expected, 2),
                    "total_paid": round(total_paid, 2),
                    "total_recoverable_variance": round(total_variance, 2),
                },
                "by_cpt": [{"cpt": k, "variance": v} for k, v in sorted(by_cpt.items(), key=lambda kv: kv[1], reverse=True)],
                "underpaid_lines": flagged,
            })
        except Exception as e:
            return SkillResult(success=False, error=str(e))
