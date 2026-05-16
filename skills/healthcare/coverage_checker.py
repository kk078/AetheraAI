"""
Aethera AI - Coverage Checker Skill

LCD/NCD medical necessity criteria checking. Contains common LCD/NCD
references with CPT/diagnosis criteria. Supports search by CPT, search
by diagnosis, check coverage criteria, and get documentation requirements.
"""

from typing import Dict, Any, List, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill


@skill(name="coverage_checker", category="healthcare")
class CoverageCheckerSkill(AetheraSkill):
    """
    LCD/NCD medical necessity criteria checker.
    """

    @property
    def name(self) -> str:
        return "coverage_checker"

    @property
    def description(self) -> str:
        return "Check LCD/NCD medical necessity criteria: search by CPT, search by diagnosis, check coverage, get documentation requirements"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["search_by_cpt", "search_by_diagnosis", "check_coverage", "documentation_requirements"],
                    "description": "Action: search_by_cpt, search_by_diagnosis, check_coverage (CPT + diagnosis), documentation_requirements"
                },
                "cpt_code": {
                    "type": "string",
                    "description": "CPT/HCPCS procedure code"
                },
                "diagnosis_code": {
                    "type": "string",
                    "description": "ICD-10-CM diagnosis code"
                },
                "contractor": {
                    "type": "string",
                    "description": "MAC/contractor name for LCD-specific lookups (optional)"
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
            {"input": {"action": "search_by_cpt", "cpt_code": "93306"}},
            {"input": {"action": "check_coverage", "cpt_code": "97110", "diagnosis_code": "M54.5"}},
            {"input": {"action": "documentation_requirements", "cpt_code": "64483"}}
        ]

    # --- NCD (National Coverage Determinations) database ---
    NCD_DATABASE: Dict[str, Dict[str, Any]] = {
        "NCD 220.1": {
            "title": "Echocardiography",
            "cpt_codes": ["93306", "93307", "93308", "93350", "93351"],
            "covered_diagnoses": ["I10", "I25.10", "I42.9", "I48.91", "I50.9", "I51.9",
                                  "Q20.5", "Q21.1", "Q22.1", "Q23.3", "Z95.0", "Z95.2",
                                  "R01.0", "R00.0", "R01.1", "I34.0", "I35.0", "I35.2"],
            "criteria": "Echocardiography is covered for the evaluation of suspected or known cardiac conditions including valvular disease, cardiomyopathy, pericardial disease, cardiac masses, and congenital heart disease. Must be ordered by treating physician.",
            "frequency_limits": "Repeat studies covered when there is a change in clinical status, new symptoms, or to evaluate response to treatment. Routine screening echocardiograms are not covered except for specific indications.",
            "documentation_requirements": [
                "Physician order with clinical indication",
                "Documentation of signs/symptoms or suspected condition",
                "Reason for study (initial evaluation vs. follow-up)",
                "If repeat study: documentation of clinical change since last study"
            ],
            "non_coverage": "Screening echocardiography in asymptomatic patients without known cardiac disease is not covered."
        },
        "NCD 220.2": {
            "title": "Cardiac Rehabilitation Programs",
            "cpt_codes": ["93797", "93798"],
            "covered_diagnoses": ["I21.9", "I22.9", "I25.10", "I25.110", "I25.5", "I42.9",
                                  "I50.9", "Z95.0", "Z95.1", "Z95.2", "Z95.3"],
            "criteria": "Covered for patients with acute MI within last 12 months, CABG, stable angina, heart valve repair/replacement, PCI with stenting, heart transplant, or stable chronic heart failure.",
            "frequency_limits": "Up to 36 sessions covered. May qualify for up to 36 additional sessions with medical necessity justification.",
            "documentation_requirements": [
                "Qualifying diagnosis documentation",
                "Physician referral",
                "Exercise tolerance test results",
                "Individualized treatment plan"
            ],
            "non_coverage": "Cardiac rehab without qualifying diagnosis or for patients who cannot safely participate."
        },
        "NCD 220.6": {
            "title": "Positron Emission Tomography (PET) Scans",
            "cpt_codes": ["78811", "78812", "78813", "78814", "78815", "78816"],
            "covered_diagnoses": ["C34.90", "C50.919", "C18.9", "C25.9", "R91.8", "G30.9",
                                  "G20", "F02.80"],
            "criteria": "PET scans covered for: (1) characterization of solitary pulmonary nodules, (2) initial staging of non-small cell lung cancer, (3) diagnosis of Alzheimer's disease when specific criteria met, (4) refractory seizure evaluation.",
            "frequency_limits": "Limited based on clinical indication. Not for general screening or surveillance.",
            "documentation_requirements": [
                "Physician order with specific clinical indication",
                "Prior imaging results (CT/MRI) for most indications",
                "Documentation of failed or inconclusive conventional imaging",
                "For Alzheimer's: cognitive assessment documentation"
            ],
            "non_coverage": "PET for cancer screening in asymptomatic patients, surveillance after completed treatment, or when conventional imaging is adequate."
        },
        "NCD 240.2": {
            "title": "Mammography Screening",
            "cpt_codes": ["77065", "77066", "77067"],
            "covered_diagnoses": ["Z12.31", "Z12.39", "Z85.840", "Z85.848", "N63.0", "N63.9", "R92.0", "R92.1"],
            "criteria": "Screening mammography covered annually for women 40 and older. Covered for women 35-39 at high risk. Diagnostic mammography covered when signs/symptoms present.",
            "frequency_limits": "Screening: annual for women 40+. Diagnostic: as medically necessary.",
            "documentation_requirements": [
                "Patient age and risk factors",
                "Date of last mammogram (for screening frequency)",
                "For diagnostic: specific signs/symptoms prompting study",
                "Physician order"
            ],
            "non_coverage": "Screening mammography for women under 35 (except high risk). More frequent than annual screening without medical necessity."
        },
        "NCD 20.1": {
            "title": "Physical Therapy",
            "cpt_codes": ["97110", "97112", "97113", "97116", "97140", "97150",
                         "97530", "97535", "97537", "97750", "97755", "97760",
                         "97010", "97012", "97014", "97016", "97018", "97022", "97032", "97033", "97034", "97035", "97036", "97039"],
            "covered_diagnoses": ["M54.5", "M54.2", "M17.11", "M17.12", "M16.11", "M16.12",
                                  "M80.00XA", "S72.001A", "M62.81", "G89.29", "G89.4",
                                  "M47.816", "M47.817", "M47.818", "M54.12", "M54.17",
                                  "M54.18", "M79.3", "M79.1", "R26.9", "G83.3", "G83.4",
                                  "G83.89", "M84.65XA", "M84.651A"],
            "criteria": "Physical therapy covered when: (1) there is a documented medical condition requiring PT, (2) the services are expected to produce reasonable improvement, (3) services require the skills of a PT, (4) the patient has the potential for functional improvement.",
            "frequency_limits": "No specific national limit, but must show continued medical necessity. Progress must be documented. Maintenance therapy not covered.",
            "documentation_requirements": [
                "Physician order/referral for physical therapy",
                "Initial evaluation with functional limitations",
                "Measurable goals and treatment plan",
                "Progress notes showing functional improvement",
                "Documentation of skilled care need (not maintenance)",
                "Time-based documentation for each modality",
                "Re-evaluation if no progress after reasonable period"
            ],
            "non_coverage": "Maintenance therapy (no expectation of improvement), services not requiring PT skills, palliative therapy without rehabilitative potential."
        },
    }

    # --- LCD (Local Coverage Determinations) database ---
    LCD_DATABASE: Dict[str, Dict[str, Any]] = {
        "LCD L35009": {
            "title": "Epidural Steroid Injections",
            "contractor": "Novitas Solutions",
            "cpt_codes": ["62321", "62323", "62325", "62326", "62327", "64483", "64484", "64485", "64486", "64492", "64493", "64494", "64495"],
            "covered_diagnoses": ["M54.5", "M54.12", "M54.16", "M54.17", "M54.18", "M47.816",
                                  "M47.817", "M47.818", "M47.26", "M47.27", "M47.28",
                                  "M51.16", "M51.17", "M51.18", "M54.30", "M54.31", "M54.32",
                                  "G89.29", "M79.3", "M79.7"],
            "criteria": "Covered for patients with radicular pain, sciatica, or spinal stenosis who have failed at least 6 weeks of conservative treatment including physical therapy, NSAIDs, and activity modification. Imaging must confirm structural pathology consistent with symptoms.",
            "frequency_limits": "Maximum 4 injections per year per spinal region. Minimum 2-month interval between injections unless medical necessity documented.",
            "documentation_requirements": [
                "MRI or CT confirming pathology consistent with symptoms",
                "Documentation of at least 6 weeks conservative treatment failure",
                "Specific level and approach documented",
                "Fluoroscopic guidance documentation (if used)",
                "Pre and post-procedure pain assessment",
                "Prior authorization (if required by payer)"
            ],
            "non_coverage": "ESI without documented conservative treatment trial, axial pain without radicular symptoms, more than 4 per year without documentation of continued need."
        },
        "LCD L33646": {
            "title": "Nerve Conduction Studies and EMG",
            "contractor": "Palmetto GBA",
            "cpt_codes": ["95907", "95908", "95909", "95910", "95911", "95912", "95913",
                         "95886", "95887", "95889"],
            "covered_diagnoses": ["G56.00", "G56.01", "G56.02", "G56.10", "G56.11", "G56.12",
                                  "G57.00", "G57.01", "G57.02", "M79.3", "G71.0", "G71.1",
                                  "G71.2", "G60.9", "G61.9", "G62.9", "E11.40", "E11.42",
                                  "M54.12", "M54.17", "M54.18", "G83.3", "G83.4"],
            "criteria": "Covered for evaluation of suspected peripheral nerve disorders, radiculopathies, motor neuron disease, and neuromuscular junction disorders. Must be performed by physician with specialized training. Clinical examination must precede testing.",
            "frequency_limits": "Generally one study per clinical condition. Repeat studies covered when there is a change in clinical status or to evaluate disease progression.",
            "documentation_requirements": [
                "Physician order with specific clinical question",
                "Detailed clinical examination documentation",
                "Rationale for each nerve/muscle tested",
                "Physician interpretation and report",
                "Practitioner credentials documentation"
            ],
            "non_coverage": "Screening for neuropathy without symptoms, testing for purely pain conditions without neurological deficits, routine repeat testing without clinical change."
        },
        "LCD L33794": {
            "title": "Transcutaneous Electrical Nerve Stimulation (TENS)",
            "contractor": "Noridian Healthcare Solutions",
            "cpt_codes": ["64550", "E0720", "E0730", "E0735", "E0740", "E0745"],
            "covered_diagnoses": ["G89.29", "M54.5", "M54.2", "M79.3", "M79.1", "R20.0",
                                  "R20.2", "R20.8", "G57.00", "G56.00", "G58.9", "G90.9"],
            "criteria": "TENS covered for patients with chronic, intractable pain who have not responded adequately to conservative treatment. A trial period is required before purchase of DME.",
            "frequency_limits": "Rental for trial period of 1-2 months. Purchase covered if trial demonstrates effective pain relief.",
            "documentation_requirements": [
                "Documentation of chronic pain condition",
                "Documentation of failed conservative treatments",
                "Trial period results and pain relief documentation",
                "Physician order for TENS unit",
                "Functional improvement documentation"
            ],
            "non_coverage": "TENS for acute pain, postoperative pain as sole treatment, or without a documented trial period."
        },
        "LCD L34980": {
            "title": "Hemoglobin A1c Testing",
            "contractor": "First Coast Service Options",
            "cpt_codes": ["83036", "83037"],
            "covered_diagnoses": ["E10.9", "E10.65", "E11.9", "E11.65", "E13.9", "E13.65",
                                  "O24.019", "O24.119", "O24.419", "R73.09", "R73.03"],
            "criteria": "Covered for monitoring glycemic control in patients with diagnosed diabetes mellitus. Frequency depends on diabetes control: quarterly for patients not at goal, twice yearly for patients at goal.",
            "frequency_limits": "Up to 4 times per year for uncontrolled diabetes, 2 times per year for controlled diabetes. Additional testing may be covered with medical necessity documentation.",
            "documentation_requirements": [
                "Diabetes diagnosis documentation",
                "Reason for frequency (controlled vs uncontrolled)",
                "Previous HbA1c results for trending",
                "Treatment plan adjustments based on results"
            ],
            "non_coverage": "HbA1c for screening in patients without diabetes risk factors, more frequent than quarterly without documented medical necessity."
        },
        "LCD L35455": {
            "title": "MRI of the Brain",
            "contractor": "CGS Administrators",
            "cpt_codes": ["70551", "70552", "70553"],
            "covered_diagnoses": ["G43.909", "G43.919", "G40.909", "G40.509", "R47.01",
                                  "R56.00", "G89.29", "R51", "G20", "G30.9", "G47.33",
                                  "G93.9", "R55", "R42", "R41.3", "C71.9", "D33.0",
                                  "D33.1", "D33.2", "Z87.898"],
            "criteria": "MRI brain covered for evaluation of suspected or known intracranial pathology including tumors, stroke, demyelinating disease, infection, developmental anomalies, and trauma. Must be ordered by treating physician with specific clinical question.",
            "frequency_limits": "As medically necessary. Repeat imaging for treatment monitoring or clinical change.",
            "documentation_requirements": [
                "Physician order with specific clinical indication",
                "Neurological examination findings",
                "Reason for MRI vs. CT (if applicable)",
                "If contrast: clinical indication for contrast enhancement",
                "For repeat: documentation of clinical change"
            ],
            "non_coverage": "Screening MRI in asymptomatic patients, MRI for conditions adequately evaluated by CT, MRI without specific clinical question."
        },
        "LCD L36979": {
            "title": "Spinal Manipulation",
            "contractor": "Novitas Solutions",
            "cpt_codes": ["98940", "98941", "98942", "98943"],
            "covered_diagnoses": ["M54.5", "M54.2", "M54.12", "M54.17", "M54.18",
                                  "M99.00", "M99.01", "M99.02", "M99.03", "M99.04",
                                  "M99.05", "M99.06", "M99.07", "M99.08", "M99.09",
                                  "M99.10", "M99.11", "M99.12", "M99.13", "M99.14",
                                  "M99.15", "M99.16", "M99.17", "M99.18", "M99.19"],
            "criteria": "Covered for treatment of spinal subluxation when there is documented spinal segment dysfunction. Must demonstrate functional improvement. X-ray or clinical examination must support subluxation.",
            "frequency_limits": "Up to 12 visits initially. Continued treatment requires documented functional improvement. Chronic maintenance manipulation not covered.",
            "documentation_requirements": [
                "Documentation of spinal subluxation/dysfunction",
                "Initial examination findings",
                "Functional assessment (pain scale, ROM, ADLs)",
                "Treatment plan with goals",
                "Progress notes showing improvement",
                "Re-evaluation every 12 visits"
            ],
            "non_coverage": "Maintenance therapy without expectation of improvement, treatment without documented subluxation, treatment beyond acute/active phase without progress."
        },
        "LCD L37588": {
            "title": "Sleep Studies (Polysomnography)",
            "contractor": "Noridian Healthcare Solutions",
            "cpt_codes": ["95800", "95801", "95805", "95807", "95808", "95810", "95811"],
            "covered_diagnoses": ["G47.33", "G47.30", "G47.00", "G47.01", "G47.09",
                                  "G47.9", "R06.03", "R06.02", "G47.31", "G47.39"],
            "criteria": "Covered for diagnosis of sleep-related breathing disorders (obstructive sleep apnea), narcolepsy, and parasomnias. Must have clinical symptoms (snoring, daytime sleepiness, observed apneas). Home sleep testing covered for OSA suspicion.",
            "frequency_limits": "One diagnostic study typically sufficient. Repeat study covered for treatment titration (CPAP) or clinical change.",
            "documentation_requirements": [
                "Clinical symptoms documentation (snoring, EDS, witnessed apneas)",
                "Epworth Sleepiness Scale or equivalent",
                "STOP-BANG or similar screening tool results",
                "Physician order specifying study type",
                "For CPAP titration: prior diagnostic study results"
            ],
            "non_coverage": "Screening sleep studies without symptoms, studies for insomnia alone, multiple studies without clinical justification."
        },
        "LCD L38151": {
            "title": "Hyperbaric Oxygen Therapy",
            "contractor": "Palmetto GBA",
            "cpt_codes": ["99183"],
            "covered_diagnoses": ["T81.12XA", "L97.529", "L97.539", "M80.00XA", "G93.2",
                                  "T79.0XXA", "T70.3XXA", "M86.9", "K13.69", "G93.41",
                                  "L89.150", "L89.151", "L89.159"],
            "criteria": "Covered for specific conditions including: gas gangrene, acute traumatic ischemia, decompression sickness, carbon monoxide poisoning, necrotizing infections, compromised grafts/flaps, chronic refractory osteomyelitis, radiation necrosis, and diabetic wounds meeting Wagner grade 3+ criteria.",
            "frequency_limits": "Varies by condition. Typically 20-40 sessions for chronic conditions, 1-10 for acute conditions.",
            "documentation_requirements": [
                "Specific qualifying diagnosis documentation",
                "Failed conventional treatment documentation (for chronic conditions)",
                "Wound measurements and photographic documentation",
                "Transcutaneous oxygen measurements (for diabetic wounds)",
                "Treatment plan specifying number of sessions",
                "Physician supervision documentation"
            ],
            "non_coverage": "HBOT for conditions not listed as covered, prophylactic use, or continuation without documented improvement."
        },
        "LCD L38651": {
            "title": "Vitamin D Testing",
            "contractor": "CGS Administrators",
            "cpt_codes": ["82306", "82652"],
            "covered_diagnoses": ["E55.9", "E83.30", "E83.31", "M81.0", "M83.30", "M83.31",
                                  "M83.32", "M83.33", "M83.34", "M83.35", "M83.36",
                                  "K90.0", "E21.0", "E21.3", "Z79.899", "N25.81",
                                  "E20.9", "E21.1", "Q78.0"],
            "criteria": "Vitamin D testing covered for patients with suspected vitamin D deficiency or monitoring treatment of known deficiency. Not covered as routine screening.",
            "frequency_limits": "Testing every 3-6 months for monitoring treatment. Once for initial deficiency diagnosis.",
            "documentation_requirements": [
                "Signs/symptoms of vitamin D deficiency or insufficiency",
                "Risk factors (malabsorption, osteoporosis, chronic kidney disease, etc.)",
                "Previous vitamin D levels (for monitoring)",
                "Treatment documentation (for monitoring response)"
            ],
            "non_coverage": "Routine screening without risk factors or symptoms, more frequent monitoring without clinical justification."
        },
        "LCD L34769": {
            "title": "Wound Care Services",
            "contractor": "First Coast Service Options",
            "cpt_codes": ["97597", "97598", "97602", "97605", "97606"],
            "covered_diagnoses": ["L97.529", "L97.539", "L89.150", "L89.151", "L89.159",
                                  "L89.310", "L89.311", "L89.319", "I70.249", "I70.259",
                                  "E11.622", "E11.621", "I96", "T81.12XA", "S81.802A",
                                  "S81.812A", "S81.822A", "S81.832A", "S81.842A"],
            "criteria": "Wound care covered for active wound treatment when wound is not healing with standard care. Must require skilled services. Must show measurable progress toward healing.",
            "frequency_limits": "As medically necessary while wound shows progress. Re-evaluation required if no improvement after 2-4 weeks.",
            "documentation_requirements": [
                "Wound measurements (length, width, depth)",
                "Wound bed description and exudate",
                "Treatment plan and modalities used",
                "Progress toward healing documented each visit",
                "Physician oversight documentation",
                "Photographic documentation recommended"
            ],
            "non_coverage": "Wound care that does not require skilled services, wound care for wounds healing with standard care, maintenance wound care without improvement potential."
        },
        "LCD L36372": {
            "title": "Botulinum Toxin Injections",
            "contractor": "Novitas Solutions",
            "cpt_codes": ["64612", "64615", "64616", "64617", "64642", "64643", "64644",
                         "64645", "J0585", "J0586", "J0587", "J0588", "J0589"],
            "covered_diagnoses": ["G43.909", "G43.919", "G24.0", "G24.1", "G24.2", "G24.3",
                                  "G24.4", "G24.5", "G24.8", "G24.9", "M79.1", "M79.3",
                                  "G83.3", "G83.4", "G83.89", "N36.43", "R32", "K59.6",
                                  "G71.0", "G71.1", "G71.2"],
            "criteria": "Botulinum toxin injections covered for chronic migraine (15+ headache days/month), cervical dystonia, spasticity, hyperhidrosis, overactive bladder, and other FDA-approved indications. Must have failed or be intolerant of conventional treatment.",
            "frequency_limits": "Minimum 12 weeks between injections for most indications. Chronic migraine: every 12 weeks. Spasticity: every 12 weeks.",
            "documentation_requirements": [
                "Specific diagnosis documentation",
                "Failed conventional treatment documentation",
                "Headache diary (for chronic migraine - 15+ days/month)",
                "Functional assessment before and after injections",
                "Dose and muscles injected documentation",
                "Previous injection response documentation"
            ],
            "non_coverage": "Botulinum toxin for cosmetic purposes, injection intervals less than 12 weeks without documentation, treatment without prior conservative treatment failure."
        },
    }

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "")
        cpt_code = kwargs.get("cpt_code", "").strip()
        diagnosis_code = kwargs.get("diagnosis_code", "").strip().upper()
        contractor = kwargs.get("contractor", "").strip()

        if not action:
            return SkillResult(success=False, error="Action is required")

        try:
            if action == "search_by_cpt":
                if not cpt_code:
                    return SkillResult(success=False, error="cpt_code is required for search_by_cpt")
                result = self._search_by_cpt(cpt_code, contractor)
            elif action == "search_by_diagnosis":
                if not diagnosis_code:
                    return SkillResult(success=False, error="diagnosis_code is required for search_by_diagnosis")
                result = self._search_by_diagnosis(diagnosis_code, contractor)
            elif action == "check_coverage":
                if not cpt_code or not diagnosis_code:
                    return SkillResult(success=False, error="Both cpt_code and diagnosis_code are required for check_coverage")
                result = self._check_coverage(cpt_code, diagnosis_code, contractor)
            elif action == "documentation_requirements":
                if not cpt_code:
                    return SkillResult(success=False, error="cpt_code is required for documentation_requirements")
                result = self._get_documentation_requirements(cpt_code, contractor)
            else:
                return SkillResult(success=False, error=f"Unknown action: {action}")

            return SkillResult(success=True, data=result)
        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _search_by_cpt(self, cpt_code: str, contractor: str) -> Dict[str, Any]:
        """Find coverage policies that include this CPT code."""
        results = []

        for ncd_id, ncd in self.NCD_DATABASE.items():
            if cpt_code in ncd["cpt_codes"]:
                results.append({
                    "policy_id": ncd_id,
                    "policy_type": "NCD",
                    "title": ncd["title"],
                    "criteria_summary": ncd["criteria"][:200] + "..." if len(ncd["criteria"]) > 200 else ncd["criteria"],
                    "covered_diagnoses": ncd["covered_diagnoses"]
                })

        for lcd_id, lcd in self.LCD_DATABASE.items():
            if cpt_code in lcd["cpt_codes"]:
                if contractor and contractor.lower() not in lcd.get("contractor", "").lower():
                    continue
                results.append({
                    "policy_id": lcd_id,
                    "policy_type": "LCD",
                    "title": lcd["title"],
                    "contractor": lcd.get("contractor", ""),
                    "criteria_summary": lcd["criteria"][:200] + "..." if len(lcd["criteria"]) > 200 else lcd["criteria"],
                    "covered_diagnoses": lcd["covered_diagnoses"]
                })

        return {
            "cpt_code": cpt_code,
            "policies_found": len(results),
            "coverage_policies": results,
            "message": f"Found {len(results)} coverage policy(ies) for CPT {cpt_code}" if results else f"No coverage policies found for CPT {cpt_code}"
        }

    def _search_by_diagnosis(self, diagnosis_code: str, contractor: str) -> Dict[str, Any]:
        """Find coverage policies that cover this diagnosis."""
        results = []

        # Match exact code and prefix (e.g., E11.9 matches E11)
        dx_prefix = diagnosis_code.split(".")[0] if "." in diagnosis_code else diagnosis_code

        for ncd_id, ncd in self.NCD_DATABASE.items():
            matched_codes = [d for d in ncd["covered_diagnoses"] if d == diagnosis_code or d.startswith(dx_prefix + ".")]
            if matched_codes:
                results.append({
                    "policy_id": ncd_id,
                    "policy_type": "NCD",
                    "title": ncd["title"],
                    "matching_diagnoses": matched_codes,
                    "applicable_cpt_codes": ncd["cpt_codes"],
                    "criteria_summary": ncd["criteria"][:200] + "..." if len(ncd["criteria"]) > 200 else ncd["criteria"]
                })

        for lcd_id, lcd in self.LCD_DATABASE.items():
            if contractor and contractor.lower() not in lcd.get("contractor", "").lower():
                continue
            matched_codes = [d for d in lcd["covered_diagnoses"] if d == diagnosis_code or d.startswith(dx_prefix + ".")]
            if matched_codes:
                results.append({
                    "policy_id": lcd_id,
                    "policy_type": "LCD",
                    "title": lcd["title"],
                    "contractor": lcd.get("contractor", ""),
                    "matching_diagnoses": matched_codes,
                    "applicable_cpt_codes": lcd["cpt_codes"],
                    "criteria_summary": lcd["criteria"][:200] + "..." if len(lcd["criteria"]) > 200 else lcd["criteria"]
                })

        return {
            "diagnosis_code": diagnosis_code,
            "policies_found": len(results),
            "coverage_policies": results,
            "message": f"Found {len(results)} coverage policy(ies) for diagnosis {diagnosis_code}" if results else f"No coverage policies found for diagnosis {diagnosis_code}"
        }

    def _check_coverage(self, cpt_code: str, diagnosis_code: str, contractor: str) -> Dict[str, Any]:
        """Check if a CPT/diagnosis combination is covered."""
        dx_prefix = diagnosis_code.split(".")[0] if "." in diagnosis_code else diagnosis_code
        covered_by = []
        not_covered_reasons = []

        for ncd_id, ncd in self.NCD_DATABASE.items():
            if cpt_code not in ncd["cpt_codes"]:
                continue
            matched_codes = [d for d in ncd["covered_diagnoses"] if d == diagnosis_code or d.startswith(dx_prefix + ".")]
            if matched_codes:
                covered_by.append({
                    "policy_id": ncd_id,
                    "policy_type": "NCD",
                    "title": ncd["title"],
                    "matching_diagnoses": matched_codes,
                    "criteria": ncd["criteria"],
                    "frequency_limits": ncd["frequency_limits"],
                    "documentation_requirements": ncd["documentation_requirements"]
                })
            else:
                not_covered_reasons.append({
                    "policy_id": ncd_id,
                    "policy_type": "NCD",
                    "title": ncd["title"],
                    "reason": f"Diagnosis {diagnosis_code} not in covered list for {ncd['title']}",
                    "covered_diagnoses": ncd["covered_diagnoses"],
                    "non_coverage_note": ncd.get("non_coverage", "")
                })

        for lcd_id, lcd in self.LCD_DATABASE.items():
            if cpt_code not in lcd["cpt_codes"]:
                continue
            if contractor and contractor.lower() not in lcd.get("contractor", "").lower():
                continue
            matched_codes = [d for d in lcd["covered_diagnoses"] if d == diagnosis_code or d.startswith(dx_prefix + ".")]
            if matched_codes:
                covered_by.append({
                    "policy_id": lcd_id,
                    "policy_type": "LCD",
                    "title": lcd["title"],
                    "contractor": lcd.get("contractor", ""),
                    "matching_diagnoses": matched_codes,
                    "criteria": lcd["criteria"],
                    "frequency_limits": lcd["frequency_limits"],
                    "documentation_requirements": lcd["documentation_requirements"]
                })
            else:
                not_covered_reasons.append({
                    "policy_id": lcd_id,
                    "policy_type": "LCD",
                    "title": lcd["title"],
                    "contractor": lcd.get("contractor", ""),
                    "reason": f"Diagnosis {diagnosis_code} not in covered list for {lcd['title']}",
                    "covered_diagnoses": lcd["covered_diagnoses"],
                    "non_coverage_note": lcd.get("non_coverage", "")
                })

        # Determine overall coverage status
        if covered_by:
            coverage_status = "covered"
            status_detail = f"Diagnosis {diagnosis_code} supports medical necessity for {cpt_code} under {len(covered_by)} policy/policies"
        elif not_covered_reasons:
            coverage_status = "not_covered"
            status_detail = f"Diagnosis {diagnosis_code} does not meet coverage criteria for {cpt_code} under the identified policies"
        else:
            coverage_status = "no_policy_found"
            status_detail = f"No coverage policy found that specifically addresses CPT {cpt_code}. Check with payer for specific requirements."

        return {
            "cpt_code": cpt_code,
            "diagnosis_code": diagnosis_code,
            "coverage_status": coverage_status,
            "status_detail": status_detail,
            "covered_by_policies": covered_by,
            "not_covered_by_policies": not_covered_reasons,
            "recommendation": self._generate_coverage_recommendation(coverage_status, covered_by, not_covered_reasons)
        }

    def _get_documentation_requirements(self, cpt_code: str, contractor: str) -> Dict[str, Any]:
        """Get documentation requirements for a CPT code."""
        requirements = []

        for ncd_id, ncd in self.NCD_DATABASE.items():
            if cpt_code in ncd["cpt_codes"]:
                requirements.append({
                    "policy_id": ncd_id,
                    "policy_type": "NCD",
                    "title": ncd["title"],
                    "documentation_requirements": ncd["documentation_requirements"],
                    "frequency_limits": ncd["frequency_limits"],
                    "non_coverage_note": ncd.get("non_coverage", "")
                })

        for lcd_id, lcd in self.LCD_DATABASE.items():
            if cpt_code in lcd["cpt_codes"]:
                if contractor and contractor.lower() not in lcd.get("contractor", "").lower():
                    continue
                requirements.append({
                    "policy_id": lcd_id,
                    "policy_type": "LCD",
                    "title": lcd["title"],
                    "contractor": lcd.get("contractor", ""),
                    "documentation_requirements": lcd["documentation_requirements"],
                    "frequency_limits": lcd["frequency_limits"],
                    "non_coverage_note": lcd.get("non_coverage", "")
                })

        # Aggregate unique requirements
        all_reqs = []
        for req in requirements:
            for item in req["documentation_requirements"]:
                if item not in all_reqs:
                    all_reqs.append(item)

        return {
            "cpt_code": cpt_code,
            "policies_found": len(requirements),
            "policies": requirements,
            "aggregated_documentation_requirements": all_reqs,
            "total_unique_requirements": len(all_reqs),
            "message": f"Documentation requirements found from {len(requirements)} policy/policies" if requirements else f"No specific documentation requirements found for CPT {cpt_code}. Follow standard clinical documentation guidelines."
        }

    def _generate_coverage_recommendation(self, status: str, covered: List, not_covered: List) -> str:
        """Generate a recommendation based on coverage check results."""
        if status == "covered":
            policies = ", ".join([p["policy_id"] for p in covered])
            return f"COVERAGE LIKELY: Diagnosis is supported under {policies}. Ensure all documentation requirements are met. Review frequency limits."
        elif status == "not_covered":
            return (f"COVERAGE UNLIKELY: Diagnosis does not match covered criteria. Review the covered diagnosis lists for the applicable policies. "
                    f"Consider whether a more specific or alternative diagnosis code may support medical necessity. "
                    f"If clinical rationale exists, prepare for appeal with supporting documentation.")
        else:
            return (f"NO POLICY FOUND: No specific LCD/NCD addresses this procedure. Contact the payer for coverage criteria. "
                    f"Ensure documentation supports medical necessity per generally accepted standards of care.")