"""
Security best practices reference.

Information security best practices for healthcare systems
including HITRUST, NIST, and OWASP frameworks.
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.nist.gov/cyberframework"
DEST_DIR = DATA_ROOT / "technology" / "security"
MODULE_NAME = "knowledge_bases.technology.security_best_practices"

SECURITY_REFERENCE = {
    "nist_cybersecurity_framework": {
        "functions": [
            {"function": "Identify", "description": "Develop organizational understanding of cybersecurity risk", "categories": ["Asset Management", "Business Environment", "Governance", "Risk Assessment", "Risk Management Strategy", "Supply Chain Risk Management"]},
            {"function": "Protect", "description": "Develop and implement safeguards to ensure delivery of critical services", "categories": ["Access Control", "Awareness and Training", "Data Security", "Information Protection", "Maintenance", "Protective Technology"]},
            {"function": "Detect", "description": "Define activities to identify cybersecurity events", "categories": ["Anomalies and Events", "Security Continuous Monitoring", "Detection Processes"]},
            {"function": "Respond", "description": "Define activities to take action regarding detected cybersecurity event", "categories": ["Response Planning", "Communications", "Analysis", "Mitigation", "Improvements"]},
            {"function": "Recover", "description": "Identify activities to maintain plans for resilience and restore capabilities", "categories": ["Recovery Planning", "Improvements", "Communications"]},
        ],
    },
    "hitrust_csF": {
        "description": "Health Information Trust Common Security Framework",
        "certification_levels": ["Self-assessment", "Third-party assessment", "Certified assessment"],
        "domains": ["Information Protection Management", "Endpoint Protection", "Network Protection", "Access Protection", "Data Protection", "Vulnerability/Threat Management", "Audit/Compliance Management", "Asset Management", "Incident Management", "Business Continuity Management"],
    },
    "owasp_top_10_2021": [
        {"rank": 1, "risk": "Broken Access Control", "description": "Restrictions on authenticated users not properly enforced", "mitigation": "Deny by default; implement access control mechanisms; disable directory listing"},
        {"rank": 2, "risk": "Cryptographic Failures", "description": "Failures related to cryptography leading to sensitive data exposure", "mitigation": "Classify data; use strong algorithms; encrypt in transit and at rest; manage keys properly"},
        {"rank": 3, "risk": "Injection", "description": "Untrusted data sent to interpreter as part of command/query", "mitigation": "Use parameterized queries; input validation; use ORMs"},
        {"rank": 4, "risk": "Insecure Design", "description": "Missing or ineffective security controls in design", "mitigation": "Threat modeling; secure design patterns; reference architecture"},
        {"rank": 5, "risk": "Security Misconfiguration", "description": "Insecure default configurations, incomplete setups, open cloud storage", "mitigation": "Hardening process; minimal platform; review configurations; segmented architecture"},
        {"rank": 6, "risk": "Vulnerable and Outdated Components", "description": "Using components with known vulnerabilities", "mitigation": "Remove unused dependencies; continuously inventory versions; monitor CVEs; only from official sources"},
        {"rank": 7, "risk": "Identification and Authentication Failures", "description": "Confirmation of user identity, authentication, or session management fails", "mitigation": "MFA; no default credentials; weak password checks; limit failed logins"},
        {"rank": 8, "risk": "Software and Data Integrity Failures", "description": "Code and infrastructure not protected against integrity violations", "mitigation": "Verify software/data integrity; use digital signatures; secure CI/CD pipeline"},
        {"rank": 9, "risk": "Security Logging and Monitoring Failures", "description": "Insufficient logging, detection, monitoring, and response", "mitigation": "Log all login/access control failures; ensure logs in consumable format; centralized management"},
        {"rank": 10, "risk": "Server-Side Request Forgery (SSRF)", "description": "Server fetches remote resource without validating user-supplied URL", "mitigation": "Sanitize/validate client URL input; disable HTTP redirections; block external access"},
    ],
    "hipaa_security_requirements": [
        "Risk analysis - conduct thorough risk assessment",
        "Access controls - unique user IDs, emergency access, automatic logoff",
        "Audit controls - hardware/software that record activity",
        "Integrity controls - mechanisms to authenticate ePHI",
        "Transmission security - encryption of ePHI in transit",
        "Backup and recovery - contingency operations plan",
        "Encryption - addressable for data at rest; required understanding",
        "Disposal - proper media sanitization and disposal",
    ],
}


async def download(force: bool = False) -> dict:
    """Download security best practices reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "security_best_practices.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading security best practices reference...")
    save_json(SECURITY_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded security best practices reference"}