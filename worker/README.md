# Aethera AI — Cloudflare Worker (phase 1)

A Cloudflare-native rewrite of the orchestrator, replacing the Python/Docker
stack. **Phase 1 is a vertical slice**, not feature parity with the Python app.

## What's here
- **Hono** API on Workers covering the React UI's surface:
  - Core: `/api/health`, `/api/skills`, `/api/skills/:name/execute`, `/api/specialists`,
    `/api/specialists/:name/query`.
  - Chat: `/api/chat`, `/api/chat/stream` (SSE), `/api/chat/specialist/:name`,
    `/api/chat/multi-agent`.
  - Conversations (D1): `GET/DELETE /api/conversations[/:id]`.
  - Healthcare tools (adapters over skills, see `src/healthcare.ts`):
    `POST /api/healthcare/{code-lookup,code-search,denial-analyze,denial-predict,
    appeal-generate,fee-schedule,npi-lookup,claim-analysis,cci-check,coverage,
    drg-group,drug-lookup,risk-adjust,medical-calc,edi-parse}`; plus
    `GET /api/codes/:codeType/:code`.
  - Memory: `POST/GET /api/memory/search`, `POST /api/memory`,
    `GET/POST /api/memory/profile/:userId`.
  - Compliance: `GET /api/audit`, `GET /api/audit/stats`, `POST /api/audit/export`,
    `DELETE /api/compliance/user-data/:userId`.
  - Proactive: `/api/knowledge/updates`, `/api/knowledge/check`, `/api/briefing`,
    `/api/briefing/generate`, `/api/news`, `/api/dashboard`.
  - Settings/models: `GET/POST /api/settings`, `GET /api/models`.
  - **Host-only / not-yet-ported** namespaces (voice, clipboard, upload, backup,
    cloudflare tunnel, plugins, connectors, temporal, alerts, queue, automations,
    and the heavier memory subsystems) return an explicit `501 {portable:false}`
    so the UI degrades gracefully instead of hitting an undefined route.
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
- **Memory / RAG** (`src/memory.ts`) — Workers AI embeddings (`@cf/baai/bge-base-en-v1.5`)
  + **Vectorize** for semantic recall. `/api/chat` retrieves relevant past
  memories into the system prompt and stores each turn. No-ops gracefully until
  the Vectorize index is created (see "Enable memory" below). Endpoints:
  `POST /api/memory`, `POST /api/memory/search`.
- **Proactive scheduler** (`src/knowledge.ts`, `src/briefing.ts`) — **Cron Triggers**
  drive a `scheduled` handler that refreshes CMS/regulatory updates (data.cms.gov +
  Federal Register → D1 `knowledge_updates`) and regenerates a morning briefing
  (cached in KV). Endpoints: `GET /api/knowledge/updates`, `POST /api/knowledge/check`,
  `GET /api/briefing`, `POST /api/briefing/generate`. A Queue binding is scaffolded
  (commented) for async tasks.
- **D1** (`DB`) for conversations/messages, **KV** (`CACHE`, = `aethera-ai-cache`),
  **R2** (`ASSETS_BUCKET`, = `aethera-ai-assets`), **Workers AI** (`AI`).
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
cd ../ui && npm run build     # build the UI; the Worker serves ui/dist as assets
cd ../worker
npm run dev                   # local
npm run deploy                # wrangler deploy (ships Worker + ui/dist)
```
The Worker serves both the API (`/api/*`) and the static React UI (Workers
Static Assets from `../ui/dist`, SPA fallback to `index.html`), so one deploy
ships the whole app. CI builds the UI then deploys the Worker via
`.github/workflows/deploy-cloudflare.yml`.

## Enable memory (one-time)
```bash
cd worker
wrangler vectorize create aethera-ai-memory --dimensions=768 --metric=cosine
# then uncomment the [[vectorize]] block in wrangler.toml and redeploy
```

## Skill port — complete
All healthcare skills from the Python app are ported (38 total in `REGISTRY`,
including general/RCM enhancement skills and the `coverage_checker`,
`denial_predictor`, `edi_parser`, `calculator` tools). Every tool advertised by
a specialist resolves to a registered skill. Data-backed skills query D1
(code_set, fee_rvu/gpci, denial_code, cci_edit, ms_drg/drg_dx, apc/cpt_apc, drug*,
ndc, hcc/hcc_dx, benefit_plan); the rest are pure-logic.

## Compliance
- **PHI/PII** (`src/sensitivity.ts`): `/api/chat` scans input, adds a
  confidentiality directive to the prompt on PHI, and returns a sensitivity flag.
- **Audit** (`src/audit.ts`): append-only `audit_log` in D1 (UPDATE/DELETE
  blocked by triggers); PHI is redacted before write. `GET /api/audit`.

## Connectors
- `npi_lookup` queries the live NPPES public API via `fetch`. Other read-only
  connectors (OpenFDA, PubMed, RxNorm) follow the same pattern.

## Not portable to serverless
- **Voice** (Whisper STT / Piper TTS) needs local model runtime — no Workers
  equivalent; use an external speech API if needed.
- "Force PHI to a local model" — there is no local model on Workers; PHI
  detection + audit + the confidentiality directive are the portable controls.
- Sensitivity/PHI routing, plugins/connectors, voice.
- Optional: enable the async task **Queue** (`wrangler queues create aethera-tasks`,
  then uncomment the `[[queues.*]]` blocks).
- Local-only features (local Ollama, Whisper/Piper) don't exist serverless — all
  inference goes to cloud LLM APIs (needs a BAA for PHI).
