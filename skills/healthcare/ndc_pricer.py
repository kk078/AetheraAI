"""
Aethera AI - NDC Pricer Skill

Drug pricing: common drug NDCs with ASP, AWP, WAC, NADAC prices.
Supports: lookup price by NDC, compare pricing benchmarks,
calculate reimbursement.
"""

from typing import Dict, Any, List, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill


# Drug pricing database (NDC -> pricing information)
NDC_DATABASE: Dict[str, Dict[str, Any]] = {
    "00009073316": {
        "ndc": "00009073316",
        "drug_name": "Atorvastatin Calcium",
        "strength": "80 mg",
        "dosage_form": "Tablet",
        "manufacturer": "Par Pharm",
        "package_size": 90,
        "package_unit": "EA",
        "prices": {
            "asp": 0.12,
            "awp": 0.35,
            "wac": 0.15,
            "nadac": 0.10
        },
        "units_per_package": 90,
        "hcpcs": "J1710",
        "therapy_class": "Statin"
    },
    "00009086830": {
        "ndc": "00009086830",
        "drug_name": "Lisinopril",
        "strength": "20 mg",
        "dosage_form": "Tablet",
        "manufacturer": "Par Pharm",
        "package_size": 100,
        "package_unit": "EA",
        "prices": {
            "asp": 0.03,
            "awp": 0.12,
            "wac": 0.04,
            "nadac": 0.03
        },
        "units_per_package": 100,
        "hcpcs": None,
        "therapy_class": "ACE Inhibitor"
    },
    "00143333601": {
        "ndc": "00143333601",
        "drug_name": "Metformin HCl",
        "strength": "500 mg",
        "dosage_form": "Tablet",
        "manufacturer": "Sandoz",
        "package_size": 100,
        "package_unit": "EA",
        "prices": {
            "asp": 0.02,
            "awp": 0.08,
            "wac": 0.03,
            "nadac": 0.02
        },
        "units_per_package": 100,
        "hcpcs": None,
        "therapy_class": "Biguanide"
    },
    "00078036405": {
        "ndc": "00078036405",
        "drug_name": "Amoxicillin",
        "strength": "500 mg",
        "dosage_form": "Capsule",
        "manufacturer": "Sandoz",
        "package_size": 100,
        "package_unit": "EA",
        "prices": {
            "asp": 0.08,
            "awp": 0.25,
            "wac": 0.10,
            "nadac": 0.07
        },
        "units_per_package": 100,
        "hcpcs": None,
        "therapy_class": "Penicillin Antibiotic"
    },
    "00378202101": {
        "ndc": "00378202101",
        "drug_name": "Omeprazole",
        "strength": "20 mg",
        "dosage_form": "Capsule DR",
        "manufacturer": "Mylan",
        "package_size": 100,
        "package_unit": "EA",
        "prices": {
            "asp": 0.05,
            "awp": 0.18,
            "wac": 0.06,
            "nadac": 0.05
        },
        "units_per_package": 100,
        "hcpcs": None,
        "therapy_class": "Proton Pump Inhibitor"
    },
    "00904688960": {
        "ndc": "00904688960",
        "drug_name": "Prednisone",
        "strength": "10 mg",
        "dosage_form": "Tablet",
        "manufacturer": "Major Pharm",
        "package_size": 100,
        "package_unit": "EA",
        "prices": {
            "asp": 0.02,
            "awp": 0.10,
            "wac": 0.03,
            "nadac": 0.02
        },
        "units_per_package": 100,
        "hcpcs": None,
        "therapy_class": "Corticosteroid"
    },
    "00781324430": {
        "ndc": "00781324430",
        "drug_name": "Levothyroxine Sodium",
        "strength": "50 mcg",
        "dosage_form": "Tablet",
        "manufacturer": "Mylan",
        "package_size": 100,
        "package_unit": "EA",
        "prices": {
            "asp": 0.04,
            "awp": 0.15,
            "wac": 0.05,
            "nadac": 0.04
        },
        "units_per_package": 100,
        "hcpcs": None,
        "therapy_class": "Thyroid Hormone"
    },
    "00002344463": {
        "ndc": "00002344463",
        "drug_name": "Adalimumab (Humira)",
        "strength": "40 mg/0.8 mL",
        "dosage_form": "Injection",
        "manufacturer": "AbbVie",
        "package_size": 2,
        "package_unit": "SYR",
        "prices": {
            "asp": 2803.47,
            "awp": 5860.00,
            "wac": 3150.00,
            "nadac": 2600.00
        },
        "units_per_package": 2,
        "hcpcs": "J0135",
        "therapy_class": "TNF Inhibitor / Biologic"
    },
    "00002473120": {
        "ndc": "00002473120",
        "drug_name": "Infliximab (Remicade)",
        "strength": "100 mg",
        "dosage_form": "Injection PWDR",
        "manufacturer": "Janssen",
        "package_size": 1,
        "package_unit": "Vial",
        "prices": {
            "asp": 875.40,
            "awp": 1243.60,
            "wac": 935.00,
            "nadac": 820.00
        },
        "units_per_package": 1,
        "hcpcs": "J1745",
        "therapy_class": "TNF Inhibitor / Biologic"
    },
    "00004350601": {
        "ndc": "00004350601",
        "drug_name": "Insulin Glargine (Lantus)",
        "strength": "100 units/mL",
        "dosage_form": "Injection",
        "manufacturer": "Sanofi-Aventis",
        "package_size": 10,
        "package_unit": "mL",
        "prices": {
            "asp": 28.75,
            "awp": 42.50,
            "wac": 31.20,
            "nadac": 26.90
        },
        "units_per_package": 10,
        "hcpcs": "J1817",
        "therapy_class": "Long-acting Insulin"
    },
    "00002520101": {
        "ndc": "00002520101",
        "drug_name": "Enoxaparin Sodium (Lovenox)",
        "strength": "40 mg/0.4 mL",
        "dosage_form": "Injection",
        "manufacturer": "Sanofi-Aventis",
        "package_size": 10,
        "package_unit": "SYR",
        "prices": {
            "asp": 18.50,
            "awp": 42.80,
            "wac": 22.00,
            "nadac": 16.75
        },
        "units_per_package": 10,
        "hcpcs": "J1650",
        "therapy_class": "Low Molecular Weight Heparin"
    },
    "00555084201": {
        "ndc": "00555084201",
        "drug_name": "Ceftriaxone Sodium",
        "strength": "1 g",
        "dosage_form": "Injection PWDR",
        "manufacturer": "Rompharm",
        "package_size": 10,
        "package_unit": "Vial",
        "prices": {
            "asp": 1.85,
            "awp": 5.60,
            "wac": 2.10,
            "nadac": 1.65
        },
        "units_per_package": 10,
        "hcpcs": "J0249",
        "therapy_class": "Cephalosporin Antibiotic"
    },
    "00006408201": {
        "ndc": "00006408201",
        "drug_name": "Pfizer-BioNTech COVID-19 Vaccine",
        "strength": "30 mcg/0.3 mL",
        "dosage_form": "Injection",
        "manufacturer": "Pfizer",
        "package_size": 6,
        "package_unit": "Dose",
        "prices": {
            "asp": 19.50,
            "awp": 28.00,
            "wac": 20.00,
            "nadac": 19.50
        },
        "units_per_package": 6,
        "hcpcs": "91301",
        "therapy_class": "COVID-19 Vaccine"
    },
    "63323039210": {
        "ndc": "63323039210",
        "drug_name": "Heparin Sodium",
        "strength": "1000 units/mL",
        "dosage_form": "Injection",
        "manufacturer": "Fresenius Kabi",
        "package_size": 10,
        "package_unit": "mL",
        "prices": {
            "asp": 0.45,
            "awp": 1.20,
            "wac": 0.55,
            "nadac": 0.40
        },
        "units_per_package": 10,
        "hcpcs": "J1644",
        "therapy_class": "Anticoagulant"
    },
    "00173086301": {
        "ndc": "00173086301",
        "drug_name": "Albuterol Sulfate (ProAir)",
        "strength": "90 mcg/actuation",
        "dosage_form": "Aerosol Inhaler",
        "manufacturer": "Teva",
        "package_size": 200,
        "package_unit": "EA",
        "prices": {
            "asp": 18.75,
            "awp": 45.00,
            "wac": 21.50,
            "nadac": 17.00
        },
        "units_per_package": 200,
        "hcpcs": "J7611",
        "therapy_class": "Bronchodilator"
    },
    "00004067030": {
        "ndc": "00004067030",
        "drug_name": "Methylprednisolone Sodium Succinate (Solu-Medrol)",
        "strength": "40 mg",
        "dosage_form": "Injection PWDR",
        "manufacturer": "Pfizer",
        "package_size": 1,
        "package_unit": "Vial",
        "prices": {
            "asp": 3.75,
            "awp": 8.90,
            "wac": 4.50,
            "nadac": 3.20
        },
        "units_per_package": 1,
        "hcpcs": "J2920",
        "therapy_class": "Corticosteroid Injectable"
    },
    "00641616010": {
        "ndc": "00641616010",
        "drug_name": "Epinephrine (EpiPen)",
        "strength": "0.3 mg/0.3 mL",
        "dosage_form": "Injection Auto-injector",
        "manufacturer": "Mylan",
        "package_size": 2,
        "package_unit": "EA",
        "prices": {
            "asp": 345.00,
            "awp": 635.00,
            "wac": 380.00,
            "nadac": 310.00
        },
        "units_per_package": 2,
        "hcpcs": "J0170",
        "therapy_class": "Sympathomimetic / Anaphylaxis Treatment"
    },
    "00074450409": {
        "ndc": "00074450409",
        "drug_name": "Amlodipine Besylate",
        "strength": "10 mg",
        "dosage_form": "Tablet",
        "manufacturer": "Pfizer",
        "package_size": 100,
        "package_unit": "EA",
        "prices": {
            "asp": 0.04,
            "awp": 0.15,
            "wac": 0.05,
            "nadac": 0.04
        },
        "units_per_package": 100,
        "hcpcs": None,
        "therapy_class": "Calcium Channel Blocker"
    },
    "00173038201": {
        "ndc": "00173038201",
        "drug_name": "Ondansetron (Zofran)",
        "strength": "4 mg/2 mL",
        "dosage_form": "Injection",
        "manufacturer": "Teva",
        "package_size": 1,
        "package_unit": "Vial",
        "prices": {
            "asp": 0.85,
            "awp": 2.50,
            "wac": 1.00,
            "nadac": 0.75
        },
        "units_per_package": 1,
        "hcpcs": "J2405",
        "therapy_class": "5-HT3 Antagonist / Antiemetic"
    },
    "00007028480": {
        "ndc": "00007028480",
        "drug_name": "Oxycodone HCl",
        "strength": "30 mg",
        "dosage_form": "Tablet",
        "manufacturer": "Rhodes Pharm",
        "package_size": 100,
        "package_unit": "EA",
        "prices": {
            "asp": 0.35,
            "awp": 1.20,
            "wac": 0.45,
            "nadac": 0.30
        },
        "units_per_package": 100,
        "hcpcs": None,
        "therapy_class": "Opioid Analgesic Schedule II"
    },
}

