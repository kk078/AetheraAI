"""
Aethera AI - Risk Adjuster Skill

Calculate HCC/RAF scores, identify HCC gaps, suggest documentation improvements.
Supports CMS-HCC V24 and V28 models.
"""

from typing import Dict, Any, List, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill


# CMS-HCC V24 Model Mappings
# Structure: HCC code -> {description, conditions (ICD-10 codes that map), hierarchy_parent, weight}
HCC_V24: Dict[str, Dict[str, Any]] = {
    "HCC1": {
        "description": "HIV/AIDS",
        "conditions": ["B20", "B97.35", "R75", "Z21"],
        "hierarchy_parent": None,
        "weight": 0.932,
        "category": "Major"
    },
    "HCC2": {
        "description": "Septicemia, Sepsis, Systemic Inflammatory Response Syndrome (SIRS)",
        "conditions": ["A40.0", "A40.1", "A40.2", "A40.3", "A40.8", "A40.9", "A41.0", "A41.1", "A41.2", "A41.3", "A41.4", "A41.50", "A41.51", "A41.52", "A41.53", "A41.59", "A41.81", "A41.89", "A41.9", "R65.20", "R65.21"],
        "hierarchy_parent": None,
        "weight": 0.716,
        "category": "Major"
    },
    "HCC6": {
        "description": "Opportunistic Infections",
        "conditions": ["B37.7", "B37.81", "B37.89", "B37.9", "B44.0", "B44.1", "B44.2", "B44.7", "B44.81", "B44.89", "B44.9", "B49", "B59"],
        "hierarchy_parent": "HCC1",
        "weight": 0.280,
        "category": "Major"
    },
    "HCC8": {
        "description": "Metastatic Cancer and Acute Leukemia",
        "conditions": ["C77.0", "C77.1", "C77.2", "C77.3", "C77.4", "C77.5", "C78.00", "C78.01", "C78.02", "C78.10", "C78.20", "C78.30", "C78.80", "C78.89", "C79.00", "C79.01", "C79.02", "C79.10", "C79.11", "C79.19", "C79.2", "C79.31", "C79.32", "C79.40", "C79.49", "C79.51", "C79.60", "C79.61", "C79.70", "C79.71", "C79.72", "C79.81", "C79.82", "C79.89", "C79.9", "C7A.0", "C7A.1", "C7A.8", "C80.0", "C80.1", "C80.2", "C91.00", "C91.02", "C91.80", "C91.90", "C92.00", "C92.02", "C92.20", "C92.22", "C92.40", "C92.42", "C92.50", "C92.52", "C92.60", "C92.62", "C92.70", "C92.72", "C92.80", "C92.90", "C93.00", "C93.02", "C93.10", "C93.12", "C93.30", "C93.32", "C93.80", "C93.90", "C94.00", "C94.02", "C94.20", "C94.22", "C94.30", "C94.32", "C94.40", "C94.42", "C94.6", "C94.80", "C94.90", "C95.00", "C95.02", "C95.10", "C95.12", "C95.30", "C95.32", "C95.80", "C95.90"],
        "hierarchy_parent": None,
        "weight": 1.285,
        "category": "Major"
    },
    "HCC9": {
        "description": "Lung and Other Severe Cancers",
        "conditions": ["C34.00", "C34.01", "C34.02", "C34.10", "C34.11", "C34.12", "C34.2", "C34.30", "C34.31", "C34.32", "C34.80", "C34.81", "C34.82", "C34.90", "C34.91", "C34.92", "C37", "C38.1", "C38.2", "C38.3", "C38.4", "C39.0", "C39.8", "C39.9", "C45.0", "C45.1", "C45.7"],
        "hierarchy_parent": "HCC8",
        "weight": 0.632,
        "category": "Major"
    },
    "HCC10": {
        "description": "Lymphoma and Other Cancers",
        "conditions": ["C81.00", "C81.02", "C81.10", "C81.12", "C81.70", "C81.72", "C81.90", "C81.92", "C82.00", "C82.02", "C82.40", "C82.42", "C82.60", "C82.62", "C82.80", "C82.82", "C82.90", "C82.92", "C83.00", "C83.02", "C83.30", "C83.32", "C83.50", "C83.52", "C83.70", "C83.72", "C83.80", "C83.82", "C83.90", "C83.92", "C84.00", "C84.02", "C84.10", "C84.12", "C84.40", "C84.42", "C84.50", "C84.52", "C84.60", "C84.62", "C84.70", "C84.72", "C84.80", "C84.82", "C84.90", "C84.92", "C85.10", "C85.12", "C85.20", "C85.22", "C85.80", "C85.82", "C85.90", "C85.92", "C86.00", "C86.02", "C86.10", "C86.12", "C86.20", "C86.22", "C86.40", "C86.42", "C86.50", "C86.52", "C86.60", "C86.62", "C88.0", "C88.1", "C88.2", "C88.3", "C88.4", "C88.5", "C88.6", "C88.7", "C88.8", "C88.9", "C90.00", "C90.02", "C90.10", "C90.12", "C90.20", "C90.22", "C90.30", "C90.32"],
        "hierarchy_parent": "HCC8",
        "weight": 0.469,
        "category": "Major"
    },
    "HCC11": {
        "description": "Colorectal, Bladder, and Other Cancers",
        "conditions": ["C15.3", "C15.4", "C15.5", "C15.8", "C15.9", "C16.0", "C16.1", "C16.2", "C16.3", "C16.4", "C16.5", "C16.6", "C16.8", "C16.9", "C18.0", "C18.1", "C18.2", "C18.3", "C18.4", "C18.5", "C18.6", "C18.7", "C18.8", "C18.9", "C19", "C20", "C21.0", "C21.1", "C21.2", "C21.8", "C49.10", "C49.11", "C49.12", "C49.20", "C49.21", "C49.22", "C49.30", "C49.31", "C49.32", "C49.40", "C49.41", "C49.42", "C49.50", "C49.51", "C49.52", "C49.60", "C49.61", "C49.62", "C49.90", "C49.91", "C49.92", "C56.0", "C56.1", "C56.2", "C56.9", "C57.00", "C57.01", "C57.02", "C57.10", "C57.11", "C57.12", "C58", "C60.0", "C60.1", "C60.2", "C60.8", "C60.9", "C61", "C62.00", "C62.01", "C62.02", "C62.10", "C62.11", "C62.12", "C62.90", "C62.91", "C62.92", "C63.0", "C63.1", "C63.2", "C63.7", "C63.8", "C63.9", "C64.1", "C64.2", "C64.9", "C65.1", "C65.2", "C65.9", "C66.1", "C66.2", "C66.9", "C67.0", "C67.1", "C67.2", "C67.3", "C67.4", "C67.5", "C67.6", "C67.7", "C67.8", "C67.9"],
        "hierarchy_parent": "HCC8",
        "weight": 0.359,
        "category": "Major"
    },
    "HCC18": {
        "description": "Diabetes with Acute Complications",
        "conditions": ["E10.10", "E10.11", "E10.20", "E10.21", "E10.22", "E10.23", "E10.24", "E10.25", "E10.26", "E10.27", "E10.29", "E10.30", "E10.31", "E10.32", "E10.33", "E10.34", "E10.35", "E10.36", "E10.37", "E10.39", "E10.40", "E10.41", "E10.42", "E10.43", "E10.44", "E10.49", "E10.50", "E10.51", "E10.52", "E10.53", "E10.54", "E10.55", "E10.59", "E10.60", "E10.61", "E10.62", "E10.63", "E10.64", "E10.65", "E10.69", "E10.8", "E10.9", "E11.10", "E11.11", "E11.20", "E11.21", "E11.22", "E11.23", "E11.24", "E11.25", "E11.26", "E11.27", "E11.29", "E11.30", "E11.31", "E11.32", "E11.33", "E11.34", "E11.35", "E11.36", "E11.37", "E11.39", "E11.40", "E11.41", "E11.42", "E11.43", "E11.44", "E11.49", "E11.50", "E11.51", "E11.52", "E11.53", "E11.54", "E11.55", "E11.59", "E11.60", "E11.61", "E11.62", "E11.63", "E11.64", "E11.65", "E11.69", "E11.8", "E11.9"],
        "hierarchy_parent": None,
        "weight": 0.399,
        "category": "Metabolic"
    },
    "HCC19": {
        "description": "Diabetes with Chronic Complications",
        "conditions": ["E10.3", "E10.4", "E10.5", "E10.6", "E11.3", "E11.4", "E11.5", "E11.6"],
        "hierarchy_parent": "HCC18",
        "weight": 0.316,
        "category": "Metabolic"
    },
    "HCC21": {
        "description": "Diabetes without Complication",
        "conditions": ["E10.0", "E11.0", "E11.9"],
        "hierarchy_parent": "HCC19",
        "weight": 0.114,
        "category": "Metabolic"
    },
    "HCC22": {
        "description": "Morbid Obesity",
        "conditions": ["E66.01"],
        "hierarchy_parent": None,
        "weight": 0.302,
        "category": "Metabolic"
    },
    "HCC23": {
        "description": "Other Obesity, Mixed Hyperlipidemia",
        "conditions": ["E66.09", "E66.1", "E66.2", "E66.8", "E66.9", "E78.2", "E78.5"],
        "hierarchy_parent": "HCC22",
        "weight": 0.066,
        "category": "Metabolic"
    },
    "HCC27": {
        "description": "End-Stage Liver Disease",
        "conditions": ["I85.01", "I85.11", "K70.30", "K70.31", "K70.40", "K70.41", "K71.1", "K72.10", "K72.11", "K72.90", "K72.91", "K73.0", "K73.1", "K73.2", "K73.3", "K73.4", "K73.5", "K73.8", "K73.9", "K74.00", "K74.01", "K74.02", "K74.10", "K74.11", "K74.12", "K74.2", "K74.3", "K74.4", "K74.5", "K74.60", "K74.69"],
        "hierarchy_parent": None,
        "weight": 0.469,
        "category": "Liver"
    },
    "HCC35": {
        "description": "Rheumatoid Arthritis and Specified Autoimmune Disorders",
        "conditions": ["M05.00", "M05.10", "M05.20", "M05.30", "M05.40", "M05.50", "M05.60", "M05.70", "M05.80", "M05.89", "M05.9", "M06.00", "M06.10", "M06.20", "M06.28", "M06.30", "M06.38", "M06.40", "M06.49", "M06.8", "M06.9", "M32.0", "M32.1", "M32.8", "M32.9", "M33.00", "M33.02", "M33.10", "M33.12", "M33.20", "M33.22", "M33.90", "M33.92", "M34.0", "M34.1", "M34.81", "M34.82", "M34.83", "M34.89", "M34.9", "M35.0", "M35.1", "M35.2", "M35.3", "M35.5", "M35.8", "M35.9"],
        "hierarchy_parent": None,
        "weight": 0.443,
        "category": "Musculoskeletal"
    },
    "HCC39": {
        "description": "Paralysis",
        "conditions": ["G04.1", "G80.00", "G80.01", "G80.02", "G80.03", "G80.04", "G80.09", "G80.1", "G80.2", "G80.3", "G80.4", "G80.8", "G80.9", "G81.00", "G81.01", "G81.10", "G81.11", "G81.90", "G81.91", "G82.0", "G82.1", "G82.2", "G82.3", "G82.4", "G82.50", "G82.51", "G82.52", "G82.53", "G82.54", "G82.55", "G82.56", "G82.57", "G82.58", "G82.59", "G82.8", "G83.0", "G83.1", "G83.2", "G83.3", "G83.4", "G83.5", "G83.8", "G83.9"],
        "hierarchy_parent": None,
        "weight": 0.570,
        "category": "Neurological"
    },
    "HCC46": {
        "description": "Severe Ischemic or Unspecified Stroke",
        "conditions": ["I63.30", "I63.31", "I63.32", "I63.33", "I63.34", "I63.39", "I63.50", "I63.51", "I63.52", "I63.53", "I63.54", "I63.59", "I63.9", "I64"],
        "hierarchy_parent": None,
        "weight": 0.535,
        "category": "Cardiovascular"
    },
    "HCC47": {
        "description": "Ischemic Stroke, Precerebral Occlusion, Other Circulatory Disease",
        "conditions": ["I63.0", "I63.10", "I63.11", "I63.12", "I63.19", "I63.20", "I63.21", "I63.22", "I63.29", "I65.01", "I65.02", "I65.03", "I65.09", "I65.1", "I65.20", "I65.21", "I65.22", "I65.23", "I65.29", "I65.8", "I65.9", "I66.01", "I66.02", "I66.03", "I66.09", "I66.1", "I66.20", "I66.21", "I66.22", "I66.23", "I66.29", "I66.3", "I66.8", "I66.9", "I67.0", "I67.1", "I67.2", "I67.3", "I67.4", "I67.5", "I67.6", "I67.7", "I67.81", "I67.82", "I67.84", "I67.89", "I67.9", "I68.0", "I68.1", "I68.2", "I68.8"],
        "hierarchy_parent": "HCC46",
        "weight": 0.257,
        "category": "Cardiovascular"
    },
    "HCC48": {
        "description": "Heart Failure",
        "conditions": ["I09.81", "I09.9", "I11.0", "I13.0", "I13.2", "I25.81", "I25.82", "I25.83", "I25.84", "I25.89", "I42.0", "I42.1", "I42.2", "I42.3", "I42.4", "I42.5", "I42.6", "I42.7", "I42.8", "I42.9", "I43", "I50.20", "I50.21", "I50.22", "I50.23", "I50.30", "I50.31", "I50.32", "I50.33", "I50.40", "I50.41", "I50.42", "I50.43", "I50.810", "I50.811", "I50.812", "I50.813", "I50.814", "I50.82", "I50.83", "I50.84", "I50.89", "I50.9"],
        "hierarchy_parent": None,
        "weight": 0.381,
        "category": "Cardiovascular"
    },
    "HCC55": {
        "description": "Conduction Disorders, Cardiac Dysrhythmias",
        "conditions": ["I44.0", "I44.1", "I44.2", "I44.30", "I44.31", "I44.32", "I44.39", "I44.4", "I44.5", "I44.6", "I44.7", "I45.0", "I45.1", "I45.2", "I45.3", "I45.4", "I45.5", "I45.6", "I45.81", "I45.82", "I45.89", "I45.9", "I46.2", "I46.9", "I47.0", "I47.1", "I47.2", "I47.9", "I48.0", "I48.1", "I48.11", "I48.19", "I48.20", "I48.21", "I48.91", "I48.92", "I49.00", "I49.01", "I49.02", "I49.1", "I49.2", "I49.3", "I49.40", "I49.41", "I49.42", "I49.43", "I49.44", "I49.45", "I49.46", "I49.47", "I49.48", "I49.49", "I49.5", "I49.8", "I49.9", "R00.0", "R00.1", "R00.2", "R00.3", "R00.8"],
        "hierarchy_parent": None,
        "weight": 0.206,
        "category": "Cardiovascular"
    },
    "HCC57": {
        "description": "Acute Myocardial Infarction",
        "conditions": ["I21.01", "I21.02", "I21.09", "I21.11", "I21.19", "I21.21", "I21.29", "I21.3", "I21.4", "I21.9", "I22.0", "I22.1", "I22.2", "I22.8", "I22.9", "I23.0", "I23.1", "I23.2", "I23.3", "I23.4", "I23.5", "I23.6", "I23.7", "I23.8"],
        "hierarchy_parent": None,
        "weight": 0.424,
        "category": "Cardiovascular"
    },
    "HCC59": {
        "description": "Chronic Obstructive Pulmonary Disease, Including Bronchiectasis",
        "conditions": ["J41.0", "J41.1", "J41.8", "J42", "J43.0", "J43.1", "J43.2", "J43.8", "J43.9", "J44.0", "J44.1", "J44.9", "J47.0", "J47.1", "J47.9", "J84.10", "J84.11", "J84.17", "J84.2", "J84.81", "J84.84", "J84.89", "J84.9", "J96.00", "J96.01", "J96.02", "J96.10", "J96.11", "J96.12", "J96.90", "J96.91", "J96.92", "J98.2", "J98.3", "J98.4"],
        "hierarchy_parent": None,
        "weight": 0.390,
        "category": "Pulmonary"
    },
    "HCC70": {
        "description": "Dialysis Status",
        "conditions": ["Z49.31", "Z49.32", "Z99.2"],
        "hierarchy_parent": None,
        "weight": 1.246,
        "category": "Kidney"
    },
    "HCC71": {
        "description": "Chronic Kidney Disease, Stage 5",
        "conditions": ["N18.5", "N18.6"],
        "hierarchy_parent": "HCC70",
        "weight": 0.678,
        "category": "Kidney"
    },
    "HCC72": {
        "description": "Chronic Kidney Disease, Stage 4",
        "conditions": ["N18.4"],
        "hierarchy_parent": "HCC71",
        "weight": 0.381,
        "category": "Kidney"
    },
    "HCC85": {
        "description": "Congestive Heart Failure",
        "conditions": ["I50.10", "I50.11", "I50.12", "I50.13", "I50.9"],
        "hierarchy_parent": "HCC48",
        "weight": 0.288,
        "category": "Cardiovascular"
    },
    "HCC96": {
        "description": "Specified Heart Arrhythmias",
        "conditions": ["I48.0", "I48.1", "I48.11", "I48.19", "I48.20", "I48.21", "I48.91", "I48.92"],
        "hierarchy_parent": "HCC55",
        "weight": 0.156,
        "category": "Cardiovascular"
    },
    "HCC108": {
        "description": "Vascular Disease with Complications",
        "conditions": ["I70.0", "I70.1", "I70.20", "I70.21", "I70.22", "I70.23", "I70.24", "I70.25", "I70.26", "I70.29", "I70.30", "I70.31", "I70.32", "I70.33", "I70.34", "I70.35", "I70.36", "I70.39", "I70.40", "I70.41", "I70.42", "I70.43", "I70.44", "I70.45", "I70.46", "I70.49", "I70.50", "I70.51", "I70.52", "I70.53", "I70.54", "I70.55", "I70.56", "I70.59", "I70.60", "I70.61", "I70.62", "I70.63", "I70.64", "I70.65", "I70.66", "I70.69", "I70.70", "I70.71", "I70.72", "I70.73", "I70.74", "I70.75", "I70.76", "I70.79", "I70.8", "I70.90", "I70.91", "I70.92", "I70.93", "I71.01", "I71.02", "I71.03", "I71.1", "I71.2", "I71.3", "I71.4", "I71.5", "I71.6", "I71.8", "I71.9", "I73.1", "I73.8", "I73.9", "I74.0", "I74.1", "I74.2", "I74.3", "I74.8", "I74.9", "I77.0", "I77.1", "I77.2", "I77.3", "I77.4", "I77.5", "I77.6", "I77.8", "I77.9", "I79.0", "I79.1", "I79.2", "I79.8", "K55.0", "K55.1", "K55.2", "K55.3", "K55.8", "K55.9"],
        "hierarchy_parent": None,
        "weight": 0.366,
        "category": "Cardiovascular"
    },
    "HCC111": {
        "description": "Vascular Disease without Complications",
        "conditions": ["I70.91", "I73.9", "I77.9", "I79.0"],
        "hierarchy_parent": "HCC108",
        "weight": 0.106,
        "category": "Cardiovascular"
    },
}

