"""
Aethera AI - Compliance Checker Skill

HIPAA, OIG, Stark Law, and Anti-Kickback Statute compliance checking.
"""

from typing import Dict, Any, List, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill


# HIPAA Compliance Check Items
HIPAA_CHECK_ITEMS: Dict[str, Dict[str, Any]] = {
    "HIPAA-001": {
        "check_id": "HIPAA-001",
        "category": "Privacy Rule",
        "title": "Notice of Privacy Practices (NPP)",
        "description": "Organization provides NPP to all patients at first service delivery and upon request",
        "requirement": "45 CFR 164.520 - Covered entities must provide NPP to individuals",
        "check_steps": [
            "Verify NPP is current and posted prominently",
            "Confirm NPP is provided to all new patients",
            "Verify NPP includes required elements (uses/disclosures, rights, duties, contact)",
            "Confirm NPP is available in alternative formats upon request",
            "Verify acknowledgment of receipt is documented"
        ],
        "common_violations": [
            "NPP not provided to new patients",
            "NPP not updated after material changes",
            "NPP missing required elements",
            "No documentation of patient receipt of NPP"
        ],
        "remediation": [
            "Provide current NPP to all patients at next visit",
            "Update NPP to include all required elements",
            "Implement system to track NPP distribution",
            "Train staff on NPP distribution requirements"
        ],
        "risk_level": "high",
        "penalty_range": "$100-$50,000 per violation; $1.5M annual maximum per category"
    },
    "HIPAA-002": {
        "check_id": "HIPAA-002",
        "category": "Privacy Rule",
        "title": "Minimum Necessary Standard",
        "description": "Only minimum necessary PHI is used or disclosed for treatment, payment, or operations",
        "requirement": "45 CFR 164.502(b) - Limit uses/disclosures to minimum necessary",
        "check_steps": [
            "Review access controls for minimum necessary limitation",
            "Verify role-based access limits PHI to job requirements",
            "Audit PHI access logs for inappropriate access",
            "Check disclosures to third parties are limited to minimum necessary",
            "Verify policies define minimum necessary for routine disclosures"
        ],
        "common_violations": [
            "Overly broad access to PHI beyond role requirements",
            "No role-based access controls implemented",
            "Bulk disclosures without minimum necessary filtering",
            "Failure to audit access patterns"
        ],
        "remediation": [
            "Implement role-based access control (RBAC) for all PHI systems",
            "Define minimum necessary standards for each role and disclosure type",
            "Conduct regular access audits",
            "Train workforce on minimum necessary principle"
        ],
        "risk_level": "high",
        "penalty_range": "$100-$50,000 per violation; $1.5M annual maximum per category"
    },
    "HIPAA-003": {
        "check_id": "HIPAA-003",
        "category": "Privacy Rule",
        "title": "Patient Access Rights",
        "description": "Patients have right to access, inspect, and obtain copy of their PHI",
        "requirement": "45 CFR 164.524 - Right to access PHI in designated record set",
        "check_steps": [
            "Verify process exists for patients to request access to PHI",
            "Confirm requests are fulfilled within 30 days (60 if extension needed)",
            "Check that fees charged are reasonable and cost-based only",
            "Verify denial reasons are properly documented and appealable",
            "Confirm electronic access is provided in requested format when feasible"
        ],
        "common_violations": [
            "Failure to provide access within 30-day timeframe",
            "Charging excessive fees for copies of records",
            "Improper denial of access requests",
            "Not providing records in requested electronic format",
            "Requiring patients to pick up records in person only"
        ],
        "remediation": [
            "Implement tracking system for access requests with deadlines",
            "Review and adjust fees to comply with cost-based limits",
            "Train staff on proper denial procedures and appeal rights",
            "Establish electronic record delivery capability",
            "Publish clear access request procedures for patients"
        ],
        "risk_level": "high",
        "penalty_range": "$100-$50,000 per violation; $1.5M annual maximum per category"
    },
    "HIPAA-004": {
        "check_id": "HIPAA-004",
        "category": "Security Rule - Administrative Safeguards",
        "title": "Security Management Process",
        "description": "Conduct risk analysis and implement risk management program",
        "requirement": "45 CFR 164.308(a)(1) - Risk analysis and risk management",
        "check_steps": [
            "Verify comprehensive risk analysis has been conducted",
            "Confirm risk analysis is updated periodically and after changes",
            "Check risk management plan exists and addresses identified risks",
            "Verify sanctions policy for workforce who violate security policies",
            "Confirm regular security awareness training is provided"
        ],
        "common_violations": [
            "No risk analysis conducted",
            "Risk analysis is outdated or not comprehensive",
            "No risk management plan to address identified vulnerabilities",
            "No sanctions policy for security violations",
            "No security awareness training program"
        ],
        "remediation": [
            "Conduct comprehensive enterprise-wide risk analysis",
            "Develop and implement risk management plan",
            "Establish sanctions policy and enforcement procedures",
            "Implement security awareness training program",
            "Schedule periodic risk analysis updates (at least annually)"
        ],
        "risk_level": "critical",
        "penalty_range": "$100-$50,000 per violation; $1.5M annual maximum per category"
    },
    "HIPAA-005": {
        "check_id": "HIPAA-005",
        "category": "Security Rule - Administrative Safeguards",
        "title": "Workforce Security and Training",
        "description": "Ensure workforce members have appropriate access and receive training",
        "requirement": "45 CFR 164.308(a)(3)-(4) - Workforce security and awareness training",
        "check_steps": [
            "Verify authorization and supervision procedures for workforce",
            "Confirm clearance procedures for workforce access to PHI",
            "Check termination procedures remove access promptly",
            "Verify security awareness training is provided to all workforce",
            "Confirm training includes reminders and updates for changes"
        ],
        "common_violations": [
            "No formal workforce clearance process",
            "Access not removed promptly after termination",
            "No security awareness training provided",
            "Training not updated for new threats or policy changes",
            "Temporary workers granted access without proper clearance"
        ],
        "remediation": [
            "Implement workforce authorization and clearance procedures",
            "Establish same-day access termination process",
            "Develop mandatory security awareness training program",
            "Conduct periodic training updates and phishing simulations",
            "Implement background check procedures for PHI access"
        ],
        "risk_level": "high",
        "penalty_range": "$100-$50,000 per violation; $1.5M annual maximum per category"
    },
    "HIPAA-006": {
        "check_id": "HIPAA-006",
        "category": "Security Rule - Technical Safeguards",
        "title": "Access Control and Audit Controls",
        "description": "Implement technical access controls and audit logging for PHI systems",
        "requirement": "45 CFR 164.312(a)-(b) - Access control and audit controls",
        "check_steps": [
            "Verify unique user identification for all workforce",
            "Confirm emergency access procedures exist",
            "Check automatic logoff is implemented for inactivity",
            "Verify encryption and decryption mechanisms for PHI",
            "Confirm audit controls log all PHI access and modifications"
        ],
        "common_violations": [
            "Shared user accounts accessing PHI",
            "No automatic logoff for idle sessions",
            "PHI not encrypted at rest or in transit",
            "No audit logging of PHI access",
            "Audit logs not reviewed regularly"
        ],
        "remediation": [
            "Eliminate shared accounts; implement unique user IDs",
            "Configure automatic logoff (15-minute maximum)",
            "Implement encryption for PHI at rest (AES-256) and in transit (TLS 1.2+)",
            "Enable comprehensive audit logging",
            "Implement regular audit log review process"
        ],
        "risk_level": "critical",
        "penalty_range": "$100-$50,000 per violation; $1.5M annual maximum per category"
    },
    "HIPAA-007": {
        "check_id": "HIPAA-007",
        "category": "Breach Notification Rule",
        "title": "Breach Notification Procedures",
        "description": "Properly notify individuals, HHS, and media (if applicable) of breaches",
        "requirement": "45 CFR 164.400-414 - Breach notification requirements",
        "check_steps": [
            "Verify breach notification policy exists and is current",
            "Confirm individual notification within 60 days of discovery",
            "Check HHS notification procedures (annual for small breaches, 60 days for large)",
            "Verify media notification process for breaches affecting 500+ individuals",
            "Confirm breach risk assessment process to determine notification necessity"
        ],
        "common_violations": [
            "Failure to notify individuals within 60 days",
            "Failure to report breaches to HHS",
            "No breach risk assessment process",
            "Inadequate breach investigation procedures",
            "Failure to notify media for large breaches"
        ],
        "remediation": [
            "Develop comprehensive breach notification policy",
            "Implement breach response team and procedures",
            "Create breach risk assessment framework",
            "Establish individual notification templates and procedures",
            "Train staff on breach identification and reporting"
        ],
        "risk_level": "critical",
        "penalty_range": "$100-$50,000 per violation; $1.5M annual maximum per category"
    },
    "HIPAA-008": {
        "check_id": "HIPAA-008",
        "category": "Privacy Rule",
        "title": "Business Associate Agreements (BAAs)",
        "description": "Ensure BAAs are in place with all business associates who access PHI",
        "requirement": "45 CFR 164.502(e) / 164.504(e) - Business associate contracts",
        "check_steps": [
            "Identify all business associates who create, receive, maintain, or transmit PHI",
            "Verify BAAs are in place with all identified business associates",
            "Confirm BAAs include all required provisions",
            "Check BAAs are updated for material changes in relationship",
            "Verify business associate compliance monitoring procedures"
        ],
        "common_violations": [
            "Missing BAAs with vendors who handle PHI",
            "BAAs do not include all required provisions",
            "BAAs not updated for regulatory changes",
            "No monitoring of business associate compliance",
            "Using vendors who refuse to sign BAAs"
        ],
        "remediation": [
            "Conduct comprehensive business associate inventory",
            "Execute BAAs with all identified business associates",
            "Review and update existing BAAs for compliance",
            "Implement business associate compliance monitoring program",
            "Replace vendors who refuse compliant BAAs"
        ],
        "risk_level": "high",
        "penalty_range": "$100-$50,000 per violation; $1.5M annual maximum per category"
    },
}

