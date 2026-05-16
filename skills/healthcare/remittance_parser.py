"""
Aethera AI - Remittance Parser Skill

Parse ERA/EOB (835) remittance advice documents.
"""

from typing import Dict, Any, List, Optional
import re

from skills.skill_base import AetheraSkill, SkillResult, skill


# CARC code database (shared with denial_analyzer, duplicated here for self-containment)
CARC_CODES: Dict[str, str] = {
    "CO-4": "Procedure code inconsistent with modifier or missing modifier",
    "CO-11": "Diagnosis inconsistent with procedure",
    "CO-16": "Claim/service lacks information needed for adjudication",
    "CO-18": "Duplicate claim/service",
    "CO-22": "Coordination of benefits (this care may be covered by another payer)",
    "CO-27": "Expenses incurred after coverage terminated",
    "CO-29": "Time limit for filing has expired",
    "CO-45": "Charges exceed your contracted/legislated fee arrangement",
    "CO-50": "Not medically necessary",
    "CO-97": "Payment adjusted because already adjudicated (bundled)",
    "PR-1": "Deductible amount",
    "PR-2": "Coinsurance amount",
    "PR-3": "Copay amount",
    "PR-84": "Capital DRG adjustment",
    "OA-23": "Impact of prior payer adjudication",
    "CO-5": "Procedure/code was not paid as billed; paid per alternate fee schedule",
    "CO-7": "Payment reduced based on allowed amount (fee schedule)",
    "CO-9": "No payment issued; covered by other payer per COB",
    "CO-12": "Services not documented in patients' medical records",
    "CO-15": "Authorization/pre-certification absent or exceeded",
    "CO-19": "Claim denied as not medically necessary for this diagnosis",
    "CO-24": "Charges covered under capitation or risk agreement",
    "CO-26": "Expenses incurred prior to coverage effective date",
    "CO-39": "Services denied at time of pre-cert review",
    "CO-96": "Non-covered charges",
    "CO-109": "Claim not covered by this payer; submit to correct payer",
    "CO-197": "Precertification/authorization/notification absent",
    "PR-96": "Patient paid amount; non-covered service",
    "PR-204": "Service not covered by this payer; patient is responsible",
    "OA-27": "Expenses incurred after coverage terminated",
    "PI-1": "Contractual obligation; payment per fee schedule",
    "PI-14": "Adjustment based on prior payer payment or adjudication",
}

# RARC code database
RARC_CODES: Dict[str, str] = {
    "N130": "Claim/service denied based on plan policy",
    "M21": "Missing/incomplete/invalid primary diagnosis code",
    "M87": "Missing/incomplete/invalid modifier",
    "N362": "Separate payment not allowed - bundled",
    "N539": "Prior authorization required",
    "W1": "Workers' Compensation jurisdiction",
    "N290": "Missing/incomplete/invalid attending provider information",
    "N425": "Statutory requirement for provider reimbursement",
    "N522": "Rebill on separate claim; services not billed correctly",
    "N724": "Service not separately payable per NCCI edits",
    "N818": "Service not covered when performed during the same session as another service",
    "M15": "Separately billed services/tests have been bundled as they are considered components of the same procedure",
    "M24": "Missing/incomplete/invalid number of doses per vial",
    "M53": "Missing/incomplete/invalid certificate of medical necessity",
    "M60": "Missing/incomplete/invalid certification",
    "M76": "Missing/incomplete/invalid diagnosis or condition",
    "M79": "Service not paid; missing/incomplete/invalid charge amount",
    "N115": "This decision was based on a National Coverage Determination (NCD)",
    "N200": "Payment based on authorization; verify authorization limits",
    "N211": "Alert: You may not appeal this decision",
    "N382": "Payment based on allowable cost; review contract terms",
    "N432": "Service not covered for this condition/diagnosis",
    "N534": "Submission/billing error(s); resubmit as a new claim",
    "MA01": "Alert: If you do not agree with this determination, you have the right to appeal",
    "MA04": "Secondary payment cannot be calculated without primary payer EOB",
    "MA07": "Claim information is also being forwarded to the patient's secondary payer",
    "MA08": "Alert: Information available to patient through other source",
    "MA13": "Alert: You may be subject to penalties if you bill the patient for amounts not allowed",
    "MA15": "Claim/service rejected; claim lacks information or submission/billing error",
    "MA27": "Penalty for failure to obtain pre-certification; patient not liable",
    "MA30": "Missing/incomplete/invalid type of bill",
    "MA81": "Interest penalty applied; late payment per state law",
    "MA92": "Payment based on approved amount for assigned claim",
    "MA114": "Missing/incomplete/invalid documentation",
    "MA120": "Missing/incomplete/invalid CLIA certification number",
    "MA130": "Claim does not contain enough information for adjudication",
}

