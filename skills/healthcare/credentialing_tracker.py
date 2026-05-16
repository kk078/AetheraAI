"""
Aethera AI - Credentialing Tracker Skill

Track provider credentialing status: state licenses, DEA, board certifications,
hospital privileges, and payer enrollment. Monitor revalidation cycles and
generate credentialing checklists.
"""

import math
from datetime import date, timedelta
from typing import Dict, Any, List, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill


# Credential type definitions with revalidation cycles
CREDENTIAL_TYPES: Dict[str, Dict[str, Any]] = {
    "state_license": {
        "label": "State Medical License",
        "revalidation_cycle_months": 24,
        "grace_period_days": 30,
        "required_documents": [
            "Completed state medical board application",
            "Verification of medical education (ECFMG for international grads)",
            "Postgraduate training verification",
            "Examination scores (USMLE/COMLEX)",
            "Malpractice history disclosure",
            "CME completion certificates",
            "Background check / fingerprinting",
        ],
        "notes": "Each state has unique requirements. Check state medical board for specific forms."
    },
    "dea": {
        "label": "DEA Registration",
        "revalidation_cycle_months": 36,
        "grace_period_days": 0,
        "required_documents": [
            "DEA Form 223 (new) or Form 224 (renewal)",
            "Active state medical license number",
            "Schedule-specific prescribing authority justification (Schedules II-V)",
            "State controlled substance registration if required",
        ],
        "notes": "DEA registration must be current; no grace period. Separate DEA required per practice location in some states."
    },
    "board_cert": {
        "label": "Board Certification",
        "revalidation_cycle_months": 120,  # Typically 10 years with MOC
        "grace_period_days": 90,
        "required_documents": [
            "Board certification verification letter or certificate",
            "MOC/participation status documentation",
            "CME / self-assessment credits per board requirements",
            "Practice improvement module completion (if applicable)",
            "Secure exam passage (at re-certification interval)",
        ],
        "notes": "Board certification is not legally required to practice but is often required by payers and hospitals."
    },
    "hospital_privileges": {
        "label": "Hospital Privileges",
        "revalidation_cycle_months": 24,
        "grace_period_days": 0,
        "required_documents": [
            "Hospital credentialing application",
            "Current CV / resume",
            "State medical license verification",
            "DEA registration verification",
            "Malpractice insurance certificate (face sheet)",
            "Peer references (typically 3-5)",
            "Clinical privilege request form (specify requested procedures)",
            "Health status attestation",
            "Immunization records (if required by facility)",
        ],
        "notes": "Each hospital has its own bylaws and privileging criteria. FPPE/OPPE may apply."
    },
    "payer_enrollment": {
        "label": "Payer Enrollment / Credentialing",
        "revalidation_cycle_months": 36,
        "grace_period_days": 60,
        "required_documents": [
            "CAQH ProView application (or payer-specific form)",
            "Current state medical license",
            "DEA registration (if prescribing controlled substances)",
            "Board certification (if applicable)",
            "Malpractice insurance face sheet",
            "W-9 / tax identification information",
            "NPI verification",
            "Hospital privileges letter (if applicable)",
            "CMS-855I / 855B for Medicare enrollment",
        ],
        "notes": "Medicare revalidation occurs every 5 years per CMS. Commercial payers vary. CAQH reduces duplicate paperwork."
    },
    "npi": {
        "label": "NPI Registration",
        "revalidation_cycle_months": 0,  # No revalidation required, but must update changes
        "grace_period_days": 0,
        "required_documents": [
            "NPPES online application or CMS-10114",
            "State medical license number",
            "Tax Identification Number (TIN/EIN)",
        ],
        "notes": "NPI does not expire but must be updated within 30 days of any changes per CMS."
    },
    "malpractice_insurance": {
        "label": "Malpractice / Professional Liability Insurance",
        "revalidation_cycle_months": 12,
        "grace_period_days": 0,
        "required_documents": [
            "Certificate of insurance / face sheet",
            "Coverage limits documentation (per occurrence / aggregate)",
            "Tail coverage confirmation (if applicable)",
        ],
        "notes": "Minimum coverage limits vary by state and hospital. Occurrence vs claims-made policies affect tail needs."
    },
    "cme": {
        "label": "Continuing Medical Education (CME)",
        "revalidation_cycle_months": 24,
        "grace_period_days": 0,
        "required_documents": [
            "CME certificates (Category 1 and Category 2)",
            "Self-assessment completion records",
            "MOC part 2 / part 4 documentation (if board certified)",
        ],
        "notes": "CME requirements vary by state (typically 20-50 Category 1 credits per 1-2 year cycle)."
    },
}

