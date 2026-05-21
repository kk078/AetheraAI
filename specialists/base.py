"""
Base specialist class for Aethera AI.

Every specialist inherits from AetheraSpecialist and provides:
- A unique name and domain
- A comprehensive system prompt
- A list of tool names it can invoke
- A priority for routing (lower = higher priority)
- An optional default model preference
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


# Tool definition format following OpenAI function-calling spec
TOOL_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    # === Healthcare Tools ===
    "code_lookup": {
        "type": "function",
        "function": {
            "name": "code_lookup",
            "description": "Search ICD-10-CM, ICD-10-PCS, CPT, HCPCS, CDT, or revenue codes. Returns code, description, and relevant guidelines.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search term or code number"},
                    "code_type": {"type": "string", "enum": ["icd10cm", "icd10pcs", "cpt", "hcpcs", "cdt", "revenue", "auto"], "description": "Code system to search"},
                    "limit": {"type": "integer", "description": "Max results to return (default 10)"}
                },
                "required": ["query"]
            }
        }
    },
    "cci_editor": {
        "type": "function",
        "function": {
            "name": "cci_editor",
            "description": "Check NCCI (National Correct Coding Initiative) edit pairs. Returns whether two codes can be billed together and if a modifier is allowed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["check_pair", "check_list"], "description": "Action to perform"},
                    "code1": {"type": "string", "description": "Column 1 code (or code list for check_list)"},
                    "code2": {"type": "string", "description": "Column 2 code"},
                    "modifier": {"type": "string", "description": "Modifier to check (e.g., 59, XE, XS, XP, XU)"},
                    "date": {"type": "string", "description": "Date of service (YYYY-MM-DD)"}
                },
                "required": ["action"]
            }
        }
    },
    "fee_schedule": {
        "type": "function",
        "function": {
            "name": "fee_schedule",
            "description": "Look up Medicare Physician Fee Schedule (MPFS) amounts, APC rates, or DRG weights.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["lookup", "compare"], "description": "Action to perform"},
                    "code": {"type": "string", "description": "CPT/HCPCS code or DRG number"},
                    "locality": {"type": "string", "description": "Geographic locality (default: national)"},
                    "year": {"type": "string", "description": "Fee schedule year (default: current)"}
                },
                "required": ["action", "code"]
            }
        }
    },
    "coverage_checker": {
        "type": "function",
        "function": {
            "name": "coverage_checker",
            "description": "Check LCD/NCD medical necessity criteria for a procedure-diagnosis pair.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["check_coverage", "search_lcd", "search_ncd"], "description": "Action to perform"},
                    "cpt": {"type": "string", "description": "CPT/HCPCS procedure code"},
                    "diagnosis": {"type": "string", "description": "ICD-10-CM diagnosis code"},
                    "payer": {"type": "string", "description": "Payer name (default: Medicare)"}
                },
                "required": ["action"]
            }
        }
    },
    "denial_analyzer": {
        "type": "function",
        "function": {
            "name": "denial_analyzer",
            "description": "Analyze denial CARC/RARC codes and recommend appeal actions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["analyze", "search_carc", "search_rarc"], "description": "Action to perform"},
                    "codes": {"type": "array", "items": {"type": "string"}, "description": "List of CARC/RARC codes to analyze"},
                    "claim_data": {"type": "object", "description": "Optional claim context data"}
                },
                "required": ["action"]
            }
        }
    },
    "denial_predictor": {
        "type": "function",
        "function": {
            "name": "denial_predictor",
            "description": "Predict denial probability before claim submission. Scores claim data for risk factors.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["predict", "scrub"], "description": "Action to perform"},
                    "claim_data": {"type": "object", "description": "Claim data including codes, amounts, patient info"}
                },
                "required": ["action", "claim_data"]
            }
        }
    },
    "appeals_writer": {
        "type": "function",
        "function": {
            "name": "appeals_writer",
            "description": "Generate an appeal letter with regulatory citations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["generate", "template"], "description": "Action to perform"},
                    "denial_info": {"type": "object", "description": "Denial details including codes, reason, payer, service info"}
                },
                "required": ["action"]
            }
        }
    },
    "drg_grouper": {
        "type": "function",
        "function": {
            "name": "drg_grouper",
            "description": "Determine MS-DRG assignment from diagnoses and procedures.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["assign", "lookup"], "description": "Action to perform"},
                    "diagnoses": {"type": "array", "items": {"type": "string"}, "description": "ICD-10-CM diagnosis codes"},
                    "procedures": {"type": "array", "items": {"type": "string"}, "description": "ICD-10-PCS procedure codes"}
                },
                "required": ["action"]
            }
        }
    },
    "apc_grouper": {
        "type": "function",
        "function": {
            "name": "apc_grouper",
            "description": "Determine APC assignment for outpatient procedures.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["assign", "lookup"], "description": "Action to perform"},
                    "cpt_codes": {"type": "array", "items": {"type": "string"}, "description": "CPT/HCPCS procedure codes"}
                },
                "required": ["action"]
            }
        }
    },
    "edi_parser": {
        "type": "function",
        "function": {
            "name": "edi_parser",
            "description": "Parse and validate X12 EDI transactions (837, 835, 270/271, 276/277, 278, 834, 820).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["parse", "validate", "generate"], "description": "Action to perform"},
                    "content": {"type": "string", "description": "EDI content to parse"},
                    "transaction_type": {"type": "string", "description": "Transaction type (837P, 837I, 835, etc.)"}
                },
                "required": ["action"]
            }
        }
    },
    "npi_lookup": {
        "type": "function",
        "function": {
            "name": "npi_lookup",
            "description": "Search NPI Registry for provider information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "npi": {"type": "string", "description": "10-digit NPI number"},
                    "name": {"type": "string", "description": "Provider or organization name"},
                    "state": {"type": "string", "description": "State abbreviation"},
                    "taxonomy": {"type": "string", "description": "Taxonomy code or description"}
                }
            }
        }
    },
    "prior_auth": {
        "type": "function",
        "function": {
            "name": "prior_auth",
            "description": "Look up prior authorization requirements by payer and procedure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["check_required", "search_criteria"], "description": "Action to perform"},
                    "cpt": {"type": "string", "description": "CPT/HCPCS procedure code"},
                    "payer": {"type": "string", "description": "Payer name"},
                    "diagnosis": {"type": "string", "description": "ICD-10-CM diagnosis code"}
                },
                "required": ["action"]
            }
        }
    },
    "medical_calculator": {
        "type": "function",
        "function": {
            "name": "medical_calculator",
            "description": "Clinical calculations: BMI, eGFR, MELD, APACHE, Wells, CURB-65, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["calculate", "list"], "description": "Action to perform"},
                    "calc_type": {"type": "string", "description": "Calculator type (bmi, egfr, meld, wells, etc.)"},
                    "values": {"type": "object", "description": "Input values for the calculation"}
                },
                "required": ["action"]
            }
        }
    },
    "drug_reference": {
        "type": "function",
        "function": {
            "name": "drug_reference",
            "description": "Drug information: indications, interactions, dosing, formulary status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["lookup", "interactions", "formulary"], "description": "Action to perform"},
                    "drug_name": {"type": "string", "description": "Drug name (brand or generic)"}
                },
                "required": ["action", "drug_name"]
            }
        }
    },
    "lab_interpreter": {
        "type": "function",
        "function": {
            "name": "lab_interpreter",
            "description": "Interpret laboratory values with reference ranges and clinical significance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "test_name": {"type": "string", "description": "Lab test name"},
                    "value": {"type": "number", "description": "Test value"},
                    "unit": {"type": "string", "description": "Unit of measurement"},
                    "patient_context": {"type": "object", "description": "Optional patient context (age, sex, conditions)"}
                },
                "required": ["test_name", "value"]
            }
        }
    },
    "remittance_parser": {
        "type": "function",
        "function": {
            "name": "remittance_parser",
            "description": "Parse ERA/835 remittance advice files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["parse", "summarize"], "description": "Action to perform"},
                    "content": {"type": "string", "description": "835/ERA content to parse"}
                },
                "required": ["action", "content"]
            }
        }
    },
    "claim_status": {
        "type": "function",
        "function": {
            "name": "claim_status",
            "description": "Interpret 276/277 claim status inquiry and response.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["inquire", "interpret"], "description": "Action to perform"},
                    "claim_data": {"type": "object", "description": "Claim data for inquiry"}
                },
                "required": ["action"]
            }
        }
    },
    "eligibility_checker": {
        "type": "function",
        "function": {
            "name": "eligibility_checker",
            "description": "Check benefits and eligibility (270/271 transaction).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["check", "interpret"], "description": "Action to perform"},
                    "member_data": {"type": "object", "description": "Member information"}
                },
                "required": ["action"]
            }
        }
    },
    "contract_analyzer": {
        "type": "function",
        "function": {
            "name": "contract_analyzer",
            "description": "Analyze payer contract terms and fee schedules.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["analyze", "compare", "extract"], "description": "Action to perform"},
                    "contract_data": {"type": "object", "description": "Contract data to analyze"}
                },
                "required": ["action"]
            }
        }
    },
    "risk_adjuster": {
        "type": "function",
        "function": {
            "name": "risk_adjuster",
            "description": "Calculate HCC/RAF risk adjustment scores and identify gaps.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["calculate", "gaps", "hierarchy"], "description": "Action to perform"},
                    "diagnoses": {"type": "array", "items": {"type": "string"}, "description": "ICD-10-CM diagnosis codes"},
                    "demographics": {"type": "object", "description": "Patient demographics (age, sex, dual status)"}
                },
                "required": ["action"]
            }
        }
    },
    "quality_tracker": {
        "type": "function",
        "function": {
            "name": "quality_tracker",
            "description": "Track HEDIS, MIPS, and Stars quality measures.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["lookup", "track", "gaps"], "description": "Action to perform"},
                    "measure": {"type": "string", "description": "Quality measure ID or name"},
                    "patient_data": {"type": "object", "description": "Patient data for gap identification"}
                },
                "required": ["action"]
            }
        }
    },
    "ndc_pricer": {
        "type": "function",
        "function": {
            "name": "ndc_pricer",
            "description": "Drug pricing lookup: ASP, AWP, WAC, NADAC.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["lookup", "compare"], "description": "Action to perform"},
                    "ndc": {"type": "string", "description": "NDC number"},
                    "drug_name": {"type": "string", "description": "Drug name"}
                },
                "required": ["action"]
            }
        }
    },
    "compliance_checker": {
        "type": "function",
        "function": {
            "name": "compliance_checker",
            "description": "Check compliance against HIPAA, OIG, Stark, Anti-Kickback, and other regulations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["check", "search", "audit_checklist"], "description": "Action to perform"},
                    "regulation": {"type": "string", "description": "Regulation to check (hipaa, stark, aks, false_claims, etc.)"},
                    "scenario": {"type": "string", "description": "Scenario description to evaluate"}
                },
                "required": ["action"]
            }
        }
    },
    "fhir_client": {
        "type": "function",
        "function": {
            "name": "fhir_client",
            "description": "FHIR R4 API client for healthcare data exchange.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["search", "read", "create", "update"], "description": "FHIR operation"},
                    "resource_type": {"type": "string", "description": "FHIR resource type (Patient, Observation, etc.)"},
                    "params": {"type": "object", "description": "Search or resource parameters"}
                },
                "required": ["action", "resource_type"]
            }
        }
    },
    # === General Tools ===
    "calculator": {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Math, financial, and statistical calculations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Mathematical expression or calculation type"},
                    "values": {"type": "object", "description": "Named values for the calculation"}
                },
                "required": ["expression"]
            }
        }
    },
    "web_researcher": {
        "type": "function",
        "function": {
            "name": "web_researcher",
            "description": "Multi-hop web search and summarization with citations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "depth": {"type": "integer", "description": "Number of hops (1-3, default 1)"},
                    "sources": {"type": "array", "items": {"type": "string"}, "description": "Preferred source domains"}
                },
                "required": ["query"]
            }
        }
    },
    "document_creator": {
        "type": "function",
        "function": {
            "name": "document_creator",
            "description": "Generate documents in DOCX, PDF, XLSX, PPTX, or Markdown format.",
            "parameters": {
                "type": "object",
                "properties": {
                    "format": {"type": "string", "enum": ["docx", "pdf", "xlsx", "pptx", "md"], "description": "Output format"},
                    "title": {"type": "string", "description": "Document title"},
                    "content": {"type": "string", "description": "Document content (Markdown supported)"},
                    "template": {"type": "string", "description": "Optional template name"}
                },
                "required": ["format", "content"]
            }
        }
    },
    "spreadsheet_analyzer": {
        "type": "function",
        "function": {
            "name": "spreadsheet_analyzer",
            "description": "Read, analyze, and write spreadsheet data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["analyze", "read", "write", "chart"], "description": "Action to perform"},
                    "file_path": {"type": "string", "description": "Path to spreadsheet file"},
                    "query": {"type": "string", "description": "Analysis query"}
                },
                "required": ["action"]
            }
        }
    },
    "data_visualizer": {
        "type": "function",
        "function": {
            "name": "data_visualizer",
            "description": "Create charts, graphs, and dashboards from data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_type": {"type": "string", "enum": ["bar", "line", "pie", "scatter", "heatmap", "table"], "description": "Chart type"},
                    "data": {"type": "object", "description": "Data for visualization"},
                    "title": {"type": "string", "description": "Chart title"}
                },
                "required": ["chart_type", "data"]
            }
        }
    },
    "summarizer": {
        "type": "function",
        "function": {
            "name": "summarizer",
            "description": "Summarize documents, URLs, or meeting transcripts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Content to summarize"},
                    "length": {"type": "string", "enum": ["brief", "medium", "detailed"], "description": "Summary length"},
                    "focus": {"type": "string", "description": "Focus area for the summary"}
                },
                "required": ["content"]
            }
        }
    },
    "code_executor": {
        "type": "function",
        "function": {
            "name": "code_executor",
            "description": "Execute Python, Node.js, or Bash code in a sandbox.",
            "parameters": {
                "type": "object",
                "properties": {
                    "language": {"type": "string", "enum": ["python", "node", "bash"], "description": "Language to execute"},
                    "code": {"type": "string", "description": "Code to execute"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default 30)"}
                },
                "required": ["language", "code"]
            }
        }
    },
    # === Cloudflare Tools ===
    "cloudflare_dns": {
        "type": "function",
        "function": {
            "name": "cloudflare_dns",
            "description": "Manage Cloudflare DNS records.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["list", "create", "update", "delete"], "description": "DNS action"},
                    "zone": {"type": "string", "description": "Zone name"},
                    "record": {"type": "object", "description": "DNS record data"}
                },
                "required": ["action", "zone"]
            }
        }
    },
    "cloudflare_tunnel": {
        "type": "function",
        "function": {
            "name": "cloudflare_tunnel",
            "description": "Manage Cloudflare Tunnels.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["status", "create", "delete", "config"], "description": "Tunnel action"},
                    "tunnel_name": {"type": "string", "description": "Tunnel name"}
                },
                "required": ["action"]
            }
        }
    },
    "cloudflare_workers": {
        "type": "function",
        "function": {
            "name": "cloudflare_workers",
            "description": "Manage Cloudflare Workers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["list", "deploy", "delete", "logs"], "description": "Worker action"},
                    "worker_name": {"type": "string", "description": "Worker name"}
                },
                "required": ["action"]
            }
        }
    },
    "cloudflare_pages": {
        "type": "function",
        "function": {
            "name": "cloudflare_pages",
            "description": "Manage Cloudflare Pages deployments.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["list", "deploy", "status"], "description": "Pages action"},
                    "project": {"type": "string", "description": "Project name"}
                },
                "required": ["action"]
            }
        }
    },
    "cloudflare_r2": {
        "type": "function",
        "function": {
            "name": "cloudflare_r2",
            "description": "Manage Cloudflare R2 object storage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["list", "upload", "download", "delete"], "description": "R2 action"},
                    "bucket": {"type": "string", "description": "Bucket name"},
                    "key": {"type": "string", "description": "Object key"}
                },
                "required": ["action"]
            }
        }
    },
    "ar_prioritizer": {
        "type": "function",
        "function": {
            "name": "ar_prioritizer",
            "description": "Prioritize an AR worklist by aging, dollars-at-risk, and payer collectibility; flags timely-filing risk.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["prioritize", "aging_summary"], "description": "Ranked worklist or bucket totals"},
                    "accounts": {"type": "array", "items": {"type": "object"}, "description": "AR accounts (account_id, balance, age_days/date_of_service, payer_class)"},
                    "limit": {"type": "integer", "description": "Max accounts in the ranked worklist"}
                },
                "required": ["accounts"]
            }
        }
    },
    "rcm_kpi_calculator": {
        "type": "function",
        "function": {
            "name": "rcm_kpi_calculator",
            "description": "Compute revenue-cycle KPIs (days in AR, clean claim/denial/collection rates, AR>90) from raw figures and grade vs benchmarks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "total_ar": {"type": "number"},
                    "average_daily_charges": {"type": "number"},
                    "total_charges": {"type": "number"},
                    "total_payments": {"type": "number"},
                    "contractual_adjustments": {"type": "number"},
                    "total_claims": {"type": "integer"},
                    "clean_claims": {"type": "integer"},
                    "denied_claims": {"type": "integer"},
                    "ar_over_90": {"type": "number"}
                }
            }
        }
    },
    "underpayment_detector": {
        "type": "function",
        "function": {
            "name": "underpayment_detector",
            "description": "Detect payer underpayments by comparing paid amounts to contractually-expected rates per claim line; totals recoverable variance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lines": {"type": "array", "items": {"type": "object"}, "description": "Claim lines (cpt, units, expected_rate, paid_amount)"},
                    "tolerance": {"type": "number", "description": "Dollar tolerance before flagging"}
                },
                "required": ["lines"]
            }
        }
    },
    "patient_cost_estimator": {
        "type": "function",
        "function": {
            "name": "patient_cost_estimator",
            "description": "Estimate patient out-of-pocket cost from benefits (deductible, coinsurance, copay, OOP max) or build a No Surprises Act Good Faith Estimate.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["estimate", "good_faith_estimate"]},
                    "charge": {"type": "number"},
                    "allowed_amount": {"type": "number"},
                    "deductible_remaining": {"type": "number"},
                    "coinsurance_rate": {"type": "number", "description": "Fraction, e.g. 0.2"},
                    "copay": {"type": "number"},
                    "oop_max_remaining": {"type": "number"},
                    "items": {"type": "array", "items": {"type": "object"}, "description": "GFE line items"}
                }
            }
        }
    },
    "timely_filing_calculator": {
        "type": "function",
        "function": {
            "name": "timely_filing_calculator",
            "description": "Compute claim timely-filing deadlines from date of service and payer; reports days remaining and status (ok/at_risk/expired).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["calculate", "batch"]},
                    "date_of_service": {"type": "string", "description": "YYYY-MM-DD"},
                    "payer_class": {"type": "string"},
                    "filing_limit_days": {"type": "integer"},
                    "as_of": {"type": "string"},
                    "claims": {"type": "array", "items": {"type": "object"}}
                }
            }
        }
    },
}


class AetheraSpecialist(ABC):
    """Abstract base for all Aethera domain specialists."""

    @property
    @abstractmethod
    def config(self) -> "SpecialistConfig":
        pass

    def get_system_prompt(self, user_profile: dict | None = None) -> str:
        prompt = self.config.system_prompt
        if user_profile:
            prefs = user_profile.get("preferences", {})
            if prefs:
                prompt += f"\n\n## User Context\n{prefs.get('specialization', '')}"
        return prompt

    def get_tool_definitions(self) -> list[dict]:
        """Return OpenAI function-calling tool definitions for this specialist's tools."""
        from specialists import TOOL_DEFINITIONS
        definitions = []
        for tool_name in self.config.tools:
            if tool_name in TOOL_DEFINITIONS:
                definitions.append(TOOL_DEFINITIONS[tool_name])
        return definitions