# 835 segment identifiers
SEGMENT_TYPES = {
    "ISA": "Interchange Control Header",
    "GS": "Functional Group Header",
    "ST": "Transaction Set Header",
    "BPR": "Financial Information (Total Payment)",
    "TRN": "Trace Number",
    "DTM": "Date/Time Reference",
    "N1": "Party Identification",
    "N3": "Party Location (Address)",
    "N4": "Geographic Location (City/State/Zip)",
    "REF": "Reference Identification",
    "LX": "Service Line Number",
    "CLP": "Claim Level Data",
    "CAS": "Claim Adjustment Segment",
    "NM1": "Entity Name",
    "PLB": "Provider Level Adjustment",
    "SE": "Transaction Set Trailer",
    "GE": "Functional Group Trailer",
    "IEA": "Interchange Control Trailer",
}


@skill(name="remittance_parser", category="healthcare")
class RemittanceParserSkill(AetheraSkill):
    """
    Parse ERA/EOB (835) remittance advice documents.
    """

    @property
    def name(self) -> str:
        return "remittance_parser"

    @property
    def description(self) -> str:
        return "Parse ERA/EOB (835) remittance advice: extract payments, adjustments, denials, patient responsibility"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["parse_835", "summarize", "identify_denials", "calculate_net", "decode_carc", "decode_rarc"],
                    "description": "Action: parse_835 (full parse), summarize, identify_denials, calculate_net, decode_carc, decode_rarc"
                },
                "remittance_text": {
                    "type": "string",
                    "description": "835 ERA text or remittance data to parse"
                },
                "carc_code": {
                    "type": "string",
                    "description": "Single CARC code to decode (for decode_carc action)"
                },
                "rarc_code": {
                    "type": "string",
                    "description": "Single RARC code to decode (for decode_rarc action)"
                },
                "claim_amount": {
                    "type": "number",
                    "description": "Total billed claim amount (for calculate_net)"
                },
                "paid_amount": {
                    "type": "number",
                    "description": "Total paid amount (for calculate_net)"
                },
                "adjustment_amount": {
                    "type": "number",
                    "description": "Total adjustment amount (for calculate_net)"
                },
                "patient_responsibility_amount": {
                    "type": "number",
                    "description": "Total patient responsibility amount (for calculate_net)"
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
            {"input": {"action": "decode_carc", "carc_code": "CO-50"}},
            {"input": {"action": "decode_rarc", "rarc_code": "N130"}},
            {"input": {"action": "calculate_net", "claim_amount": 5000, "paid_amount": 3200, "adjustment_amount": 1200, "patient_responsibility_amount": 600}},
        ]

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "parse_835")

        try:
            if action == "parse_835":
                remittance_text = kwargs.get("remittance_text", "")
                if not remittance_text:
                    return SkillResult(success=False, error="Remittance text is required for parse_835 action")
                result = self._parse_835(remittance_text)

            elif action == "summarize":
                remittance_text = kwargs.get("remittance_text", "")
                if not remittance_text:
                    return SkillResult(success=False, error="Remittance text is required for summarize action")
                result = self._summarize_remittance(remittance_text)

            elif action == "identify_denials":
                remittance_text = kwargs.get("remittance_text", "")
                if not remittance_text:
                    return SkillResult(success=False, error="Remittance text is required for identify_denials action")
                result = self._identify_denials(remittance_text)

            elif action == "calculate_net":
                result = self._calculate_net_payment(kwargs)

            elif action == "decode_carc":
                carc_code = kwargs.get("carc_code", "")
                if not carc_code:
                    return SkillResult(success=False, error="CARC code is required for decode_carc action")
                result = self._decode_carc(carc_code)

            elif action == "decode_rarc":
                rarc_code = kwargs.get("rarc_code", "")
                if not rarc_code:
                    return SkillResult(success=False, error="RARC code is required for decode_rarc action")
                result = self._decode_rarc(rarc_code)

            else:
                return SkillResult(success=False, error=f"Unknown action: {action}")

            return SkillResult(success=True, data=result)

        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _parse_835(self, text: str) -> Dict[str, Any]:
        """Parse an 835 EDI remittance advice document."""
        segments = self._split_segments(text)
        parsed = {
            "header": {},
            "financial_info": {},
            "claims": [],
            "provider_adjustments": [],
            "segment_count": len(segments)
        }

        current_claim = None

        for segment in segments:
            fields = segment.split("*") if "*" in segment else segment.split("|")
            seg_id = fields[0].strip() if fields else ""

            if seg_id == "ISA":
                parsed["header"]["interchange_control"] = {
                    "sender_id": fields[6].strip() if len(fields) > 6 else "",
                    "receiver_id": fields[8].strip() if len(fields) > 8 else "",
                }

            elif seg_id == "BPR":
                parsed["financial_info"] = self._parse_bpr(fields)

            elif seg_id == "TRN":
                if not parsed["financial_info"].get("trace_number"):
                    parsed["financial_info"]["trace_number"] = fields[2].strip() if len(fields) > 2 else ""
                    parsed["financial_info"]["trace_type"] = fields[3].strip() if len(fields) > 3 else ""

            elif seg_id == "DTM":
                dtm = self._parse_dtm(fields)
                if dtm:
                    key = f"date_{dtm['qualifier']}"
                    parsed["financial_info"][key] = dtm["date"]

            elif seg_id == "N1":
                party = self._parse_n1(fields)
                if party:
                    role = party.get("role", "unknown").lower()
                    if "payer" in role:
                        parsed["header"]["payer"] = party
                    elif "payee" in role or "provider" in role:
                        parsed["header"]["payee"] = party

            elif seg_id == "CLP":
                if current_claim:
                    parsed["claims"].append(current_claim)
                current_claim = self._parse_clp(fields)

            elif seg_id == "CAS" and current_claim is not None:
                adjustments = self._parse_cas(fields)
                if adjustments:
                    if "adjustments" not in current_claim:
                        current_claim["adjustments"] = []
                    current_claim["adjustments"].extend(adjustments)

            elif seg_id == "NM1" and current_claim is not None:
                entity = self._parse_nm1(fields)
                if entity:
                    role = entity.get("role_code", "")
                    if role == "QC":
                        current_claim["patient"] = entity
                    elif role == "82":
                        current_claim["rendering_provider"] = entity

            elif seg_id == "LX" and current_claim is not None:
                line_num = fields[1].strip() if len(fields) > 1 else ""
                if "service_lines" not in current_claim:
                    current_claim["service_lines"] = []
                current_claim["service_lines"].append({"line_number": line_num})

            elif seg_id == "PLB":
                plb = self._parse_plb(fields)
                if plb:
                    parsed["provider_adjustments"].append(plb)

        if current_claim:
            parsed["claims"].append(current_claim)

        return parsed

    def _split_segments(self, text: str) -> List[str]:
        """Split 835 text into individual segments."""
        text = text.strip()
        if "~" in text:
            return [s.strip() for s in text.split("~") if s.strip()]
        if "\n" in text:
            return [s.strip() for s in text.split("\n") if s.strip()]
        return [text]

    def _parse_bpr(self, fields: List[str]) -> Dict[str, Any]:
        """Parse BPR (Financial Information) segment."""
        return {
            "transaction_type": fields[1].strip() if len(fields) > 1 else "",
            "total_payment": self._safe_float(fields[2]) if len(fields) > 2 else 0,
            "credit_debit": fields[3].strip() if len(fields) > 3 else "",
            "payment_method": fields[4].strip() if len(fields) > 4 else "",
            "payment_date": fields[16].strip() if len(fields) > 16 else "",
        }

    def _parse_dtm(self, fields: List[str]) -> Optional[Dict[str, Any]]:
        """Parse DTM (Date/Time Reference) segment."""
        if len(fields) < 3:
            return None
        qualifier_map = {
            "036": "expiration",
            "037": "effective",
            "405": "production",
            "472": "service",
            "232": "claim_received",
            "233": "claim_processed",
        }
        qualifier = fields[1].strip()
        date_str = fields[2].strip()
        return {
            "qualifier": qualifier_map.get(qualifier, qualifier),
            "date": date_str,
            "description": qualifier_map.get(qualifier, f"DTM qualifier {qualifier}")
        }

    def _parse_n1(self, fields: List[str]) -> Optional[Dict[str, Any]]:
        """Parse N1 (Party Identification) segment."""
        if len(fields) < 2:
            return None
        role_map = {
            "PR": "Payer",
            "PE": "Payee/Provider",
        }
        entity_id = fields[3].strip() if len(fields) > 3 else ""
        id_qualifier = fields[2].strip() if len(fields) > 2 else ""
        return {
            "role": role_map.get(fields[1].strip(), fields[1].strip()),
            "name": fields[4].strip() if len(fields) > 4 and id_qualifier != fields[4] else "",
            "id": entity_id,
            "id_qualifier": id_qualifier
        }

    def _parse_clp(self, fields: List[str]) -> Dict[str, Any]:
        """Parse CLP (Claim Level Data) segment."""
        claim_status_map = {
            "1": "Processed as primary",
            "2": "Processed as secondary",
            "3": "Processed as tertiary",
            "4": "Denied",
            "19": "Primary payer adjudication to be determined",
            "20": "Secondary payer adjudication to be determined",
            "21": "Tertiary payer adjudication to be determined",
            "22": "Reversal of previous payment",
            "23": "Not our claim, forwarded to another payer",
        }
        status_code = fields[3].strip() if len(fields) > 3 else ""
        return {
            "claim_id": fields[1].strip() if len(fields) > 1 else "",
            "status": claim_status_map.get(status_code, f"Status code {status_code}"),
            "status_code": status_code,
            "charged_amount": self._safe_float(fields[2]) if len(fields) > 2 else 0,
            "paid_amount": self._safe_float(fields[4]) if len(fields) > 4 else 0,
            "patient_responsibility": self._safe_float(fields[5]) if len(fields) > 5 else 0,
            "payer_responsibility": fields[6].strip() if len(fields) > 6 else "",
        }

    def _parse_cas(self, fields: List[str]) -> List[Dict[str, Any]]:
        """Parse CAS (Claim Adjustment) segment."""
        adjustments = []
        if len(fields) < 4:
            return adjustments

        adjustment_group = fields[1].strip()
        group_map = {
            "CO": "Contractual Obligation",
            "PR": "Patient Responsibility",
            "OA": "Other Adjustment",
            "PI": "Payor Initiated Reduction"
        }

        i = 2
        while i + 2 < len(fields):
            reason_code = f"{adjustment_group}-{fields[i].strip()}"
            amount = self._safe_float(fields[i + 1])
            quantity = fields[i + 2].strip() if len(fields) > i + 2 else ""

            if fields[i].strip() or amount != 0:
                adjustments.append({
                    "group": group_map.get(adjustment_group, adjustment_group),
                    "group_code": adjustment_group,
                    "reason_code": reason_code,
                    "description": CARC_CODES.get(reason_code, f"CARC code {reason_code}"),
                    "amount": amount,
                    "quantity": quantity
                })
            i += 3

        return adjustments

    def _parse_nm1(self, fields: List[str]) -> Optional[Dict[str, Any]]:
        """Parse NM1 (Entity Name) segment."""
        if len(fields) < 3:
            return None
        role_code = fields[1].strip() if len(fields) > 1 else ""
        entity_type = "Person" if (len(fields) > 2 and fields[2].strip() == "1") else "Organization"
        last_name = fields[3].strip() if len(fields) > 3 else ""
        first_name = fields[4].strip() if len(fields) > 4 else ""

        return {
            "role_code": role_code,
            "entity_type": entity_type,
            "last_name": last_name,
            "first_name": first_name,
            "full_name": f"{first_name} {last_name}".strip() if first_name else last_name,
            "id": fields[9].strip() if len(fields) > 9 else "",
        }

    def _parse_plb(self, fields: List[str]) -> Dict[str, Any]:
        """Parse PLB (Provider Level Adjustment) segment."""
        if len(fields) < 4:
            return {"provider_id": "", "adjustments": []}
        adjustments = []
        i = 3
        while i + 1 < len(fields):
            adjustments.append({
                "reason": fields[i].strip(),
                "amount": self._safe_float(fields[i + 1])
            })
            i += 2
        return {
            "provider_id": fields[1].strip() if len(fields) > 1 else "",
            "fiscal_period": fields[2].strip() if len(fields) > 2 else "",
            "adjustments": adjustments
        }

    def _summarize_remittance(self, text: str) -> Dict[str, Any]:
        """Generate summary of a remittance advice."""
        parsed = self._parse_835(text)
        total_charged = 0.0
        total_paid = 0.0
        total_patient_resp = 0.0
        total_adjustments = 0.0
        denial_count = 0
        claim_count = len(parsed["claims"])

        for claim in parsed["claims"]:
            total_charged += claim.get("charged_amount", 0)
            total_paid += claim.get("paid_amount", 0)
            total_patient_resp += claim.get("patient_responsibility", 0)
            if "4" in claim.get("status_code", ""):
                denial_count += 1
            for adj in claim.get("adjustments", []):
                total_adjustments += adj.get("amount", 0)

        return {
            "summary": {
                "total_claims": claim_count,
                "total_charged": round(total_charged, 2),
                "total_paid": round(total_paid, 2),
                "total_patient_responsibility": round(total_patient_resp, 2),
                "total_adjustments": round(abs(total_adjustments), 2),
                "denial_count": denial_count,
                "denial_rate": round(denial_count / claim_count * 100, 1) if claim_count > 0 else 0,
                "payment_rate": round(total_paid / total_charged * 100, 1) if total_charged > 0 else 0,
            },
            "financial_info": parsed["financial_info"],
            "payer": parsed["header"].get("payer", {}),
            "payee": parsed["header"].get("payee", {}),
        }

    def _identify_denials(self, text: str) -> Dict[str, Any]:
        """Identify denied claims and their denial reasons from remittance."""
        parsed = self._parse_835(text)
        denials = []

        for claim in parsed["claims"]:
            status_code = claim.get("status_code", "")
            if status_code == "4":
                denial_adjustments = [adj for adj in claim.get("adjustments", [])
                                      if adj.get("group_code") in ("CO", "OA", "PI")]
                denial_reasons = []
                for adj in denial_adjustments:
                    denial_reasons.append({
                        "code": adj["reason_code"],
                        "description": adj["description"],
                        "amount": adj["amount"]
                    })

                denials.append({
                    "claim_id": claim.get("claim_id", ""),
                    "status": "Denied",
                    "charged_amount": claim.get("charged_amount", 0),
                    "denial_reasons": denial_reasons,
                    "patient": claim.get("patient", {}),
                    "appealable": any(
                        adj["group_code"] == "CO"
                        for adj in denial_adjustments
                    )
                })

            # Check for partial denials (adjustments with CO codes)
            elif claim.get("adjustments"):
                partial_denials = [adj for adj in claim["adjustments"]
                                   if adj.get("group_code") in ("CO", "PI") and adj.get("amount", 0) > 0]
                if partial_denials:
                    denials.append({
                        "claim_id": claim.get("claim_id", ""),
                        "status": "Partial denial / adjustment",
                        "charged_amount": claim.get("charged_amount", 0),
                        "paid_amount": claim.get("paid_amount", 0),
                        "denial_reasons": [
                            {"code": adj["reason_code"], "description": adj["description"], "amount": adj["amount"]}
                            for adj in partial_denials
                        ],
                        "patient": claim.get("patient", {}),
                        "appealable": True
                    })

        return {
            "total_denials": len(denials),
            "denials": denials,
            "total_denial_amount": round(sum(
                d.get("charged_amount", 0) - d.get("paid_amount", 0)
                for d in denials
            ), 2),
            "appealable_denials": sum(1 for d in denials if d.get("appealable", False))
        }

    def _calculate_net_payment(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate net payment from remittance amounts."""
        claim_amount = kwargs.get("claim_amount", 0) or 0
        paid_amount = kwargs.get("paid_amount", 0) or 0
        adjustment_amount = kwargs.get("adjustment_amount", 0) or 0
        patient_responsibility = kwargs.get("patient_responsibility_amount", 0) or 0

        calculated_adjustment = round(claim_amount - paid_amount - patient_responsibility, 2)
        variance = round(adjustment_amount - calculated_adjustment, 2) if adjustment_amount else 0

        return {
            "claim_amount": round(claim_amount, 2),
            "paid_amount": round(paid_amount, 2),
            "adjustment_amount": round(adjustment_amount, 2),
            "patient_responsibility": round(patient_responsibility, 2),
            "calculated_contractual_adjustment": calculated_adjustment,
            "variance_from_reported_adjustment": variance,
            "net_provider_reimbursement": round(paid_amount, 2),
            "collection_ratio": round(paid_amount / claim_amount * 100, 1) if claim_amount > 0 else 0,
            "patient_responsibility_ratio": round(patient_responsibility / claim_amount * 100, 1) if claim_amount > 0 else 0,
            "adjustment_ratio": round(adjustment_amount / claim_amount * 100, 1) if claim_amount > 0 else 0,
            "balanced": abs(variance) < 0.01,
            "notes": "Amounts reconcile correctly." if abs(variance) < 0.01 else f"Variance of ${abs(variance):.2f} detected between reported and calculated adjustments."
        }

    def _decode_carc(self, code: str) -> Dict[str, Any]:
        """Decode a single CARC code."""
        code_upper = code.upper()
        if not code_upper[0:2].isalpha() and "-" not in code_upper:
            code_upper = code_upper

        description = CARC_CODES.get(code_upper, f"Unknown CARC code: {code}")

        group_code = code_upper.split("-")[0] if "-" in code_upper else ""
        group_map = {
            "CO": "Contractual Obligation",
            "PR": "Patient Responsibility",
            "OA": "Other Adjustment",
            "PI": "Payor Initiated Reduction"
        }

        return {
            "code": code_upper,
            "description": description,
            "group_code": group_code,
            "group_description": group_map.get(group_code, "Unknown group"),
            "is_denial": group_code in ("CO", "OA", "PI"),
            "is_patient_responsibility": group_code == "PR"
        }

    def _decode_rarc(self, code: str) -> Dict[str, Any]:
        """Decode a single RARC code."""
        code_upper = code.upper()
        description = RARC_CODES.get(code_upper, f"Unknown RARC code: {code}")

        code_prefix = code_upper[0] if code_upper else ""
        prefix_map = {
            "N": "Non-financial informational/remittance",
            "M": "Mandatory message (required action)",
            "MA": "Mandatory message (alert/info only)",
            "W": "Workers' Compensation"
        }

        prefix_desc = "Unknown"
        for prefix, desc in prefix_map.items():
            if code_upper.startswith(prefix):
                prefix_desc = desc
                break

        return {
            "code": code_upper,
            "description": description,
            "category": prefix_desc,
            "requires_action": code_prefix == "M" and not code_upper.startswith("MA")
        }

    def _safe_float(self, value) -> float:
        """Safely convert a string to float."""
        if value is None:
            return 0.0
        try:
            cleaned = str(value).strip().replace(",", "").replace("$", "")
            return float(cleaned) if cleaned else 0.0
        except (ValueError, TypeError):
            return 0.0