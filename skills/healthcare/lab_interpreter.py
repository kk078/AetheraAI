"""
Aethera AI - Lab Interpreter Skill

Lab value interpretation with normal ranges, clinical significance,
and trend analysis. Contains common lab tests including CBC, BMP,
CMP, thyroid, HbA1c, lipids, and more. Supports interpret value,
compare to range, and trend analysis.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from skills.skill_base import AetheraSkill, SkillResult, skill


@skill(name="lab_interpreter", category="healthcare")
class LabInterpreterSkill(AetheraSkill):
    """
    Lab value interpretation and trend analysis.
    """

    @property
    def name(self) -> str:
        return "lab_interpreter"

    @property
    def description(self) -> str:
        return "Interpret lab values: compare to normal ranges, identify abnormalities, trend analysis over time"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["interpret", "compare_to_range", "trend_analysis"],
                    "description": "Action: interpret (full interpretation), compare_to_range (simple range check), trend_analysis (multi-value trend)"
                },
                "test_name": {
                    "type": "string",
                    "description": "Lab test name (e.g., 'hemoglobin', 'sodium', 'TSH')"
                },
                "value": {
                    "type": "number",
                    "description": "Lab test result value"
                },
                "unit": {
                    "type": "string",
                    "description": "Unit of measurement (e.g., 'mg/dL', 'mEq/L')"
                },
                "patient_age": {
                    "type": "integer",
                    "description": "Patient age in years"
                },
                "patient_sex": {
                    "type": "string",
                    "enum": ["male", "female"],
                    "description": "Patient biological sex for sex-specific ranges"
                },
                "historical_values": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string", "description": "Date (YYYY-MM-DD)"},
                            "value": {"type": "number", "description": "Lab value on that date"}
                        }
                    },
                    "description": "Historical values for trend analysis (date + value pairs)"
                }
            },
            "required": ["action", "test_name"]
        }

    @property
    def requires_phi_protection(self) -> bool:
        return True

    @property
    def examples(self) -> list:
        return [
            {"input": {"action": "interpret", "test_name": "hemoglobin", "value": 10.5, "patient_sex": "female"}},
            {"input": {"action": "compare_to_range", "test_name": "sodium", "value": 128}},
            {"input": {"action": "trend_analysis", "test_name": "HbA1c", "historical_values": [{"date": "2024-01-15", "value": 8.2}, {"date": "2024-04-15", "value": 7.8}, {"date": "2024-07-15", "value": 7.1}]}}
        ]

    # --- Lab test database with normal ranges ---
    # Ranges are adult defaults unless otherwise specified
    LAB_TESTS: Dict[str, Dict[str, Any]] = {
        # CBC
        "wbc": {
            "full_name": "White Blood Cell Count",
            "category": "CBC",
            "unit": "x10^3/uL",
            "normal_range": {"low": 4.5, "high": 11.0},
            "male_range": {"low": 4.5, "high": 11.0},
            "female_range": {"low": 4.5, "high": 11.0},
            "pediatric_range": {"low": 5.0, "high": 13.0},
            "critical_low": 2.0,
            "critical_high": 30.0,
            "low_interpretation": "Leukopenia - may indicate viral infection, bone marrow suppression, autoimmune disease, medication effect, or nutritional deficiency",
            "high_interpretation": "Leukocytosis - may indicate bacterial infection, inflammation, stress response, leukemia, or medication effect (e.g., corticosteroids)",
            "critical_low_interpretation": "Severe leukopenia - high risk of infection. Requires urgent clinical evaluation.",
            "critical_high_interpretation": "Marked leukocytosis - consider leukemia, severe infection, or leukemoid reaction. Urgent evaluation required.",
            "common_causes_low": ["Viral infection", "Medications (chemotherapy, immunosuppressants)", "Aplastic anemia", "Autoimmune disease", "Nutritional deficiency (B12, folate)", "Radiation exposure"],
            "common_causes_high": ["Bacterial infection", "Inflammation", "Stress (physical/emotional)", "Corticosteroids", "Leukemia", "Tissue necrosis", "Hemolytic anemia"],
            "follow_up": ["CBC with differential", "Peripheral blood smear", "Reticulocyte count if anemia present"]
        },
        "hemoglobin": {
            "full_name": "Hemoglobin",
            "category": "CBC",
            "unit": "g/dL",
            "normal_range": {"low": 12.0, "high": 16.0},
            "male_range": {"low": 13.5, "high": 17.5},
            "female_range": {"low": 12.0, "high": 15.5},
            "pediatric_range": {"low": 11.0, "high": 16.0},
            "critical_low": 7.0,
            "critical_high": 20.0,
            "low_interpretation": "Anemia - further evaluation needed to determine etiology (iron deficiency, B12 deficiency, chronic disease, hemolysis, bleeding, bone marrow failure)",
            "high_interpretation": "Polycythemia or hemoconcentration - may indicate polycythemia vera, chronic hypoxia, dehydration, high altitude, or EPO-producing tumors",
            "critical_low_interpretation": "Severe anemia - may require transfusion. Assess for active bleeding, hemolysis, or marrow failure.",
            "critical_high_interpretation": "Severe polycythemia - risk of thrombosis. Evaluate for polycythemia vera, chronic hypoxia.",
            "common_causes_low": ["Iron deficiency", "Vitamin B12/folate deficiency", "Chronic disease", "Acute/chronic blood loss", "Hemolysis", "Bone marrow failure", "Kidney disease (low EPO)"],
            "common_causes_high": ["Polycythemia vera", "Chronic hypoxia (COPD, smoking)", "Dehydration", "High altitude", "EPO-producing tumors", "Testosterone therapy"],
            "follow_up": ["MCV", "RDW", "Iron studies (ferritin, TIBC, iron)", "Reticulocyte count", "B12/folate levels", "Stool guaiac if GI blood loss suspected"]
        },
        "hematocrit": {
            "full_name": "Hematocrit",
            "category": "CBC",
            "unit": "%",
            "normal_range": {"low": 36.0, "high": 46.0},
            "male_range": {"low": 41.0, "high": 50.0},
            "female_range": {"low": 36.0, "high": 44.0},
            "pediatric_range": {"low": 32.0, "high": 44.0},
            "critical_low": 21.0,
            "critical_high": 60.0,
            "low_interpretation": "Anemia - reflects reduced red cell mass. Correlates with hemoglobin (approximately 3x hemoglobin in g/dL)",
            "high_interpretation": "Elevated hematocrit - polycythemia or hemoconcentration. See hemoglobin interpretation.",
            "critical_low_interpretation": "Severe anemia - consider transfusion if symptomatic.",
            "critical_high_interpretation": "Severe polycythemia - risk of hyperviscosity and thrombosis.",
            "common_causes_low": ["See hemoglobin causes"],
            "common_causes_high": ["See hemoglobin causes"],
            "follow_up": ["See hemoglobin follow-up"]
        },
        "platelets": {
            "full_name": "Platelet Count",
            "category": "CBC",
            "unit": "x10^3/uL",
            "normal_range": {"low": 150, "high": 400},
            "male_range": {"low": 150, "high": 400},
            "female_range": {"low": 150, "high": 400},
            "pediatric_range": {"low": 150, "high": 400},
            "critical_low": 50,
            "critical_high": 1000,
            "low_interpretation": "Thrombocytopenia - risk of bleeding increases. Causes include ITP, TTP/HUS, DIC, splenic sequestration, bone marrow failure, medications, and infection",
            "high_interpretation": "Thrombocytosis - may be reactive (infection, inflammation, iron deficiency) or primary (myeloproliferative neoplasm)",
            "critical_low_interpretation": "Severe thrombocytopenia - high bleeding risk. Avoid IM injections. Consider platelet transfusion if bleeding or count < 10k.",
            "critical_high_interpretation": "Extreme thrombocytosis - risk of both thrombosis and bleeding (acquired VWD). Evaluate for myeloproliferative neoplasm.",
            "common_causes_low": ["ITP", "DIC", "TTP/HUS", "Medications (heparin, H2 blockers, antibiotics)", "Viral infection", "Bone marrow failure", "Splenic sequestration", "Sepsis"],
            "common_causes_high": ["Reactive (infection, inflammation)", "Iron deficiency", "Post-splenectomy", "Myeloproliferative neoplasms", "Malignancy", "Post-hemorrhage"],
            "follow_up": ["Peripheral smear", "PT/PTT", "D-dimer and fibrinogen (if DIC suspected)", "Heparin-induced antibody (if HIT suspected)", "Bone marrow biopsy (if primary suspected)"]
        },
        "mcv": {
            "full_name": "Mean Corpuscular Volume",
            "category": "CBC",
            "unit": "fL",
            "normal_range": {"low": 80, "high": 100},
            "male_range": {"low": 80, "high": 100},
            "female_range": {"low": 80, "high": 100},
            "pediatric_range": {"low": 75, "high": 90},
            "critical_low": 60,
            "critical_high": 130,
            "low_interpretation": "Microcytic anemia - most commonly iron deficiency, thalassemia, or anemia of chronic disease",
            "high_interpretation": "Macrocytic anemia - consider B12 deficiency, folate deficiency, hypothyroidism, liver disease, medications (methotrexate, AZT), or MDS",
            "critical_low_interpretation": "Severe microcytosis - strongly consider thalassemia or severe iron deficiency.",
            "critical_high_interpretation": "Severe macrocytosis - evaluate urgently for B12 deficiency (neurologic risk) or MDS.",
            "common_causes_low": ["Iron deficiency", "Thalassemia", "Anemia of chronic disease", "Sideroblastic anemia", "Lead poisoning"],
            "common_causes_high": ["B12 deficiency", "Folate deficiency", "Hypothyroidism", "Liver disease", "Alcoholism", "MDS", "Medications (methotrexate, hydroxyurea, AZT)"],
            "follow_up": ["Iron studies", "Hemoglobin electrophoresis (if thalassemia suspected)", "B12 and folate levels", "TSH", "Reticulocyte count"]
        },
        # BMP / CMP
        "sodium": {
            "full_name": "Sodium",
            "category": "BMP",
            "unit": "mEq/L",
            "normal_range": {"low": 135, "high": 145},
            "male_range": {"low": 135, "high": 145},
            "female_range": {"low": 135, "high": 145},
            "pediatric_range": {"low": 135, "high": 145},
            "critical_low": 120,
            "critical_high": 160,
            "low_interpretation": "Hyponatremia - evaluate volume status (hypovolemic, euvolemic, hypervolemic). Common causes include SIADH, diuretics, heart failure, cirrhosis, and psychogenic polydipsia",
            "high_interpretation": "Hypernatremia - usually indicates free water deficit. Causes include dehydration, diabetes insipidus, excessive sodium intake, and diuretics",
            "critical_low_interpretation": "Severe hyponatremia - risk of cerebral edema, seizures. Requires careful correction (no more than 8-10 mEq/L in 24 hours to avoid osmotic demyelination).",
            "critical_high_interpretation": "Severe hypernatremia - risk of cerebral shrinkage, hemorrhage. Requires gradual correction with free water.",
            "common_causes_low": ["SIADH", "Diuretics (thiazides)", "Heart failure", "Cirrhosis", "Psychogenic polydipsia", "Adrenal insufficiency", "Hypothyroidism", "Vomiting/diarrhea"],
            "common_causes_high": ["Dehydration", "Diabetes insipidus", "Excessive NaCl administration", "Diuretics (loop)", "Cushing syndrome", "Hyperaldosteronism", "Insensible losses (fever, burns)"],
            "follow_up": ["Serum osmolality", "Urine osmolality", "Urine sodium", "Volume status assessment", "TSH and cortisol (if euvolemic)"]
        },
        "potassium": {
            "full_name": "Potassium",
            "category": "BMP",
            "unit": "mEq/L",
            "normal_range": {"low": 3.5, "high": 5.0},
            "male_range": {"low": 3.5, "high": 5.0},
            "female_range": {"low": 3.5, "high": 5.0},
            "pediatric_range": {"low": 3.5, "high": 5.0},
            "critical_low": 2.5,
            "critical_high": 6.5,
            "low_interpretation": "Hypokalemia - causes muscle weakness, cardiac arrhythmias. Common causes include diuretics, GI losses, renal losses, and alkalosis",
            "high_interpretation": "Hyperkalemia - medical emergency. Causes include renal failure, ACE inhibitors/ARBs, potassium supplements, hemolysis, acidosis, and adrenal insufficiency",
            "critical_low_interpretation": "Severe hypokalemia - high risk of cardiac arrhythmias, respiratory failure from muscle weakness. IV potassium replacement often needed.",
            "critical_high_interpretation": "Life-threatening hyperkalemia - risk of cardiac arrest. Immediate treatment: calcium gluconate (membrane stabilizer), insulin+glucose, albuterol, kayexalate/lokelma. ECG monitoring essential.",
            "common_causes_low": ["Loop/thiazide diuretics", "Vomiting/diarrhea", "Alkalosis", "Hypomagnesemia", "Renal tubular acidosis", "Beta agonists", "Cushing syndrome"],
            "common_causes_high": ["Renal failure", "ACE inhibitors/ARBs", "Potassium supplements", "Hemolysis (pseudohyperkalemia)", "Acidosis", "Adrenal insufficiency", "NSAIDs", "Heparin", "Trimethoprim"],
            "follow_up": ["ECG", "Magnesium level", "BUN/Creatinine", "Aldosterone/renin ratio", "Arterial blood gas", "Urine potassium"]
        },
        "creatinine": {
            "full_name": "Creatinine",
            "category": "BMP",
            "unit": "mg/dL",
            "normal_range": {"low": 0.7, "high": 1.3},
            "male_range": {"low": 0.7, "high": 1.3},
            "female_range": {"low": 0.6, "high": 1.1},
            "pediatric_range": {"low": 0.2, "high": 0.7},
            "critical_low": 0.2,
            "critical_high": 5.0,
            "low_interpretation": "Low creatinine - usually not clinically significant. May indicate low muscle mass, pregnancy, or liver disease",
            "high_interpretation": "Elevated creatinine - indicates reduced renal function. Determine if acute or chronic. Calculate eGFR for staging.",
            "critical_low_interpretation": "Very low creatinine - typically reflects very low muscle mass or severe malnutrition.",
            "critical_high_interpretation": "Severe renal impairment - may require dialysis evaluation. Assess for acute kidney injury vs. end-stage renal disease.",
            "common_causes_low": ["Low muscle mass", "Pregnancy", "Liver disease (decreased production)", "Malnutrition"],
            "common_causes_high": ["Acute kidney injury", "Chronic kidney disease", "Dehydration", "Nephrotoxic medications", "Urinary obstruction", "Rhabdomyolysis", "Heart failure"],
            "follow_up": ["eGFR calculation", "BUN", "Urinalysis", "Urine protein/creatinine ratio", "Renal ultrasound", "Kidney biopsy (if indicated)"]
        },
        "bun": {
            "full_name": "Blood Urea Nitrogen",
            "category": "BMP",
            "unit": "mg/dL",
            "normal_range": {"low": 7, "high": 20},
            "male_range": {"low": 7, "high": 20},
            "female_range": {"low": 7, "high": 20},
            "pediatric_range": {"low": 5, "high": 18},
            "critical_low": 2,
            "critical_high": 100,
            "low_interpretation": "Low BUN - may indicate liver disease, malnutrition, overhydration, or pregnancy",
            "high_interpretation": "Elevated BUN - evaluate BUN/Creatinine ratio. Ratio >20 suggests prerenal cause (dehydration, GI bleed, high protein intake). Ratio <10 suggests intrinsic renal disease",
            "critical_low_interpretation": "Very low BUN - significant malnutrition or severe liver failure.",
            "critical_high_interpretation": "Markedly elevated BUN - significant renal impairment. Assess for dialysis need.",
            "common_causes_low": ["Liver disease", "Malnutrition", "Overhydration", "Pregnancy"],
            "common_causes_high": ["Renal failure", "Dehydration", "GI bleeding", "High protein diet", "Urinary obstruction", "Corticosteroids", "Heart failure"],
            "follow_up": ["Creatinine and eGFR", "BUN/Creatinine ratio", "Urinalysis", "Liver function tests"]
        },
        "glucose": {
            "full_name": "Glucose (Fasting)",
            "category": "BMP",
            "unit": "mg/dL",
            "normal_range": {"low": 70, "high": 100},
            "male_range": {"low": 70, "high": 100},
            "female_range": {"low": 70, "high": 100},
            "pediatric_range": {"low": 60, "high": 100},
            "critical_low": 40,
            "critical_high": 500,
            "low_interpretation": "Hypoglycemia - requires prompt treatment. Causes include insulin/sulfonylurea use, liver failure, sepsis, adrenal insufficiency, insulinoma",
            "high_interpretation": "Hyperglycemia - evaluate for diabetes, prediabetes, or stress hyperglycemia. Fasting 100-125 = prediabetes. Fasting >=126 = diabetes (on 2 occasions)",
            "critical_low_interpretation": "Severe hypoglycemia - risk of seizures, coma, and brain damage. Immediate IV dextrose or IM glucagon required.",
            "critical_high_interpretation": "Severe hyperglycemia - risk of HHS or DKA. Check ketones, blood gas, and osmolality. Insulin therapy likely needed.",
            "common_causes_low": ["Insulin excess", "Sulfonylureas", "Liver failure", "Sepsis", "Adrenal insufficiency", "Insulinoma", "Alcohol", "Post-gastrectomy"],
            "common_causes_high": ["Diabetes mellitus", "Stress (illness, surgery)", "Corticosteroids", "Pancreatitis", "Cushing syndrome", "Medications (atypical antipsychotics, immunosuppressants)", "Acromegaly"],
            "follow_up": ["Hemoglobin A1c", "Oral glucose tolerance test", "Fasting lipid panel", "Kidney function", "C-peptide and insulin levels (if hypoglycemia workup)"]
        },
        # CMP additions
        "alt": {
            "full_name": "Alanine Aminotransferase (ALT/SGPT)",
            "category": "CMP",
            "unit": "U/L",
            "normal_range": {"low": 7, "high": 56},
            "male_range": {"low": 7, "high": 56},
            "female_range": {"low": 7, "high": 56},
            "pediatric_range": {"low": 5, "high": 50},
            "critical_low": 0,
            "critical_high": 1000,
            "low_interpretation": "Low ALT - typically not clinically significant; may indicate vitamin B6 deficiency",
            "high_interpretation": "Elevated ALT - indicates hepatocellular injury. More specific for liver than AST. Causes include viral hepatitis, fatty liver, medications, alcohol, autoimmune hepatitis",
            "critical_low_interpretation": "Not clinically significant.",
            "critical_high_interpretation": "Markedly elevated ALT - suggests acute hepatocellular injury (viral hepatitis, ischemia, drug-induced liver injury). Urgent evaluation.",
            "common_causes_low": ["Vitamin B6 deficiency", "End-stage liver disease (loss of functional hepatocytes)"],
            "common_causes_high": ["Viral hepatitis", "NAFLD/NASH", "Alcohol", "Drug-induced liver injury", "Autoimmune hepatitis", "Ischemic hepatitis", "Wilson disease", "Hemochromatosis"],
            "follow_up": ["AST", "Alkaline phosphatase", "Bilirubin", "Hepatitis panel", "Liver ultrasound", "PT/INR"]
        },
        "ast": {
            "full_name": "Aspartate Aminotransferase (AST/SGOT)",
            "category": "CMP",
            "unit": "U/L",
            "normal_range": {"low": 10, "high": 40},
            "male_range": {"low": 10, "high": 40},
            "female_range": {"low": 10, "high": 40},
            "pediatric_range": {"low": 8, "high": 40},
            "critical_low": 0,
            "critical_high": 1000,
            "low_interpretation": "Low AST - typically not clinically significant; may indicate vitamin B6 deficiency",
            "high_interpretation": "Elevated AST - less specific than ALT (also found in muscle, heart). AST > ALT suggests alcoholic liver disease. ALT > AST suggests viral hepatitis or NAFLD",
            "critical_low_interpretation": "Not clinically significant.",
            "critical_high_interpretation": "Markedly elevated AST - evaluate for acute liver injury, MI, rhabdomyolysis, or hemolysis.",
            "common_causes_low": ["Vitamin B6 deficiency", "End-stage liver disease"],
            "common_causes_high": ["Liver disease", "Myocardial infarction", "Skeletal muscle injury", "Hemolysis", "Alcohol", "Pancreatitis"],
            "follow_up": ["ALT", "CK (if muscle source suspected)", "Troponin (if cardiac source suspected)", "LDH", "Haptoglobin (if hemolysis suspected)"]
        },
        "alkaline_phosphatase": {
            "full_name": "Alkaline Phosphatase (ALP)",
            "category": "CMP",
            "unit": "U/L",
            "normal_range": {"low": 44, "high": 147},
            "male_range": {"low": 44, "high": 147},
            "female_range": {"low": 44, "high": 147},
            "pediatric_range": {"low": 100, "high": 420},
            "critical_low": 0,
            "critical_high": 500,
            "low_interpretation": "Low ALP - may indicate zinc deficiency, hypothyroidism, or malnutrition",
            "high_interpretation": "Elevated ALP - evaluate GGT to determine source. If GGT also elevated = liver source. If GGT normal = bone source. Causes include biliary obstruction, bone disease, pregnancy, and medications",
            "critical_low_interpretation": "Not typically critical.",
            "critical_high_interpretation": "Markedly elevated ALP - consider biliary obstruction, bone metastases, or Paget disease.",
            "common_causes_low": ["Zinc deficiency", "Hypothyroidism", "Malnutrition", "Wilson disease", "Hypophosphatasia"],
            "common_causes_high": ["Biliary obstruction", "Primary biliary cholangitis", "Bone disease (Paget, metastases)", "Pregnancy (placental source)", "Medications", "Hepatitis", "Growing children"],
            "follow_up": ["GGT", "Bilirubin", "ALT/AST", "5'-nucleotidase", "Bone-specific ALP", "PTH", "Vitamin D"]
        },
        "albumin": {
            "full_name": "Albumin",
            "category": "CMP",
            "unit": "g/dL",
            "normal_range": {"low": 3.5, "high": 5.5},
            "male_range": {"low": 3.5, "high": 5.5},
            "female_range": {"low": 3.5, "high": 5.5},
            "pediatric_range": {"low": 3.0, "high": 5.0},
            "critical_low": 1.5,
            "critical_high": 8.0,
            "low_interpretation": "Hypoalbuminemia - may indicate malnutrition, liver disease, nephrotic syndrome, protein-losing enteropathy, inflammation, or volume overload",
            "high_interpretation": "Hyperalbuminemia - almost always due to dehydration. No primary condition causes elevated albumin.",
            "critical_low_interpretation": "Severe hypoalbuminemia - high risk of edema, poor wound healing, drug binding issues. Evaluate nutritional status and underlying cause.",
            "critical_high_interpretation": "Extreme elevation - always dehydration. Rehydrate and recheck.",
            "common_causes_low": ["Malnutrition", "Liver disease", "Nephrotic syndrome", "Protein-losing enteropathy", "Severe burns", "Inflammation", "Volume overload", "Malabsorption"],
            "common_causes_high": ["Dehydration"],
            "follow_up": ["Total protein", "Liver function tests", "Urinalysis (protein)", "24-hour urine protein", "Prealbumin (short-term nutritional marker)"]
        },
        "total_bilirubin": {
            "full_name": "Total Bilirubin",
            "category": "CMP",
            "unit": "mg/dL",
            "normal_range": {"low": 0.1, "high": 1.2},
            "male_range": {"low": 0.1, "high": 1.2},
            "female_range": {"low": 0.1, "high": 1.2},
            "pediatric_range": {"low": 0.1, "high": 1.0},
            "critical_low": 0.0,
            "critical_high": 15.0,
            "low_interpretation": "Low bilirubin - typically not clinically significant",
            "high_interpretation": "Hyperbilirubinemia - determine if direct (conjugated) or indirect (unconjugated) predominates. Direct predominant = biliary obstruction or hepatocellular disease. Indirect predominant = hemolysis or Gilbert syndrome",
            "critical_low_interpretation": "Not clinically significant.",
            "critical_high_interpretation": "Severe hyperbilirubinemia - risk of kernicterus in neonates. In adults, suggests severe liver disease, biliary obstruction, or massive hemolysis.",
            "common_causes_low": ["Not clinically significant"],
            "common_causes_high": ["Gilbert syndrome (indirect)", "Hemolysis (indirect)", "Biliary obstruction (direct)", "Hepatitis (mixed)", "Cirrhosis (mixed)", "Drug-induced cholestasis", "Dubin-Johnson syndrome (direct)", "Crigler-Najjar (indirect)"],
            "follow_up": ["Direct and indirect bilirubin", "ALT/AST", "Alkaline phosphatase", "GGT", "LDH", "Haptoglobin", "Abdominal ultrasound", "MRCP if biliary obstruction suspected"]
        },
        # Thyroid
        "tsh": {
            "full_name": "Thyroid Stimulating Hormone",
            "category": "Thyroid",
            "unit": "mIU/L",
            "normal_range": {"low": 0.4, "high": 4.0},
            "male_range": {"low": 0.4, "high": 4.0},
            "female_range": {"low": 0.4, "high": 4.0},
            "pediatric_range": {"low": 0.5, "high": 5.0},
            "critical_low": 0.01,
            "critical_high": 50.0,
            "low_interpretation": "Suppressed TSH - suggests hyperthyroidism. Check free T4 to confirm. If free T4 normal, check free T3 (T3 thyrotoxicosis) or consider subclinical hyperthyroidism",
            "high_interpretation": "Elevated TSH - suggests primary hypothyroidism. Check free T4 to confirm. If free T4 normal, may be subclinical hypothyroidism",
            "critical_low_interpretation": "Markedly suppressed TSH - likely overt hyperthyroidism. Urgent evaluation for thyroid storm risk.",
            "critical_high_interpretation": "Markedly elevated TSH - overt hypothyroidism. Evaluate for myxedema risk. Start levothyroxine.",
            "common_causes_low": ["Graves disease", "Toxic adenoma", "Toxic multinodular goiter", "Thyroiditis (early phase)", "Excess thyroid hormone replacement", "Pituitary failure (rare)"],
            "common_causes_high": ["Hashimoto thyroiditis", "Iodine deficiency", "Lithium", "Amiodarone", "Post-thyroidectomy", "Post-RAI", "Subacute thyroiditis (recovery phase)"],
            "follow_up": ["Free T4", "Free T3", "Thyroid antibodies (TPO, TSI)", "Thyroid ultrasound", "Radioactive iodine uptake (if hyperthyroid)"]
        },
        "free_t4": {
            "full_name": "Free Thyroxine (Free T4)",
            "category": "Thyroid",
            "unit": "ng/dL",
            "normal_range": {"low": 0.8, "high": 1.8},
            "male_range": {"low": 0.8, "high": 1.8},
            "female_range": {"low": 0.8, "high": 1.8},
            "pediatric_range": {"low": 0.9, "high": 2.0},
            "critical_low": 0.2,
            "critical_high": 5.0,
            "low_interpretation": "Low free T4 with high TSH = overt primary hypothyroidism. Low free T4 with normal/low TSH = central hypothyroidism (pituitary failure)",
            "high_interpretation": "High free T4 with low TSH = overt hyperthyroidism. High free T4 with normal TSH = TSH-secreting pituitary adenoma or thyroid hormone resistance (rare)",
            "critical_low_interpretation": "Severe hypothyroidism - risk of myxedema coma. Urgent thyroid hormone replacement.",
            "critical_high_interpretation": "Severe thyrotoxicosis - risk of thyroid storm. Urgent antithyroid therapy.",
            "common_causes_low": ["Hypothyroidism (primary or central)", "Severe illness (euthyroid sick syndrome)", "Medications (PTU, methimazole)"],
            "common_causes_high": ["Hyperthyroidism", "Thyroiditis (early phase)", "Exogenous thyroid hormone excess", "Factitious ingestion"],
            "follow_up": ["TSH", "Free T3", "Thyroid antibodies", "Thyroid uptake scan"]
        },
        # HbA1c
        "hba1c": {
            "full_name": "Hemoglobin A1c",
            "category": "Diabetes Monitoring",
            "unit": "%",
            "normal_range": {"low": 4.0, "high": 5.6},
            "male_range": {"low": 4.0, "high": 5.6},
            "female_range": {"low": 4.0, "high": 5.6},
            "pediatric_range": {"low": 4.0, "high": 5.6},
            "critical_low": 3.5,
            "critical_high": 14.0,
            "low_interpretation": "Low HbA1c (<4.0) may indicate frequent hypoglycemia, hemolytic anemia, recent blood loss, or hemoglobin variants affecting assay accuracy",
            "high_interpretation": "Elevated HbA1c: 5.7-6.4 = prediabetes. >=6.5 = diabetes. Each 1% increase correlates with ~35 mg/dL increase in average glucose. Target <7% for most adults with diabetes",
            "critical_low_interpretation": "Very low HbA1c - suspect frequent hypoglycemia (especially if diabetic) or conditions affecting RBC lifespan.",
            "critical_high_interpretation": "Very high HbA1c - poor long-term glycemic control. Average glucose >350 mg/dL. High risk of complications. Intensify treatment.",
            "common_causes_low": ["Frequent hypoglycemia", "Hemolytic anemia", "Blood loss/transfusion", "Hemoglobin variants", "Chronic kidney disease (falsely low)", "Shortened RBC lifespan"],
            "common_causes_high": ["Poor glycemic control", "Iron deficiency anemia (falsely elevated)", "Vitamin B12/folate deficiency", "Chronic kidney disease (some assays)", "Alcoholism", "Splenic removal delay"],
            "follow_up": ["Fasting glucose", "Oral glucose tolerance test (if diagnostic uncertainty)", "Self-monitoring blood glucose logs", "Kidney function", "Eye exam (if diabetic)", "Foot exam"]
        },
        # Lipids
        "total_cholesterol": {
            "full_name": "Total Cholesterol",
            "category": "Lipid Panel",
            "unit": "mg/dL",
            "normal_range": {"low": 0, "high": 200},
            "male_range": {"low": 0, "high": 200},
            "female_range": {"low": 0, "high": 200},
            "pediatric_range": {"low": 0, "high": 170},
            "critical_low": 50,
            "critical_high": 400,
            "low_interpretation": "Low total cholesterol - may indicate malnutrition, liver disease, hyperthyroidism, malabsorption, or chronic illness. Very low levels associated with higher non-cardiac mortality in some studies",
            "high_interpretation": "Elevated total cholesterol - evaluate LDL and HDL components. Desirable <200 mg/dL. Risk depends on LDL, HDL, and overall cardiovascular risk factors",
            "critical_low_interpretation": "Very low cholesterol - evaluate for severe malnutrition, liver failure, or malabsorption.",
            "critical_high_interpretation": "Severely elevated cholesterol - high cardiovascular risk. Evaluate for familial hypercholesterolemia. Intensive lipid-lowering therapy indicated.",
            "common_causes_low": ["Malnutrition", "Liver disease", "Hyperthyroidism", "Malabsorption", "Chronic illness", "Statins", "Familial hypobetalipoproteinemia"],
            "common_causes_high": ["Dietary factors", "Genetic (familial hypercholesterolemia)", "Hypothyroidism", "Nephrotic syndrome", "Cholestasis", "Pregnancy", "Medications (beta-blockers, diuretics)"],
            "follow_up": ["LDL cholesterol", "HDL cholesterol", "Triglycerides", "Apolipoprotein B", "Lp(a)", "TSH", "Statins indication assessment (ASCVD risk calculator)"]
        },
        "ldl": {
            "full_name": "LDL Cholesterol",
            "category": "Lipid Panel",
            "unit": "mg/dL",
            "normal_range": {"low": 0, "high": 130},
            "male_range": {"low": 0, "high": 130},
            "female_range": {"low": 0, "high": 130},
            "pediatric_range": {"low": 0, "high": 110},
            "critical_low": 0,
            "critical_high": 300,
            "low_interpretation": "Low LDL - generally protective against cardiovascular disease. May indicate malnutrition, liver disease, or hyperthyroidism",
            "high_interpretation": "Elevated LDL - primary target for cardiovascular risk reduction. Optimal <100. Near optimal 100-129. Borderline high 130-159. High 160-189. Very high >=190",
            "critical_low_interpretation": "Very low LDL on treatment - generally not concerning if on statin/PCSK9. Monitor for deficiency of fat-soluble vitamins if extremely low.",
            "critical_high_interpretation": "Very high LDL - suggests familial hypercholesterolemia. Aggressive treatment needed. Consider referral to lipid specialist.",
            "common_causes_low": ["Statin therapy", "PCSK9 inhibitors", "Malnutrition", "Liver disease", "Hyperthyroidism", "Familial hypobetalipoproteinemia"],
            "common_causes_high": ["Diet (saturated fat, trans fat)", "Familial hypercholesterolemia", "Hypothyroidism", "Nephrotic syndrome", "Cholestasis", "Chronic kidney disease", "Pregnancy"],
            "follow_up": ["ASCVD 10-year risk calculation", "Apolipoprotein B", "Lp(a)", "Coronary calcium score (if intermediate risk)", "TSH", "Statin therapy evaluation"]
        },
        "hdl": {
            "full_name": "HDL Cholesterol",
            "category": "Lipid Panel",
            "unit": "mg/dL",
            "normal_range": {"low": 40, "high": 60},
            "male_range": {"low": 40, "high": 60},
            "female_range": {"low": 50, "high": 60},
            "pediatric_range": {"low": 35, "high": 65},
            "critical_low": 10,
            "critical_high": 120,
            "low_interpretation": "Low HDL - independent cardiovascular risk factor. Men <40, women <50 mg/dL considered low. Associated with metabolic syndrome, sedentary lifestyle, smoking, obesity",
            "high_interpretation": "High HDL - generally protective. However, extremely high HDL (>80-90) may not confer additional benefit and in rare cases may indicate dysfunctional HDL",
            "critical_low_interpretation": "Very low HDL - significantly increased cardiovascular risk. Aggressive management of all other risk factors needed.",
            "critical_high_interpretation": "Very high HDL - generally not concerning but very high levels may indicate genetic variants (e.g., CETP deficiency).",
            "common_causes_low": ["Smoking", "Sedentary lifestyle", "Obesity", "Metabolic syndrome", "Type 2 diabetes", "High triglycerides", "Beta-blockers", "Anabolic steroids"],
            "common_causes_high": ["Regular exercise", "Moderate alcohol", "Estrogen therapy", "Niacin", "Genetic factors", "CETP deficiency"],
            "follow_up": ["Triglycerides", "LDL", "Apolipoprotein A1", "Metabolic syndrome evaluation", "Lifestyle modification assessment"]
        },
        "triglycerides": {
            "full_name": "Triglycerides (Fasting)",
            "category": "Lipid Panel",
            "unit": "mg/dL",
            "normal_range": {"low": 0, "high": 150},
            "male_range": {"low": 0, "high": 150},
            "female_range": {"low": 0, "high": 150},
            "pediatric_range": {"low": 0, "high": 100},
            "critical_low": 0,
            "critical_high": 1000,
            "low_interpretation": "Low triglycerides - typically not clinically significant. May indicate malnutrition or malabsorption",
            "high_interpretation": "Elevated triglycerides: 150-199 = borderline high. 200-499 = high. >=500 = very high (pancreatitis risk). Associated with metabolic syndrome, diabetes, alcohol, medications",
            "critical_low_interpretation": "Not clinically significant.",
            "critical_high_interpretation": "Very high triglycerides - risk of acute pancreatitis. Fibrates and omega-3 fatty acids indicated. Very low fat diet. Exclude alcohol.",
            "common_causes_low": ["Malnutrition", "Malabsorption", "Very low fat diet"],
            "common_causes_high": ["Metabolic syndrome", "Type 2 diabetes", "Alcohol", "Hypothyroidism", "Renal disease", "Pregnancy", "Medications (beta-blockers, diuretics, steroids, tamoxifen, isotretinoin)", "Familial hypertriglyceridemia"],
            "follow_up": ["Fasting lipid panel", "HbA1c", "TSH", "Liver function tests", "Amylase/lipase (if >500)", "Apolipoprotein B"]
        },
        # Additional tests
        "tropontin": {
            "full_name": "High-Sensitivity Troponin I",
            "category": "Cardiac",
            "unit": "ng/mL",
            "normal_range": {"low": 0, "high": 0.04},
            "male_range": {"low": 0, "high": 0.04},
            "female_range": {"low": 0, "high": 0.04},
            "pediatric_range": {"low": 0, "high": 0.04},
            "critical_low": 0,
            "critical_high": 1.0,
            "low_interpretation": "Undetectable troponin - no evidence of myocardial injury",
            "high_interpretation": "Elevated troponin - indicates myocardial injury. Serial measurements needed to differentiate acute MI (rise and fall pattern) from chronic elevation. Must interpret with clinical context and ECG",
            "critical_low_interpretation": "Not applicable.",
            "critical_high_interpretation": "Markedly elevated troponin - likely acute MI. Urgent cardiology consult, serial troponins, ECG, and possible cath lab activation per institutional protocol.",
            "common_causes_low": ["Normal - no myocardial injury detected"],
            "common_causes_high": ["Acute MI", "Pulmonary embolism", "Heart failure", "Myocarditis", "Renal failure (chronic elevation)", "Sepsis", "Aortic dissection", "Cardiac contusion", "Demand ischemia", "Stress cardiomyopathy"],
            "follow_up": ["Serial troponins (0, 3, 6 hours)", "ECG", "BNP/NT-proBNP", "Echocardiogram", "CT angiography (if PE suspected)"]
        },
        "bnp": {
            "full_name": "B-type Natriuretic Peptide (BNP)",
            "category": "Cardiac",
            "unit": "pg/mL",
            "normal_range": {"low": 0, "high": 100},
            "male_range": {"low": 0, "high": 100},
            "female_range": {"low": 0, "high": 100},
            "pediatric_range": {"low": 0, "high": 100},
            "critical_low": 0,
            "critical_high": 1000,
            "low_interpretation": "Low BNP - heart failure unlikely as cause of dyspnea (negative predictive value >95%)",
            "high_interpretation": "Elevated BNP - supports diagnosis of heart failure. >400 pg/mL strongly suggestive. Correlates with severity. May also be elevated in renal failure, pulmonary hypertension, PE, and atrial fibrillation",
            "critical_low_interpretation": "Not applicable.",
            "critical_high_interpretation": "Markedly elevated BNP - severe heart failure likely. Associated with poor prognosis. Requires aggressive management.",
            "common_causes_low": ["Normal cardiac function", "Obesity (BNP may be falsely lower)", "Flash pulmonary edema (early)"],
            "common_causes_high": ["Heart failure (systolic or diastolic)", "Renal failure", "Pulmonary hypertension", "PE", "Atrial fibrillation", "Age (baseline increases)", "Right ventricular strain"],
            "follow_up": ["Echocardiogram", "Chest X-ray", "NT-proBNP (more stable marker)", "Cardiac catheterization (if indicated)"]
        },
        "crp": {
            "full_name": "C-Reactive Protein",
            "category": "Inflammatory",
            "unit": "mg/L",
            "normal_range": {"low": 0, "high": 10},
            "male_range": {"low": 0, "high": 10},
            "female_range": {"low": 0, "high": 10},
            "pediatric_range": {"low": 0, "high": 10},
            "critical_low": 0,
            "critical_high": 300,
            "low_interpretation": "Low CRP - no evidence of significant acute inflammation",
            "high_interpretation": "Elevated CRP - nonspecific marker of inflammation. Acute infection, autoimmune flare, tissue injury, malignancy, or cardiovascular risk marker (hs-CRP). Levels >100 suggest significant infection or inflammation",
            "critical_low_interpretation": "Not applicable.",
            "critical_high_interpretation": "Markedly elevated CRP - suggests severe infection, sepsis, acute inflammatory condition, or severe tissue injury. Urgent clinical evaluation.",
            "common_causes_low": ["No significant inflammation"],
            "common_causes_high": ["Bacterial infection", "Autoimmune disease flare", "Tissue injury/surgery", "Malignancy", "MI", "IBD", "Pneumonia", "Sepsis"],
            "follow_up": ["ESR", "Procalcitonin (if infection suspected)", "Blood cultures", "hs-CRP (for cardiovascular risk)", "Autoimmune workup (ANA, RF)"]
        },
        "psa": {
            "full_name": "Prostate Specific Antigen",
            "category": "Tumor Marker",
            "unit": "ng/mL",
            "normal_range": {"low": 0, "high": 4.0},
            "male_range": {"low": 0, "high": 4.0},
            "female_range": {"low": 0, "high": 0.0},
            "pediatric_range": {"low": 0, "high": 0.0},
            "critical_low": 0,
            "critical_high": 100,
            "low_interpretation": "Low PSA - generally reassuring for prostate cancer screening. However, prostate cancer can occur even with PSA <4, especially in high-risk individuals",
            "high_interpretation": "Elevated PSA - does not always mean cancer. PSA 4-10 is diagnostic gray zone. Consider free/total PSA ratio, PSA velocity, and PSA density. Causes include BPH, prostatitis, recent ejaculation, and prostate cancer",
            "critical_low_interpretation": "Not applicable.",
            "critical_high_interpretation": "Very high PSA - high suspicion for prostate cancer. May indicate advanced or metastatic disease. Urgent urology referral and prostate biopsy.",
            "common_causes_low": ["Normal finding", "5-alpha reductase inhibitors (finasteride, dutasteride) lower PSA by ~50%"],
            "common_causes_high": ["BPH", "Prostatitis", "Prostate cancer", "Recent ejaculation", "Urinary retention", "Prostate massage/biopsy", "Bicycle riding"],
            "follow_up": ["Free/total PSA ratio", "PSA velocity", "PSA density", "Multiparametric prostate MRI", "Prostate biopsy", "Urology referral"]
        },
        "vitamin_d": {
            "full_name": "25-Hydroxy Vitamin D",
            "category": "Nutritional",
            "unit": "ng/mL",
            "normal_range": {"low": 30, "high": 100},
            "male_range": {"low": 30, "high": 100},
            "female_range": {"low": 30, "high": 100},
            "pediatric_range": {"low": 20, "high": 100},
            "critical_low": 5,
            "critical_high": 200,
            "low_interpretation": "Vitamin D deficiency or insufficiency. <20 ng/mL = deficiency. 20-29 = insufficiency. Associated with osteoporosis, fractures, muscle weakness, and possibly autoimmune disease, infections, and cardiovascular disease",
            "high_interpretation": "Vitamin D excess - usually from excessive supplementation. Risk of hypercalcemia, kidney stones, and soft tissue calcification. Reduce or discontinue supplementation",
            "critical_low_interpretation": "Severe vitamin D deficiency - risk of osteomalacia, hypocalcemia, and fractures. Requires high-dose vitamin D supplementation (50,000 IU weekly for 8 weeks then maintenance).",
            "critical_high_interpretation": "Vitamin D toxicity - stop all supplementation. Monitor calcium. Risk of hypercalcemia and renal damage.",
            "common_causes_low": ["Inadequate sun exposure", "Poor dietary intake", "Malabsorption (celiac, IBD, bariatric surgery)", "Obesity (sequestration in fat)", "Chronic kidney disease", "Liver disease", "Medications (anticonvulsants, glucocorticoids)"],
            "common_causes_high": ["Excessive supplementation", "Granulomatous disease (sarcoidosis)", "Lymphoma", "Primary hyperparathyroidism", "Williams syndrome"],
            "follow_up": ["Calcium", "Phosphorus", "PTH", "Alkaline phosphatase", "24-hour urine calcium", "Bone density scan (if deficiency)"]
        },
    }

    # --- Alias mapping for common test name variations ---
    TEST_ALIASES: Dict[str, str] = {
        "hgb": "hemoglobin", "hba1c": "hba1c", "a1c": "hba1c", "glycated_hemoglobin": "hba1c",
        "hct": "hematocrit", "plt": "platelets", "rbc": "hemoglobin",
        "na": "sodium", "k": "potassium", "pot": "potassium",
        "cr": "creatinine", "creatinine": "creatinine",
        "bun": "bun", "blood_urea_nitrogen": "bun",
        "glu": "glucose", "fasting_glucose": "glucose", "fbg": "glucose",
        "sgpt": "alt", "gpt": "alt",
        "sgot": "ast", "got": "ast",
        "alp": "alkaline_phosphatase", "alk_phos": "alkaline_phosphatase",
        "tbili": "total_bilirubin", "bilirubin": "total_bilirubin",
        "thyroid_stimulating_hormone": "tsh",
        "free_t4": "free_t4", "ft4": "free_t4", "thyroxine": "free_t4",
        "chol": "total_cholesterol", "cholesterol": "total_cholesterol", "tc": "total_cholesterol",
        "ldl_c": "ldl", "ldl_cholesterol": "ldl",
        "hdl_c": "hdl", "hdl_cholesterol": "hdl",
        "trig": "triglycerides", "tg": "triglycerides",
        "trop": "tropontin", "troponin_i": "tropontin", "hs_troponin": "tropontin",
        "bnp": "bnp", "nt_probnp": "bnp",
        "c_reactive_protein": "crp", "crp_hs": "crp",
        "prostate_specific_antigen": "psa",
        "vit_d": "vitamin_d", "25oh_d": "vitamin_d", "25_hydroxy_vitamin_d": "vitamin_d",
        "mcv": "mcv",
        "white_blood_cell": "wbc", "white_count": "wbc",
    }

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "")
        test_name = kwargs.get("test_name", "").strip().lower()
        value = kwargs.get("value")
        unit = kwargs.get("unit", "")
        patient_age = kwargs.get("patient_age")
        patient_sex = kwargs.get("patient_sex", "")
        historical_values = kwargs.get("historical_values", [])

        if not action:
            return SkillResult(success=False, error="Action is required")
        if not test_name:
            return SkillResult(success=False, error="Test name is required")

        # Resolve alias
        resolved_name = self.TEST_ALIASES.get(test_name, test_name)

        try:
            if action == "interpret":
                if value is None:
                    return SkillResult(success=False, error="Value is required for interpret action")
                result = self._interpret_value(resolved_name, value, unit, patient_age, patient_sex)
            elif action == "compare_to_range":
                if value is None:
                    return SkillResult(success=False, error="Value is required for compare_to_range action")
                result = self._compare_to_range(resolved_name, value, unit, patient_age, patient_sex)
            elif action == "trend_analysis":
                if not historical_values:
                    return SkillResult(success=False, error="historical_values is required for trend_analysis action")
                result = self._trend_analysis(resolved_name, historical_values, patient_age, patient_sex)
            else:
                return SkillResult(success=False, error=f"Unknown action: {action}")

            return SkillResult(success=True, data=result)
        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _get_test_info(self, test_name: str) -> Optional[Dict[str, Any]]:
        """Get test info by name or alias."""
        if test_name in self.LAB_TESTS:
            return self.LAB_TESTS[test_name]
        resolved = self.TEST_ALIASES.get(test_name, test_name)
        return self.LAB_TESTS.get(resolved)

    def _get_applicable_range(self, test_info: Dict[str, Any], patient_age: Optional[int], patient_sex: str) -> Dict[str, float]:
        """Determine which normal range to use based on age and sex."""
        if patient_age is not None and patient_age < 18 and "pediatric_range" in test_info:
            return test_info["pediatric_range"]
        if patient_sex == "male" and "male_range" in test_info:
            return test_info["male_range"]
        if patient_sex == "female" and "female_range" in test_info:
            return test_info["female_range"]
        return test_info["normal_range"]

    def _interpret_value(self, test_name: str, value: float, unit: str, patient_age: Optional[int], patient_sex: str) -> Dict[str, Any]:
        """Full interpretation of a lab value."""
        test_info = self._get_test_info(test_name)
        if not test_info:
            return {
                "test_name": test_name,
                "found": False,
                "message": f"Test '{test_name}' not found in database. Available tests: {', '.join(list(self.LAB_TESTS.keys()))}",
                "suggestion": "Try a common test name or abbreviation."
            }

        normal_range = self._get_applicable_range(test_info, patient_age, patient_sex)
        low = normal_range["low"]
        high = normal_range["high"]

        # Determine status
        if value < low:
            if test_info.get("critical_low") is not None and value <= test_info["critical_low"]:
                status = "critical_low"
                interpretation = test_info.get("critical_low_interpretation", test_info["low_interpretation"])
            else:
                status = "low"
                interpretation = test_info["low_interpretation"]
        elif value > high:
            if test_info.get("critical_high") is not None and value >= test_info["critical_high"]:
                status = "critical_high"
                interpretation = test_info.get("critical_high_interpretation", test_info["high_interpretation"])
            else:
                status = "high"
                interpretation = test_info["high_interpretation"]
        else:
            status = "normal"
            interpretation = "Value within normal reference range."

        # Calculate how far from normal (percentage)
        if value < low and low > 0:
            deviation_pct = round(((low - value) / low) * 100, 1)
            deviation_direction = "below_low"
        elif value > high and high > 0:
            deviation_pct = round(((value - high) / high) * 100, 1)
            deviation_direction = "above_high"
        else:
            deviation_pct = 0
            deviation_direction = "within_range"

        return {
            "found": True,
            "test_name": test_name,
            "full_name": test_info["full_name"],
            "category": test_info["category"],
            "value": value,
            "unit": unit or test_info["unit"],
            "expected_unit": test_info["unit"],
            "normal_range": normal_range,
            "status": status,
            "interpretation": interpretation,
            "deviation": {
                "percent": deviation_pct,
                "direction": deviation_direction
            },
            "critical_values": {
                "critical_low": test_info.get("critical_low"),
                "critical_high": test_info.get("critical_high")
            },
            "common_causes": test_info.get(f"common_causes_{status.replace('critical_', '')}", []),
            "follow_up_tests": test_info.get("follow_up", []),
            "requires_urgent_attention": status.startswith("critical_")
        }

    def _compare_to_range(self, test_name: str, value: float, unit: str, patient_age: Optional[int], patient_sex: str) -> Dict[str, Any]:
        """Simple range comparison."""
        test_info = self._get_test_info(test_name)
        if not test_info:
            return {
                "test_name": test_name,
                "found": False,
                "message": f"Test '{test_name}' not found in database."
            }

        normal_range = self._get_applicable_range(test_info, patient_age, patient_sex)
        low = normal_range["low"]
        high = normal_range["high"]

        if value < low:
            status = "low"
            how_far = f"{round(low - value, 2)} below lower limit"
        elif value > high:
            status = "high"
            how_far = f"{round(value - high, 2)} above upper limit"
        else:
            status = "normal"
            how_far = "within range"

        is_critical = False
        if test_info.get("critical_low") is not None and value <= test_info["critical_low"]:
            is_critical = True
        if test_info.get("critical_high") is not None and value >= test_info["critical_high"]:
            is_critical = True

        return {
            "found": True,
            "test_name": test_name,
            "full_name": test_info["full_name"],
            "value": value,
            "unit": unit or test_info["unit"],
            "normal_range_low": low,
            "normal_range_high": high,
            "status": status,
            "how_far_from_normal": how_far,
            "is_critical": is_critical,
            "message": f"{test_info['full_name']}: {value} {unit or test_info['unit']} - {status.upper()} ({how_far})"
        }

    def _trend_analysis(self, test_name: str, historical_values: List[Dict[str, Any]], patient_age: Optional[int], patient_sex: str) -> Dict[str, Any]:
        """Analyze trends in lab values over time."""
        test_info = self._get_test_info(test_name)
        if not test_info:
            return {
                "test_name": test_name,
                "found": False,
                "message": f"Test '{test_name}' not found in database."
            }

        normal_range = self._get_applicable_range(test_info, patient_age, patient_sex)
        low = normal_range["low"]
        high = normal_range["high"]

        # Sort by date
        sorted_values = sorted(historical_values, key=lambda x: x.get("date", ""))
        values = [v["value"] for v in sorted_values]
        dates = [v["date"] for v in sorted_values]

        if len(values) < 2:
            return {
                "test_name": test_name,
                "full_name": test_info["full_name"],
                "error": "At least 2 values are required for trend analysis",
                "values_provided": len(values)
            }

        # Calculate statistics
        min_val = min(values)
        max_val = max(values)
        avg_val = sum(values) / len(values)
        latest_val = values[-1]
        earliest_val = values[0]

        # Calculate trend direction
        overall_change = latest_val - earliest_val
        if overall_change > 0:
            trend_direction = "increasing"
        elif overall_change < 0:
            trend_direction = "decreasing"
        else:
            trend_direction = "stable"

        # Calculate rate of change per interval
        total_change = abs(overall_change)
        num_intervals = len(values) - 1
        avg_change_per_interval = round(total_change / num_intervals, 3) if num_intervals > 0 else 0

        # Check if values are consistently normal, abnormal, or fluctuating
        normal_count = sum(1 for v in values if low <= v <= high)
        abnormal_count = len(values) - normal_count

        if normal_count == len(values):
            consistency = "all_normal"
        elif abnormal_count == len(values):
            consistency = "all_abnormal"
        elif normal_count > abnormal_count:
            consistency = "mostly_normal"
        else:
            consistency = "mostly_abnormal"

        # Check for significant change (more than 10% of range width)
        range_width = high - low
        significant_threshold = range_width * 0.10
        if abs(overall_change) > significant_threshold:
            significance = "clinically_significant"
        elif abs(overall_change) > significant_threshold / 2:
            significance = "moderately_significant"
        else:
            significance = "minimal_change"

        # Evaluate each value
        value_assessments = []
        for i, val in enumerate(values):
            if val < low:
                val_status = "low"
            elif val > high:
                val_status = "high"
            else:
                val_status = "normal"
            value_assessments.append({
                "date": dates[i],
                "value": val,
                "status": val_status
            })

        # Generate trend interpretation
        if consistency == "all_normal" and trend_direction == "stable":
            trend_interpretation = f"All {test_info['full_name']} values are within normal range and stable. No action needed."
        elif consistency == "all_normal" and trend_direction != "stable":
            trend_interpretation = f"All {test_info['full_name']} values are within normal range but trending {trend_direction}. Monitor for potential future abnormality."
        elif consistency == "all_abnormal":
            direction = "low" if latest_val < low else "high"
            trend_interpretation = f"All {test_info['full_name']} values are abnormal. {trend_direction.capitalize()} trend noted. {test_info.get(f'common_causes_{direction}', [])}"
        else:
            trend_interpretation = f"{test_info['full_name']} values are fluctuating between normal and abnormal ranges. Trend direction: {trend_direction}. This warrants further evaluation."

        # Improvement assessment
        if earliest_val < low and latest_val >= low:
            improvement = "improving_from_low"
        elif earliest_val > high and latest_val <= high:
            improvement = "improving_from_high"
        elif earliest_val >= low <= high and (latest_val < low or latest_val > high):
            improvement = "worsening"
        elif trend_direction == "stable":
            improvement = "stable"
        else:
            improvement = trend_direction

        return {
            "found": True,
            "test_name": test_name,
            "full_name": test_info["full_name"],
            "category": test_info["category"],
            "unit": test_info["unit"],
            "normal_range": {"low": low, "high": high},
            "data_points": value_assessments,
            "statistics": {
                "earliest_value": earliest_val,
                "latest_value": latest_val,
                "minimum": min_val,
                "maximum": max_val,
                "average": round(avg_val, 2),
                "total_change": round(overall_change, 2),
                "avg_change_per_interval": avg_change_per_interval
            },
            "trend": {
                "direction": trend_direction,
                "significance": significance,
                "consistency": consistency,
                "improvement": improvement,
                "normal_count": normal_count,
                "abnormal_count": abnormal_count
            },
            "interpretation": trend_interpretation,
            "latest_status": "normal" if low <= latest_val <= high else ("low" if latest_val < low else "high"),
            "latest_interpretation": test_info["low_interpretation"] if latest_val < low else (test_info["high_interpretation"] if latest_val > high else "Within normal range"),
            "follow_up": test_info.get("follow_up", []),
            "recommendation": self._generate_trend_recommendation(consistency, trend_direction, significance, latest_val, low, high, test_info)
        }

    def _generate_trend_recommendation(self, consistency: str, trend: str, significance: str, latest: float, low: float, high: float, test_info: Dict) -> str:
        """Generate a clinical recommendation based on trend analysis."""
        if consistency == "all_normal" and trend == "stable":
            return "Continue routine monitoring per clinical guidelines. No immediate action required."
        elif consistency == "all_normal" and trend != "stable":
            return f"Values trending {trend} but still within normal range. Consider more frequent monitoring to detect if values cross the normal threshold."
        elif consistency == "mostly_normal":
            return "Occasional abnormal values noted. Correlate with clinical context. May need repeat testing to confirm."
        elif consistency == "all_abnormal" and trend == "increasing" and latest > high:
            return "Persistently elevated and worsening. Intervention likely needed. Review medications, lifestyle, and consider specialist referral."
        elif consistency == "all_abnormal" and trend == "decreasing" and latest < low:
            return "Persistently low and decreasing. Evaluate underlying cause. Consider supplementation or treatment adjustment."
        elif consistency == "all_abnormal" and trend == "decreasing" and latest > high:
            return "Abnormal but improving (decreasing toward normal). Current treatment may be effective. Continue monitoring."
        elif consistency == "all_abnormal" and trend == "increasing" and latest < low:
            return "Abnormal but improving (increasing toward normal). Current treatment may be effective. Continue monitoring."
        else:
            return "Abnormal values detected. Correlate with clinical presentation and consider follow-up testing as recommended."