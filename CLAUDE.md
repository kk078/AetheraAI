# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Aethera AI is a self-hosted personal AI "super agent" specialized in US healthcare (provider + payer) with broader multi-industry coverage. It is a multi-service stack: a FastAPI orchestrator (the brain), a React PWA frontend, a LiteLLM proxy fronting a model cascade (Ollama Cloud → HuggingFace → Ollama Local), and supporting services (ChromaDB, Redis, SearXNG, voice). The whole system is designed to run locally via Docker Compose with optional Cloudflare tunnel for remote access. Windows is the primary host target (`setup.ps1`, `.ps1` installers for host agent and clipboard agent).

## Common commands

### Backend (Python 3.11+)
```bash
# Install orchestrator deps (each subsystem has its own requirements.txt)
pip install -r orchestrator/requirements.txt
pip install -r requirements-test.txt

# Run the orchestrator locally (outside Docker)
uvicorn orchestrator.main:app --host 0.0.0.0 --port 8000

# Tests (config in tests/pytest.ini; asyncio_mode=auto, so no @pytest.mark.asyncio needed)
pytest                          # all tests
pytest tests/test_router.py     # one file
pytest tests/test_router.py::TestIntentClassifier::test_classify   # one test
pytest -m "not slow"            # skip slow tests
pytest -m "not requires_api"    # skip tests needing external APIs
pytest --cov=. --cov-report=html
```

### Frontend (`ui/`)
```bash
cd ui
npm install
npm run dev      # Vite dev server, host 0.0.0.0 (default port 5173)
npm run build
npm run lint     # eslint src --ext js,jsx
npm run test     # vitest
```

### Full stack
```bash
docker-compose up -d            # start all services
# orchestrator :8000, ui :5173, litellm :4000, chromadb :8000(internal), redis, searxng, voice
.\setup.ps1                     # Windows one-click setup
```

Copy `.env.example` → `.env` before running. Docker reads secrets/integration tokens from `.env`; see the `orchestrator` service env block in `docker-compose.yml` for the full list of recognized variables.

## Architecture (the big picture)

Request flow: **UI → `POST /api/chat` (orchestrator) → router → sensitivity scan → cascade → agent loop → LiteLLM → model**, with specialists/skills/plugins/connectors/memory layered in. Read these to understand the core loop:

- **`orchestrator/agent.py`** — the agentic reason-act loop (`run_agent_loop`). This is what lets the model actually *use* tools: the model proposes `tool_calls`, the loop executes each via the skill registry, appends the result as a `role="tool"` message, and iterates until the model returns a final answer or `max_iterations` is hit. The LLM call is injected (`llm_client`) so the loop is unit-testable without a live model (see `tests/test_agent.py`). `execute_llm_call` in `main.py` wires this to LiteLLM via `_litellm_client` and returns an `AgentResult` (content + `tools_used` + per-tool `invocations`). When adding agent behavior, extend this loop rather than the per-endpoint code.

- **`orchestrator/main.py`** — the FastAPI app and the single source of truth for HTTP/WebSocket endpoints. Subsystems (skills, plugins, connectors, memory, proactive) are loaded **lazily** via module-global `_get_*()` helpers that swallow import errors and log a warning, so the app boots even when an optional subsystem or its deps are missing. When adding a subsystem, follow this lazy-getter pattern rather than importing at top level.
- **`orchestrator/router.py`** — `AetheraRouter` + `IntentClassifier`. Classifies a query to one of the 20 specialists using keyword/intent/entity matching defined in `orchestrator/config.yaml`, and returns recommended tools. Routing is config-driven, not hardcoded.
- **`orchestrator/cascade.py`** — `ModelCascade` picks a provider/model with automatic failover across `OLLAMA_CLOUD → HUGGINGFACE → OLLAMA_LOCAL`, tracking per-provider rate limits (session/weekly/daily). Model definitions live here.
- **`orchestrator/sensitivity.py`** — PHI/PII detection and redaction (HIPAA). Runs on input before model calls when `PHI_DETECTION_ENABLED`.
- Other orchestrator modules: `multi_agent.py` (multi-specialist coordination), `temporal.py` (time-aware), `confidence.py`, `explainer.py` (reasoning chains), `scenarios.py`, `proactive.py`, `session_sync.py`, `pc_control.py`.

### Extensible subsystems — all follow a register-into-a-singleton-registry pattern

