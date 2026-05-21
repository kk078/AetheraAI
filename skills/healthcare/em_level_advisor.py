"""
Aethera AI - E/M Level Advisor Skill

Recommend an office/outpatient E/M code (2021+ guidelines) by total time or by
medical decision making (MDM), with the supporting rationale.
"""

from typing import Any, Dict, List, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill

# Time thresholds (minutes, lower bound) -> code, for 2021+ office/outpatient.
TIME_NEW = [(60, "99205"), (45, "99204"), (30, "99203"), (15, "99202")]
TIME_ESTABLISHED = [(40, "99215"), (30, "99214"), (20, "99213"), (10, "99212")]

MDM_NEW = {"straightforward": "99202", "low": "99203", "moderate": "99204", "high": "99205"}
MDM_ESTABLISHED = {"straightforward": "99212", "low": "99213", "moderate": "99214", "high": "99215"}

_LEVEL_ORDER = ["straightforward", "low", "moderate", "high"]


def _code_by_time(patient_type: str, minutes: float) -> Optional[str]:
    table = TIME_NEW if patient_type == "new" else TIME_ESTABLISHED
    for lower, code in table:
        if minutes >= lower:
            return code
    return None


def _mdm_from_components(problems: str, data: str, risk: str) -> str:
    """MDM is the level met by at least two of the three elements."""
    levels = [problems, data, risk]
    # Count how many elements reach each level; pick the highest level reached by >=2.
    best = "straightforward"
    for lvl in _LEVEL_ORDER:
        reached = sum(1 for el in levels if _LEVEL_ORDER.index(el) >= _LEVEL_ORDER.index(lvl))
        if reached >= 2:
            best = lvl
    return best


@skill(name="em_level_advisor", category="healthcare")
class EMLevelAdvisorSkill(AetheraSkill):

    @property
    def name(self) -> str:
        return "em_level_advisor"

    @property
    def description(self) -> str:
        return (
            "Recommend an office/outpatient E/M level (99202-99215, 2021+ rules) "
            "by total time or by medical decision making (MDM). MDM can be given "
            "directly or derived from problems/data/risk via the 2-of-3 rule."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "method": {"type": "string", "enum": ["time", "mdm"], "description": "Selection method"},
                "patient_type": {"type": "string", "enum": ["new", "established"]},
                "total_time_minutes": {"type": "number"},
                "mdm_level": {"type": "string", "enum": ["straightforward", "low", "moderate", "high"]},
                "problems_level": {"type": "string", "enum": ["straightforward", "low", "moderate", "high"]},
                "data_level": {"type": "string", "enum": ["straightforward", "low", "moderate", "high"]},
                "risk_level": {"type": "string", "enum": ["straightforward", "low", "moderate", "high"]},
            },
            "required": ["patient_type"],
        }

    async def execute(self, **kwargs) -> SkillResult:
        patient_type = str(kwargs.get("patient_type", "")).lower()
        if patient_type not in ("new", "established"):
            return SkillResult(success=False, error="patient_type must be 'new' or 'established'")
        method = kwargs.get("method")
        try:
            if method == "time" or (method is None and kwargs.get("total_time_minutes") is not None):
                minutes = kwargs.get("total_time_minutes")
                if minutes is None:
                    return SkillResult(success=False, error="total_time_minutes required for time method")
                code = _code_by_time(patient_type, float(minutes))
                if not code:
                    return SkillResult(success=False, error="Total time below the minimum E/M threshold")
                return SkillResult(success=True, data={
                    "recommended_code": code,
                    "method": "time",
                    "rationale": f"{minutes} minutes of total time on the date of encounter for an "
                                 f"{patient_type} patient supports {code}.",
                })

            # MDM method
            mdm = kwargs.get("mdm_level")
            derived = None
            if not mdm:
                p, d, r = kwargs.get("problems_level"), kwargs.get("data_level"), kwargs.get("risk_level")
                if not (p and d and r):
                    return SkillResult(success=False, error="Provide mdm_level, or all of problems_level/data_level/risk_level")
                mdm = _mdm_from_components(p, d, r)
                derived = {"problems": p, "data": d, "risk": r, "rule": "2-of-3 highest"}
            table = MDM_NEW if patient_type == "new" else MDM_ESTABLISHED
            code = table[mdm]
            return SkillResult(success=True, data={
                "recommended_code": code,
                "method": "mdm",
                "mdm_level": mdm,
                "derived_from": derived,
                "rationale": f"{mdm.capitalize()} MDM for an {patient_type} patient supports {code}.",
            })
        except KeyError:
            return SkillResult(success=False, error="Invalid MDM level")
        except Exception as e:
            return SkillResult(success=False, error=str(e))
