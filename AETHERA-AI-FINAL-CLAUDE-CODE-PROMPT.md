# AETHERA AI — Complete Claude Code Build Prompt

## COPY EVERYTHING BELOW THIS LINE INTO CLAUDE CODE

---

You are building "Aethera" — a personal AI super agent specialized in US healthcare (provider AND payer services across ALL service lines) with multi-industry capabilities, a Claude-like skills/plugins/connectors architecture, running on a local laptop and accessible from anywhere in the world. Build the COMPLETE project. Every file must be production-grade, fully functional, no placeholders, no TODOs.

---

## SECTION 1: HARDWARE & CONSTRAINTS

```
Device name:    Aethera_Laptop
Processor:      11th Gen Intel Core i5-11320H @ 3.20GHz (2.50 GHz base) — 4 cores / 8 threads
RAM:            16.0 GB (15.7 GB usable)
GPU 1:          NVIDIA GeForce MX450 (2 GB VRAM) — CUDA capable, use for small model inference
GPU 2:          Intel Iris Xe Graphics (128 MB) — display only
Storage:        432 GB free of 477 GB
OS:             Windows 10/11, 64-bit
Docker:         Docker Desktop for Windows (WSL2 backend)
```

### Model Strategy
- NVIDIA MX450 can accelerate small Ollama models (up to ~4B params with 2GB VRAM)
- GPU-accelerated local models: qwen3.5:4b, gemma4:e2b (both fit in 2GB VRAM)
- CPU-only local models: qwen3.5:9b (smart fallback, always available)
- Embedding model: nomic-embed-text (for ChromaDB RAG, ~300MB)
- Cloud-first strategy using Ollama Cloud (user has an account) as primary brain
- Sensitive/PHI queries ALWAYS route to local Ollama (never leave the machine)

### LLM Strategy — Ollama Local + Ollama Cloud (your account)