# CMS-HCC V28 Model Mappings (subset - key differences from V24)
HCC_V28: Dict[str, Dict[str, Any]] = {
    "HCC1": {
        "description": "HIV/AIDS",
        "conditions": ["B20", "B97.35", "R75", "Z21"],
        "hierarchy_parent": None,
        "weight": 0.886,
        "category": "Major",
        "v28_notes": "Slightly reduced weight from V24"
    },
    "HCC8": {
        "description": "Metastatic Cancer",
        "conditions": ["C77.0", "C77.1", "C77.2", "C77.3", "C77.4", "C77.5", "C78.00", "C78.01", "C78.02", "C78.10", "C78.20", "C78.30", "C78.80", "C78.89", "C79.00", "C79.01", "C79.02", "C79.10", "C79.11", "C79.19", "C79.2", "C79.31", "C79.32", "C79.40", "C79.49", "C79.51", "C79.60", "C79.61", "C79.70", "C79.71", "C79.72", "C79.81", "C79.82", "C79.89", "C79.9", "C7A.0", "C7A.1", "C7A.8", "C80.0", "C80.1", "C80.2"],
        "hierarchy_parent": None,
        "weight": 1.314,
        "category": "Major",
        "v28_notes": "V28 separates acute leukemia into new HCC9"
    },
    "HCC9": {
        "description": "Acute Myeloid Leukemia and Other Leukemias",
        "conditions": ["C91.00", "C91.02", "C91.80", "C91.90", "C92.00", "C92.02", "C92.20", "C92.22", "C92.40", "C92.42", "C92.50", "C92.52", "C92.60", "C92.62", "C92.70", "C92.72", "C92.80", "C92.90", "C93.00", "C93.02", "C93.10", "C93.12", "C93.30", "C93.32", "C93.80", "C93.90", "C94.00", "C94.02", "C94.20", "C94.22", "C94.30", "C94.32", "C94.40", "C94.42", "C94.6", "C94.80", "C94.90", "C95.00", "C95.02", "C95.10", "C95.12", "C95.30", "C95.32", "C95.80", "C95.90"],
        "hierarchy_parent": None,
        "weight": 1.092,
        "category": "Major",
        "v28_notes": "New HCC in V28; split from HCC8 in V24"
    },
    "HCC18": {
        "description": "Diabetes with Complications",
        "conditions": ["E10.10", "E10.11", "E10.20", "E10.21", "E10.22", "E10.23", "E10.24", "E10.25", "E10.26", "E10.27", "E10.29", "E10.30", "E10.31", "E10.32", "E10.33", "E10.34", "E10.35", "E10.36", "E10.37", "E10.39", "E10.40", "E10.41", "E10.42", "E10.43", "E10.44", "E10.49", "E10.50", "E10.51", "E10.52", "E10.53", "E10.54", "E10.55", "E10.59", "E10.60", "E10.61", "E10.62", "E10.63", "E10.64", "E10.65", "E10.69", "E10.8", "E10.9", "E11.10", "E11.11", "E11.20", "E11.21", "E11.22", "E11.23", "E11.24", "E11.25", "E11.26", "E11.27", "E11.29", "E11.30", "E11.31", "E11.32", "E11.33", "E11.34", "E11.35", "E11.36", "E11.37", "E11.39", "E11.40", "E11.41", "E11.42", "E11.43", "E11.44", "E11.49", "E11.50", "E11.51", "E11.52", "E11.53", "E11.54", "E11.55", "E11.59", "E11.60", "E11.61", "E11.62", "E11.63", "E11.64", "E11.65", "E11.69", "E11.8", "E11.9"],
        "hierarchy_parent": None,
        "weight": 0.372,
        "category": "Metabolic",
        "v28_notes": "V28 merges acute and chronic complications into single HCC"
    },
    "HCC19": {
        "description": "Diabetes without Complications",
        "conditions": ["E10.0", "E11.0"],
        "hierarchy_parent": "HCC18",
        "weight": 0.098,
        "category": "Metabolic",
        "v28_notes": "Reduced weight; V24 HCC21 remapped to HCC19"
    },
    "HCC22": {
        "description": "Morbid Obesity",
        "conditions": ["E66.01"],
        "hierarchy_parent": None,
        "weight": 0.312,
        "category": "Metabolic",
        "v28_notes": "Similar to V24"
    },
    "HCC48": {
        "description": "Heart Failure",
        "conditions": ["I09.81", "I09.9", "I11.0", "I13.0", "I13.2", "I25.81", "I25.82", "I25.83", "I25.84", "I25.89", "I42.0", "I42.1", "I42.2", "I42.3", "I42.4", "I42.5", "I42.6", "I42.7", "I42.8", "I42.9", "I43", "I50.20", "I50.21", "I50.22", "I50.23", "I50.30", "I50.31", "I50.32", "I50.33", "I50.40", "I50.41", "I50.42", "I50.43", "I50.810", "I50.811", "I50.812", "I50.813", "I50.814", "I50.82", "I50.83", "I50.84", "I50.89", "I50.9"],
        "hierarchy_parent": None,
        "weight": 0.396,
        "category": "Cardiovascular",
        "v28_notes": "Similar to V24"
    },
    "HCC59": {
        "description": "COPD and Related Conditions",
        "conditions": ["J41.0", "J41.1", "J41.8", "J42", "J43.0", "J43.1", "J43.2", "J43.8", "J43.9", "J44.0", "J44.1", "J44.9", "J47.0", "J47.1", "J47.9", "J84.10", "J84.11", "J84.17", "J84.2", "J84.81", "J84.84", "J84.89", "J84.9", "J98.2", "J98.3", "J98.4"],
        "hierarchy_parent": None,
        "weight": 0.404,
        "category": "Pulmonary",
        "v28_notes": "V28 removes respiratory failure codes from COPD HCC"
    },
    "HCC70": {
        "description": "Dialysis Status",
        "conditions": ["Z49.31", "Z49.32", "Z99.2"],
        "hierarchy_parent": None,
        "weight": 1.293,
        "category": "Kidney",
        "v28_notes": "Increased weight from V24"
    },
    "HCC71": {
        "description": "Chronic Kidney Disease Stage 5",
        "conditions": ["N18.5", "N18.6"],
        "hierarchy_parent": "HCC70",
        "weight": 0.693,
        "category": "Kidney",
        "v28_notes": "Slightly increased from V24"
    },
}

