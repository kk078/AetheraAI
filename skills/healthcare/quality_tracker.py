"""
Aethera AI - Quality Tracker Skill

Track HEDIS, MIPS, and Stars quality measures.
"""

from typing import Dict, Any, List, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill


# HEDIS Measures (NCQA Healthcare Effectiveness Data and Information Set)
HEDIS_MEASURES: Dict[str, Dict[str, Any]] = {
    "HBD": {
        "measure_id": "HBD",
        "name": "Controlling High Blood Pressure",
        "description": "Adults 18-85 with a diagnosis of hypertension whose BP was adequately controlled (<140/90)",
        "domain": "Cardiovascular",
        "population": "Adults 18-85 with hypertension",
        "denominator_criteria": "Patients 18-85 with diagnosis of hypertension (essential or secondary) during measurement year",
        "numerator_criteria": "Most recent BP reading < 140/90 during measurement year",
        "exclusions": [
            "Pregnancy during measurement year",
            "End-stage renal disease",
            "Hospice or palliative care",
            "Patients age 81+ with frailty indicators"
        ],
        "benchmark": 0.70,
        "performance_levels": {"poor": 0.50, "fair": 0.60, "good": 0.70, "excellent": 0.80},
        "data_source": "EHR/Chart review or claims",
        "measure_type": "Outcome"
    },
    "CBC": {
        "measure_id": "CBC",
        "name": "Colorectal Cancer Screening",
        "description": "Adults 50-75 appropriately screened for colorectal cancer",
        "domain": "Cancer Screening",
        "population": "Adults 50-75",
        "denominator_criteria": "Patients 50-75 continuously enrolled during measurement year",
        "numerator_criteria": "Colonoscopy within 10 years, FIT within 1 year, FIT-DNA within 3 years, CT colonography within 5 years, or flexible sigmoidoscopy within 5 years",
        "exclusions": [
            "Colorectal cancer diagnosis",
            "Colectomy",
            "Hospice or palliative care"
        ],
        "benchmark": 0.65,
        "performance_levels": {"poor": 0.45, "fair": 0.55, "good": 0.65, "excellent": 0.75},
        "data_source": "Claims or EHR",
        "measure_type": "Process"
    },
    "CDC": {
        "measure_id": "CDC",
        "name": "Comprehensive Diabetes Care",
        "description": "Diabetics with HbA1c control, eye exam, kidney monitoring, and BP control",
        "domain": "Diabetes",
        "population": "Adults 18-75 with diabetes (Type 1 or Type 2)",
        "denominator_criteria": "Patients 18-75 with diagnosis of diabetes during measurement year or prior year",
        "numerator_criteria": "Multiple sub-measures: HbA1c testing, HbA1c control (<8%), retinal eye exam, nephropathy monitoring, BP control (<140/90)",
        "exclusions": [
            "Hospice or palliative care",
            "Gestational diabetes",
            "Steroid-induced diabetes"
        ],
        "benchmark": 0.60,
        "performance_levels": {"poor": 0.40, "fair": 0.50, "good": 0.60, "excellent": 0.70},
        "data_source": "EHR/Chart review",
        "measure_type": "Outcome/Process (composite)"
    },
    "CCB": {
        "measure_id": "CCB",
        "name": "Childhood Immunization Status",
        "description": "Children who received recommended vaccines by age 2",
        "domain": "Immunization",
        "population": "Children turning 2 during measurement year",
        "denominator_criteria": "Children who turn 2 years old during measurement year, continuously enrolled",
        "numerator_criteria": "DTaP (4 doses), IPV (3 doses), MMR (1 dose), Hib (3 doses), Hep B (3 doses), VZV (1 dose), PCV (4 doses), Hep A (2 doses), RV (2-3 doses), Influenza (2 doses)",
        "exclusions": [
            "Enzyme deficiency or contraindication to specific vaccine",
            "Documented allergy/anaphylaxis to vaccine",
            "Hospice care"
        ],
        "benchmark": 0.75,
        "performance_levels": {"poor": 0.55, "fair": 0.65, "good": 0.75, "excellent": 0.85},
        "data_source": "Immunization registry or EHR",
        "measure_type": "Process"
    },
    "W30": {
        "measure_id": "W30",
        "name": "Breast Cancer Screening",
        "description": "Women 50-74 who had mammography within 2 years",
        "domain": "Cancer Screening",
        "population": "Women 50-74",
        "denominator_criteria": "Women 50-74 continuously enrolled during measurement year and prior year",
        "numerator_criteria": "Mammography within 2 years (screening or diagnostic)",
        "exclusions": [
            "Bilateral mastectomy",
            "Hospice or palliative care"
        ],
        "benchmark": 0.70,
        "performance_levels": {"poor": 0.50, "fair": 0.60, "good": 0.70, "excellent": 0.80},
        "data_source": "Claims or EHR",
        "measure_type": "Process"
    },
    "PCS": {
        "measure_id": "PCS",
        "name": "Pneumococcal Vaccination Status for Older Adults",
        "description": "Adults 65+ who received pneumococcal vaccination",
        "domain": "Immunization",
        "population": "Adults 65+",
        "denominator_criteria": "Adults 65+ continuously enrolled during measurement year",
        "numerator_criteria": "Pneumococcal vaccination (PCV20 or PCV15 + PPSV23 sequence) ever received",
        "exclusions": [
            "Documented allergy/anaphylaxis to pneumococcal vaccine",
            "Hospice or palliative care"
        ],
        "benchmark": 0.70,
        "performance_levels": {"poor": 0.50, "fair": 0.60, "good": 0.70, "excellent": 0.80},
        "data_source": "Claims or EHR",
        "measure_type": "Process"
    },
    "SPC": {
        "measure_id": "SPC",
        "name": "Statin Therapy for Patients with Cardiovascular Disease",
        "description": "Patients 20-75 with clinical ASCVD who received statin therapy",
        "domain": "Cardiovascular",
        "population": "Adults 20-75 with ASCVD",
        "denominator_criteria": "Patients 20-75 with ASCVD diagnosis during measurement year or prior year",
        "numerator_criteria": "Received or active on statin therapy during measurement year",
        "exclusions": [
            "Statin-associated muscle symptoms with documented intolerance",
            "Hospice or palliative care",
            "Cirrhosis or active liver disease",
            "Pregnancy or fertility treatment"
        ],
        "benchmark": 0.75,
        "performance_levels": {"poor": 0.55, "fair": 0.65, "good": 0.75, "excellent": 0.85},
        "data_source": "Claims or EHR",
        "measure_type": "Process"
    },
    "MRP": {
        "measure_id": "MRP",
        "name": "Medication Reconciliation Post-Discharge",
        "description": "Patients discharged from inpatient setting who received medication reconciliation",
        "domain": "Medication Management",
        "population": "Patients discharged from acute inpatient stay",
        "denominator_criteria": "Patients discharged from acute inpatient stay during measurement year",
        "numerator_criteria": "Medication reconciliation performed within 30 days of discharge",
        "exclusions": [
            "Hospice or palliative care",
            "Deceased within 30 days of discharge"
        ],
        "benchmark": 0.70,
        "performance_levels": {"poor": 0.40, "fair": 0.55, "good": 0.70, "excellent": 0.85},
        "data_source": "EHR/Chart review",
        "measure_type": "Process"
    },
    "AWC": {
        "measure_id": "AWC",
        "name": "Adolescent Well-Care Visits",
        "description": "Adolescents 12-21 who had at least one well-care visit",
        "domain": "Access/Prevention",
        "population": "Adolescents 12-21",
        "denominator_criteria": "Adolescents 12-21 continuously enrolled during measurement year",
        "numerator_criteria": "At least one well-care visit with a PCP or OB/GYN during measurement year",
        "exclusions": [],
        "benchmark": 0.50,
        "performance_levels": {"poor": 0.30, "fair": 0.40, "good": 0.50, "excellent": 0.60},
        "data_source": "Claims",
        "measure_type": "Process"
    },
    "AMR": {
        "measure_id": "AMR",
        "name": "Antidepressant Medication Management",
        "description": "Patients with new antidepressant prescription who remained on medication",
        "domain": "Mental Health",
        "population": "Patients 18+ newly prescribed antidepressant",
        "denominator_criteria": "Patients 18+ with new antidepressant prescription (no antidepressant use in prior 105 days)",
        "numerator_criteria": "Two sub-measures: effective acute phase (6 months) and effective continuation phase (12 months)",
        "exclusions": [
            "Hospice or palliative care",
            "Dementia diagnosis"
        ],
        "benchmark": 0.60,
        "performance_levels": {"poor": 0.40, "fair": 0.50, "good": 0.60, "excellent": 0.70},
        "data_source": "Claims",
        "measure_type": "Process"
    },
    "AAP": {
        "measure_id": "AAP",
        "name": "Well-Child Visits in the First 30 Months of Life",
        "description": "Children with well-child visits in first 30 months",
        "domain": "Access/Prevention",
        "population": "Children 0-30 months",
        "denominator_criteria": "Children who turned 15 months or 30 months during measurement year",
        "numerator_criteria": "6 or more well-child visits by 15 months; 2 or more well-child visits between 15-30 months",
        "exclusions": [
            "Hospice or palliative care"
        ],
        "benchmark": 0.70,
        "performance_levels": {"poor": 0.50, "fair": 0.60, "good": 0.70, "excellent": 0.80},
        "data_source": "Claims",
        "measure_type": "Process"
    },
    "FVA": {
        "measure_id": "FVA",
        "name": "Flu Vaccinations for Adults Ages 18-64",
        "description": "Adults 18-64 who received influenza vaccination",
        "domain": "Immunization",
        "population": "Adults 18-64",
        "denominator_criteria": "Adults 18-64 continuously enrolled during measurement year",
        "numerator_criteria": "Influenza vaccination received during measurement year (July-June flu season)",
        "exclusions": [
            "Documented allergy/anaphylaxis to influenza vaccine",
            "Hospice or palliative care",
            "Guillain-Barre syndrome within 6 weeks of prior flu vaccine"
        ],
        "benchmark": 0.60,
        "performance_levels": {"poor": 0.40, "fair": 0.50, "good": 0.60, "excellent": 0.70},
        "data_source": "Claims or EHR",
        "measure_type": "Process"
    },
    "PPV": {
        "measure_id": "PPV",
        "name": "Postpartum Care",
        "description": "Women who completed postpartum visit within 7-84 days of delivery",
        "domain": "Maternal Health",
        "population": "Women who delivered a live birth",
        "denominator_criteria": "Women who delivered a live birth during measurement year",
        "numerator_criteria": "Postpartum visit within 7-84 days after delivery including assessment and care plan",
        "exclusions": [
            "Fetal death without live birth delivery"
        ],
        "benchmark": 0.80,
        "performance_levels": {"poor": 0.60, "fair": 0.70, "good": 0.80, "excellent": 0.90},
        "data_source": "Claims",
        "measure_type": "Process"
    },
    "LBP": {
        "measure_id": "LBP",
        "name": "Avoidance of Antibiotics for Acute Bronchitis/Bronchiolitis",
        "description": "Adults with acute bronchitis not prescribed antibiotics",
        "domain": "Appropriate Use",
        "population": "Adults 18-64 with acute bronchitis",
        "denominator_criteria": "Adults 18-64 with acute bronchitis diagnosis and no competing diagnosis",
        "numerator_criteria": "No antibiotic prescription filled within 30 days of diagnosis",
        "exclusions": [
            "Competing diagnosis requiring antibiotics (pneumonia, COPD exacerbation, etc.)",
            "Immunocompromised patients"
        ],
        "benchmark": 0.35,
        "performance_levels": {"poor": 0.15, "fair": 0.25, "good": 0.35, "excellent": 0.50},
        "data_source": "Claims",
        "measure_type": "Process (overuse)"
    },
    "CAA": {
        "measure_id": "CAA",
        "name": "Cervical Cancer Screening",
        "description": "Women 21-65 screened for cervical cancer",
        "domain": "Cancer Screening",
        "population": "Women 21-65",
        "denominator_criteria": "Women 21-65 continuously enrolled during measurement year",
        "numerator_criteria": "Pap smear within 3 years (age 21-29) or Pap + HPV co-testing within 5 years (age 30-65)",
        "exclusions": [
            "Hysterectomy (cervical)",
            "Hospice or palliative care"
        ],
        "benchmark": 0.65,
        "performance_levels": {"poor": 0.45, "fair": 0.55, "good": 0.65, "excellent": 0.75},
        "data_source": "Claims or EHR",
        "measure_type": "Process"
    },
}

