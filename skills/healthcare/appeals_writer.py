"""
Aethera AI - Appeals Writer Skill

Generate appeals letters with regulatory citations. Takes denial codes,
procedure codes, diagnosis, and clinical rationale. Produces a structured
appeal letter with recipient address, reference info, clinical justification,
regulatory citations (CFR, CMS manual), supporting documentation checklist,
and requested action.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from skills.skill_base import AetheraSkill, SkillResult, skill


@skill(name="appeals_writer", category="healthcare")
class AppealsWriterSkill(AetheraSkill):
    """
    Generate structured appeals letters with regulatory citations.
    """

    @property
    def name(self) -> str:
        return "appeals_writer"

    @property
    def description(self) -> str:
        return "Generate appeals letters with regulatory citations for claim denials"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "denial_codes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "CARC/RARC codes for the denial (e.g., CO-50, N130)"
                },
                "procedure_codes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "CPT/HCPCS procedure codes that were denied"
                },
                "diagnosis_codes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "ICD-10-CM diagnosis codes supporting the claim"
                },
                "claim_number": {
                    "type": "string",
                    "description": "Original claim number"
                },
                "denial_date": {
                    "type": "string",
                    "description": "Date of denial (YYYY-MM-DD)"
                },
                "billed_amount": {
                    "type": "number",
                    "description": "Amount originally billed"
                },
                "payer_name": {
                    "type": "string",
                    "description": "Name of the insurance payer"
                },
                "payer_address": {
                    "type": "string",
                    "description": "Payer appeals mailing address"
                },
                "provider_name": {
                    "type": "string",
                    "description": "Healthcare provider or practice name"
                },
                "provider_npi": {
                    "type": "string",
                    "description": "Provider NPI number"
                },
                "provider_address": {
                    "type": "string",
                    "description": "Provider mailing address"
                },
                "patient_name": {
                    "type": "string",
                    "description": "Patient name (or initials for privacy)"
                },
                "patient_id": {
                    "type": "string",
                    "description": "Patient member ID or subscriber number"
                },
                "date_of_service": {
                    "type": "string",
                    "description": "Date(s) of service (YYYY-MM-DD)"
                },
                "clinical_rationale": {
                    "type": "string",
                    "description": "Clinical rationale for why the service was medically necessary"
                },
                "appeal_level": {
                    "type": "string",
                    "enum": ["initial", "redetermination", "reconsideration", "administrative_law_judge", "council"],
                    "description": "Level of appeal"
                }
            },
            "required": ["denial_codes", "procedure_codes", "payer_name"]
        }

    @property
    def requires_phi_protection(self) -> bool:
        return True

    @property
    def examples(self) -> list:
        return [
            {
                "input": {
                    "denial_codes": ["CO-50"],
                    "procedure_codes": ["97110", "97112"],
                    "diagnosis_codes": ["M54.5"],
                    "payer_name": "Medicare",
                    "clinical_rationale": "Patient has chronic low back pain with functional limitations despite 6 weeks of conservative treatment including medication and home exercise program."
                }
            }
        ]

    # --- CARC code to regulatory citation mapping ---
    DENIAL_CITATIONS: Dict[str, Dict[str, Any]] = {
        "CO-4": {
            "description": "Procedure code inconsistent with modifier or missing modifier",
            "cfr": "42 CFR 414.24 - Payment for physician services",
            "cms_manual": "CMS IOM 100-04, Chapter 1, Section 40.2 - Correct Use of Modifiers",
            "appeal_basis": "The modifier appended to the procedure code accurately reflects the service performed as documented in the medical record. The claim was submitted with the appropriate modifier consistent with CMS guidelines.",
            "required_evidence": ["operative_report", "progress_notes"]
        },
        "CO-11": {
            "description": "Diagnosis inconsistent with procedure",
            "cfr": "42 CFR 424.5 - Requirements for diagnostic tests",
            "cms_manual": "CMS IOM 100-04, Chapter 1, Section 20.2 - Diagnosis Code Requirements",
            "appeal_basis": "The submitted diagnosis code(s) accurately represent the patient's condition and support the medical necessity of the procedure performed, as documented in the medical record.",
            "required_evidence": ["medical_records", "progress_notes"]
        },
        "CO-16": {
            "description": "Claim lacks information for adjudication",
            "cfr": "42 CFR 424.32 - Requirements for claims",
            "cms_manual": "CMS IOM 100-04, Chapter 1, Section 10 - Claim Submission Requirements",
            "appeal_basis": "All required information for proper adjudication has been submitted. The claim contains complete and accurate data as required by CMS guidelines.",
            "required_evidence": ["corrected_claim", "supporting_documents"]
        },
        "CO-18": {
            "description": "Duplicate claim",
            "cfr": "42 CFR 440.188 - Limitation on provider billing",
            "cms_manual": "CMS IOM 100-04, Chapter 1, Section 50.1 - Duplicate Claims",
            "appeal_basis": "This is not a duplicate claim. The services billed are distinct from any previously adjudicated claims, as evidenced by different dates of service, different procedures, or different diagnoses.",
            "required_evidence": ["claim_comparison", "medical_records"]
        },
        "CO-22": {
            "description": "Coordination of benefits",
            "cfr": "42 CFR 422.214 - Coordination of benefits",
            "cms_manual": "CMS IOM 100-05, Chapter 3 - Coordination of Benefits",
            "appeal_basis": "This claim is appropriately submitted to this payer as the primary/secondary insurer per coordination of benefits rules.",
            "required_evidence": ["cob_information", "other_payer_eob"]
        },
        "CO-50": {
            "description": "Not medically necessary",
            "cfr": "42 CFR 410.32 - Diagnostic tests",
            "cms_manual": "CMS IOM 100-04, Chapter 1, Section 80.3 - Medical Necessity",
            "appeal_basis": "The service was medically necessary based on the patient's clinical condition, documented symptoms, and the applicable coverage criteria. The treatment aligns with accepted standards of medical practice.",
            "required_evidence": ["medical_records", "clinical_guidelines", "physician_statement"]
        },
        "CO-97": {
            "description": "Payment adjusted - bundled",
            "cfr": "42 CFR 414.2 - Definitions (bundling/unbundling)",
            "cms_manual": "CMS IOM 100-04, Chapter 1, Section 40.6 - NCCI Edits",
            "appeal_basis": "The procedures billed are distinct services that should not be bundled. They were performed at separate sites, during separate sessions, or for separate conditions as documented in the medical record.",
            "required_evidence": ["operative_report", "medical_records", "distinct_documentation"]
        },
        "PR-1": {
            "description": "Deductible amount",
            "cfr": "42 CFR 422.104 - Benefit category",
            "cms_manual": "CMS IOM 100-04, Chapter 1, Section 60 - Patient Responsibility",
            "appeal_basis": "Patient responsibility adjustments (deductible, coinsurance, copay) are contractual and generally not appealable to the payer. May pursue patient balance.",
            "required_evidence": ["patient_billing_records"]
        },
    }

    # --- Regulatory reference library ---
    REGULATORY_REFERENCES: Dict[str, Dict[str, str]] = {
        "42 CFR 410.32": {
            "title": "Diagnostic Tests",
            "summary": "Requires that diagnostic tests be reasonable and necessary for the diagnosis or treatment of the patient's condition, ordered by the treating physician, and performed by qualified personnel."
        },
        "42 CFR 414.2": {
            "title": "Definitions - Bundling/Unbundling",
            "summary": "Defines bundling as including all services integral to a procedure in the reimbursement for that procedure. Unbundling (billing separately) is prohibited unless criteria for separate billing are met."
        },
        "42 CFR 414.24": {
            "title": "Payment for Physician Services",
            "summary": "Establishes the Medicare Physician Fee Schedule payment methodology and proper coding requirements including modifier usage."
        },
        "42 CFR 424.5": {
            "title": "Requirements for Diagnostic Tests",
            "summary": "Specifies requirements for ordering and performing diagnostic tests including medical necessity criteria."
        },
        "42 CFR 424.32": {
            "title": "Requirements for Claims",
            "summary": "Details the information that must be included on Medicare claims for proper processing."
        },
        "42 CFR 422.214": {
            "title": "Coordination of Benefits",
            "summary": "Establishes rules for determining which payer is primary and which is secondary when a beneficiary has multiple coverage."
        },
        "42 CFR 440.188": {
            "title": "Limitation on Provider Billing",
            "summary": "Limits on billing practices including prohibitions on duplicate billing."
        },
        "42 CFR 405.940-405.986": {
            "title": "Medicare Appeals Process",
            "summary": "Establishes the five-level Medicare appeals process: Redetermination, Reconsideration by QIC, ALJ hearing, Council review, and Federal court review."
        },
        "Social Security Act 1862(a)(1)(A)": {
            "title": "Reasonable and Necessary Requirement",
            "summary": "The foundational statute requiring that Medicare only pay for items and services that are reasonable and necessary for the diagnosis or treatment of illness or injury."
        },
        "Social Security Act 1862(a)(1)(D)": {
            "title": "Investigational/Experimental Exclusion",
            "summary": "Excludes payment for services that are experimental or investigational unless part of a qualifying clinical trial."
        },
    }

    # --- Appeal timeline by level ---
    APPEAL_TIMELINES: Dict[str, Dict[str, Any]] = {
        "initial": {
            "deadline_days": 180,
            "payer_response_days": 30,
            "description": "Initial appeal to the payer (commercial) or Redetermination (Medicare)",
            "next_level": "redetermination"
        },
        "redetermination": {
            "deadline_days": 180,
            "payer_response_days": 60,
            "description": "Medicare redetermination by MAC",
            "next_level": "reconsideration"
        },
        "reconsideration": {
            "deadline_days": 180,
            "payer_response_days": 60,
            "description": "Reconsideration by Qualified Independent Contractor (QIC)",
            "next_level": "administrative_law_judge"
        },
        "administrative_law_judge": {
            "deadline_days": 60,
            "payer_response_days": 90,
            "description": "Administrative Law Judge (ALJ) hearing - minimum amount in controversy required",
            "next_level": "council"
        },
        "council": {
            "deadline_days": 60,
            "payer_response_days": 60,
            "description": "Medicare Appeals Council review",
            "next_level": "federal_court"
        }
    }

    # --- Documentation checklist templates ---
    DOCUMENTATION_CHECKLISTS: Dict[str, List[str]] = {
        "medical_necessity": [
            "Complete medical records for dates of service",
            "Physician's signed statement of medical necessity",
            "History and physical examination documentation",
            "Treatment plan showing progression of care",
            "Documentation of prior conservative treatments attempted",
            "Relevant peer-reviewed literature supporting treatment",
            "LCD/NCD coverage criteria documentation",
            "Laboratory/diagnostic results supporting diagnosis",
            "Specialist consultation notes (if applicable)",
            "Medication records and response documentation"
        ],
        "modifier_dispute": [
            "Operative report detailing distinct procedures",
            "Documentation of separate anatomical sites",
            "Documentation of separate sessions/encounters",
            "Progress notes showing distinct diagnoses",
            "Time-based documentation for time-based codes",
            "Consent forms and procedural notes"
        ],
        "bundling_dispute": [
            "Operative report showing distinct procedures",
            "Documentation of separate incisions/excisions",
            "Documentation of separate encounters",
            "Documentation of separate organ/structure involvement",
            "Anesthesia records showing distinct procedures",
            "Pathology reports (if applicable)"
        ],
        "duplicate_claim_dispute": [
            "Comparison of original and resubmitted claims",
            "Documentation of different dates of service",
            "Documentation of different procedure codes",
            "Documentation of different diagnoses",
            "EOB from prior adjudication showing different service"
        ],
        "missing_information": [
            "Corrected claim form with all required fields",
            "Missing demographic information",
            "Missing provider information (NPI, taxonomy)",
            "Missing referral/authorization numbers",
            "Missing diagnosis pointer information"
        ]
    }

    async def execute(self, **kwargs) -> SkillResult:
        denial_codes = kwargs.get("denial_codes", [])
        procedure_codes = kwargs.get("procedure_codes", [])
        diagnosis_codes = kwargs.get("diagnosis_codes", [])
        claim_number = kwargs.get("claim_number", "")
        denial_date = kwargs.get("denial_date", "")
        billed_amount = kwargs.get("billed_amount", 0)
        payer_name = kwargs.get("payer_name", "")
        payer_address = kwargs.get("payer_address", "")
        provider_name = kwargs.get("provider_name", "")
        provider_npi = kwargs.get("provider_npi", "")
        provider_address = kwargs.get("provider_address", "")
        patient_name = kwargs.get("patient_name", "")
        patient_id = kwargs.get("patient_id", "")
        date_of_service = kwargs.get("date_of_service", "")
        clinical_rationale = kwargs.get("clinical_rationale", "")
        appeal_level = kwargs.get("appeal_level", "initial")

        if not denial_codes:
            return SkillResult(success=False, error="At least one denial code is required")
        if not procedure_codes:
            return SkillResult(success=False, error="Procedure codes are required")
        if not payer_name:
            return SkillResult(success=False, error="Payer name is required")

        try:
            letter = self._generate_appeal_letter(
                denial_codes=denial_codes,
                procedure_codes=procedure_codes,
                diagnosis_codes=diagnosis_codes,
                claim_number=claim_number,
                denial_date=denial_date,
                billed_amount=billed_amount,
                payer_name=payer_name,
                payer_address=payer_address,
                provider_name=provider_name,
                provider_npi=provider_npi,
                provider_address=provider_address,
                patient_name=patient_name,
                patient_id=patient_id,
                date_of_service=date_of_service,
                clinical_rationale=clinical_rationale,
                appeal_level=appeal_level
            )
            return SkillResult(success=True, data=letter)
        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _generate_appeal_letter(
        self,
        denial_codes: List[str],
        procedure_codes: List[str],
        diagnosis_codes: List[str],
        claim_number: str,
        denial_date: str,
        billed_amount: float,
        payer_name: str,
        payer_address: str,
        provider_name: str,
        provider_npi: str,
        provider_address: str,
        patient_name: str,
        patient_id: str,
        date_of_service: str,
        clinical_rationale: str,
        appeal_level: str
    ) -> Dict[str, Any]:
        """Generate a complete structured appeal letter."""

        today = datetime.now().strftime("%B %d, %Y")

        # Decode denial codes and get citations
        denial_details = []
        all_citations = []
        all_checklist_items = []

        for code in denial_codes:
            code_upper = code.upper()
            if code_upper in self.DENIAL_CITATIONS:
                detail = self.DENIAL_CITATIONS[code_upper]
                denial_details.append({
                    "code": code_upper,
                    "description": detail["description"],
                    "appeal_basis": detail["appeal_basis"]
                })
                all_citations.append({
                    "cfr": detail["cfr"],
                    "cms_manual": detail["cms_manual"],
                    "denial_code": code_upper
                })
                # Add relevant checklist
                checklist_key = self._map_checklist(code_upper)
                if checklist_key and checklist_key in self.DOCUMENTATION_CHECKLISTS:
                    for item in self.DOCUMENTATION_CHECKLISTS[checklist_key]:
                        if item not in all_checklist_items:
                            all_checklist_items.append(item)
            else:
                denial_details.append({
                    "code": code_upper,
                    "description": f"Denial code {code_upper}",
                    "appeal_basis": f"The denial under code {code_upper} is being contested based on the clinical documentation and applicable coverage guidelines."
                })

        # Build the appeal letter body
        appeal_basis_paragraphs = []
        for dd in denial_details:
            appeal_basis_paragraphs.append(dd["appeal_basis"])

        # Clinical justification section
        clinical_justification = self._build_clinical_justification(
            clinical_rationale, denial_codes, procedure_codes, diagnosis_codes
        )

        # Regulatory citations section
        regulatory_section = self._build_regulatory_section(all_citations)

        # Appeal timeline
        timeline = self.APPEAL_TIMELINES.get(appeal_level, self.APPEAL_TIMELINES["initial"])

        # Compose full letter text
        letter_text = self._compose_letter(
            today=today,
            payer_name=payer_name,
            payer_address=payer_address,
            provider_name=provider_name,
            provider_address=provider_address,
            provider_npi=provider_npi,
            patient_name=patient_name,
            patient_id=patient_id,
            claim_number=claim_number,
            denial_date=denial_date,
            date_of_service=date_of_service,
            denial_codes=denial_codes,
            procedure_codes=procedure_codes,
            diagnosis_codes=diagnosis_codes,
            billed_amount=billed_amount,
            appeal_basis_paragraphs=appeal_basis_paragraphs,
            clinical_justification=clinical_justification,
            regulatory_section=regulatory_section,
            appeal_level=appeal_level,
            timeline=timeline
        )

        return {
            "letter": letter_text,
            "metadata": {
                "generated_date": today,
                "appeal_level": appeal_level,
                "denial_codes": denial_codes,
                "procedure_codes": procedure_codes,
                "diagnosis_codes": diagnosis_codes
            },
            "reference_info": {
                "claim_number": claim_number,
                "patient_id": patient_id,
                "provider_npi": provider_npi,
                "payer": payer_name
            },
            "denial_details": denial_details,
            "regulatory_citations": all_citations,
            "clinical_justification": clinical_justification,
            "supporting_documentation_checklist": all_checklist_items,
            "appeal_timeline": {
                "level": appeal_level,
                "deadline_days": timeline["deadline_days"],
                "expected_response_days": timeline["payer_response_days"],
                "description": timeline["description"],
                "next_level": timeline["next_level"]
            },
            "requested_action": self._build_requested_action(billed_amount, appeal_level)
        }

    def _map_checklist(self, denial_code: str) -> Optional[str]:
        """Map denial code to documentation checklist category."""
        mapping = {
            "CO-4": "modifier_dispute",
            "CO-11": "medical_necessity",
            "CO-16": "missing_information",
            "CO-18": "duplicate_claim_dispute",
            "CO-22": "missing_information",
            "CO-50": "medical_necessity",
            "CO-97": "bundling_dispute",
        }
        return mapping.get(denial_code.upper())

    def _build_clinical_justification(
        self,
        clinical_rationale: str,
        denial_codes: List[str],
        procedure_codes: List[str],
        diagnosis_codes: List[str]
    ) -> str:
        """Build clinical justification section."""
        justification_parts = []

        if clinical_rationale:
            justification_parts.append(f"Clinical Rationale: {clinical_rationale}")

        # Add procedure-specific context
        proc_list = ", ".join(procedure_codes)
        justification_parts.append(
            f"The procedure(s) billed ({proc_list}) were performed based on the patient's "
            f"documented clinical condition and are consistent with accepted medical practice "
            f"for the diagnosis(es) submitted."
        )

        # Add diagnosis context
        if diagnosis_codes:
            dx_list = ", ".join(diagnosis_codes)
            justification_parts.append(
                f"The supporting diagnosis code(s) ({dx_list}) accurately represent the patient's "
                f"condition as documented in the medical record and support the medical necessity "
                f"of the service(s) rendered."
            )

        # Add denial-specific clinical arguments
        for code in denial_codes:
            code_upper = code.upper()
            if code_upper == "CO-50":
                justification_parts.append(
                    "The service meets the applicable medical necessity criteria as defined by "
                    "the payer's coverage determination policy and CMS guidelines. The patient's "
                    "clinical presentation, as documented in the enclosed medical records, "
                    "clearly supports the need for this service. Alternative treatments were "
                    "considered and either attempted without adequate improvement or were not "
                    "appropriate given the patient's condition."
                )
            elif code_upper == "CO-97":
                justification_parts.append(
                    "The procedures billed are distinct services that meet the criteria for "
                    "separate reimbursement. They were performed at separate anatomical sites, "
                    "during separate sessions, or addressed separate clinical conditions as "
                    "documented in the operative report and medical records."
                )
            elif code_upper == "CO-11":
                justification_parts.append(
                    "The relationship between the diagnosis and the procedure is well-established "
                    "in medical literature and is consistent with standard clinical practice. "
                    "The enclosed documentation demonstrates the clinical basis for the procedure "
                    "in the context of the patient's diagnosed condition."
                )

        return " ".join(justification_parts)

    def _build_regulatory_section(self, citations: List[Dict[str, Any]]) -> str:
        """Build regulatory citations section."""
        if not citations:
            return "No specific regulatory citations identified for the given denial codes."

        sections = []
        for cite in citations:
            cfr = cite.get("cfr", "")
            cms_manual = cite.get("cms_manual", "")
            denial_code = cite.get("denial_code", "")

            parts = [f"For denial code {denial_code}:"]
            if cfr and cfr in self.REGULATORY_REFERENCES:
                ref = self.REGULATORY_REFERENCES[cfr]
                parts.append(
                    f"  - {cfr} ({ref['title']}): {ref['summary']}"
                )
            elif cfr:
                parts.append(f"  - {cfr}")
            if cms_manual:
                parts.append(f"  - {cms_manual}")
            sections.append(" ".join(parts))

        return " ".join(sections)

    def _compose_letter(
        self,
        today: str,
        payer_name: str,
        payer_address: str,
        provider_name: str,
        provider_address: str,
        provider_npi: str,
        patient_name: str,
        patient_id: str,
        claim_number: str,
        denial_date: str,
        date_of_service: str,
        denial_codes: List[str],
        procedure_codes: List[str],
        diagnosis_codes: List[str],
        billed_amount: float,
        appeal_basis_paragraphs: List[str],
        clinical_justification: str,
        regulatory_section: str,
        appeal_level: str,
        timeline: Dict[str, Any]
    ) -> str:
        """Compose the full letter text."""

        # Recipient block
        recipient = payer_name
        if payer_address:
            recipient += f"\n{payer_address}"

        # Reference block
        ref_lines = [
            f"Claim Number: {claim_number or '[Not Provided]'}",
            f"Date of Denial: {denial_date or '[Not Provided]'}",
            f"Date of Service: {date_of_service or '[Not Provided]'}",
            f"Patient: {patient_name or '[Protected]'} (ID: {patient_id or '[Not Provided]'})",
            f"Provider NPI: {provider_npi or '[Not Provided]'}",
            f"Denied Procedure(s): {', '.join(procedure_codes)}",
            f"Diagnosis Code(s): {', '.join(diagnosis_codes) if diagnosis_codes else '[Not Provided]'}",
            f"Denial Code(s): {', '.join(denial_codes)}",
            f"Billed Amount: ${billed_amount:,.2f}" if billed_amount else "Billed Amount: [Not Provided]",
        ]

        # Level label
        level_labels = {
            "initial": "First-Level Appeal",
            "redetermination": "Request for Redetermination",
            "reconsideration": "Request for Reconsideration",
            "administrative_law_judge": "Request for Administrative Law Judge Hearing",
            "council": "Request for Medicare Appeals Council Review"
        }
        level_label = level_labels.get(appeal_level, "Appeal")

        letter = f"""{provider_name or '[Provider Name]'}
{provider_address or '[Provider Address]'}

