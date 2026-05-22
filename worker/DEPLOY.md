# Deploying the Aethera Worker (serverless — no Docker, no .env)

There is **no `.env` file** for the Worker. Configuration lives in three places:

| What | Where | How |
|---|---|---|
| Non-secret config (`LLM_BASE_URL`, `DEFAULT_MODEL`, `API_AUTH_ENABLED`) | `wrangler.toml` `[vars]` | already set |
| Runtime secrets (`OLLAMA_API_KEY`, `API_KEYS`) | Cloudflare (encrypted) | `wrangler secret put` |
| Deploy creds (`CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`) | your shell / GitHub repo secrets | `wrangler login` or env vars |

Account: `2c268625d9e6e4c084ff296fcdf5f3bd`. Bindings are already wired in
`wrangler.toml` (D1 `aethera-ai-db`, KV `aethera-ai-cache`, R2 `aethera-ai-assets`).
The D1 schema is already applied — no `db:init` needed.

## A. Deploy from your machine
```bash
cd worker
npm install
npx wrangler login                      # browser auth (or export CLOUDFLARE_API_TOKEN)

# Runtime secrets (interactive — values are NOT stored in the repo):
npx wrangler secret put OLLAMA_API_KEY  # your Ollama Cloud key
npx wrangler secret put API_KEYS        # a long random string; the UI/clients send it as a Bearer token

npm run typecheck && npm test           # verify before shipping
npx wrangler deploy
```

`API_AUTH_ENABLED=true`, so every `/api/*` route except `/api/health` requires
`Authorization: Bearer <one of API_KEYS>`.

## B. Deploy via GitHub Actions (no local tooling)
Add repo secrets (Settings → Secrets and variables → Actions):
`CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`. Set the Worker runtime secrets
once with `wrangler secret put` (above). Then merge to `main` (or run the
workflow manually) — `.github/workflows/deploy-cloudflare.yml` deploys the
Worker and the Pages UI.

## C. Custom domain + login
1. **Domain:** in the Workers dashboard for `aethera-ai`, add a **Custom Domain**
   `ai.aetherahealthcare.com` (or uncomment the `[[routes]]` block in
   `wrangler.toml` and redeploy). Cloudflare creates the DNS + cert.
2. **Login (Cloudflare Access):** Zero Trust → Access → Applications → Add
   (Self-hosted), domain `ai.aetherahealthcare.com`, policy Allow → Include →
   Emails = your address (template: `infrastructure/cloudflare/access_policy.json`).
   Now nobody reaches the API without an email one-time-passcode login.

## D. Frontend (Cloudflare Pages)
Build the UI pointed at the Worker and deploy:
```bash
cd ../ui
VITE_API_URL=https://ai.aetherahealthcare.com \
VITE_WS_URL=wss://ai.aetherahealthcare.com/api/voice/stream \
npm install && npm run build
npx wrangler pages deploy dist --project-name=aethera-ai
```

## E. Smoke test
```bash
curl -H "Authorization: Bearer <API_KEYS value>" https://ai.aetherahealthcare.com/api/health
curl -X POST https://ai.aetherahealthcare.com/api/chat \
  -H "Authorization: Bearer <API_KEYS value>" -H "Content-Type: application/json" \
  -d '{"message":"total AR 400000, avg daily charges 10000 — compute RCM KPIs"}'
```
`/api/health` returns the skill count; `/api/chat` routes to a specialist and
runs the agent loop.
