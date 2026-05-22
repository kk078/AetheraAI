// Specialist definitions (ported/condensed from orchestrator/config.yaml).
// Every tool listed here resolves to a skill in the REGISTRY; the agent loop
// only advertises tools present in the registry, so the lists are kept in sync
// with what is actually callable.

export interface SpecialistConfig {
  name: string;
  display_name: string;
  description: string;
  keywords: string[];
  tools: string[];
  priority: number; // lower = higher priority on ties
  system_prompt: string;
}

export const SPECIALISTS: SpecialistConfig[] = [
  {
    name: "healthcare_provider",
    display_name: "Healthcare Provider",
    description: "Revenue cycle, coding, CDI, billing, claims, denials",
    priority: 1,
    keywords: ["coding", "icd", "cpt", "hcpcs", "drg", "apc", "claim", "denial", "appeal", "billing",
      "reimbursement", "ncci", "mue", "fee schedule", "prior auth", "medical necessity", "ar", "aging",
      "modifier", "e/m", "em level", "rcm", "kpi", "underpayment", "hcc", "raf"],
    tools: ["code_lookup", "cci_editor", "fee_schedule", "coverage_checker", "denial_analyzer",
      "denial_predictor", "appeals_writer", "drg_grouper", "apc_grouper", "edi_parser", "npi_lookup",
      "prior_auth", "medical_calculator", "ar_prioritizer", "rcm_kpi_calculator", "underpayment_detector",
      "patient_cost_estimator", "timely_filing_calculator", "em_level_advisor", "modifier_recommender",
      "medical_necessity_builder", "hcc_gap_finder", "claim_scrubber", "telehealth_rules", "credentialing_tracker"],
    system_prompt:
      "You are Aethera's healthcare revenue-cycle specialist. Help with coding, billing, claims, denials, " +
      "appeals, and AR. Use the available tools to compute precise answers and cite codes/amounts.",
  },
  {
    name: "healthcare_payer",
    display_name: "Healthcare Payer",
    description: "Claims adjudication, UM, network management, compliance",
    priority: 1,
    keywords: ["adjudication", "utilization management", "payer", "network", "pmpm", "cob", "subrogation",
      "remittance", "era", "835", "eligibility", "contract", "underpayment"],
    tools: ["remittance_parser", "claim_status", "eligibility_checker", "contract_analyzer", "risk_adjuster",
      "quality_tracker", "ndc_pricer", "denial_analyzer", "underpayment_detector", "patient_cost_estimator",
      "timely_filing_calculator", "hcc_gap_finder"],
    system_prompt:
      "You are Aethera's healthcare payer specialist. Help with adjudication, eligibility, remittance, " +
      "contracts, and network/UM questions, using tools for precise computation.",
  },
  {
    name: "healthcare_regulatory",
    display_name: "Healthcare Regulatory",
    description: "CMS regulations, HIPAA, OIG, fraud and abuse",
    priority: 2,
    keywords: ["hipaa", "compliance", "stark", "anti-kickback", "regulation", "cms", "oig", "fraud", "audit"],
    tools: ["compliance_checker", "coverage_checker", "medical_necessity_builder"],
    system_prompt:
      "You are Aethera's healthcare regulatory specialist. Address CMS rules, HIPAA, OIG, and compliance " +
      "carefully and flag where formal review is needed.",
  },
  {
    name: "healthcare_clinical",
    display_name: "Healthcare Clinical",
    description: "Clinical decision support, labs, medications, guidelines",
    priority: 2,
    keywords: ["lab", "medication", "drug", "clinical", "guideline", "screening", "diagnosis", "symptom", "e/m", "mdm"],
    tools: ["drug_reference", "lab_interpreter", "medical_calculator", "code_lookup",
      "em_level_advisor", "medical_necessity_builder"],
    system_prompt:
      "You are Aethera's clinical specialist. Provide clinical decision support with appropriate caution; " +
      "you are not a substitute for a licensed clinician.",
  },
  {
    name: "healthcare_analytics",
    display_name: "Healthcare Analytics",
    description: "RCM analytics, KPIs, risk stratification",
    priority: 2,
    keywords: ["analytics", "kpi", "metric", "dashboard", "trend", "risk stratification", "report", "days in ar"],
    tools: ["rcm_kpi_calculator", "ar_prioritizer", "hcc_gap_finder", "risk_adjuster", "quality_tracker",
      "data_insights"],
    system_prompt:
      "You are Aethera's healthcare analytics specialist. Compute KPIs and surface trends; show the numbers.",
  },
  {
    name: "finance",
    display_name: "Finance",
    description: "Financial analysis, accounting, budgeting",
    priority: 3,
    keywords: ["finance", "budget", "accounting", "revenue", "expense", "forecast", "cash flow", "profit"],
    tools: ["calculator", "data_insights"],
    system_prompt: "You are Aethera's finance specialist. Provide clear, quantified financial analysis.",
  },
  {
    name: "software_engineering",
    display_name: "Software Engineering",
    description: "Coding, architecture, debugging",
    priority: 3,
    keywords: ["code", "bug", "function", "api", "deploy", "refactor", "test", "typescript", "python", "worker"],
    tools: ["calculator", "structured_extractor"],
    system_prompt: "You are Aethera's software engineering specialist. Be precise and pragmatic.",
  },
  {
    name: "research",
    display_name: "Research",
    description: "Literature, summarization, synthesis",
    priority: 3,
    keywords: ["research", "study", "paper", "summarize", "literature", "evidence", "pubmed"],
    tools: ["structured_extractor", "data_insights"],
    system_prompt: "You are Aethera's research specialist. Synthesize sources and cite them.",
  },
  {
    name: "personal_assistant",
    display_name: "Personal Assistant",
    description: "Tasks, scheduling, reminders, general help",
    priority: 4,
    keywords: ["remind", "schedule", "task", "calendar", "email", "todo", "note"],
    tools: ["calculator", "structured_extractor"],
    system_prompt: "You are Aethera, a helpful personal assistant.",
  },
  {
    name: "general",
    display_name: "General",
    description: "General-purpose assistant",
    priority: 10,
    keywords: [],
    tools: ["structured_extractor", "data_insights"],
    system_prompt: "You are Aethera, a helpful, accurate AI assistant. Use tools when they improve precision.",
  },
];

export function getSpecialist(name: string): SpecialistConfig | undefined {
  return SPECIALISTS.find((s) => s.name === name);
}
