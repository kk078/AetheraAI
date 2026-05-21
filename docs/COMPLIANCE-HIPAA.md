# AetheraAI — HIPAA Configuration Checklist

This is the app-side checklist to make AetheraAI safe for Protected Health
Information (PHI). A signed **Cloudflare BAA** (and written confirmation that
the specific services you use — R2, D1, Workers KV, Workers — are in scope) is a
prerequisite before any PHI is routed through Cloudflare. A BAA alone does not
make a deployment compliant; the controls below must also be in place.

Legend: **[done]** already in code · **[config]** operator must set · **[todo]** code work needed before PHI

## 1. Encryption in transit
- **[config]** Expose the orchestrator/UI only over TLS (Cloudflare Tunnel or a TLS-terminating proxy). Never serve `:8000`/`:5173` in cleartext.
- **[todo]** Internal Docker traffic (orchestrator ↔ `chromadb`, `redis`, `litellm`, `searxng`) is plaintext HTTP. For PHI, keep all services on one trusted host or enable TLS/mTLS between them; document the trust boundary.
- **[config]** Ensure PHI LLM requests resolve only to **local Ollama** (loopback/host), never a cloud base URL.

## 2. Encryption at rest
- **[done]** User profiles encrypted with Fernet/AES via `ENCRYPTION_KEY` (`memory/user_profile.py`, `ENCRYPTED_DB_PATH`).
- **[config]** Set a strong, secret-managed `ENCRYPTION_KEY` (never in the repo or chat); rotate per policy.
- **[todo]** `conversation_store` (SQLite), `vector_store` (ChromaDB), `health_records`, and `fact_store` are not encrypted at rest by default. Mitigate with encrypted volumes / full-disk encryption (LUKS) on the host, or app-level encryption.
- **[config]** Place the `aethera-data`, `chroma-data`, and `redis-data` volumes on encrypted storage.

## 3. No PHI in logs
- **[done]** PHI detection/redaction exists (`orchestrator/sensitivity.py`); keep `PHI_DETECTION_ENABLED=true`.
- **[done]** PHI-redaction logging filter (`orchestrator/phi_logging.py`) scrubs PHI/PII from log records; install at startup.
- **[todo]** Verify the audit log (`infrastructure/security/audit_logger.py`) never stores message bodies or PHI in its `details`.
- **[config]** Disable prompt/response logging in `litellm_config.yaml` for PHI traffic (no callbacks that persist prompts).

## 4. Access controls
- **[config]** Front the app with Cloudflare Access (Zero Trust) + SSO/OTP; no anonymous access to PHI endpoints.
- **[todo]** Add authentication/authorization to `/api/*` and scope all `user_id` data so users cannot read each other's records.
- **[config]** Keep `AUDIT_LOGGING_ENABLED=true` (HIPAA access logging).
- **[config]** Least-privilege on the Cloudflare API token and host/DB credentials.

## 5. Backup handling
- **[done]** `infrastructure/backup.py` supports encrypted backups (Fernet) when a backup key is set; encryption fails closed (won't write plaintext if a key was requested but crypto is unavailable).
- **[config]** Set `BACKUP_ENCRYPTION_KEY` (or reuse `ENCRYPTION_KEY`) so backups — which contain PHI and `.env` — are always encrypted.
- **[todo]** Store PHI backups only in a **BAA-covered** R2 bucket (not the non-PHI `aethera-ai-assets`); set retention/lifecycle; restrict and log restores.
- **[config]** Periodically test restores; document RPO/RTO.

## 6. PHI routing / external processors
- **[done]** Flagged PHI/PII forces a local model (`orchestrator/cascade.py:select_model`), bypassing Ollama Cloud and HuggingFace.
- **[done]** Conversation PHI taint pinning (`orchestrator/phi_guard.py`): once a conversation contains PHI/PII, all later turns in it are pinned to local models even if the later message looks clean.
- **[config]** Any external service that could receive PHI (SearXNG, voice STT/TTS, email/calendar plugins, data connectors) must be PHI-free by design or disabled for PHI flows — otherwise each needs its own BAA.
- **[config]** Use `aethera-ai-cache` (KV) only for non-PHI keys (rate-limit counters, model metadata); do not cache chat responses there.

## 7. Audit, retention, governance
- **[config]** Retain audit logs ≥ 6 years, tamper-evident and access-controlled.
- **[todo]** Implement PHI retention/disposal and patient right-to-delete across the memory subsystem.
- **[config]** Keep the signed BAA + in-scope service list with these records; re-verify scope before adding any new Cloudflare service.