{today}

{recipient}

RE: {level_label} - Claim {claim_number or '[Claim Number]'}

Dear {payer_name} Appeals Department,

I am writing on behalf of {provider_name or '[Provider Name]'} to formally appeal the denial of services for the above-referenced claim. The claim was denied under the following code(s): {', '.join(denial_codes)}.

REFERENCE INFORMATION:
{chr(10).join(ref_lines)}

BASIS FOR APPEAL:

{'  '.join(appeal_basis_paragraphs)}

CLINICAL JUSTIFICATION:

{clinical_justification}

REGULATORY AUTHORITY:

{regulatory_section}

This appeal is filed pursuant to 42 CFR 405.940-405.986 (Medicare Appeals Process) and applicable state insurance regulations. We respectfully request that you reconsider this denial based on the enclosed documentation and the regulatory provisions cited above.

REQUESTED ACTION:

We request that the denial be reversed and the claim be processed for payment in full. The services rendered were medically necessary, properly coded, and fully documented in the enclosed records.

This appeal must be adjudicated within {timeline['payer_response_days']} days per regulatory requirements. Failure to respond within the required timeframe may result in deemed reversal of the denial.

Sincerely,

{provider_name or '[Provider Name]'}
{provider_address or '[Provider Address]'}
NPI: {provider_npi or '[NPI]'}

Enclosures: See attached supporting documentation checklist
"""
        return letter

    def _build_requested_action(self, billed_amount: float, appeal_level: str) -> Dict[str, Any]:
        """Build the requested action section."""
        return {
            "action": "Reverse denial and process claim for payment",
            "amount_requested": billed_amount,
            "appeal_level": appeal_level,
            "statement": (
                "We respectfully request that the denial be overturned and the claim "
                "be adjudicated for payment in the full billed amount. The services "
                "were medically necessary, properly coded, appropriately documented, "
                "and submitted in compliance with all applicable payer requirements "
                "and regulatory guidelines."
            )
        }