// Ported skills (phases 1-2 pure-logic, phase 3 data-backed via D1). Pure skills
// ignore the optional ctx; data-backed skills read ctx.env.DB (D1).

import type { Env } from "./types";

export interface SkillResult {
  success: boolean;
  data?: unknown;
  error?: string;
}

export interface SkillContext {
  env: Env;
}

export interface Skill {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
  execute: (args: Record<string, any>, ctx?: SkillContext) => SkillResult | Promise<SkillResult>;
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

// --------------------------------------------------------------------------
// AR follow-up prioritizer
// --------------------------------------------------------------------------
const PAYER_COLLECTIBILITY: Record<string, number> = {
  commercial: 0.95, medicare: 0.93, medicaid: 0.85, managed_medicaid: 0.82,
  workers_comp: 0.8, self_pay: 0.4, auto: 0.7, other: 0.75,
};
const TIMELY_FILING_DAYS: Record<string, number> = {
  medicare: 365, medicaid: 95, managed_medicaid: 95, commercial: 90, bcbs: 365,
  aetna: 90, cigna: 90, uhc: 90, tricare: 365, workers_comp: 365, auto: 180, self_pay: 0, other: 180,
};
const AGING_BUCKETS: [number, number | null][] = [[0, 30], [31, 60], [61, 90], [91, 120], [121, null]];

function bucketLabel(age: number): string {
  for (const [lo, hi] of AGING_BUCKETS) {
    if (hi === null) { if (age >= lo) return `${lo}+`; }
    else if (age >= lo && age <= hi) return `${lo}-${hi}`;
  }
  return "0-30";
}
function ageDays(acct: any): number {
  if (acct.age_days != null) return Math.max(0, parseInt(acct.age_days, 10) || 0);
  const dos = acct.date_of_service || acct.dos;
  if (dos) {
    const d = new Date(String(dos).slice(0, 10));
    if (!isNaN(d.getTime())) return Math.max(0, Math.floor((Date.now() - d.getTime()) / 86400000));
  }
  return 0;
}

export const arPrioritizer: Skill = {
  name: "ar_prioritizer",
  description:
    "Prioritize an AR worklist by aging, dollars-at-risk, and payer collectibility; flags timely-filing risk.",
  parameters: {
    type: "object",
    properties: {
      action: { type: "string", enum: ["prioritize", "aging_summary"] },
      accounts: { type: "array", items: { type: "object" } },
      limit: { type: "integer" },
    },
    required: ["accounts"],
  },
  execute(a) {
    const accounts = a.accounts;
    if (!Array.isArray(accounts)) return { success: false, error: "'accounts' must be a list" };
    const r2 = (n: number) => Math.round(n * 100) / 100;
    const enriched: any[] = [];
    const buckets: Record<string, any> = {};
    let totalAr = 0;
    for (const acct of accounts) {
      const balance = Number(acct.balance ?? 0) || 0;
      const age = ageDays(acct);
      const payer = String(acct.payer_class ?? "other").toLowerCase();
      const collect = PAYER_COLLECTIBILITY[payer] ?? PAYER_COLLECTIBILITY.other;
      const score = r2(balance * (1 + Math.min(age, 180) / 90) * collect);
      const tf = TIMELY_FILING_DAYS[payer] ?? TIMELY_FILING_DAYS.other;
      const tfAtRisk = !!tf && age >= tf - 15 && age < tf;
      const tfExpired = !!tf && age >= tf;
      const label = bucketLabel(age);
      const b = (buckets[label] ??= { bucket: label, count: 0, balance: 0 });
      b.count += 1; b.balance = r2(b.balance + balance); totalAr += balance;
      enriched.push({
        account_id: acct.account_id, balance: r2(balance), age_days: age, aging_bucket: label,
        payer_class: payer, priority_score: score, timely_filing_at_risk: tfAtRisk, timely_filing_expired: tfExpired,
      });
    }
    const ordered = ["0-30", "31-60", "61-90", "91-120", "121+"].filter((l) => buckets[l]).map((l) => buckets[l]);
    const summary = {
      total_accounts: accounts.length, total_ar: r2(totalAr), buckets: ordered,
      at_risk_timely_filing: enriched.filter((e) => e.timely_filing_at_risk).length,
      expired_timely_filing: enriched.filter((e) => e.timely_filing_expired).length,
    };
    if (a.action === "aging_summary") return { success: true, data: summary };
    enriched.sort((x, y) => y.priority_score - x.priority_score);
    const worklist = a.limit ? enriched.slice(0, Number(a.limit)) : enriched;
    return { success: true, data: { summary, worklist } };
  },
};

// --------------------------------------------------------------------------
// Underpayment / contract variance detector
// --------------------------------------------------------------------------
export const underpaymentDetector: Skill = {
  name: "underpayment_detector",
  description:
    "Detect payer underpayments by comparing paid amounts to contractually-expected rates per claim line.",
  parameters: {
    type: "object",
    properties: {
      lines: { type: "array", items: { type: "object" } },
      tolerance: { type: "number" },
    },
    required: ["lines"],
  },
  execute(a) {
    const lines = a.lines;
    if (!Array.isArray(lines)) return { success: false, error: "'lines' must be a list" };
    const tol = Number(a.tolerance ?? 0.01) || 0.01;
    const r2 = (n: number) => Math.round(n * 100) / 100;
    const flagged: any[] = [];
    const byCpt: Record<string, number> = {};
    let totalExpected = 0, totalPaid = 0, totalVar = 0;
    for (const ln of lines) {
      const cpt = String(ln.cpt ?? "").trim() || "UNKNOWN";
      const units = Number(ln.units ?? 1) || 1;
      const rate = Number(ln.expected_rate ?? 0) || 0;
      const paid = Number(ln.paid_amount ?? 0) || 0;
      const expected = r2(rate * units);
      const variance = r2(expected - paid);
      totalExpected += expected; totalPaid += paid;
      if (variance > tol) {
        totalVar += variance;
        byCpt[cpt] = r2((byCpt[cpt] ?? 0) + variance);
        flagged.push({ cpt, units, expected, paid: r2(paid), variance, pct_underpaid: expected ? r2((variance / expected) * 100) : null });
      }
    }
    flagged.sort((x, y) => y.variance - x.variance);
    return {
      success: true,
      data: {
        summary: {
          lines_evaluated: lines.length, lines_underpaid: flagged.length,
          total_expected: r2(totalExpected), total_paid: r2(totalPaid), total_recoverable_variance: r2(totalVar),
        },
        by_cpt: Object.entries(byCpt).sort((x, y) => y[1] - x[1]).map(([cpt, variance]) => ({ cpt, variance })),
        underpaid_lines: flagged,
      },
    };
  },
};

// --------------------------------------------------------------------------
// Timely filing calculator
// --------------------------------------------------------------------------
export const timelyFilingCalculator: Skill = {
  name: "timely_filing_calculator",
  description:
    "Compute claim timely-filing deadlines from date of service and payer; reports days remaining and status.",
  parameters: {
    type: "object",
    properties: {
      action: { type: "string", enum: ["calculate", "batch"] },
      date_of_service: { type: "string" },
      payer_class: { type: "string" },
      filing_limit_days: { type: "integer" },
      as_of: { type: "string" },
      claims: { type: "array", items: { type: "object" } },
    },
  },
  execute(a) {
    const AT_RISK = 15;
    const evalOne = (dos: any, payer: any, override: any, asOf: Date) => {
      const dosDate = new Date(String(dos).slice(0, 10));
      if (isNaN(dosDate.getTime())) throw new Error(`Invalid date: ${dos}`);
      const key = String(payer ?? "other").toLowerCase();
      const limit = override ? parseInt(override, 10) : (TIMELY_FILING_DAYS[key] ?? TIMELY_FILING_DAYS.other);
      const deadline = new Date(dosDate.getTime() + limit * 86400000);
      const daysRemaining = Math.floor((deadline.getTime() - asOf.getTime()) / 86400000);
      const status = daysRemaining < 0 ? "expired" : daysRemaining <= AT_RISK ? "at_risk" : "ok";
      return {
        date_of_service: dosDate.toISOString().slice(0, 10), payer_class: key,
        filing_limit_days: limit, deadline: deadline.toISOString().slice(0, 10), days_remaining: daysRemaining, status,
      };
    };
    try {
      const asOf = a.as_of ? new Date(String(a.as_of).slice(0, 10)) : new Date();
      if (a.action === "batch") {
        const claims = Array.isArray(a.claims) ? a.claims : [];
        const results = claims.filter((c: any) => c.date_of_service)
          .map((c: any) => evalOne(c.date_of_service, c.payer_class ?? "other", c.filing_limit_days, asOf));
        return {
          success: true,
          data: {
            results,
            expired: results.filter((r) => r.status === "expired").length,
            at_risk: results.filter((r) => r.status === "at_risk").length,
          },
        };
      }
      if (!a.date_of_service) return { success: false, error: "'date_of_service' is required" };
      return { success: true, data: evalOne(a.date_of_service, a.payer_class ?? "other", a.filing_limit_days, asOf) };
    } catch (e: any) {
      return { success: false, error: String(e?.message ?? e) };
    }
  },
};

// --------------------------------------------------------------------------
// Modifier recommender
// --------------------------------------------------------------------------
const FLAG_MODIFIERS: Record<string, [string, string]> = {
  separate_em_same_day_procedure: ["25", "Significant, separately identifiable E/M on the same day as a procedure"],
  distinct_procedural_service: ["59", "Distinct procedural service (consider X{EPSU} subsets)"],
  bilateral_procedure: ["50", "Bilateral procedure performed"],
  repeat_same_physician: ["76", "Repeat procedure by the same physician"],
  repeat_other_physician: ["77", "Repeat procedure by another physician"],
  multiple_procedures: ["51", "Multiple procedures in the same session"],
  professional_component: ["26", "Professional component only"],
  technical_component: ["TC", "Technical component only"],
  assistant_surgeon: ["80", "Assistant surgeon"],
  discontinued_procedure: ["53", "Discontinued procedure"],
  staged_related_postop: ["58", "Staged/related procedure during the postoperative period"],
  unrelated_postop: ["79", "Unrelated procedure during the postoperative period"],
  unrelated_em_postop: ["24", "Unrelated E/M during a postoperative period"],
  mandated_service: ["32", "Mandated service"],
  reduced_service: ["52", "Reduced services"],
};
const X_SUBSETS: Record<string, [string, string]> = {
  separate_encounter: ["XE", "Separate encounter"],
  separate_structure: ["XS", "Separate structure/organ"],
  separate_practitioner: ["XP", "Separate practitioner"],
  unusual_separate: ["XU", "Unusual non-overlapping service"],
};
const SIDE_MODIFIERS: Record<string, [string, string]> = { left: ["LT", "Left side"], right: ["RT", "Right side"] };

export const modifierRecommender: Skill = {
  name: "modifier_recommender",
  description: "Recommend CPT/HCPCS modifiers for a billing scenario, with a rationale for each.",
  parameters: {
    type: "object",
    properties: { cpt: { type: "string" }, scenario: { type: "object" } },
    required: ["scenario"],
  },
  execute(a) {
    const scenario = a.scenario;
    if (typeof scenario !== "object" || scenario === null) return { success: false, error: "'scenario' must be an object" };
    const recommended: { modifier: string; rationale: string }[] = [];
    const seen = new Set<string>();
    const add = (mod: string, why: string) => { if (!seen.has(mod)) { seen.add(mod); recommended.push({ modifier: mod, rationale: why }); } };
    for (const [flag, [mod, why]] of Object.entries(FLAG_MODIFIERS)) if (scenario[flag]) add(mod, why);
    const x = scenario.x_subset;
    if (x && X_SUBSETS[x]) add(X_SUBSETS[x][0], X_SUBSETS[x][1] + " (preferred over 59 when specific)");
    const side = String(scenario.side ?? "").toLowerCase();
    if (SIDE_MODIFIERS[side]) add(SIDE_MODIFIERS[side][0], SIDE_MODIFIERS[side][1]);
    if (!recommended.length)
      return { success: true, data: { cpt: a.cpt, recommended_modifiers: [], note: "No modifier indicated by the provided scenario." } };
    return { success: true, data: { cpt: a.cpt, recommended_modifiers: recommended, modifiers: recommended.map((r) => r.modifier) } };
  },
};

// --------------------------------------------------------------------------
// Medical necessity rationale builder
// --------------------------------------------------------------------------
export const medicalNecessityBuilder: Skill = {
  name: "medical_necessity_builder",
  description:
    "Build a structured medical-necessity rationale linking a service to diagnoses, indications, and failed conservative care, with a documentation checklist.",
  parameters: {
    type: "object",
    properties: {
      cpt: { type: "string" },
      service_description: { type: "string" },
      diagnoses: { type: "array", items: { type: "string" } },
      clinical_indications: { type: "array", items: { type: "string" } },
      failed_conservative: { type: "array", items: { type: "string" } },
      supporting_findings: { type: "array", items: { type: "string" } },
    },
    required: ["cpt", "diagnoses"],
  },
  execute(a) {
    const cpt = String(a.cpt ?? "").trim();
    const diagnoses: string[] = a.diagnoses ?? [];
    if (!cpt) return { success: false, error: "'cpt' is required" };
    if (!diagnoses.length) return { success: false, error: "At least one supporting diagnosis is required" };
    const svc = a.service_description || `the requested service (${cpt})`;
    const indications: string[] = a.clinical_indications ?? [];
    const findings: string[] = a.supporting_findings ?? [];
    const failed: string[] = a.failed_conservative ?? [];
    const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
    const parts = [`${cap(svc)} is medically necessary for this patient, who presents with ${diagnoses.join(", ")}.`];
    if (indications.length) parts.push("Clinical indications supporting the service include: " + indications.join("; ") + ".");
    if (findings.length) parts.push("Objective findings documented: " + findings.join("; ") + ".");
    if (failed.length) parts.push("Conservative management has been attempted without adequate response, including: " + failed.join("; ") + ".");
    parts.push(`Given the above, ${svc} is reasonable and necessary to diagnose or treat the documented condition(s) and is consistent with accepted standards of care.`);
    const checklist = [
      { item: "Diagnosis codes linked to the service", satisfied: diagnoses.length > 0 },
      { item: "Clinical indication documented", satisfied: indications.length > 0 },
      { item: "Objective findings (imaging/labs/exam)", satisfied: findings.length > 0 },
      { item: "Conservative treatment tried/failed", satisfied: failed.length > 0 },
    ];
    const missing = checklist.filter((c) => !c.satisfied).map((c) => c.item);
    return {
      success: true,
      data: {
        cpt, rationale: parts.join(" "), documentation_checklist: checklist, missing_documentation: missing,
        strength: missing.length === 0 ? "strong" : missing.length <= 2 ? "moderate" : "weak",
      },
    };
  },
};

// --------------------------------------------------------------------------
// HCC capture gap finder (sample model)
// --------------------------------------------------------------------------
const ICD_TO_HCC: Record<string, [string, string, number]> = {
  "E11.9": ["HCC19", "Diabetes without complication", 0.105],
  "E11.4": ["HCC18", "Diabetes with chronic complications", 0.302],
  "E11.5": ["HCC18", "Diabetes with chronic complications", 0.302],
  "I50": ["HCC85", "Congestive heart failure", 0.331],
  "N18.5": ["HCC136", "CKD stage 5", 0.289],
  "N18.6": ["HCC136", "ESRD/CKD stage 5", 0.289],
  "J44": ["HCC111", "COPD", 0.328],
  "F32": ["HCC155", "Major depression", 0.309],
  "C50": ["HCC12", "Breast cancer", 0.15],
  "I12": ["HCC138", "Hypertensive CKD", 0.289],
};
function mapDx(code: string): [string, string, number] | null {
  const c = (code || "").toUpperCase().trim();
  if (ICD_TO_HCC[c]) return ICD_TO_HCC[c];
  for (const [prefix, m] of Object.entries(ICD_TO_HCC)) if (c.startsWith(prefix)) return m;
  return null;
}

export const hccGapFinder: Skill = {
  name: "hcc_gap_finder",
  description:
    "Find HCC risk-adjustment recapture gaps and suspected new HCCs; estimates RAF and revenue impact (sample model).",
  parameters: {
    type: "object",
    properties: {
      current_year_dx: { type: "array", items: { type: "string" } },
      prior_year_hccs: { type: "array", items: { type: "string" } },
      revenue_per_raf: { type: "number" },
    },
    required: ["prior_year_hccs"],
  },
  execute(a) {
    const prior: string[] = a.prior_year_hccs ?? [];
    const currentDx: string[] = a.current_year_dx ?? [];
    const revPerRaf = Number(a.revenue_per_raf ?? 10000) || 10000;
    const currentHccs: Record<string, any> = {};
    for (const dx of currentDx) {
      const m = mapDx(dx);
      if (m) currentHccs[m[0]] = { hcc: m[0], label: m[1], raf_weight: m[2], from_dx: dx };
    }
    const priorSet = new Set(prior.map((h) => String(h).toUpperCase().trim()));
    const currentSet = new Set(Object.keys(currentHccs));
    const gaps: any[] = [];
    let rafAtRisk = 0;
    for (const hcc of priorSet) {
      if (!currentSet.has(hcc)) {
        const known = Object.values(ICD_TO_HCC).find((v) => v[0] === hcc);
        const weight = known ? known[2] : 0;
        rafAtRisk += weight;
        gaps.push({ hcc, label: known ? known[1] : "Unknown HCC", raf_weight: weight, reason: "not recaptured this year" });
      }
    }
    const suspected = Object.entries(currentHccs).filter(([h]) => !priorSet.has(h)).map(([, v]) => v);
    return {
      success: true,
      data: {
        recapture_gaps: gaps, suspected_new_hccs: suspected,
        raf_at_risk: Math.round(rafAtRisk * 1000) / 1000,
        estimated_revenue_at_risk: Math.round(rafAtRisk * revPerRaf * 100) / 100,
        summary: {
          prior_hccs: priorSet.size, recaptured: [...priorSet].filter((h) => currentSet.has(h)).length,
          gaps: gaps.length, suspected_new: suspected.length,
        },
      },
    };
  },
};

// --------------------------------------------------------------------------
// Structured extractor (general)
// --------------------------------------------------------------------------
const BUILTIN_PATTERNS: Record<string, string> = {
  email: "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}",
  phone: "(?:\\+?1[-.\\s]?)?\\(?\\d{3}\\)?[-.\\s]?\\d{3}[-.\\s]?\\d{4}",
  date: "\\d{1,2}[/-]\\d{1,2}[/-]\\d{2,4}|\\d{4}-\\d{2}-\\d{2}",
  ssn: "\\b\\d{3}-\\d{2}-\\d{4}\\b",
  mrn: "MRN[#:]?\\s*(\\d{4,})",
  npi: "\\b\\d{10}\\b",
  money: "\\$\\s?\\d{1,3}(?:,\\d{3})*(?:\\.\\d{2})?|\\b\\d+\\.\\d{2}\\b",
  icd10: "\\b[A-TV-Z]\\d{2}(?:\\.\\d{1,4})?\\b",
  cpt: "\\b\\d{5}\\b",
  zip: "\\b\\d{5}(?:-\\d{4})?\\b",
};

export const structuredExtractor: Skill = {
  name: "structured_extractor",
  description:
    "Extract structured fields from free text using typed patterns (email/phone/date/ssn/mrn/npi/money/icd10/cpt/zip) or custom regex/keyword.",
  parameters: {
    type: "object",
    properties: {
      action: { type: "string", enum: ["extract", "extract_all"] },
      text: { type: "string" },
      fields: { type: "array", items: { type: "object" } },
    },
    required: ["text", "fields"],
  },
  execute(a) {
    const text: string = a.text;
    const fields: any[] = a.fields ?? [];
    const action = a.action ?? "extract";
    if (!text) return { success: false, error: "'text' is required" };
    if (!Array.isArray(fields) || !fields.length) return { success: false, error: "'fields' must be a non-empty list" };
    const patternFor = (f: any): string => {
      if (f.regex) return f.regex;
      if (f.keyword) return `${f.keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*[:#-]?\\s*(.+?)(?:\\n|$)`;
      return BUILTIN_PATTERNS[String(f.type ?? "").toLowerCase()] ?? "";
    };
    const results: Record<string, any> = {};
    for (const f of fields) {
      const name = f.name;
      if (!name) continue;
      const pat = patternFor(f);
      if (!pat) { results[name] = action === "extract" ? null : []; continue; }
      let rx: RegExp;
      try { rx = new RegExp(pat, action === "extract_all" ? "ig" : "i"); }
      catch (e: any) { results[name] = { error: `bad pattern: ${e?.message ?? e}` }; continue; }
      if (action === "extract_all") {
        const out: string[] = [];
        for (const m of text.matchAll(rx)) out.push((m[1] ?? m[0]).trim());
        results[name] = out;
      } else {
        const m = rx.exec(text);
        results[name] = m ? (m[1] ?? m[0]).trim() : null;
      }
    }
    const found = Object.values(results).filter((v) => v && (!Array.isArray(v) || v.length)).length;
    return { success: true, data: { extracted: results, fields_requested: fields.length, fields_found: found } };
  },
};

// --------------------------------------------------------------------------
// Data insights (general)
// --------------------------------------------------------------------------
function nums(values: any[]): number[] {
  const out: number[] = [];
  for (const v of values) { const n = Number(v); if (isFinite(n)) out.push(n); }
  return out;
}
function mean(xs: number[]): number { return xs.reduce((a, b) => a + b, 0) / xs.length; }
function median(xs: number[]): number {
  const s = [...xs].sort((a, b) => a - b); const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}
function stdev(xs: number[]): number {
  if (xs.length < 2) return 0; const m = mean(xs);
  return Math.sqrt(xs.reduce((a, b) => a + (b - m) ** 2, 0) / (xs.length - 1));
}

export const dataInsights: Skill = {
  name: "data_insights",
  description: "Analyze an array of records: describe (stats), group_by (aggregate), or outliers (z-score).",
  parameters: {
    type: "object",
    properties: {
      action: { type: "string", enum: ["describe", "group_by", "outliers"] },
      records: { type: "array", items: { type: "object" } },
      fields: { type: "array", items: { type: "string" } },
      group_field: { type: "string" },
      agg_field: { type: "string" },
      agg: { type: "string", enum: ["sum", "mean", "count", "min", "max"] },
      field: { type: "string" },
      z_threshold: { type: "number" },
    },
    required: ["action", "records"],
  },
  execute(a) {
    const records: any[] = a.records;
    if (!Array.isArray(records)) return { success: false, error: "'records' must be a list" };
    const r4 = (n: number) => Math.round(n * 10000) / 10000;
    if (a.action === "describe") {
      if (!records.length) return { success: false, error: "No records to describe" };
      let fields: string[] = a.fields;
      if (!fields || !fields.length) fields = Object.keys(records[0]).filter((k) => typeof records[0][k] === "number");
      const stats: Record<string, any> = {};
      for (const f of fields) {
        const ns = nums(records.filter((r) => f in r).map((r) => r[f]));
        if (!ns.length) continue;
        stats[f] = { count: ns.length, sum: r4(ns.reduce((a, b) => a + b, 0)), mean: r4(mean(ns)), median: r4(median(ns)), min: Math.min(...ns), max: Math.max(...ns), stdev: r4(stdev(ns)) };
      }
      return { success: true, data: { row_count: records.length, fields: stats } };
    }
    if (a.action === "group_by") {
      const gf = a.group_field;
      if (!gf) return { success: false, error: "'group_field' is required" };
      const groups: Record<string, any[]> = {};
      for (const r of records) { const k = String(r[gf] ?? "∅"); (groups[k] ??= []).push(r[a.agg_field]); }
      const out = Object.entries(groups).map(([group, vals]) => {
        let value: number | null;
        if (a.agg === "count" || !a.agg) value = records.filter((r) => String(r[gf] ?? "∅") === group).length;
        else {
          const ns = nums(vals);
          if (!ns.length) value = null;
          else if (a.agg === "sum") value = r4(ns.reduce((x, y) => x + y, 0));
          else if (a.agg === "mean") value = r4(mean(ns));
          else if (a.agg === "min") value = Math.min(...ns);
          else if (a.agg === "max") value = Math.max(...ns);
          else value = null;
        }
        return { group, agg: a.agg ?? "count", field: a.agg_field, value };
      });
      out.sort((x, y) => (y.value ?? -Infinity) - (x.value ?? -Infinity));
      return { success: true, data: { groups: out, group_count: out.length } };
    }
    if (a.action === "outliers") {
      const field = a.field;
      if (!field) return { success: false, error: "'field' is required" };
      const ns = nums(records.filter((r) => field in r).map((r) => r[field]));
      if (ns.length < 2) return { success: false, error: "Need at least 2 numeric values" };
      const m = mean(ns), sd = stdev(ns), z = Number(a.z_threshold ?? 2) || 2;
      const outliers: any[] = [];
      if (sd > 0) for (const r of records) {
        const v = Number(r[field]); if (!isFinite(v)) continue;
        const zs = (v - m) / sd; if (Math.abs(zs) >= z) outliers.push({ record: r, value: v, z_score: Math.round(zs * 1000) / 1000 });
      }
      return { success: true, data: { field, mean: r4(m), stdev: r4(sd), z_threshold: z, outliers, outlier_count: outliers.length } };
    }
    return { success: false, error: `Unknown action: ${a.action}` };
  },
};

// ==========================================================================
// Phase 3 — data-backed skills (datasets live in D1: code_set / fee_rvu /
// gpci / denial_code). These require ctx.env.DB.
// ==========================================================================

function noDb(): SkillResult {
  return { success: false, error: "Datastore unavailable" };
}

function detectCodeType(code: string): string {
  const c = code.toUpperCase();
  if (/^[A-Z]\d{2}/.test(c)) {
    if (c.startsWith("D") && /^D\d{4}$/.test(c)) return "cdt";
    if (/^[A-Z]\d{4}$/.test(c)) return "hcpcs";
    return "icd10cm";
  }
  if (/^\d{5}$/.test(c)) return "cpt";
  return "unknown";
}

export const codeLookup: Skill = {
  name: "code_lookup",
  description: "Search ICD-10-CM, CPT, HCPCS, CDT codes by code or keyword (data in D1).",
  parameters: {
    type: "object",
    properties: {
      code: { type: "string", description: "Exact code, e.g. E11.9, 99213, A0428" },
      code_type: { type: "string", enum: ["icd10cm", "icd10pcs", "cpt", "hcpcs", "cdt", "revenue"] },
      search: { type: "string", description: "Keyword search (if code not provided)" },
      include_children: { type: "boolean" },
    },
  },
  async execute(a, ctx) {
    const db = ctx?.env?.DB;
    if (!db) return noDb();
    const code = String(a.code ?? "").toUpperCase().trim();
    const search = String(a.search ?? "").trim();
    if (!code && !search) return { success: false, error: "Either code or search term is required" };
    try {
      if (code) {
        const row = await db.prepare(
          "SELECT code, code_type, description, parent FROM code_set WHERE code = ?1",
        ).bind(code).first<any>();
        if (!row) {
          return { success: true, data: { code, code_type: a.code_type || detectCodeType(code), description: "Not found in local cache", valid: false } };
        }
        const out: any = { code: row.code, code_type: row.code_type, description: row.description, valid: true };
        if (a.include_children && row.parent) {
          const kids = await db.prepare("SELECT code, description FROM code_set WHERE parent = ?1").bind(row.code.split(".")[0]).all<any>();
          out.children = kids.results ?? [];
        }
        return { success: true, data: out };
      }
      // keyword search
      let stmt;
      if (a.code_type) {
        stmt = db.prepare("SELECT code, code_type, description FROM code_set WHERE description LIKE ?1 AND code_type = ?2 LIMIT 25").bind(`%${search}%`, a.code_type);
      } else {
        stmt = db.prepare("SELECT code, code_type, description FROM code_set WHERE description LIKE ?1 LIMIT 25").bind(`%${search}%`);
      }
      const res = await stmt.all<any>();
      return { success: true, data: { search_term: search, code_type: a.code_type ?? null, results: res.results ?? [], total: (res.results ?? []).length } };
    } catch (e: any) {
      return { success: false, error: String(e?.message ?? e) };
    }
  },
};

const CONVERSION_FACTOR = 33.2875;
const MODIFIER_ADJ: Record<string, { work: number; pe: number; mp: number; description: string }> = {
  "26": { work: 1.0, pe: 0.0, mp: 0.0, description: "Professional component only" },
  TC: { work: 0.0, pe: 1.0, mp: 1.0, description: "Technical component only" },
  "50": { work: 1.5, pe: 1.5, mp: 1.5, description: "Bilateral procedure" },
  "80": { work: 0.16, pe: 0.16, mp: 0.16, description: "Assistant surgeon" },
};

export const feeSchedule: Skill = {
  name: "fee_schedule",
  description:
    "Look up Medicare MPFS RVUs and calculate the allowed amount by locality (RVU x GPCI x conversion factor); data in D1.",
  parameters: {
    type: "object",
    properties: {
      action: { type: "string", enum: ["lookup", "calculate", "compare_localities"] },
      cpt_code: { type: "string" },
      locality: { type: "string", description: "CMS locality code (default 01010); comma-separated for compare" },
      modifier: { type: "string" },
    },
    required: ["action"],
  },
  async execute(a, ctx) {
    const db = ctx?.env?.DB;
    if (!db) return noDb();
    const action = a.action;
    const cpt = String(a.cpt_code ?? "").trim();
    const r2 = (n: number) => Math.round(n * 100) / 100;
    const r4 = (n: number) => Math.round(n * 10000) / 10000;
    try {
      const getRvu = (c: string) => db.prepare("SELECT * FROM fee_rvu WHERE cpt = ?1").bind(c).first<any>();
      const getGpci = (loc: string) => db.prepare("SELECT * FROM gpci WHERE locality = ?1").bind(loc).first<any>();

      if (action === "lookup") {
        if (!cpt) return { success: false, error: "cpt_code is required for lookup" };
        const rvu = await getRvu(cpt);
        if (!rvu) return { success: false, error: `CPT ${cpt} not found in fee schedule` };
        const total = rvu.work_rvu + rvu.pe_rvu_nf + rvu.mp_rvu_nf;
        return { success: true, data: {
          conversion_factor: CONVERSION_FACTOR, cpt_code: cpt, description: rvu.description,
          work_rvu: rvu.work_rvu, pe_rvu_nf: rvu.pe_rvu_nf, mp_rvu_nf: rvu.mp_rvu_nf,
          total_rvu_nf: r4(total), national_average_allowed: r2(total * CONVERSION_FACTOR),
        } };
      }

      if (action === "calculate") {
        if (!cpt) return { success: false, error: "cpt_code is required for calculate" };
        const rvu = await getRvu(cpt);
        if (!rvu) return { success: false, error: `CPT ${cpt} not found in fee schedule` };
        const loc = String(a.locality ?? "01010").trim() || "01010";
        const gpci = await getGpci(loc);
        if (!gpci) return { success: false, error: `Locality ${loc} not found` };
        const mod = String(a.modifier ?? "").trim().toUpperCase();
        const m = MODIFIER_ADJ[mod];
        const wMul = m ? m.work : 1, peMul = m ? m.pe : 1, mpMul = m ? m.mp : 1;
        const workC = rvu.work_rvu * wMul * gpci.work_gpci;
        const peC = rvu.pe_rvu_nf * peMul * gpci.pe_gpci;
        const mpC = rvu.mp_rvu_nf * mpMul * gpci.mp_gpci;
        const allowed = (workC + peC + mpC) * CONVERSION_FACTOR;
        return { success: true, data: {
          cpt_code: cpt, description: rvu.description, locality: gpci.name, locality_code: loc,
          modifier: mod || "None",
          components: { work_component: r4(workC), pe_component: r4(peC), mp_component: r4(mpC) },
          conversion_factor: CONVERSION_FACTOR, allowed_amount: r2(allowed),
          modifier_info: m ? { description: m.description } : null,
        } };
      }

      if (action === "compare_localities") {
        if (!cpt) return { success: false, error: "cpt_code is required for compare_localities" };
        const rvu = await getRvu(cpt);
        if (!rvu) return { success: false, error: `CPT ${cpt} not found in fee schedule` };
        const locs = String(a.locality ?? "").split(",").map((l: string) => l.trim()).filter(Boolean);
        const comparisons = [];
        for (const loc of locs) {
          const gpci = await getGpci(loc);
          if (!gpci) { comparisons.push({ locality_code: loc, error: "not found" }); continue; }
          const allowed = (rvu.work_rvu * gpci.work_gpci + rvu.pe_rvu_nf * gpci.pe_gpci + rvu.mp_rvu_nf * gpci.mp_gpci) * CONVERSION_FACTOR;
          comparisons.push({ locality_code: loc, locality: gpci.name, allowed_amount: r2(allowed) });
        }
        comparisons.sort((x: any, y: any) => (y.allowed_amount ?? 0) - (x.allowed_amount ?? 0));
        return { success: true, data: { cpt_code: cpt, description: rvu.description, comparisons } };
      }
      return { success: false, error: `Unknown action: ${action}` };
    } catch (e: any) {
      return { success: false, error: String(e?.message ?? e) };
    }
  },
};

const APPEAL_RECS: Record<string, { rec: string; docs: string[]; timeline?: string }> = {
  "CO-4": { rec: "Submit corrected claim with appropriate modifier", docs: ["Operative report supporting modifier use"] },
  "CO-11": { rec: "Submit appeal with clinical documentation", docs: ["Medical records showing medical necessity", "Physician letter of medical necessity"] },
  "CO-16": { rec: "Submit corrected claim with missing information", docs: ["Complete claim form with all required fields"] },
  "CO-50": { rec: "File formal appeal with clinical evidence", docs: ["Complete medical records", "Peer-reviewed literature supporting treatment", "Physician statement of medical necessity"], timeline: "120 days (Medicare)" },
  "CO-97": { rec: "Review NCCI edits and appeal if separately billable", docs: ["Documentation showing distinct procedure"] },
};

export const denialAnalyzer: Skill = {
  name: "denial_analyzer",
  description: "Analyze CARC/RARC denial codes (data in D1) and recommend appeal actions.",
  parameters: {
    type: "object",
    properties: {
      carc_codes: { type: "array", items: { type: "string" } },
      rarc_codes: { type: "array", items: { type: "string" } },
      claim_amount: { type: "number" },
      paid_amount: { type: "number" },
      payer: { type: "string" },
    },
    required: ["carc_codes"],
  },
  async execute(a, ctx) {
    const db = ctx?.env?.DB;
    if (!db) return noDb();
    const carc: string[] = a.carc_codes ?? [];
    const rarc: string[] = a.rarc_codes ?? [];
    if (!carc.length) return { success: false, error: "At least one CARC code is required" };
    try {
      const decode = async (code: string) => {
        const row = await db.prepare("SELECT code, ctype, description, category, appeal_priority FROM denial_code WHERE code = ?1").bind(code.toUpperCase()).first<any>();
        return row ?? { code: code.toUpperCase(), description: `Unknown code: ${code}`, category: "unknown", appeal_priority: "medium" };
      };
      const decodedCarc = [];
      for (const c of carc) decodedCarc.push(await decode(c));
      const decodedRarc = [];
      for (const r of rarc) decodedRarc.push(await decode(r));

      // Category/priority = highest-priority CARC (high > medium > low).
      const rank: Record<string, number> = { high: 3, medium: 2, low: 1, unknown: 0 };
      let top = decodedCarc[0];
      for (const d of decodedCarc) if ((rank[d.appeal_priority] ?? 0) > (rank[top.appeal_priority] ?? 0)) top = d;
      const appealable = top.appeal_priority === "high" || top.appeal_priority === "medium";

      const recommendations: string[] = [];
      const requiredDocs: string[] = [];
      let timeline = "30 days";
      for (const c of carc) {
        const r = APPEAL_RECS[c.toUpperCase()];
        if (r) { recommendations.push(r.rec); requiredDocs.push(...r.docs); if (r.timeline) timeline = r.timeline; }
      }
      if (!recommendations.length) recommendations.push("Review denial reason and determine appeal viability");

      const claim = Number(a.claim_amount ?? 0), paid = Number(a.paid_amount ?? 0);
      const adjusted = claim && paid ? Math.round((claim - paid) * 100) / 100 : 0;

      return { success: true, data: {
        payer: a.payer ?? "Unknown",
        carc: decodedCarc, rarc: decodedRarc,
        category: { category: top.category, appeal_priority: top.appeal_priority, appealable },
        financials: { claim_amount: claim, paid_amount: paid, adjusted_amount: adjusted, potential_recovery: appealable ? adjusted : 0, write_off: appealable ? 0 : adjusted },
        appeal_recommendation: { recommendations, required_documents: [...new Set(requiredDocs)], appeal_timeline: timeline, appeal_level: carc.map((c) => c.toUpperCase()).includes("CO-50") ? "Redetermination" : "Initial" },
      } };
    } catch (e: any) {
      return { success: false, error: String(e?.message ?? e) };
    }
  },
};

// --------------------------------------------------------------------------
// CCI editor (NCCI edits in D1)
// --------------------------------------------------------------------------
export const cciEditor: Skill = {
  name: "cci_editor",
  description:
    "Check NCCI edit pairs (data in D1): whether two codes are billable together, whether a modifier can override, and list edits for a code.",
  parameters: {
    type: "object",
    properties: {
      action: { type: "string", enum: ["check_pair", "check_with_modifier", "list_edits"] },
      code1: { type: "string" }, code2: { type: "string" }, modifier: { type: "string" }, code: { type: "string" },
    },
    required: ["action"],
  },
  async execute(a, ctx) {
    const db = ctx?.env?.DB;
    if (!db) return noDb();
    try {
      if (a.action === "list_edits") {
        const code = String(a.code ?? "").trim();
        if (!code) return { success: false, error: "'code' is required" };
        const res = await db.prepare("SELECT col1, col2, modifier_indicator, rationale FROM cci_edit WHERE col1 = ?1 OR col2 = ?1").bind(code).all<any>();
        return { success: true, data: { code, edits: res.results ?? [], total: (res.results ?? []).length } };
      }
      const c1 = String(a.code1 ?? "").trim();
      const c2 = String(a.code2 ?? "").trim();
      if (!c1 || !c2) return { success: false, error: "code1 and code2 are required" };
      const edit = await db.prepare(
        "SELECT col1, col2, modifier_indicator, rationale FROM cci_edit WHERE (col1 = ?1 AND col2 = ?2) OR (col1 = ?2 AND col2 = ?1)",
      ).bind(c1, c2).first<any>();
      if (!edit) {
        return { success: true, data: { code1: c1, code2: c2, edit_found: false, billable_together: true, message: "No NCCI edit found; codes may be billed together." } };
      }
      const modAllowed = edit.modifier_indicator === 1;
      if (a.action === "check_with_modifier") {
        const mod = String(a.modifier ?? "").trim().toUpperCase();
        const distinct = ["59", "XE", "XS", "XP", "XU"].includes(mod);
        const allowed = modAllowed && distinct;
        return { success: true, data: {
          code1: c1, code2: c2, edit_found: true, modifier: mod, modifier_indicator: edit.modifier_indicator,
          modifier_allows_billing: allowed, rationale: edit.rationale,
          message: allowed
            ? `Modifier ${mod} can override this edit if documentation supports a distinct service.`
            : modAllowed
              ? `This edit allows a modifier, but ${mod || "(none)"} is not a valid distinct-service modifier.`
              : "This edit cannot be overridden by any modifier (indicator 0).",
        } };
      }
      return { success: true, data: { code1: c1, code2: c2, edit_found: true, billable_together: false, modifier_indicator: edit.modifier_indicator, modifier_can_override: modAllowed, rationale: edit.rationale } };
    } catch (e: any) {
      return { success: false, error: String(e?.message ?? e) };
    }
  },
};

// --------------------------------------------------------------------------
// DRG grouper (MS-DRGs in D1)
// --------------------------------------------------------------------------
const DRG_BASE_RATE = 6131.0; // FY2024 approx national average
export const drgGrouper: Skill = {
  name: "drg_grouper",
  description:
    "Assign/look up MS-DRGs and calculate inpatient reimbursement (weight x base rate). Data in D1.",
  parameters: {
    type: "object",
    properties: {
      action: { type: "string", enum: ["lookup_drg", "calculate_reimbursement", "assign_drg"] },
      drg_code: { type: "string" }, principal_dx: { type: "string" },
      secondary_dx: { type: "array", items: { type: "string" } }, base_rate: { type: "number" },
    },
    required: ["action"],
  },
  async execute(a, ctx) {
    const db = ctx?.env?.DB;
    if (!db) return noDb();
    const baseRate = Number(a.base_rate ?? DRG_BASE_RATE) || DRG_BASE_RATE;
    const norm = (c: string) => String(c || "").replace(/^0+/, "").padStart(3, "0");
    const r2 = (n: number) => Math.round(n * 100) / 100;
    const getDrg = (c: string) => db.prepare("SELECT * FROM ms_drg WHERE drg = ?1").bind(norm(c)).first<any>();
    try {
      if (a.action === "lookup_drg" || a.action === "calculate_reimbursement") {
        const d = await getDrg(String(a.drg_code ?? ""));
        if (!d) return { success: false, error: `DRG ${a.drg_code} not found` };
        return { success: true, data: { drg: d.drg, description: d.description, weight: d.weight, gmlos: d.gmlos, type: d.type, severity: d.severity, base_rate: baseRate, reimbursement: r2(d.weight * baseRate) } };
      }
      // assign_drg
      const pdx = String(a.principal_dx ?? "").trim().toUpperCase();
      if (!pdx) return { success: false, error: "principal_dx is required for assign_drg" };
      const map = await db.prepare("SELECT base_drg, description FROM drg_dx WHERE dx = ?1").bind(pdx).first<any>();
      if (!map) return { success: true, data: { principal_dx: pdx, drg_assigned: null, message: "No DRG mapping for this principal diagnosis in the local table." } };
      const range = String(map.base_drg);
      const secondary: string[] = a.secondary_dx ?? [];
      const sev = secondary.length >= 2 ? "MCC" : secondary.length === 1 ? "CC" : "none";
      let codes: string[] = [];
      const m = range.match(/^(\d+)-(\d+)$/);
      if (m) { for (let i = parseInt(m[1], 10); i <= parseInt(m[2], 10); i++) codes.push(String(i).padStart(3, "0")); }
      else codes = [range];
      let chosen: any = null;
      for (const c of codes) {
        const d = await getDrg(c);
        if (d) { if (d.severity === sev) { chosen = d; break; } if (!chosen) chosen = d; }
      }
      if (!chosen) return { success: true, data: { principal_dx: pdx, base_drg_range: range, drg_assigned: null, message: "DRG range known but specific DRGs not in local table." } };
      return { success: true, data: { principal_dx: pdx, base_drg_range: range, severity: sev, drg_assigned: chosen.drg, description: chosen.description, weight: chosen.weight, base_rate: baseRate, reimbursement: r2(chosen.weight * baseRate) } };
    } catch (e: any) {
      return { success: false, error: String(e?.message ?? e) };
    }
  },
};

// --------------------------------------------------------------------------
// APC grouper (OPPS APCs in D1)
// --------------------------------------------------------------------------
export const apcGrouper: Skill = {
  name: "apc_grouper",
  description:
    "Assign/look up outpatient APCs from CPT/HCPCS and estimate OPPS payment. Data in D1.",
  parameters: {
    type: "object",
    properties: {
      action: { type: "string", enum: ["assign_apc", "lookup_apc", "calculate_opps_payment", "device_intensive_check"] },
      cpt_codes: { type: "array", items: { type: "string" } }, cpt_code: { type: "string" }, apc_code: { type: "string" },
    },
    required: ["action"],
  },
  async execute(a, ctx) {
    const db = ctx?.env?.DB;
    if (!db) return noDb();
    const r2 = (n: number) => Math.round(n * 100) / 100;
    const getApc = (c: string) => db.prepare("SELECT * FROM apc WHERE apc = ?1").bind(c).first<any>();
    const mapCpt = (c: string) => db.prepare("SELECT cpt, apc, description FROM cpt_apc WHERE cpt = ?1").bind(c).first<any>();
    try {
      if (a.action === "lookup_apc") {
        const d = await getApc(String(a.apc_code ?? "").trim());
        if (!d) return { success: false, error: `APC ${a.apc_code} not found` };
        return { success: true, data: { ...d, device_intensive: !!d.device_intensive } };
      }
      const cpts: string[] = a.cpt_codes ?? (a.cpt_code ? [a.cpt_code] : []);
      if (a.action === "device_intensive_check") {
        const cpt = String(a.cpt_code ?? cpts[0] ?? "").trim();
        const map = await mapCpt(cpt);
        if (!map) return { success: true, data: { cpt, mapped: false } };
        const apc = await getApc(map.apc);
        return { success: true, data: { cpt, apc: map.apc, device_intensive: !!(apc && apc.device_intensive) } };
      }
      if (!cpts.length) return { success: false, error: "cpt_codes is required" };
      const assignments: any[] = [];
      const notMapped: string[] = [];
      let total = 0;
      for (const cpt of cpts) {
        const map = await mapCpt(String(cpt).trim());
        if (!map) { notMapped.push(String(cpt)); continue; }
        const apc = await getApc(map.apc);
        if (!apc) { notMapped.push(String(cpt)); continue; }
        total += apc.payment_rate;
        assignments.push({ cpt: map.cpt, apc: apc.apc, description: apc.description, status_indicator: apc.status_indicator, payment_rate: apc.payment_rate, device_intensive: !!apc.device_intensive });
      }
      return { success: true, data: { assignments, not_mapped: notMapped, total_payment: r2(total) } };
    } catch (e: any) {
      return { success: false, error: String(e?.message ?? e) };
    }
  },
};

export const REGISTRY: Record<string, Skill> = {
  [rcmKpiCalculator.name]: rcmKpiCalculator,
  [emLevelAdvisor.name]: emLevelAdvisor,
  [patientCostEstimator.name]: patientCostEstimator,
  [arPrioritizer.name]: arPrioritizer,
  [underpaymentDetector.name]: underpaymentDetector,
  [timelyFilingCalculator.name]: timelyFilingCalculator,
  [modifierRecommender.name]: modifierRecommender,
  [medicalNecessityBuilder.name]: medicalNecessityBuilder,
  [hccGapFinder.name]: hccGapFinder,
  [structuredExtractor.name]: structuredExtractor,
  [dataInsights.name]: dataInsights,
  [codeLookup.name]: codeLookup,
  [feeSchedule.name]: feeSchedule,
  [denialAnalyzer.name]: denialAnalyzer,
  [cciEditor.name]: cciEditor,
  [drgGrouper.name]: drgGrouper,
  [apcGrouper.name]: apcGrouper,
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