# OIG Compliance Check Items (Office of Inspector General - Fraud and Abuse)
OIG_CHECK_ITEMS: Dict[str, Dict[str, Any]] = {
    "OIG-001": {
        "check_id": "OIG-001",
        "category": "Billing and Coding",
        "title": "Accuracy of Claims Submission",
        "description": "Claims are accurately coded and reflect services actually provided",
        "requirement": "False Claims Act (31 USC 3729-3733); Social Security Act 1862(a)(1)(A)",
        "check_steps": [
            "Verify coding accuracy by comparing documentation to billed codes",
            "Check for upcoding (billing higher level than documented)",
            "Review unbundling practices (separately billing components of bundled service)",
            "Verify medical necessity for all billed services",
            "Check for duplicate billing and claims"
        ],
        "common_violations": [
            "Upcoding E/M levels beyond documentation support",
            "Billing for services not rendered",
            "Unbundling services to increase reimbursement",
            "Billing non-covered services as covered services",
            "Duplicate claims submitted"
        ],
        "remediation": [
            "Implement pre-billing coding audit process",
            "Conduct regular retrospective coding audits",
            "Train providers on documentation to support billed codes",
            "Use claim scrubbing software to detect errors before submission",
            "Establish compliance hotline for reporting concerns"
        ],
        "risk_level": "critical",
        "penalty_range": "$11,803-$23,607 per claim (2024); treble damages under FCA"
    },
    "OIG-002": {
        "check_id": "OIG-002",
        "category": "Billing and Coding",
        "title": "Evaluation and Management Documentation",
        "description": "E/M services are documented and billed according to current guidelines",
        "requirement": "CMS E/M Documentation Guidelines; AMA CPT E/M guidelines (2021 updates)",
        "check_steps": [
            "Verify E/M level selection matches documentation (2021 guidelines for office visits)",
            "Check time-based billing accuracy against documented time",
            "Review medical decision-making complexity vs billed level",
            "Verify add-on codes are supported by documentation",
            "Confirm prolonged services are documented when billed"
        ],
        "common_violations": [
            "Billing 99214/99215 without adequate MDM or time documentation",
            "Not documenting total time when using time-based billing",
            "Billing prolonged services without meeting time thresholds",
            "Using 1995 guidelines when 2021 guidelines should apply",
            "Not documenting medical necessity for higher-level visits"
        ],
        "remediation": [
            "Train providers on 2021 E/M guideline changes",
            "Implement E/M leveling audit program",
            "Provide documentation templates supporting appropriate E/M levels",
            "Audit time-based billing for accuracy",
            "Establish internal monitoring of E/M distribution patterns"
        ],
        "risk_level": "high",
        "penalty_range": "$11,803-$23,607 per claim; treble damages under FCA"
    },
    "OIG-003": {
        "check_id": "OIG-003",
        "category": "Exclusion Screening",
        "title": "OIG Exclusion List Screening",
        "description": "Screen all employees, contractors, and vendors against OIG exclusion list",
        "requirement": "42 USC 1320a-7(b) - Excluded individuals may not participate in federal healthcare programs",
        "check_steps": [
            "Verify all employees are screened against OIG exclusion list before hire",
            "Confirm periodic re-screening (monthly recommended) for all workforce",
            "Check that vendors and contractors are screened",
            "Verify no excluded individuals are providing services billed to federal programs",
            "Confirm screening includes SAM.gov (System for Award Management) exclusions"
        ],
        "common_violations": [
            "No exclusion screening process in place",
            "Screening only at hire (no periodic re-checks)",
            "Not screening contractors and vendors",
            "Not screening against SAM.gov in addition to OIG list",
            "Employing excluded individuals in any capacity with federal program billing"
        ],
        "remediation": [
            "Implement monthly OIG exclusion screening for all workforce",
            "Add SAM.gov screening to compliance program",
            "Screen contractors and vendors before engagement",
            "Establish policy for immediate action if exclusion found",
            "Document all screening results and actions taken"
        ],
        "risk_level": "critical",
        "penalty_range": "$11,803 per claim; potential for program exclusion; FCA liability"
    },
    "OIG-004": {
        "check_id": "OIG-004",
        "category": "Anti-Kickback Compliance",
        "title": "Referral and Payment Arrangement Review",
        "description": "Review arrangements with referral sources for AKS compliance",
        "requirement": "42 USC 1320a-7b(b) - Anti-Kickback Statute",
        "check_steps": [
            "Identify all financial arrangements with referral sources",
            "Verify arrangements meet safe harbor protections where applicable",
            "Check fair market value analysis for all compensation arrangements",
            "Review marketing and advertising arrangements for AKS implications",
            "Verify no compensation is based on volume or value of referrals"
        ],
        "common_violations": [
            "Paying referral fees or providing value in exchange for referrals",
            "Compensation arrangements tied to referral volume",
            "Below fair market value rental of space or equipment to referral sources",
            "Excessive compensation to physicians who are referral sources",
            "Joint venture arrangements structured to reward referrals"
        ],
        "remediation": [
            "Conduct fair market value analysis for all physician arrangements",
            "Ensure all arrangements fit within AKS safe harbors",
            "Implement anti-kickback compliance training",
            "Review and restructure any problematic arrangements",
            "Obtain legal opinion for complex financial relationships"
        ],
        "risk_level": "critical",
        "penalty_range": "Up to $100,000 per violation; imprisonment up to 10 years; program exclusion"
    },
    "OIG-005": {
        "check_id": "OIG-005",
        "category": "Compliance Program",
        "title": "Effective Compliance Program",
        "description": "Maintain effective compliance program per OIG guidance",
        "requirement": "OIG Compliance Program Guidance; Social Security Act 1866(j)",
        "check_steps": [
            "Verify written compliance policies and procedures exist",
            "Confirm designation of compliance officer/officer committee",
            "Check compliance education and training program",
            "Review internal monitoring and auditing processes",
            "Verify open lines of communication (hotline, reporting mechanisms)",
            "Check enforcement through disciplinary guidelines",
            "Confirm prompt response to detected offenses"
        ],
        "common_violations": [
            "No formal compliance program",
            "Compliance program exists but is not effectively implemented",
            "No designated compliance officer",
            "No compliance training for staff",
            "No internal auditing or monitoring",
            "No anonymous reporting mechanism"
        ],
        "remediation": [
            "Establish formal compliance program with seven elements",
            "Designate qualified compliance officer with direct board access",
            "Implement annual compliance training for all workforce",
            "Develop internal audit work plan with regular reviews",
            "Establish anonymous compliance hotline",
            "Create and publicize disciplinary guidelines"
        ],
        "risk_level": "high",
        "penalty_range": "Mandatory for certain provider types; mitigating factor in enforcement actions"
    },
}