- **Specialists** (`specialists/`): domain experts. Each module calls `register_specialist(SpecialistConfig(...))` at import time into the `SPECIALISTS` dict (`specialists/__init__.py`). `_load_all_specialists()` auto-imports every module in `_SPECIALIST_MODULES` on package import, skipping failures. To add a specialist: create the module, register a `SpecialistConfig`, add it to `_SPECIALIST_MODULES`, and mirror its routing config (keywords/tools/priority) in `orchestrator/config.yaml`. `specialists/base.py` holds `TOOL_DEFINITIONS` (OpenAI function-calling spec) shared across specialists.
- **Skills** (`skills/`): the actual executable tools (this is where "healthcare tools" like `code_lookup`, `edi_parser`, `denial_predictor` live — under `skills/healthcare/`). Subclass `AetheraSkill`, decorate with `@skill(name=..., category=...)`, implement `name`/`description`/`parameters`/`execute()`. `SkillRegistry` (singleton) auto-discovers modules in `skills/builtin/`, `skills/healthcare/`, `skills/user/`. Healthcare API endpoints in `main.py` call `registry.execute("<skill_name>", ...)`. User-created skills support hot-reload.
- **Plugins** (`plugins/`): external integrations (Cloudflare, GitHub, email, calendar) under category subdirs. Subclass the plugin base; loaded via `PluginRegistry`.
- **Connectors** (`connectors/`): read-only external data sources (NPI Registry, OpenFDA, PubMed, RxNorm, FHIR, CMS). `ConnectorRegistry` (`get_registry()`).

### Memory & data
- **`memory/`**: `vector_store.py` (ChromaDB embeddings), `conversation_store.py` (SQLite history), `user_profile.py` (encrypted profiles via `ENCRYPTION_KEY`), plus `knowledge_graph.py`, `fact_store.py`, `memory_manager.py`, `health_records.py`, `learning.py`, `contradiction_detector.py`.
- **`pipeline/`** and **`data_intelligence/`**: ingestion/extraction pipelines (entities, facts, classification, indexing, profile updates).
- **`knowledge_bases/`**: downloaders/indexers for medical code sets and domain corpora (`download_all.py`, `index_all.py`, `manage.py`), split by domain (healthcare/finance/legal/technology).

### Other components
- **`proactive/`**: scheduler-driven morning briefings, alerts, news/feeds (`feeds.yaml`), weekly reports.
- **`voice/`**, **`clipboard/`**: STT/TTS and clipboard monitoring for healthcare codes; these run on the host (Windows installers `.ps1`).
- **`host_agent/`**: privileged host-side agent for PC control, with a `safety.py` guard layer.
- **`ui/`**: React 18 + Vite + Tailwind + Zustand PWA. SPA served via nginx in Docker (`ui/nginx.conf`).

## Conventions & gotchas

- **Config over code for routing.** Specialist keywords, tools, priorities, models, and enabled-state are declared in `orchestrator/config.yaml`. Keep the YAML and the in-code `SpecialistConfig` registration in sync.
- **Lazy, failure-tolerant subsystem loading** is intentional throughout (`main.py` getters, `_load_all_specialists`, skill discovery). Don't convert these to hard top-level imports — optional deps are expected to be absent in some deployments.
- **Tools = skills.** When the README/specialists refer to a "tool" by name (e.g. `npi_lookup`, `appeals_writer`), the executable implementation is a skill in `skills/` and the schema is in `specialists/base.py:TOOL_DEFINITIONS`. Adding a tool means: define its schema, implement the skill, and reference it in a specialist's `tools` list + config.
- **Per-subsystem `requirements.txt`.** `orchestrator/`, `memory/`, `host_agent/`, `clipboard/` each have their own; there is no top-level `requirements.txt` despite the README mentioning one.
- **Healthcare/PHI is a first-class concern.** PHI detection and audit logging are gated by env flags (`PHI_DETECTION_ENABLED`, `AUDIT_LOGGING_ENABLED`) and default on. Treat any data flowing through sensitivity/memory paths as potentially sensitive.
- **`skills-lock.json`** pins externally-sourced skill definitions (e.g. from `google/skills`) with content hashes; it is generated, not hand-edited.
- **`AETHERA-AI-FINAL-CLAUDE-CODE-PROMPT.md`** is the original product/build spec — useful for intent and feature scope, not a description of current code state.
