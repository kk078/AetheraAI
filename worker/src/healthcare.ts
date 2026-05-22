// Adapter map for the UI's /api/healthcare/* endpoints. Each entry names a
// skill in the REGISTRY and a transform from the request body to that skill's
// arguments, so the React UI's healthcare tool calls resolve to real skills.

export interface HealthcareRoute {
  skill: string;
  map: (body: any) => Record<string, any>;
}

export const HEALTHCARE_ROUTES: Record<string, HealthcareRoute> = {
  "code-lookup": { skill: "code_lookup", map: (b) => ({ code: b.code, code_type: b.codeType ?? b.code_type }) },
  "code-search": { skill: "code_lookup", map: (b) => ({ search: b.search, code_type: b.codeType ?? b.code_type }) },
  "denial-analyze": {
    skill: "denial_analyzer",
    map: (b) => ({
      carc_codes: b.carc_codes ?? (b.car_code ? [b.car_code] : []),
      rarc_codes: b.rarc_codes ?? (b.rarc_code ? [b.rarc_code] : []),
      claim_amount: b.claim_amount,
      paid_amount: b.paid_amount,
      payer: b.payer,
    }),
  },
  "denial-predict": { skill: "denial_predictor", map: (b) => ({ claim_data: b.claim_data ?? b }) },
  "appeal-generate": { skill: "appeals_writer", map: (b) => ({ action: "generate", ...b }) },
  "fee-schedule": {
    skill: "fee_schedule",
    map: (b) => ({ action: "calculate", cpt_code: b.cptCode ?? b.cpt_code ?? b.cpt, locality: b.locality ?? "01010", modifier: b.modifier }),
  },
  "npi-lookup": { skill: "npi_lookup", map: (b) => ({ npi: b.npi }) },
  "claim-analysis": { skill: "claim_scrubber", map: (b) => ({ ...b }) },
  "cci-check": {
    skill: "cci_editor",
    map: (b) => {
      const codes: string[] = b.codes ?? [];
      if (codes.length >= 2) return { action: "check_pair", code1: codes[0], code2: codes[1] };
      return { action: "list_edits", code: codes[0] ?? b.code };
    },
  },
  coverage: { skill: "coverage_checker", map: (b) => ({ cpt: b.code ?? b.cpt, payer: b.payer }) },
  "drg-group": { skill: "drg_grouper", map: (b) => ({ action: b.action ?? "assign_drg", ...b }) },
  "drug-lookup": { skill: "drug_reference", map: (b) => ({ action: "lookup", drug_name: b.drug_name ?? b.drugName }) },
  "risk-adjust": { skill: "risk_adjuster", map: (b) => ({ action: b.action ?? "calculate_raf", ...b }) },
  "medical-calc": { skill: "medical_calculator", map: (b) => (b.calculator ? b : { calculator: b.calc_type, params: b.params ?? b }) },
  "edi-parse": { skill: "edi_parser", map: (b) => ({ content: b.transaction_set ?? b.content ?? b.edi_content }) },
};
