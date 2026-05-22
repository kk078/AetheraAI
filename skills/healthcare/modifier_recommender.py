"""
Aethera AI - CPT Modifier Recommender Skill

Given a billing scenario, recommend the appropriate CPT/HCPCS modifiers with a
short rationale for each.
"""

from typing import Any, Dict, List

from skills.skill_base import AetheraSkill, SkillResult, skill

# scenario flag -> (modifier, rationale)
FLAG_MODIFIERS = {
    "separate_em_same_day_procedure": ("25", "Significant, separately identifiable E/M on the same day as a procedure"),
    "distinct_procedural_service": ("59", "Distinct procedural service (consider X{EPSU} subsets when applicable)"),
    "bilateral_procedure": ("50", "Bilateral procedure performed"),
    "repeat_same_physician": ("76", "Repeat procedure by the same physician"),
    "repeat_other_physician": ("77", "Repeat procedure by another physician"),
    "multiple_procedures": ("51", "Multiple procedures in the same session"),
    "professional_component": ("26", "Professional component only"),
    "technical_component": ("TC", "Technical component only"),
    "assistant_surgeon": ("80", "Assistant surgeon"),
    "discontinued_procedure": ("53", "Discontinued procedure"),
    "staged_related_postop": ("58", "Staged/related procedure during the postoperative period"),
    "unrelated_postop": ("79", "Unrelated procedure during the postoperative period"),
    "unrelated_em_postop": ("24", "Unrelated E/M during a postoperative period"),
    "mandated_service": ("32", "Mandated service"),
    "reduced_service": ("52", "Reduced services"),
}

# More specific X{EPSU} subsets for distinct service, when the side/encounter is known.
X_SUBSETS = {
    "separate_encounter": ("XE", "Separate encounter"),
    "separate_structure": ("XS", "Separate structure/organ"),
    "separate_practitioner": ("XP", "Separate practitioner"),
    "unusual_separate": ("XU", "Unusual non-overlapping service"),
}

SIDE_MODIFIERS = {"left": ("LT", "Left side"), "right": ("RT", "Right side")}


@skill(name="modifier_recommender", category="healthcare")
class ModifierRecommenderSkill(AetheraSkill):

    @property
    def name(self) -> str:
        return "modifier_recommender"

    @property
    def description(self) -> str:
        return (
            "Recommend CPT/HCPCS modifiers (25, 59/X{EPSU}, 50, 51, 76/77, 26/TC, "
            "58/79/24, RT/LT, etc.) for a billing scenario, with a rationale for each."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "cpt": {"type": "string", "description": "Primary CPT code (optional, for context)"},
                "scenario": {
                    "type": "object",
                    "description": "Boolean scenario flags (see skill docs) plus optional 'side' and 'x_subset'",
                },
            },
            "required": ["scenario"],
        }

    async def execute(self, **kwargs) -> SkillResult:
        scenario = kwargs.get("scenario") or {}
        if not isinstance(scenario, dict):
            return SkillResult(success=False, error="'scenario' must be an object of flags")
        try:
            recommended: List[Dict[str, str]] = []
            seen = set()

            def add(mod: str, why: str):
                if mod not in seen:
                    seen.add(mod)
                    recommended.append({"modifier": mod, "rationale": why})

            for flag, (mod, why) in FLAG_MODIFIERS.items():
                if scenario.get(flag):
                    add(mod, why)

            # X{EPSU} refinement for distinct service.
            x = scenario.get("x_subset")
            if x and x in X_SUBSETS:
                mod, why = X_SUBSETS[x]
                add(mod, why + " (preferred over 59 when specific)")

            side = str(scenario.get("side", "")).lower()
            if side in SIDE_MODIFIERS:
                mod, why = SIDE_MODIFIERS[side]
                add(mod, why)

            if not recommended:
                return SkillResult(success=True, data={
                    "cpt": kwargs.get("cpt"),
                    "recommended_modifiers": [],
                    "note": "No modifier indicated by the provided scenario.",
                })

            return SkillResult(success=True, data={
                "cpt": kwargs.get("cpt"),
                "recommended_modifiers": recommended,
                "modifiers": [r["modifier"] for r in recommended],
            })
        except Exception as e:
            return SkillResult(success=False, error=str(e))