# Demographic factor weights
DEMOGRAPHIC_FACTORS: Dict[str, Dict[str, Any]] = {
    "age_sex_factors": {
        "description": "Base demographic RAF factors by age group and sex",
        "factors": {
            "age_0_34_male": 0.168,
            "age_0_34_female": 0.156,
            "age_35_44_male": 0.273,
            "age_35_44_female": 0.275,
            "age_45_54_male": 0.470,
            "age_45_54_female": 0.488,
            "age_55_59_male": 0.632,
            "age_55_59_female": 0.654,
            "age_60_64_male": 0.773,
            "age_60_64_female": 0.798,
            "age_65_69_male": 0.822,
            "age_65_69_female": 0.845,
            "age_70_74_male": 0.916,
            "age_70_74_female": 0.940,
            "age_75_79_male": 1.020,
            "age_75_79_female": 1.045,
            "age_80_84_male": 1.145,
            "age_80_84_female": 1.171,
            "age_85_89_male": 1.282,
            "age_85_89_female": 1.310,
            "age_90_94_male": 1.444,
            "age_90_94_female": 1.472,
            "age_95_plus_male": 1.632,
            "age_95_plus_female": 1.660,
        }
    },
    "medicaid_dual_eligible": {
        "description": "Additional factor for dual-eligible (Medicare + Medicaid) beneficiaries",
        "factor": 0.114,
        "note": "Full dual-eligible beneficiaries receive additional payment adjustment"
    },
    "institutional_status": {
        "description": "Adjustment for institutionalized beneficiaries (SNF, LTC, etc.)",
        "factors": {
            "community": 1.000,
            "snf_short_stay": 1.401,
            "snf_long_stay": 1.714,
            "ltc": 1.714,
            "community_snf": 1.526
        }
    },
    "disabled_status": {
        "description": "Factor adjustment for disabled beneficiaries under 65",
        "factor": 0.078,
        "note": "Originally entitled to Medicare due to disability"
    }
}