# MIPS Quality Measures (Merit-based Incentive Payment System)
MIPS_MEASURES: Dict[str, Dict[str, Any]] = {
    "MIPS-236": {
        "measure_id": "MIPS-236",
        "name": "Controlling High Blood Pressure",
        "description": "Percentage of patients 18-85 with hypertension whose BP was adequately controlled",
        "category": "Quality",
        "measure_type": "Outcome",
        "high_priority": True,
        "specialty": "Internal Medicine, Family Medicine, Cardiology",
        "benchmark_7": 0.602,
        "benchmark_decile_10": 0.828,
        "data_submission_methods": ["EHR", "Registry", "QCDR", "Claims"],
        "weight": 1.0,
        "notes": "Same as HEDIS HBD measure; high-priority outcome measure"
    },
    "MIPS-110": {
        "measure_id": "MIPS-110",
        "name": "Preventive Care and Screening: Influenza Immunization",
        "description": "Percentage of patients 6 months+ who received influenza immunization",
        "category": "Quality",
        "measure_type": "Process",
        "high_priority": False,
        "specialty": "All specialties",
        "benchmark_7": 0.646,
        "benchmark_decile_10": 0.889,
        "data_submission_methods": ["EHR", "Registry", "QCDR", "Claims"],
        "weight": 1.0,
        "notes": "Most commonly reported MIPS measure"
    },
    "MIPS-130": {
        "measure_id": "MIPS-130",
        "name": "Documentation of Current Medications in the Medical Record",
        "description": "Percentage of visits with documentation of current medications",
        "category": "Quality",
        "measure_type": "Process",
        "high_priority": False,
        "specialty": "All specialties",
        "benchmark_7": 0.941,
        "benchmark_decile_10": 1.000,
        "data_submission_methods": ["EHR", "Registry", "QCDR"],
        "weight": 1.0,
        "notes": "High benchmark; most providers perform well on this measure"
    },
    "MIPS-134": {
        "measure_id": "MIPS-134",
        "name": "Preventive Care and Screening: Screening for Depression and Follow-Up Plan",
        "description": "Patients screened for depression with follow-up documented",
        "category": "Quality",
        "measure_type": "Process",
        "high_priority": True,
        "specialty": "Internal Medicine, Family Medicine, Psychiatry, OB/GYN",
        "benchmark_7": 0.504,
        "benchmark_decile_10": 0.889,
        "data_submission_methods": ["EHR", "Registry", "QCDR"],
        "weight": 1.0,
        "notes": "High-priority process measure; screening plus follow-up required"
    },
    "MIPS-238": {
        "measure_id": "MIPS-238",
        "name": "Use of High-Risk Medications in Older Adults",
        "description": "Percentage of adults 65+ prescribed high-risk medications (Beers criteria)",
        "category": "Quality",
        "measure_type": "Outcome",
        "high_priority": True,
        "specialty": "Internal Medicine, Family Medicine, Geriatrics",
        "benchmark_7": 0.095,
        "benchmark_decile_10": 0.033,
        "notes": "Lower is better; measures avoidance of high-risk medications in elderly"
    },
    "MIPS-046": {
        "measure_id": "MIPS-046",
        "name": "Medication Reconciliation",
        "description": "Percentage of discharged patients with medication reconciliation performed",
        "category": "Quality",
        "measure_type": "Process",
        "high_priority": False,
        "specialty": "Internal Medicine, Family Medicine, Hospitalists",
        "benchmark_7": 0.807,
        "benchmark_decile_10": 0.991,
        "data_submission_methods": ["EHR", "Registry"],
        "weight": 1.0,
        "notes": "Similar to HEDIS MRP measure"
    },
    "MIPS-438": {
        "measure_id": "MIPS-438",
        "name": "Statin Therapy for the Prevention and Treatment of Cardiovascular Disease",
        "description": "Percentage of patients with ASCVD or diabetes who are prescribed statin therapy",
        "category": "Quality",
        "measure_type": "Process",
        "high_priority": True,
        "specialty": "Internal Medicine, Family Medicine, Cardiology, Endocrinology",
        "benchmark_7": 0.692,
        "benchmark_decile_10": 0.890,
        "data_submission_methods": ["EHR", "Registry", "QCDR"],
        "weight": 1.0,
        "notes": "Similar to HEDIS SPC measure; high-priority process measure"
    },
    "MIPS-318": {
        "measure_id": "MIPS-318",
        "name": "Falls: Screening for Future Fall Risk",
        "description": "Percentage of patients 65+ screened for future fall risk during measurement period",
        "category": "Quality",
        "measure_type": "Process",
        "high_priority": True,
        "specialty": "Internal Medicine, Family Medicine, Geriatrics",
        "benchmark_7": 0.754,
        "benchmark_decile_10": 0.973,
        "data_submission_methods": ["EHR", "Registry", "QCDR"],
        "weight": 1.0,
        "notes": "High-priority process measure for geriatric populations"
    },
    "MIPS-398": {
        "measure_id": "MIPS-398",
        "name": "Asthma: Pharmacologic Therapy for Persistent Asthma",
        "description": "Percentage of patients with persistent asthma prescribed long-term control therapy",
        "category": "Quality",
        "measure_type": "Process",
        "high_priority": False,
        "specialty": "Pulmonology, Allergy/Immunology, Family Medicine",
        "benchmark_7": 0.740,
        "benchmark_decile_10": 0.940,
        "data_submission_methods": ["EHR", "Registry", "QCDR", "Claims"],
        "weight": 1.0,
        "notes": "Important for asthma management quality assessment"
    },
    "MIPS-475": {
        "measure_id": "MIPS-475",
        "name": "Advanced Care Planning",
        "description": "Percentage of patients with advance care planning documented or billed",
        "category": "Quality",
        "measure_type": "Process",
        "high_priority": True,
        "specialty": "Internal Medicine, Family Medicine, Geriatrics, Oncology",
        "benchmark_7": 0.408,
        "benchmark_decile_10": 0.761,
        "data_submission_methods": ["EHR", "Registry", "QCDR", "Claims"],
        "weight": 1.0,
        "notes": "High-priority measure; CPT 99497/99498 for billing"
    },
}

