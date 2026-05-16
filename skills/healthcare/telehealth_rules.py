"""
Aethera AI - Telehealth Rules Skill

Telehealth billing rules by state and payer. Covers Medicare telehealth rules,
POS codes 02/10, GT/95 modifiers, state parity laws, and payer-specific coverage.
"""

from typing import Dict, Any, List, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill


# Telehealth rules for all 50 states (top 10 in detail, rest summarized)
STATE_TELEHEALTH_RULES: Dict[str, Dict[str, Any]] = {
    "CA": {
        "name": "California",
        "parity_law": True,
        "parity_details": "CA requires commercial payers to reimburse telehealth services at the same rate as in-person services. AB 2839 (2022) strengthened parity requirements.",
        "medicaid_telehealth": "Comprehensive",
        "medicaid_details": "Medi-Cal reimburses telehealth for most covered services. Audio-only allowed for established patients when video not available.",
        "consent_required": "Informed consent required before or at first telehealth visit",
        "prescribing_rules": "Controlled substances: telehealth prescribing allowed for Schedules III-V. Schedule II requires established provider-patient relationship. BPC section 2242.",
        "eligible_providers": "All licensed providers in CA",
        "eligible_modalities": ["video", "audio-only", "store-and-forward", "remote_patient_monitoring"],
        "pos_codes": {"02": "Telehealth (non-patient home)", "10": "Telehealth (patient home)"},
        "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"},
        "notes": "CA is one of the most telehealth-friendly states. Post-PHE flexibilities largely made permanent."
    },
    "TX": {
        "name": "Texas",
        "parity_law": True,
        "parity_details": "TX Insurance Code Section 1455.004 requires parity for telehealth reimbursement. HB 4 (2023) made many PHE flexibilities permanent.",
        "medicaid_telehealth": "Comprehensive",
        "medicaid_details": "Texas Medicaid covers telehealth for most covered services. Audio-only reimbursable. Home health telehealth allowed.",
        "consent_required": "Written or verbal consent required, documented in medical record",
        "prescribing_rules": "Controlled substances allowed via telehealth with valid provider-patient relationship. Texas Medical Board has specific telemedicine prescribing rules (22 TAC 172.12).",
        "eligible_providers": "All licensed TX providers; out-of-state with TX license or compact",
        "eligible_modalities": ["video", "audio-only", "store-and-forward", "remote_patient_monitoring"],
        "pos_codes": {"02": "Telehealth (non-patient home)", "10": "Telehealth (patient home)"},
        "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"},
        "notes": "TX permanently adopted many COVID-era telehealth flexibilities. Audio-only reimbursement is notable."
    },
    "NY": {
        "name": "New York",
        "parity_law": True,
        "parity_details": "NY Insurance Law Section 4317 requires parity. Effective Jan 2022, commercial payers must reimburse telehealth at same rate as in-person.",
        "medicaid_telehealth": "Comprehensive",
        "medicaid_details": "NY Medicaid covers video and audio-only telehealth. Store-and-forward limited. Telephonic services for established patients.",
        "consent_required": "Informed consent required at first visit; verbal acceptable, must be documented",
        "prescribing_rules": "NY allows telehealth prescribing including controlled substances when proper provider-patient relationship exists. Education Law Section 6803.",
        "eligible_providers": "All NY licensed providers; limited out-of-state via special registration",
        "eligible_modalities": ["video", "audio-only", "store-and-forward"],
        "pos_codes": {"02": "Telehealth (non-patient home)", "10": "Telehealth (patient home)"},
        "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"},
        "notes": "NY adopted strong parity. Audio-only coverage for established patients is a key feature."
    },
    "FL": {
        "name": "Florida",
        "parity_law": True,
        "parity_details": "FL Statute 627.6616 requires commercial payers to cover telehealth. Parity for reimbursement mandated by SB 7016 (2022).",
        "medicaid_telehealth": "Comprehensive",
        "medicaid_details": "Florida Medicaid covers synchronous and asynchronous telehealth. Audio-only for established patients and behavioral health.",
        "consent_required": "Verbal consent required, documented in medical record",
        "prescribing_rules": "Telehealth prescribing permitted. Controlled substances: federal rules apply (DEA telehealth prescribing). FL Board of Medicine Rule 64B8-9.0141.",
        "eligible_providers": "FL licensed providers; out-of-state must register with FL Board",
        "eligible_modalities": ["video", "audio-only", "store-and-forward"],
        "pos_codes": {"02": "Telehealth (non-patient home)", "10": "Telehealth (patient home)"},
        "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"},
        "notes": "FL has robust telehealth law. Out-of-state provider registration is available."
    },
    "IL": {
        "name": "Illinois",
        "parity_law": True,
        "parity_details": "IL Public Act 102-0675 requires commercial payer parity for telehealth. Audio-only parity also mandated.",
        "medicaid_telehealth": "Comprehensive",
        "medicaid_details": "IL Medicaid covers video, audio-only, and store-and-forward. Behavioral health telehealth expanded permanently.",
        "consent_required": "Informed consent required; verbal acceptable, must document in chart",
        "prescribing_rules": "Telehealth prescribing allowed per IL Medical Practice Act. Controlled substances follow federal DEA telehealth rules.",
        "eligible_providers": "IL licensed providers",
        "eligible_modalities": ["video", "audio-only", "store-and-forward", "remote_patient_monitoring"],
        "pos_codes": {"02": "Telehealth (non-patient home)", "10": "Telehealth (patient home)"},
        "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"},
        "notes": "IL strong parity including audio-only. Behavioral health telehealth has special expanded provisions."
    },
    "PA": {
        "name": "Pennsylvania",
        "parity_law": True,
        "parity_details": "PA Act 19 of 2022 requires commercial payers to cover telehealth and reimburse at parity. Audio-only included.",
        "medicaid_telehealth": "Comprehensive",
        "medicaid_details": "PA Medicaid covers synchronous telehealth and audio-only. Store-and-forward limited to specific services.",
        "consent_required": "Informed consent required; may be verbal, must document",
        "prescribing_rules": "Controlled substance prescribing via telehealth follows federal rules. PA Medical Board telemedicine regulations under 49 Pa. Code Chapter 18.",
        "eligible_providers": "PA licensed providers; limited out-of-state options",
        "eligible_modalities": ["video", "audio-only", "store-and-forward"],
        "pos_codes": {"02": "Telehealth (non-patient home)", "10": "Telehealth (patient home)"},
        "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"},
        "notes": "PA adopted comprehensive telehealth law in 2022. Audio-only parity is included."
    },
    "OH": {
        "name": "Ohio",
        "parity_law": True,
        "parity_details": "OH Revised Code 3901.73 requires telehealth parity for commercial payers. HB 122 expanded telehealth access.",
        "medicaid_telehealth": "Comprehensive",
        "medicaid_details": "Ohio Medicaid covers video, audio-only, and store-and-forward. Behavioral health audio-only is permanently allowed.",
        "consent_required": "Verbal consent required and documented",
        "prescribing_rules": "Telehealth prescribing follows federal rules. OH Medical Board has telemedicine standards under OAC 4731-11-09.",
        "eligible_providers": "OH licensed providers; out-of-state with Ohio license or compact license",
        "eligible_modalities": ["video", "audio-only", "store-and-forward", "remote_patient_monitoring"],
        "pos_codes": {"02": "Telehealth (non-patient home)", "10": "Telehealth (patient home)"},
        "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"},
        "notes": "OH permanently adopted many PHE telehealth flexibilities. Good audio-only coverage."
    },
    "GA": {
        "name": "Georgia",
        "parity_law": True,
        "parity_details": "GA Code 33-24-56.4 requires commercial payer telehealth parity. SB 115 (2022) expanded telehealth access.",
        "medicaid_telehealth": "Moderate",
        "medicaid_details": "GA Medicaid covers video telehealth. Audio-only for behavioral health. Store-and-forward limited.",
        "consent_required": "Consent required; verbal acceptable with documentation",
        "prescribing_rules": "Telehealth prescribing allowed. GA Composite Medical Board Rule 360-3-.07 governs telemedicine practice.",
        "eligible_providers": "GA licensed providers",
        "eligible_modalities": ["video", "audio-only"],
        "pos_codes": {"02": "Telehealth (non-patient home)", "10": "Telehealth (patient home)"},
        "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"},
        "notes": "GA telehealth law is developing. Audio-only primarily for behavioral health."
    },
    "AZ": {
        "name": "Arizona",
        "parity_law": True,
        "parity_details": "AZ Rev. Stat. 20-672 requires telehealth parity. HB 2452 (2022) made audio-only parity permanent.",
        "medicaid_telehealth": "Comprehensive",
        "medicaid_details": "AHCCCS (AZ Medicaid) covers video, audio-only, and store-and-forward broadly. Remote patient monitoring covered.",
        "consent_required": "Informed consent required; verbal acceptable",
        "prescribing_rules": "AZ allows telehealth prescribing per A.R.S. 36-3603. Controlled substances follow federal telehealth rules.",
        "eligible_providers": "AZ licensed providers; out-of-state via AzHHA or compact",
        "eligible_modalities": ["video", "audio-only", "store-and-forward", "remote_patient_monitoring"],
        "pos_codes": {"02": "Telehealth (non-patient home)", "10": "Telehealth (patient home)"},
        "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"},
        "notes": "AZ is very telehealth-friendly. AHCCCS has broad telehealth coverage."
    },
    "WA": {
        "name": "Washington",
        "parity_law": True,
        "parity_details": "WA RCW 48.43.735 requires telehealth parity. HB 1196 (2023) expanded telehealth and audio-only coverage.",
        "medicaid_telehealth": "Comprehensive",
        "medicaid_details": "WA Apple Health (Medicaid) covers video, audio-only, and store-and-forward. Broad telehealth coverage.",
        "consent_required": "Informed consent required; verbal acceptable with documentation",
        "prescribing_rules": "WA allows telehealth prescribing per RCW 70.41.350. Controlled substances follow federal DEA rules.",
        "eligible_providers": "WA licensed providers",
        "eligible_modalities": ["video", "audio-only", "store-and-forward", "remote_patient_monitoring"],
        "pos_codes": {"02": "Telehealth (non-patient home)", "10": "Telehealth (patient home)"},
        "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"},
        "notes": "WA strong telehealth law. Audio-only permanently covered for many services."
    },
    # Remaining 40 states (abbreviated entries)
    "AL": {"name": "Alabama", "parity_law": True, "medicaid_telehealth": "Moderate", "eligible_modalities": ["video", "audio-only"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "AL parity law effective 2021. Audio-only limited."},
    "AK": {"name": "Alaska", "parity_law": True, "medicaid_telehealth": "Comprehensive", "eligible_modalities": ["video", "audio-only", "store-and-forward"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "AK strong telehealth due to rural geography. Broad coverage."},
    "AR": {"name": "Arkansas", "parity_law": True, "medicaid_telehealth": "Moderate", "eligible_modalities": ["video", "audio-only"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "AR parity law in effect. Audio-only for behavioral health."},
    "CO": {"name": "Colorado", "parity_law": True, "medicaid_telehealth": "Comprehensive", "eligible_modalities": ["video", "audio-only", "store-and-forward", "remote_patient_monitoring"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "CO comprehensive telehealth law. Broad modalities covered."},
    "CT": {"name": "Connecticut", "parity_law": True, "medicaid_telehealth": "Comprehensive", "eligible_modalities": ["video", "audio-only"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "CT telehealth parity established. Audio-only covered."},
    "DE": {"name": "Delaware", "parity_law": True, "medicaid_telehealth": "Moderate", "eligible_modalities": ["video", "audio-only"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "DE parity law effective 2022. Moderate coverage."},
    "DC": {"name": "District of Columbia", "parity_law": True, "medicaid_telehealth": "Comprehensive", "eligible_modalities": ["video", "audio-only"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "DC has robust telehealth parity law."},
    "HI": {"name": "Hawaii", "parity_law": True, "medicaid_telehealth": "Comprehensive", "eligible_modalities": ["video", "audio-only", "store-and-forward"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "HI broad telehealth due to geography. Store-and-forward covered."},
    "ID": {"name": "Idaho", "parity_law": True, "medicaid_telehealth": "Moderate", "eligible_modalities": ["video", "audio-only"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "ID parity law. Audio-only limited."},
    "IN": {"name": "Indiana", "parity_law": True, "medicaid_telehealth": "Comprehensive", "eligible_modalities": ["video", "audio-only", "store-and-forward"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "IN expanded telehealth permanently post-PHE."},
    "IA": {"name": "Iowa", "parity_law": True, "medicaid_telehealth": "Moderate", "eligible_modalities": ["video", "audio-only"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "IA telehealth parity. Audio-only for behavioral health."},
    "KS": {"name": "Kansas", "parity_law": True, "medicaid_telehealth": "Moderate", "eligible_modalities": ["video", "audio-only"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "KS parity law. Some limitations on audio-only."},
    "KY": {"name": "Kentucky", "parity_law": True, "medicaid_telehealth": "Comprehensive", "eligible_modalities": ["video", "audio-only", "store-and-forward"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "KY expanded telehealth. Broad modalities."},
    "LA": {"name": "Louisiana", "parity_law": True, "medicaid_telehealth": "Moderate", "eligible_modalities": ["video", "audio-only"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "LA parity law. Audio-only for established patients."},
    "ME": {"name": "Maine", "parity_law": True, "medicaid_telehealth": "Comprehensive", "eligible_modalities": ["video", "audio-only", "store-and-forward"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "ME broad telehealth coverage. Rural access priority."},
    "MD": {"name": "Maryland", "parity_law": True, "medicaid_telehealth": "Comprehensive", "eligible_modalities": ["video", "audio-only"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "MD strong telehealth law. Audio-only covered."},
    "MA": {"name": "Massachusetts", "parity_law": True, "medicaid_telehealth": "Comprehensive", "eligible_modalities": ["video", "audio-only", "store-and-forward"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "MA comprehensive telehealth. Broad modalities."},
    "MI": {"name": "Michigan", "parity_law": True, "medicaid_telehealth": "Comprehensive", "eligible_modalities": ["video", "audio-only", "store-and-forward"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "MI expanded telehealth permanently. Audio-only covered."},
    "MN": {"name": "Minnesota", "parity_law": True, "medicaid_telehealth": "Comprehensive", "eligible_modalities": ["video", "audio-only", "store-and-forward", "remote_patient_monitoring"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "MN very telehealth-friendly. All modalities covered."},
    "MS": {"name": "Mississippi", "parity_law": False, "medicaid_telehealth": "Limited", "eligible_modalities": ["video"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "MS has limited telehealth law. Video only for most services. No parity statute."},
    "MO": {"name": "Missouri", "parity_law": True, "medicaid_telehealth": "Moderate", "eligible_modalities": ["video", "audio-only"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "MO parity law. Audio-only for behavioral health."},
    "MT": {"name": "Montana", "parity_law": True, "medicaid_telehealth": "Comprehensive", "eligible_modalities": ["video", "audio-only", "store-and-forward"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "MT broad telehealth due to rural areas."},
    "NE": {"name": "Nebraska", "parity_law": True, "medicaid_telehealth": "Moderate", "eligible_modalities": ["video", "audio-only"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "NE parity law. Moderate coverage."},
    "NV": {"name": "Nevada", "parity_law": True, "medicaid_telehealth": "Comprehensive", "eligible_modalities": ["video", "audio-only", "store-and-forward"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "NV comprehensive telehealth law. All modalities."},
    "NH": {"name": "New Hampshire", "parity_law": True, "medicaid_telehealth": "Moderate", "eligible_modalities": ["video", "audio-only"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "NH parity law. Audio-only for established patients."},
    "NJ": {"name": "New Jersey", "parity_law": True, "medicaid_telehealth": "Comprehensive", "eligible_modalities": ["video", "audio-only", "store-and-forward"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "NJ robust telehealth law. Broad modalities covered."},
    "NM": {"name": "New Mexico", "parity_law": True, "medicaid_telehealth": "Comprehensive", "eligible_modalities": ["video", "audio-only", "store-and-forward", "remote_patient_monitoring"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "NM very telehealth-friendly. All modalities."},
    "NC": {"name": "North Carolina", "parity_law": True, "medicaid_telehealth": "Moderate", "eligible_modalities": ["video", "audio-only"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "NC expanded telehealth post-PHE. Audio-only limited."},
    "ND": {"name": "North Dakota", "parity_law": True, "medicaid_telehealth": "Moderate", "eligible_modalities": ["video", "audio-only"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "ND parity law. Rural telehealth prioritized."},
    "OK": {"name": "Oklahoma", "parity_law": True, "medicaid_telehealth": "Moderate", "eligible_modalities": ["video", "audio-only"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "OK parity law. Audio-only for behavioral health."},
    "OR": {"name": "Oregon", "parity_law": True, "medicaid_telehealth": "Comprehensive", "eligible_modalities": ["video", "audio-only", "store-and-forward", "remote_patient_monitoring"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "OR very comprehensive telehealth law. All modalities."},
    "RI": {"name": "Rhode Island", "parity_law": True, "medicaid_telehealth": "Comprehensive", "eligible_modalities": ["video", "audio-only", "store-and-forward"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "RI comprehensive telehealth. Broad coverage."},
    "SC": {"name": "South Carolina", "parity_law": True, "medicaid_telehealth": "Moderate", "eligible_modalities": ["video", "audio-only"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "SC parity law. Moderate telehealth coverage."},
    "SD": {"name": "South Dakota", "parity_law": True, "medicaid_telehealth": "Moderate", "eligible_modalities": ["video", "audio-only"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "SD parity law. Audio-only limited."},
    "TN": {"name": "Tennessee", "parity_law": True, "medicaid_telehealth": "Moderate", "eligible_modalities": ["video", "audio-only"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "TN parity law. Audio-only for behavioral health."},
    "UT": {"name": "Utah", "parity_law": True, "medicaid_telehealth": "Comprehensive", "eligible_modalities": ["video", "audio-only", "store-and-forward"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "UT broad telehealth. Store-and-forward covered."},
    "VT": {"name": "Vermont", "parity_law": True, "medicaid_telehealth": "Comprehensive", "eligible_modalities": ["video", "audio-only", "store-and-forward"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "VT comprehensive telehealth. Rural access focus."},
    "VA": {"name": "Virginia", "parity_law": True, "medicaid_telehealth": "Comprehensive", "eligible_modalities": ["video", "audio-only", "store-and-forward"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "VA comprehensive telehealth law. All modalities."},
    "WV": {"name": "West Virginia", "parity_law": True, "medicaid_telehealth": "Moderate", "eligible_modalities": ["video", "audio-only"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "WV parity law. Rural telehealth prioritized."},
    "WI": {"name": "Wisconsin", "parity_law": True, "medicaid_telehealth": "Comprehensive", "eligible_modalities": ["video", "audio-only", "store-and-forward"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "WI comprehensive telehealth. Broad modalities."},
    "WY": {"name": "Wyoming", "parity_law": True, "medicaid_telehealth": "Moderate", "eligible_modalities": ["video", "audio-only"], "modifiers": {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}, "pos_codes": {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}, "notes": "WY parity law. Rural access focus."},
}

# Medicare telehealth rules
MEDICARE_TELEHEALTH_RULES: Dict[str, Any] = {
    "pos_02": {
        "code": "02",
        "description": "Telehealth Provided Other than in Patient's Home",
        "billing_rules": "Use POS 02 when patient is located at a telehealth originating site (clinic, hospital, FQHC, RHC) other than their home",
        "payment": "Reimbursed at non-facility rate (higher than facility rate)",
        "modifier_required": "Append modifier 95 or GT to telehealth CPT codes"
    },
    "pos_10": {
        "code": "10",
        "description": "Telehealth Provided in Patient's Home",
        "billing_rules": "Use POS 10 when patient is located at home for telehealth visit",
        "payment": "Reimbursed at non-facility rate",
        "modifier_required": "Append modifier 95 or GT to telehealth CPT codes"
    },
    "eligible_services": [
        "E/M services (99202-99215, 99221-99223, 99231-99233)",
        "Psychiatric diagnostic evaluation (90791, 90792)",
        "Psychotherapy (90832, 90834, 90837, 90839, 90840, 90845, 90846, 90847, 90853)",
        "End-stage renal disease services (90960, 90962, 90966)",
        "Neurobehavioral status exam (96116)",
        "Smoking cessation counseling (99406, 99407)",
        "Alcohol/substance abuse counseling (99078)",
        "Medical nutrition therapy (97802, 97803, 97804)",
        "Diabetes self-management training (98053)",
        "Remote patient monitoring (99453, 99454, 99457, 99458)",
        "Chronic care management (99490, 99491, 99439)",
        "Behavioral health integration (99492, 99493, 99494)",
    ],
    "originating_sites": [
        "Office (11)",
        "Hospital outpatient (19/22)",
        "Critical access hospital (21)",
        "Rural health clinic (72)",
        "FQHC (71)",
        "SNF (31)",
        "Renal dialysis center (65)",
        "Patient home (10) - expanded post-PHE",
        "Any location (02) - expanded post-PHE",
    ],
    "geographic_restrictions": "Removed for most services post-PHE. Previously limited to rural/HPSA areas.",
    "audio_only": "Audio-only telephone E/M services (99441-99443) were added during PHE and extended. Check current CMS guidance.",
    "notes": "Medicare telehealth flexibilities expanded significantly during PHE. Many made permanent via Consolidated Appropriations Act. Verify current CMS guidance."
}

# Modifier definitions
MODIFIER_RULES: Dict[str, Dict[str, Any]] = {
    "GT": {
        "description": "Via interactive audio and video telecommunications systems",
        "usage": "Append to CPT code when service rendered via real-time interactive audio/video telecommunication",
        "pos_codes": ["02", "10"],
        "payer_usage": {
            "medicare": "Accepted. Use with POS 02 or 10.",
            "medicaid": "Varies by state. Most accept.",
            "commercial": "Varies. Check payer policy."
        }
    },
    "95": {
        "description": "Synchronous telemedicine service rendered via real-time interactive audio and video telecommunications system",
        "usage": "CMS-preferred modifier for Medicare telehealth claims",
        "pos_codes": ["02", "10"],
        "payer_usage": {
            "medicare": "CMS preferred modifier for synchronous telehealth",
            "medicaid": "Varies by state. Many accept.",
            "commercial": "Varies. Some prefer GT."
        }
    },
    "GQ": {
        "description": "Via asynchronous telecommunications system (store-and-forward)",
        "usage": "Use for store-and-forward telehealth services",
        "pos_codes": ["02"],
        "payer_usage": {
            "medicare": "Limited to specific services/regions (e.g., Alaska, Hawaii federal telehealth demonstrations)",
            "medicaid": "Some states accept for store-and-forward",
            "commercial": "Limited acceptance"
        }
    },
    "93": {
        "description": "Synonym of modifier 95 (synchronous telemedicine)",
        "usage": "Some payers prefer 93 over 95. Same meaning.",
        "pos_codes": ["02", "10"],
        "payer_usage": {
            "medicare": "Not standard Medicare modifier",
            "medicaid": "Some states use",
            "commercial": "Some commercial payers use 93 instead of 95"
        }
    },
    "FQ": {
        "description": "Service furnished using audio-only communication technology",
        "usage": "Append for audio-only telehealth visits when allowed by payer",
        "pos_codes": ["02", "10", "11"],
        "payer_usage": {
            "medicare": "Accepted for audio-only E/M per CMS guidance",
            "medicaid": "Varies by state",
            "commercial": "Varies"
        }
    },
}

# Payer-specific telehealth rules
PAYER_TELEHEALTH_RULES: Dict[str, Dict[str, Any]] = {
    "medicare": {
        "coverage": "Comprehensive",
        "pos_accepted": ["02", "10"],
        "modifiers_accepted": ["95", "GT", "GQ", "FQ"],
        "parity": True,
        "audio_only": "Covered for E/M services per CMS guidance. Use modifier FQ.",
        "notes": "Medicare telehealth rules follow CMS Internet-Only Manuals (IOM). Pub 100-04, Chapter 12."
    },
    "medicaid": {
        "coverage": "Varies by state",
        "pos_accepted": ["02", "10"],
        "modifiers_accepted": ["95", "GT"],
        "parity": "Varies by state",
        "audio_only": "Varies by state. Most cover for behavioral health.",
        "notes": "Check state-specific Medicaid telehealth rules."
    },
    "uhc": {
        "coverage": "Comprehensive",
        "pos_accepted": ["02", "10"],
        "modifiers_accepted": ["95", "GT", "93"],
        "parity": True,
        "audio_only": "Covered for established patients. Check UHC policy for specific codes.",
        "notes": "UHC telehealth policy via UnitedHealthcare Provider Portal."
    },
    "aetna": {
        "coverage": "Comprehensive",
        "pos_accepted": ["02", "10"],
        "modifiers_accepted": ["95", "GT"],
        "parity": True,
        "audio_only": "Covered for behavioral health and established patients.",
        "notes": "Aetna telehealth coverage per Clinical Policy Bulletin."
    },
    "cigna": {
        "coverage": "Comprehensive",
        "pos_accepted": ["02", "10"],
        "modifiers_accepted": ["95", "GT", "93"],
        "parity": True,
        "audio_only": "Covered for behavioral health.",
        "notes": "Cigna telehealth policy via provider portal."
    },
    "bcbs": {
        "coverage": "Varies by plan",
        "pos_accepted": ["02", "10"],
        "modifiers_accepted": ["95", "GT"],
        "parity": "Varies by plan",
        "audio_only": "Varies by plan. Many cover for behavioral health.",
        "notes": "BCBS telehealth varies significantly by plan and state."
    },
    "humana": {
        "coverage": "Comprehensive",
        "pos_accepted": ["02", "10"],
        "modifiers_accepted": ["95", "GT"],
        "parity": True,
        "audio_only": "Covered for established patients and behavioral health.",
        "notes": "Humana telehealth policy via Availity portal."
    },
}


@skill(name="telehealth_rules", category="healthcare")
class TelehealthRulesSkill(AetheraSkill):
    """
    Telehealth billing rules by state and payer.
    """

    @property
    def name(self) -> str:
        return "telehealth_rules"

    @property
    def description(self) -> str:
        return "Check telehealth billing rules by state, verify payer coverage, and get billing requirements including POS codes and modifiers."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["check_state_rules", "verify_payer_coverage", "get_billing_requirements", "medicare_rules"],
                    "description": "Action: check_state_rules (state telehealth law), verify_payer_coverage (payer telehealth policy), get_billing_requirements (POS/modifier for a service), medicare_rules (Medicare telehealth details)"
                },
                "state": {
                    "type": "string",
                    "description": "Two-letter state abbreviation (e.g., CA, TX, NY)"
                },
                "payer": {
                    "type": "string",
                    "description": "Payer name (e.g., medicare, medicaid, uhc, aetna, cigna, bcbs, humana)"
                },
                "modality": {
                    "type": "string",
                    "enum": ["video", "audio-only", "store-and-forward", "remote_patient_monitoring"],
                    "description": "Telehealth modality to check"
                },
                "cpt_code": {
                    "type": "string",
                    "description": "CPT code to check billing requirements for"
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
            {"input": {"action": "check_state_rules", "state": "CA"}},
            {"input": {"action": "verify_payer_coverage", "payer": "medicare", "modality": "audio-only"}},
            {"input": {"action": "get_billing_requirements", "state": "TX", "payer": "uhc", "cpt_code": "99213"}},
            {"input": {"action": "medicare_rules"}},
        ]

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "")
        state = kwargs.get("state", "").upper()
        payer = kwargs.get("payer", "").lower()
        modality = kwargs.get("modality", "")
        cpt_code = kwargs.get("cpt_code", "")

        try:
            if action == "check_state_rules":
                if not state:
                    return SkillResult(success=False, error="State code is required for check_state_rules")
                result = self._check_state_rules(state, modality)
                return SkillResult(success=True, data=result)

            elif action == "verify_payer_coverage":
                if not payer:
                    return SkillResult(success=False, error="Payer name is required for verify_payer_coverage")
                result = self._verify_payer_coverage(payer, modality, state)
                return SkillResult(success=True, data=result)

            elif action == "get_billing_requirements":
                result = self._get_billing_requirements(state, payer, cpt_code, modality)
                return SkillResult(success=True, data=result)

            elif action == "medicare_rules":
                result = self._get_medicare_rules(modality, cpt_code)
                return SkillResult(success=True, data=result)

            else:
                return SkillResult(success=False, error=f"Unknown action: {action}")

        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _check_state_rules(self, state: str, modality: str) -> Dict[str, Any]:
        """Check telehealth rules for a specific state."""
        state_data = STATE_TELEHEALTH_RULES.get(state)
        if not state_data:
            return {
                "state": state,
                "found": False,
                "message": f"State {state} not found. Use two-letter abbreviation (e.g., CA, TX)."
            }

        result = {
            "state": state,
            "name": state_data.get("name", state),
            "parity_law": state_data.get("parity_law", False),
            "parity_details": state_data.get("parity_details", "See state regulations for details"),
            "medicaid_telehealth": state_data.get("medicaid_telehealth", "Unknown"),
            "medicaid_details": state_data.get("medicaid_details", ""),
            "consent_required": state_data.get("consent_required", "Check state requirements"),
            "prescribing_rules": state_data.get("prescribing_rules", "Check state and federal prescribing rules"),
            "eligible_providers": state_data.get("eligible_providers", "State licensed providers"),
            "eligible_modalities": state_data.get("eligible_modalities", []),
            "pos_codes": state_data.get("pos_codes", {"02": "Telehealth non-patient home", "10": "Telehealth patient home"}),
            "modifiers": state_data.get("modifiers", {"GT": "Via interactive audio/video", "95": "Synchronous telemedicine"}),
            "notes": state_data.get("notes", ""),
        }

        if modality:
            eligible = state_data.get("eligible_modalities", [])
            result["modality_check"] = {
                "modality": modality,
                "covered": modality in eligible,
                "notes": f"Modality '{modality}' {'is' if modality in eligible else 'is not'} listed as eligible in {state_data.get('name', state)}"
            }

        return result

    def _verify_payer_coverage(self, payer: str, modality: str, state: str) -> Dict[str, Any]:
        """Verify payer telehealth coverage."""
        payer_data = PAYER_TELEHEALTH_RULES.get(payer)
        if not payer_data:
            # Try common aliases
            aliases = {"united": "uhc", "unitedhealthcare": "uhc", "blue cross": "bcbs", "blue shield": "bcbs"}
            payer = aliases.get(payer, payer)
            payer_data = PAYER_TELEHEALTH_RULES.get(payer)

        if not payer_data:
            return {
                "payer": payer,
                "found": False,
                "message": f"Payer {payer} not found. Supported: {', '.join(PAYER_TELEHEALTH_RULES.keys())}"
            }

        result = {
            "payer": payer,
            "coverage": payer_data.get("coverage", "Unknown"),
            "pos_accepted": payer_data.get("pos_accepted", []),
            "modifiers_accepted": payer_data.get("modifiers_accepted", []),
            "parity": payer_data.get("parity", "Unknown"),
            "audio_only": payer_data.get("audio_only", ""),
            "notes": payer_data.get("notes", ""),
        }

        if modality:
            if modality == "audio-only":
                result["modality_coverage"] = {
                    "modality": modality,
                    "covered": True,
                    "details": payer_data.get("audio_only", "Check payer policy")
                }
            elif modality == "store-and-forward":
                result["modality_coverage"] = {
                    "modality": modality,
                    "covered": "GQ" in payer_data.get("modifiers_accepted", []),
                    "details": "Store-and-forward requires modifier GQ in most cases"
                }
            elif modality == "video":
                result["modality_coverage"] = {
                    "modality": modality,
                    "covered": True,
                    "details": "Synchronous video telehealth is the standard telehealth modality"
                }
            elif modality == "remote_patient_monitoring":
                result["modality_coverage"] = {
                    "modality": modality,
                    "covered": payer_data.get("coverage") == "Comprehensive",
                    "details": "RPM coverage varies by payer. Check specific CPT codes (99453, 99454, 99457, 99458)."
                }

        if state:
            state_data = STATE_TELEHEALTH_RULES.get(state.upper())
            if state_data:
                result["state_specific"] = {
                    "state": state.upper(),
                    "state_parity": state_data.get("parity_law", False),
                    "state_modalities": state_data.get("eligible_modalities", []),
                    "notes": state_data.get("notes", "")
                }

        return result

    def _get_billing_requirements(self, state: str, payer: str, cpt_code: str, modality: str) -> Dict[str, Any]:
        """Get billing requirements for a telehealth service."""
        result: Dict[str, Any] = {
            "billing_requirements": {},
            "pos_codes": {},
            "modifiers": {},
            "recommendations": []
        }

        # Determine recommended POS
        if modality == "audio-only" or modality == "video":
            result["pos_codes"] = {
                "02": {
                    "description": "Telehealth Provided Other than in Patient's Home",
                    "when_to_use": "Patient is at an originating site (clinic, office, facility) other than home"
                },
                "10": {
                    "description": "Telehealth Provided in Patient's Home",
                    "when_to_use": "Patient is at home for the telehealth visit"
                }
            }
        else:
            result["pos_codes"] = {
                "02": "Telehealth Provided Other than in Patient's Home",
                "10": "Telehealth Provided in Patient's Home"
            }

        # Determine recommended modifiers
        payer_lower = payer.lower() if payer else ""
        if payer_lower == "medicare":
            result["modifiers"] = {
                "95": "CMS preferred for synchronous telehealth",
                "GT": "Alternative for synchronous telehealth (some payers prefer)",
                "FQ": "For audio-only telehealth services"
            }
        elif payer_lower in ("uhc", "cigna"):
            result["modifiers"] = {
                "95": "Synchronous telemedicine",
                "93": "Alternative synchronous modifier (some commercial payers prefer)",
                "GT": "Via interactive audio/video"
            }
        else:
            result["modifiers"] = {
                "95": "Synchronous telemedicine (most widely accepted)",
                "GT": "Via interactive audio/video (alternative)"
            }

        # State-specific requirements
        if state:
            state_data = STATE_TELEHEALTH_RULES.get(state.upper())
            if state_data:
                result["state_requirements"] = {
                    "state": state.upper(),
                    "consent_required": state_data.get("consent_required", "Check state requirements"),
                    "eligible_modalities": state_data.get("eligible_modalities", []),
                    "parity_law": state_data.get("parity_law", False),
                    "prescribing_rules": state_data.get("prescribing_rules", ""),
                    "state_modifiers": state_data.get("modifiers", {})
                }

        # CPT-specific guidance
        if cpt_code:
            result["cpt_code"] = cpt_code
            is_em = cpt_code.startswith("992")
            is_psych = cpt_code.startswith("908") or cpt_code in ("90791", "90792")
            if is_em:
                result["recommendations"].append("E/M telehealth: Ensure documentation supports level of service. Time can include telehealth time.")
            if is_psych:
                result["recommendations"].append("Behavioral health telehealth: Most payers cover. Audio-only commonly accepted for established patients.")

        result["recommendations"].extend([
            "Always verify current payer policy before billing telehealth services",
            "Document the telehealth modality used (video vs audio-only) in the medical record",
            "Ensure informed consent for telehealth is documented per state requirements"
        ])

        return result

    def _get_medicare_rules(self, modality: str, cpt_code: str) -> Dict[str, Any]:
        """Get Medicare telehealth rules."""
        result = {
            "medicare_telehealth": MEDICARE_TELEHEALTH_RULES.copy(),
            "modifier_rules": {k: v for k, v in MODIFIER_RULES.items() if k in ("95", "GT", "GQ", "FQ")}
        }

        if modality:
            if modality == "audio-only":
                result["modality_guidance"] = {
                    "modality": "audio-only",
                    "medicare_coverage": "Covered for specific E/M and behavioral health codes",
                    "pos": "Use POS 02 or 10 with modifier FQ (or 99441-99443 for telephone E/M)",
                    "notes": "Audio-only flexibilities extended post-PHE. Verify current CMS guidance."
                }
            elif modality == "store-and-forward":
                result["modality_guidance"] = {
                    "modality": "store-and-forward",
                    "medicare_coverage": "Limited. Primarily for federal telehealth demonstrations (AK, HI)",
                    "modifier": "GQ",
                    "notes": "Store-and-forward not widely covered by Medicare outside demonstrations."
                }
            elif modality == "video":
                result["modality_guidance"] = {
                    "modality": "video (synchronous)",
                    "medicare_coverage": "Broadly covered for eligible telehealth services",
                    "modifier": "95 (preferred) or GT",
                    "pos": "02 or 10",
                    "notes": "Standard Medicare telehealth modality."
                }

        if cpt_code:
            eligible = MEDICARE_TELEHEALTH_RULES.get("eligible_services", [])
            is_likely_eligible = any(cpt_code in svc or cpt_code[:3] in svc for svc in eligible)
            result["cpt_code_check"] = {
                "cpt_code": cpt_code,
                "likely_eligible": is_likely_eligible,
                "note": "Verify on CMS telehealth eligible services list. List is updated periodically."
            }

        return result