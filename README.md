# Aethera AI - Personal AI Super Agent

A complete personal AI super agent specialized in US healthcare (provider AND payer services) with multi-industry capabilities.

## Features

- **20 Specialists**: Healthcare provider, payer, regulatory, clinical, analytics, IT, pharmacy, behavioral, dental/vision, workers comp, finance, legal, software engineering, media/marketing, research, personal assistant, Cloudflare ops, data analytics, and general
- **Model Cascade**: Ollama Cloud → HuggingFace → Ollama Local with automatic failover
- **PHI/PII Protection**: HIPAA-compliant detection and redaction of sensitive data
- **Skills System**: Extensible skill/plugins architecture matching Claude's tools
- **Memory**: Vector store (ChromaDB) + conversation history (SQLite) + encrypted user profiles
- **Healthcare Tools**: Code lookup, denial analysis, fee schedules, NPI lookup, claim analysis
- **Connectors**: NPI Registry, OpenFDA, PubMed, RxNorm, FHIR, CMS data
- **Plugins**: Cloudflare, GitHub, Email, Calendar integrations
- **Voice**: Speech-to-text and text-to-speech using local models
- **Clipboard Agent**: Automatic detection of healthcare codes and data
- **Proactive Intelligence**: Morning briefings, deadline alerts, news aggregation
- **PWA Frontend**: React 18 + Vite + TailwindCSS with offline support

## Hardware Requirements

- **RAM**: 16GB minimum
- **GPU**: NVIDIA GPU with 2GB+ VRAM (for local models)
- **Storage**: 50GB+ for models and knowledge bases

## Quick Start

### 1. Clone and Setup

```bash
# Run the one-click setup
.\setup.ps1
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
# Ollama Cloud (required)
OLLAMA_CLOUD_KEY=your-ollama-cloud-key

# Cloudflare (optional, for remote access)
CLOUDFLARE_API_KEY=your-api-key
CLOUDFLARE_ACCOUNT_ID=your-account-id
CLOUDFLARE_ZONE_ID=your-zone-id
```

### 3. Start Services

```bash
docker-compose up -d
```

### 4. Access the UI

Open http://localhost:5173 in your browser.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     React PWA Frontend                       │
│  (Chat, Dashboard, Command Palette, Specialist Badges)       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Orchestrator                      │
│  (Router, Cascade, Sensitivity, Multi-Agent, Temporal)       │
└─────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Specialists   │  │     Skills      │  │    Plugins      │
│   (20 modules)  │  │  (8+ modules)   │  │  (4 modules)    │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Connectors + Memory                      │
│  (NPI, FDA, PubMed, RxNorm | ChromaDB, SQLite, Encryption)   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    LiteLLM Proxy + Ollama                    │
│         (Unified API | Cloud + Local Model Cascade)          │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
AetheraAI/
├── docker-compose.yml       # Main Docker configuration
├── docker-compose.override.yml  # GPU passthrough config
├── .env.example             # Environment template
├── litellm_config.yaml      # LiteLLM proxy configuration
├── setup.ps1                # One-click setup script
├── requirements.txt         # Python dependencies
├── requirements-test.txt    # Testing dependencies
│
├── orchestrator/            # FastAPI backend
│   ├── main.py             # Main application
│   ├── router.py           # Intent classification
│   ├── cascade.py          # Model cascade
│   ├── sensitivity.py      # PHI/PII detection
│   ├── config.yaml         # Configuration
│   ├── multi_agent.py      # Multi-agent coordination
│   ├── temporal.py         # Time-aware processing
│   ├── confidence.py       # Confidence scoring
│   └── proactive.py        # Proactive intelligence
│
├── specialists/             # 20 specialist modules
│   ├── healthcare_provider.py
│   ├── healthcare_payer.py
│   ├── healthcare_regulatory.py
│   ├── healthcare_clinical.py
│   ├── healthcare_analytics.py
│   ├── healthcare_it.py
│   ├── healthcare_pharmacy.py
│   ├── healthcare_behavioral.py
│   ├── healthcare_dental_vision.py
│   ├── healthcare_workers_comp.py
│   ├── finance.py
│   ├── legal.py
│   ├── software_engineering.py
│   ├── media_marketing.py
│   ├── research.py
│   ├── personal_assistant.py
│   ├── cloudflare_ops.py
│   ├── data_analytics.py
│   └── general.py
│
├── skills/                  # Skills system
│   ├── skill_base.py
│   ├── skill_registry.py
│   └── builtin/
│       ├── calculator.py
│       ├── web_researcher.py
│       ├── summarizer.py
│       └── document_creator.py
│
├── plugins/                 # Plugin system
│   ├── plugin_base.py
│   ├── plugin_registry.py
│   ├── cloud/
│   │   └── cloudflare_plugin.py
│   ├── dev/
│   │   └── github_plugin.py
│   └── communication/
│       ├── email_plugin.py
│       └── calendar_plugin.py
│
├── connectors/              # Data connectors
│   ├── connector_base.py
│   ├── connector_registry.py
│   ├── npi_connector.py
│   ├── openfda_connector.py
│   ├── pubmed_connector.py
│   ├── rxnorm_connector.py
│   ├── fhir_connector.py
│   └── cms_connector.py
│
├── memory/                  # Memory system
│   ├── vector_store.py     # ChromaDB
│   ├── conversation_store.py  # SQLite
│   └── user_profile.py     # Encrypted profiles
│
├── knowledge/               # Knowledge base downloaders
│   └── code_downloader.py
│
├── voice/                   # Voice subsystem
│   ├── stt_tts.py          # Speech-to-text / Text-to-speech
│   └── clipboard_agent.py  # Clipboard monitoring
│
├── infrastructure/          # Infrastructure
│   ├── cloudflare_setup.py
│   ├── backup.py
│   └── monitoring.py
│
├── tests/                   # Test suite
│   ├── test_router.py
│   ├── test_cascade.py
│   ├── test_sensitivity.py
│   ├── test_skills.py
│   ├── test_plugins.py
│   ├── test_connectors.py
│   ├── test_memory.py
│   └── test_specialists.py
│
└── ui/                      # React frontend
    ├── src/
    │   ├── App.jsx
    │   ├── main.jsx
    │   ├── components/
    │   ├── hooks/
    │   └── utils/
    └── public/
```

## API Endpoints

### Chat
- `POST /api/chat` - Send message
- `POST /api/chat/stream` - Streaming SSE response

### Specialists
- `GET /api/specialists` - List all specialists
- `POST /api/specialists/{name}/query` - Query specialist

### Skills
- `GET /api/skills` - List skills
- `POST /api/skills/{name}/execute` - Execute skill

### Healthcare
- `POST /api/healthcare/code-lookup` - Lookup medical code
- `POST /api/healthcare/denial-analysis` - Analyze denial
- `POST /api/healthcare/fee-schedule` - Get fee schedule
- `POST /api/healthcare/npi-lookup` - Lookup NPI
- `POST /api/healthcare/claim-analysis` - Analyze claim

### Memory
- `POST /api/memory` - Save to memory
- `POST /api/memory/search` - Search memory
- `GET /api/memory/conversation/{id}` - Get conversation

## Running Tests

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=. --cov-report=html
```

## License

MIT License - See LICENSE file for details.

## Disclaimer

This software is for educational and research purposes. For production healthcare use, ensure HIPAA compliance and obtain appropriate certifications.