# Disease hierarchy rules
HIERARCHY_RULES: Dict[str, Dict[str, Any]] = {
    "cancer_hierarchy": {
        "description": "Metastatic cancer supersedes other cancer categories",
        "rules": [
            {"parent": "HCC8", "children": ["HCC9", "HCC10", "HCC11"], "action": "Only highest HCC counted; children set to zero weight when parent present"}
        ]
    },
    "diabetes_hierarchy": {
        "description": "Diabetes with complications supersedes diabetes without",
        "rules": [
            {"parent": "HCC18", "children": ["HCC19", "HCC21"], "action": "Only highest diabetes HCC counted; less severe forms zeroed"}
        ]
    },
    "kidney_disease_hierarchy": {
        "description": "Dialysis status supersedes CKD stages",
        "rules": [
            {"parent": "HCC70", "children": ["HCC71", "HCC72"], "action": "Dialysis status counted; CKD stages below set to zero"}
        ]
    },
    "vascular_hierarchy": {
        "description": "Vascular disease with complications supersedes without",
        "rules": [
            {"parent": "HCC108", "children": ["HCC111"], "action": "Vascular with complications counted; uncomplicated set to zero"}
        ]
    },
    "stroke_hierarchy": {
        "description": "Severe stroke supersedes less severe stroke categories",
        "rules": [
            {"parent": "HCC46", "children": ["HCC47"], "action": "Severe stroke counted; less severe stroke set to zero"}
        ]
    },
    "cardiac_hierarchy": {
        "description": "Heart failure and acute MI supersede arrhythmia categories",
        "rules": [
            {"parent": "HCC48", "children": ["HCC85"], "action": "Heart failure counted; subset conditions may still add weight per model rules"},
            {"parent": "HCC57", "children": [], "action": "Acute MI stands alone; may coexist with heart failure"}
        ]
    },
    "obesity_hierarchy": {
        "description": "Morbid obesity supersedes other obesity",
        "rules": [
            {"parent": "HCC22", "children": ["HCC23"], "action": "Morbid obesity counted; other obesity set to zero"}
        ]
    }
}

