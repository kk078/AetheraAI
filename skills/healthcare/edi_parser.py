"""
Aethera AI - EDI Parser Skill

Parse and generate X12 EDI transactions. Supports: detect transaction type
(837P/837I/835/270/271/276/277/278/834/820), parse segments
(ISA/GS/ST/SE/GE/IEA plus transaction-specific), extract key data
(claim amounts, patient info, provider info), validate structure.
"""

import re
from typing import Dict, Any, List, Optional, Tuple

from skills.skill_base import AetheraSkill, SkillResult, skill


# X12 EDI transaction type definitions
TRANSACTION_TYPES: Dict[str, Dict[str, Any]] = {
    "837": {"name": "Health Care Claim", "subtypes": {"837P": "Professional", "837I": "Institutional", "837D": "Dental"}},
    "835": {"name": "Health Care Claim Payment/Advice (Remittance)"},
    "270": {"name": "Health Care Eligibility Inquiry"},
    "271": {"name": "Health Care Eligibility Response"},
    "276": {"name": "Health Care Claim Status Inquiry"},
    "277": {"name": "Health Care Claim Status Response"},
    "278": {"name": "Health Care Services Review (Prior Authorization)"},
    "834": {"name": "Health Plan Enrollment/Disenrollment"},
    "820": {"name": "Premium Payment"},
    "999": {"name": "Implementation Acknowledgment"},
    "277CA": {"name": "Claim Adjustment"},
}

