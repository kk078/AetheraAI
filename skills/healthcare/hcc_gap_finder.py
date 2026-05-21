"""
Aethera AI - HCC Capture Gap Finder Skill

Compare conditions documented this year against prior-year HCCs to find risk
adjustment recapture gaps and estimate the RAF (and revenue) impact.

The ICD-10 -> HCC mapping and weights here are a representative sample for
demonstration; production use should load the full CMS-HCC model for the
applicable payment year.
"""

from typing import Any, Dict, List

from skills.skill_base import AetheraSkill, SkillResult, skill

# Sample ICD-10 prefix -> (HCC, label, RAF weight). Representative, not exhaustive.
ICD_TO_HCC = {
    "E11.9": ("HCC19", "Diabetes without complication", 0.105),
    "E11.4": ("HCC18", "Diabetes with chronic complications", 0.302),
    "E11.5": ("HCC18", "Diabetes with chronic complications", 0.302),
    "I50": ("HCC85", "Congestive heart failure", 0.331),
    "N18.5": ("HCC136", "CKD stage 5", 0.289),
    "N18.6": ("HCC136", "ESRD/CKD stage 5", 0.289),
    "J44": ("HCC111", "COPD", 0.328),
    "F32": ("HCC155", "Major depression", 0.309),
    "C50": ("HCC12", "Breast cancer", 0.150),
    "I12": ("HCC138", "Hypertensive CKD", 0.289),
}

# Average per-member-per-year revenue per 1.0 RAF (rough default; configurable).
DEFAULT_REVENUE_PER_RAF = 10000.0


def _map_dx(code: str):
    code = (code or "").upper().strip()
    if code in ICD_TO_HCC:
        return ICD_TO_HCC[code]
    # Prefix match (e.g. I50.9 -> I50, J44.1 -> J44).
    for prefix, mapping in ICD_TO_HCC.items():
        if code.startswith(prefix):
            return mapping
    return None


@skill(name="hcc_gap_finder", category="healthcare")
class HCCGapFinderSkill(AetheraSkill):

    @property
    def name(self) -> str:
        return "hcc_gap_finder"

    @property
    def description(self) -> str:
        return (
            "Find HCC risk-adjustment recapture gaps: prior-year HCCs not yet "
            "recaptured this year, plus suspected HCCs from this year's documented "
            "diagnoses. Estimates RAF and revenue impact. Uses a sample HCC model."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "current_year_dx": {"type": "array", "items": {"type": "string"}, "description": "ICD-10 codes documented this year"},
                "prior_year_hccs": {"type": "array", "items": {"type": "string"}, "description": "HCC codes captured last year"},
                "revenue_per_raf": {"type": "number", "description": "PMPY revenue per 1.0 RAF (default 10000)"},
            },
            "required": ["prior_year_hccs"],
        }

    async def execute(self, **kwargs) -> SkillResult:
        prior = kwargs.get("prior_year_hccs") or []
        current_dx = kwargs.get("current_year_dx") or []
        rev_per_raf = float(kwargs.get("revenue_per_raf", DEFAULT_REVENUE_PER_RAF) or DEFAULT_REVENUE_PER_RAF)

        try:
            # HCCs supported by this year's documentation.
            current_hccs: Dict[str, Dict[str, Any]] = {}
            for dx in current_dx:
                m = _map_dx(dx)
                if m:
                    hcc, label, weight = m
                    current_hccs[hcc] = {"hcc": hcc, "label": label, "raf_weight": weight, "from_dx": dx}

            prior_set = {str(h).upper().strip() for h in prior}
            current_set = set(current_hccs.keys())

            # Recapture gaps: captured last year, not yet supported this year.
            gaps = []
            raf_at_risk = 0.0
            for hcc in prior_set:
                if hcc not in current_set:
                    # Look up a weight/label for the prior HCC if we know it.
                    known = next((v for v in ICD_TO_HCC.values() if v[0] == hcc), None)
                    weight = known[2] if known else 0.0
                    label = known[1] if known else "Unknown HCC"
                    raf_at_risk += weight
                    gaps.append({"hcc": hcc, "label": label, "raf_weight": weight, "reason": "not recaptured this year"})

            # Suspected: supported by this year's dx but not in prior year.
            suspected = [v for h, v in current_hccs.items() if h not in prior_set]

            return SkillResult(success=True, data={
                "recapture_gaps": gaps,
                "suspected_new_hccs": suspected,
                "raf_at_risk": round(raf_at_risk, 3),
                "estimated_revenue_at_risk": round(raf_at_risk * rev_per_raf, 2),
                "summary": {
                    "prior_hccs": len(prior_set),
                    "recaptured": len(prior_set & current_set),
                    "gaps": len(gaps),
                    "suspected_new": len(suspected),
                },
            })
        except Exception as e:
            return SkillResult(success=False, error=str(e))