# CMS Stars Measure Weights (Medicare Advantage Star Ratings)
STARS_MEASURES: Dict[str, Dict[str, Any]] = {
    "C01": {
        "measure_id": "C01",
        "name": "Breast Cancer Screening",
        "domain": "Prevention/Screening",
        "weight": "Triple-weighted",
        "weight_value": 3,
        "star_thresholds": {1: 0.44, 2: 0.52, 3: 0.60, 4: 0.68, 5: 0.76},
        "data_source": "HEDIS"
    },
    "C02": {
        "measure_id": "C02",
        "name": "Colorectal Cancer Screening",
        "domain": "Prevention/Screening",
        "weight": "Triple-weighted",
        "weight_value": 3,
        "star_thresholds": {1: 0.36, 2: 0.44, 3: 0.52, 4: 0.62, 5: 0.72},
        "data_source": "HEDIS"
    },
    "C05": {
        "measure_id": "C05",
        "name": "Controlling High Blood Pressure",
        "domain": "Chronic Disease Management",
        "weight": "Triple-weighted",
        "weight_value": 3,
        "star_thresholds": {1: 0.44, 2: 0.52, 3: 0.60, 4: 0.70, 5: 0.80},
        "data_source": "HEDIS"
    },
    "C08": {
        "measure_id": "C08",
        "name": "Diabetes Care - HbA1c Control (<8%)",
        "domain": "Chronic Disease Management",
        "weight": "Triple-weighted",
        "weight_value": 3,
        "star_thresholds": {1: 0.40, 2: 0.48, 3: 0.56, 4: 0.64, 5: 0.72},
        "data_source": "HEDIS"
    },
    "C11": {
        "measure_id": "C11",
        "name": "Statin Use in Persons with Diabetes",
        "domain": "Medication Management",
        "weight": "Double-weighted",
        "weight_value": 2,
        "star_thresholds": {1: 0.58, 2: 0.66, 3: 0.74, 4: 0.80, 5: 0.86},
        "data_source": "HEDIS"
    },
    "C13": {
        "measure_id": "C13",
        "name": "Statin Adherence for Diabetes",
        "domain": "Medication Adherence",
        "weight": "Triple-weighted",
        "weight_value": 3,
        "star_thresholds": {1: 0.64, 2: 0.72, 3: 0.78, 4: 0.84, 5: 0.88},
        "data_source": "HEDIS/PDE"
    },
    "C15": {
        "measure_id": "C15",
        "name": "RAS Antagonists Adherence",
        "domain": "Medication Adherence",
        "weight": "Triple-weighted",
        "weight_value": 3,
        "star_thresholds": {1: 0.66, 2: 0.74, 3: 0.80, 4: 0.86, 5: 0.90},
        "data_source": "HEDIS/PDE"
    },
    "D07": {
        "measure_id": "D07",
        "name": "Member Experience: Getting Needed Care",
        "domain": "Member Experience",
        "weight": "Quadruple-weighted",
        "weight_value": 4,
        "star_thresholds": {1: 0.55, 2: 0.65, 3: 0.75, 4: 0.85, 5: 0.90},
        "data_source": "CAHPS"
    },
    "D08": {
        "measure_id": "D08",
        "name": "Member Experience: Care Coordination",
        "domain": "Member Experience",
        "weight": "Quadruple-weighted",
        "weight_value": 4,
        "star_thresholds": {1: 0.50, 2: 0.60, 3: 0.70, 4: 0.80, 5: 0.88},
        "data_source": "CAHPS"
    },
    "E02": {
        "measure_id": "E02",
        "name": "Plan All-Cause Readmissions",
        "domain": "Outcomes",
        "weight": "Triple-weighted",
        "weight_value": 3,
        "star_thresholds": {1: 0.19, 2: 0.17, 3: 0.15, 4: 0.13, 5: 0.11},
        "data_source": "Claims (lower is better)"
    },
}