# Stark Law Compliance Check Items
STARK_CHECK_ITEMS: Dict[str, Dict[str, Any]] = {
    "STARK-001": {
        "check_id": "STARK-001",
        "category": "Physician Self-Referral",
        "title": "DHS Referral Prohibition",
        "description": "Physicians may not refer Medicare/Medicaid patients for DHS to entities with which they have a financial relationship",
        "requirement": "42 USC 1395nn - Stark Law (Physician Self-Referral Law)",
        "check_steps": [
            "Identify all physician financial relationships with the entity",
            "Determine if entity provides designated health services (DHS)",
            "Check if referrals from physicians with financial relationships are for DHS",
            "Verify applicable exception applies to each financial relationship",
            "Confirm referral patterns are not influenced by financial relationship"
        ],
        "common_violations": [
            "Physician ownership in entity providing DHS without meeting an exception",
            "Compensation arrangements with DHS-referring physicians without exception",
            "Failure to meet all elements of a claimed Stark exception",
            "Physician self-referrals to entities with financial relationship",
            "Inadequate documentation of fair market value compensation"
        ],
        "remediation": [
            "Conduct comprehensive financial relationship inventory",
            "Analyze each relationship against Stark exceptions",
            "Obtain fair market value opinions for all physician compensation",
            "Restructure arrangements that do not meet exceptions",
            "Implement monitoring of referral patterns by physicians with financial relationships"
        ],
        "risk_level": "critical",
        "penalty_range": "$15,000-$100,000 per claim; program exclusion possible"
    },
    "STARK-002": {
        "check_id": "STARK-002",
        "category": "Physician Self-Referral",
        "title": "Compensation Arrangement Exceptions",
        "description": "Verify physician compensation arrangements meet Stark Law exceptions",
        "requirement": "42 USC 1395nn(e) - Stark Law exceptions for compensation arrangements",
        "check_steps": [
            "Identify all physician compensation arrangements",
            "Verify arrangements are in writing and signed by parties",
            "Confirm compensation is fair market value for services actually provided",
            "Check that compensation does not vary with volume or value of referrals",
            "Verify arrangement is commercially reasonable"
        ],
        "common_violations": [
            "Compensation arrangements not in writing",
            "Compensation above or below fair market value",
            "Compensation varies based on referral volume or value",
            "Arrangement not commercially reasonable",
            "Services not actually provided or documented"
        ],
        "remediation": [
            "Execute written agreements for all physician compensation arrangements",
            "Obtain independent fair market value opinions",
            "Ensure compensation methodology does not correlate with referrals",
            "Document commercial reasonableness of each arrangement",
            "Implement regular compensation monitoring and audit process"
        ],
        "risk_level": "critical",
        "penalty_range": "$15,000-$100,000 per claim; program exclusion possible"
    },
    "STARK-003": {
        "check_id": "STARK-003",
        "category": "Physician Self-Referral",
        "title": "Ownership/Investment Interest Disclosure",
        "description": "Verify disclosure of physician ownership/investment interests in DHS entities",
        "requirement": "42 USC 1395nn(a) - Stark Law ownership/investment restrictions",
        "check_steps": [
            "Identify all physicians with ownership or investment interests",
            "Verify DHS entity disclosure requirements are met",
            "Check for prohibited ownership structures (compensation based on DHS referrals)",
            "Confirm ownership percentage does not exceed applicable limits",
            "Verify group practice compliance if applicable"
        ],
        "common_violations": [
            "Undisclosed physician ownership in DHS entities",
            "Compensation from DHS entity based on referrals",
            "Physician ownership exceeding permitted thresholds",
            "Group practice not meeting Stark definition",
            "In-office ancillary services not meeting all requirements"
        ],
        "remediation": [
            "Conduct physician ownership disclosure audit",
            "Ensure all ownership interests are properly disclosed",
            "Review and restructure prohibited ownership arrangements",
            "Verify group practice compliance with Stark definition",
            "Confirm in-office ancillary services exception requirements are met"
        ],
        "risk_level": "high",
        "penalty_range": "$15,000-$100,000 per claim; program exclusion possible"
    },
}

