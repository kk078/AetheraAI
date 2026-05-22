"""
Aethera AI - Medical Necessity Rationale Builder Skill

Assemble a structured medical-necessity statement linking a service (CPT) to
supporting diagnoses and clinical findings, plus a documentation checklist —
the kind of narrative used to support coverage and appeals.
"""

from typing import Any, Dict, List

from skills.skill_base import AetheraSkill, SkillResult, skill


@skill(name="medical_necessity_builder", category="healthcare")
class MedicalNecessityBuilderSkill(AetheraSkill):

    @property
    def name(self) -> str:
        return "medical_necessity_builder"

    @property
    def description(self) -> str:
        return (
            "Build a structured medical-necessity rationale linking a CPT/HCPCS "
            "service to supporting ICD-10 diagnoses, clinical indications, and "
            "failed conservative care, with a documentation checklist."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "cpt": {"type": "string", "description": "Service/procedure code"},
                "service_description": {"type": "string"},
                "diagnoses": {"type": "array", "items": {"type": "string"}, "description": "Supporting ICD-10 codes/terms"},
                "clinical_indications": {"type": "array", "items": {"type": "string"}},
                "failed_conservative": {"type": "array", "items": {"type": "string"}, "description": "Conservative treatments tried/failed"},
                "supporting_findings": {"type": "array", "items": {"type": "string"}, "description": "Imaging/labs/exam findings"},
            },
            "required": ["cpt", "diagnoses"],
        }

    async def execute(self, **kwargs) -> SkillResult:
        cpt = str(kwargs.get("cpt", "")).strip()
        diagnoses = kwargs.get("diagnoses") or []
        if not cpt:
            return SkillResult(success=False, error="'cpt' is required")
        if not diagnoses:
            return SkillResult(success=False, error="At least one supporting diagnosis is required")

        try:
            svc = kwargs.get("service_description") or f"the requested service ({cpt})"
            indications = kwargs.get("clinical_indications") or []
            failed = kwargs.get("failed_conservative") or []
            findings = kwargs.get("supporting_findings") or []

            parts: List[str] = []
            parts.append(
                f"{svc.capitalize()} is medically necessary for this patient, who "
                f"presents with {', '.join(diagnoses)}."
            )
            if indications:
                parts.append("Clinical indications supporting the service include: " + "; ".join(indications) + ".")
            if findings:
                parts.append("Objective findings documented: " + "; ".join(findings) + ".")
            if failed:
                parts.append(
                    "Conservative management has been attempted without adequate "
                    "response, including: " + "; ".join(failed) + "."
                )
            parts.append(
                f"Given the above, {svc} is reasonable and necessary to diagnose or "
                f"treat the documented condition(s) and is consistent with accepted "
                f"standards of care."
            )
            rationale = " ".join(parts)

            checklist = [
                {"item": "Diagnosis codes linked to the service", "satisfied": bool(diagnoses)},
                {"item": "Clinical indication documented", "satisfied": bool(indications)},
                {"item": "Objective findings (imaging/labs/exam)", "satisfied": bool(findings)},
                {"item": "Conservative treatment tried/failed", "satisfied": bool(failed)},
            ]
            missing = [c["item"] for c in checklist if not c["satisfied"]]

            return SkillResult(success=True, data={
                "cpt": cpt,
                "rationale": rationale,
                "documentation_checklist": checklist,
                "missing_documentation": missing,
                "strength": "strong" if not missing else ("moderate" if len(missing) <= 2 else "weak"),
            })
        except Exception as e:
            return SkillResult(success=False, error=str(e))
