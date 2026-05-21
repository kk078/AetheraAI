// Ported skills (phase 1). Pure functions — no Worker bindings — so they're
// unit-testable and safe. The Python app has ~28 skills; these three seed the
// registry and the rest get ported incrementally.

export interface SkillResult {
  success: boolean;
  data?: unknown;
  error?: string;
}

export interface Skill {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
  execute: (args: Record<string, any>) => SkillResult;
}

function safeDiv(n: any, d: any): number | null {
  const nn = Number(n), dd = Number(d);
  if (!isFinite(nn) || !isFinite(dd) || dd === 0) return null;
  return nn / dd;
}

const BENCHMARKS: Record<string, [number | null, boolean]> = {
  days_in_ar: [40, false],
  clean_claim_rate: [95, true],
  net_collection_rate: [96, true],
  denial_rate: [5, false],
  ar_over_90_pct: [15, false],
};

function grade(metric: string, value: number): string {
  const b = BENCHMARKS[metric];
  if (!b || b[0] === null) return "n/a";
  const [target, higherBetter] = b;
  if (higherBetter) return value >= target ? "good" : value >= target * 0.9 ? "warning" : "poor";
  return value <= target ? "good" : value <= target * 1.2 ? "warning" : "poor";
}

export const rcmKpiCalculator: Skill = {
  name: "rcm_kpi_calculator",
  description:
    "Compute revenue-cycle KPIs (days in AR, clean-claim/denial/collection rates, AR>90) from raw figures and grade vs benchmarks.",
  parameters: {
    type: "object",
    properties: {
      total_ar: { type: "number" },
      average_daily_charges: { type: "number" },
      total_charges: { type: "number" },
      total_payments: { type: "number" },
      contractual_adjustments: { type: "number" },
      total_claims: { type: "integer" },
      clean_claims: { type: "integer" },
      denied_claims: { type: "integer" },
      ar_over_90: { type: "number" },
    },
  },
  execute(a) {
    const out: Record<string, number> = {};
    const dia = safeDiv(a.total_ar, a.average_daily_charges);
    if (dia !== null) out.days_in_ar = Math.round(dia * 10) / 10;
    const ccr = safeDiv(a.clean_claims, a.total_claims);
    if (ccr !== null) out.clean_claim_rate = Math.round(ccr * 1000) / 10;
    const dr = safeDiv(a.denied_claims, a.total_claims);
    if (dr !== null) out.denial_rate = Math.round(dr * 1000) / 10;
    const gcr = safeDiv(a.total_payments, a.total_charges);
    if (gcr !== null) out.gross_collection_rate = Math.round(gcr * 1000) / 10;
    if (a.total_charges != null && a.contractual_adjustments != null) {
      const ncr = safeDiv(a.total_payments, Number(a.total_charges) - Number(a.contractual_adjustments));
      if (ncr !== null) out.net_collection_rate = Math.round(ncr * 1000) / 10;
    }
    const ar90 = safeDiv(a.ar_over_90, a.total_ar);
    if (ar90 !== null) out.ar_over_90_pct = Math.round(ar90 * 1000) / 10;

    if (Object.keys(out).length === 0)
      return { success: false, error: "Insufficient inputs — provide figures for at least one KPI." };

    const kpis: Record<string, unknown> = {};
    const needs: string[] = [];
    for (const [m, v] of Object.entries(out)) {
      const status = grade(m, v);
      kpis[m] = { value: v, benchmark: BENCHMARKS[m]?.[0] ?? null, status };
      if (status === "poor") needs.push(m);
    }
    return { success: true, data: { kpis, needs_attention: needs } };
  },
};

const TIME_NEW: [number, string][] = [[60, "99205"], [45, "99204"], [30, "99203"], [15, "99202"]];
const TIME_EST: [number, string][] = [[40, "99215"], [30, "99214"], [20, "99213"], [10, "99212"]];
const MDM_NEW: Record<string, string> = { straightforward: "99202", low: "99203", moderate: "99204", high: "99205" };
const MDM_EST: Record<string, string> = { straightforward: "99212", low: "99213", moderate: "99214", high: "99215" };
const LEVELS = ["straightforward", "low", "moderate", "high"];

