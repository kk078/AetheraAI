"""
Aethera AI - Calculator Skill

Mathematical, financial, statistical, and clinical calculations.
"""

import math
import statistics
from typing import Optional

from skills.skill_base import AetheraSkill, SkillResult, skill


@skill(name="calculator", category="general")
class CalculatorSkill(AetheraSkill):
    """
    Perform mathematical, financial, statistical, and clinical calculations.
    """

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Perform mathematical, financial, statistical, and clinical calculations"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "Type of calculation: basic, statistical, financial, clinical"
                },
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate (for basic operations)"
                },
                "values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Array of values for statistical operations"
                },
                "formula": {
                    "type": "string",
                    "description": "Named formula for financial/clinical calculations (e.g., 'bmi', 'egfr', 'pv')"
                },
                "inputs": {
                    "type": "object",
                    "description": "Named inputs for formula calculations"
                }
            }
        }

    @property
    def examples(self) -> list:
        return [
            {"input": {"operation": "basic", "expression": "150 * 0.25"}},
            {"input": {"operation": "statistical", "values": [1, 2, 3, 4, 5]}},
            {"input": {"formula": "bmi", "inputs": {"weight_kg": 70, "height_m": 1.75}}},
        ]

    async def execute(self, **kwargs) -> SkillResult:
        operation = kwargs.get("operation", "basic")

        try:
            if operation == "basic":
                return self._basic_calc(kwargs.get("expression", ""))
            elif operation == "statistical":
                return self._statistical_calc(kwargs.get("values", []))
            elif operation == "financial":
                return self._financial_calc(kwargs.get("formula", ""), kwargs.get("inputs", {}))
            elif operation == "clinical":
                return self._clinical_calc(kwargs.get("formula", ""), kwargs.get("inputs", {}))
            else:
                return SkillResult(success=False, error=f"Unknown operation: {operation}")
        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _basic_calc(self, expression: str) -> SkillResult:
        """Evaluate basic mathematical expression safely."""
        if not expression:
            return SkillResult(success=False, error="No expression provided")

        # Only allow safe characters
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return SkillResult(success=False, error="Invalid characters in expression")

        try:
            result = eval(expression, {"__builtins__": {}}, {})
            return SkillResult(success=True, data={"result": result, "expression": expression})
        except Exception as e:
            return SkillResult(success=False, error=f"Calculation error: {e}")

    def _statistical_calc(self, values: list) -> SkillResult:
        """Perform statistical calculations."""
        if not values:
            return SkillResult(success=False, error="No values provided")

        if len(values) < 1:
            return SkillResult(success=False, error="Need at least one value")

        try:
            numeric_values = [float(v) for v in values]
            results = {
                "count": len(numeric_values),
                "sum": sum(numeric_values),
                "mean": statistics.mean(numeric_values),
                "median": statistics.median(numeric_values),
                "min": min(numeric_values),
                "max": max(numeric_values),
            }

            if len(numeric_values) > 1:
                results["stdev"] = statistics.stdev(numeric_values)
                results["variance"] = statistics.variance(numeric_values)

            return SkillResult(success=True, data=results)
        except Exception as e:
            return SkillResult(success=False, error=f"Statistical error: {e}")

    def _financial_calc(self, formula: str, inputs: dict) -> SkillResult:
        """Perform financial calculations."""
        formulas = {
            "pv": self._calc_pv,  # Present value
            "fv": self._calc_fv,  # Future value
            "pmt": self._calc_pmt,  # Payment
            "roi": self._calc_roi,  # Return on investment
            "margin": self._calc_margin,  # Profit margin
            "markup": self._calc_markup,  # Markup percentage
        }

        if formula not in formulas:
            return SkillResult(success=False, error=f"Unknown formula: {formula}")

        try:
            result = formulas[formula](inputs)
            return SkillResult(success=True, data=result)
        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _clinical_calc(self, formula: str, inputs: dict) -> SkillResult:
        """Perform clinical calculations."""
        formulas = {
            "bmi": self._calc_bmi,
            "egfr": self._calc_egfr,
            "creatinine_clearance": self._calc_crcl,
            "abd_waist_hip": self._calc_whr,
            "corrected_calcium": self._calc_corrected_ca,
            "anion_gap": self._calc_anion_gap,
        }

        if formula not in formulas:
            return SkillResult(success=False, error=f"Unknown formula: {formula}")

        try:
            result = formulas[formula](inputs)
            return SkillResult(success=True, data=result)
        except Exception as e:
            return SkillResult(success=False, error=str(e))

    # Financial calculation implementations
    def _calc_pv(self, inputs: dict) -> dict:
        """Calculate present value."""
        fv = inputs.get("fv", 0)
        rate = inputs.get("rate", 0) / 100
        periods = inputs.get("periods", 0)
        pv = fv / ((1 + rate) ** periods)
        return {"present_value": pv, "inputs": inputs}

    def _calc_fv(self, inputs: dict) -> dict:
        """Calculate future value."""
        pv = inputs.get("pv", 0)
        rate = inputs.get("rate", 0) / 100
        periods = inputs.get("periods", 0)
        fv = pv * ((1 + rate) ** periods)
        return {"future_value": fv, "inputs": inputs}

    def _calc_pmt(self, inputs: dict) -> dict:
        """Calculate loan payment."""
        pv = inputs.get("pv", 0)
        rate = inputs.get("rate", 0) / 100 / 12  # Monthly
        nper = inputs.get("nper", 0)  # Months
        if rate == 0:
            pmt = pv / nper
        else:
            pmt = pv * rate * (1 + rate) ** nper / ((1 + rate) ** nper - 1)
        return {"payment": pmt, "inputs": inputs}

    def _calc_roi(self, inputs: dict) -> dict:
        """Calculate return on investment."""
        gain = inputs.get("gain", 0)
        cost = inputs.get("cost", 0)
        roi = ((gain - cost) / cost) * 100 if cost > 0 else 0
        return {"roi_percent": roi, "inputs": inputs}

    def _calc_margin(self, inputs: dict) -> dict:
        """Calculate profit margin."""
        revenue = inputs.get("revenue", 0)
        cost = inputs.get("cost", 0)
        margin = ((revenue - cost) / revenue) * 100 if revenue > 0 else 0
        return {"margin_percent": margin, "inputs": inputs}

    def _calc_markup(self, inputs: dict) -> dict:
        """Calculate markup percentage."""
        cost = inputs.get("cost", 0)
        price = inputs.get("price", 0)
        markup = ((price - cost) / cost) * 100 if cost > 0 else 0
        return {"markup_percent": markup, "inputs": inputs}

    # Clinical calculation implementations
    def _calc_bmi(self, inputs: dict) -> dict:
        """Calculate Body Mass Index."""
        weight = inputs.get("weight_kg", 0)
        height = inputs.get("height_m", 0)
        if height <= 0:
            raise ValueError("Height must be positive")
        bmi = weight / (height ** 2)
        category = self._bmi_category(bmi)
        return {"bmi": round(bmi, 2), "category": category, "inputs": inputs}

    def _bmi_category(self, bmi: float) -> str:
        if bmi < 18.5:
            return "Underweight"
        elif bmi < 25:
            return "Normal"
        elif bmi < 30:
            return "Overweight"
        else:
            return "Obese"

    def _calc_egfr(self, inputs: dict) -> dict:
        """Calculate eGFR using CKD-EPI equation."""
        creatinine = inputs.get("creatinine_mg_dl", 0)
        age = inputs.get("age", 0)
        female = inputs.get("female", False)
        black = inputs.get("black", False)

        if creatinine <= 0 or age <= 0:
            raise ValueError("Invalid inputs")

        # CKD-EPI 2009 equation
        if female:
            if creatinine <= 0.7:
                egfr = 144 * ((creatinine / 0.7) ** -0.329) * (0.993 ** age)
            else:
                egfr = 144 * ((creatinine / 0.7) ** -1.209) * (0.993 ** age)
        else:
            if creatinine <= 0.9:
                egfr = 141 * ((creatinine / 0.9) ** -0.411) * (0.993 ** age)
            else:
                egfr = 141 * ((creatinine / 0.9) ** -1.209) * (0.993 ** age)

        if black:
            egfr *= 1.159

        stage = self._ckd_stage(egfr)
        return {"egfr": round(egfr, 1), "stage": stage, "inputs": inputs}

    def _ckd_stage(self, egfr: float) -> str:
        if egfr >= 90:
            return "G1 - Normal or high"
        elif egfr >= 60:
            return "G2 - Mildly decreased"
        elif egfr >= 45:
            return "G3a - Mildly to moderately decreased"
        elif egfr >= 30:
            return "G3b - Moderately to severely decreased"
        elif egfr >= 15:
            return "G4 - Severely decreased"
        else:
            return "G5 - Kidney failure"

    def _calc_crcl(self, inputs: dict) -> dict:
        """Calculate creatinine clearance using Cockcroft-Gault."""
        weight = inputs.get("weight_kg", 0)
        age = inputs.get("age", 0)
        creatinine = inputs.get("creatinine_mg_dl", 0)
        female = inputs.get("female", False)

        if creatinine <= 0:
            raise ValueError("Creatinine must be positive")

        crcl = ((140 - age) * weight) / (72 * creatinine)
        if female:
            crcl *= 0.85

        return {"crcl_ml_min": round(crcl, 1), "inputs": inputs}

    def _calc_whr(self, inputs: dict) -> dict:
        """Calculate waist-to-hip ratio."""
        waist = inputs.get("waist_cm", 0)
        hip = inputs.get("hip_cm", 0)
        if hip <= 0:
            raise ValueError("Hip measurement must be positive")
        whr = waist / hip
        risk = "High" if whr > 0.9 else "Moderate" if whr > 0.85 else "Low"
        return {"whr": round(whr, 2), "risk": risk, "inputs": inputs}

    def _calc_corrected_ca(self, inputs: dict) -> dict:
        """Calculate corrected calcium."""
        calcium = inputs.get("calcium_mg_dl", 0)
        albumin = inputs.get("albumin_g_dl", 4.0)
        corrected = calcium + 0.8 * (4.0 - albumin)
        return {"corrected_calcium": round(corrected, 2), "inputs": inputs}

    def _calc_anion_gap(self, inputs: dict) -> dict:
        """Calculate anion gap."""
        na = inputs.get("sodium", 0)
        cl = inputs.get("chloride", 0)
        hco3 = inputs.get("bicarbonate", 0)
        gap = na - (cl + hco3)
        interpretation = "High" if gap > 12 else "Normal" if gap >= 8 else "Low"
        return {"anion_gap": gap, "interpretation": interpretation, "inputs": inputs}