# Pricing benchmark definitions
PRICING_BENCHMARKS: Dict[str, Dict[str, Any]] = {
    "asp": {
        "name": "Average Sales Price",
        "description": "Weighted average of all non-federal sales prices. CMS uses ASP + 6% for Part B drug reimbursement.",
        "calculation": "Net sales revenue / total units sold to non-federal purchasers",
        "update_frequency": "Quarterly (CMS updates ASP files quarterly)",
        "usage": "Primary Medicare Part B reimbursement basis (ASP + 6%)"
    },
    "awp": {
        "name": "Average Wholesale Price",
        "description": "Published list price. Historically used for reimbursement but considered inflated. Not an actual transaction price.",
        "calculation": "Published by pricing compendia (Red Book, Medi-Span, Gold Standard)",
        "update_frequency": "Varies; often lags actual market changes",
        "usage": "Some commercial payers still use AWP-based formulas (e.g., AWP - 15% to AWP - 25%). Not recommended as primary benchmark."
    },
    "wac": {
        "name": "Wholesale Acquisition Cost",
        "description": "Manufacturer's list price to wholesalers or direct purchasers. Excludes discounts/rebates.",
        "calculation": "Manufacturer-reported list price",
        "update_frequency": "Updated by manufacturers; published in compendia",
        "usage": "Used as benchmark by some payers and 340B pricing calculations. Closer to actual cost than AWP."
    },
    "nadac": {
        "name": "National Average Drug Acquisition Cost",
        "description": "Average price pharmacies pay to acquire the drug. Survey-based. Most accurate retail cost benchmark.",
        "calculation": "CMS survey of retail pharmacy acquisition costs",
        "update_frequency": "Weekly (CMS publishes NADAC files weekly)",
        "usage": "Medicaid reimbursement benchmark. Many states use NADAC + dispensing fee for Medicaid drug reimbursement."
    },
}