# Sample provider credential database (in production, this would be a database)
SAMPLE_PROVIDERS: Dict[str, Dict[str, Any]] = {
    "PROV-001": {
        "name": "Dr. Sarah Chen",
        "npi": "1234567890",
        "specialty": "Internal Medicine",
        "credentials": {
            "state_license": {
                "number": "MD-048201",
                "state": "CA",
                "issue_date": "2022-01-15",
                "expiry_date": "2024-01-15",
                "status": "active",
            },
            "dea": {
                "number": "AC1234567",
                "issue_date": "2021-06-01",
                "expiry_date": "2024-06-01",
                "schedules": ["II", "IIN", "III", "IIIN", "IV", "V"],
                "status": "active",
            },
            "board_cert": {
                "board": "ABIM",
                "specialty": "Internal Medicine",
                "issue_date": "2020-07-01",
                "expiry_date": "2030-07-01",
                "moc_status": "compliant",
                "status": "active",
            },
            "hospital_privileges": [
                {
                    "hospital": "City General Hospital",
                    "privilege_level": "active",
                    "expiry_date": "2024-12-31",
                    "status": "active",
                }
            ],
            "payer_enrollment": [
                {"payer": "Medicare", "ptan": "MH123456", "status": "active", "revalidation_due": "2026-03-01"},
                {"payer": "BCBS of CA", "provider_id": "BC987654", "status": "active", "revalidation_due": "2025-09-01"},
            ],
            "npi": {
                "number": "1234567890",
                "status": "active",
            },
            "malpractice_insurance": {
                "carrier": "MedPro Group",
                "policy_number": "MP-998877",
                "expiry_date": "2024-12-01",
                "limits": "1M/3M",
                "status": "active",
            },
        },
    },
    "PROV-002": {
        "name": "Dr. James Rivera",
        "npi": "9876543210",
        "specialty": "Orthopedic Surgery",
        "credentials": {
            "state_license": {
                "number": "MD-051902",
                "state": "TX",
                "issue_date": "2021-03-20",
                "expiry_date": "2023-03-20",
                "status": "expired",
            },
            "dea": {
                "number": "FR7654321",
                "issue_date": "2022-01-15",
                "expiry_date": "2025-01-15",
                "schedules": ["II", "IIN", "III", "IIIN", "IV", "V"],
                "status": "active",
            },
            "board_cert": {
                "board": "ABOS",
                "specialty": "Orthopedic Surgery",
                "issue_date": "2019-10-01",
                "expiry_date": "2029-10-01",
                "moc_status": "compliant",
                "status": "active",
            },
            "hospital_privileges": [
                {
                    "hospital": "Memorial Medical Center",
                    "privilege_level": "active",
                    "expiry_date": "2024-06-30",
                    "status": "active",
                },
                {
                    "hospital": "St. David's Medical Center",
                    "privilege_level": "provisional",
                    "expiry_date": "2024-06-30",
                    "status": "pending",
                },
            ],
            "payer_enrollment": [
                {"payer": "Medicare", "ptan": "MH543210", "status": "active", "revalidation_due": "2025-07-01"},
                {"payer": "Aetna", "provider_id": "AE112233", "status": "pending", "revalidation_due": "2025-11-01"},
            ],
            "npi": {
                "number": "9876543210",
                "status": "active",
            },
            "malpractice_insurance": {
                "carrier": "The Doctors Company",
                "policy_number": "DC-556677",
                "expiry_date": "2024-07-01",
                "limits": "1M/3M",
                "status": "active",
            },
        },
    },
}