# Anti-Kickback Statute (AKS) Compliance Check Items
AKS_CHECK_ITEMS: Dict[str, Dict[str, Any]] = {
    "AKS-001": {
        "check_id": "AKS-001",
        "category": "Remuneration Prohibition",
        "title": "Prohibited Remuneration for Referrals",
        "description": "No remuneration (direct or indirect) to induce or reward referrals for federal healthcare program services",
        "requirement": "42 USC 1320a-7b(b) - Anti-Kickback Statute",
        "check_steps": [
            "Review all financial arrangements with referral sources for remuneration",
            "Identify gifts, discounts, or other benefits provided to referring parties",
            "Check marketing and educational programs for improper inducement",
            "Review physician consulting and speaker arrangements",
            "Verify no compensation is tied to volume or value of referrals"
        ],
        "common_violations": [
            "Providing gifts or free services to referring physicians",
            "Speaker programs with excessive compensation or no legitimate audience",
            "Consulting arrangements paying for referrals rather than services",
            "Free equipment or supplies conditioned on product usage",
            "Volume-based discounts that effectively pay for referrals"
        ],
        "remediation": [
            "Review all financial arrangements for AKS compliance",
            "Eliminate gifts and free services to referral sources",
            "Restructure speaker programs to ensure legitimate educational purpose",
            "Document fair market value for all consulting arrangements",
            "Implement AKS compliance training for all staff and providers"
        ],
        "risk_level": "critical",
        "penalty_range": "Up to $100,000 per violation; imprisonment up to 10 years; program exclusion"
    },
    "AKS-002": {
        "check_id": "AKS-002",
        "category": "Safe Harbor Compliance",
        "title": "Safe Harbor Protections",
        "description": "Verify financial arrangements fit within applicable AKS safe harbors",
        "requirement": "42 CFR 1001.952 - AKS Regulatory Safe Harbors",
        "check_steps": [
            "Identify all financial arrangements that could implicate AKS",
            "Determine which safe harbors potentially apply to each arrangement",
            "Verify all elements of applicable safe harbor are met",
            "Document compliance with safe harbor requirements",
            "Check arrangements that do not fit safe harbors for AKS risk"
        ],
        "common_violations": [
            "Arrangement does not meet all elements of claimed safe harbor",
            "Not documenting safe harbor compliance for each arrangement",
            "Assuming safe harbor protection without verifying all elements",
            "Modifying arrangement terms without re-evaluating safe harbor fit",
            "Overreliance on safe harbors without legal analysis"
        ],
        "remediation": [
            "Conduct safe harbor analysis for each financial arrangement",
            "Document compliance with each safe harbor element",
            "Obtain legal opinion for arrangements not clearly within safe harbors",
            "Restructure arrangements that do not fit safe harbors",
            "Implement periodic review of arrangement compliance"
        ],
        "risk_level": "high",
        "penalty_range": "Up to $100,000 per violation; imprisonment up to 10 years; program exclusion"
    },
    "AKS-003": {
        "check_id": "AKS-003",
        "category": "Patient Inducement",
        "title": "Beneficiary Inducement",
        "description": "No remuneration to induce beneficiaries to obtain items/services from a particular provider",
        "requirement": "42 USC 1320a-7b(b)(3) - Beneficiary Inducement Civil Monetary Penalty",
        "check_steps": [
            "Review patient incentive programs for compliance",
            "Check copay waiver or reduction practices",
            "Verify transport and accommodation assistance programs",
            "Review patient giveaway and marketing programs",
            "Check value-based arrangements with patients for compliance"
        ],
        "common_violations": [
            "Routinely waiving copays without financial need determination",
            "Providing gifts of more than nominal value to patients",
            "Offering free transportation conditioned on using specific provider",
            "Providing cash payments or gift cards for patient referrals",
            "Marketing free services to induce Medicare/Medicaid patients"
        ],
        "remediation": [
            "Implement financial need assessment before waiving copays",
            "Review and limit patient incentive programs to nominal value",
            "Ensure transportation programs are not conditioned on provider choice",
            "Eliminate cash or cash-equivalent gifts to patients",
            "Train staff on beneficiary inducement prohibitions"
        ],
        "risk_level": "high",
        "penalty_range": "Up to $106,440 per violation (2024 CMP); program exclusion possible"
    },
}