@skill(name="quality_tracker", category="healthcare")
class QualityTrackerSkill(AetheraSkill):
    """
    Track HEDIS, MIPS, and Stars quality measures.
    """

    @property
    def name(self) -> str:
        return "quality_tracker"

    @property
    def description(self) -> str:
        return "Get HEDIS/MIPS/Stars measure specifications, calculate rates, identify quality gaps"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get_measure_specs", "calculate_rate", "identify_gaps", "list_measures", "get_star_thresholds"],
                    "description": "Action: get_measure_specs, calculate_rate, identify_gaps, list_measures, get_star_thresholds"
                },
                "program": {
                    "type": "string",
                    "enum": ["hedis", "mips", "stars"],
                    "description": "Quality program (HEDIS, MIPS, or Stars)"
                },
                "measure_id": {
                    "type": "string",
                    "description": "Measure ID to look up (e.g., HBD, CBC, MIPS-236, C05)"
                },
                "numerator_count": {
                    "type": "integer",
                    "description": "Numerator count for rate calculation"
                },
                "denominator_count": {
                    "type": "integer",
                    "description": "Denominator count for rate calculation"
                },
                "current_rates": {
                    "type": "object",
                    "description": "Dict of measure_id -> current rate (0-1) for gap analysis"
                }
            },
            "required": ["action", "program"]
        }

    @property
    def requires_phi_protection(self) -> bool:
        return True

    @property
    def examples(self) -> list:
        return [
            {"input": {"action": "get_measure_specs", "program": "hedis", "measure_id": "HBD"}},
            {"input": {"action": "calculate_rate", "program": "hedis", "numerator_count": 750, "denominator_count": 1000}},
            {"input": {"action": "identify_gaps", "program": "hedis", "current_rates": {"HBD": 0.55, "CBC": 0.48, "CDC": 0.42}}},
            {"input": {"action": "list_measures", "program": "mips"}},
        ]

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "list_measures")
        program = kwargs.get("program", "hedis")

        try:
            measure_db = self._get_measure_db(program)

            if action == "get_measure_specs":
                measure_id = kwargs.get("measure_id", "")
                if not measure_id:
                    return SkillResult(success=False, error="Measure ID is required for get_measure_specs")
                result = self._get_measure_specs(measure_id, measure_db, program)

            elif action == "calculate_rate":
                numerator = kwargs.get("numerator_count", 0)
                denominator = kwargs.get("denominator_count", 0)
                measure_id = kwargs.get("measure_id", "")
                result = self._calculate_rate(numerator, denominator, measure_id, measure_db, program)

            elif action == "identify_gaps":
                current_rates = kwargs.get("current_rates", {})
                result = self._identify_gaps(current_rates, measure_db, program)

            elif action == "list_measures":
                result = self._list_measures(measure_db, program)

            elif action == "get_star_thresholds":
                measure_id = kwargs.get("measure_id", "")
                if program != "stars":
                    return SkillResult(success=False, error="Star thresholds only available for 'stars' program")
                result = self._get_star_thresholds(measure_id)

            else:
                return SkillResult(success=False, error=f"Unknown action: {action}")

            return SkillResult(success=True, data=result)

        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _get_measure_db(self, program: str) -> Dict[str, Dict[str, Any]]:
        """Get the measure database for the specified program."""
        if program == "hedis":
            return HEDIS_MEASURES
        elif program == "mips":
            return MIPS_MEASURES
        elif program == "stars":
            return STARS_MEASURES
        return {}

    def _get_measure_specs(self, measure_id: str, measure_db: Dict, program: str) -> Dict[str, Any]:
        """Get full specification for a quality measure."""
        measure = measure_db.get(measure_id.upper())
        if not measure:
            available = list(measure_db.keys())
            return {
                "measure_id": measure_id,
                "error": f"Measure {measure_id} not found in {program}",
                "available_measures": available
            }
        return {
            "program": program,
            **measure
        }

    def _calculate_rate(self, numerator: int, denominator: int, measure_id: str,
                        measure_db: Dict, program: str) -> Dict[str, Any]:
        """Calculate quality measure rate and compare to benchmark."""
        if denominator == 0:
            return {
                "error": "Denominator cannot be zero",
                "numerator": numerator,
                "denominator": denominator
            }

        rate = numerator / denominator
        result = {
            "numerator": numerator,
            "denominator": denominator,
            "rate": round(rate, 4),
            "rate_percentage": f"{round(rate * 100, 1)}%"
        }

        # Compare to benchmark if measure provided
        if measure_id:
            measure = measure_db.get(measure_id.upper())
            if measure:
                benchmark = measure.get("benchmark", measure.get("benchmark_7", None))
                if benchmark is not None:
                    result["benchmark"] = benchmark
                    result["meets_benchmark"] = rate >= benchmark
                    result["benchmark_gap"] = round(max(0, benchmark - rate), 4)
                    result["patients_needed_for_benchmark"] = max(0, int((benchmark * denominator) - numerator) + 1)

                perf_levels = measure.get("performance_levels", {})
                if perf_levels:
                    performance = "poor"
                    for level, threshold in sorted(perf_levels.items(), key=lambda x: x[1]):
                        if rate >= threshold:
                            performance = level
                    result["performance_level"] = performance

                if program == "stars":
                    thresholds = measure.get("star_thresholds", {})
                    if thresholds:
                        star_rating = 1
                        for star, threshold in sorted(thresholds.items()):
                            meets = rate >= threshold if measure_id != "E02" else rate <= threshold
                            if meets:
                                star_rating = star
                        result["star_rating"] = star_rating

        return result

    def _identify_gaps(self, current_rates: Dict[str, float], measure_db: Dict, program: str) -> Dict[str, Any]:
        """Identify quality measure gaps based on current rates vs benchmarks."""
        gaps = []
        met_measures = []

        for measure_id, current_rate in current_rates.items():
            measure = measure_db.get(measure_id.upper())
            if not measure:
                gaps.append({
                    "measure_id": measure_id,
                    "error": f"Measure {measure_id} not found in {program}"
                })
                continue

            benchmark = measure.get("benchmark", measure.get("benchmark_7", None))
            perf_levels = measure.get("performance_levels", {})

            if benchmark is not None:
                gap = max(0, round(benchmark - current_rate, 4))
                meets = current_rate >= benchmark

                performance = "poor"
                if perf_levels:
                    for level, threshold in sorted(perf_levels.items(), key=lambda x: x[1]):
                        if current_rate >= threshold:
                            performance = level

                gap_info = {
                    "measure_id": measure_id,
                    "name": measure.get("name", ""),
                    "current_rate": round(current_rate, 4),
                    "current_percentage": f"{round(current_rate * 100, 1)}%",
                    "benchmark": benchmark,
                    "benchmark_percentage": f"{round(benchmark * 100, 1)}%",
                    "meets_benchmark": meets,
                    "gap": gap,
                    "performance_level": performance
                }

                if program == "stars":
                    thresholds = measure.get("star_thresholds", {})
                    weight = measure.get("weight_value", 1)
                    star_rating = 1
                    for star, threshold in sorted(thresholds.items()):
                        is_readmission = measure_id.upper() == "E02"
                        meets_threshold = current_rate <= threshold if is_readmission else current_rate >= threshold
                        if meets_threshold:
                            star_rating = star
                    gap_info["star_rating"] = star_rating
                    gap_info["weight"] = weight
                    gap_info["weighted_gap"] = gap * weight

                if meets:
                    met_measures.append(gap_info)
                else:
                    gaps.append(gap_info)

        # Sort gaps by size (largest first)
        gaps.sort(key=lambda x: x.get("weighted_gap", x.get("gap", 0)), reverse=True)

        return {
            "program": program,
            "total_measures_assessed": len(current_rates),
            "measures_meeting_benchmark": len(met_measures),
            "measures_below_benchmark": len([g for g in gaps if "error" not in g]),
            "gaps": gaps,
            "met_measures": met_measures,
            "overall_compliance_rate": round(
                len(met_measures) / len(current_rates) * 100, 1
            ) if current_rates else 0
        }

    def _list_measures(self, measure_db: Dict, program: str) -> Dict[str, Any]:
        """List all available measures for a program."""
        measures = []
        for measure_id, data in measure_db.items():
            measures.append({
                "measure_id": measure_id,
                "name": data.get("name", ""),
                "domain": data.get("domain", data.get("category", "")),
                "measure_type": data.get("measure_type", ""),
                "high_priority": data.get("high_priority", None),
                "benchmark": data.get("benchmark", data.get("benchmark_7", None))
            })

        return {
            "program": program,
            "total_measures": len(measures),
            "measures": measures
        }

    def _get_star_thresholds(self, measure_id: str) -> Dict[str, Any]:
        """Get Star rating thresholds for a measure."""
        measure_id_upper = measure_id.upper()
        measure = STARS_MEASURES.get(measure_id_upper)

        if not measure:
            return {
                "measure_id": measure_id_upper,
                "error": f"Stars measure {measure_id_upper} not found",
                "available_measures": list(STARS_MEASURES.keys())
            }

        thresholds = measure.get("star_thresholds", {})
        threshold_list = []
        for star, value in sorted(thresholds.items()):
            threshold_list.append({
                "star": star,
                "threshold": value,
                "threshold_percentage": f"{round(value * 100, 1)}%",
                "direction": "lower is better" if measure_id_upper == "E02" else "higher is better"
            })

        return {
            "measure_id": measure_id_upper,
            "name": measure["name"],
            "domain": measure["domain"],
            "weight": measure["weight"],
            "weight_value": measure["weight_value"],
            "data_source": measure["data_source"],
            "thresholds": threshold_list
        }