# AetheraAI — HIPAA Configuration Checklist

This is the app-side checklist to make AetheraAI safe for Protected Health
Information (PHI). A signed **Cloudflare BAA** (and written confirmation that
the specific services you use — R2, D1, Workers KV, Workers — are in scope) is a
prerequisite before any PHI is routed through Cloudflare. A BAA alone does not
make a deployment compliant; the controls below must also be in place.

> **Deployment model: single user.** This is a self-hosted, single-operator
> deployment — the owner is the only user. The API bearer key therefore *is* the
> access control (one key = the owner); there is no multi-tenant data to isolate,
> so per-user authorization is out of scope. The "minimum necessary" and access
> controls below are about protecting the one account, not separating users.

Legend: **[done]** already in code · **[config]** operator must set · **[todo]** code work needed before PHI · **n/a** not applicable to a single-user deployment

## 1. Encryption in transit
- **[config]** Expose the orchestrator/UI only over TLS (Cloudflare Tunnel or a TLS-terminating proxy). Never serve `:8000`/`:5173` in cleartext.
- **[done]** `docker-compose.secure.yml` overlay removes host port exposure for `chromadb`/`redis`/`searxng`/`litellm` and puts them on an `internal`-only network, so PHI never crosses a published plaintext port. Apply it for PHI deployments; add mTLS between services if they span hosts.
- **[config]** Ensure PHI LLM requests resolve only to **local Ollama** (loopback/host), never a cloud base URL.

## 2. Encryption at rest
- **[done]** User profiles encrypted with Fernet/AES via `ENCRYPTION_KEY` (`memory/user_profile.py`).
- **[done]** Health records use field-level encryption (and SQLCipher full-DB encryption when available) — `memory/health_records.py`.
- **[config]** Set a strong, secret-managed `ENCRYPTION_KEY` (never in the repo or chat); rotate per policy.
- **[config]** `conversation_store` (SQLite), `vector_store` (ChromaDB), and `fact_store` rely on **encrypted volumes** — app-level field encryption would break LIKE search and vector similarity. Use the `docker-compose.secure.yml` overlay with `DATA_ROOT` pointed at a LUKS/encrypted mount.

## 3. No PHI in logs
- **[done]** PHI detection/redaction exists (`orchestrator/sensitivity.py`); keep `PHI_DETECTION_ENABLED=true`.
- **[done]** PHI-redaction logging filter (`orchestrator/phi_logging.py`) installed at orchestrator startup.
- **[done]** The audit log redacts PHI/PII from its `resource`/`details` on write (`infrastructure/security/audit_logger.py`).
- **[config]** Disable prompt/response logging in `litellm_config.yaml` for PHI traffic (no callbacks that persist prompts).

## 4. Access controls
- **[config]** Front the app with Cloudflare Access (Zero Trust) + SSO/OTP; no anonymous access to PHI endpoints.
- **[done]** Bearer-key gate on `/api/*` (`orchestrator/auth.py`), enabled with `API_AUTH_ENABLED=true` + `API_KEYS`; off by default. The `docker-compose.secure.yml` overlay turns it on. The UI sends the key as a bearer token (set it in Settings → Privacy & Security, or via the `VITE_API_KEY` build var).
- **[done]** WebSocket auth: `/api/voice/stream`, `/api/pc/ws`, and `/api/pc/confirmations` validate the key via a `?token=` query param and reject unauthorized handshakes (close 1008); the UI appends it automatically.
- **n/a** Per-user authorization — out of scope for this single-user deployment (no other users to isolate). The bearer key authenticates the sole owner.
- **[config]** Keep `AUDIT_LOGGING_ENABLED=true`; restrict `CORS_ALLOW_ORIGINS` (no `*`) for PHI deployments.
- **[config]** Least-privilege on the Cloudflare API token and host/DB credentials.

## 5. Backup handling
- **[done]** `infrastructure/backup.py` supports Fernet-encrypted backups (fail-closed) and optional off-site upload to a Cloudflare R2 bucket (`upload_backup`), which refuses to upload an unencrypted backup.
- **[config]** Set `BACKUP_ENCRYPTION_KEY` (or reuse `ENCRYPTION_KEY`) so backups — which contain PHI and `.env` — are always encrypted.
- **[config]** Set `BACKUP_R2_BUCKET` + `R2_ACCOUNT_ID`/`R2_ACCESS_KEY_ID`/`R2_SECRET_ACCESS_KEY` to a **BAA-covered** bucket (not the non-PHI `aethera-ai-assets`); requires `boto3`. Set lifecycle/retention; restrict and log restores.
- **[config]** Periodically test restores; document RPO/RTO.

## 6. PHI routing / external processors
- **[done]** Flagged PHI/PII forces a local model (`orchestrator/cascade.py:select_model`), bypassing Ollama Cloud and HuggingFace.
- **[done]** Conversation PHI taint pinning (`orchestrator/phi_guard.py`): once a conversation contains PHI/PII, all later turns in it are pinned to local models even if the later message looks clean.
- **[config]** Any external service that could receive PHI (SearXNG, voice STT/TTS, email/calendar plugins, data connectors) must be PHI-free by design or disabled for PHI flows — otherwise each needs its own BAA.
- **[config]** Use `aethera-ai-cache` (KV) only for non-PHI keys (rate-limit counters, model metadata); do not cache chat responses there.

## 7. Audit, retention, governance
- **[config]** Retain audit logs ≥ 6 years, tamper-evident and access-controlled (the audit DB is append-only with `AUDIT_RETENTION_DAYS` default 2555).
- **[done]** Right-to-delete and retention for conversations: `DELETE /api/compliance/user-data/{user_id}` and `POST /api/compliance/retention/cleanup` (also `ConversationStore.delete_user_data` / `purge_older_than`; `CONVERSATION_RETENTION_DAYS`).
- **[todo]** Extend disposal to the remaining stores (vector store, facts, health records) for a complete patient erasure.
- **[config]** Keep the signed BAA + in-scope service list with these records; re-verify scope before adding any new Cloudflare service.
