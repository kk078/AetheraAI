"""
Clinical calculation formulas reference.

Common medical calculation formulas used in clinical decision-making,
dosing, and risk assessment.
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://www.mdcalc.com/"
DEST_DIR = DATA_ROOT / "healthcare" / "clinical" / "medical_calculators"
MODULE_NAME = "knowledge_bases.healthcare.clinical.medical_calculators"

MEDICAL_CALCULATIONS = [
    {"name": "BMI (Body Mass Index)", "formula": "weight(kg) / height(m)^2", "units": "kg/m2", "categories": [{"range": "<18.5", "classification": "Underweight"}, {"range": "18.5-24.9", "classification": "Normal"}, {"range": "25.0-29.9", "classification": "Overweight"}, {"range": ">=30", "classification": "Obese"}]},
    {"name": "eGFR (CKD-EPI 2021)", "formula": "142 * min(Scr/kappa, 1)^alpha * max(Scr/kappa, 1)^(-1.200) * 0.9938^Age * 1.012 (if female)", "notes": " kappa=0.7 (f) or 0.9 (m); alpha=-0.241 (f) or -0.302 (m); race coefficient removed in 2021 update", "stages": [{"range": ">=90", "stage": "G1"}, {"range": "60-89", "stage": "G2"}, {"range": "45-59", "stage": "G3a"}, {"range": "30-44", "stage": "G3b"}, {"range": "15-29", "stage": "G4"}, {"range": "<15", "stage": "G5 (ESRD)"}]},
    {"name": "Corrected Calcium", "formula": "Measured Ca + 0.8 * (4.0 - Albumin)", "units": "mg/dL", "notes": "Corrects total calcium for low albumin; normal range 8.5-10.5 mg/dL"},
    {"name": "Anion Gap", "formula": "Na - (Cl + HCO3)", "units": "mEq/L", "normal_range": "8-12 mEq/L", "notes": "Elevated in metabolic acidosis (MUDPILES: Methanol, Uremia, DKA, Propylene glycol, Isoniazid, Lactic acidosis, Ethylene glycol, Salicylates)"},
    {"name": "FENA (Fractional Excretion of Na)", "formula": "(Urine_Na * Plasma_Cr) / (Plasma_Na * Urine_Cr) * 100", "units": "%", "interpretation": [{"range": "<1%", "meaning": "Pre-renal AKI"}, {"range": ">2%", "meaning": "Intrinsic renal AKI"}]},
    {"name": "CHA2DS2-VASc (AF Stroke Risk)", "components": [{"factor": "CHF/LV dysfunction", "points": 1}, {"factor": "Hypertension", "points": 1}, {"factor": "Age >=75", "points": 2}, {"factor": "Diabetes", "points": 1}, {"factor": "Stroke/TIA/thromboembolism", "points": 2}, {"factor": "Vascular disease", "points": 1}, {"factor": "Age 65-74", "points": 1}, {"factor": "Sex category (female)", "points": 1}], "anticoagulation_threshold": "Score >=2 in men, >=3 in women: oral anticoagulation recommended"},
    {"name": "HAS-BLED (Bleeding Risk)", "components": [{"factor": "Hypertension", "points": 1}, {"factor": "Abnormal renal/liver function", "points": "1-2"}, {"factor": "Stroke", "points": 1}, {"factor": "Bleeding history", "points": 1}, {"factor": "Labile INR", "points": 1}, {"factor": "Elderly (>65)", "points": 1}, {"factor": "Drugs/alcohol", "points": "1-2"}], "high_risk": "Score >=3: high bleeding risk; address correctable risk factors"},
    {"name": "Wells Score (DVT)", "components": [{"factor": "Active cancer", "points": 1}, {"factor": "Paralysis or recent cast", "points": 1}, {"factor": "Bedridden >3 days or surgery <12 weeks", "points": 1}, {"factor": "Localized tenderness", "points": 1}, {"factor": "Swelling of entire leg", "points": 1}, {"factor": "Calf swelling >3cm vs asymptomatic side", "points": 1}, {"factor": "Pitting edema", "points": 1}, {"factor": "Collateral superficial veins", "points": 1}, {"factor": "Alternative diagnosis as likely", "points": "-2"}], "interpretation": "Score <=0: low probability; 1-2: moderate; >=3: high"},
    {"name": "Wells Score (PE)", "components": [{"factor": "DVT symptoms/signs", "points": 3}, {"factor": "PE most likely diagnosis", "points": 3}, {"factor": "Heart rate >100", "points": 1.5}, {"factor": "Immobilization or surgery <4 weeks", "points": 1.5}, {"factor": "Previous DVT/PE", "points": 1.5}, {"factor": "Hemoptysis", "points": 1}, {"factor": "Active cancer", "points": 1}], "interpretation": "Score <=4: PE unlikely (consider D-dimer); >4: PE likely (imaging)"},
    {"name": "Cage Questionnaire (Alcohol)", "components": [{"question": "Cut down", "description": "Have you felt you should cut down?"}, {"question": "Annoyed", "description": "Have people annoyed you by criticizing your drinking?"}, {"question": "Guilty", "description": "Have you felt bad/guilty about drinking?"}, {"question": "Eye-opener", "description": "Have you had a drink first thing in the morning?"}], "interpretation": "Score >=2: suggestive of alcohol problem"},
    {"name": "Columbia Suicide Severity Rating", "components": "Standardized questions to assess suicidal ideation and behavior severity", "clinical_use": "Suicide risk assessment and safety planning"},
    {"name": "Apache II", "formula": "Scoring system based on 12 physiological variables, age, and chronic health", "clinical_use": "ICU mortality prediction; severity of illness classification"},
    {"name": "SOFA Score", "components": [{"system": "Respiration (PaO2/FiO2)"}, {"system": "Coagulation (Platelets)"}, {"system": "Liver (Bilirubin)"}, {"system": "Cardiovascular (MAP/vasopressors)"}, {"system": "CNS (GCS)"}, {"system": "Renal (Creatinine/UOP)"}], "clinical_use": "Organ dysfunction assessment; sepsis-3 criteria (SOFA >=2 indicates organ dysfunction)"},
    {"name": "Creatinine Clearance (Cockcroft-Gault)", "formula": "((140 - Age) * Weight(kg)) / (72 * Serum_Cr) * (0.85 if female)", "units": "mL/min", "clinical_use": "Drug dosing adjustments based on renal function"},
    {"name": "Oxygenation Index (PaO2/FiO2)", "formula": "PaO2(mmHg) / FiO2(fraction)", "interpretation": [{"range": ">400", "classification": "Normal"}, {"range": "300-400", "classification": "Mild ARDS"}, {"range": "200-300", "classification": "Moderate ARDS"}, {"range": "<200", "classification": "Severe ARDS"}]},
]


async def download(force: bool = False) -> dict:
    """Download medical calculator formulas reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "medical_calculators.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading medical calculator formulas reference...")
    save_json(MEDICAL_CALCULATIONS, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": f"Downloaded {len(MEDICAL_CALCULATIONS)} medical calculation formulas"}