@skill(name="ndc_pricer", category="healthcare")
class NDCPricerSkill(AetheraSkill):
    """
    Drug pricing lookup and comparison.
    """

    @property
    def name(self) -> str:
        return "ndc_pricer"

    @property
    def description(self) -> str:
        return "Lookup drug prices by NDC, compare pricing benchmarks (ASP, AWP, WAC, NADAC), and calculate reimbursement for Medicare Part B and Medicaid."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["lookup_price", "compare_benchmarks", "calculate_reimbursement", "benchmark_info"],
                    "description": "Action: lookup_price (find price by NDC), compare_benchmarks (compare ASP/AWP/WAC/NADAC for a drug), calculate_reimbursement (calc Medicare/Medicaid reimbursement), benchmark_info (explain pricing benchmarks)"
                },
                "ndc": {
                    "type": "string",
                    "description": "National Drug Code (11-digit format, e.g., 00009073316)"
                },
                "payer": {
                    "type": "string",
                    "enum": ["medicare_part_b", "medicaid", "commercial"],
                    "description": "Payer for reimbursement calculation"
                },
                "units_billed": {
                    "type": "integer",
                    "description": "Number of units to calculate reimbursement for",
                    "default": 1
                },
                "benchmark": {
                    "type": "string",
                    "description": "Specific benchmark to look up (asp, awp, wac, nadac)"
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
            {"input": {"action": "lookup_price", "ndc": "00009073316"}},
            {"input": {"action": "compare_benchmarks", "ndc": "00002344463"}},
            {"input": {"action": "calculate_reimbursement", "ndc": "00002344463", "payer": "medicare_part_b", "units_billed": 2}},
            {"input": {"action": "benchmark_info"}},
        ]

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "")
        ndc = kwargs.get("ndc", "")
        payer = kwargs.get("payer", "medicare_part_b")
        units_billed = kwargs.get("units_billed", 1)
        benchmark = kwargs.get("benchmark", "")

        try:
            if action == "lookup_price":
                if not ndc:
                    return SkillResult(success=False, error="ndc is required for lookup_price")
                result = self._lookup_price(ndc, benchmark)
                return SkillResult(success=True, data=result)

            elif action == "compare_benchmarks":
                if not ndc:
                    return SkillResult(success=False, error="ndc is required for compare_benchmarks")
                result = self._compare_benchmarks(ndc)
                return SkillResult(success=True, data=result)

            elif action == "calculate_reimbursement":
                if not ndc:
                    return SkillResult(success=False, error="ndc is required for calculate_reimbursement")
                result = self._calculate_reimbursement(ndc, payer, units_billed)
                return SkillResult(success=True, data=result)

            elif action == "benchmark_info":
                result = self._benchmark_info(benchmark)
                return SkillResult(success=True, data=result)

            else:
                return SkillResult(success=False, error=f"Unknown action: {action}")

        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _normalize_ndc(self, ndc: str) -> str:
        """Normalize NDC to 11-digit format without hyphens."""
        ndc = ndc.replace("-", "").strip()
        if len(ndc) == 10:
            # Pad to 11 digits (assume 5-4-2 or 5-3-2 or 4-4-2)
            ndc = "0" + ndc
        return ndc

    def _lookup_price(self, ndc: str, benchmark: str) -> Dict[str, Any]:
        """Look up drug price by NDC."""
        normalized = self._normalize_ndc(ndc)
        drug_info = NDC_DATABASE.get(normalized)

        if not drug_info:
            return {
                "ndc": ndc,
                "normalized_ndc": normalized,
                "found": False,
                "message": f"NDC {ndc} not found in pricing database"
            }

        prices = drug_info.get("prices", {})

        if benchmark:
            bench_lower = benchmark.lower()
            if bench_lower in prices:
                return {
                    "ndc": normalized,
                    "drug_name": drug_info["drug_name"],
                    "strength": drug_info["strength"],
                    "dosage_form": drug_info["dosage_form"],
                    "manufacturer": drug_info["manufacturer"],
                    "benchmark": bench_lower,
                    "price_per_unit": prices[bench_lower],
                    "package_size": drug_info["package_size"],
                    "units_per_package": drug_info["units_per_package"],
                    "found": True
                }
            else:
                return {
                    "ndc": normalized,
                    "drug_name": drug_info["drug_name"],
                    "found": True,
                    "message": f"Benchmark '{benchmark}' not available for this drug. Available: {', '.join(prices.keys())}"
                }

        return {
            "ndc": normalized,
            "drug_name": drug_info["drug_name"],
            "strength": drug_info["strength"],
            "dosage_form": drug_info["dosage_form"],
            "manufacturer": drug_info["manufacturer"],
            "package_size": drug_info["package_size"],
            "package_unit": drug_info["package_unit"],
            "hcpcs": drug_info.get("hcpcs"),
            "therapy_class": drug_info["therapy_class"],
            "prices": {
                "asp": {"price_per_unit": prices.get("asp"), "description": "Average Sales Price"},
                "awp": {"price_per_unit": prices.get("awp"), "description": "Average Wholesale Price"},
                "wac": {"price_per_unit": prices.get("wac"), "description": "Wholesale Acquisition Cost"},
                "nadac": {"price_per_unit": prices.get("nadac"), "description": "National Average Drug Acquisition Cost"}
            },
            "found": True
        }

    def _compare_benchmarks(self, ndc: str) -> Dict[str, Any]:
        """Compare pricing benchmarks for a drug."""
        normalized = self._normalize_ndc(ndc)
        drug_info = NDC_DATABASE.get(normalized)

        if not drug_info:
            return {
                "ndc": ndc,
                "found": False,
                "message": f"NDC {ndc} not found in pricing database"
            }

        prices = drug_info.get("prices", {})
        asp = prices.get("asp", 0)
        awp = prices.get("awp", 0)
        wac = prices.get("wac", 0)
        nadac = prices.get("nadac", 0)

        # Calculate spread between benchmarks
        comparisons = {}
        if asp and awp:
            comparisons["awp_vs_asp"] = {
                "spread": round(awp - asp, 4),
                "spread_pct": round(((awp - asp) / asp) * 100, 1) if asp > 0 else 0,
                "note": "AWP is typically 15-25% above ASP for generics; much higher for brands"
            }
        if asp and wac:
            comparisons["wac_vs_asp"] = {
                "spread": round(wac - asp, 4),
                "spread_pct": round(((wac - asp) / asp) * 100, 1) if asp > 0 else 0,
                "note": "WAC is closer to actual cost than AWP"
            }
        if asp and nadac:
            comparisons["nadac_vs_asp"] = {
                "spread": round(nadac - asp, 4),
                "spread_pct": round(((nadac - asp) / asp) * 100, 1) if asp > 0 else 0,
                "note": "NADAC should be closest to actual acquisition cost"
            }
        if awp and nadac:
            comparisons["awp_vs_nadac"] = {
                "spread": round(awp - nadac, 4),
                "spread_pct": round(((awp - nadac) / nadac) * 100, 1) if nadac > 0 else 0,
                "note": "AWP-NADAC spread shows how inflated AWP is vs actual cost"
            }

        return {
            "ndc": normalized,
            "drug_name": drug_info["drug_name"],
            "strength": drug_info["strength"],
            "dosage_form": drug_info["dosage_form"],
            "therapy_class": drug_info["therapy_class"],
            "prices": prices,
            "price_ranking": sorted(prices.items(), key=lambda x: x[1]),
            "comparisons": comparisons,
            "cheapest_benchmark": min(prices, key=prices.get) if prices else None,
            "most_expensive_benchmark": max(prices, key=prices.get) if prices else None,
            "recommended_benchmark": {
                "medicare_part_b": "ASP (reimbursement = ASP + 6%)",
                "medicaid": "NADAC (reimbursement = NADAC + dispensing fee)",
                "commercial": "Varies by payer (AWP discount or ASP-based)"
            },
            "reference": "CMS ASP/NADAC files; pricing compendia"
        }

    def _calculate_reimbursement(self, ndc: str, payer: str, units_billed: int) -> Dict[str, Any]:
        """Calculate drug reimbursement for a payer."""
        normalized = self._normalize_ndc(ndc)
        drug_info = NDC_DATABASE.get(normalized)

        if not drug_info:
            return {
                "ndc": ndc,
                "found": False,
                "message": f"NDC {ndc} not found in pricing database"
            }

        prices = drug_info.get("prices", {})
        hcpcs = drug_info.get("hcpcs")

        reimbursement = {}
        if payer == "medicare_part_b":
            # Medicare Part B: ASP + 6%
            asp = prices.get("asp", 0)
            rate_per_unit = round(asp * 1.06, 4)
            total_reimb = round(rate_per_unit * units_billed, 2)
            coinsurance_pct = 0.20  # 20% patient coinsurance
            coinsurance_amt = round(total_reimb * coinsurance_pct, 2)
            reimbursement = {
                "payer": "Medicare Part B",
                "method": "ASP + 6%",
                "asp_per_unit": asp,
                "add_on_pct": "6%",
                "rate_per_unit": rate_per_unit,
                "units_billed": units_billed,
                "total_reimbursement": total_reimb,
                "medicare_payment_80_pct": round(total_reimb * 0.80, 2),
                "patient_coinsurance_20_pct": coinsurance_amt,
                "sequestration_note": "2% sequestration may apply to Medicare payment. Not included in this calculation.",
                "hcpcs": hcpcs,
                "requires_j_code": hcpcs is not None,
                "billing_note": "Part B drugs require HCPCS J-code for billing. Provider-administered drugs only."
            }

        elif payer == "medicaid":
            # Medicaid: NADAC + dispensing fee
            nadac = prices.get("nadac", 0)
            dispensing_fee = 10.50  # Average state dispensing fee
            rate_per_unit = nadac
            ingredient_cost = round(rate_per_unit * units_billed, 2)
            total_reimb = round(ingredient_cost + dispensing_fee, 2)
            reimbursement = {
                "payer": "Medicaid",
                "method": "NADAC + Dispensing Fee (varies by state)",
                "nadac_per_unit": nadac,
                "dispensing_fee": dispensing_fee,
                "dispensing_fee_note": "Average state dispensing fee. Actual varies by state ($3-$12+).",
                "ingredient_cost": ingredient_cost,
                "units_billed": units_billed,
                "total_reimbursement": total_reimb,
                "state_variation_note": "Medicaid reimbursement varies significantly by state. Check state-specific fee schedule.",
                "340b_note": "340B-covered entities may bill at reduced acquisition cost. Check 340B pricing."
            }

        elif payer == "commercial":
            # Commercial: typically AWP discount
            awp = prices.get("awp", 0)
            discount_pct = 0.15  # Common AWP - 15%
            rate_per_unit = round(awp * (1 - discount_pct), 4)
            total_reimb = round(rate_per_unit * units_billed, 2)
            reimbursement = {
                "payer": "Commercial (estimated)",
                "method": "AWP - 15% (typical; varies by payer/contract)",
                "awp_per_unit": awp,
                "discount_pct": "15% (example only)",
                "rate_per_unit": rate_per_unit,
                "units_billed": units_billed,
                "total_reimbursement": total_reimb,
                "variation_note": "Commercial reimbursement varies widely. Common formulas: AWP-15%, AWP-20%, ASP+6%, or contract-specific rates.",
                "contract_note": "Check specific payer contract for actual reimbursement terms."
            }

        return {
            "ndc": normalized,
            "drug_name": drug_info["drug_name"],
            "strength": drug_info["strength"],
            "dosage_form": drug_info["dosage_form"],
            "therapy_class": drug_info["therapy_class"],
            "reimbursement": reimbursement,
            "prices": prices,
            "reference": "CMS ASP, NADAC files; payer-specific fee schedules"
        }

    def _benchmark_info(self, benchmark: str) -> Dict[str, Any]:
        """Get information about pricing benchmarks."""
        if benchmark:
            bench_lower = benchmark.lower()
            bench_info = PRICING_BENCHMARKS.get(bench_lower)
            if bench_info:
                return {
                    "benchmark": bench_lower,
                    "found": True,
                    **bench_info
                }
            else:
                return {
                    "benchmark": benchmark,
                    "found": False,
                    "message": f"Unknown benchmark: {benchmark}",
                    "available": list(PRICING_BENCHMARKS.keys())
                }

        return {
            "benchmarks": PRICING_BENCHMARKS,
            "quick_reference": {
                "ASP": "Best for Medicare Part B reimbursement (ASP + 6%)",
                "AWP": "Inflated list price; some commercial payers still use",
                "WAC": "Manufacturer list price; closer to actual cost than AWP",
                "NADAC": "Best for Medicaid reimbursement (actual pharmacy acquisition cost)"
            }
        }