# Documentation improvement suggestions by HCC
DOCUMENTATION_IMPROVEMENTS: Dict[str, Dict[str, Any]] = {
    "HCC18": {
        "hcc": "HCC18",
        "description": "Diabetes with Acute Complications",
        "documentation_tips": [
            "Specify type of diabetes (Type 1 vs Type 2) with every encounter",
            "Document acute complication (DKA, hypoglycemia, hyperosmolar state) with specificity",
            "Link diabetes to complication using 'due to' or 'with' language",
            "Document current A1C level and management plan",
            "Document whether complication is current or historical (use Z79 codes for long-term meds)",
            "Ensure 'uncontrolled' or 'hyperglycemia' is documented when applicable (E11.65)"
        ],
        "common_errors": [
            "Documenting 'diabetes' without specifying type or complication",
            "Failing to link complication to diabetes explicitly",
            "Using 'history of' when condition is still active and being managed",
            "Not documenting insulin use or pump status"
        ]
    },
    "HCC48": {
        "hcc": "HCC48",
        "description": "Heart Failure",
        "documentation_tips": [
            "Document specific type of heart failure (systolic, diastolic, combined)",
            "Include NYHA class or ACC/AHA stage with every encounter",
            "Document ejection fraction percentage when available",
            "Use 'heart failure' not just 'CHF' abbreviation",
            "Document if condition is acute, chronic, or acute on chronic",
            "Link heart failure to underlying cause (ischemic, hypertensive, valvular)",
            "Document current BNP/NT-proBNP levels when available"
        ],
        "common_errors": [
            "Documenting 'CHF' without specifying systolic/diastolic",
            "Not documenting current severity or functional class",
            "Failing to code heart failure type with reduced vs preserved EF",
            "Using 'history of heart failure' when condition is active"
        ]
    },
    "HCC59": {
        "hcc": "HCC59",
        "description": "COPD",
        "documentation_tips": [
            "Document COPD with specific type (emphysema, chronic bronchitis)",
            "Include GOLD classification or FEV1 percentage when available",
            "Document acute exacerbation episodes with specificity",
            "Document oxygen dependency and home O2 use (Z99.81)",
            "Link COPD to related conditions (cor pulmonale, respiratory failure)",
            "Document smoking status and cessation counseling if applicable"
        ],
        "common_errors": [
            "Using 'COPD' without specifying type or severity",
            "Not documenting exacerbation episodes separately",
            "Failing to document oxygen use status",
            "Not linking related conditions like cor pulmonale"
        ]
    },
    "HCC22": {
        "hcc": "HCC22",
        "description": "Morbid Obesity",
        "documentation_tips": [
            "Document BMI with every encounter for obese patients",
            "Use 'morbid obesity' (E66.01) when BMI >= 40 or BMI >= 35 with comorbidity",
            "Document obesity-related comorbidities explicitly",
            "Link obesity to related conditions using 'due to' language",
            "Document weight management interventions and counseling",
            "Record whether bariatric surgery has been performed"
        ],
        "common_errors": [
            "Documenting BMI without corresponding diagnosis code",
            "Using 'obesity' (E66.9) when 'morbid obesity' (E66.01) is more appropriate",
            "Not linking obesity to comorbid conditions",
            "Failing to document weight management treatment plan"
        ]
    },
    "HCC70": {
        "hcc": "HCC70",
        "description": "Dialysis Status",
        "documentation_tips": [
            "Document type of dialysis (hemodialysis, peritoneal, home HD)",
            "Include frequency and duration of dialysis sessions",
            "Document dialysis access type (AV fistula, graft, catheter)",
            "Link ESRD to underlying cause (diabetes, hypertension, etc.)",
            "Document dialysis complications when present",
            "Use Z99.2 (dependence on renal dialysis) for ongoing dialysis status"
        ],
        "common_errors": [
            "Not documenting dialysis access type and complications",
            "Failing to code ESRD and dialysis status together",
            "Using acute kidney injury codes when patient has chronic ESRD",
            "Not documenting dialysis modality and frequency"
        ]
    }
}


