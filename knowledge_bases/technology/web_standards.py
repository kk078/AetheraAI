"""
Web standards reference.

Key web standards relevant to healthcare application development
including FHIR, OAuth2, OpenAPI, and security standards.
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.w3.org/standards/"
DEST_DIR = DATA_ROOT / "technology" / "web_standards"
MODULE_NAME = "knowledge_bases.technology.web_standards"

WEB_STANDARDS = {
    "healthcare_interoperability": [
        {"standard": "HL7 FHIR R4", "description": "Fast Healthcare Interoperability Resources; RESTful API standard for healthcare data exchange", "resources": ["Patient", "Observation", "Condition", "Procedure", "MedicationRequest", "Encounter", "DiagnosticReport", "Immunization", "AllergyIntolerance", "CarePlan", "Claim", "ExplanationOfBenefit"], "mime_types": ["application/fhir+json", "application/fhir+xml"]},
        {"standard": "SMART on FHIR", "description": "Authorization framework for FHIR using OAuth2; enables app authorization in clinical context", "scopes": ["patient/*.read", "user/*.read", "launch", "launch/patient", "openid", "fhirUser"]},
        {"standard": "USCDI v3", "description": "US Core Data for Interoperability; standardized set of health data classes and elements for nationwide exchange", "data_classes": ["Patient Demographics", "Allergies/Intolerances", "Assessment/Plan of Treatment", "Care Team Members", "Clinical Notes", "Encounter", "Health Concerns", "Immunizations", "Lab Results", "Medications", "Problems", "Procedures", "Provenance", "Vital Signs"]},
        {"standard": "C-CDA", "description": "Consolidated CDA; clinical document architecture for structured clinical documents", "document_types": ["Continuity of Care Document (CCD)", "Discharge Summary", "History and Physical", "Progress Note", "Consultation Note", "Procedure Note"]},
    ],
    "api_standards": [
        {"standard": "OpenAPI 3.1", "description": "Specification for describing RESTful APIs", "use": "API documentation, code generation, testing"},
        {"standard": "GraphQL", "description": "Query language and runtime for APIs", "use": "Flexible data retrieval; reduces over/under-fetching"},
        {"standard": "gRPC", "description": "High-performance RPC framework using Protocol Buffers", "use": "Microservice communication; low-latency systems"},
    ],
    "authentication_authorization": [
        {"standard": "OAuth 2.0", "description": "Authorization framework for third-party application access", "grant_types": ["Authorization Code", "Client Credentials", "Refresh Token", "PKCE (for public clients)"], "healthcare_use": "SMART on FHIR, EHR integration"},
        {"standard": "OpenID Connect (OIDC)", "description": "Identity layer on top of OAuth 2.0", "use": "Single sign-on, identity verification, user info"},
        {"standard": "SAML 2.0", "description": "XML-based SSO standard", "use": "Enterprise SSO, federated identity, healthcare portals"},
        {"standard": "JWT (JSON Web Token)", "description": "Compact URL-safe token format for claims", "use": "Stateless authentication, API tokens"},
    ],
    "security_standards": [
        {"standard": "TLS 1.3", "description": "Transport Layer Security for encrypted communications", "healthcare_requirement": "Required for all PHI transmission under HIPAA Security Rule"},
        {"standard": "JSON Web Encryption (JWE)", "description": "Standard for encrypting JSON content", "use": "Encrypting FHIR resources, securing PHI in transit"},
        {"standard": "JSON Web Signature (JWS)", "description": "Standard for digitally signing JSON content", "use": "Verifying authenticity of FHIR resources and API responses"},
    ],
    "data_standards": [
        {"standard": "JSON Schema", "description": "Vocabulary for validating JSON document structure", "use": "Validating FHIR resources, API request/response validation"},
        {"standard": "SNOMED CT", "description": "Systematized Nomenclature of Medicine Clinical Terms", "use": "Standardized clinical terminology; coded problem lists, procedures"},
        {"standard": "LOINC", "description": "Logical Observation Identifiers Names and Codes", "use": "Standardized lab/observation codes; clinical observations"},
        {"standard": "RxNorm", "description": "Normalized naming for clinical drugs", "use": "Medication identification, prescribing, drug interactions"},
    ],
}


async def download(force: bool = False) -> dict:
    """Download web standards reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "web_standards.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading web standards reference...")
    save_json(WEB_STANDARDS, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded web standards reference"}