# X12 segment definitions
SEGMENT_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "ISA": {
        "description": "Interchange Control Header",
        "fields": [
            {"position": 1, "name": "Authorization Information Qualifier", "example": "00"},
            {"position": 2, "name": "Authorization Information", "example": "          "},
            {"position": 3, "name": "Security Information Qualifier", "example": "00"},
            {"position": 4, "name": "Security Information", "example": "          "},
            {"position": 5, "name": "Interchange ID Qualifier", "example": "ZZ"},
            {"position": 6, "name": "Interchange Sender ID", "example": "SENDERID      "},
            {"position": 7, "name": "Interchange ID Qualifier", "example": "ZZ"},
            {"position": 8, "name": "Interchange Receiver ID", "example": "RECEIVERID     "},
            {"position": 9, "name": "Interchange Date", "example": "240101"},
            {"position": 10, "name": "Interchange Time", "example": "1200"},
            {"position": 11, "name": "Repetition Separator", "example": "^"},
            {"position": 12, "name": "Interchange Control Version Number", "example": "00501"},
            {"position": 13, "name": "Interchange Control Number", "example": "000000001"},
            {"position": 14, "name": "Acknowledgment Requested", "example": "1"},
            {"position": 15, "name": "Usage Indicator", "example": "P"},
            {"position": 16, "name": "Component Element Separator", "example": ":"},
        ]
    },
    "GS": {
        "description": "Functional Group Header",
        "fields": [
            {"position": 1, "name": "Functional Identifier Code", "example": "HC"},
            {"position": 2, "name": "Application Sender's Code", "example": "SENDER"},
            {"position": 3, "name": "Application Receiver's Code", "example": "RECEIVER"},
            {"position": 4, "name": "Date", "example": "20240101"},
            {"position": 5, "name": "Time", "example": "1200"},
            {"position": 6, "name": "Group Control Number", "example": "1"},
            {"position": 7, "name": "Responsible Agency Code", "example": "X"},
            {"position": 8, "name": "Version/Release/Industry ID", "example": "005010X222A2"},
        ]
    },
    "ST": {
        "description": "Transaction Set Header",
        "fields": [
            {"position": 1, "name": "Transaction Set Identifier Code", "example": "837"},
            {"position": 2, "name": "Transaction Set Control Number", "example": "0001"},
            {"position": 3, "name": "Implementation Convention Reference", "example": "005010X222A2"},
        ]
    },
    "SE": {
        "description": "Transaction Set Trailer",
        "fields": [
            {"position": 1, "name": "Number of Included Segments", "example": "150"},
            {"position": 2, "name": "Transaction Set Control Number", "example": "0001"},
        ]
    },
    "GE": {
        "description": "Functional Group Trailer",
        "fields": [
            {"position": 1, "name": "Number of Transaction Sets Included", "example": "1"},
            {"position": 2, "name": "Group Control Number", "example": "1"},
        ]
    },
    "IEA": {
        "description": "Interchange Control Trailer",
        "fields": [
            {"position": 1, "name": "Number of Included Functional Groups", "example": "1"},
            {"position": 2, "name": "Interchange Control Number", "example": "000000001"},
        ]
    },
    "BHT": {"description": "Beginning of Hierarchical Transaction", "fields": [
        {"position": 1, "name": "Hierarchical Structure Code", "example": "0019"},
        {"position": 2, "name": "Transaction Set Purpose Code", "example": "00"},
        {"position": 3, "name": "Reference Identification", "example": "CLM12345"},
        {"position": 4, "name": "Date", "example": "20240101"},
        {"position": 5, "name": "Time", "example": "1200"},
        {"position": 6, "name": "Transaction Type Code", "example": "CH"},
    ]},
    "NM1": {"description": "Individual or Organizational Name", "fields": [
        {"position": 1, "name": "Entity Identifier Code", "example": "41"},
        {"position": 2, "name": "Entity Type Qualifier", "example": "1"},
        {"position": 3, "name": "Name Last or Organization Name", "example": "SMITH"},
        {"position": 4, "name": "Name First", "example": "JOHN"},
        {"position": 5, "name": "Name Middle", "example": ""},
        {"position": 6, "name": "Name Prefix", "example": ""},
        {"position": 7, "name": "Name Suffix", "example": ""},
        {"position": 8, "name": "Identification Code Qualifier", "example": "46"},
        {"position": 9, "name": "Identification Code", "example": "1234567890"},
    ]},
    "CLM": {"description": "Claim Information (837)", "fields": [
        {"position": 1, "name": "Claim Number", "example": "1"},
        {"position": 2, "name": "Total Claim Charge Amount", "example": "150.00"},
        {"position": 3, "name": "Claim Filing Indicator Code", "example": "MC"},
        {"position": 4, "name": "Non-Institutional Claim Type Code", "example": ""},
        {"position": 5, "name": "Health Care Service Location Information", "example": "11"},
    ]},
    "CLP": {"description": "Claim Level Data (835)", "fields": [
        {"position": 1, "name": "Claim Number", "example": "1"},
        {"position": 2, "name": "Claim Status Code", "example": "1"},
        {"position": 3, "name": "Total Claim Charge Amount", "example": "150.00"},
        {"position": 4, "name": "Total Claim Paid Amount", "example": "120.00"},
        {"position": 5, "name": "Patient Responsibility Amount", "example": "30.00"},
        {"position": 6, "name": "Claim Filing Indicator Code", "example": "MC"},
        {"position": 7, "name": "Payer Claim Control Number", "example": "CLM001"},
    ]},
    "SVC": {"description": "Service Payment Information (835)", "fields": [
        {"position": 1, "name": "Composite Medical Procedure Identifier", "example": "HC:99213"},
        {"position": 2, "name": "Service Line Charge Amount", "example": "150.00"},
        {"position": 3, "name": "Service Line Paid Amount", "example": "120.00"},
        {"position": 4, "name": "Revenue Code", "example": ""},
        {"position": 5, "name": "Units of Service", "example": "1"},
    ]},
    "HL": {"description": "Hierarchical Level", "fields": [
        {"position": 1, "name": "Hierarchical ID Number", "example": "1"},
        {"position": 2, "name": "Hierarchical Parent ID Number", "example": ""},
        {"position": 3, "name": "Hierarchical Level Code", "example": "20"},
        {"position": 4, "name": "Hierarchical Child Code", "example": "1"},
    ]},
    "REF": {"description": "Reference Identification", "fields": [
        {"position": 1, "name": "Reference Identification Qualifier", "example": "1L"},
        {"position": 2, "name": "Reference Identification", "example": "GROUP001"},
    ]},
    "DTP": {"description": "Date/Time Period", "fields": [
        {"position": 1, "name": "Date/Time Qualifier", "example": "472"},
        {"position": 2, "name": "Date Time Period Format Qualifier", "example": "D8"},
        {"position": 3, "name": "Date Time Period", "example": "20240101"},
    ]},
    "PER": {"description": "Administrative Communications Contact", "fields": [
        {"position": 1, "name": "Contact Function Code", "example": "IC"},
        {"position": 2, "name": "Name", "example": "JOHN DOE"},
        {"position": 3, "name": "Communication Number Qualifier", "example": "TE"},
        {"position": 4, "name": "Communication Number", "example": "5551234567"},
    ]},
    "N3": {"description": "Party Location (Address)", "fields": [
        {"position": 1, "name": "Address Information", "example": "123 MAIN ST"},
        {"position": 2, "name": "Address Information", "example": "SUITE 100"},
    ]},
    "N4": {"description": "Geographic Location (City/State/ZIP)", "fields": [
        {"position": 1, "name": "City Name", "example": "ANYTOWN"},
        {"position": 2, "name": "State or Province Code", "example": "CA"},
        {"position": 3, "name": "Postal Code", "example": "90210"},
    ]},
    "LX": {"description": "Transaction Set Line Number", "fields": [
        {"position": 1, "name": "Assigned Number", "example": "1"},
    ]},
    "CAS": {"description": "Claim Adjustments (835)", "fields": [
        {"position": 1, "name": "Claim Adjustment Group Code", "example": "CO"},
        {"position": 2, "name": "Claim Adjustment Reason Code", "example": "45"},
        {"position": 3, "name": "Monetary Amount", "example": "30.00"},
    ]},
    "AMT": {"description": "Monetary Amount Information", "fields": [
        {"position": 1, "name": "Amount Qualifier Code", "example": "F5"},
        {"position": 2, "name": "Monetary Amount", "example": "150.00"},
    ]},
    "PRV": {"description": "Provider Information", "fields": [
        {"position": 1, "name": "Provider Code", "example": "AT"},
        {"position": 2, "name": "Reference Identification Qualifier", "example": "PXC"},
        {"position": 3, "name": "Reference Identification", "example": "207R00000X"},
    ]},
    "EQ": {"description": "Eligibility or Benefit Inquiry (270)", "fields": [
        {"position": 1, "name": "Eligibility Benefit Type Code", "example": "1"},
        {"position": 2, "name": "Service Type Code", "example": "30"},
    ]},
    "EB": {"description": "Eligibility Benefit Response (271)", "fields": [
        {"position": 1, "name": "Eligibility Benefit Type Code", "example": "1"},
        {"position": 2, "name": "Service Type Code", "example": "30"},
        {"position": 3, "name": "Insurance Type Code", "example": "12"},
        {"position": 4, "name": "Benefit Coverage Level Code", "example": ""},

    ]},
    "TRN": {"description": "Trace Number", "fields": [
        {"position": 1, "name": "Trace Type Code", "example": "1"},
        {"position": 2, "name": "Reference Identifer", "example": "1"},
        {"position": 3, "name": "Originating Company ID", "example": "9876543210"},
    ]},
    "DMG": {"description": "Demographic Information", "fields": [
        {"position": 1, "name": "Date Time Period Format Qualifier", "example": "D8"},
        {"position": 2, "name": "Date Time Period", "example": "19800101"},
        {"position": 3, "name": "Gender Code", "example": "M"},
    ]},
    "INS": {"description": "Insured Benefit Information (834)", "fields": [
        {"position": 1, "name": "Insured Indicator Code", "example": "Y"},
        {"position": 2, "name": "Individual Relationship Code", "example": "18"},
        {"position": 3, "name": "Maintenance Type Code", "example": "021"},
    ]},
}

