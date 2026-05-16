"""
Aethera AI - Code Lookup Skill

Search ICD-10-CM, ICD-10-PCS, CPT, HCPCS, CDT, and revenue codes.
"""

from typing import Optional, Dict, Any

from skills.skill_base import AetheraSkill, SkillResult, skill


@skill(name="code_lookup", category="healthcare")
class CodeLookupSkill(AetheraSkill):
    """
    Look up medical codes: ICD-10-CM, ICD-10-PCS, CPT, HCPCS, CDT.
    """

    @property
    def name(self) -> str:
        return "code_lookup"

    @property
    def description(self) -> str:
        return "Search ICD-10-CM, ICD-10-PCS, CPT, HCPCS, CDT, and revenue codes"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Code to look up (e.g., E11.9, 99213, A0428)"
                },
                "code_type": {
                    "type": "string",
                    "enum": ["icd10cm", "icd10pcs", "cpt", "hcpcs", "cdt", "revenue"],
                    "description": "Type of code"
                },
                "search": {
                    "type": "string",
                    "description": "Keyword search term (if code not provided)"
                },
                "include_children": {
                    "type": "boolean",
                    "description": "Include child codes",
                    "default": False
                }
            }
        }

    @property
    def requires_phi_protection(self) -> bool:
        return False

    @property
    def examples(self) -> list:
        return [
            {"input": {"code": "E11.9", "code_type": "icd10cm"}},
            {"input": {"code": "99213", "code_type": "cpt"}},
            {"input": {"search": "diabetes type 2", "code_type": "icd10cm"}},
        ]

    async def execute(self, **kwargs) -> SkillResult:
        code = kwargs.get("code", "")
        code_type = kwargs.get("code_type", "")
        search = kwargs.get("search", "")
        include_children = kwargs.get("include_children", False)

        if not code and not search:
            return SkillResult(success=False, error="Either code or search term is required")

        try:
            if code:
                result = await self._lookup_code(code, code_type, include_children)
            else:
                result = await self._search_codes(search, code_type)

            return SkillResult(success=True, data=result)
        except Exception as e:
            return SkillResult(success=False, error=str(e))

    async def _lookup_code(self, code: str, code_type: str, include_children: bool) -> Dict[str, Any]:
        """Look up a specific code."""
        # Normalize code
        code = code.upper().strip()

        # In production, this would query the knowledge base
        # For now, return structured response
        result = {
            "code": code,
            "code_type": code_type or self._detect_code_type(code),
            "description": self._get_description(code),
            "valid": True,
        }

        if include_children:
            result["children"] = self._get_child_codes(code)

        return result

    async def _search_codes(self, search_term: str, code_type: str) -> Dict[str, Any]:
        """Search for codes by keyword."""
        # In production, this would search the knowledge base
        # For now, return mock results
        return {
            "search_term": search_term,
            "code_type": code_type,
            "results": [
                {"code": "EXAMPLE", "description": f"Code matching '{search_term}'"}
            ],
            "total": 1
        }

    def _detect_code_type(self, code: str) -> str:
        """Detect code type from code format."""
        code = code.upper()

        # ICD-10-CM: Letter + 2 digits, optional decimal + more chars
        if code[0].isalpha() and code[1].isdigit() and code[2].isdigit():
            return "icd10cm"

        # CPT: 5 digits, optional letter suffix
        if code.isdigit() and len(code) == 5:
            return "cpt"

        # HCPCS Level II: Letter + 4 digits
        if code[0].isalpha() and code[1:].isdigit() and len(code) == 5:
            return "hcpcs"

        # CDT: D + 4 digits
        if code.startswith("D") and code[1:].isdigit():
            return "cdt"

        return "unknown"

    def _get_description(self, code: str) -> str:
        """Get code description (mock - would query knowledge base)."""
        # In production, query ChromaDB or SQLite knowledge base
        descriptions = {
            "E11.9": "Type 2 diabetes mellitus without complications",
            "E11.65": "Type 2 diabetes mellitus with hyperglycemia",
            "99213": "Office/outpatient E/M visit, established patient, low complexity",
            "99214": "Office/outpatient E/M visit, established patient, moderate complexity",
            "A0428": "Ambulance service, basic life support, non-emergency transport",
        }
        return descriptions.get(code.upper(), "Description not found in local cache")

    def _get_child_codes(self, code: str) -> list:
        """Get child codes (for hierarchical code systems)."""
        # In production, query knowledge base
        children_map = {
            "E11": ["E11.9", "E11.65", "E11.21", "E11.22", "E11.39"],
            "9921": ["99211", "99212", "99213", "99214", "99215"],
        }
        base = code.split(".")[0] if "." in code else code[:4]
        return children_map.get(base, [])
