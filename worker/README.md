# Aethera AI — Cloudflare Worker (phase 1)

A Cloudflare-native rewrite of the orchestrator, replacing the Python/Docker
stack. **Phase 1 is a vertical slice**, not feature parity with the Python app.

## What's here
- **Hono** API on Workers: `/api/health`, `/api/chat`, `/api/skills`,
  `/api/skills/:name/execute`, `/api/compliance/user-data/:userId`.
- **Agent loop** (`src/agent.ts`) — TS port of `orchestrator/agent.py`: the model
  calls tools, we execute them, feed results back, iterate.
- **Router + specialists** (`src/router.ts`, `src/specialists.ts`) — config-driven
  keyword routing (port of `orchestrator/router.py` + `config.yaml`). `/api/chat`
  routes the query to a specialist and uses its system prompt + tool set.
- **Skills** (`src/skills.ts`) — 14 ported. Pure-logic: `rcm_kpi_calculator`,
  `em_level_advisor`, `patient_cost_estimator`, `ar_prioritizer`,
  `underpayment_detector`, `timely_filing_calculator`, `modifier_recommender`,
  `medical_necessity_builder`, `hcc_gap_finder`, `structured_extractor`,
  `data_insights`. **Data-backed (datasets in D1)**: `code_lookup` (code_set),
  `fee_schedule` (fee_rvu + gpci), `denial_analyzer` (denial_code). Skills get an
  optional `ctx` with the D1 binding; pure skills ignore it.
- **D1** (`DB`) for conversations/messages, **KV** (`CACHE`, = `aethera-ai-cache`),
  **R2** (`ASSETS_BUCKET`, = `aethera-ai-assets`).
- **Auth** (`src/auth.ts`) — bearer-key gate on `/api/*` (`API_AUTH_ENABLED`),
  defense-in-depth behind Cloudflare Access.

## Bindings (already provisioned in this account)
| Binding | Resource | ID |
|---|---|---|
| `DB` | D1 `aethera-ai-db` | `92194d9c-6f40-414f-82a0-acdbc2e2dfb6` |
| `CACHE` | KV `aethera-ai-cache` | `e8180d7db46e4fc69ce27128b6ec6628` |
| `ASSETS_BUCKET` | R2 `aethera-ai-assets` | — |

## Develop / deploy
```bash
cd worker
npm install
npm test                      # vitest (skills + agent loop)
npm run typecheck             # tsc --noEmit
npm run db:init               # apply schema.sql to D1
npx wrangler secret put OLLAMA_API_KEY
npx wrangler secret put API_KEYS
npm run dev                   # local
npm run deploy                # wrangler deploy
```
CI deploys both Worker and Pages via `.github/workflows/deploy-cloudflare.yml`.

## Not yet ported (roadmap)
- **More data-backed skills** (`cci_editor`, `eligibility_checker`,
  `drug_reference`, `ndc_pricer`, `drg_grouper`, `apc_grouper`, `claim_scrubber`,
  …) — follow the same pattern as phase 3: seed the dataset into D1, query it
  from the skill. (`code_lookup` / `fee_schedule` / `denial_analyzer` are done.)
- **Memory / RAG** → **Vectorize**; **sensitivity/PHI routing**; **proactive
  scheduler** → **Cron Triggers + Queues**; **plugins/connectors**; **voice**.
- Local-only features (local Ollama, Whisper/Piper) don't exist serverless — all
  inference goes to cloud LLM APIs (needs a BAA for PHI).