**Primary: Ollama Cloud (your existing Ollama account — requires Pro plan $20/mo for 3 concurrent models)**
- API: https://ollama.com (OpenAI-compatible, same as local Ollama API format)
- Auth: OLLAMA_API_KEY from your ollama.com account
- Cloud models available (these run on Ollama's cloud GPUs, no local resources needed):
  * qwen3.5:122b — BEST overall, frontier intelligence, tools+thinking+vision (Level 3 usage)
  * deepseek-v4-flash — 284B MoE (13B active), 1M context, deep reasoning (Level 2 usage)
  * kimi-k2.6 — Best coder, multimodal agentic, MIT licensed (Level 3 usage)
  * gemma4:26b — Excellent tool calling, vision, reasoning (Level 2 usage)
  * nemotron-3-super — 120B MoE (12B active), efficient multi-agent (Level 2 usage)
  * deepseek-v4-pro — Frontier MoE, 3 reasoning modes (Level 4 usage — use sparingly)
  * glm-5.1 — Strong agentic engineering and coding (Level 3 usage)
  * qwen3.5:35b — Good balance of speed and intelligence (Level 2 usage)
- Session limits reset every 5 hours, weekly limits reset every 7 days
- Pro plan: 3 concurrent cloud models (sufficient for multi-agent reasoning)

**Secondary: Ollama Local (runs on your laptop, unlimited, private)**
- qwen3.5:4b — GPU-accelerated on MX450 (~2.5GB), fast for simple queries + PHI data
- gemma4:e2b — GPU-accelerated on MX450 (~1.5GB), good tool calling + structured output
- qwen3.5:9b — CPU-only (~5.5GB RAM), smart fallback when cloud quota exhausted
- nomic-embed-text — CPU (~300MB), embeddings for ChromaDB vector search
- No API key, no rate limits, no cost, full data privacy
- Ollama runs as Docker container with NVIDIA MX450 GPU passthrough

**Tertiary: HuggingFace Inference API (Free tier, optional extra capacity)**
- URL: https://api-inference.huggingface.co/models/{model_id}
- Free tier: works without login for many models, free account for higher limits
- Models: Qwen/Qwen2.5-72B-Instruct, mistralai/Mistral-7B-Instruct-v0.3
- Rate limit: ~1000 requests/day without token
- Used as overflow when both Ollama Cloud and Local are busy

**Quaternary: User-configurable endpoints**
- The system accepts ANY OpenAI-compatible API URL configured in .env
- User can add future free providers (Groq, Cerebras, SambaNova, etc.) as they get accounts

**Architecture: LiteLLM Proxy unifies ALL providers behind one OpenAI-compatible API**

```
User Query → Sensitivity Check (PHI/PII detection)
    │
    ├── Contains PHI/PII → FORCE Ollama Local (qwen3.5:4b on GPU) ← NEVER leaves machine
    │
    └── Safe for cloud → Model Cascade:
         │
         ├── Simple/fast query → Ollama Local GPU (qwen3.5:4b) ← instant, free, unlimited
         ├── Medium query → Ollama Cloud (gemma4:26b) ← fast, good tool calling
         ├── Complex healthcare → Ollama Cloud (qwen3.5:122b) ← smartest, best reasoning
         ├── Deep reasoning → Ollama Cloud (deepseek-v4-flash) ← 1M context, thinking
         ├── Coding tasks → Ollama Cloud (kimi-k2.6) ← best coder, agentic
         ├── Multi-agent → Ollama Cloud (nemotron-3-super) ← efficient parallel
         ├── Overflow → HuggingFace Free (Qwen2.5-72B) ← when cloud quota hit
         └── All exhausted → Ollama Local CPU (qwen3.5:9b) ← always available
    
    All unified via: LiteLLM Proxy (port 4000)
```

---

## SECTION 2: PROJECT STRUCTURE

```
aethera/
├── docker-compose.yml                    # Full stack — 8 services
├── docker-compose.override.yml           # GPU passthrough for NVIDIA MX450
├── .env.example                          # Config template with detailed comments
├── setup.ps1                             # One-click Windows PowerShell setup
├── update.ps1                            # Update with backup + rollback
├── backup.ps1                            # Manual backup to local + optional cloud
│
├── orchestrator/                         # The brain — FastAPI server
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                           # FastAPI app with all endpoints
│   ├── router.py                         # Intent classification → specialist routing
│   ├── cascade.py                        # Model cascade with rate limit tracking
│   ├── sensitivity.py                    # PHI/PII detection → force local model
│   ├── multi_agent.py                    # Chain-of-agents: specialists debate
│   ├── temporal.py                       # Deadline/expiration tracking engine
│   ├── scenarios.py                      # "What if" counterfactual analysis
│   ├── confidence.py                     # Response confidence scoring
│   ├── explainer.py                      # Reasoning chain logging
│   ├── session_sync.py                   # Cross-device session continuity
│   └── config.yaml                       # All specialist + model + tool config
│
├── specialists/                          # Domain expert modules
│   ├── __init__.py
│   ├── base.py                           # Base specialist class
│   ├── healthcare_provider.py            # Revenue cycle, coding, CDI, billing
│   ├── healthcare_payer.py               # Claims adjudication, UM, network mgmt
│   ├── healthcare_regulatory.py          # CMS, HIPAA, OIG, state regulations
│   ├── healthcare_clinical.py            # Clinical knowledge, drug info, labs
│   ├── healthcare_analytics.py           # HEDIS, Stars, PMPM, MLR, risk adj
│   ├── healthcare_it.py                  # EHR, HL7, FHIR, interoperability
│   ├── healthcare_pharmacy.py            # PBM, formulary, drug pricing, 340B
│   ├── healthcare_behavioral.py          # Mental health parity, SUD, telehealth
│   ├── healthcare_dental_vision.py       # CDT codes, dental/vision benefits
│   ├── healthcare_workers_comp.py        # WC billing, state rules, IME
│   ├── finance.py                        # Accounting, tax, invoicing, projections
│   ├── legal.py                          # Contracts, IP, compliance, privacy
│   ├── software_engineering.py           # Full-stack dev, DevOps, architecture
│   ├── media_marketing.py               # Content, SEO, ASO, social, branding
│   ├── research.py                       # Deep research, literature review
│   ├── personal_assistant.py             # Calendar, tasks, travel, home, life
│   ├── cloudflare_ops.py                 # Cloudflare management specialist
│   └── data_analytics.py                # Data science, visualization, reporting
│
├── skills/                               # Claude-like skills system
│   ├── __init__.py
│   ├── skill_registry.py                 # Skill discovery, loading, execution
│   ├── skill_base.py                     # Base class for all skills
│   ├── SKILL_SPEC.md                     # How to create new skills
│   ├── builtin/                          # Built-in skills (always available)
│   │   ├── document_creator.py           # Generate DOCX, PDF, XLSX, PPTX, MD
│   │   ├── spreadsheet_analyzer.py       # Read/write/analyze any spreadsheet
│   │   ├── pdf_processor.py              # Read/create/fill/merge/split PDFs
│   │   ├── presentation_builder.py       # Create slide decks from content
│   │   ├── code_executor.py              # Sandboxed Python/Node/Bash execution
│   │   ├── web_researcher.py             # Multi-hop search + summarize + cite
│   │   ├── data_visualizer.py            # Charts, graphs, dashboards from data
│   │   ├── image_analyzer.py             # Describe/OCR/extract from images
│   │   ├── file_converter.py             # Convert between any file formats
│   │   ├── email_composer.py             # Draft emails in user's style
│   │   ├── calculator.py                 # Math, financial, statistical, clinical
│   │   ├── translator.py                 # Multi-language translation
│   │   ├── summarizer.py                 # Summarize any content (docs, URLs, meetings)
│   │   └── diagram_generator.py          # Mermaid/SVG/flowchart generation
│   ├── healthcare/                       # Healthcare-specific skills
│   │   ├── claim_scrubber.py             # Pre-submission claim validation
│   │   ├── denial_analyzer.py            # Root cause + appeal recommendation
│   │   ├── denial_predictor.py           # Predict denial probability pre-submit
│   │   ├── appeals_writer.py             # Generate appeals with regulatory citations
│   │   ├── code_lookup.py                # ICD-10, CPT, HCPCS, CDT, NDC lookup
│   │   ├── cci_editor.py                 # NCCI edit pair checking
│   │   ├── fee_schedule.py               # Medicare/Medicaid fee schedule lookup
│   │   ├── coverage_checker.py           # LCD/NCD medical necessity criteria
│   │   ├── drug_reference.py             # Drug info, interactions, formulary
│   │   ├── lab_interpreter.py            # Lab value interpretation + trending
│   │   ├── prior_auth.py                 # Auth requirements by payer + procedure
│   │   ├── eligibility_checker.py        # Benefits and eligibility interpretation
│   │   ├── remittance_parser.py          # ERA/EOB (835) parsing + analysis
│   │   ├── claim_status.py               # 276/277 claim status interpretation
│   │   ├── contract_analyzer.py          # Payer contract terms extraction
│   │   ├── risk_adjuster.py              # HCC/RAF score calculation + gaps
│   │   ├── quality_tracker.py            # HEDIS/MIPS/Stars measure tracking
│   │   ├── compliance_checker.py         # HIPAA/OIG/Stark/AKS compliance check
│   │   ├── credentialing_tracker.py      # Provider credentialing status + alerts
│   │   ├── telehealth_rules.py           # Telehealth billing rules by state + payer
│   │   ├── medical_calculator.py         # BMI, eGFR, MELD, APACHE, Wells, etc.
│   │   ├── drg_grouper.py               # DRG assignment logic + weights
│   │   ├── apc_grouper.py               # APC assignment for outpatient
│   │   ├── ndc_pricer.py                 # Drug pricing (ASP, AWP, NADAC, WAC)
│   │   └── edi_parser.py                # Parse/generate X12 EDI (837/835/270/271/276/277/278/834/820)
│   └── user/                             # User-created custom skills
│       └── README.md                     # How to add your own skills
│
├── plugins/                              # External service integrations
│   ├── __init__.py
│   ├── plugin_registry.py                # Plugin discovery, auth, lifecycle
│   ├── plugin_base.py                    # Base class for plugins
│   ├── PLUGIN_SPEC.md                    # How to create new plugins
│   ├── cloudflare/                       # Cloudflare integration
│   │   ├── __init__.py
│   │   ├── dns_manager.py               # DNS record CRUD
│   │   ├── tunnel_manager.py            # Tunnel status, create, delete
│   │   ├── pages_manager.py             # Pages deployment status
│   │   ├── workers_manager.py           # Workers management
│   │   ├── analytics.py                 # Site analytics pull
│   │   ├── security.py                  # WAF rules, DDoS status, SSL certs
│   │   ├── access_manager.py            # Zero Trust access policies
│   │   └── r2_storage.py               # R2 object storage operations
│   ├── github/                           # GitHub integration
│   │   ├── __init__.py
│   │   ├── repos.py                     # Repo management, code search
│   │   ├── issues.py                    # Issue/PR management
│   │   ├── actions.py                   # CI/CD status, trigger workflows
│   │   └── code_review.py              # Automated code review
│   ├── email/                            # Email integration (IMAP/SMTP)
│   │   ├── __init__.py
│   │   ├── reader.py                    # Read/search/categorize emails
│   │   ├── composer.py                  # Draft/send with approval
│   │   ├── auto_processor.py            # Auto-categorize + extract actions
│   │   └── templates.py                 # Email template management
│   ├── calendar/                         # Calendar integration
│   │   ├── __init__.py
│   │   ├── caldav_client.py             # CalDAV (works with Google, Outlook, etc.)
│   │   └── scheduler.py                # Find free time, schedule meetings
│   ├── database/                         # Database connectors
│   │   ├── __init__.py
│   │   ├── sqlite_connector.py
│   │   ├── postgres_connector.py
│   │   └── csv_connector.py
│   ├── notifications/                    # Push notification channels
│   │   ├── __init__.py
│   │   ├── telegram_bot.py              # Telegram notifications (free)
│   │   ├── webhook.py                   # Generic webhook
│   │   └── browser_push.py             # Web push notifications via PWA
│   └── user/                             # User-created plugins
│       └── README.md
│
├── connectors/                           # MCP-like connector system
│   ├── __init__.py
│   ├── connector_registry.py             # Discover, connect, manage connectors
│   ├── connector_base.py                 # Base class with auth + reconnect
│   ├── CONNECTOR_SPEC.md                 # How to create new connectors
│   ├── mcp_bridge.py                     # Bridge to real MCP protocol servers
│   ├── openapi_bridge.py                # Auto-generate connector from OpenAPI spec
│   ├── builtin/
│   │   ├── cms_npi.py                   # CMS NPI Registry connector
│   │   ├── cms_coverage.py              # CMS Coverage Database connector
│   │   ├── openfda.py                   # OpenFDA connector (drugs, recalls, adverse events)
│   │   ├── pubmed.py                    # PubMed/NCBI literature search
│   │   ├── rxnorm.py                    # RxNorm drug normalization
│   │   ├── snomed.py                    # SNOMED CT terminology
│   │   ├── loinc.py                     # LOINC lab code lookup
│   │   ├── umls.py                      # UMLS Metathesaurus (free with license)
│   │   ├── fhir_client.py              # Generic FHIR R4 client
│   │   ├── cms_data.py                  # CMS public datasets (Provider of Services, cost reports, etc.)
│   │   ├── federal_register.py          # Federal Register API (CMS/HHS rules)
│   │   ├── hcpcs_api.py                # HCPCS code lookup
│   │   ├── nucc_taxonomy.py            # Provider taxonomy codes
│   │   ├── cloudflare_api.py            # Cloudflare REST API v4
│   │   ├── github_api.py               # GitHub REST API
│   │   ├── searxng.py                   # SearXNG search connector
│   │   ├── wikipedia.py                 # Wikipedia API
│   │   ├── arxiv.py                     # ArXiv paper search
│   │   └── weather.py                   # OpenMeteo weather (free, no key)
│   └── user/                             # User-added connectors
│       └── README.md
│
├── tools/                                # Low-level tool implementations
│   ├── __init__.py
│   ├── web_search.py                     # SearXNG integration
│   ├── web_fetch.py                      # URL scraping with readability extraction
│   ├── code_executor.py                  # Docker-sandboxed Python/Node/Bash
│   ├── file_handler.py                   # Read/write/convert any file format
│   ├── calculator.py                     # Math, finance, statistics, clinical
│   ├── image_processor.py                # OCR, resize, analyze (Gemma2 vision or Ollama)
│   └── shell.py                          # Controlled shell command execution
│
├── memory/                               # Persistent memory system
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── __init__.py
│   ├── vector_store.py                   # ChromaDB operations
│   ├── user_profile.py                   # Structured user profile (encrypted)
│   ├── conversation_store.py             # Full conversation history (SQLite)
│   ├── knowledge_graph.py                # Entity-relationship graph
│   ├── health_records.py                 # PHI store (SQLCipher encrypted)
│   ├── fact_store.py                     # Verified facts with source + confidence
│   ├── contradiction_detector.py         # Detect conflicting stored facts
│   ├── learning.py                       # Adaptive preference learning
│   └── knowledge_gaps.py                 # Track + auto-fill knowledge gaps
│
├── knowledge_bases/                      # RAG knowledge (downloaded on setup)
│   ├── download_all.py                   # Master download script
│   ├── index_all.py                      # Index everything into ChromaDB
│   ├── update_all.py                     # Scheduled update script
│   ├── healthcare/
│   │   ├── coding/
│   │   │   ├── icd10cm_codes.py         # Download ICD-10-CM from CMS
│   │   │   ├── icd10pcs_codes.py        # Download ICD-10-PCS from CMS
│   │   │   ├── cpt_descriptions.py      # CPT category descriptions (public portions)
│   │   │   ├── hcpcs_codes.py           # HCPCS Level II from CMS
│   │   │   ├── cdt_codes.py             # CDT dental codes (public descriptions)
│   │   │   ├── ndc_codes.py             # NDC drug codes from FDA
│   │   │   ├── revenue_codes.py         # Revenue code descriptions
│   │   │   ├── place_of_service.py      # POS code list
│   │   │   ├── modifier_list.py         # CPT/HCPCS modifier descriptions
│   │   │   ├── taxonomy_codes.py        # NUCC provider taxonomy
│   │   │   └── drg_weights.py           # MS-DRG weights + descriptions from CMS
│   │   ├── claims/
│   │   │   ├── carc_rarc_codes.py       # CARC/RARC reason codes from X12
│   │   │   ├── claim_status_codes.py    # Claim status category codes
│   │   │   ├── cci_edits.py             # NCCI edit pairs (quarterly from CMS)
│   │   │   ├── mue_values.py            # Medically Unlikely Edits from CMS
│   │   │   ├── ocm_edits.py            # Outpatient Code Editor
│   │   │   └── edi_specs.py            # X12 EDI transaction specifications
│   │   ├── reimbursement/
│   │   │   ├── mpfs.py                  # Medicare Physician Fee Schedule (RVUs)
│   │   │   ├── opps.py                  # Outpatient Prospective Payment System
│   │   │   ├── ipps.py                  # Inpatient Prospective Payment System
│   │   │   ├── asc_fee_schedule.py      # Ambulatory Surgery Center fees
│   │   │   ├── dme_fee_schedule.py      # DME fee schedule
│   │   │   ├── clinical_lab_fee.py      # Clinical Lab Fee Schedule
│   │   │   ├── snf_pps.py              # Skilled Nursing Facility PPS
│   │   │   ├── hh_pps.py               # Home Health PPS (PDGM)
│   │   │   ├── irf_pps.py              # Inpatient Rehab Facility PPS
│   │   │   ├── ltch_pps.py             # Long-Term Care Hospital PPS
│   │   │   ├── hospice_rates.py         # Hospice payment rates
│   │   │   ├── esrd_pps.py             # ESRD (dialysis) PPS
│   │   │   └── drug_pricing.py         # ASP, AWP, NADAC, AMP drug pricing
│   │   ├── regulatory/
│   │   │   ├── cms_manuals.py           # Medicare Benefit Policy Manual chapters
│   │   │   ├── claims_processing_manual.py  # CMS Claims Processing Manual
│   │   │   ├── program_integrity_manual.py  # Program Integrity Manual
│   │   │   ├── mln_articles.py         # MLN Matters articles
│   │   │   ├── cms_transmittals.py     # CMS Transmittals (Change Requests)
│   │   │   ├── hipaa_rules.py          # HIPAA Privacy + Security Rule text
│   │   │   ├── no_surprises_act.py     # No Surprises Act final rules
│   │   │   ├── price_transparency.py    # Hospital/Insurer price transparency rules
│   │   │   ├── oig_work_plan.py        # OIG Work Plan items
│   │   │   ├── stark_law.py            # Stark Law (physician self-referral)
│   │   │   ├── anti_kickback.py        # Anti-Kickback Statute
│   │   │   ├── false_claims_act.py     # False Claims Act
│   │   │   ├── emtala.py               # EMTALA (emergency treatment)
│   │   │   ├── mental_health_parity.py # MHPAEA mental health parity
│   │   │   ├── telehealth_rules.py     # Telehealth regulations by state
│   │   │   ├── state_medicaid.py       # State Medicaid rules (top 10 states)
│   │   │   └── cms_final_rules.py      # Recent CMS Final Rules
│   │   ├── quality/
│   │   │   ├── hedis_measures.py       # HEDIS measure specs
│   │   │   ├── mips_measures.py        # MIPS quality measures
│   │   │   ├── star_ratings.py         # MA Star Ratings methodology
│   │   │   ├── cahps.py               # CAHPS survey measures
│   │   │   ├── core_measures.py        # CMS Core Measures
│   │   │   └── value_based_programs.py # VBP, BPCI, ACO models
│   │   ├── clinical/
│   │   │   ├── drug_database.py        # OpenFDA drug data
│   │   │   ├── lab_reference.py        # Lab normal ranges
│   │   │   ├── screening_guidelines.py # USPSTF preventive care guidelines
│   │   │   ├── clinical_guidelines.py  # Major clinical practice guidelines
│   │   │   └── medical_calculators.py  # Clinical calculation formulas
│   │   └── payer_specific/
│   │       ├── medicare_parts.py       # Medicare Parts A/B/C/D rules
│   │       ├── medicaid_rules.py       # Medicaid general rules
│   │       ├── tricare.py              # TRICARE military insurance
│   │       ├── va_community_care.py    # VA Community Care rules
│   │       ├── workers_comp.py         # Workers' comp billing by state
│   │       ├── auto_nofault.py         # Auto/no-fault insurance rules
│   │       └── commercial_basics.py    # Commercial insurance fundamentals
│   ├── finance/
│   │   ├── tax_reference.py
│   │   ├── accounting_standards.py
│   │   └── financial_formulas.py
│   ├── legal/
│   │   ├── contract_templates.py
│   │   ├── license_types.py
│   │   └── privacy_frameworks.py
│   └── technology/
│       ├── cloudflare_docs.py
│       ├── security_best_practices.py
│       └── web_standards.py
│
├── proactive/                            # Proactive intelligence engine
│   ├── __init__.py
│   ├── scheduler.py                      # Cron-like job runner (APScheduler)
│   ├── morning_briefing.py               # Daily morning briefing
│   ├── alerts.py                         # Threshold-based alerts + push
│   ├── action_queue.py                   # Prioritized task queue with escalation
│   ├── weekly_reports.py                 # Automated weekly summaries
│   ├── knowledge_updater.py              # Auto-fetch CMS updates, CVEs, news
│   ├── news_aggregator.py               # RSS feed monitoring + summarization
│   ├── automations.py                    # Natural language automation builder
│   └── feeds.yaml                        # RSS/Atom feed URLs to monitor
│
├── ui/                                   # React PWA frontend
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── public/
│   │   ├── index.html
│   │   ├── manifest.json                 # PWA manifest
│   │   ├── sw.js                         # Service worker for offline
│   │   └── icons/                        # PWA icons (generate via script)
│   │       ├── icon-72.png
│   │       ├── icon-96.png
│   │       ├── icon-128.png
│   │       ├── icon-144.png
│   │       ├── icon-152.png
│   │       ├── icon-192.png
│   │       ├── icon-384.png
│   │       └── icon-512.png
│   └── src/
│       ├── App.jsx                       # Main app shell
│       ├── main.jsx                      # Entry point
│       ├── styles/
│       │   └── globals.css               # Global styles + CSS variables
│       ├── components/
│       │   ├── chat/
│       │   │   ├── ChatInterface.jsx     # Main chat with streaming
│       │   │   ├── MessageBubble.jsx     # Message with specialist badge + confidence
│       │   │   ├── ReasoningChain.jsx    # Expandable reasoning panel
│       │   │   ├── ToolCallDisplay.jsx   # Show tool usage in real-time
│       │   │   ├── FileUploadZone.jsx    # Drag-drop file processing
│       │   │   ├── VoiceButton.jsx       # Push-to-talk voice input
│       │   │   └── InputBar.jsx          # Chat input with slash commands
│       │   ├── specialists/
│       │   │   ├── SpecialistBadge.jsx   # Color-coded active specialist indicator
│       │   │   ├── SpecialistSwitcher.jsx # Quick switch panel
│       │   │   └── MultiAgentView.jsx    # Show multi-agent debate results
│       │   ├── healthcare/
│       │   │   ├── CodeLookup.jsx        # Quick ICD-10/CPT/HCPCS search widget
│       │   │   ├── ClaimAnalyzer.jsx     # Upload claim/EOB for analysis
│       │   │   ├── AppealsWorkflow.jsx   # Guided appeals letter builder
│       │   │   ├── DenialDashboard.jsx   # Denial trends + analytics
│       │   │   ├── FeeSchedule.jsx       # Fee schedule comparison tool
│       │   │   ├── DrugLookup.jsx        # Drug info + interactions
│       │   │   ├── CoverageChecker.jsx   # LCD/NCD criteria lookup
│       │   │   └── EDIViewer.jsx         # EDI transaction viewer/parser
│       │   ├── dashboards/
│       │   │   ├── HealthcareDashboard.jsx # Claims, denials, revenue metrics
│       │   │   ├── FinanceDashboard.jsx  # Income, expenses, projections
│       │   │   ├── SystemDashboard.jsx   # AI usage, model stats, container health
│       │   │   ├── AlertsFeed.jsx        # Proactive alerts timeline
│       │   │   └── ActionQueue.jsx       # Prioritized task list
│       │   ├── skills/
│       │   │   ├── SkillBrowser.jsx      # Browse/search available skills
│       │   │   ├── PluginManager.jsx     # Enable/disable/configure plugins
│       │   │   ├── ConnectorPanel.jsx    # Connect/disconnect external services
│       │   │   └── AutomationBuilder.jsx # Visual automation builder
│       │   ├── common/
│       │   │   ├── Sidebar.jsx           # Navigation + mode switcher
│       │   │   ├── CommandPalette.jsx    # Ctrl+K command palette
│       │   │   ├── SearchBar.jsx         # Global search across all data
│       │   │   ├── ConfidenceBadge.jsx   # Green/yellow/red confidence indicator
│       │   │   ├── ThemeToggle.jsx       # Light/dark mode
│       │   │   └── LoadingStates.jsx     # Skeleton loaders, streaming indicators
│       │   └── settings/
│       │       ├── SettingsPanel.jsx     # All settings
│       │       ├── ModelConfig.jsx       # Model preferences + cascade config
│       │       ├── ProfileEditor.jsx     # Edit user profile + preferences
│       │       ├── PrivacySettings.jsx   # PHI routing, encryption settings
│       │       └── NotificationSettings.jsx # Alert preferences
│       ├── hooks/
│       │   ├── useChat.js                # Chat state + streaming
│       │   ├── useVoice.js               # Voice recording + STT
│       │   ├── useWebSocket.js           # WebSocket connection
│       │   ├── useKeyboard.js            # Keyboard shortcuts
│       │   ├── useOffline.js             # Offline detection + queue
│       │   └── useTheme.js               # Theme management
│       └── utils/
│           ├── api.js                    # API client
│           ├── markdown.js               # Markdown rendering with code highlight
│           ├── storage.js                # IndexedDB for offline cache
│           └── constants.js              # App constants
│
├── voice/                                # Voice subsystem
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── stt.py                            # Speech-to-text (Whisper local or HF API)
│   ├── tts.py                            # Text-to-speech (Piper, runs on CPU)
│   ├── voice_session.py                  # WebSocket voice conversation
│   └── wake_word.py                      # Optional wake word detection
│
├── clipboard/                            # Clipboard intelligence agent
│   ├── requirements.txt
│   ├── clipboard_agent.py                # System tray + clipboard monitoring
│   ├── patterns.py                       # Detection patterns (ICD-10, CPT, NPI, etc.)
│   └── install.ps1                       # Install as startup app
│
├── infrastructure/
│   ├── cloudflare/
│   │   ├── tunnel_setup.ps1              # Cloudflare Tunnel setup
│   │   ├── access_setup.ps1              # Cloudflare Access (zero-trust)
│   │   ├── tunnel.yml                    # Tunnel config
│   │   └── access_policy.json            # Access policy (email OTP)
│   ├── monitoring/
│   │   ├── health_check.py               # Container health monitoring
│   │   ├── usage_tracker.py              # Token usage + cost tracking
│   │   └── uptime_checker.py            # External uptime monitoring
│   ├── backup/
│   │   ├── backup_local.ps1              # Local backup to external drive
│   │   ├── backup_r2.py                  # Backup to Cloudflare R2 (your account)
│   │   └── restore.ps1                   # Restore from backup
│   └── security/
│       ├── encryption.py                 # SQLCipher + file encryption utilities
│       ├── audit_logger.py               # HIPAA-grade immutable audit trail
│       └── phi_detector.py              # PHI/PII regex + ML detection
│
└── tests/
    ├── test_router.py
    ├── test_cascade.py
    ├── test_sensitivity.py
    ├── test_healthcare_tools.py
    ├── test_skills.py
    ├── test_plugins.py
    ├── test_connectors.py
    ├── test_memory.py
    └── test_edi_parser.py
```

---

## SECTION 3: DOCKER COMPOSE

### docker-compose.yml
```yaml
# Design for 16GB RAM system with NVIDIA MX450 (2GB VRAM)
# Total RAM budget: ~12GB for containers (leave 4GB for Windows + WSL2)

services:
  orchestrator:
    build: ./orchestrator
    ports: ["8000:8000"]
    environment:
      - LITELLM_URL=http://litellm:4000
      - CHROMADB_URL=http://chromadb:8000
      - SEARXNG_URL=http://searxng:8080
      - OLLAMA_URL=http://ollama:11434
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./specialists:/app/specialists
      - ./skills:/app/skills
      - ./plugins:/app/plugins
      - ./connectors:/app/connectors
      - ./tools:/app/tools
      - ./memory:/app/memory
      - ./knowledge_bases:/app/knowledge_bases
      - ./proactive:/app/proactive
      - aethera-data:/data
    depends_on: [litellm, chromadb, searxng, redis, ollama]
    restart: always
    deploy:
      resources:
        limits: { memory: 2G }

  litellm:
    image: ghcr.io/berriai/litellm:main-latest
    ports: ["4000:4000"]
    volumes:
      - ./litellm_config.yaml:/app/config.yaml
    command: ["--config", "/app/config.yaml"]
    restart: always
    deploy:
      resources:
        limits: { memory: 512M }

  ollama:
    image: ollama/ollama:latest
    ports: ["11434:11434"]
    volumes:
      - ollama-models:/root/.ollama
    restart: always
    deploy:
      resources:
        limits: { memory: 8G }
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  chromadb:
    image: chromadb/chroma:latest
    ports: ["8001:8000"]
    volumes:
      - chroma-data:/chroma/chroma
    restart: always
    deploy:
      resources:
        limits: { memory: 1G }

  searxng:
    image: searxng/searxng:latest
    ports: ["8888:8080"]
    volumes:
      - ./searxng-settings.yml:/etc/searxng/settings.yml
    restart: always
    deploy:
      resources:
        limits: { memory: 512M }

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes:
      - redis-data:/data
    restart: always
    deploy:
      resources:
        limits: { memory: 256M }

  ui:
    build: ./ui
    ports: ["3000:3000"]
    depends_on: [orchestrator]
    restart: always
    deploy:
      resources:
        limits: { memory: 256M }

  voice:
    build: ./voice
    ports: ["8500:8500"]
    volumes:
      - voice-models:/models
    depends_on: [orchestrator]
    restart: always
    deploy:
      resources:
        limits: { memory: 1G }

volumes:
  aethera-data:
  ollama-models:
  chroma-data:
  redis-data:
  voice-models:
```

### litellm_config.yaml
```yaml
model_list:
  # ============================================================
  # LOCAL MODELS — run on your laptop, unlimited, private
  # ============================================================
  
  # GPU-accelerated on NVIDIA MX450 (2GB VRAM) — fast, for simple queries + PHI
  - model_name: "aethera-local-fast"
    litellm_params:
      model: "ollama/qwen3.5:4b"
      api_base: "http://ollama:11434"
      stream: true
    model_info:
      description: "Fast local model on MX450 GPU — primary for PHI and simple queries"
      mode: "chat"

  # GPU-accelerated — good for tool calling and structured output
  - model_name: "aethera-local-tools"
    litellm_params:
      model: "ollama/gemma4:e2b"
      api_base: "http://ollama:11434"
      stream: true
    model_info:
      description: "Local tool-calling model on MX450 GPU"
      mode: "chat"

  # CPU-only — smart fallback when cloud is exhausted
  - model_name: "aethera-local-smart"
    litellm_params:
      model: "ollama/qwen3.5:9b"
      api_base: "http://ollama:11434"
      stream: true
    model_info:
      description: "Smart local model on CPU — fallback when cloud quota exhausted"
      mode: "chat"

  # Embeddings — for ChromaDB RAG indexing and search
  - model_name: "aethera-embed"
    litellm_params:
      model: "ollama/nomic-embed-text"
      api_base: "http://ollama:11434"
    model_info:
      description: "Local embedding model for RAG"
      mode: "embedding"

  # ============================================================
  # OLLAMA CLOUD MODELS — your Ollama account (Pro plan $20/mo)
  # These run on Ollama's cloud GPUs, zero local resource usage
  # API key from: ollama.com → Settings → API Keys
  # ============================================================
  
  # Primary brain — frontier intelligence for complex queries
  - model_name: "aethera-cloud-brain"
    litellm_params:
      model: "ollama/qwen3.5:122b"
      api_base: "https://ollama.com"
      api_key: "os.environ/OLLAMA_API_KEY"
      stream: true
    model_info:
      description: "Frontier 122B model — best for complex healthcare, reasoning, analysis"
      mode: "chat"

  # Deep reasoning — 1M token context window, chain-of-thought
  - model_name: "aethera-cloud-reason"
    litellm_params:
      model: "ollama/deepseek-v4-flash"
      api_base: "https://ollama.com"
      api_key: "os.environ/OLLAMA_API_KEY"
      stream: true
    model_info:
      description: "284B MoE reasoning model — best for deep analysis, long documents"
      mode: "chat"

  # Best coder — multimodal agentic, long-horizon coding
  - model_name: "aethera-cloud-coder"
    litellm_params:
      model: "ollama/kimi-k2.6"
      api_base: "https://ollama.com"
      api_key: "os.environ/OLLAMA_API_KEY"
      stream: true
    model_info:
      description: "Best coding model — agentic, multimodal, MIT licensed"
      mode: "chat"

  # Tool calling + vision — excellent for structured extraction
  - model_name: "aethera-cloud-tools"
    litellm_params:
      model: "ollama/gemma4:26b"
      api_base: "https://ollama.com"
      api_key: "os.environ/OLLAMA_API_KEY"
      stream: true
    model_info:
      description: "Tool calling + vision model — best for document analysis, structured output"
      mode: "chat"

  # Efficient multi-agent — 120B MoE with only 12B active params
  - model_name: "aethera-cloud-agent"
    litellm_params:
      model: "ollama/nemotron-3-super"
      api_base: "https://ollama.com"
      api_key: "os.environ/OLLAMA_API_KEY"
      stream: true
    model_info:
      description: "Efficient MoE model — best for multi-agent parallel reasoning"
      mode: "chat"

  # Medium-weight cloud — balanced speed/intelligence
  - model_name: "aethera-cloud-balanced"
    litellm_params:
      model: "ollama/qwen3.5:35b"
      api_base: "https://ollama.com"
      api_key: "os.environ/OLLAMA_API_KEY"
      stream: true
    model_info:
      description: "Balanced cloud model — good mix of speed and intelligence"
      mode: "chat"

  # Strong engineering/coding — agentic engineering focus
  - model_name: "aethera-cloud-engineer"
    litellm_params:
      model: "ollama/glm-5.1"
      api_base: "https://ollama.com"
      api_key: "os.environ/OLLAMA_API_KEY"
      stream: true
    model_info:
      description: "Agentic engineering model — strong coding and systems design"
      mode: "chat"

  # ============================================================
  # HUGGINGFACE FREE INFERENCE — overflow when Ollama Cloud quota hit
  # Optional: set HF_TOKEN for higher rate limits (free account)
  # ============================================================
  
  - model_name: "hf-qwen-72b"
    litellm_params:
      model: "huggingface/Qwen/Qwen2.5-72B-Instruct"
      api_key: "os.environ/HF_TOKEN"
    model_info:
      description: "HuggingFace free Qwen 72B — overflow capacity"
      mode: "chat"

  - model_name: "hf-mistral"
    litellm_params:
      model: "huggingface/mistralai/Mistral-7B-Instruct-v0.3"
      api_key: "os.environ/HF_TOKEN"
    model_info:
      description: "HuggingFace free Mistral 7B — fast overflow"
      mode: "chat"

  # ============================================================
  # USER-CONFIGURABLE — add any OpenAI-compatible endpoint
  # Set CUSTOM_API_BASE, CUSTOM_MODEL_NAME, CUSTOM_API_KEY in .env
  # ============================================================
  
  - model_name: "custom-endpoint"
    litellm_params:
      model: "openai/os.environ/CUSTOM_MODEL_NAME"
      api_base: "os.environ/CUSTOM_API_BASE"
      api_key: "os.environ/CUSTOM_API_KEY"
    model_info:
      description: "User-configured custom endpoint"
      mode: "chat"

router_settings:
  routing_strategy: "usage-based-routing-v2"
  enable_pre_call_checks: true
  redis_host: "redis"
  redis_port: 6379
  # Fallback order when primary model fails:
  fallbacks:
    - "aethera-cloud-brain": ["aethera-cloud-balanced", "aethera-cloud-reason", "hf-qwen-72b", "aethera-local-smart"]
    - "aethera-cloud-coder": ["aethera-cloud-engineer", "hf-qwen-72b", "aethera-local-smart"]
    - "aethera-cloud-tools": ["aethera-cloud-balanced", "aethera-local-tools", "aethera-local-smart"]
    - "aethera-cloud-reason": ["aethera-cloud-brain", "hf-qwen-72b", "aethera-local-smart"]
```

---

## SECTION 4: SKILLS / PLUGINS / CONNECTORS SYSTEM

This is the core architecture that makes Aethera extensible like Claude.

### skills/skill_base.py
```python
from abc import ABC, abstractmethod
from typing import Any

class AetheraSkill(ABC):
    """
    Base class for all Aethera skills.
    Skills are self-contained capabilities that process input and produce output.
    They are the equivalent of Claude's built-in tools.
    
    Skills are:
    - Stateless (no persistent state between calls)
    - Self-describing (name, description, parameters, examples)
    - Composable (skills can call other skills)
    - Discoverable (auto-registered via decorator)
    
    To create a skill:
    1. Create a new .py file in skills/builtin/ or skills/healthcare/ or skills/user/
    2. Subclass AetheraSkill
    3. Implement name, description, parameters, execute()
    4. The skill auto-registers on startup
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique skill identifier, e.g. 'icd10_lookup'"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this skill does.
        Used by the router to decide when to invoke this skill."""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> dict:
        """JSON Schema describing the skill's input parameters."""
        pass
    
    @property
    def examples(self) -> list[dict]:
        """Example invocations for few-shot prompting."""
        return []
    
    @property
    def category(self) -> str:
        """Skill category for UI grouping."""
        return "general"
    
    @property
    def requires_phi_protection(self) -> bool:
        """If True, inputs/outputs are encrypted and routed to local models."""
        return False
    
    @abstractmethod
    async def execute(self, **kwargs) -> dict:
        """Execute the skill and return structured result."""
        pass
    
    def to_tool_definition(self) -> dict:
        """Convert to OpenAI function-calling format for LLM tool use."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
```

### skills/skill_registry.py
```python
class SkillRegistry:
    """
    Discovers, loads, and manages all skills.
    
    Startup:
    1. Scan skills/builtin/, skills/healthcare/, skills/user/
    2. Import all modules, find AetheraSkill subclasses
    3. Register each with name, description, parameters
    4. Generate tool definitions for LLM function calling
    
    Runtime:
    - Router queries registry: "which skills match this user intent?"
    - Registry returns ranked list of relevant skills
    - LLM receives tool definitions for selected skills
    - LLM calls tools → Registry routes to skill.execute()
    - Results returned to LLM for response generation
    
    Slash commands in chat:
    /skills              — list all available skills
    /skills healthcare   — list healthcare skills
    /skill info <name>   — show skill details
    /skill run <name>    — force-run a specific skill
    """
```

### plugins/plugin_base.py
```python
class AetheraPlugin(ABC):
    """
    Base class for external service integrations.
    Plugins differ from skills:
    - Plugins maintain state (auth tokens, connections)
    - Plugins interact with external services
    - Plugins have lifecycle (connect, disconnect, reconnect)
    - Plugins may require configuration (API keys, URLs)
    
    Slash commands:
    /plugins              — list all plugins + status
    /plugin enable <name> — enable a plugin
    /plugin disable <name>— disable a plugin
    /plugin config <name> — configure a plugin
    """
    
    @property
    @abstractmethod
    def name(self) -> str: pass
    
    @property
    @abstractmethod
    def description(self) -> str: pass
    
    @property
    def requires_auth(self) -> bool:
        return False
    
    @property
    def config_schema(self) -> dict:
        """JSON Schema for plugin configuration."""
        return {}
    
    @abstractmethod
    async def connect(self, config: dict) -> bool: pass
    
    @abstractmethod
    async def disconnect(self) -> bool: pass
    
    @abstractmethod
    async def health_check(self) -> bool: pass
    
    @abstractmethod
    def get_tools(self) -> list[dict]:
        """Return tool definitions this plugin provides."""
        pass
```

### connectors/connector_base.py
```python
class AetheraConnector(ABC):
    """
    Base class for data source connectors.
    Connectors are read/write interfaces to external data.
    
    Connectors differ from plugins:
    - Connectors are specifically for data access
    - Connectors implement a standard CRUD interface
    - Connectors can be used by any specialist
    
    Built-in connectors for healthcare:
    - CMS NPI Registry (REST API, no auth)
    - CMS Coverage Database (REST API, no auth)
    - OpenFDA (REST API, no auth)
    - PubMed/NCBI (REST API, free with optional key)
    - RxNorm (REST API, no auth)
    - FHIR R4 (configurable endpoint)
    - Federal Register (REST API, no auth)
    
    Built-in connectors for infrastructure:
    - Cloudflare API v4 (your API token)
    - GitHub API (your PAT)
    - SearXNG (local instance)
    
    Slash commands:
    /connectors           — list all connectors + status
    /connect <name>       — connect to a data source
    /disconnect <name>    — disconnect
    """
    
    @abstractmethod
    async def search(self, query: str, **filters) -> list[dict]: pass
    
    @abstractmethod
    async def get(self, id: str) -> dict: pass
    
    async def create(self, data: dict) -> dict:
        raise NotImplementedError("This connector is read-only")
    
    async def update(self, id: str, data: dict) -> dict:
        raise NotImplementedError("This connector is read-only")
    
    async def delete(self, id: str) -> bool:
        raise NotImplementedError("This connector is read-only")
```

---

## SECTION 5: SPECIALIST SYSTEM PROMPTS

### specialists/healthcare_provider.py — COMPLETE SYSTEM PROMPT
```python
SYSTEM_PROMPT = """
You are Aethera's Healthcare Provider Operations specialist. You are a senior
US healthcare revenue cycle management expert with encyclopedic knowledge across
all provider settings: acute care hospitals, physician practices, ASCs, SNFs,
home health, hospice, rehab facilities, LTCHs, dialysis centers, FQHCs, RHCs,
behavioral health, dental, and vision practices.

## COMPLETE KNOWLEDGE DOMAINS

### Medical Coding (ICD-10-CM/PCS, CPT/HCPCS, CDT)
- ICD-10-CM: All chapters A00-Z99, Official Coding Guidelines (OGCR) Sections I-IV
- ICD-10-PCS: Root operations, body part values, approaches, devices, qualifiers
- CPT Category I (00100-99499): Surgery, radiology, pathology, medicine, E/M
- CPT Category II (performance measures) and Category III (emerging technology)
- HCPCS Level II (A0000-V5999): DME, drugs, supplies, ambulance, dental
- CDT codes (D0100-D9999): Dental diagnostic, preventive, restorative, endo, perio, prosth
- Modifiers: All CPT (22,24,25,26,27,50,51,52,53,54,55,56,57,58,59,62,66,73,74,76,77,78,79,80,81,82,91,95,96,97,TC,XE,XS,XP,XU) and HCPCS (GA,GY,GZ,KX,LT,RT,etc.)
- E/M coding: 2021+ MDM-based guidelines, time-based rules, split/shared visits, critical care, prolonged services
- Global surgical package: 0-day, 10-day, 90-day global periods, modifier usage
- Revenue codes (0001-0999): room/board, pharmacy, lab, imaging, therapy, OR, ER, clinic

### Charge Capture & CDM
- Charge Description Master (CDM) structure and maintenance
- Charge capture workflows by department
- Late charge identification
- Hard-coded vs soft-coded charges
- Exploding charges for supplies, drugs
- Price transparency requirements (machine-readable files, shoppable services)

### Claims Submission
- 837P (Professional) claim format — all loops and segments
- 837I (Institutional) claim format — all loops and segments
- 837D (Dental) claim format
- UB-04 (CMS-1450) field-by-field guide
- CMS-1500 field-by-field guide
- ADA Dental Claim Form
- Timely filing limits by payer (Medicare: 12 months, Medicaid: varies, Commercial: 90-365 days)
- Electronic vs paper submission rules
- Coordination of Benefits (COB) billing order
- Medicare Secondary Payer (MSP) rules — Group Health Plan, liability, workers comp, auto

### Denial Management
- CARC (Claim Adjustment Reason Codes) — all categories (CO, OA, PI, PR)
- RARC (Remittance Advice Remark Codes) — all codes
- Denial categorization: clinical, technical, administrative, authorization
- Root cause analysis methodology
- Prevention strategies by denial type
- Appeal levels: internal 1st/2nd, external IRO, ALJ, Medicare Appeals Council, Federal Court
- Appeal timelines: Medicare (120 days redetermination, 180 days QIC, 60 days ALJ)
- Corrected claim vs appeal decision tree
- Reconsideration vs reopening

### Prior Authorization
- Requirements by payer and service category
- Gold carding / prior auth reform rules
- Interoperability rules (CMS-0057-F — Prior Auth API)
- Peer-to-peer review preparation
- Expedited vs standard timelines
- Retro-auth rules

### Reimbursement Methodologies
- RBRVS / MPFS: Work RVU, Practice Expense RVU, Malpractice RVU, GPCI, Conversion Factor
- MS-DRG: Relative weight, base rate, wage index, DSH, IME, outlier
- APR-DRG: Severity of illness, risk of mortality
- APC: Payment rate, status indicators (S, T, V, Q1-Q4, N, X, etc.)
- ASC fee schedule: Payment groups, device-intensive procedures
- Clinical Lab Fee Schedule (CLFS): PAMA pricing reform
- DME fee schedule: Competitive bidding, rental vs purchase
- SNF PPS (PDPM): PT, OT, SLP, nursing, NTA components
- Home Health PPS (PDGM): LUPA, outlier, 30-day periods
- IRF PPS: CMG classification, FIM scores
- LTCH PPS: MS-LTC-DRG, site-neutral payments, 25% rule
- Hospice: Routine Home Care, Continuous Home Care, Inpatient Respite, General Inpatient
- ESRD PPS: Composite rate, add-on payments, outlier
- FQHC PPS: Prospective Payment System, wrap-around payments
- RHC: AIR methodology, productivity standards

### Clinical Documentation Improvement (CDI)
- Query types: compliant physician queries (non-leading)
- CC/MCC capture optimization
- SOI/ROM impact on DRG
- PSI/HAC documentation requirements
- Present on Admission (POA) indicator rules
- Risk adjustment documentation (HCC/RAF)
- Quality measure documentation requirements

### HCC Risk Adjustment
- CMS-HCC model versions (V24, V28)
- RAF score components and calculation
- HCC hierarchies and interactions
- Acceptable documentation for risk adjustment
- RADV audit preparation
- Encounter data validation (EDPS)
- Risk Adjustment Data Validation

### Credentialing
- CAQH ProView maintenance
- NPPES/NPI updates
- State license tracking
- DEA registration
- Board certification
- Hospital privileges
- Payer enrollment (Medicare PECOS, state Medicaid, commercial)
- Revalidation cycles

### Compliance
- OIG compliance program guidance (7 elements)
- Coding audits: prospective, retrospective, focused
- Medical necessity documentation
- Incident-to billing rules
- Teaching physician rules (PATH)
- Locum tenens billing
- Reassignment of benefits
- Place of service rules and consistency

## AVAILABLE TOOLS
You MUST use these tools for accuracy — never guess codes or values:
- code_lookup: Search ICD-10-CM, ICD-10-PCS, CPT, HCPCS, CDT, Revenue codes
- cci_editor: Check NCCI edit pairs and modifier requirements
- fee_schedule: Look up Medicare/Medicaid fee schedule amounts
- coverage_checker: Check LCD/NCD medical necessity criteria
- denial_analyzer: Analyze denial codes and recommend actions
- denial_predictor: Pre-submission claim scrubbing
- appeals_writer: Generate appeals letters with citations
- drg_grouper: Determine DRG assignment and weight
- apc_grouper: Determine APC assignment
- edi_parser: Parse/validate X12 EDI transactions
- npi_lookup: Provider NPI registry search
- credentialing_tracker: Check provider credential status
- prior_auth: Look up prior auth requirements
- medical_calculator: Clinical calculations (BMI, eGFR, etc.)
- drug_reference: Drug information and interactions
- compliance_checker: Check compliance with regulations

## RESPONSE RULES
1. ALWAYS cite specific code numbers with descriptions
2. ALWAYS check CCI edits before suggesting code combinations
3. ALWAYS note documentation requirements for suggested codes
4. ALWAYS distinguish Medicare vs Medicaid vs Commercial rules
5. ALWAYS flag compliance risks (upcoding, unbundling, medical necessity)
6. ALWAYS reference specific CMS manual chapters/sections for regulatory guidance
7. NEVER fabricate code descriptions — use code_lookup tool
8. NEVER guess reimbursement amounts — use fee_schedule tool
9. When in doubt, note that clinical judgment applies
10. For ambiguous coding scenarios, present options with pros/cons
"""
```

### specialists/healthcare_payer.py — COMPLETE SYSTEM PROMPT
```python
SYSTEM_PROMPT = """
You are Aethera's Healthcare Payer Operations specialist. You are a senior
US health insurance operations expert with deep knowledge of claims adjudication,
utilization management, network management, compliance, and analytics across
Medicare Advantage, Medicaid Managed Care, ACA Marketplace, Employer-Sponsored,
and Individual market segments.

## COMPLETE KNOWLEDGE DOMAINS

### Claims Adjudication Engine Logic
- Auto-adjudication flow: eligibility → benefits → authorization → edits → pricing → payment
- Editing hierarchy: pre-payment edits → NCCI → MUE → LCD/NCD → clinical → custom payer
- Pricing methodologies by claim type:
  * Professional: RBRVS-based, percent of Medicare, flat fee, case rate
  * Institutional Inpatient: DRG-based, per diem, percent of charges, case rate
  * Institutional Outpatient: APC-based, percent of Medicare, fee schedule
  * ASC: ASC grouper, Medicare ASC fee schedule percentage
  * SNF/HH/Hospice: Per diem, episodic, prospective
  * Lab: CLFS-based, percent of Medicare
  * DME: Fee schedule, competitive bidding, rental calculations
  * Dental: UCR-based, NDAS-based, fee schedule
  * Pharmacy: AWP-discount, WAC+, ASP+, MAC pricing
- COB determination: Medicare primary/secondary rules, birthday rule, gender rule, NAIC rules
- Subrogation and third-party liability recovery
- Claim recoupment and overpayment recovery
- Cross-plan offsetting
- Interest calculations on clean claims (state-specific prompt pay laws)

### Utilization Management
- Prior authorization: medical necessity criteria, InterQual/MCG equivalent logic
- Concurrent review: continued stay criteria, discharge planning
- Retrospective review: medical necessity after service delivery
- Level of care: inpatient vs observation vs outpatient, 2-midnight rule
- Site of service optimization
- Peer-to-peer review process and requirements
- Appeal levels and timelines:
  * Medicare: Redetermination (60 days), QIC Reconsideration (60 days), ALJ (90 days), MAC Review (90 days), Judicial
  * Commercial: Internal 1st level, Internal 2nd level, External/IRO
  * Medicaid: Fair Hearing
  * Expedited: 72-hour turnaround for urgent cases
- Prior auth reform / gold carding / CMS interoperability rules

### Network Management
- Provider contracting: fee-for-service, value-based, capitation, risk-sharing
- Contract loading and configuration in claims system
- Network adequacy: time/distance standards by CMS and state DOI
- Provider directory accuracy (CMS requirements, No Surprises Act)
- Credentialing: NCQA standards, delegated credentialing
- Single case agreements for out-of-network
- No Surprises Act: QPA calculation, open negotiation, IDR process, patient billing rules
- Balance billing protections by state
- Surprise billing for emergency and non-emergency services

### Member Services
- Eligibility and enrollment: open enrollment, SEPs, qualifying life events
- Benefits interpretation: in-network vs OON, deductible, copay, coinsurance, OOPM
- Accumulator management: deductible accumulators, OOPM tracking
- Grievance processing: expedited vs standard, timeframes
- CTM (Complaint Tracking Module) for Medicare
- Member rights: ACA essential health benefits, preventive care, mental health parity

### Compliance & Regulatory
- Medicare Advantage:
  * Part C regulations (42 CFR Part 422)
  * Part D regulations (42 CFR Part 423)
  * Bid and premium development
  * Star Ratings (Part C + D measures, weights, cut points, improvement bonus)
  * ODAG (Organization Determinations, Appeals, and Grievances)
  * Marketing rules (MCMG)
  * Model of care for SNPs (D-SNP, C-SNP, I-SNP)
  * Network adequacy (HSD table)
  * Provider and Supplier Directory requirements
- Medicaid Managed Care:
  * 42 CFR Part 438
  * State-specific managed care contracts
  * EPSDT requirements for children
  * Retroactive eligibility processing
  * Dual-eligible coordination (D-SNP, FIDE-SNP, HIDE-SNP, Medicare-Medicaid Plans)
- ACA Marketplace:
  * Qualified Health Plans (QHP) certification
  * Essential Health Benefits (EHB)
  * Metal levels (bronze/silver/gold/platinum)
  * Risk adjustment (HHS-HCC model)
  * Risk corridors and reinsurance (historical)
  * EDGE server reporting
  * CSR (Cost-Sharing Reduction) variants
  * Section 1332 waivers
- HIPAA:
  * EDI transaction standards: 837, 835, 270/271, 276/277, 278, 834, 820
  * Code sets: ICD-10, CPT, HCPCS, NDC, CDT
  * Privacy Rule: minimum necessary, TPO, authorization requirements
  * Security Rule: administrative, physical, technical safeguards
  * Breach Notification Rule
  * HITECH Act
- Other:
  * ERISA (self-funded plan rules)
  * COBRA continuation coverage
  * State insurance regulations
  * DOL/DOI jurisdiction rules
  * Anti-Kickback Statute implications for payers
  * False Claims Act exposure

### Analytics & Reporting
- PMPM (Per Member Per Month) trending: medical, pharmacy, admin, total
- MLR (Medical Loss Ratio): numerator/denominator, credibility adjustment, rebate calculation
- HEDIS measures: domains (effectiveness of care, access, experience, utilization)
- Star Ratings: Part C and D measures, display measures, improvement measures
- Risk adjustment:
  * CMS-HCC model for MA (V24, V28 transition)
  * HHS-HCC model for ACA marketplace
  * CDPS model for Medicaid
  * RAF score calculation, normalization, coding intensity adjustment
- Encounter data submission: RAPS vs EDS, chart review
- Utilization metrics: admits/1000, bed days/1000, ER visits/1000
- Cost of care analysis: trend decomposition (utilization, unit cost, mix, severity)
- Network leakage analysis
- Provider profiling and scorecards
- Pharmacy analytics: generic dispensing rate, specialty utilization, rebate analysis

## AVAILABLE TOOLS
Same tools as Provider specialist plus:
- remittance_parser: Parse ERA/835 files
- claim_status: Interpret 276/277 transactions
- eligibility_checker: Benefits and eligibility interpretation
- contract_analyzer: Payer contract terms extraction
- risk_adjuster: HCC/RAF score calculation
- quality_tracker: HEDIS/Stars/MIPS tracking
- ndc_pricer: Drug pricing (ASP, AWP, NADAC)

## RESPONSE RULES
1. Explain adjudication logic step-by-step (like walking through a claims system)
2. Reference specific CFR citations (42 CFR 422.xxx, 42 CFR 438.xxx, etc.)
3. Distinguish Medicare vs Medicaid vs Commercial vs ACA rules clearly
4. When explaining denials, show BOTH payer logic AND provider recourse
5. Note state-specific variations when relevant
6. For regulatory questions, cite specific CMS manual chapters
7. Always note effective dates for rule changes
8. Present both payer and provider perspectives for balanced guidance
"""
```

### specialists/healthcare_regulatory.py — COMPLETE SYSTEM PROMPT
```python
SYSTEM_PROMPT = """
You are Aethera's Healthcare Regulatory & Compliance specialist. Encyclopedic
knowledge of US healthcare law, CMS regulations, HIPAA, fraud and abuse statutes,
state insurance law, and healthcare reform.

## COMPLETE REGULATORY KNOWLEDGE

### Federal Statutes & Regulations
- Social Security Act: Title XVIII (Medicare), Title XIX (Medicaid), Title XXI (CHIP)
- Affordable Care Act (ACA): All titles, key provisions, regulatory implementation
- HIPAA: Privacy Rule (45 CFR 164 Subpart E), Security Rule (45 CFR 164 Subpart C)
- HITECH Act: Breach notification, meaningful use, penalties
- No Surprises Act: Patient billing protections, QPA, IDR, good faith estimates
- Consolidated Appropriations Act 2021: Price transparency, mental health parity
- 21st Century Cures Act: Information blocking, interoperability, TEFCA
- EMTALA: Emergency screening, stabilization, transfer obligations
- Stark Law (42 USC 1395nn): Physician self-referral prohibition, exceptions
- Anti-Kickback Statute (42 USC 1320a-7b): Elements, safe harbors
- False Claims Act (31 USC 3729-3733): Qui tam, treble damages, per-claim penalties
- Civil Monetary Penalties Law
- Exclusion authorities (OIG, GSA)
- Medicare Prescription Drug Improvement and Modernization Act (MMA)
- MACRA/MIPS/APMs: Quality Payment Program
- Mental Health Parity and Addiction Equity Act (MHPAEA)
- Genetic Information Nondiscrimination Act (GINA)
- Women's Health and Cancer Rights Act
- Newborns' and Mothers' Health Protection Act
- COBRA (Consolidated Omnibus Budget Reconciliation Act)
- ERISA (Employee Retirement Income Security Act)

### CMS Regulations (Code of Federal Regulations)
- 42 CFR Part 405: Federal HI for the Aged and Disabled
- 42 CFR Part 410: Supplementary Medical Insurance Benefits
- 42 CFR Part 411: Exclusions from Medicare
- 42 CFR Part 412: Prospective Payment Systems for Inpatient Hospital Services
- 42 CFR Part 413: Principles of Reasonable Cost Reimbursement
- 42 CFR Part 414: Payment for Part B Medical and Other Health Services
- 42 CFR Part 416: Ambulatory Surgical Services
- 42 CFR Part 418: Hospice Care
- 42 CFR Part 422: Medicare Advantage Program
- 42 CFR Part 423: Voluntary Medicare Prescription Drug Benefit
- 42 CFR Part 438: Medicaid Managed Care
- 42 CFR Part 482: Conditions of Participation for Hospitals
- 42 CFR Part 483: Requirements for Long Term Care Facilities
- 42 CFR Part 484: Home Health Services
- 42 CFR Part 485: Conditions of Participation for Specialized Providers
- 45 CFR Parts 160, 162, 164: HIPAA

### CMS Guidance Documents
- Medicare Benefit Policy Manual (CMS Pub. 100-02)
- Medicare Claims Processing Manual (CMS Pub. 100-04)
- Medicare Program Integrity Manual (CMS Pub. 100-08)
- Medicare Managed Care Manual (CMS Pub. 100-16)
- Medicare Prescription Drug Benefit Manual (CMS Pub. 100-18)
- State Operations Manual (CMS Pub. 100-07)
- MLN Matters Articles
- CMS Transmittals / Change Requests
- Medicare Learning Network (MLN) educational materials
- CMS FAQs and informational bulletins

### Fraud & Abuse
- OIG Work Plan: current focus areas
- OIG Advisory Opinions
- Corporate Integrity Agreements (CIA)
- Compliance Program Guidance (7 elements)
- Qui tam / whistleblower provisions
- Yates Memo implications
- Common fraud schemes: phantom billing, upcoding, unbundling, kickbacks, self-referral
- Voluntary self-disclosure protocol (OIG, CMS)
- RAC (Recovery Audit Contractor) audits
- ZPIC/UPIC audits
- MAC audits (prepayment and postpayment)
- SMRC (Supplemental Medical Review Contractor)
- CERT (Comprehensive Error Rate Testing)
- TPE (Targeted Probe and Educate)

### State Regulations
- State insurance department regulations
- State Medicaid rules (varies by state)
- State prompt pay laws
- State surprise billing laws
- State telehealth regulations
- Certificate of Need (CON) laws
- State licensure requirements
- State privacy laws (exceeding HIPAA)
- State mental health parity enforcement

## AVAILABLE TOOLS
- compliance_checker: Check against specific regulations
- coverage_checker: LCD/NCD lookup
- web_researcher: Search CMS.gov, Federal Register, OIG.hhs.gov
- document_creator: Generate compliance reports, audit checklists

## RESPONSE RULES
1. ALWAYS cite specific statute section, CFR citation, or CMS manual chapter
2. Note effective dates — regulations change frequently
3. Distinguish between law (statute), regulation (CFR), and guidance (manual/MLN)
4. Flag when state law may differ from federal requirements
5. For fraud/abuse questions, explain both provider and payer exposure
6. Note enforcement trends from recent OIG/DOJ actions
7. When uncertain about current status of a rule, recommend checking primary source
8. Always note that this is educational guidance, not legal advice
"""
```

### specialists/healthcare_clinical.py
```python
SYSTEM_PROMPT = """
You are Aethera's Clinical Knowledge specialist. You provide clinical reference
information to support coding, documentation, and healthcare operations decisions.
You are NOT providing medical advice to patients — you support healthcare
professionals with clinical knowledge for operational purposes.

## KNOWLEDGE DOMAINS
- Anatomy and physiology (sufficient for accurate coding)
- Pathophysiology of major conditions (for CDI and coding support)
- Pharmacology: drug classes, mechanisms, interactions, contraindications
- Laboratory medicine: test names, LOINC codes, normal ranges, clinical significance
- Diagnostic imaging: modality types, appropriate use criteria
- Medical terminology and abbreviations
- Clinical practice guidelines (USPSTF, ACC/AHA, NCCN, etc.)
- Preventive care screening schedules
- Medical calculators: BMI, eGFR (CKD-EPI), MELD, APACHE II, Wells Score,
  CHA2DS2-VASc, CURB-65, ASCVD risk, Glasgow Coma Scale, NIHSS, etc.
- Chronic disease management protocols
- Social determinants of health (Z-codes for coding)
- Telehealth clinical documentation requirements

## TOOLS
- drug_reference: Drug info, interactions, black box warnings
- lab_interpreter: Lab value lookup and interpretation
- medical_calculator: Clinical scoring tools
- code_lookup: ICD-10 codes for clinical conditions
- screening_guidelines: USPSTF and other preventive care guidelines

## RULES
1. This is clinical REFERENCE information, not patient care advice
2. Always recommend clinical judgment for patient-specific decisions
3. Note when guidelines differ between organizations
4. Flag drug interactions at clinically significant levels
5. Provide context for lab values (not just normal/abnormal)
"""
```

### specialists/healthcare_analytics.py
```python
SYSTEM_PROMPT = """
You are Aethera's Healthcare Analytics specialist. Expert in healthcare data
analysis, quality measurement, risk adjustment, financial modeling, and
population health analytics.

## KNOWLEDGE DOMAINS
- HEDIS measures: all domains, specifications, hybrid vs admin collection
- Medicare Star Ratings: Part C and D measures, cut points, weights, CAI, HEI
- MIPS: Quality, Cost, Promoting Interoperability, Improvement Activities
- APMs: MSSP, BPCI-A, CJR, KCC, ACO REACH, Primary Care First, Making Care Primary
- Risk adjustment: CMS-HCC V24/V28, HHS-HCC, CDPS, ACG
- PMPM analysis and trend decomposition
- MLR calculation (80/20 rule, 85/15 for large group)
- Actuarial analysis: trend factors, IBNR, completion factors
- Utilization metrics: admits/1000, days/1000, ER/1000
- Network analysis: adequacy, leakage, steerage
- Provider profiling: cost efficiency, quality, utilization patterns
- Population health: risk stratification, care gap identification
- Pharmacy analytics: GDR, formulary adherence, specialty spend
- Social determinants data integration

## TOOLS
- risk_adjuster, quality_tracker, calculator (financial/statistical)
- data_visualizer: Create charts and dashboards
- spreadsheet_analyzer: Analyze uploaded data files
"""
```

### specialists/healthcare_it.py
```python
SYSTEM_PROMPT = """
You are Aethera's Healthcare IT specialist. Expert in health information
technology, interoperability standards, and healthcare data systems.

## KNOWLEDGE DOMAINS
- HL7 v2.x messaging: ADT, ORM, ORU, DFT, MDM, SIU segments and fields
- HL7 FHIR R4: Resources, RESTful API, search parameters, extensions
- X12 EDI: 837P/I/D, 835, 270/271, 276/277, 278, 834, 820 — segment-level knowledge
- CDA/C-CDA: Document types, sections, templates
- NCPDP: Pharmacy claim formats
- IHE Profiles: XDS, PIX, PDQ, XCA
- DICOM: Medical imaging standard basics
- Terminology standards: ICD-10, CPT, SNOMED CT, LOINC, RxNorm, NDC, CVX
- EHR systems: Epic, Cerner/Oracle Health, MEDITECH, Allscripts, athenahealth, eClinicalWorks
- Clearinghouse operations: claim submission, ERA retrieval, eligibility checks
- Revenue cycle systems: claim scrubber, encoder, grouper, A/R management
- Population health platforms
- Data warehousing for healthcare
- CMS Interoperability and Patient Access rules
- Information Blocking (21st Century Cures Act)
- TEFCA (Trusted Exchange Framework and Common Agreement)
- Patient matching and MPI management
- Healthcare API security (SMART on FHIR, OAuth2)

## TOOLS
- edi_parser, fhir_client, code_lookup, code_executor
"""
```

### specialists/healthcare_pharmacy.py
```python
SYSTEM_PROMPT = """
You are Aethera's Pharmacy Benefits specialist. Expert in pharmacy benefit
management, drug pricing, formulary management, and pharmacy regulations.

## KNOWLEDGE DOMAINS
- PBM operations: claims adjudication, formulary management, rebate contracting
- Drug pricing benchmarks: AWP, WAC, ASP, NADAC, AMP, FUL, MAC
- 340B Drug Pricing Program: eligible entities, contract pharmacy, duplicate discount
- Medicare Part B drugs: ASP+6%, buy-and-bill, sequestration
- Medicare Part D: Standard benefit design, coverage gap, catastrophic, Low Income Subsidy
- Specialty pharmacy: Limited distribution, REMS, biosimilars, step therapy
- Formulary tiers: generic, preferred brand, non-preferred, specialty, not covered
- Prior authorization for medications
- Quantity limits, age/gender edits, therapeutic class restrictions
- Drug utilization review (DUR): prospective, concurrent, retrospective
- Rebate management: CMS Medicaid Drug Rebate Program, commercial rebates
- Biosimilar and interchangeable biologic products
- Insulin and IRA (Inflation Reduction Act) drug pricing provisions
- NCPDP transaction standards
- Pharmacy network management: retail, mail, specialty, 90-day
- MTM (Medication Therapy Management) programs
- Opioid management programs

## TOOLS
- drug_reference, ndc_pricer, code_lookup (HCPCS J-codes)
"""
```

### specialists/healthcare_behavioral.py
```python
SYSTEM_PROMPT = """
You are Aethera's Behavioral Health specialist. Expert in mental health and
substance use disorder service delivery, billing, parity compliance, and
regulatory requirements.

## KNOWLEDGE DOMAINS
- Mental Health Parity and Addiction Equity Act (MHPAEA)
  * Financial requirements (deductible, copay, coinsurance, OOPM)
  * Quantitative treatment limitations (visit limits, day limits)
  * Non-quantitative treatment limitations (prior auth, step therapy, network)
  * Comparative analysis methodology
  * 2024 Final Rules (NQTL analysis requirements)
- Behavioral health coding:
  * Psychiatric evaluation (90791, 90792)
  * Psychotherapy (90832, 90834, 90837, 90839, 90840)
  * Psychotherapy add-on codes with E/M
  * Psychological testing (96130-96146)
  * Applied behavior analysis (97151-97158, 0362T-0374T)
  * Substance use disorder services (H-codes, T-codes)
  * Crisis intervention (90839, 90840, S9484, S9485)
  * Peer support services (H0038, H0039)
  * Opioid treatment programs (G2067-G2080)
  * Collaborative care model (99492-99494)
  * General behavioral health integration (99484)
- Telehealth behavioral health: originating site, distant site, audio-only
- Behavioral health carve-outs vs carve-ins
- IMD (Institution for Mental Disease) exclusion and exceptions
- SAMHSA regulations (42 CFR Part 2 — SUD confidentiality)
- Involuntary commitment and emergency psychiatric holds
- Autism spectrum disorder services and coverage mandates
- Eating disorder treatment coverage
"""
```

### specialists/healthcare_workers_comp.py
```python
SYSTEM_PROMPT = """
You are Aethera's Workers' Compensation specialist. Expert in workers'
compensation billing, state-specific rules, and occupational health.

## KNOWLEDGE DOMAINS
- WC billing rules by state (fee schedules, billing forms, timely filing)
- First Report of Injury (FROI) requirements
- CMS-1500 vs state-specific WC forms
- WC fee schedules (often based on Medicare RBRVS with multiplier)
- Treatment guidelines (ODG, ACOEM, state-specific)
- Independent Medical Examination (IME) process
- Impairment ratings (AMA Guides to the Evaluation of Permanent Impairment)
- Maximum Medical Improvement (MMI)
- Return-to-work programs
- Medicare Set-Aside (MSA) arrangements
- WC Medicare coordination (Section 111 reporting)
- State WC commission/board procedures
- Employer vs insurer vs third-party administrator roles
- Occupational disease vs injury distinction
"""
```

### specialists/cloudflare_ops.py
```python
SYSTEM_PROMPT = """
You are Aethera's Cloudflare Operations specialist. You manage and optimize
the user's Cloudflare infrastructure across all their websites and applications.

## CAPABILITIES (via Cloudflare API v4 connector)
- DNS: List/create/update/delete DNS records across all zones
- SSL/TLS: Certificate status, encryption mode management
- Tunnels: Status, create, configure, route management
- Access: Zero Trust policies, application configuration
- Pages: Deployment status, build logs, environment variables
- Workers: Script management, KV storage, cron triggers
- R2: Object storage operations, bucket management
- WAF: Rule management, custom rules, rate limiting
- DDoS: Protection status, analytics
- Analytics: Traffic analytics, security events, performance metrics
- Page Rules / Transform Rules / Redirect Rules
- Cache: Purge, cache rules, tiered caching
- Speed: Performance optimization settings
- Images: Image optimization, resizing

## RESPONSE RULES
1. Always confirm destructive actions before executing
2. Show current state before making changes
3. Recommend security best practices
4. Monitor for misconfigurations
5. Use the cloudflare_api connector for all operations
"""
```

### specialists/software_engineering.py, finance.py, legal.py, media_marketing.py, research.py, personal_assistant.py, data_analytics.py
```
# Each of these follows the same pattern:
# - Comprehensive system prompt with domain expertise
# - List of available tools
# - Response rules
# - Write complete implementations matching the depth shown above
# Reference the earlier conversation context for content — 
# implement ALL domains described in the original plans
```

---

## SECTION 6: HEALTHCARE KNOWLEDGE — FINGERTIP REFERENCE

### The AI must know these INSTANTLY without searching:

**Medicare Part A (Hospital Insurance)**
- Covers: inpatient hospital, SNF, home health, hospice
- Deductible: $1,676 (2025), per benefit period
- SNF coinsurance: Days 1-20 $0, Days 21-100 $209.50/day (2025)
- Benefit period: begins on admission, ends after 60 consecutive days out
- Lifetime reserve days: 60 total, $418.50/day coinsurance (2025)

**Medicare Part B (Medical Insurance)**
- Covers: physician services, outpatient, DME, preventive
- Premium: $185.00/month standard (2025), IRMAA surcharges
- Deductible: $257/year (2025)
- Coinsurance: 20% after deductible (most services)
- Assignment: participating vs non-participating vs opt-out providers
- Limiting charge: 115% of non-par allowed amount

**Medicare Part C (Medicare Advantage)**
- Must cover all Part A and B benefits (except hospice)
- Can offer supplemental benefits
- Star Ratings drive quality bonus payments
- Risk adjusted payments (CMS-HCC model)

**Medicare Part D (Prescription Drug)**
- Standard benefit phases: deductible → initial coverage → coverage gap → catastrophic
- 2025 IRA changes: $2,000 out-of-pocket cap, manufacturer discounts
- Part D plans: PDP (standalone) or MA-PD (bundled with MA)
- LIS (Low Income Subsidy) / Extra Help

**Key Numbers to Know (2025 values — update annually)**
- Medicare conversion factor: ~$32.74 (check annually)
- DRG base rate: varies by hospital (wage index adjusted)
- OOPM limits: ACA marketplace $9,200 individual / $18,400 family (2025)
- HSA contribution limits: $4,300 individual / $8,550 family (2025)

**CARC Codes — Most Common (instant recall)**
- CO-4: Procedure code inconsistent with modifier or missing modifier
- CO-11: Diagnosis inconsistent with procedure
- CO-16: Claim/service lacks information needed for adjudication
- CO-18: Duplicate claim/service
- CO-22: Coordination of benefits (this care may be covered by another payer)
- CO-27: Expenses incurred after coverage terminated
- CO-29: Time limit for filing has expired
- CO-45: Charges exceed your contracted/legislated fee arrangement
- CO-50: Not medically necessary
- CO-97: Payment adjusted because already adjudicated (bundled)
- PR-1: Deductible amount
- PR-2: Coinsurance amount
- PR-3: Copay amount
- OA-23: Impact of prior payer adjudication

**Timely Filing Limits**
- Medicare: 12 months from DOS (or 12 months from MSP discovery for secondary)
- Medicaid: Varies by state (90 days to 12 months)
- TRICARE: 12 months from DOS
- Workers Comp: Varies by state
- Commercial: 90 days to 365 days (per contract)

**Appeal Deadlines**
- Medicare Redetermination: 120 days from date on RA
- Medicare QIC Reconsideration: 180 days from Redetermination
- Medicare ALJ Hearing: 60 days from QIC decision (must meet $180 minimum 2025)
- Medicare Appeals Council: 60 days from ALJ decision
- Federal Court: 60 days from Appeals Council decision

**HIPAA Transaction Code Sets**
- 837P: Professional claim
- 837I: Institutional claim
- 837D: Dental claim
- 835: Electronic remittance advice
- 270/271: Eligibility inquiry/response
- 276/277: Claim status inquiry/response
- 278: Prior authorization request/response
- 834: Enrollment/disenrollment
- 820: Premium payment

**Place of Service Codes (most common)**
- 11: Office
- 12: Home
- 19: Off Campus-Outpatient Hospital
- 21: Inpatient Hospital
- 22: On Campus-Outpatient Hospital
- 23: Emergency Room-Hospital
- 24: Ambulatory Surgical Center
- 31: Skilled Nursing Facility
- 32: Nursing Facility
- 81: Independent Laboratory
- 02: Telehealth (provided in patient's home)
- 10: Telehealth (provided other than patient's home)

---

## SECTION 7: ORCHESTRATOR — COMPLETE IMPLEMENTATION

### orchestrator/router.py
```python
class AetheraRouter:
    """
    The brain of Aethera. Routes every query to the right specialist(s)
    with the right model, tools, and context.
    
    Flow:
    1. Receive user message + conversation history
    2. Check sensitivity (PHI/PII) → if positive, force local model
    3. Classify intent → identify primary specialist + confidence
    4. If confidence < 0.7 or query spans domains → multi-agent reasoning
    5. Select model based on: specialist preference, complexity, rate limits
    6. Attach relevant tools (skills) based on specialist + query content
    7. Inject relevant RAG context from ChromaDB
    8. Inject user profile context
    9. Execute LLM call with full context
    10. Score confidence of response
    11. Log everything to audit trail
    12. Return response with metadata (specialist, model, confidence, tools used)
    
    SPECIALISTS (20 total):
    - healthcare_provider
    - healthcare_payer
    - healthcare_regulatory
    - healthcare_clinical
    - healthcare_analytics
    - healthcare_it
    - healthcare_pharmacy
    - healthcare_behavioral
    - healthcare_dental_vision
    - healthcare_workers_comp
    - finance
    - legal
    - software_engineering
    - media_marketing
    - research
    - personal_assistant
    - cloudflare_ops
    - data_analytics
    - general (default fallback)
    
    Slash commands recognized:
    /help                     — show all commands
    /specialist <name>        — force a specific specialist
    /skills                   — list available skills
    /skill <name>             — run a specific skill
    /plugins                  — list plugins and status
    /connectors               — list connectors and status
    /automations              — list active automations
    /queue                    — show action queue
    /briefing                 — generate morning briefing
    /alerts                   — show active alerts
    /dashboard                — switch to dashboard view
    /code <query>             — force ICD-10/CPT lookup
    /appeal <claim_info>      — start appeals workflow
    /denial <codes>           — analyze denial
    /drug <name>              — drug lookup
    /npi <number_or_name>     — NPI lookup
    /coverage <cpt> <payer>   — coverage criteria check
    /fee <cpt>                — fee schedule lookup
    /cf status                — Cloudflare infrastructure status
    /profile                  — view/edit user profile
    /settings                 — open settings
    /export <type>            — export data (audit, claims, financials)
    /model <name>             — force a specific model
    /local                    — force local Ollama model
    /search <query>           — web search
    /memory                   — show what Aethera remembers about you
    /forget <topic>           — remove specific memories
    """
```

### orchestrator/cascade.py
```python
class AetheraCascade:
    """
    Model cascade optimized for Ollama Cloud (Pro plan) + Local models.
    
    ROUTING LOGIC — which model handles what:
    
    ┌─────────────────────────────────────────────────────────────────┐
    │ PHI/PII DETECTED → ALWAYS aethera-local-fast (qwen3.5:4b GPU) │
    │                    Data NEVER leaves the machine               │
    └─────────────────────────────────────────────────────────────────┘
    
    For non-sensitive queries, route by task type:
    
    1. Simple/fast queries → aethera-local-fast (qwen3.5:4b GPU)
       - Code lookups, quick definitions, simple math
       - Instant response, zero cloud usage
    
    2. Healthcare analysis → aethera-cloud-brain (qwen3.5:122b)
       - Complex coding questions, denial analysis, appeals
       - Regulatory interpretation, contract analysis
       - Best quality, uses Level 3 cloud quota
    
    3. Deep reasoning → aethera-cloud-reason (deepseek-v4-flash)
       - Long document analysis (1M context window)
       - Multi-step research, literature review
       - Chain-of-thought reasoning tasks
    
    4. Coding tasks → aethera-cloud-coder (kimi-k2.6)
       - Code generation, debugging, architecture
       - Agentic coding workflows
       - Building Aethera features/plugins
    
    5. Tool calling / structured output → aethera-cloud-tools (gemma4:26b)
       - Document parsing, image/screenshot analysis
       - EDI parsing, form filling, structured extraction
       - Lower cloud usage (Level 2)
    
    6. Multi-agent debates → aethera-cloud-agent (nemotron-3-super)
       - When 2-3 specialists reason in parallel
       - Efficient: 120B MoE but only 12B active
    
    7. Medium queries → aethera-cloud-balanced (qwen3.5:35b)
       - Good enough for most queries, lower usage than 122b
       - Default for general conversation, drafting, summarization
    
    8. Overflow → hf-qwen-72b (HuggingFace free tier)
       - When Ollama Cloud session/weekly limit hit
       - Free, ~1000 req/day
    
    9. Last resort → aethera-local-smart (qwen3.5:9b CPU)
       - When ALL cloud is exhausted
       - Slower but capable, always available, unlimited
    
    SPECIALIST → MODEL MAPPING:
    
    healthcare_provider:    aethera-cloud-brain (needs accuracy for coding/billing)
    healthcare_payer:       aethera-cloud-brain (needs accuracy for adjudication logic)
    healthcare_regulatory:  aethera-cloud-brain (needs accuracy for regulatory citations)
    healthcare_clinical:    aethera-cloud-brain (needs accuracy for clinical knowledge)
    healthcare_analytics:   aethera-cloud-reason (needs deep analysis + large context)
    healthcare_it:          aethera-cloud-tools (needs structured output for EDI/FHIR)
    healthcare_pharmacy:    aethera-cloud-balanced (medium complexity)
    healthcare_behavioral:  aethera-cloud-balanced (medium complexity)
    healthcare_dental_vision: aethera-cloud-balanced (medium complexity)
    healthcare_workers_comp: aethera-cloud-balanced (medium complexity)
    software_engineering:   aethera-cloud-coder (best for code)
    finance:                aethera-cloud-balanced (calculations + analysis)
    legal:                  aethera-cloud-brain (needs accuracy for legal analysis)
    media_marketing:        aethera-cloud-balanced (creative tasks)
    research:               aethera-cloud-reason (deep research, long context)
    personal_assistant:     aethera-local-fast (simple tasks, keep local)
    cloudflare_ops:         aethera-cloud-tools (API calls, structured operations)
    data_analytics:         aethera-cloud-reason (data analysis, large context)
    
    RATE LIMIT TRACKING (Redis):
    - Track Ollama Cloud session usage (resets every 5 hours)
    - Track Ollama Cloud weekly usage (resets every 7 days)
    - Track HuggingFace daily requests (~1000/day)
    - Track per-model usage levels (L1 light → L4 extra heavy)
    - Auto-failover: when one provider hits limit, seamlessly try next
    - User dashboard shows real-time usage across all providers
    
    COST OPTIMIZATION:
    - Route simple queries locally (free) to preserve cloud quota
    - Use Level 2 models (gemma4:26b, qwen3.5:35b) over Level 3 when possible
    - Reserve Level 3+ (qwen3.5:122b, kimi-k2.6) for genuinely complex tasks
    - Batch similar queries to share cached context (reduces cloud usage)
    """
```

---

## SECTION 8: PROACTIVE INTELLIGENCE

### proactive/morning_briefing.py
```python
"""
Daily morning briefing generated at user's configured time.

Contents:
1. Date, weather at user's location
2. Calendar events today (if calendar plugin connected)
3. Action queue: critical and urgent items
4. New alerts since last briefing
5. Healthcare updates: new CMS transmittals, LCD/NCD changes, OIG reports
6. System status: all containers healthy, model availability, storage usage
7. Stats: yesterday's usage (queries, tools used, denials analyzed)
8. News digest: top 3-5 relevant items from RSS feeds
9. Upcoming deadlines (from temporal engine)
10. Knowledge gap resolutions: "I learned about X overnight"

Delivered via:
- Chat notification in UI
- Telegram bot (if configured)
- Browser push notification
- Available via /briefing command anytime
"""
```

### proactive/feeds.yaml
```yaml
healthcare:
  - name: "CMS Newsroom"
    url: "https://www.cms.gov/newsroom/rss"
    check_interval: "4h"
  - name: "Federal Register - CMS"
    url: "https://www.federalregister.gov/api/v1/documents.rss?conditions[agencies][]=centers-for-medicare-medicaid-services"
    check_interval: "4h"
  - name: "OIG Reports"
    url: "https://oig.hhs.gov/rss/spotlight.xml"
    check_interval: "24h"
  - name: "HHS.gov"
    url: "https://www.hhs.gov/rss/news.xml"
    check_interval: "12h"
  - name: "Becker's Hospital Review"
    url: "https://www.beckershospitalreview.com/feed.xml"
    check_interval: "6h"
  - name: "Health Affairs Blog"
    url: "https://www.healthaffairs.org/do/10.1377/feeds/blog/rss"
    check_interval: "12h"
  - name: "Modern Healthcare"
    url: "https://www.modernhealthcare.com/section/rss"
    check_interval: "12h"
  - name: "AMA News"
    url: "https://www.ama-assn.org/rss"
    check_interval: "24h"

technology:
  - name: "Hacker News"
    url: "https://hnrss.org/frontpage"
    check_interval: "2h"
  - name: "Cloudflare Blog"
    url: "https://blog.cloudflare.com/rss/"
    check_interval: "12h"
  - name: "GitHub Blog"
    url: "https://github.blog/feed/"
    check_interval: "12h"

security:
  - name: "NVD CVE Feed"
    url: "https://nvd.nist.gov/feeds/xml/cve/misc/nvd-rss-analyzed.xml"
    check_interval: "6h"
  - name: "CISA Alerts"
    url: "https://www.cisa.gov/news.xml"
    check_interval: "12h"
```

---

## SECTION 9: UI DESIGN SPECIFICATION

### Design System for Aethera
```
Theme: "Clinical Intelligence" — dark mode primary, light mode available
Background: Deep charcoal #0D1117 (dark) / Snow white #FAFBFC (light)
Primary accent: Teal #06B6D4 (healthcare trust color)
Secondary accent: Amber #F59E0B (alerts, warnings)
Success: Emerald #10B981
Error: Rose #F43F5E
Text: #E6EDF3 (dark) / #1F2937 (light)

Typography:
- Headings: "Outfit" (modern, clean, geometric)
- Body: "Source Sans 3" (optimized for medical terminology readability)
- Code/Data: "JetBrains Mono" (excellent for codes, numbers, EDI data)

Specialist Color Coding:
- Healthcare Provider: #06B6D4 (teal)
- Healthcare Payer: #8B5CF6 (purple)
- Healthcare Regulatory: #F43F5E (rose)
- Healthcare Clinical: #10B981 (emerald)
- Healthcare Analytics: #F59E0B (amber)
- Healthcare IT: #3B82F6 (blue)
- Healthcare Pharmacy: #EC4899 (pink)
- Finance: #22C55E (green)
- Legal: #EF4444 (red)
- Software: #6366F1 (indigo)
- Research: #14B8A6 (teal-dark)
- Personal: #A855F7 (violet)
- Cloudflare: #F97316 (orange)

Layout: Responsive 3-panel (sidebar / chat / context panel)
Mobile: Single-panel with slide-out sidebar and bottom nav
Animations: Subtle — fade-in messages, smooth panel transitions
```

### PWA Configuration
```json
{
  "name": "Aethera AI",
  "short_name": "Aethera",
  "description": "Your Personal Healthcare AI Super Agent",
  "start_url": "/",
  "display": "standalone",
  "orientation": "any",
  "background_color": "#0D1117",
  "theme_color": "#06B6D4",
  "categories": ["productivity", "medical", "business"],
  "icons": [
    {"src": "/icons/icon-72.png", "sizes": "72x72", "type": "image/png"},
    {"src": "/icons/icon-96.png", "sizes": "96x96", "type": "image/png"},
    {"src": "/icons/icon-128.png", "sizes": "128x128", "type": "image/png"},
    {"src": "/icons/icon-144.png", "sizes": "144x144", "type": "image/png"},
    {"src": "/icons/icon-152.png", "sizes": "152x152", "type": "image/png"},
    {"src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
    {"src": "/icons/icon-384.png", "sizes": "384x384", "type": "image/png"},
    {"src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}
  ]
}
```

---

## SECTION 10: setup.ps1 — ONE-CLICK SETUP

The setup script must:
1. Display Aethera ASCII art banner
2. Check prerequisites: Docker Desktop (with WSL2), Git, Node.js v18+, Python 3.11+
3. Check NVIDIA driver for MX450 GPU passthrough
4. Prompt for configurations:
   - Ollama API Key (REQUIRED — get from ollama.com → Settings → API Keys)
     * Explain: "Aethera uses Ollama Cloud for frontier models like qwen3.5:122b"
     * Recommend: "Pro plan ($20/mo) for 3 concurrent models needed for multi-agent"
     * Free tier works but with limited session/weekly usage
   - HuggingFace token (optional — free account at huggingface.co for overflow capacity)
   - Cloudflare API token (RECOMMENDED — for managing your websites + Aethera tunnel)
   - Cloudflare Account ID (shown in Cloudflare dashboard)
   - Cloudflare Tunnel name for Aethera remote access (e.g., "aethera")
   - Your email for Cloudflare Access OTP authentication
   - GitHub PAT (optional — for repo integration and code review plugin)
   - Email IMAP server + credentials (optional — for email intelligence plugin)
   - Telegram Bot Token (optional — for push notifications via Telegram)
   - Custom API endpoint (optional — any OpenAI-compatible URL for extra models)
5. Generate .env file from inputs
6. Create Docker volumes
7. Build all Docker images (show progress)
8. Start Docker Compose stack
9. Wait for Ollama to be ready, then pull LOCAL models:
   - qwen3.5:4b (GPU-optimized for MX450, ~2.5GB) — primary local model
   - gemma4:e2b (GPU-optimized for MX450, ~1.5GB) — tool calling model
   - qwen3.5:9b (CPU-only, ~5.5GB) — smart local fallback
   - nomic-embed-text (CPU, ~300MB) — embeddings for ChromaDB RAG
   Note: Cloud models (qwen3.5:122b, deepseek-v4-flash, kimi-k2.6, gemma4:26b, etc.)
   do NOT need to be pulled — they run on Ollama's cloud infrastructure via API
10. Download healthcare knowledge bases (show progress for each):
    - ICD-10-CM codes from CMS.gov
    - HCPCS codes from CMS.gov
    - NCCI edit files from CMS.gov
    - MUE values from CMS.gov
    - MPFS RVU files from CMS.gov
    - DRG weights from CMS.gov
    - CARC/RARC codes from X12.org
    - Medicare manuals (key chapters) from CMS.gov
    - OIG Work Plan from OIG.hhs.gov
    - HIPAA rule text from HHS.gov
11. Index all knowledge bases into ChromaDB (show progress)
12. Set up Cloudflare Tunnel (if token provided):
    - Install cloudflared
    - Create tunnel
    - Configure route to Aethera UI (port 3000)
    - Configure Cloudflare Access with email OTP
13. Create Windows Task Scheduler entry:
    - Task: "Aethera AI Auto-Start"
    - Trigger: At system startup
    - Action: docker compose up -d in project directory
14. Create desktop shortcut to http://localhost:3000
15. Print summary:
    - Local URL: http://localhost:3000
    - Tunnel URL: https://aethera.yourdomain.com (if configured)
    - API URL: http://localhost:8000
    - Models loaded: list
    - Knowledge bases indexed: list
    - Storage used: X GB
    - Estimated RAM usage: X GB
    - "Aethera is ready. Open your browser to get started."

---

## SECTION 11: COMPLETE ENHANCEMENT LIST

Build ALL of these (refer to earlier conversation for full specs):

1. **Chain-of-Agents Reasoning** — Multi-specialist debate for complex queries
2. **Temporal Reasoning Engine** — Deadline/expiration tracking with auto-escalation
3. **Counterfactual Analysis** — "What if" scenario modeling
4. **Contradiction Detector** — Flag conflicting stored facts
5. **Denial Prediction Engine** — Pre-submission claim scrubbing with risk score
6. **Revenue Forecast Model** — Project revenue from claims data
7. **Smart Follow-Up Queue** — Prioritized action items with auto-escalation
8. **Email Intelligence** — Auto-categorize, extract actions, draft replies (IMAP)
9. **Document Intelligence Pipeline** — Auto-classify and process any uploaded document
10. **Webhook Receiver** — React to external events (GitHub, Cloudflare, RSS)
11. **Clipboard Intelligence** — System tray agent monitoring clipboard for codes/NPIs
12. **Ambient Voice Mode** — Hands-free voice conversation
13. **Screen Understanding** — Screenshot analysis (via multimodal local model)
14. **Audio Meeting Processor** — Transcription + action items + compliance flags
15. **Personal Knowledge Graph** — Entity-relationship visualization
16. **Real-Time Analytics Dashboard** — Live system + healthcare + finance metrics
17. **Comparative Intelligence** — Side-by-side comparisons on demand
18. **Explainable AI Layer** — Reasoning chain for every response
19. **Confidence Scoring** — Green/yellow/red confidence badges
20. **Audit Trail** — HIPAA-grade immutable logging
21. **Knowledge Gap Detector** — Auto-research and fill gaps overnight
22. **Prompt Self-Optimization** — A/B test specialist prompts based on feedback
23. **Adaptive Learning** — Learn user patterns locally, never send data out
24. **Natural Language Automation** — Create workflows in plain English
25. **Smart Templates** — Self-improving document templates
26. **Context Handoff** — Seamless device-to-device conversation continuity
27. **News Aggregator** — RSS-based curated news with impact assessment
28. **Peer Benchmarking** — Compare metrics against industry benchmarks
29. **Adaptive UI Modes** — Focus/Dashboard/Mobile/Emergency modes
30. **Gamification & Stats** — Achievements, streaks, productivity tracking

---

## SECTION 12: API ENDPOINTS

```
# Core Chat
POST   /api/chat                          # Main chat (streaming SSE)
POST   /api/chat/specialist/{name}        # Force specific specialist
POST   /api/chat/multi-agent              # Force multi-agent reasoning
POST   /api/upload                        # File upload + auto-process
GET    /api/conversations                 # List conversations
GET    /api/conversations/{id}            # Get conversation history
DELETE /api/conversations/{id}            # Delete conversation

# Specialists
GET    /api/specialists                   # List all specialists
GET    /api/specialists/{name}            # Specialist details + stats

# Skills
GET    /api/skills                        # List all skills by category
GET    /api/skills/{name}                 # Skill details + examples
POST   /api/skills/{name}/execute         # Execute a skill directly

# Healthcare Tools (direct access)
POST   /api/healthcare/code-lookup        # ICD-10/CPT/HCPCS/CDT lookup
POST   /api/healthcare/cci-check          # CCI edit pair check
POST   /api/healthcare/fee-schedule       # Fee schedule lookup
POST   /api/healthcare/coverage           # LCD/NCD criteria check
POST   /api/healthcare/denial-analyze     # Denial code analysis
POST   /api/healthcare/denial-predict     # Pre-submission claim scrub
POST   /api/healthcare/appeal-generate    # Generate appeals letter
POST   /api/healthcare/drg-group          # DRG grouping
POST   /api/healthcare/drug-lookup        # Drug info + interactions
POST   /api/healthcare/npi-lookup         # NPI registry search
POST   /api/healthcare/edi-parse          # Parse EDI transaction
POST   /api/healthcare/risk-adjust        # HCC/RAF calculation
POST   /api/healthcare/medical-calc       # Clinical calculator

# Plugins & Connectors
GET    /api/plugins                       # List plugins + status
POST   /api/plugins/{name}/enable         # Enable plugin
POST   /api/plugins/{name}/disable        # Disable plugin
POST   /api/plugins/{name}/config         # Configure plugin
GET    /api/connectors                    # List connectors + status
POST   /api/connectors/{name}/connect     # Connect to data source
POST   /api/connectors/{name}/disconnect  # Disconnect
POST   /api/connectors/{name}/test        # Test connection

# Cloudflare Management
GET    /api/cloudflare/status             # All zones, tunnels, workers status
GET    /api/cloudflare/zones              # List zones with analytics
POST   /api/cloudflare/dns               # DNS operations
GET    /api/cloudflare/tunnels            # Tunnel status
GET    /api/cloudflare/security           # Security overview

# Memory & Profile
GET    /api/memory/profile                # Get user profile
POST   /api/memory/profile                # Update user profile
GET    /api/memory/search                 # Search memory/knowledge
GET    /api/memory/knowledge-graph        # Get knowledge graph data
POST   /api/memory/forget                 # Remove specific memories

# Proactive Intelligence
GET    /api/briefing                      # Get/generate morning briefing
GET    /api/alerts                        # Active alerts
POST   /api/alerts/{id}/acknowledge       # Acknowledge alert
GET    /api/queue                         # Action queue (sorted by priority)
POST   /api/queue/{id}/complete           # Mark item complete
GET    /api/automations                   # List automations
POST   /api/automations                   # Create automation (natural language)
DELETE /api/automations/{id}              # Delete automation
GET    /api/news                          # Curated news feed

# Analytics & Monitoring
GET    /api/dashboard                     # Dashboard data (usage, health, metrics)
GET    /api/usage                         # Token usage by provider
GET    /api/models                        # Available models + health
GET    /api/audit                         # Audit log (filterable)
POST   /api/audit/export                  # Export audit report

# Voice
POST   /api/voice/stt                     # Speech-to-text
POST   /api/voice/tts                     # Text-to-speech
WS     /api/voice/stream                  # WebSocket voice conversation

# System
GET    /api/health                        # System health check
GET    /api/version                       # Version info
POST   /api/backup                        # Trigger backup
GET    /api/settings                      # Get settings
POST   /api/settings                      # Update settings
```

---

## SECTION 13: CRITICAL REQUIREMENTS

1. **EVERY file must be complete and runnable** — no stubs, no placeholders, no "implement this"
2. **setup.ps1 is the ONLY thing I run** — it handles everything from scratch
3. **ALL healthcare data stays local** — PHI detection routes to local Ollama, NEVER to cloud
4. **Ollama Cloud is the primary brain** — user has Ollama account, Pro plan ($20/mo) recommended for 3 concurrent models
5. **Ollama Cloud API** — api_base: https://ollama.com, Authorization: Bearer OLLAMA_API_KEY
6. **Cloud models to configure** — qwen3.5:122b (brain), deepseek-v4-flash (reasoning), kimi-k2.6 (coding), gemma4:26b (tools), nemotron-3-super (agent), qwen3.5:35b (balanced), glm-5.1 (engineering)
7. **Local models to pull** — qwen3.5:4b (GPU), gemma4:e2b (GPU), qwen3.5:9b (CPU), nomic-embed-text (embeddings)
8. **HuggingFace free tier as overflow** — Qwen2.5-72B and Mistral-7B when cloud quota exhausted
9. **PWA must be installable** — works on phone home screen like a native app
10. **Cloudflare Tunnel for anywhere access** — with Cloudflare Access email OTP auth
11. **Survives reboots** — Task Scheduler auto-start
12. **Memory persists forever** — ChromaDB + SQLite + SQLCipher for encrypted health data
13. **Model cascade auto-failover** — seamless, user never sees an error
14. **Skills/Plugins/Connectors** are extensible — anyone can add new ones following the spec
15. **NVIDIA MX450 must be utilized** — GPU passthrough for local qwen3.5:4b and gemma4:e2b
16. **Healthcare knowledge must be encyclopedic** — download and index ALL public CMS data
17. **Audit trail is HIPAA-grade** — immutable, timestamped, exportable
18. **The name is "Aethera" everywhere** — UI, API responses, prompts, branding
19. **Smart cloud quota management** — use Level 2 cloud models for medium tasks, reserve Level 3+ for complex
20. **Route simple queries locally** — preserve cloud quota by handling lookups, PHI, and basic queries on-device

## SECTION 14: BUILD ORDER

Phase 1 (Foundation):
- docker-compose.yml + docker-compose.override.yml (GPU)
- .env.example
- litellm_config.yaml
- searxng-settings.yml
- setup.ps1

Phase 2 (Orchestrator):
- orchestrator/main.py (FastAPI with ALL endpoints)
- orchestrator/router.py (intent classification)
- orchestrator/cascade.py (model cascade)
- orchestrator/sensitivity.py (PHI/PII detection)
- orchestrator/config.yaml

Phase 3 (Specialists):
- ALL 20 specialist files with complete system prompts

Phase 4 (Skills System):
- skills/skill_base.py, skill_registry.py
- ALL built-in skills (14 general + 24 healthcare)

Phase 5 (Plugins):
- plugins/plugin_base.py, plugin_registry.py
- Cloudflare plugin (complete)
- Email plugin
- GitHub plugin
- Calendar plugin
- Notification plugins (Telegram, browser push)

Phase 6 (Connectors):
- connectors/connector_base.py, connector_registry.py
- ALL healthcare connectors (CMS NPI, OpenFDA, PubMed, RxNorm, etc.)
- Infrastructure connectors (Cloudflare API, SearXNG, GitHub)

Phase 7 (Memory):
- ALL memory modules (vector store, conversation, profile, knowledge graph, health records, audit)

Phase 8 (Knowledge Bases):
- ALL download scripts for healthcare data
- index_all.py for ChromaDB indexing

Phase 9 (UI):
- Complete React PWA with ALL components listed
- Service worker for offline
- PWA manifest and icons

Phase 10 (Enhancements):
- Multi-agent reasoning
- Temporal engine
- Denial prediction
- Action queue
- All 30 enhancements

Phase 11 (Proactive):
- Scheduler, briefing, alerts, news, automations

Phase 12 (Voice + Clipboard):
- Voice subsystem (STT/TTS)
- Clipboard agent

Phase 13 (Infrastructure):
- Cloudflare Tunnel + Access setup scripts
- Backup/restore scripts
- Monitoring

Phase 14 (Tests):
- ALL test files

---

**Build everything. Build it completely. Make Aethera the most capable personal AI agent ever built on a laptop. Start with Phase 1.**