export const emLevelAdvisor: Skill = {
  name: "em_level_advisor",
  description: "Recommend an office/outpatient E/M code (99202-99215, 2021+ rules) by total time or MDM.",
  parameters: {
    type: "object",
    properties: {
      method: { type: "string", enum: ["time", "mdm"] },
      patient_type: { type: "string", enum: ["new", "established"] },
      total_time_minutes: { type: "number" },
      mdm_level: { type: "string", enum: LEVELS },
      problems_level: { type: "string", enum: LEVELS },
      data_level: { type: "string", enum: LEVELS },
      risk_level: { type: "string", enum: LEVELS },
    },
    required: ["patient_type"],
  },
  execute(a) {
    const pt = String(a.patient_type || "").toLowerCase();
    if (pt !== "new" && pt !== "established")
      return { success: false, error: "patient_type must be 'new' or 'established'" };

    if (a.method === "time" || (a.method == null && a.total_time_minutes != null)) {
      const mins = Number(a.total_time_minutes);
      if (!isFinite(mins)) return { success: false, error: "total_time_minutes required for time method" };
      const table = pt === "new" ? TIME_NEW : TIME_EST;
      const hit = table.find(([lo]) => mins >= lo);
      if (!hit) return { success: false, error: "Total time below the minimum E/M threshold" };
      return { success: true, data: { recommended_code: hit[1], method: "time" } };
    }

    let mdm = a.mdm_level as string | undefined;
    let derived = null as null | Record<string, unknown>;
    if (!mdm) {
      const p = a.problems_level, d = a.data_level, r = a.risk_level;
      if (!(p && d && r))
        return { success: false, error: "Provide mdm_level, or all of problems_level/data_level/risk_level" };
      const els = [p, d, r];
      let best = "straightforward";
      for (const lvl of LEVELS) {
        const reached = els.filter((e) => LEVELS.indexOf(e) >= LEVELS.indexOf(lvl)).length;
        if (reached >= 2) best = lvl;
      }
      mdm = best;
      derived = { problems: p, data: d, risk: r, rule: "2-of-3 highest" };
    }
    const table = pt === "new" ? MDM_NEW : MDM_EST;
    const code = table[mdm];
    if (!code) return { success: false, error: "Invalid MDM level" };
    return { success: true, data: { recommended_code: code, method: "mdm", mdm_level: mdm, derived_from: derived } };
  },
};

export const patientCostEstimator: Skill = {
  name: "patient_cost_estimator",
  description:
    "Estimate patient out-of-pocket cost from benefits (deductible, coinsurance, copay, OOP max).",
  parameters: {
    type: "object",
    properties: {
      charge: { type: "number" },
      allowed_amount: { type: "number" },
      deductible_remaining: { type: "number" },
      coinsurance_rate: { type: "number" },
      copay: { type: "number" },
      oop_max_remaining: { type: "number" },
    },
    required: ["charge"],
  },
  execute(a) {
    const charge = Number(a.charge);
    if (!(charge > 0)) return { success: false, error: "'charge' is required and must be > 0" };
    const allowed = Number(a.allowed_amount ?? charge);
    const dedRemaining = Number(a.deductible_remaining ?? 0);
    const coins = Number(a.coinsurance_rate ?? 0);
    const copay = Number(a.copay ?? 0);
    const r2 = (n: number) => Math.round(n * 100) / 100;

    const dedApplied = Math.min(dedRemaining, allowed);
    const remainder = Math.max(0, allowed - dedApplied);
    const coinsurance = r2(remainder * coins);
    let patient = r2(copay + dedApplied + coinsurance);
    let capped = false;
    if (a.oop_max_remaining != null && patient > Number(a.oop_max_remaining)) {
      patient = r2(Number(a.oop_max_remaining));
      capped = true;
    }
    return {
      success: true,
      data: {
        allowed_amount: r2(allowed),
        estimated_patient_responsibility: patient,
        breakdown: { copay: r2(copay), deductible_applied: r2(dedApplied), coinsurance, capped_at_oop_max: capped },
        contractual_adjustment: r2(charge - allowed),
      },
    };
  },
};

export const REGISTRY: Record<string, Skill> = {
  [rcmKpiCalculator.name]: rcmKpiCalculator,
  [emLevelAdvisor.name]: emLevelAdvisor,
  [patientCostEstimator.name]: patientCostEstimator,
};

export function toolDefinitions(names: string[]) {
  return names
    .map((n) => REGISTRY[n])
    .filter(Boolean)
    .map((s) => ({
      type: "function",
      function: { name: s.name, description: s.description, parameters: s.parameters },
    }));
}