@skill(name="risk_adjuster", category="healthcare")
class RiskAdjusterSkill(AetheraSkill):
    """
    Calculate HCC/RAF scores, identify gaps, suggest documentation improvements.
    """

    @property
    def name(self) -> str:
        return "risk_adjuster"

    @property
    def description(self) -> str:
        return "Calculate RAF/HCC scores (CMS-HCC V24/V28), identify HCC gaps, suggest documentation improvements"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["calculate_raf", "identify_gaps", "suggest_improvements", "lookup_hcc", "compare_v24_v28"],
                    "description": "Action: calculate_raf, identify_gaps, suggest_improvements, lookup_hcc, compare_v24_v28"
                },
                "model_version": {
                    "type": "string",
                    "enum": ["v24", "v28"],
                    "description": "CMS-HCC model version (v24 or v28)"
                },
                "diagnosis_codes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of ICD-10-CM diagnosis codes to evaluate"
                },
                "age": {
                    "type": "integer",
                    "description": "Patient age"
                },
                "sex": {
                    "type": "string",
                    "enum": ["M", "F"],
                    "description": "Patient sex (M or F)"
                },
                "dual_eligible": {
                    "type": "boolean",
                    "description": "Whether patient is dual-eligible (Medicare + Medicaid)"
                },
                "institutional": {
                    "type": "boolean",
                    "description": "Whether patient is in institutional setting"
                },
                "disabled": {
                    "type": "boolean",
                    "description": "Whether patient is disabled (under 65 Medicare)"
                },
                "hcc_code": {
                    "type": "string",
                    "description": "Specific HCC code to look up (for lookup_hcc action)"
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
            {"input": {"action": "calculate_raf", "model_version": "v24", "diagnosis_codes": ["E11.9", "I50.9", "J44.1"], "age": 72, "sex": "M"}},
            {"input": {"action": "identify_gaps", "model_version": "v24", "diagnosis_codes": ["E11.9"]}},
            {"input": {"action": "suggest_improvements", "hcc_code": "HCC18"}},
            {"input": {"action": "lookup_hcc", "hcc_code": "HCC48"}},
        ]

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "calculate_raf")

        try:
            if action == "calculate_raf":
                result = self._calculate_raf(kwargs)
            elif action == "identify_gaps":
                result = self._identify_gaps(kwargs)
            elif action == "suggest_improvements":
                hcc_code = kwargs.get("hcc_code", "")
                result = self._suggest_improvements(hcc_code)
            elif action == "lookup_hcc":
                hcc_code = kwargs.get("hcc_code", "")
                model_version = kwargs.get("model_version", "v24")
                result = self._lookup_hcc(hcc_code, model_version)
            elif action == "compare_v24_v28":
                diagnosis_codes = kwargs.get("diagnosis_codes", [])
                result = self._compare_v24_v28(diagnosis_codes)
            else:
                return SkillResult(success=False, error=f"Unknown action: {action}")

            return SkillResult(success=True, data=result)

        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _calculate_raf(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate RAF score from diagnoses and demographics."""
        model_version = kwargs.get("model_version", "v24")
        diagnosis_codes = kwargs.get("diagnosis_codes", [])
        age = kwargs.get("age", 70)
        sex = kwargs.get("sex", "M")
        dual_eligible = kwargs.get("dual_eligible", False)
        institutional = kwargs.get("institutional", False)
        disabled = kwargs.get("disabled", False)

        hcc_model = HCC_V24 if model_version == "v24" else HCC_V28

        # Map diagnoses to HCCs
        mapped_hccs = self._map_diagnoses_to_hccs(diagnosis_codes, hcc_model)

        # Apply hierarchy rules
        active_hccs = self._apply_hierarchy(mapped_hccs)

        # Calculate demographic factor
        demo_factor = self._get_demographic_factor(age, sex)

        # Calculate disease factor
        disease_factor = sum(hcc["weight"] for hcc in active_hccs.values())

        # Apply demographic adjustments
        dual_factor = DEMOGRAPHIC_FACTORS["medicaid_dual_eligible"]["factor"] if dual_eligible else 0
        disability_factor = DEMOGRAPHIC_FACTORS["disabled_status"]["factor"] if disabled else 0
        institutional_factor = DEMOGRAPHIC_FACTORS["institutional_status"]["factors"].get(
            "snf_long_stay" if institutional else "community", 1.000
        )

        total_raf = round(
            (demo_factor + disease_factor + dual_factor + disability_factor) * institutional_factor, 3
        )

        return {
            "model_version": model_version,
            "demographic_factor": round(demo_factor, 3),
            "disease_factor": round(disease_factor, 3),
            "dual_eligible_factor": round(dual_factor, 3),
            "disability_factor": round(disability_factor, 3),
            "institutional_multiplier": round(institutional_factor, 3),
            "mapped_hccs": [
                {"hcc": hcc_data["hcc"], "description": hcc_data["description"], "weight": hcc_data["weight"]}
                for hcc_data in active_hccs.values()
            ],
            "excluded_by_hierarchy": [
                {"hcc": hcc_data["hcc"], "description": hcc_data["description"],
                 "excluded_by": hcc_data.get("excluded_by", "hierarchy rule")}
                for hcc_data in mapped_hccs.values()
                if hcc_data["hcc"] not in active_hccs
            ],
            "total_raf": total_raf,
            "input_diagnoses": diagnosis_codes,
            "age": age,
            "sex": sex
        }

    def _map_diagnoses_to_hccs(self, diagnosis_codes: List[str], hcc_model: Dict) -> Dict[str, Dict[str, Any]]:
        """Map ICD-10 diagnosis codes to HCC categories."""
        mapped = {}
        for dx_code in diagnosis_codes:
            dx_upper = dx_code.upper().strip()
            for hcc_code, hcc_data in hcc_model.items():
                if dx_upper in hcc_data["conditions"]:
                    if hcc_code not in mapped:
                        mapped[hcc_code] = {
                            "hcc": hcc_code,
                            "description": hcc_data["description"],
                            "weight": hcc_data["weight"],
                            "hierarchy_parent": hcc_data["hierarchy_parent"],
                            "category": hcc_data["category"],
                            "triggering_diagnoses": []
                        }
                    mapped[hcc_code]["triggering_diagnoses"].append(dx_upper)
        return mapped

    def _apply_hierarchy(self, mapped_hccs: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Apply disease hierarchy rules - only count the highest HCC in each hierarchy."""
        active = dict(mapped_hccs)

        for hcc_code, hcc_data in list(active.items()):
            parent = hcc_data.get("hierarchy_parent")
            if parent and parent in active:
                # This HCC is superseded by its parent; remove it
                active[hcc_code]["excluded_by"] = parent
                del active[hcc_code]

        return active

    def _get_demographic_factor(self, age: int, sex: str) -> float:
        """Get demographic RAF factor based on age and sex."""
        age_groups = DEMOGRAPHIC_FACTORS["age_sex_factors"]["factors"]

        if age < 35:
            age_key = "0_34"
        elif age < 45:
            age_key = "35_44"
        elif age < 55:
            age_key = "45_54"
        elif age < 60:
            age_key = "55_59"
        elif age < 65:
            age_key = "60_64"
        elif age < 70:
            age_key = "65_69"
        elif age < 75:
            age_key = "70_74"
        elif age < 80:
            age_key = "75_79"
        elif age < 85:
            age_key = "80_84"
        elif age < 90:
            age_key = "85_89"
        elif age < 95:
            age_key = "90_94"
        else:
            age_key = "95_plus"

        sex_key = "male" if sex.upper() == "M" else "female"
        factor_key = f"age_{age_key}_{sex_key}"
        return age_groups.get(factor_key, 0.822)

    def _identify_gaps(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Identify HCC gaps - conditions that may be present but not coded."""
        model_version = kwargs.get("model_version", "v24")
        diagnosis_codes = kwargs.get("diagnosis_codes", [])

        hcc_model = HCC_V24 if model_version == "v24" else HCC_V28
        mapped_hccs = self._map_diagnoses_to_hccs(diagnosis_codes, hcc_model)
        active_hccs = self._apply_hierarchy(mapped_hccs)

        gaps = []
        # Check for commonly missed comorbidity HCCs
        has_diabetes = any("Diabetes" in h["description"] for h in mapped_hccs.values())
        has_ckd = any("Kidney" in h["description"] or "Dialysis" in h["description"] for h in mapped_hccs.values())
        has_heart_failure = any("Heart Failure" in h["description"] for h in mapped_hccs.values())
        has_copd = any("COPD" in h["description"] for h in mapped_hccs.values())
        has_vascular = any("Vascular" in h["description"] for h in mapped_hccs.values())

        if has_diabetes and not has_ckd:
            gaps.append({
                "potential_hcc": "HCC70/HCC71/HCC72",
                "description": "Diabetic kidney disease / CKD",
                "reason": "Patients with diabetes often have comorbid kidney disease; verify kidney function",
                "suggested_screening": "Check eGFR and urine albumin at least annually per ADA guidelines"
            })

        if has_diabetes and not has_heart_failure:
            gaps.append({
                "potential_hcc": "HCC48",
                "description": "Heart Failure",
                "reason": "Diabetes is a major risk factor for heart failure; consider cardiac evaluation",
                "suggested_screening": "Assess for heart failure symptoms; BNP/NT-proBNP screening"
            })

        if has_copd and not has_heart_failure:
            gaps.append({
                "potential_hcc": "HCC48",
                "description": "Heart Failure / Cor Pulmonale",
                "reason": "COPD patients at risk for right heart failure (cor pulmonale)",
                "suggested_screening": "Echocardiogram to assess right heart function"
            })

        if has_diabetes:
            diabetes_hccs = [h for h in mapped_hccs.values() if "Diabetes" in h["description"]]
            has_complications = any("Complication" in h["description"] or "Acute" in h["description"]
                                    for h in diabetes_hccs)
            if not has_complications:
                gaps.append({
                    "potential_hcc": "HCC18",
                    "description": "Diabetes with Complications",
                    "reason": "Diabetes may have undocumented complications (neuropathy, retinopathy, nephropathy)",
                    "suggested_screening": "Annual diabetic eye exam, foot exam, neuropathy assessment, urine microalbumin"
                })

        if has_vascular:
            gaps.append({
                "potential_hcc": "HCC48",
                "description": "Heart Failure",
                "reason": "Vascular disease increases heart failure risk; verify cardiac status",
                "suggested_screening": "Cardiac assessment including echocardiogram if symptomatic"
            })

        # General documentation quality gaps
        doc_gaps = []
        for dx in diagnosis_codes:
            # Check if diagnosis is specific enough
            if dx.endswith(".9") or "." not in dx:
                doc_gaps.append({
                    "diagnosis": dx,
                    "issue": "Diagnosis code may lack specificity",
                    "recommendation": f"Consider if {dx} can be coded to a more specific subcategory"
                })

        return {
            "model_version": model_version,
            "current_hccs": list(active_hccs.keys()),
            "potential_gaps": gaps,
            "documentation_specificity_issues": doc_gaps,
            "gap_count": len(gaps),
            "documentation_issue_count": len(doc_gaps),
            "recommendation": "Review gaps at next patient encounter and document any applicable conditions with specificity"
        }

    def _suggest_improvements(self, hcc_code: str) -> Dict[str, Any]:
        """Suggest documentation improvements for an HCC."""
        hcc_upper = hcc_code.upper().strip()
        improvements = DOCUMENTATION_IMPROVEMENTS.get(hcc_upper)

        if not improvements:
            # Try to find HCC in models and provide generic guidance
            for model_name, model in [("V24", HCC_V24), ("V28", HCC_V28)]:
                if hcc_upper in model:
                    hcc_data = model[hcc_upper]
                    return {
                        "hcc_code": hcc_upper,
                        "description": hcc_data["description"],
                        "documentation_tips": [
                            "Ensure diagnosis is documented at every applicable encounter",
                            "Document current status and severity",
                            "Link this condition to related complications using 'due to' language",
                            "Use the most specific ICD-10 code available",
                            "Document treatment plan and response to treatment"
                        ],
                        "common_errors": [
                            "Using unspecified codes when more specific codes are available",
                            "Documenting 'history of' when condition is still active",
                            "Failing to link related conditions"
                        ],
                        "model_found_in": model_name
                    }

            return {
                "hcc_code": hcc_upper,
                "error": f"HCC code {hcc_upper} not found in V24 or V28 models",
                "available_v24_hccs": list(HCC_V24.keys()),
                "available_v28_hccs": list(HCC_V28.keys())
            }

        return {
            "hcc_code": hcc_upper,
            "description": improvements["description"],
            "documentation_tips": improvements["documentation_tips"],
            "common_errors": improvements["common_errors"]
        }

    def _lookup_hcc(self, hcc_code: str, model_version: str) -> Dict[str, Any]:
        """Look up HCC code details."""
        hcc_upper = hcc_code.upper().strip()
        model = HCC_V24 if model_version == "v24" else HCC_V28

        hcc_data = model.get(hcc_upper)
        if not hcc_data:
            return {
                "hcc_code": hcc_upper,
                "model_version": model_version,
                "error": f"HCC code {hcc_upper} not found in {model_version} model"
            }

        result = {
            "hcc_code": hcc_upper,
            "model_version": model_version,
            "description": hcc_data["description"],
            "weight": hcc_data["weight"],
            "category": hcc_data["category"],
            "hierarchy_parent": hcc_data.get("hierarchy_parent"),
            "conditions_count": len(hcc_data["conditions"]),
            "sample_conditions": hcc_data["conditions"][:10]
        }

        if model_version == "v28" and "v28_notes" in hcc_data:
            result["v28_notes"] = hcc_data["v28_notes"]

        return result

    def _compare_v24_v28(self, diagnosis_codes: List[str]) -> Dict[str, Any]:
        """Compare RAF/HCC mappings between V24 and V28 models."""
        v24_mapped = self._map_diagnoses_to_hccs(diagnosis_codes, HCC_V24)
        v28_mapped = self._map_diagnoses_to_hccs(diagnosis_codes, HCC_V28)

        v24_active = self._apply_hierarchy(v24_mapped)
        v28_active = self._apply_hierarchy(v28_mapped)

        v24_weight = sum(h["weight"] for h in v24_active.values())
        v28_weight = sum(h["weight"] for h in v28_active.values())

        only_v24 = set(v24_active.keys()) - set(v28_active.keys())
        only_v28 = set(v28_active.keys()) - set(v24_active.keys())
        both = set(v24_active.keys()) & set(v28_active.keys())

        weight_differences = []
        for hcc in both:
            v24_w = v24_active[hcc]["weight"]
            v28_w = v28_active[hcc]["weight"]
            if v24_w != v28_w:
                weight_differences.append({
                    "hcc": hcc,
                    "description": v24_active[hcc]["description"],
                    "v24_weight": v24_w,
                    "v28_weight": v28_w,
                    "difference": round(v28_w - v24_w, 3)
                })

        return {
            "diagnosis_codes": diagnosis_codes,
            "v24": {
                "active_hccs": list(v24_active.keys()),
                "disease_factor": round(v24_weight, 3)
            },
            "v28": {
                "active_hccs": list(v28_active.keys()),
                "disease_factor": round(v28_weight, 3)
            },
            "differences": {
                "only_in_v24": list(only_v24),
                "only_in_v28": list(only_v28),
                "in_both": list(both),
                "weight_differences": weight_differences
            },
            "disease_factor_change": round(v28_weight - v24_weight, 3),
            "impact": "increase" if v28_weight > v24_weight else "decrease" if v28_weight < v24_weight else "no_change"
        }