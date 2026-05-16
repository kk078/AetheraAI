"""
Lab normal ranges reference.

Common laboratory test reference ranges and clinical significance
for interpreting lab results.
"""

import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://medlineplus.gov/ency/article/003617.htm"
DEST_DIR = DATA_ROOT / "healthcare" / "clinical" / "lab_reference"
MODULE_NAME = "knowledge_bases.healthcare.clinical.lab_reference"

LAB_RANGES = [
    {"test": "Complete Blood Count (CBC)", "components": [
        {"name": "WBC", "range": "4,500-11,000 cells/mcL", "unit": "cells/mcL", "low_indicates": "Leukopenia, infection risk", "high_indicates": "Infection, inflammation, leukemia"},
        {"name": "RBC", "range": "Male: 4.3-5.9 million/mcL; Female: 3.5-5.5 million/mcL", "unit": "million/mcL", "low_indicates": "Anemia", "high_indicates": "Polycythemia"},
        {"name": "Hemoglobin", "range": "Male: 13.5-17.5 g/dL; Female: 12.0-16.0 g/dL", "unit": "g/dL", "low_indicates": "Anemia", "high_indicates": "Polycythemia, dehydration"},
        {"name": "Hematocrit", "range": "Male: 41-53%; Female: 36-46%", "unit": "%", "low_indicates": "Anemia", "high_indicates": "Polycythemia, dehydration"},
        {"name": "Platelet Count", "range": "150,000-400,000/mcL", "unit": "/mcL", "low_indicates": "Thrombocytopenia, bleeding risk", "high_indicates": "Thrombocytosis, clotting risk"},
        {"name": "MCV", "range": "80-100 fL", "unit": "fL", "low_indicates": "Microcytic anemia (iron deficiency)", "high_indicates": "Macrocytic anemia (B12/folate)"},
        {"name": "MCH", "range": "27-31 pg", "unit": "pg", "low_indicates": "Hypochromic anemia", "high_indicates": "Macrocytic anemia"},
        {"name": "MCHC", "range": "32-36 g/dL", "unit": "g/dL", "low_indicates": "Hypochromic anemia", "high_indicates": "Spherocytosis"},
    ]},
    {"test": "Comprehensive Metabolic Panel (CMP)", "components": [
        {"name": "Glucose (fasting)", "range": "70-100 mg/dL", "unit": "mg/dL", "low_indicates": "Hypoglycemia", "high_indicates": "Diabetes, prediabetes"},
        {"name": "BUN", "range": "7-20 mg/dL", "unit": "mg/dL", "low_indicates": "Liver disease, malnutrition", "high_indicates": "Kidney disease, dehydration"},
        {"name": "Creatinine", "range": "0.6-1.2 mg/dL", "unit": "mg/dL", "low_indicates": "Low muscle mass", "high_indicates": "Kidney disease"},
        {"name": "eGFR", "range": ">60 mL/min/1.73m2", "unit": "mL/min/1.73m2", "low_indicates": "Kidney disease staging", "high_indicates": "N/A"},
        {"name": "Sodium", "range": "135-145 mEq/L", "unit": "mEq/L", "low_indicates": "Hyponatremia", "high_indicates": "Hypernatremia"},
        {"name": "Potassium", "range": "3.5-5.0 mEq/L", "unit": "mEq/L", "low_indicates": "Hypokalemia, muscle weakness", "high_indicates": "Hyperkalemia, arrhythmia risk"},
        {"name": "Chloride", "range": "98-106 mEq/L", "unit": "mEq/L", "low_indicates": "Hypochloremia", "high_indicates": "Hyperchloremia"},
        {"name": "CO2/Bicarbonate", "range": "23-29 mEq/L", "unit": "mEq/L", "low_indicates": "Metabolic acidosis", "high_indicates": "Metabolic alkalosis"},
        {"name": "Calcium", "range": "8.5-10.5 mg/dL", "unit": "mg/dL", "low_indicates": "Hypocalcemia, tetany", "high_indicates": "Hypercalcemia, kidney stones"},
        {"name": "Total Protein", "range": "6.0-8.3 g/dL", "unit": "g/dL", "low_indicates": "Malnutrition, liver disease", "high_indicates": "Multiple myeloma"},
        {"name": "Albumin", "range": "3.5-5.0 g/dL", "unit": "g/dL", "low_indicates": "Liver disease, malnutrition", "high_indicates": "Dehydration"},
        {"name": "ALT", "range": "4-36 U/L", "unit": "U/L", "low_indicates": "N/A", "high_indicates": "Liver damage"},
        {"name": "AST", "range": "0-40 U/L", "unit": "U/L", "low_indicates": "N/A", "high_indicates": "Liver damage, muscle injury"},
        {"name": "Alkaline Phosphatase", "range": "44-147 U/L", "unit": "U/L", "low_indicates": "N/A", "high_indicates": "Bone disease, bile duct obstruction"},
        {"name": "Total Bilirubin", "range": "0.1-1.2 mg/dL", "unit": "mg/dL", "low_indicates": "N/A", "high_indicates": "Jaundice, liver disease"},
    ]},
    {"test": "Lipid Panel", "components": [
        {"name": "Total Cholesterol", "range": "<200 mg/dL (desirable)", "unit": "mg/dL", "low_indicates": "N/A", "high_indicates": "Hypercholesterolemia, cardiovascular risk"},
        {"name": "HDL Cholesterol", "range": "Male: >40 mg/dL; Female: >50 mg/dL", "unit": "mg/dL", "low_indicates": "Increased cardiovascular risk", "high_indicates": "Protective"},
        {"name": "LDL Cholesterol", "range": "<100 mg/dL (optimal)", "unit": "mg/dL", "low_indicates": "N/A", "high_indicates": "Atherosclerosis risk"},
        {"name": "Triglycerides", "range": "<150 mg/dL (normal)", "unit": "mg/dL", "low_indicates": "N/A", "high_indicates": "Pancreatitis risk, metabolic syndrome"},
    ]},
    {"test": "Thyroid Panel", "components": [
        {"name": "TSH", "range": "0.4-4.0 mIU/L", "unit": "mIU/L", "low_indicates": "Hyperthyroidism", "high_indicates": "Hypothyroidism"},
        {"name": "Free T4", "range": "0.8-1.8 ng/dL", "unit": "ng/dL", "low_indicates": "Hypothyroidism", "high_indicates": "Hyperthyroidism"},
        {"name": "Free T3", "range": "2.3-4.2 pg/mL", "unit": "pg/mL", "low_indicates": "Hypothyroidism", "high_indicates": "Hyperthyroidism"},
    ]},
    {"test": "Coagulation Studies", "components": [
        {"name": "PT/INR", "range": "PT: 11-13.5 sec; INR: 0.8-1.1", "unit": "sec / ratio", "low_indicates": "Thrombotic risk", "high_indicates": "Bleeding risk, anticoagulation effect"},
        {"name": "aPTT", "range": "25-35 sec", "unit": "sec", "low_indicates": "Thrombotic risk", "high_indicates": "Bleeding risk, heparin effect"},
    ]},
    {"test": "Cardiac Markers", "components": [
        {"name": "Troponin I", "range": "<0.04 ng/mL", "unit": "ng/mL", "low_indicates": "N/A", "high_indicates": "Myocardial infarction"},
        {"name": "BNP / NT-proBNP", "range": "BNP <100 pg/mL; NT-proBNP <300 pg/mL (age <75)", "unit": "pg/mL", "low_indicates": "N/A", "high_indicates": "Heart failure"},
    ]},
    {"test": "HbA1c", "components": [
        {"name": "Hemoglobin A1c", "range": "<5.7% (normal); 5.7-6.4% (prediabetes); >=6.5% (diabetes)", "unit": "%", "low_indicates": "Hypoglycemia risk", "high_indicates": "Poor diabetes control"},
    ]},
]


async def download(force: bool = False) -> dict:
    """Download lab normal ranges reference."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "lab_reference.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading lab normal ranges reference...")
    save_json(LAB_RANGES, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    total_tests = sum(len(t["components"]) for t in LAB_RANGES)
    return {"files_downloaded": 1, "message": f"Downloaded lab reference ({len(LAB_RANGES)} test groups, {total_tests} components)"}