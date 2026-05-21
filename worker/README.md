# Aethera AI — Cloudflare Worker (phase 1)

A Cloudflare-native rewrite of the orchestrator, replacing the Python/Docker
stack. **Phase 1 is a vertical slice**, not feature parity with the Python app.

## What's here
- **Hono** API on Workers: `/api/health`, `/api/chat`, `/api/skills`,
  `/api/skills/:name/execute`, `/api/compliance/user-data/:userId`.
- **Agent loop** (`src/agent.ts`) — TS port of `orchestrator/agent.py`: the model
  calls tools, we execute them, feed results back, iterate.
- **Skills** (`src/skills.ts`) — 3 ported so far: `rcm_kpi_calculator`,
  `em_level_advisor`, `patient_cost_estimator`. The other ~25 are still to port.
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
Router/specialists, the remaining 25 skills, memory/RAG (→ **Vectorize**),
sensitivity/PHI routing, proactive scheduler (→ **Cron Triggers + Queues**),
plugins/connectors, voice. Local-only features (local Ollama, Whisper/Piper) do
not exist serverless — all inference goes to cloud LLM APIs (needs a BAA for PHI).
