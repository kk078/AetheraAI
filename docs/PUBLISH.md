# Publishing Aethera at ai.aetherahealthcare.com (login-only)

This publishes the stack through a **Cloudflare Tunnel** (no inbound ports) and
puts **Cloudflare Access** in front so the site requires a login (email
one-time passcode) before any request reaches the app. Run these on the host
where `docker compose up` runs — they can't be done from the cloud dev sandbox
(its network can't reach the Cloudflare API).

## 0. Prerequisites
- `aetherahealthcare.com` is active in this Cloudflare account.
- Docker + the stack run locally (`docker compose up -d` works).

## 1. Fill in `.env`
Copy `.env.example` to `.env` and set at least:
```
OLLAMA_API_KEY=...            # https://ollama.com/settings/api
CLOUDFLARE_API_TOKEN=...      # rotate the one shared earlier; scope: DNS+Tunnel+Access edit
CLOUDFLARE_ACCOUNT_ID=2c268625d9e6e4c084ff296fcdf5f3bd
GITHUB_TOKEN=...              # optional
CLOUDFLARE_DOMAIN=ai.aetherahealthcare.com
CLOUDFLARE_ACCESS_EMAIL=you@example.com   # the only email allowed to log in
CLOUDFLARE_TUNNEL_TOKEN=      # filled in step 2
ENCRYPTION_KEY=...            # generate: python -c "import secrets;print(secrets.token_urlsafe(32))"
# Defense-in-depth app auth (Access is the primary login):
API_AUTH_ENABLED=true
API_KEYS=<a-long-random-string>
CORS_ALLOW_ORIGINS=https://ai.aetherahealthcare.com
```

## 2. Create the tunnel
In the Cloudflare dashboard → **Zero Trust → Networks → Tunnels → Create a
tunnel** (Cloudflared). Name it `aethera`. Copy the **connector token** into
`CLOUDFLARE_TUNNEL_TOKEN` in `.env`.

Then add **Public Hostnames** on that tunnel (cloudflared reaches the other
containers by service name on the compose network):

| Hostname | Path | Service |
|---|---|---|
| ai.aetherahealthcare.com | `api/*` | http://orchestrator:8000 |
| ai.aetherahealthcare.com | `ws*` | http://orchestrator:8000 |
| ai.aetherahealthcare.com | *(blank)* | http://ui:80 |

Cloudflare creates the `ai.aetherahealthcare.com` DNS record automatically.

> Prefer config-as-code instead of the dashboard? Use
> `infrastructure/cloudflare/tunnel.ai.yml` with a credentials file and run
> cloudflared directly on the host.

## 3. Require login (Cloudflare Access)
Zero Trust → **Access → Applications → Add → Self-hosted**:
- Application domain: `ai.aetherahealthcare.com`
- Add a policy: **Allow**, include **Emails** = your address (see
  `infrastructure/cloudflare/access_policy.json`). Identity method **Email OTP**
  is on by default — visitors get a one-time code to sign in.

This means nobody can reach the app without logging in with an approved email.

## 4. Rebuild the UI for the public URL and launch
Vite bakes `VITE_*` at build time, so set them and rebuild:
```
VITE_API_URL=https://ai.aetherahealthcare.com \
VITE_WS_URL=wss://ai.aetherahealthcare.com/api/voice/stream \
docker compose build ui

docker compose -f docker-compose.yml -f docker-compose.cloudflared.yml up -d
```
(Add `-f docker-compose.secure.yml` too for the PHI-hardening overlay.)

## 5. Verify
- Visit https://ai.aetherahealthcare.com → you should get the Cloudflare Access
  login (email code) before the UI loads.
- In the UI, open Settings → Privacy & Security and paste your `API_KEYS` value
  as the API Access Key (the backend has `API_AUTH_ENABLED=true`).

## Two layers of "login"
1. **Cloudflare Access** (edge): the real login — no traffic reaches the app
   without an approved email's OTP. This is what makes it "accessible only with
   login credentials."
2. **App API key** (`API_AUTH_ENABLED`): defense-in-depth on `/api/*` and the
   WebSockets, in case the origin is ever reached directly.