# Regulation registry for easy lookup
REGULATION_REGISTRY: Dict[str, Dict[str, Any]] = {
    "hipaa": {
        "name": "HIPAA (Health Insurance Portability and Accountability Act)",
        "full_name": "Health Insurance Portability and Accountability Act of 1996",
        "check_items": HIPAA_CHECK_ITEMS,
        "total_checks": len(HIPAA_CHECK_ITEMS),
        "key_rules": ["Privacy Rule", "Security Rule", "Breach Notification Rule", "Enforcement Rule"]
    },
    "oig": {
        "name": "OIG Fraud and Abuse",
        "full_name": "OIG Compliance Program Guidance and Fraud/Abuse Laws",
        "check_items": OIG_CHECK_ITEMS,
        "total_checks": len(OIG_CHECK_ITEMS),
        "key_rules": ["False Claims Act", "Anti-Kickback Statute", "Physician Self-Referral (Stark)", "Exclusion Authorities"]
    },
    "stark": {
        "name": "Stark Law (Physician Self-Referral)",
        "full_name": "Ethics in Patient Referrals Act (Stark Law)",
        "check_items": STARK_CHECK_ITEMS,
        "total_checks": len(STARK_CHECK_ITEMS),
        "key_rules": ["Self-Referral Prohibition", "Compensation Exception Requirements", "Ownership/Investment Restrictions"]
    },
    "aks": {
        "name": "Anti-Kickback Statute",
        "full_name": "Medicare and Medicaid Anti-Kickback Statute",
        "check_items": AKS_CHECK_ITEMS,
        "total_checks": len(AKS_CHECK_ITEMS),
        "key_rules": ["Remuneration Prohibition", "Safe Harbor Protections", "Beneficiary Inducement CMP"]
    }
}


