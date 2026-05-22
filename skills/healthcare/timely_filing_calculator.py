"""
Aethera AI - Timely Filing Calculator Skill

Compute claim filing deadlines from the date of service and payer, and report
how many days remain (or how overdue a claim is).
"""

from datetime import datetime, date, timedelta
from typing import Any, Dict, List

from skills.skill_base import AetheraSkill, SkillResult, skill

# Default timely-filing windows (days) by payer class.
TIMELY_FILING_DAYS = {
    "medicare": 365,
    "medicaid": 95,
    "managed_medicaid": 95,
    "commercial": 90,
    "bcbs": 365,
    "aetna": 90,
    "cigna": 90,
    "uhc": 90,
    "tricare": 365,
    "workers_comp": 365,
    "auto": 180,
    "other": 180,
}

AT_RISK_WINDOW_DAYS = 15


def _parse_date(value: Any) -> date:
    return datetime.fromisoformat(str(value)[:10]).date()


@skill(name="timely_filing_calculator", category="healthcare")
class TimelyFilingCalculatorSkill(AetheraSkill):

    @property
    def name(self) -> str:
        return "timely_filing_calculator"

    @property
    def description(self) -> str:
        return (
            "Calculate claim timely-filing deadlines from date of service and "
            "payer (or an explicit filing limit), reporting the deadline, days "
            "remaining, and status (ok / at_risk / expired). Supports batch input."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["calculate", "batch"], "description": "single or batch"},
                "date_of_service": {"type": "string", "description": "DOS (YYYY-MM-DD)"},
                "payer_class": {"type": "string", "description": "Payer or class (e.g. medicare, commercial, aetna)"},
                "filing_limit_days": {"type": "integer", "description": "Explicit limit; overrides payer default"},
                "as_of": {"type": "string", "description": "Reference date (defaults to today)"},
                "claims": {
                    "type": "array",
                    "description": "For batch: list of {date_of_service, payer_class, filing_limit_days?}",
                    "items": {"type": "object"},
                },
            },
        }

    def _evaluate(self, dos: Any, payer: str, limit_override: Any, as_of: date) -> Dict[str, Any]:
        dos_date = _parse_date(dos)
        payer_key = str(payer or "other").lower()
        limit = int(limit_override) if limit_override else TIMELY_FILING_DAYS.get(payer_key, TIMELY_FILING_DAYS["other"])
        deadline = dos_date + timedelta(days=limit)
        days_remaining = (deadline - as_of).days
        if days_remaining < 0:
            status = "expired"
        elif days_remaining <= AT_RISK_WINDOW_DAYS:
            status = "at_risk"
        else:
            status = "ok"
        return {
            "date_of_service": dos_date.isoformat(),
            "payer_class": payer_key,
            "filing_limit_days": limit,
            "deadline": deadline.isoformat(),
            "days_remaining": days_remaining,
            "status": status,
        }

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "calculate")
        as_of = _parse_date(kwargs["as_of"]) if kwargs.get("as_of") else date.today()
        try:
            if action == "batch":
                claims = kwargs.get("claims") or []
                results = [
                    self._evaluate(
                        c.get("date_of_service"), c.get("payer_class", "other"),
                        c.get("filing_limit_days"), as_of,
                    )
                    for c in claims if c.get("date_of_service")
                ]
                return SkillResult(success=True, data={
                    "results": results,
                    "expired": sum(1 for r in results if r["status"] == "expired"),
                    "at_risk": sum(1 for r in results if r["status"] == "at_risk"),
                })

            dos = kwargs.get("date_of_service")
            if not dos:
                return SkillResult(success=False, error="'date_of_service' is required")
            return SkillResult(success=True, data=self._evaluate(
                dos, kwargs.get("payer_class", "other"),
                kwargs.get("filing_limit_days"), as_of,
            ))
        except (ValueError, TypeError) as e:
            return SkillResult(success=False, error=f"Invalid date input: {e}")
        except Exception as e:
            return SkillResult(success=False, error=str(e))
