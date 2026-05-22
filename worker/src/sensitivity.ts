// PHI/PII detection + redaction (port of orchestrator/sensitivity.py intent).
// On Cloudflare there is no local model to force PHI to, but detection,
// redaction, and audit are fully portable — that's the compliance piece.

interface Rule { cat: string; phi: boolean; re: RegExp }

const RULES: Rule[] = [
  { cat: "ssn", phi: false, re: /\b\d{3}-\d{2}-\d{4}\b/g },
  { cat: "mrn", phi: true, re: /\bMRN[#:]?\s*\d{4,}\b/gi },
  { cat: "email", phi: false, re: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g },
  { cat: "phone", phi: false, re: /\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b/g },
  { cat: "dob", phi: true, re: /\b(?:DOB|date of birth)[#:\s]+\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b/gi },
  { cat: "npi", phi: true, re: /\bNPI[:\s#]+\d{10}\b/gi },
  { cat: "mbi", phi: true, re: /\bMBI[:\s]+[A-Z0-9]{11}\b/gi },
  { cat: "member_id", phi: true, re: /\b(?:member id|policy number|group number)[#:\s]+[A-Z0-9]{6,}\b/gi },
];
const HEALTHCARE_CONTEXT = /\b(patient|diagnosis|icd|cpt|claim|provider|hospital|clinic|prescription|treatment|specimen|lab result)\b/i;

export interface Sensitivity {
  contains_phi: boolean;
  contains_pii: boolean;
  categories: string[];
  level: "none" | "pii" | "phi";
  redacted: string;
}

/** Redact PHI/PII spans, replacing each with a [CATEGORY REDACTED] marker. */
export function redact(text: string): string {
  let out = text || "";
  for (const { cat, re } of RULES) {
    re.lastIndex = 0;
    out = out.replace(re, `[${cat.toUpperCase()} REDACTED]`);
  }
  return out;
}

/** Detect PHI/PII and return flags + a redacted copy. PII in a healthcare
 * context is treated as PHI (HIPAA). */
export function analyzeSensitivity(text: string): Sensitivity {
  const t = text || "";
  const cats = new Set<string>();
  let phi = false;
  let pii = false;
  for (const { cat, phi: isPhi, re } of RULES) {
    re.lastIndex = 0;
    if (re.test(t)) {
      cats.add(cat);
      if (isPhi) phi = true; else pii = true;
    }
  }
  if (HEALTHCARE_CONTEXT.test(t) && (pii || phi)) phi = true;
  const level: Sensitivity["level"] = phi ? "phi" : pii ? "pii" : "none";
  return { contains_phi: phi, contains_pii: pii, categories: [...cats], level, redacted: redact(t) };
}