# Entity identifier codes used in NM1 segments
ENTITY_CODES: Dict[str, str] = {
    "41": "Submitter",
    "40": "Receiver",
    "85": "Billing Provider",
    "82": "Rendering Provider",
    "77": "Service Provider",
    "87": "Pay-to Provider",
    "IL": "Insured or Subscriber",
    "QC": "Patient",
    "TT": "Transfer To",
    "87": "Pay-to Provider",
    "PE": "Payee",
    "PR": "Payer",
    "1P": "Provider (information)",
    "2P": "Provider (secondary)",
    "DN": "Referring Provider",
    "P5": "Pharmacy",
    "74": "Corrected Insured",
    "GW": "Other Insured",
}


@skill(name="edi_parser", category="healthcare")
class EDIParserSkill(AetheraSkill):
    """
    Parse and generate X12 EDI transactions.
    """

    @property
    def name(self) -> str:
        return "edi_parser"

    @property
    def description(self) -> str:
        return "Parse X12 EDI transactions (837P/837I/835/270/271/276/277/278/834/820): detect type, parse segments, extract claim/patient/provider data, validate structure."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["detect_type", "parse", "extract_data", "validate", "segment_info"],
                    "description": "Action: detect_type (identify transaction type), parse (full parse of EDI content), extract_data (extract key fields), validate (structural validation), segment_info (look up segment definition)"
                },
                "edi_content": {
                    "type": "string",
                    "description": "Raw EDI X12 content to parse"
                },
                "segment_id": {
                    "type": "string",
                    "description": "Segment identifier to look up (e.g., ISA, NM1, CLM, CLP)"
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
            {"input": {"action": "detect_type", "edi_content": "ISA*00*          *00*          *ZZ*SENDERID      *ZZ*RECEIVERID     *240101*1200*^*00501*000000001*0*P*:~GS*HC*SENDER*RECEIVER*20240101*1200*1*X*005010X222A2~ST*837*0001*005010X222A2~"}},
            {"input": {"action": "parse", "edi_content": "ISA*00*          *00*          *ZZ*SENDERID      *ZZ*RECEIVERID     *240101*1200*^*00501*000000001*0*P*:~GS*HC*SENDER*RECEIVER*20240101*1200*1*X*005010X222A2~ST*837*0001*005010X222A2~BHT*0019*00*CLM12345*20240101*1200*CH~SE*5*0001~GE*1*1~IEA*1*000000001~"}},
            {"input": {"action": "segment_info", "segment_id": "NM1"}},
        ]

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "")
        edi_content = kwargs.get("edi_content", "")
        segment_id = kwargs.get("segment_id", "")

        try:
            if action == "detect_type":
                if not edi_content:
                    return SkillResult(success=False, error="edi_content is required for detect_type")
                result = self._detect_type(edi_content)
                return SkillResult(success=True, data=result)

            elif action == "parse":
                if not edi_content:
                    return SkillResult(success=False, error="edi_content is required for parse")
                result = self._parse(edi_content)
                return SkillResult(success=True, data=result)

            elif action == "extract_data":
                if not edi_content:
                    return SkillResult(success=False, error="edi_content is required for extract_data")
                result = self._extract_data(edi_content)
                return SkillResult(success=True, data=result)

            elif action == "validate":
                if not edi_content:
                    return SkillResult(success=False, error="edi_content is required for validate")
                result = self._validate(edi_content)
                return SkillResult(success=True, data=result)

            elif action == "segment_info":
                result = self._segment_info(segment_id)
                return SkillResult(success=True, data=result)

            else:
                return SkillResult(success=False, error=f"Unknown action: {action}")

        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _split_segments(self, edi_content: str) -> List[str]:
        """Split EDI content into individual segments."""
        # Normalize line endings and split by segment terminator
        edi_content = edi_content.replace("\n", "").replace("\r", "")
        # Common segment terminators: ~ or newline
        if "~" in edi_content:
            segments = edi_content.split("~")
        else:
            segments = re.split(r"[\r\n]+", edi_content)
        return [s.strip() for s in segments if s.strip()]

    def _parse_segment(self, segment_str: str, element_separator: str = "*") -> Dict[str, Any]:
        """Parse a single segment string into its components."""
        parts = segment_str.split(element_separator)
        segment_id = parts[0] if parts else ""
        fields = parts[1:] if len(parts) > 1 else []
        return {
            "segment_id": segment_id,
            "fields": fields,
            "raw": segment_str
        }

    def _detect_delimiters(self, edi_content: str) -> Dict[str, str]:
        """Detect EDI delimiters from the ISA segment."""
        delimiters = {
            "element_separator": "*",
            "segment_terminator": "~",
            "component_separator": ":",
            "repetition_separator": "^"
        }
        # ISA segment defines delimiters
        if edi_content.startswith("ISA"):
            # Element separator is character after ISA
            if len(edi_content) > 3:
                delimiters["element_separator"] = edi_content[3]
            # Component separator is the last character of ISA segment
            # Repetition separator is ISA position 11 (index after 10 element separators)
            # Find the segment terminator
            for char in ["~", "\r", "\n", "\x1c", "\x1d"]:
                if char in edi_content[:200]:
                    delimiters["segment_terminator"] = char
                    break
        return delimiters

    def _detect_type(self, edi_content: str) -> Dict[str, Any]:
        """Detect the EDI transaction type(s)."""
        segments = self._split_segments(edi_content)
        delimiters = self._detect_delimiters(edi_content)
        detected_transactions = []
        interchange_info = {}
        functional_groups = []

        for seg_str in segments:
            parsed = self._parse_segment(seg_str, delimiters["element_separator"])

            if parsed["segment_id"] == "ISA":
                fields = parsed["fields"]
                interchange_info = {
                    "sender_id": fields[4].strip() if len(fields) > 4 else "",
                    "receiver_id": fields[6].strip() if len(fields) > 6 else "",
                    "date": fields[8].strip() if len(fields) > 8 else "",
                    "time": fields[9].strip() if len(fields) > 9 else "",
                    "control_number": fields[12].strip() if len(fields) > 12 else "",
                    "usage_indicator": fields[14].strip() if len(fields) > 14 else "",
                }

            elif parsed["segment_id"] == "GS":
                fields = parsed["fields"]
                func_code = fields[0].strip() if fields else ""
                functional_groups.append({
                    "functional_identifier": func_code,
                    "sender": fields[1].strip() if len(fields) > 1 else "",
                    "receiver": fields[2].strip() if len(fields) > 2 else "",
                    "control_number": fields[5].strip() if len(fields) > 5 else "",
                    "version": fields[7].strip() if len(fields) > 7 else "",
                })

            elif parsed["segment_id"] == "ST":
                fields = parsed["fields"]
                txn_code = fields[0].strip() if fields else ""
                txn_info = TRANSACTION_TYPES.get(txn_code, {"name": f"Unknown ({txn_code})"})
                subtype = ""
                if txn_code == "837":
                    # Check version for subtype
                    version = fields[2].strip() if len(fields) > 2 else ""
                    if "X222" in version:
                        subtype = "837P (Professional)"
                    elif "X223" in version:
                        subtype = "837I (Institutional)"
                    elif "X224" in version:
                        subtype = "837D (Dental)"

                detected_transactions.append({
                    "transaction_code": txn_code,
                    "name": txn_info.get("name", "Unknown"),
                    "subtype": subtype,
                    "subtypes": txn_info.get("subtypes", {}) if txn_code == "837" else None,
                    "control_number": fields[1].strip() if len(fields) > 1 else "",
                    "version": fields[2].strip() if len(fields) > 2 else "",
                })

        return {
            "detected_transactions": detected_transactions,
            "transaction_count": len(detected_transactions),
            "transaction_types": list(set(t["transaction_code"] for t in detected_transactions)) if detected_transactions else [],
            "interchange_info": interchange_info,
            "functional_groups": functional_groups,
            "delimiters": self._detect_delimiters(edi_content),
        }

    def _parse(self, edi_content: str) -> Dict[str, Any]:
        """Full parse of EDI content."""
        segments = self._split_segments(edi_content)
        delimiters = self._detect_delimiters(edi_content)
        parsed_segments = []
        interchange = {}
        functional_group = {}
        transactions = []
        current_transaction = None

        for seg_str in segments:
            parsed = self._parse_segment(seg_str, delimiters["element_separator"])
            segment_id = parsed["segment_id"]
            fields = parsed["fields"]

            parsed_segments.append({
                "segment_id": segment_id,
                "fields": fields,
                "field_count": len(fields)
            })

            if segment_id == "ISA":
                interchange = {
                    "sender_id": fields[4].strip() if len(fields) > 4 else "",
                    "receiver_id": fields[6].strip() if len(fields) > 6 else "",
                    "date": fields[8].strip() if len(fields) > 8 else "",
                    "control_number": fields[12].strip() if len(fields) > 12 else "",
                    "usage": {"P": "Production", "T": "Test"}.get(fields[14].strip() if len(fields) > 14 else "", "Unknown")
                }

            elif segment_id == "GS":
                functional_group = {
                    "functional_id": fields[0].strip() if fields else "",
                    "sender": fields[1].strip() if len(fields) > 1 else "",
                    "receiver": fields[2].strip() if len(fields) > 2 else "",
                    "control_number": fields[5].strip() if len(fields) > 5 else "",
                    "version": fields[7].strip() if len(fields) > 7 else "",
                }

            elif segment_id == "ST":
                current_transaction = {
                    "type": fields[0].strip() if fields else "",
                    "control_number": fields[1].strip() if len(fields) > 1 else "",
                    "version": fields[2].strip() if len(fields) > 2 else "",
                    "segments": []
                }

            elif segment_id == "SE":
                if current_transaction:
                    current_transaction["segment_count"] = fields[0].strip() if fields else ""
                    current_transaction["control_number"] = fields[1].strip() if len(fields) > 1 else current_transaction["control_number"]
                    transactions.append(current_transaction)
                    current_transaction = None

            elif segment_id == "GE":
                functional_group = {}

            elif segment_id == "IEA":
                interchange = {}

            if current_transaction and segment_id not in ("ST", "SE"):
                current_transaction["segments"].append({
                    "segment_id": segment_id,
                    "fields": fields
                })

        return {
            "total_segments": len(parsed_segments),
            "interchange": interchange,
            "functional_group": functional_group,
            "transactions": transactions,
            "transaction_count": len(transactions),
            "parsed_segments": parsed_segments,
            "segment_summary": self._summarize_segments(parsed_segments)
        }

    def _summarize_segments(self, parsed_segments: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count occurrences of each segment type."""
        summary: Dict[str, int] = {}
        for seg in parsed_segments:
            sid = seg["segment_id"]
            summary[sid] = summary.get(sid, 0) + 1
        return dict(sorted(summary.items()))

    def _extract_data(self, edi_content: str) -> Dict[str, Any]:
        """Extract key data fields from EDI content."""
        segments = self._split_segments(edi_content)
        delimiters = self._detect_delimiters(edi_content)
        extracted: Dict[str, Any] = {
            "interchange": {},
            "transaction_type": None,
            "submitter": {},
            "receiver": {},
            "billing_provider": {},
            "subscriber": {},
            "patient": {},
            "claims": [],
            "payments": [],
            "service_lines": [],
        }

        current_claim = None

        for seg_str in segments:
            parsed = self._parse_segment(seg_str, delimiters["element_separator"])
            segment_id = parsed["segment_id"]
            fields = parsed["fields"]

            if segment_id == "ISA":
                extracted["interchange"]["sender_id"] = fields[4].strip() if len(fields) > 4 else ""
                extracted["interchange"]["receiver_id"] = fields[6].strip() if len(fields) > 6 else ""
                extracted["interchange"]["date"] = fields[8].strip() if len(fields) > 8 else ""
                extracted["interchange"]["control_number"] = fields[12].strip() if len(fields) > 12 else ""

            elif segment_id == "ST":
                extracted["transaction_type"] = fields[0].strip() if fields else ""

            elif segment_id == "BHT":
                extracted["transaction_purpose"] = fields[1].strip() if len(fields) > 1 else ""
                extracted["reference_id"] = fields[2].strip() if len(fields) > 2 else ""
                extracted["transaction_date"] = fields[3].strip() if len(fields) > 3 else ""

            elif segment_id == "NM1":
                entity_code = fields[0].strip() if fields else ""
                entity_type = fields[1].strip() if len(fields) > 1 else ""
                last_name = fields[2].strip() if len(fields) > 2 else ""
                first_name = fields[3].strip() if len(fields) > 3 else ""
                id_qualifier = fields[7].strip() if len(fields) > 7 else ""
                id_code = fields[8].strip() if len(fields) > 8 else ""

                entity_name = f"{last_name}, {first_name}" if first_name else last_name
                entity_info = {
                    "name": entity_name,
                    "last_name": last_name,
                    "first_name": first_name,
                    "id_qualifier": id_qualifier,
                    "id": id_code,
                    "entity_type": "Person" if entity_type == "1" else "Organization" if entity_type == "2" else ""
                }

                if entity_code == "41":
                    extracted["submitter"] = entity_info
                elif entity_code == "40":
                    extracted["receiver"] = entity_info
                elif entity_code == "85":
                    extracted["billing_provider"] = entity_info
                elif entity_code == "82":
                    extracted["rendering_provider"] = entity_info
                elif entity_code == "IL":
                    extracted["subscriber"] = entity_info
                elif entity_code == "QC":
                    extracted["patient"] = entity_info
                elif entity_code == "PR":
                    extracted["payer"] = entity_info

            elif segment_id == "CLM":
                claim_number = fields[0].strip() if fields else ""
                claim_amount = fields[1].strip() if len(fields) > 1 else ""
                filing_indicator = fields[2].strip() if len(fields) > 2 else ""
                pos_code = fields[4].strip() if len(fields) > 4 else ""
                current_claim = {
                    "claim_number": claim_number,
                    "charge_amount": claim_amount,
                    "filing_indicator": filing_indicator,
                    "place_of_service": pos_code,
                    "service_lines": []
                }
                extracted["claims"].append(current_claim)

            elif segment_id == "CLP":
                claim_number = fields[0].strip() if fields else ""
                claim_status = fields[1].strip() if len(fields) > 1 else ""
                charge_amount = fields[2].strip() if len(fields) > 2 else ""
                paid_amount = fields[3].strip() if len(fields) > 3 else ""
                patient_responsibility = fields[4].strip() if len(fields) > 4 else ""
                current_claim = {
                    "claim_number": claim_number,
                    "status_code": claim_status,
                    "charge_amount": charge_amount,
                    "paid_amount": paid_amount,
                    "patient_responsibility": patient_responsibility,
                    "adjustments": []
                }
                extracted["payments"].append(current_claim)

            elif segment_id == "SVC":
                proc_info = fields[0].strip() if fields else ""
                # Parse composite procedure code (e.g., HC:99213)
                proc_parts = proc_info.split(delimiters.get("component_separator", ":"))
                proc_qualifier = proc_parts[0] if proc_parts else ""
                proc_code = proc_parts[1] if len(proc_parts) > 1 else proc_info
                charge = fields[1].strip() if len(fields) > 1 else ""
                paid = fields[2].strip() if len(fields) > 2 else ""
                units = fields[4].strip() if len(fields) > 4 else "1"
                svc_line = {
                    "procedure_qualifier": proc_qualifier,
                    "procedure_code": proc_code,
                    "charge_amount": charge,
                    "paid_amount": paid,
                    "units": units
                }
                extracted["service_lines"].append(svc_line)
                if current_claim:
                    current_claim.setdefault("service_lines", []).append(svc_line)

            elif segment_id == "CAS":
                group_code = fields[0].strip() if fields else ""
                reason_code = fields[1].strip() if len(fields) > 1 else ""
                amount = fields[2].strip() if len(fields) > 2 else ""
                adjustment = {
                    "group_code": group_code,
                    "reason_code": reason_code,
                    "amount": amount
                }
                if current_claim:
                    current_claim.setdefault("adjustments", []).append(adjustment)

            elif segment_id == "DMG":
                dob_format = fields[0].strip() if fields else ""
                dob = fields[1].strip() if len(fields) > 1 else ""
                gender = fields[2].strip() if len(fields) > 2 else ""
                extracted["patient"]["date_of_birth"] = dob
                extracted["patient"]["gender"] = gender

            elif segment_id == "DTP":
                qualifier = fields[0].strip() if fields else ""
                date_format = fields[1].strip() if len(fields) > 1 else ""
                date_val = fields[2].strip() if len(fields) > 2 else ""
                date_types = {
                    "472": "Service date",
                    "434": "Admission date",
                    "096": "Discharge date",
                    "036": "Eligibility date",
                    "291": "Plan begin date",
                    "292": "Plan end date",
                }
                date_label = date_types.get(qualifier, f"Date (qualifier {qualifier})")
                extracted.setdefault("dates", {})[date_label] = date_val

            elif segment_id == "REF":
                ref_qualifier = fields[0].strip() if fields else ""
                ref_value = fields[1].strip() if len(fields) > 1 else ""
                ref_types = {
                    "1L": "Group Number",
                    "0F": "Policy Number",
                    "1A": "Blue Cross Provider ID",
                    "1B": "Blue Shield Provider ID",
                    "2U": "Payer ID",
                    "EV": "Member ID",
                    "PQ": "Payee ID",
                    "BB": "Billing Provider Tax ID",
                }
                ref_label = ref_types.get(ref_qualifier, f"Reference ({ref_qualifier})")
                extracted.setdefault("references", {})[ref_label] = ref_value

        # Summary
        total_charges = 0.0
        total_paid = 0.0
        for claim in extracted.get("claims", []):
            try:
                total_charges += float(claim.get("charge_amount", "0").replace(",", ""))
            except (ValueError, TypeError):
                pass
        for payment in extracted.get("payments", []):
            try:
                total_paid += float(payment.get("paid_amount", "0").replace(",", ""))
            except (ValueError, TypeError):
                pass

        extracted["summary"] = {
            "transaction_type": extracted["transaction_type"],
            "claim_count": len(extracted.get("claims", [])),
            "payment_count": len(extracted.get("payments", [])),
            "service_line_count": len(extracted.get("service_lines", [])),
            "total_charges": round(total_charges, 2),
            "total_paid": round(total_paid, 2)
        }

        return extracted

    def _validate(self, edi_content: str) -> Dict[str, Any]:
        """Validate EDI structure."""
        segments = self._split_segments(edi_content)
        delimiters = self._detect_delimiters(edi_content)
        issues = []
        warnings = []

        if not segments:
            return {"valid": False, "issues": [{"severity": "critical", "message": "No segments found in EDI content"}]}

        # Check ISA header
        if not segments[0].startswith("ISA"):
            issues.append({"severity": "critical", "message": "EDI content must start with ISA segment"})

        # Check IEA trailer
        if not segments[-1].startswith("IEA"):
            issues.append({"severity": "critical", "message": "EDI content must end with IEA segment"})

        # Validate envelope pairs
        isa_count = sum(1 for s in segments if s.startswith("ISA"))
        iea_count = sum(1 for s in segments if s.startswith("IEA"))
        if isa_count != iea_count:
            issues.append({"severity": "critical", "message": f"ISA count ({isa_count}) does not match IEA count ({iea_count})"})

        gs_count = sum(1 for s in segments if s.startswith("GS"))
        ge_count = sum(1 for s in segments if s.startswith("GE"))
        if gs_count != ge_count:
            issues.append({"severity": "critical", "message": f"GS count ({gs_count}) does not match GE count ({ge_count})"})

        st_count = sum(1 for s in segments if s.startswith("ST"))
        se_count = sum(1 for s in segments if s.startswith("SE"))
        if st_count != se_count:
            issues.append({"severity": "critical", "message": f"ST count ({st_count}) does not match SE count ({se_count})"})

        # Validate control numbers match
        for seg_str in segments:
            parsed = self._parse_segment(seg_str, delimiters["element_separator"])
            if parsed["segment_id"] == "ISA":
                isa_ctrl = parsed["fields"][12].strip() if len(parsed["fields"]) > 12 else ""
            elif parsed["segment_id"] == "IEA":
                iea_ctrl = parsed["fields"][1].strip() if len(parsed["fields"]) > 1 else ""
                if "isa_ctrl" in dir() and isa_ctrl and iea_ctrl and isa_ctrl != iea_ctrl:
                    issues.append({"severity": "critical", "message": f"ISA control number ({isa_ctrl}) does not match IEA ({iea_ctrl})"})

        # Validate segment count in SE
        st_ctrl = ""
        expected_se_count = 0
        actual_segment_count = 0
        for seg_str in segments:
            parsed = self._parse_segment(seg_str, delimiters["element_separator"])
            if parsed["segment_id"] == "ST":
                st_ctrl = parsed["fields"][1].strip() if len(parsed["fields"]) > 1 else ""
                actual_segment_count = 0
            elif parsed["segment_id"] == "SE":
                se_ctrl = parsed["fields"][1].strip() if len(parsed["fields"]) > 1 else ""
                expected_se_count = int(parsed["fields"][0].strip()) if parsed["fields"] and parsed["fields"][0].strip().isdigit() else 0
                actual_segment_count += 1  # Include SE itself
                if st_ctrl and se_ctrl and st_ctrl != se_ctrl:
                    issues.append({"severity": "error", "message": f"ST control number ({st_ctrl}) does not match SE ({se_ctrl})"})
                if expected_se_count and expected_se_count != actual_segment_count:
                    warnings.append({"severity": "warning", "message": f"SE segment count ({expected_se_count}) does not match actual count ({actual_segment_count}) for transaction {se_ctrl}"})
                actual_segment_count = 0
            else:
                if st_ctrl:
                    actual_segment_count += 1

        # Check for required segments
        has_bht = any(s.startswith("BHT") for s in segments)
        has_nm1 = any(s.startswith("NM1") for s in segments)
        if not has_nm1:
            warnings.append({"severity": "warning", "message": "No NM1 (name) segments found. Most healthcare EDI requires entity identification."})

        # Check segment lengths
        for seg_str in segments:
            parsed = self._parse_segment(seg_str, delimiters["element_separator"])
            seg_id = parsed["segment_id"]
            if seg_id == "ISA" and len(parsed["fields"]) != 15:
                issues.append({"severity": "error", "message": f"ISA segment should have 15 fields, found {len(parsed['fields'])}"})

        is_valid = not any(i["severity"] == "critical" for i in issues)

        return {
            "valid": is_valid,
            "critical_issues": [i for i in issues if i["severity"] == "critical"],
            "errors": [i for i in issues if i["severity"] == "error"],
            "warnings": warnings,
            "total_issues": len(issues) + len(warnings),
            "segment_count": len(segments),
            "isa_present": any(s.startswith("ISA") for s in segments),
            "iea_present": any(s.startswith("IEA") for s in segments),
            "gs_ge_balanced": gs_count == ge_count,
            "st_se_balanced": st_count == se_count,
        }

    def _segment_info(self, segment_id: str) -> Dict[str, Any]:
        """Look up segment definition."""
        if segment_id:
            seg_info = SEGMENT_DEFINITIONS.get(segment_id.upper())
            if seg_info:
                return {
                    "segment_id": segment_id.upper(),
                    "found": True,
                    "description": seg_info["description"],
                    "fields": seg_info["fields"],
                    "field_count": len(seg_info["fields"]),
                    "related_entity_codes": ENTITY_CODES if segment_id.upper() == "NM1" else None
                }
            else:
                return {
                    "segment_id": segment_id,
                    "found": False,
                    "message": f"Segment {segment_id} not found in definition database",
                    "available_segments": sorted(SEGMENT_DEFINITIONS.keys())
                }
        else:
            return {
                "available_segments": [
                    {"id": k, "description": v["description"], "field_count": len(v["fields"])}
                    for k, v in sorted(SEGMENT_DEFINITIONS.items())
                ],
                "total_defined": len(SEGMENT_DEFINITIONS)
            }