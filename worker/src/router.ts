import { SPECIALISTS, getSpecialist, type SpecialistConfig } from "./specialists";

export interface RoutingResult {
  primary_specialist: string;
  recommended_tools: string[];
  confidence: number;
  reasoning: string;
}

/**
 * Keyword-based intent routing (condensed port of orchestrator/router.py).
 * Scores each specialist by how many of its keywords appear in the query,
 * weighting longer (more specific) phrases higher; ties break by priority.
 */
export function route(query: string, forcedSpecialist?: string): RoutingResult {
  if (forcedSpecialist) {
    const spec = getSpecialist(forcedSpecialist);
    if (spec) {
      return {
        primary_specialist: spec.name,
        recommended_tools: spec.tools,
        confidence: 1,
        reasoning: `User forced specialist: ${spec.name}`,
      };
    }
  }

  const q = query.toLowerCase();
  // Token set for whole-word matching (keeps "/" so "e/m" stays one token),
  // avoiding false positives like "ar" matching inside "parse".
  const tokens = new Set(q.split(/[^a-z0-9/]+/).filter(Boolean));
  let best: SpecialistConfig | null = null;
  let bestScore = 0;
  const matched: string[] = [];

  for (const spec of SPECIALISTS) {
    let score = 0;
    const hits: string[] = [];
    for (const kw of spec.keywords) {
      const k = kw.toLowerCase();
      const isPhrase = k.includes(" ") || k.includes("-");
      const hit = isPhrase ? q.includes(k) : tokens.has(k);
      if (hit) {
        score += isPhrase ? 2 : 1; // specific phrases weigh more
        hits.push(kw);
      }
    }
    if (score > bestScore || (score === bestScore && score > 0 && best && spec.priority < best.priority)) {
      best = spec;
      bestScore = score;
      matched.length = 0;
      matched.push(...hits);
    }
  }

  if (!best || bestScore === 0) {
    const general = getSpecialist("general")!;
    return {
      primary_specialist: general.name,
      recommended_tools: general.tools,
      confidence: 0.3,
      reasoning: "No specialist keywords matched; using general.",
    };
  }

  const confidence = Math.min(1, 0.5 + bestScore * 0.15);
  return {
    primary_specialist: best.name,
    recommended_tools: best.tools,
    confidence: Math.round(confidence * 100) / 100,
    reasoning: `Matched ${best.name} on: ${matched.join(", ")}`,
  };
}