@skill(name="compliance_checker", category="healthcare")
class ComplianceCheckerSkill(AetheraSkill):
    """
    Check HIPAA, OIG, Stark, and AKS compliance.
    """

    @property
    def name(self) -> str:
        return "compliance_checker"

    @property
    def description(self) -> str:
        return "Run compliance audits for HIPAA, OIG, Stark Law, and Anti-Kickback Statute; flag violations; generate remediation steps"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["run_audit", "flag_violations", "get_remediation", "list_regulations", "get_check_detail"],
                    "description": "Action: run_audit, flag_violations, get_remediation, list_regulations, get_check_detail"
                },
                "regulation": {
                    "type": "string",
                    "enum": ["hipaa", "oig", "stark", "aks", "all"],
                    "description": "Regulation to check (hipaa, oig, stark, aks, or all)"
                },
                "check_id": {
                    "type": "string",
                    "description": "Specific check ID to examine (e.g., HIPAA-001, OIG-003)"
                },
                "findings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "check_id": {"type": "string"},
                            "status": {"type": "string", "enum": ["pass", "fail", "partial", "not_assessed"]},
                            "notes": {"type": "string"}
                        }
                    },
                    "description": "Assessment findings for flag_violations and get_remediation actions"
                }
            },
            "required": ["action"]
        }

    @property
    def requires_phi_protection(self) -> bool:
        return False

    @property
    def examples(self) -> list:
        return [
            {"input": {"action": "run_audit", "regulation": "hipaa"}},
            {"input": {"action": "get_check_detail", "check_id": "OIG-003"}},
            {"input": {"action": "flag_violations", "regulation": "all", "findings": [{"check_id": "HIPAA-001", "status": "fail"}, {"check_id": "HIPAA-004", "status": "partial"}]}},
            {"input": {"action": "list_regulations"}},
        ]

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "run_audit")

        try:
            if action == "run_audit":
                regulation = kwargs.get("regulation", "all")
                result = self._run_audit(regulation)

            elif action == "flag_violations":
                regulation = kwargs.get("regulation", "all")
                findings = kwargs.get("findings", [])
                result = self._flag_violations(findings, regulation)

            elif action == "get_remediation":
                findings = kwargs.get("findings", [])
                result = self._get_remediation(findings)

            elif action == "list_regulations":
                result = self._list_regulations()

            elif action == "get_check_detail":
                check_id = kwargs.get("check_id", "")
                if not check_id:
                    return SkillResult(success=False, error="Check ID is required for get_check_detail action")
                result = self._get_check_detail(check_id)

            else:
                return SkillResult(success=False, error=f"Unknown action: {action}")

            return SkillResult(success=True, data=result)

        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _run_audit(self, regulation: str) -> Dict[str, Any]:
        """Run a comprehensive compliance audit checklist."""
        regulations = [regulation] if regulation != "all" else list(REGULATION_REGISTRY.keys())
        audit_results = {}
        total_checks = 0
        total_required_checks = 0

        for reg_key in regulations:
            reg_data = REGULATION_REGISTRY.get(reg_key)
            if not reg_data:
                continue

            checks = []
            for check_id, check_data in reg_data["check_items"].items():
                total_required_checks += 1
                checks.append({
                    "check_id": check_id,
                    "title": check_data["title"],
                    "category": check_data["category"],
                    "risk_level": check_data["risk_level"],
                    "check_steps": check_data["check_steps"],
                    "common_violations": check_data["common_violations"],
                    "status": "not_assessed",
                    "requires_assessment": True
                })
                total_checks += 1

            audit_results[reg_key] = {
                "regulation_name": reg_data["name"],
                "total_checks": len(checks),
                "checks": checks
            }

        return {
            "audit_type": "Comprehensive compliance audit checklist",
            "regulations_audited": regulations,
            "total_checks": total_checks,
            "audit_results": audit_results,
            "instructions": "Review each check item, assess compliance status, and use flag_violations action to report findings"
        }

    def _flag_violations(self, findings: List[Dict[str, Any]], regulation: str) -> Dict[str, Any]:
        """Flag violations from assessment findings."""
        violations = []
        warnings = []
        passed = []

        for finding in findings:
            check_id = finding.get("check_id", "").upper()
            status = finding.get("status", "not_assessed")
            notes = finding.get("notes", "")

            # Look up check data across all regulations
            check_data = None
            parent_regulation = None
            for reg_key, reg_data in REGULATION_REGISTRY.items():
                if check_id in reg_data["check_items"]:
                    check_data = reg_data["check_items"][check_id]
                    parent_regulation = reg_key
                    break

            if not check_data:
                violations.append({
                    "check_id": check_id,
                    "error": f"Check ID {check_id} not found in any regulation",
                    "status": status
                })
                continue

            flagged_item = {
                "check_id": check_id,
                "title": check_data["title"],
                "category": check_data["category"],
                "regulation": parent_regulation,
                "status": status,
                "risk_level": check_data["risk_level"],
                "notes": notes,
                "penalty_range": check_data["penalty_range"]
            }

            if status == "fail":
                flagged_item["common_violations"] = check_data["common_violations"]
                flagged_item["remediation"] = check_data["remediation"]
                violations.append(flagged_item)
            elif status == "partial":
                flagged_item["common_violations"] = check_data["common_violations"]
                flagged_item["remediation"] = check_data["remediation"]
                warnings.append(flagged_item)
            elif status == "pass":
                passed.append(flagged_item)

        # Sort violations by risk level
        risk_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        violations.sort(key=lambda x: risk_order.get(x.get("risk_level", "low"), 3))
        warnings.sort(key=lambda x: risk_order.get(x.get("risk_level", "low"), 3))

        critical_count = sum(1 for v in violations if v.get("risk_level") == "critical")
        high_count = sum(1 for v in violations if v.get("risk_level") == "high")

        return {
            "regulation_filter": regulation,
            "total_findings": len(findings),
            "violations": {
                "total": len(violations),
                "critical": critical_count,
                "high": high_count,
                "items": violations
            },
            "warnings": {
                "total": len(warnings),
                "items": warnings
            },
            "passed": {
                "total": len(passed)
            },
            "overall_risk": "critical" if critical_count > 0 else "high" if high_count > 0 else "moderate" if violations else "low",
            "immediate_action_required": critical_count > 0
        }

    def _get_remediation(self, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get remediation steps for flagged findings."""
        remediation_steps = []
        prioritized_actions = []

        for finding in findings:
            check_id = finding.get("check_id", "").upper()
            status = finding.get("status", "not_assessed")

            if status not in ("fail", "partial"):
                continue

            # Look up check data
            check_data = None
            parent_regulation = None
            for reg_key, reg_data in REGULATION_REGISTRY.items():
                if check_id in reg_data["check_items"]:
                    check_data = reg_data["check_items"][check_id]
                    parent_regulation = reg_key
                    break

            if not check_data:
                continue

            remediation = {
                "check_id": check_id,
                "title": check_data["title"],
                "regulation": parent_regulation,
                "risk_level": check_data["risk_level"],
                "status": status,
                "remediation_steps": check_data["remediation"],
                "common_violations_to_address": check_data["common_violations"],
                "penalty_exposure": check_data["penalty_range"]
            }
            remediation_steps.append(remediation)

            # Add to prioritized actions based on risk level
            if check_data["risk_level"] == "critical":
                for step in check_data["remediation"][:2]:
                    prioritized_actions.append({
                        "priority": "immediate",
                        "check_id": check_id,
                        "action": step,
                        "risk_level": "critical"
                    })
            elif check_data["risk_level"] == "high":
                for step in check_data["remediation"][:1]:
                    prioritized_actions.append({
                        "priority": "urgent",
                        "check_id": check_id,
                        "action": step,
                        "risk_level": "high"
                    })

        return {
            "total_findings_requiring_remediation": len(remediation_steps),
            "remediation_steps": remediation_steps,
            "prioritized_actions": sorted(prioritized_actions, key=lambda x: {"immediate": 0, "urgent": 1, "scheduled": 2}.get(x["priority"], 3)),
            "summary": {
                "critical_items": sum(1 for r in remediation_steps if r["risk_level"] == "critical"),
                "high_items": sum(1 for r in remediation_steps if r["risk_level"] == "high"),
                "medium_items": sum(1 for r in remediation_steps if r["risk_level"] == "medium"),
                "total_steps": sum(len(r["remediation_steps"]) for r in remediation_steps)
            }
        }

    def _list_regulations(self) -> Dict[str, Any]:
        """List all available compliance regulations and their check items."""
        regulations = []
        for reg_key, reg_data in REGULATION_REGISTRY.items():
            check_items = []
            for check_id, check_data in reg_data["check_items"].items():
                check_items.append({
                    "check_id": check_id,
                    "title": check_data["title"],
                    "category": check_data["category"],
                    "risk_level": check_data["risk_level"]
                })

            regulations.append({
                "key": reg_key,
                "name": reg_data["name"],
                "full_name": reg_data["full_name"],
                "total_checks": reg_data["total_checks"],
                "key_rules": reg_data["key_rules"],
                "check_items": check_items
            })

        total_checks = sum(r["total_checks"] for r in regulations)

        return {
            "total_regulations": len(regulations),
            "total_check_items": total_checks,
            "regulations": regulations
        }

    def _get_check_detail(self, check_id: str) -> Dict[str, Any]:
        """Get full details for a specific compliance check item."""
        check_id_upper = check_id.upper()

        for reg_key, reg_data in REGULATION_REGISTRY.items():
            if check_id_upper in reg_data["check_items"]:
                check_data = reg_data["check_items"][check_id_upper]
                return {
                    "check_id": check_id_upper,
                    "regulation": reg_key,
                    "regulation_name": reg_data["name"],
                    "title": check_data["title"],
                    "category": check_data["category"],
                    "description": check_data["description"],
                    "requirement": check_data["requirement"],
                    "risk_level": check_data["risk_level"],
                    "penalty_range": check_data["penalty_range"],
                    "check_steps": check_data["check_steps"],
                    "common_violations": check_data["common_violations"],
                    "remediation": check_data["remediation"]
                }

        available_ids = []
        for reg_data in REGULATION_REGISTRY.values():
            available_ids.extend(reg_data["check_items"].keys())

        return {
            "check_id": check_id_upper,
            "error": f"Check ID {check_id_upper} not found",
            "available_check_ids": available_ids
        }