@skill(name="credentialing_tracker", category="healthcare")
class CredentialingTrackerSkill(AetheraSkill):
    """
    Track provider credentialing status, monitor revalidation cycles,
    and generate credentialing checklists.
    """

    @property
    def name(self) -> str:
        return "credentialing_tracker"

    @property
    def description(self) -> str:
        return "Track provider credentialing status (state license, DEA, board cert, hospital privileges, payer enrollment), check upcoming expirations, and generate credentialing checklists."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["check_status", "upcoming_expirations", "generate_checklist", "full_report"],
                    "description": "Action to perform: check_status (check credential status for a provider), upcoming_expirations (get credentials expiring within window), generate_checklist (generate credentialing checklist by type), full_report (comprehensive provider credential report)"
                },
                "provider_id": {
                    "type": "string",
                    "description": "Provider identifier (e.g., PROV-001, NPI number)"
                },
                "credential_type": {
                    "type": "string",
                    "enum": ["state_license", "dea", "board_cert", "hospital_privileges", "payer_enrollment", "npi", "malpractice_insurance", "cme", "all"],
                    "description": "Type of credential to check or generate checklist for"
                },
                "days_ahead": {
                    "type": "integer",
                    "description": "Number of days ahead to check for expirations (default 90)",
                    "default": 90
                }
            },
            "required": ["action"]
        }

    @property
    def requires_phi_protection(self) -> bool:
        return True

    @property
    def examples(self) -> list:
        return [
            {"input": {"action": "check_status", "provider_id": "PROV-001"}},
            {"input": {"action": "upcoming_expirations", "provider_id": "PROV-002", "days_ahead": 180}},
            {"input": {"action": "generate_checklist", "credential_type": "state_license"}},
            {"input": {"action": "full_report", "provider_id": "PROV-001"}},
        ]

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "")
        provider_id = kwargs.get("provider_id", "")
        credential_type = kwargs.get("credential_type", "all")
        days_ahead = kwargs.get("days_ahead", 90)

        try:
            if action == "check_status":
                if not provider_id:
                    return SkillResult(success=False, error="provider_id is required for check_status action")
                result = self._check_status(provider_id, credential_type)
                return SkillResult(success=True, data=result)

            elif action == "upcoming_expirations":
                result = self._get_upcoming_expirations(provider_id, days_ahead)
                return SkillResult(success=True, data=result)

            elif action == "generate_checklist":
                result = self._generate_checklist(credential_type)
                return SkillResult(success=True, data=result)

            elif action == "full_report":
                if not provider_id:
                    return SkillResult(success=False, error="provider_id is required for full_report action")
                result = self._full_report(provider_id)
                return SkillResult(success=True, data=result)

            else:
                return SkillResult(success=False, error=f"Unknown action: {action}")

        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _find_provider(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """Look up a provider by ID or NPI."""
        if provider_id in SAMPLE_PROVIDERS:
            return SAMPLE_PROVIDERS[provider_id]
        for pid, prov in SAMPLE_PROVIDERS.items():
            if prov.get("npi") == provider_id:
                return prov
        return None

    def _check_status(self, provider_id: str, credential_type: str) -> Dict[str, Any]:
        """Check credentialing status for a specific provider."""
        provider = self._find_provider(provider_id)
        if not provider:
            return {
                "provider_id": provider_id,
                "found": False,
                "message": f"Provider {provider_id} not found in credentialing database"
            }

        credentials = provider.get("credentials", {})
        today = date.today()

        status_items = []

        if credential_type == "all":
            types_to_check = list(credentials.keys())
        else:
            types_to_check = [credential_type] if credential_type in credentials else []

        for ctype in types_to_check:
            cred_data = credentials[ctype]
            type_info = CREDENTIAL_TYPES.get(ctype, {})

            if isinstance(cred_data, list):
                # Handle list-based credentials (hospital_privileges, payer_enrollment)
                for item in cred_data:
                    item_status = self._evaluate_credential_item(ctype, item, today, type_info)
                    status_items.append(item_status)
            elif isinstance(cred_data, dict):
                item_status = self._evaluate_credential_item(ctype, cred_data, today, type_info)
                status_items.append(item_status)

        overall_status = "compliant"
        if any(s["status"] == "expired" for s in status_items):
            overall_status = "non_compliant"
        elif any(s["status"] == "expiring_soon" for s in status_items):
            overall_status = "action_required"
        elif any(s["status"] == "pending" for s in status_items):
            overall_status = "action_required"

        return {
            "provider_id": provider_id,
            "provider_name": provider.get("name", ""),
            "npi": provider.get("npi", ""),
            "specialty": provider.get("specialty", ""),
            "overall_status": overall_status,
            "credential_statuses": status_items,
            "checked_date": today.isoformat()
        }

    def _evaluate_credential_item(self, ctype: str, item: Dict[str, Any], today: date, type_info: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a single credential item's status."""
        expiry_str = item.get("expiry_date") or item.get("revalidation_due")
        raw_status = item.get("status", "unknown")
        grace_days = type_info.get("grace_period_days", 0)

        if not expiry_str:
            # NPI has no expiry
            if ctype == "npi":
                return {
                    "credential_type": ctype,
                    "label": type_info.get("label", ctype),
                    "status": "active" if raw_status == "active" else raw_status,
                    "details": item
                }
            return {
                "credential_type": ctype,
                "label": type_info.get("label", ctype),
                "status": raw_status,
                "details": item
            }

        expiry_date = date.fromisoformat(expiry_str)
        days_until_expiry = (expiry_date - today).days

        if raw_status == "expired" or days_until_expiry < -grace_days:
            computed_status = "expired"
        elif days_until_expiry <= 30 + grace_days:
            computed_status = "expiring_soon"
        elif raw_status == "pending":
            computed_status = "pending"
        else:
            computed_status = "active"

        return {
            "credential_type": ctype,
            "label": type_info.get("label", ctype),
            "status": computed_status,
            "expiry_date": expiry_str,
            "days_until_expiry": days_until_expiry,
            "grace_period_remaining": max(0, grace_days + days_until_expiry) if days_until_expiry < 0 else grace_days,
            "revalidation_cycle_months": type_info.get("revalidation_cycle_months", 0),
            "details": item
        }

    def _get_upcoming_expirations(self, provider_id: str, days_ahead: int) -> Dict[str, Any]:
        """Get credentials expiring within the specified window."""
        today = date.today()
        cutoff = today + timedelta(days=days_ahead)
        expirations = []

        providers_to_check = {}
        if provider_id:
            provider = self._find_provider(provider_id)
            if provider:
                providers_to_check[provider_id] = provider
            else:
                return {
                    "provider_id": provider_id,
                    "found": False,
                    "expirations": [],
                    "message": f"Provider {provider_id} not found"
                }
        else:
            providers_to_check = SAMPLE_PROVIDERS

        for pid, provider in providers_to_check.items():
            credentials = provider.get("credentials", {})
            for ctype, cred_data in credentials.items():
                type_info = CREDENTIAL_TYPES.get(ctype, {})

                if isinstance(cred_data, list):
                    for item in cred_data:
                        expiry_str = item.get("expiry_date") or item.get("revalidation_due")
                        if expiry_str:
                            expiry_date = date.fromisoformat(expiry_str)
                            if today <= expiry_date <= cutoff:
                                expirations.append({
                                    "provider_id": pid,
                                    "provider_name": provider.get("name", ""),
                                    "credential_type": ctype,
                                    "label": type_info.get("label", ctype),
                                    "expiry_date": expiry_str,
                                    "days_until_expiry": (expiry_date - today).days,
                                    "grace_period_days": type_info.get("grace_period_days", 0),
                                    "details": item
                                })
                elif isinstance(cred_data, dict):
                    expiry_str = cred_data.get("expiry_date") or cred_data.get("revalidation_due")
                    if expiry_str:
                        expiry_date = date.fromisoformat(expiry_str)
                        if today <= expiry_date <= cutoff:
                            expirations.append({
                                "provider_id": pid,
                                "provider_name": provider.get("name", ""),
                                "credential_type": ctype,
                                "label": type_info.get("label", ctype),
                                "expiry_date": expiry_str,
                                "days_until_expiry": (expiry_date - today).days,
                                "grace_period_days": type_info.get("grace_period_days", 0),
                                "details": cred_data
                            })

        expirations.sort(key=lambda x: x["days_until_expiry"])

        return {
            "check_date": today.isoformat(),
            "window_days": days_ahead,
            "cutoff_date": cutoff.isoformat(),
            "total_expirations": len(expirations),
            "expirations": expirations
        }

    def _generate_checklist(self, credential_type: str) -> Dict[str, Any]:
        """Generate a credentialing checklist for a specific credential type."""
        if credential_type == "all":
            checklists = []
            for ctype, type_info in CREDENTIAL_TYPES.items():
                checklists.append({
                    "credential_type": ctype,
                    "label": type_info["label"],
                    "revalidation_cycle_months": type_info["revalidation_cycle_months"],
                    "grace_period_days": type_info["grace_period_days"],
                    "required_documents": type_info["required_documents"],
                    "notes": type_info["notes"]
                })
            return {
                "checklist_type": "all_credentials",
                "credential_types": checklists,
                "total_documents": sum(len(t["required_documents"]) for t in CREDENTIAL_TYPES.values())
            }
        else:
            type_info = CREDENTIAL_TYPES.get(credential_type)
            if not type_info:
                return {
                    "credential_type": credential_type,
                    "found": False,
                    "message": f"Unknown credential type: {credential_type}. Valid types: {', '.join(CREDENTIAL_TYPES.keys())}"
                }
            return {
                "credential_type": credential_type,
                "label": type_info["label"],
                "revalidation_cycle_months": type_info["revalidation_cycle_months"],
                "grace_period_days": type_info["grace_period_days"],
                "required_documents": type_info["required_documents"],
                "notes": type_info["notes"]
            }

    def _full_report(self, provider_id: str) -> Dict[str, Any]:
        """Generate a comprehensive credentialing report for a provider."""
        provider = self._find_provider(provider_id)
        if not provider:
            return {
                "provider_id": provider_id,
                "found": False,
                "message": f"Provider {provider_id} not found in credentialing database"
            }

        credentials = provider.get("credentials", {})
        today = date.today()

        # Check status for all credentials
        status_result = self._check_status(provider_id, "all")

        # Find upcoming expirations (365 days)
        expirations_result = self._get_upcoming_expirations(provider_id, 365)

        # Identify issues
        issues = []
        for cs in status_result["credential_statuses"]:
            if cs["status"] == "expired":
                issues.append({
                    "severity": "critical",
                    "credential_type": cs["credential_type"],
                    "message": f"{cs['label']} is expired",
                    "action": f"Renew {cs['label']} immediately. Grace period may have elapsed."
                })
            elif cs["status"] == "expiring_soon":
                issues.append({
                    "severity": "warning",
                    "credential_type": cs["credential_type"],
                    "message": f"{cs['label']} expires in {cs.get('days_until_expiry', '?')} days",
                    "action": f"Initiate renewal process for {cs['label']} before expiration."
                })
            elif cs["status"] == "pending":
                issues.append({
                    "severity": "warning",
                    "credential_type": cs["credential_type"],
                    "message": f"{cs['label']} is in pending status",
                    "action": f"Follow up on pending {cs['label']} application/credential."
                })

        # Credentialing completeness assessment
        required_types = ["state_license", "dea", "board_cert", "npi", "malpractice_insurance"]
        missing = [t for t in required_types if t not in credentials]

        return {
            "provider_id": provider_id,
            "provider_name": provider.get("name", ""),
            "npi": provider.get("npi", ""),
            "specialty": provider.get("specialty", ""),
            "report_date": today.isoformat(),
            "overall_status": status_result["overall_status"],
            "credential_summary": {
                "total_credentials": len(status_result["credential_statuses"]),
                "active": sum(1 for s in status_result["credential_statuses"] if s["status"] == "active"),
                "expiring_soon": sum(1 for s in status_result["credential_statuses"] if s["status"] == "expiring_soon"),
                "expired": sum(1 for s in status_result["credential_statuses"] if s["status"] == "expired"),
                "pending": sum(1 for s in status_result["credential_statuses"] if s["status"] == "pending"),
            },
            "credential_statuses": status_result["credential_statuses"],
            "upcoming_expirations_365d": expirations_result["expirations"],
            "issues": issues,
            "missing_required_credentials": missing,
            "recommendations": self._generate_recommendations(issues, missing)
        }

    def _generate_recommendations(self, issues: List[Dict[str, Any]], missing: List[str]) -> List[str]:
        """Generate actionable recommendations."""
        recs = []
        critical_issues = [i for i in issues if i["severity"] == "critical"]
        warnings = [i for i in issues if i["severity"] == "warning"]

        if critical_issues:
            recs.append(f"URGENT: {len(critical_issues)} credential(s) are expired. Resolve immediately to avoid billing and practice interruptions.")
        if warnings:
            recs.append(f"ATTENTION: {len(warnings)} credential(s) require action (expiring soon or pending). Initiate renewal processes promptly.")
        if missing:
            missing_labels = [CREDENTIAL_TYPES.get(m, {}).get("label", m) for m in missing]
            recs.append(f"Missing required credentials: {', '.join(missing_labels)}. Apply for these to achieve full credentialing compliance.")
        if not issues and not missing:
            recs.append("All credentials are current and compliant. Continue monitoring revalidation dates.")

        return recs