"""
License type reference.

Software and data license types and their implications for
healthcare data usage and compliance.
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://opensource.org/licenses"
DEST_DIR = DATA_ROOT / "legal" / "licensing"
MODULE_NAME = "knowledge_bases.legal.license_types"

LICENSE_REFERENCE = {
    "open_source_licenses": [
        {"name": "MIT License", "type": "Permissive", "description": "Very permissive; allows any use with attribution; no copyleft", "commercial_use": True, "modification": True, "distribution": True, "patent_grant": False},
        {"name": "Apache License 2.0", "type": "Permissive", "description": "Permissive with patent grant and contribution protection", "commercial_use": True, "modification": True, "distribution": True, "patent_grant": True},
        {"name": "GPL v3", "type": "Copyleft", "description": "Strong copyleft; derivative works must also be GPL", "commercial_use": True, "modification": True, "distribution": True, "copyleft": True},
        {"name": "AGPL v3", "type": "Strong Copyleft", "description": "Network copyleft; applies to SaaS/network use", "commercial_use": True, "modification": True, "distribution": True, "network_copyleft": True},
        {"name": "BSD 3-Clause", "type": "Permissive", "description": "Permissive with non-endorsement clause", "commercial_use": True, "modification": True, "distribution": True},
        {"name": "LGPL v3", "type": "Weak Copyleft", "description": "Allows linking without copyleft; modifications to library are copyleft", "commercial_use": True, "modification": True, "distribution": True, "weak_copyleft": True},
    ],
    "healthcare_data_licenses": [
        {"name": "CPT License (AMA)", "description": "Required license to use CPT codes; annual fee; restricts redistribution", "restrictions": "Cannot redistribute raw codes; must maintain license", "cost": "Annual licensing fee varies by use case"},
        {"name": "LOINC License (Regenstrief)", "description": "Free for most uses; license agreement required", "restrictions": "Attribution required; some restrictions on redistribution", "cost": "Free for most uses"},
        {"name": "SNOMED CT License (NLM/HTSD)", "description": "Free for US via NLM license; international via member license", "restrictions": "Must register; attribution required; sub-distribution restricted", "cost": "Free in US through NLM; varies internationally"},
        {"name": "UMLS License (NLM)", "description": "License required to access Unified Medical Language System", "restrictions": "Must sign license agreement; annual recertification; some restrictions on redistribution", "cost": "Free with license agreement"},
        {"name": "ICD-10 (WHO/CMS)", "description": "ICD-10 modifications free in US; WHO ICD-10 requires license for modifications", "restrictions": "US modifications freely available via CMS; WHO version has different terms", "cost": "Free for US CMS version"},
        {"name": "HL7 FHIR License", "description": "Creative Commons Attribution 4.0 for specification; implementations vary", "restrictions": "Specification freely available; implementation may involve licensed terminology", "cost": "Free for specification"},
    ],
    "creative_commons": [
        {"name": "CC0", "description": "Public domain dedication; no rights reserved"},
        {"name": "CC-BY", "description": "Attribution required; otherwise free to use"},
        {"name": "CC-BY-SA", "description": "Attribution + share-alike; derivatives must use same license"},
        {"name": "CC-BY-NC", "description": "Attribution + non-commercial use only"},
        {"name": "CC-BY-ND", "description": "Attribution + no derivatives"},
        {"name": "CC-BY-NC-SA", "description": "Attribution + non-commercial + share-alike"},
        {"name": "CC-BY-NC-ND", "description": "Attribution + non-commercial + no derivatives (most restrictive)"},
    ],
}


async def download(force: bool = False) -> dict:
    """Download license type reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "license_types.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading license type reference...")
    save_json(LICENSE_REFERENCE, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": "Downloaded license type reference"}