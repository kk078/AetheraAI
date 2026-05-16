"""
Aethera AI - Drug Reference Skill

Drug information and interactions. Contains common drug database with
class, indications, interactions, and black box warnings. Supports
lookup drug, check interactions, and get formulary info.
"""

from typing import Dict, Any, List, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill


@skill(name="drug_reference", category="healthcare")
class DrugReferenceSkill(AetheraSkill):
    """
    Drug information lookup and interaction checking.
    """

    @property
    def name(self) -> str:
        return "drug_reference"

    @property
    def description(self) -> str:
        return "Drug information and interactions: lookup drugs, check drug-drug interactions, get formulary info"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["lookup", "check_interactions", "formulary_info"],
                    "description": "Action: lookup (drug info), check_interactions (drug-drug), formulary_info (formulary/tier)"
                },
                "drug_name": {
                    "type": "string",
                    "description": "Drug name (generic or brand) to look up"
                },
                "drug_list": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of drug names to check for interactions"
                },
                "payer": {
                    "type": "string",
                    "description": "Payer name for formulary lookup (e.g., Medicare, Aetna)"
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
            {"input": {"action": "lookup", "drug_name": "metformin"}},
            {"input": {"action": "check_interactions", "drug_list": ["warfarin", "aspirin", "omeprazole"]}},
            {"input": {"action": "formulary_info", "drug_name": "atorvastatin", "payer": "Medicare"}}
        ]

    # --- Drug database ---
    DRUG_DATABASE: Dict[str, Dict[str, Any]] = {
        "metformin": {
            "brand_names": ["Glucophage", "Glucophage XR", "Fortamet", "Riomet"],
            "drug_class": "Biguanide",
            "indications": ["Type 2 diabetes mellitus", "Polycystic ovary syndrome (off-label)"],
            "route": "Oral",
            "common_dosage": "500-2550 mg/day in divided doses",
            "black_box_warning": "Lactic acidosis: Post-marketing cases of serious lactic acidosis reported, particularly in patients with renal impairment. Contraindicated in severe renal impairment (eGFR < 30 mL/min).",
            "major_interactions": ["alcohol", "iodinated_contrast", "topiramate", "dolutegravir"],
            "moderate_interactions": ["cimetidine", "digoxin", "furosemide", "ranolazine", "trimethoprim", "vandetanib"],
            "contraindications": ["Severe renal impairment (eGFR < 30)", "Metabolic acidosis", "Before iodinated contrast procedures (hold temporarily)"],
            "monitoring": ["Renal function (eGFR)", "Hemoglobin A1c", "Vitamin B12 levels (long-term use)", "Lactic acid levels if symptomatic"],
            "pregnancy_category": "Not recommended (no established human data; insulin preferred)",
            "formulary_tier": {"Medicare": 1, "Aetna": 1, "UnitedHealthcare": 1, "Cigna": 1, "BCBS": 1},
            "generic_available": True
        },
        "atorvastatin": {
            "brand_names": ["Lipitor"],
            "drug_class": "HMG-CoA Reductase Inhibitor (Statin)",
            "indications": ["Hyperlipidemia", "Prevention of cardiovascular events", "Familial hypercholesterolemia"],
            "route": "Oral",
            "common_dosage": "10-80 mg once daily",
            "black_box_warning": None,
            "major_interactions": ["clarithromycin", "itraconazole", "ketoconazole", "nefazodone", "ritonavir", "telaprevir", "telithromycin", "cyclosporine", "gemfibrozil", "danazol"],
            "moderate_interactions": ["amlodipine", "diltiazem", "erythromycin", "fluconazole", "verapamil", "warfarin", "digoxin", "colchicine", "fusidic_acid"],
            "contraindications": ["Active liver disease", "Pregnancy", "Breastfeeding", "Unexplained persistent transaminase elevation"],
            "monitoring": ["Lipid panel", "Liver function tests (ALT/AST)", "CK if muscle symptoms", "Blood glucose"],
            "pregnancy_category": "X - Contraindicated",
            "formulary_tier": {"Medicare": 1, "Aetna": 1, "UnitedHealthcare": 1, "Cigna": 1, "BCBS": 1},
            "generic_available": True
        },
        "lisinopril": {
            "brand_names": ["Zestril", "Prinivil"],
            "drug_class": "Angiotensin-Converting Enzyme (ACE) Inhibitor",
            "indications": ["Hypertension", "Heart failure", "Post-MI left ventricular dysfunction", "Diabetic nephropathy"],
            "route": "Oral",
            "common_dosage": "10-40 mg once daily",
            "black_box_warning": None,
            "major_interactions": ["aliskiren", "potassium_supplements", "spironolactone", "trimethoprim", "lithium", "gold_injections", "sacubitril"],
            "moderate_interactions": ["aspirin", "ibuprofen", "naproxen", "potassium_sparing_diuretics", "allopurinol", "indomethacin", "tizanidine"],
            "contraindications": ["History of angioedema", "Pregnancy (2nd/3rd trimester)", "Bilateral renal artery stenosis", "Co-administration with aliskiren in diabetics"],
            "monitoring": ["Blood pressure", "Serum potassium", "Renal function (BUN, creatinine)", "Cough (side effect)"],
            "pregnancy_category": "D - Positive evidence of risk",
            "formulary_tier": {"Medicare": 1, "Aetna": 1, "UnitedHealthcare": 1, "Cigna": 1, "BCBS": 1},
            "generic_available": True
        },
        "amlodipine": {
            "brand_names": ["Norvasc"],
            "drug_class": "Calcium Channel Blocker (Dihydropyridine)",
            "indications": ["Hypertension", "Angina pectoris", "Coronary artery disease"],
            "route": "Oral",
            "common_dosage": "2.5-10 mg once daily",
            "black_box_warning": None,
            "major_interactions": ["simvastatin", "clarithromycin", "itraconazole", "ketoconazole", "ritonavir"],
            "moderate_interactions": ["atorvastatin", "diltiazem", "verapamil", "cyclosporine", "tacrolimus", "warfarin", "sildenafil", "tadalafil"],
            "contraindications": ["Severe aortic stenosis", "Cardiogenic shock", "Unstable angina (not controlled)", "Known hypersensitivity"],
            "monitoring": ["Blood pressure", "Heart rate", "Peripheral edema", "Liver function"],
            "pregnancy_category": "C - Risk cannot be ruled out",
            "formulary_tier": {"Medicare": 1, "Aetna": 1, "UnitedHealthcare": 1, "Cigna": 1, "BCBS": 1},
            "generic_available": True
        },
        "omeprazole": {
            "brand_names": ["Prilosec", "Prilosec OTC", "Zegerid"],
            "drug_class": "Proton Pump Inhibitor (PPI)",
            "indications": ["GERD", "Peptic ulcer disease", "H. pylori eradication", "Zollinger-Ellison syndrome", "Erosive esophagitis"],
            "route": "Oral",
            "common_dosage": "20-40 mg once daily",
            "black_box_warning": None,
            "major_interactions": ["clopidogrel", "atazananvir", "nelfinavir", "rilpivirine", "erlotinib", "dasatinib", "pazopanib"],
            "moderate_interactions": ["warfarin", "methotrexate", "digoxin", "ketoconazole", "itraconazole", "iron_supplements", "cyanocobalamin", "cefdinir", "citalopram", "diazepam", "phenytoin"],
            "contraindications": ["Hypersensitivity to PPIs", "Co-administration with rilpivirine", "Co-administration with atazanavir (without ritonavir)"],
            "monitoring": ["Magnesium levels (long-term use)", "Vitamin B12 (long-term use)", "Bone density (long-term use)", "Renal function"],
            "pregnancy_category": "C - Risk cannot be ruled out",
            "formulary_tier": {"Medicare": 1, "Aetna": 1, "UnitedHealthcare": 1, "Cigna": 1, "BCBS": 1},
            "generic_available": True
        },
        "warfarin": {
            "brand_names": ["Coumadin", "Jantoven"],
            "drug_class": "Anticoagulant (Vitamin K Antagonist)",
            "indications": ["Atrial fibrillation with stroke risk", "Deep vein thrombosis", "Pulmonary embolism", "Mechanical heart valve", "Antiphospholipid syndrome"],
            "route": "Oral",
            "common_dosage": "Individualized (typically 2-10 mg/day, dosed to target INR)",
            "black_box_warning": "Bleeding risk: Warfarin can cause major or fatal bleeding. Regular INR monitoring required. Many drugs, foods, and conditions affect warfarin response. Discontinue if serious bleeding occurs.",
            "major_interactions": ["aspirin", "clopidogrel", "ibuprofen", "naproxen", "amiodarone", "azithromycin", "ciprofloxacin", "clarithromycin", "fluconazole", "itraconazole", "ketoconazole", "metronidazole", "trimethoprim_sulfamethoxazole", "phenytoin", "carbamazepine", "rifampin", "vitamin_k", "cranberry", "st_johns_wort", "garlic_supplements", "gingko_biloba"],
            "moderate_interactions": ["atorvastatin", "omeprazole", "cimetidine", "prednisone", "levothyroxine", "celecoxib", "diclofenac", "meloxicam", "apixaban", "rivaroxaban"],
            "contraindications": ["Active bleeding", "Severe liver disease", "Pregnancy", "Uncontrolled hypertension", "Recent major surgery", "Pericarditis or pericardial effusion", "Inability to obtain regular INR monitoring"],
            "monitoring": ["INR (target usually 2.0-3.0 or 2.5-3.5 for mechanical valves)", "Hemoglobin/hematocrit", "Signs of bleeding", "Liver function", "Renal function"],
            "pregnancy_category": "X - Contraindicated",
            "formulary_tier": {"Medicare": 1, "Aetna": 1, "UnitedHealthcare": 1, "Cigna": 1, "BCBS": 1},
            "generic_available": True
        },
        "aspirin": {
            "brand_names": ["Bayer", "Ecotrin", "Bufferin", "St. Joseph"],
            "drug_class": "NSAID / Antiplatelet Agent / Salicylate",
            "indications": ["Pain/fever (higher doses)", "Cardiovascular prophylaxis (low dose)", "Acute MI", "Post-CABG", "Post-stent placement"],
            "route": "Oral",
            "common_dosage": "81-325 mg/day (cardiovascular); 325-650 mg q4-6h (pain/fever)",
            "black_box_warning": None,
            "major_interactions": ["warfarin", "clopidogrel", "ibuprofen", "naproxen", "methotrexate", "valproic_acid", "ace_inhibitors", "spironolactone"],
            "moderate_interactions": ["lisinopril", "losartan", "prednisone", "phenytoin", "phenobarbital", "digoxin", "insulin", "sulfonylureas"],
            "contraindications": ["Active GI bleeding", "Hemophilia or bleeding disorders", "Aspirin-sensitive asthma", "Children with viral infections (Reye syndrome risk)", "Last trimester of pregnancy"],
            "monitoring": ["GI symptoms", "Bleeding signs", "Blood pressure (with ACE inhibitors)", "Renal function"],
            "pregnancy_category": "D (3rd trimester); C (1st/2nd trimester low dose)",
            "formulary_tier": {"Medicare": 1, "Aetna": 1, "UnitedHealthcare": 1, "Cigna": 1, "BCBS": 1},
            "generic_available": True
        },
        "levothyroxine": {
            "brand_names": ["Synthroid", "Levoxyl", "Tirosint", "Unithroid"],
            "drug_class": "Thyroid Hormone",
            "indications": ["Hypothyroidism", "Myxedema coma", "Thyroid hormone replacement post-thyroidectomy", "TSH suppression in thyroid cancer"],
            "route": "Oral",
            "common_dosage": "25-200 mcg once daily (weight-based: ~1.6 mcg/kg/day)",
            "black_box_warning": None,
            "major_interactions": ["cholestyramine", "colestipol", "ferrous_sulfate", "aluminum_hydroxide", "calcium_carbonate", "sucralfate", "orlistat", "sevelamer"],
            "moderate_interactions": ["warfarin", "amiodarone", "carbamazepine", "phenytoin", "rifampin", "phenobarbital", "sertraline", "omeprazole", "cimetidine", "estrogen", "raloxifene", "metformin"],
            "contraindications": ["Untreated adrenal insufficiency", "Untreated thyrotoxicosis", "Acute MI", "Uncorrected adrenal cortical insufficiency"],
            "monitoring": ["TSH (primary marker)", "Free T4", "Heart rate", "Bone density (long-term overtreatment)", "Weight"],
            "pregnancy_category": "A - Generally safe (doses may need increase)",
            "formulary_tier": {"Medicare": 1, "Aetna": 1, "UnitedHealthcare": 1, "Cigna": 1, "BCBS": 1},
            "generic_available": True
        },
        "amoxicillin": {
            "brand_names": ["Amoxil", "Moxatag", "Trimox"],
            "drug_class": "Penicillin Antibiotic (Aminopenicillin)",
            "indications": ["Otitis media", "Pharyngitis/tonsillitis", "Sinusitis", "URI", "UTI", "H. pylori eradication", "Skin infections", "Dental infections", "Lyme disease"],
            "route": "Oral",
            "common_dosage": "250-500 mg q8h or 500-875 mg q12h",
            "black_box_warning": None,
            "major_interactions": ["allopurinol", "methotrexate", "warfarin", "live_vaccines"],
            "moderate_interactions": ["probenecid", "doxycycline", "tetracycline", "erythromycin", "chloramphenicol", "sulfonamides", "oral_contraceptives"],
            "contraindications": ["Penicillin allergy (anaphylaxis history)", "History of amoxicillin-associated hepatic dysfunction", "Infectious mononucleosis (risk of rash)"],
            "monitoring": ["Renal function (dose adjustment)", "Signs of allergic reaction", "Liver function (with prolonged use)"],
            "pregnancy_category": "B - No evidence of risk in humans",
            "formulary_tier": {"Medicare": 1, "Aetna": 1, "UnitedHealthcare": 1, "Cigna": 1, "BCBS": 1},
            "generic_available": True
        },
        "prednisone": {
            "brand_names": ["Deltasone", "Prednisone Intensol", "Rayos"],
            "drug_class": "Corticosteroid (Glucocorticoid)",
            "indications": ["Inflammatory conditions", "Autoimmune diseases", "Asthma exacerbation", "COPD exacerbation", "Allergic reactions", "Organ transplant rejection", "Adrenal insufficiency", "Nephrotic syndrome"],
            "route": "Oral",
            "common_dosage": "5-60 mg/day (varies widely by indication)",
            "black_box_warning": None,
            "major_interactions": ["warfarin", "nsaids", "live_vaccines", "ketoconazole", "cyclosporine", "tacrolimus", "nifedipine"],
            "moderate_interactions": ["aspirin", "ibuprofen", "furosemide", "metformin", "insulin", "phenytoin", "carbamazepine", "rifampin", "phenobarbital", "fluconazole", "macrolide_antibiotics", "digoxin", "alendronate", "cimetidine"],
            "contraindications": ["Systemic fungal infections", "Live vaccines (with immunosuppressive doses)", "Known hypersensitivity"],
            "monitoring": ["Blood glucose", "Blood pressure", "Weight", "Bone density (long-term)", "Potassium", "Adrenal function (tapering)", "Infection signs", "Cataracts/glaucoma (long-term)", "Mental health"],
            "pregnancy_category": "C - Risk cannot be ruled out",
            "formulary_tier": {"Medicare": 1, "Aetna": 1, "UnitedHealthcare": 1, "Cigna": 1, "BCBS": 1},
            "generic_available": True
        },
        "sertraline": {
            "brand_names": ["Zoloft"],
            "drug_class": "Selective Serotonin Reuptake Inhibitor (SSRI)",
            "indications": ["Major depressive disorder", "Generalized anxiety disorder", "PTSD", "OCD", "Panic disorder", "Social anxiety disorder", "PMDD"],
            "route": "Oral",
            "common_dosage": "50-200 mg once daily",
            "black_box_warning": "Suicidal thoughts and behaviors: Increased risk of suicidal thinking and behavior in children, adolescents, and young adults with major depressive disorder. Monitor for clinical worsening and emergence of suicidal thoughts.",
            "major_interactions": ["pimozide", "disulfiram (oral solution only)", "mao_inhibitors", "linezolid", "methylene_blue", "tramadol", "triptans", "tryptophan"],
            "moderate_interactions": ["warfarin", "aspirin", "ibuprofen", "cimetidine", "digoxin", "levothyroxine", "phenytoin", "tolbutamide", "diazepam", "lithium", "buspirone", "fentanyl"],
            "contraindications": ["Concurrent MAOI use (within 14 days)", "Pimozide co-administration", "Hypersensitivity to sertraline"],
            "monitoring": ["Mental health (suicidality, especially in young adults)", "Serotonin syndrome signs", "Serum sodium (SIADH risk)", "Bleeding risk (with NSAIDs/anticoagulants)", "Liver function", "Weight changes"],
            "pregnancy_category": "C - Risk cannot be ruled out",
            "formulary_tier": {"Medicare": 1, "Aetna": 1, "UnitedHealthcare": 1, "Cigna": 1, "BCBS": 1},
            "generic_available": True
        },
        "metoprolol": {
            "brand_names": ["Lopressor", "Toprol XL"],
            "drug_class": "Beta-1 Selective Adrenergic Blocker",
            "indications": ["Hypertension", "Heart failure", "Angina pectoris", "Post-MI", "Atrial fibrillation (rate control)", "Migraine prophylaxis (off-label)"],
            "route": "Oral",
            "common_dosage": "25-200 mg/day (succinate: 25-200 mg once daily; tartrate: 25-100 mg twice daily)",
            "black_box_warning": None,
            "major_interactions": ["verapamil", "diltiazem", "digoxin", "clonidine", "ritodrine", "mao_inhibitors", "barbiturates"],
            "moderate_interactions": ["amiodarone", "fluoxetine", "paroxetine", "quinidine", "propafenone", "hydralazine", "insulin", "phenytoin", "rifampin", "celecoxib", "nsaids", "albuterol"],
            "contraindications": ["Second/third degree AV block", "Sick sinus syndrome", "Severe bradycardia", "Cardiogenic shock", "Severe peripheral arterial disease", "Pheochromocytoma (without alpha blockade)"],
            "monitoring": ["Heart rate", "Blood pressure", "Ejection fraction (heart failure)", "Respiratory function", "Blood glucose (masks hypoglycemia symptoms)"],
            "pregnancy_category": "C - Risk cannot be ruled out",
            "formulary_tier": {"Medicare": 1, "Aetna": 1, "UnitedHealthcare": 1, "Cigna": 1, "BCBS": 1},
            "generic_available": True
        },
        "clopidogrel": {
            "brand_names": ["Plavix"],
            "drug_class": "Antiplatelet Agent (Thienopyridine)",
            "indications": ["Acute coronary syndrome", "Post-stent placement", "Secondary stroke prevention", "Peripheral arterial disease"],
            "route": "Oral",
            "common_dosage": "75 mg once daily (300-600 mg loading dose for ACS)",
            "black_box_warning": None,
            "major_interactions": ["omeprazole", "esomeprazole", "warfarin", "aspirin", "naproxen", "ibuprofen", "repaglinide", "fluconazole", "ketoconazole", "ciprofloxacin", "fluvoxamine", "fluoxetine", "carbamazepine", "rifampin", "ticagrelor"],
            "moderate_interactions": ["atorvastatin", "simvastatin", "bupropion", "duloxetine", "tamoxifen", "voriconazole", "etravirine", "cefoperazone", "ceftazidime"],
            "contraindications": ["Active pathological bleeding (peptic ulcer, intracranial hemorrhage)", "Hypersensitivity to clopidogrel"],
            "monitoring": ["Signs of bleeding", "CBC with platelet count", "CYP2C19 genotype (poor metabolizers have reduced response)"],
            "pregnancy_category": "B - No evidence of risk in humans",
            "formulary_tier": {"Medicare": 2, "Aetna": 2, "UnitedHealthcare": 2, "Cigna": 2, "BCBS": 2},
            "generic_available": True
        },
        "insulin_glargine": {
            "brand_names": ["Lantus", "Basaglar", "Toujeo", "Semglee"],
            "drug_class": "Insulin (Long-Acting)",
            "indications": ["Type 1 diabetes mellitus", "Type 2 diabetes mellitus"],
            "route": "Subcutaneous injection",
            "common_dosage": "10-80 units once daily (individualized)",
            "black_box_warning": "Never share insulin pens or syringes between patients. Sharing poses risk of transmission of blood-borne pathogens.",
            "major_interactions": ["alcohol", "beta_blockers", "clonidine", "lithium", "pentamidine", "somatostatin_analogues", "sympathomimetics"],
            "moderate_interactions": ["ace_inhibitors", "arbs", "disopyramide", "fenfluramine", "fibrates", "fluoxetine", "mao_inhibitors", "oral_hypoglycemics", "prasugrel", "sulfonamide_antibiotics"],
            "contraindications": ["Hypoglycemia episodes", "Known hypersensitivity to insulin glargine"],
            "monitoring": ["Blood glucose (self-monitoring)", "Hemoglobin A1c", "Hypoglycemia symptoms", "Weight", "Injection site reactions", "Potassium levels"],
            "pregnancy_category": "C - Risk cannot be ruled out (insulin generally preferred in pregnancy)",
            "formulary_tier": {"Medicare": 2, "Aetna": 2, "UnitedHealthcare": 2, "Cigna": 2, "BCBS": 2},
            "generic_available": True
        },
        "fluoxetine": {
            "brand_names": ["Prozac"],
            "drug_class": "Selective Serotonin Reuptake Inhibitor (SSRI)",
            "indications": ["Major depressive disorder", "OCD", "Bulimia nervosa", "Panic disorder", "PMDD"],
            "route": "Oral",
            "common_dosage": "20-80 mg once daily",
            "black_box_warning": "Suicidal thoughts and behaviors: Increased risk in children, adolescents, and young adults. Monitor for clinical worsening and emergence of suicidal thoughts.",
            "major_interactions": ["pimozide", "thioridazine", "mao_inhibitors", "linezolid", "methylene_blue", "tramadol", "tryptophan", "meperidine"],
            "moderate_interactions": ["warfarin", "aspirin", "nsaids", "clopidogrel", "metoprolol", "carbamazepine", "phenytoin", "tricyclic_antidepressants", "lithium", "buspirone", "fentanyl", "triptans", "tamoxifen"],
            "contraindications": ["Concurrent MAOI use (within 14 days)", "Pimozide co-administration", "Thioridazine co-administration", "Hypersensitivity"],
            "monitoring": ["Mental health status", "Suicidal ideation", "Serotonin syndrome signs", "Bleeding risk", "Weight changes", "Serum sodium"],
            "pregnancy_category": "C - Risk cannot be ruled out",
            "formulary_tier": {"Medicare": 1, "Aetna": 1, "UnitedHealthcare": 1, "Cigna": 1, "BCBS": 1},
            "generic_available": True
        },
        "albuterol": {
            "brand_names": ["ProAir HFA", "Ventolin HFA", "ProAir RespiClick"],
            "drug_class": "Beta-2 Adrenergic Agonist (Short-Acting)",
            "indications": ["Bronchospasm (asthma)", "Exercise-induced bronchospasm", "COPD exacerbation"],
            "route": "Inhalation",
            "common_dosage": "2 puffs q4-6h PRN or before exercise",
            "black_box_warning": None,
            "major_interactions": ["beta_blockers", "mao_inhibitors", "tricyclic_antidepressants"],
            "moderate_interactions": ["digoxin", "diuretics", "theophylline", "methylxanthines", "levodopa", "thyroid_hormones"],
            "contraindications": ["Hypersensitivity to albuterol or any component"],
            "monitoring": ["Respiratory function (peak flow, spirometry)", "Heart rate", "Serum potassium (hypokalemia risk)", "Blood glucose (hyperglycemia risk)"],
            "pregnancy_category": "C - Risk cannot be ruled out",
            "formulary_tier": {"Medicare": 1, "Aetna": 1, "UnitedHealthcare": 1, "Cigna": 1, "BCBS": 1},
            "generic_available": True
        },
        "losartan": {
            "brand_names": ["Cozaar"],
            "drug_class": "Angiotensin II Receptor Blocker (ARB)",
            "indications": ["Hypertension", "Diabetic nephropathy (Type 2)", "Heart failure (ACE inhibitor intolerant)", "Stroke reduction in hypertensive LVH"],
            "route": "Oral",
            "common_dosage": "25-100 mg once daily",
            "black_box_warning": None,
            "major_interactions": ["aliskiren", "lithium", "potassium_supplements", "spironolactone", "nsaids", "ace_inhibitors"],
            "moderate_interactions": ["fluconazole", "rifampin", "phenobarbital", "indomethacin", "cimetidine", "colestipol", "warfarin", "aspirin"],
            "contraindications": ["Pregnancy (2nd/3rd trimester)", "Bilateral renal artery stenosis", "Hyperkalemia", "Co-administration with aliskiren in diabetics"],
            "monitoring": ["Blood pressure", "Serum potassium", "Renal function", "Liver function"],
            "pregnancy_category": "D - Positive evidence of risk",
            "formulary_tier": {"Medicare": 1, "Aetna": 1, "UnitedHealthcare": 1, "Cigna": 1, "BCBS": 1},
            "generic_available": True
        },
        "gabapentin": {
            "brand_names": ["Neurontin", "Gralise", "Horizant"],
            "drug_class": "Anticonvulsant / Analgesic (Structural analogue of GABA)",
            "indications": ["Epilepsy (adjunctive)", "Postherpetic neuralgia", "Neuropathic pain (off-label)", "Restless legs syndrome"],
            "route": "Oral",
            "common_dosage": "300-3600 mg/day in divided doses",
            "black_box_warning": None,
            "major_interactions": ["alcohol", "opioids", "mao_inhibitors", "orlistat"],
            "moderate_interactions": ["morphine", "hydrocodone", "cimetidine", "antacids", "hydrocodone", "naproxen"],
            "contraindications": ["Hypersensitivity to gabapentin"],
            "monitoring": ["Renal function (dose adjustment)", "Mental health (suicidal ideation risk per FDA warning for anticonvulsants class)", "Signs of abuse/dependence"],
            "pregnancy_category": "C - Risk cannot be ruled out",
            "formulary_tier": {"Medicare": 1, "Aetna": 1, "UnitedHealthcare": 1, "Cigna": 1, "BCBS": 1},
            "generic_available": True
        },
        "hydrochlorothiazide": {
            "brand_names": ["Microzide", "HydroDIURIL", "Oretic"],
            "drug_class": "Thiazide Diuretic",
            "indications": ["Hypertension", "Edema (heart failure, hepatic cirrhosis, renal dysfunction, steroid therapy)", "Nephrolithiasis (calcium) prevention"],
            "route": "Oral",
            "common_dosage": "12.5-50 mg once daily",
            "black_box_warning": None,
            "major_interactions": ["lithium", "digoxin", "nsaids", "ace_inhibitors", "arb", "succinylcholine"],
            "moderate_interactions": ["warfarin", "carbamazepine", "cyclosporine", "tacrolimus", "vitamin_d", "calcium_supplements", "corticosteroids", "metformin", "insulin", "allopurinol", "cholestyramine", "colestipol"],
            "contraindications": ["Anuria", "Severe renal impairment", "Hypersensitivity to sulfonamide-derived drugs", "Refractory hypokalemia/hyponatremia", "Hypercalcemia"],
            "monitoring": ["Serum electrolytes (potassium, sodium, magnesium)", "Renal function", "Blood glucose", "Uric acid", "Blood pressure", "Lipid panel"],
            "pregnancy_category": "B - No evidence of risk (generally; caution in 3rd trimester)",
            "formulary_tier": {"Medicare": 1, "Aetna": 1, "UnitedHealthcare": 1, "Cigna": 1, "BCBS": 1},
            "generic_available": True
        },
        "montelukast": {
            "brand_names": ["Singulair"],
            "drug_class": "Leukotriene Receptor Antagonist",
            "indications": ["Asthma (prophylaxis and maintenance)", "Allergic rhinitis", "Exercise-induced bronchoconstriction"],
            "route": "Oral",
            "common_dosage": "10 mg once daily (adults); 4-5 mg (pediatric based on age)",
            "black_box_warning": "Serious neuropsychiatric events: Post-marketing reports include agitation, depression, suicidal thinking and behavior, and other mental health changes. Monitor for behavioral and mood changes.",
            "major_interactions": ["phenobarbital", "rifampin", "carbamazepine", "phenytoin"],
            "moderate_interactions": ["gemfibrozil", "itraconazole"],
            "contraindications": ["Hypersensitivity to montelukast", "Not for acute asthma exacerbations"],
            "monitoring": ["Behavioral/mood changes", "Asthma control (symptoms, peak flow)", "Eosinophil counts (Churg-Strauss risk)"],
            "pregnancy_category": "B - No evidence of risk in humans",
            "formulary_tier": {"Medicare": 2, "Aetna": 2, "UnitedHealthcare": 2, "Cigna": 2, "BCBS": 2},
            "generic_available": True
        },
        "meloxicam": {
            "brand_names": ["Mobic", "Vivlodex"],
            "drug_class": "NSAID (Enolic Acid Derivative / Oxicam)",
            "indications": ["Osteoarthritis", "Rheumatoid arthritis", "Juvenile rheumatoid arthritis"],
            "route": "Oral",
            "common_dosage": "7.5-15 mg once daily",
            "black_box_warning": "Cardiovascular and GI risks: (1) Increased risk of serious cardiovascular thrombotic events (MI, stroke) which may be fatal. (2) Increased risk of serious GI adverse events (bleeding, ulceration, perforation) which may be fatal. Use lowest effective dose for shortest duration.",
            "major_interactions": ["warfarin", "aspirin", "ace_inhibitors", "arb", "lithium", "methotrexate", "cyclosporine", "pemetrexed", "tacrolimus"],
            "moderate_interactions": ["furosemide", "digoxin", "cholestyramine", "cimetidine", "aspirin_low_dose", "prednisone", "citalopram", "fluoxetine", "sertraline"],
            "contraindications": ["Active GI bleeding/ulceration", "ASA/NSAID-induced asthma", "Severe renal impairment", "Third trimester pregnancy", "CABG perioperative pain", "Hypersensitivity to NSAIDs"],
            "monitoring": ["Blood pressure", "Renal function", "Liver function", "CBC", "GI symptoms", "Cardiovascular status"],
            "pregnancy_category": "C (1st/2nd trimester); D (3rd trimester)",
            "formulary_tier": {"Medicare": 1, "Aetna": 1, "UnitedHealthcare": 1, "Cigna": 1, "BCBS": 1},
            "generic_available": True
        },
        "tamsulosin": {
            "brand_names": ["Flomax"],
            "drug_class": "Alpha-1 Adrenergic Blocker (Selective)",
            "indications": ["Benign prostatic hyperplasia (BPH)"],
            "route": "Oral",
            "common_dosage": "0.4 mg once daily (30 min after same meal)",
            "black_box_warning": None,
            "major_interactions": ["cimetidine", "ketoconazole", "clarithromycin", "itraconazole", "ritonavir", "fluconazole"],
            "moderate_interactions": ["warfarin", "amlodipine", "atenolol", "metoprolol", "enalapril", "furosemide", "digoxin", "sildenafil", "tadalafil", "vardenafil", "theophylline", "tramadol"],
            "contraindications": ["Hypersensitivity to tamsulosin", "History of intraoperative floppy iris syndrome (caution with cataract surgery)"],
            "monitoring": ["Orthostatic hypotension", "Prostate symptoms (IPSS score)", "PSA (does not affect significantly)", "Intraoperative floppy iris syndrome risk", "Renal function (severe impairment)"],
            "pregnancy_category": "B - No evidence of risk (not used in women)",
            "formulary_tier": {"Medicare": 1, "Aetna": 1, "UnitedHealthcare": 1, "Cigna": 1, "BCBS": 1},
            "generic_available": True
        },
        "escitalopram": {
            "brand_names": ["Lexapro"],
            "drug_class": "Selective Serotonin Reuptake Inhibitor (SSRI)",
            "indications": ["Major depressive disorder", "Generalized anxiety disorder"],
            "route": "Oral",
            "common_dosage": "10-20 mg once daily",
            "black_box_warning": "Suicidal thoughts and behaviors: Increased risk in children, adolescents, and young adults. Monitor for clinical worsening and emergence of suicidal thoughts.",
            "major_interactions": ["pimozide", "mao_inhibitors", "linezolid", "methylene_blue", "tramadol", "tryptophan", "meperidine", "triptans", "fentanyl"],
            "moderate_interactions": ["warfarin", "aspirin", "nsaids", "cimetidine", "metoprolol", "carbamazepine", "lithium", "clopidogrel", "rasagiline", "selegiline", "desipramine", "omeprazole"],
            "contraindications": ["Concurrent MAOI use (within 14 days)", "Pimozide co-administration", "Hypersensitivity", "QT prolongation risk (dose dependent)"],
            "monitoring": ["Mental health (suicidality)", "Serotonin syndrome signs", "Electrolytes (sodium/SIADH)", "QTc interval (at higher doses)", "Bleeding risk", "Weight changes"],
            "pregnancy_category": "C - Risk cannot be ruled out",
            "formulary_tier": {"Medicare": 1, "Aetna": 1, "UnitedHealthcare": 1, "Cigna": 1, "BCBS": 1},
            "generic_available": True
        },
        "rosuvastatin": {
            "brand_names": ["Crestor"],
            "drug_class": "HMG-CoA Reductase Inhibitor (Statin)",
            "indications": ["Hyperlipidemia", "Prevention of cardiovascular events", "Familial hypercholesterolemia", "Atherosclerosis", "Mixed dyslipidemia"],
            "route": "Oral",
            "common_dosage": "5-40 mg once daily",
            "black_box_warning": None,
            "major_interactions": ["cyclosporine", "gemfibrozil", "atazanavir", "ritonavir", "lopinavir", "elbasvir", "grazoprevir", "danazol", "fusidic_acid"],
            "moderate_interactions": ["warfarin", "fenofibrate", "ezetimibe", "spironolactone", "ketoconazole", "fluconazole", "erythromycin", "clofibrate", "colchicine", "niacin"],
            "contraindications": ["Active liver disease", "Pregnancy", "Breastfeeding", "Unexplained persistent transaminase elevation", "Asian patients (lower starting dose: 5 mg)"],
            "monitoring": ["Lipid panel", "Liver function tests", "CK if muscle symptoms", "Proteinuria (especially at higher doses)", "Blood glucose"],
            "pregnancy_category": "X - Contraindicated",
            "formulary_tier": {"Medicare": 2, "Aetna": 2, "UnitedHealthcare": 2, "Cigna": 2, "BCBS": 2},
            "generic_available": True
        },
        "apixaban": {
            "brand_names": ["Eliquis"],
            "drug_class": "Direct Oral Anticoagulant (Factor Xa Inhibitor)",
            "indications": ["Non-valvular atrial fibrillation stroke prevention", "Deep vein thrombosis treatment", "Pulmonary embolism treatment", "DVT/PE extended prophylaxis", "Post-orthopedic surgery DVT prophylaxis"],
            "route": "Oral",
            "common_dosage": "5 mg twice daily (2.5 mg BID if criteria met for dose reduction)",
            "black_box_warning": "Premature discontinuation increases thrombotic events risk. Do not discontinue without adequate anticoagulant replacement. Epidural/spinal hematoma risk with neuraxial anesthesia.",
            "major_interactions": ["ketoconazole", "itraconazole", "ritonavir", "clarithromycin", "carbamazepine", "phenytoin", "rifampin", "st_johns_wort", "aspirin", "clopidogrel", "warfarin", "nsaids"],
            "moderate_interactions": ["diltiazem", "naproxen", "amiodarone", "quinidine", "verapamil", "prednisone", "selective_serotonin_reuptake_inhibitors"],
            "contraindications": ["Active pathological bleeding", "Severe hypersensitivity", "Valvular atrial fibrillation (not studied)", "Triple antithrombotic therapy generally contraindicated"],
            "monitoring": ["Signs of bleeding", "CBC", "Renal function (dose adjustment for Cr < 30)", "Anti-Xa levels if needed (not routine)", "Liver function"],
            "pregnancy_category": "B - No evidence of risk in humans",
            "formulary_tier": {"Medicare": 3, "Aetna": 3, "UnitedHealthcare": 3, "Cigna": 3, "BCBS": 3},
            "generic_available": False
        },
    }

    # --- Interaction severity definitions ---
    INTERACTION_SEVERITY = {
        "major": {
            "level": "major",
            "description": "Significant clinical risk; combination should be avoided or used only with close monitoring",
            "action": "Avoid combination. If clinically necessary, monitor closely and adjust doses."
        },
        "moderate": {
            "level": "moderate",
            "description": "Potential interaction that may require dose adjustment or monitoring",
            "action": "Monitor for effects. May need dose adjustment or additional monitoring."
        }
    }

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "")
        drug_name = kwargs.get("drug_name", "").strip().lower()
        drug_list = kwargs.get("drug_list", [])
        payer = kwargs.get("payer", "").strip()

        if not action:
            return SkillResult(success=False, error="Action is required: lookup, check_interactions, or formulary_info")

        try:
            if action == "lookup":
                if not drug_name:
                    return SkillResult(success=False, error="drug_name is required for lookup")
                result = self._lookup_drug(drug_name)
            elif action == "check_interactions":
                if not drug_list or len(drug_list) < 2:
                    return SkillResult(success=False, error="At least 2 drugs required for interaction check")
                result = self._check_interactions([d.strip().lower() for d in drug_list])
            elif action == "formulary_info":
                if not drug_name:
                    return SkillResult(success=False, error="drug_name is required for formulary_info")
                result = self._get_formulary_info(drug_name, payer)
            else:
                return SkillResult(success=False, error=f"Unknown action: {action}")

            return SkillResult(success=True, data=result)
        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _find_drug(self, name: str) -> Optional[Dict[str, Any]]:
        """Find drug by generic or brand name."""
        name = name.lower().strip()
        if name in self.DRUG_DATABASE:
            return {"generic_name": name, **self.DRUG_DATABASE[name]}
        for generic, info in self.DRUG_DATABASE.items():
            if name in generic.lower() or name in [b.lower() for b in info.get("brand_names", [])]:
                return {"generic_name": generic, **info}
        return None

    def _lookup_drug(self, drug_name: str) -> Dict[str, Any]:
        """Look up complete drug information."""
        drug = self._find_drug(drug_name)
        if not drug:
            return {
                "drug_name": drug_name,
                "found": False,
                "message": f"Drug '{drug_name}' not found in database. Available drugs: {', '.join(list(self.DRUG_DATABASE.keys())[:15])}...",
                "suggestion": "Try the generic name or a known brand name."
            }

        generic = drug["generic_name"]
        return {
            "found": True,
            "generic_name": generic,
            "brand_names": drug["brand_names"],
            "drug_class": drug["drug_class"],
            "indications": drug["indications"],
            "route": drug["route"],
            "common_dosage": drug["common_dosage"],
            "black_box_warning": drug["black_box_warning"],
            "contraindications": drug["contraindications"],
            "monitoring": drug["monitoring"],
            "pregnancy_category": drug["pregnancy_category"],
            "generic_available": drug["generic_available"],
            "major_interactions": drug["major_interactions"],
            "moderate_interactions": drug["moderate_interactions"]
        }

    def _check_interactions(self, drug_list: List[str]) -> Dict[str, Any]:
        """Check for drug-drug interactions between all pairs."""
        interactions = []
        drugs_found = {}
        drugs_not_found = []

        for name in drug_list:
            drug = self._find_drug(name)
            if drug:
                drugs_found[name] = drug
            else:
                drugs_not_found.append(name)

        if len(drugs_found) < 2:
            return {
                "drugs_checked": drug_list,
                "found_count": len(drugs_found),
                "not_found": drugs_not_found,
                "interactions": [],
                "message": "Fewer than 2 drugs found in database. Cannot check interactions."
            }

        found_names = list(drugs_found.keys())

        for i in range(len(found_names)):
            for j in range(i + 1, len(found_names)):
                drug_a = drugs_found[found_names[i]]
                drug_b = drugs_found[found_names[j]]
                generic_a = drug_a["generic_name"]
                generic_b = drug_b["generic_name"]

                # Check drug A interactions for drug B
                for inter_name in drug_a.get("major_interactions", []):
                    if inter_name == generic_b or inter_name in generic_b or generic_b in inter_name:
                        interactions.append({
                            "drug_a": found_names[i],
                            "drug_a_generic": generic_a,
                            "drug_b": found_names[j],
                            "drug_b_generic": generic_b,
                            "severity": "major",
                            "description": f"Major interaction between {generic_a} and {generic_b}",
                            "action": "Avoid combination. If clinically necessary, use with extreme caution and close monitoring. Consider alternative therapy.",
                            "direction": f"{generic_a} affects {generic_b}"
                        })

                for inter_name in drug_a.get("moderate_interactions", []):
                    if inter_name == generic_b or inter_name in generic_b or generic_b in inter_name:
                        interactions.append({
                            "drug_a": found_names[i],
                            "drug_a_generic": generic_a,
                            "drug_b": found_names[j],
                            "drug_b_generic": generic_b,
                            "severity": "moderate",
                            "description": f"Moderate interaction between {generic_a} and {generic_b}",
                            "action": "Monitor for effects. May require dose adjustment or additional monitoring.",
                            "direction": f"{generic_a} affects {generic_b}"
                        })

                # Check drug B interactions for drug A
                for inter_name in drug_b.get("major_interactions", []):
                    if inter_name == generic_a or inter_name in generic_a or generic_a in inter_name:
                        # Avoid duplicate
                        existing = [i for i in interactions
                                    if i["drug_a_generic"] == generic_b and i["drug_b_generic"] == generic_a
                                    and i["severity"] == "major"]
                        if not existing:
                            interactions.append({
                                "drug_a": found_names[j],
                                "drug_a_generic": generic_b,
                                "drug_b": found_names[i],
                                "drug_b_generic": generic_a,
                                "severity": "major",
                                "description": f"Major interaction between {generic_b} and {generic_a}",
                                "action": "Avoid combination. If clinically necessary, use with extreme caution and close monitoring. Consider alternative therapy.",
                                "direction": f"{generic_b} affects {generic_a}"
                            })

                for inter_name in drug_b.get("moderate_interactions", []):
                    if inter_name == generic_a or inter_name in generic_a or generic_a in inter_name:
                        existing = [i for i in interactions
                                    if i["drug_a_generic"] == generic_b and i["drug_b_generic"] == generic_a
                                    and i["severity"] == "moderate"]
                        if not existing:
                            interactions.append({
                                "drug_a": found_names[j],
                                "drug_a_generic": generic_b,
                                "drug_b": found_names[i],
                                "drug_b_generic": generic_a,
                                "severity": "moderate",
                                "description": f"Moderate interaction between {generic_b} and {generic_a}",
                                "action": "Monitor for effects. May require dose adjustment or additional monitoring.",
                                "direction": f"{generic_b} affects {generic_a}"
                            })

        # Sort: major first
        interactions.sort(key=lambda x: 0 if x["severity"] == "major" else 1)

        major_count = sum(1 for i in interactions if i["severity"] == "major")
        moderate_count = sum(1 for i in interactions if i["severity"] == "moderate")

        if major_count > 0:
            risk_level = "high"
        elif moderate_count > 0:
            risk_level = "moderate"
        else:
            risk_level = "low"

        return {
            "drugs_checked": drug_list,
            "drugs_found": found_names,
            "drugs_not_found": drugs_not_found,
            "total_interactions": len(interactions),
            "major_interactions": major_count,
            "moderate_interactions": moderate_count,
            "risk_level": risk_level,
            "interactions": interactions,
            "summary": f"Found {major_count} major and {moderate_count} moderate interaction(s) among {len(drugs_found)} drugs." if interactions else f"No known interactions found among {', '.join(found_names)} in the database."
        }

    def _get_formulary_info(self, drug_name: str, payer: str) -> Dict[str, Any]:
        """Get formulary information for a drug."""
        drug = self._find_drug(drug_name)
        if not drug:
            return {
                "drug_name": drug_name,
                "found": False,
                "message": f"Drug '{drug_name}' not found in database."
            }

        generic = drug["generic_name"]
        tiers = drug.get("formulary_tier", {})

        if payer:
            payer_lower = payer.lower()
            matching_tier = None
            for key, tier in tiers.items():
                if payer_lower in key.lower() or key.lower() in payer_lower:
                    matching_tier = {"payer": key, "tier": tier}
                    break
        else:
            matching_tier = None

        tier_descriptions = {
            1: "Preferred Generic - Lowest copay",
            2: "Non-Preferred Generic or Preferred Brand - Moderate copay",
            3: "Non-Preferred Brand - Higher copay",
            4: "Specialty - Highest copay / May require prior authorization",
            5: "Not covered or specialty with restrictions"
        }

        all_tiers = []
        for payer_name, tier_num in tiers.items():
            all_tiers.append({
                "payer": payer_name,
                "tier": tier_num,
                "description": tier_descriptions.get(tier_num, f"Tier {tier_num}")
            })

        result = {
            "drug_name": drug_name,
            "generic_name": generic,
            "brand_names": drug["brand_names"],
            "generic_available": drug["generic_available"],
            "formulary_tiers": all_tiers,
            "prior_authorization_likely": any(t >= 3 for t in tiers.values()),
            "step_therapy_likely": any(t >= 3 for t in tiers.values())
        }

        if matching_tier:
            result["specific_payer"] = matching_tier
            result["specific_payer_description"] = tier_descriptions.get(matching_tier["tier"], f"Tier {matching_tier['tier']}")

        return result