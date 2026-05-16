// ---------------------------------------------------------------------------
// Specialist definitions
// ---------------------------------------------------------------------------

export const SPECIALIST_NAMES = {
  healthcare_provider: 'Provider Ops',
  healthcare_payer: 'Payer Ops',
  healthcare_clinical: 'Clinical',
  healthcare_regulatory: 'Regulatory',
  healthcare_analytics: 'Analytics',
  healthcare_it: 'Healthcare IT',
  healthcare_pharmacy: 'Pharmacy',
  healthcare_behavioral: 'Behavioral Health',
  healthcare_dental_vision: 'Dental & Vision',
  healthcare_workers_comp: 'Workers Comp',
  finance: 'Finance',
  legal: 'Legal',
  software_engineering: 'Software Engineering',
  media_marketing: 'Media & Marketing',
  research: 'Research',
  personal_assistant: 'Personal Assistant',
  cloudflare_ops: 'Cloudflare Ops',
  data_analytics: 'Data Analytics',
  general: 'General',
};

export const SPECIALIST_COLORS = {
  healthcare_provider:     { bg: '#0E7C6B', text: '#FFFFFF' },
  healthcare_payer:       { bg: '#1D6FB8', text: '#FFFFFF' },
  healthcare_clinical:    { bg: '#7C3AED', text: '#FFFFFF' },
  healthcare_regulatory:  { bg: '#B45309', text: '#FFFFFF' },
  healthcare_analytics:   { bg: '#0891B2', text: '#FFFFFF' },
  healthcare_it:          { bg: '#4F46E5', text: '#FFFFFF' },
  healthcare_pharmacy:    { bg: '#059669', text: '#FFFFFF' },
  healthcare_behavioral: { bg: '#DB2777', text: '#FFFFFF' },
  healthcare_dental_vision: { bg: '#0D9488', text: '#FFFFFF' },
  healthcare_workers_comp: { bg: '#9333EA', text: '#FFFFFF' },
  finance:                { bg: '#16A34A', text: '#FFFFFF' },
  legal:                  { bg: '#DC2626', text: '#FFFFFF' },
  software_engineering:   { bg: '#2563EB', text: '#FFFFFF' },
  media_marketing:        { bg: '#EA580C', text: '#FFFFFF' },
  research:               { bg: '#7C3AED', text: '#FFFFFF' },
  personal_assistant:     { bg: '#6B7280', text: '#FFFFFF' },
  cloudflare_ops:         { bg: '#F59E0B', text: '#000000' },
  data_analytics:         { bg: '#0EA5E9', text: '#FFFFFF' },
  general:                { bg: '#6B7280', text: '#FFFFFF' },
};

// ---------------------------------------------------------------------------
// Model definitions
// ---------------------------------------------------------------------------

export const MODEL_NAMES = {
  claude_4_7_sonnet:  'Claude 4.7 Sonnet',
  claude_4_opus:      'Claude 4 Opus',
  claude_3_5_haiku:   'Claude 3.5 Haiku',
  gpt_4o:            'GPT-4o',
  gpt_4o_mini:       'GPT-4o Mini',
  gemini_2_pro:       'Gemini 2 Pro',
  llama_3_1_70b:      'Llama 3.1 70B',
  mixtral_8x7b:       'Mixtral 8x7B',
};

export const DEFAULT_MODEL = 'claude_4_7_sonnet';

// ---------------------------------------------------------------------------
// API paths
// ---------------------------------------------------------------------------

export const API_PATHS = {
  // Chat
  CHAT_STREAM:        '/api/chat/stream',
  CHAT:               '/api/chat',
  CHAT_SPECIALIST:    (name) => `/api/chat/specialist/${name}`,
  CHAT_MULTI_AGENT:   '/api/chat/multi-agent',

  // Conversations
  CONVERSATIONS:      '/api/conversations',
  CONVERSATION:       (id) => `/api/conversations/${id}`,

  // Specialists
  SPECIALISTS:        '/api/specialists',
  SPECIALIST_QUERY:   (id) => `/api/specialists/${id}/query`,

  // Healthcare
  CODE_LOOKUP:        '/api/healthcare/code-lookup',
  CODE_SEARCH:        '/api/healthcare/code-search',
  CCI_CHECK:          '/api/healthcare/cci-check',
  COVERAGE:           '/api/healthcare/coverage',
  DENIAL_ANALYSIS:    '/api/healthcare/denial-analyze',
  DENIAL_PREDICT:     '/api/healthcare/denial-predict',
  APPEAL_GENERATE:    '/api/healthcare/appeal-generate',
  FEE_SCHEDULE:       '/api/healthcare/fee-schedule',
  NPI_LOOKUP:         '/api/healthcare/npi-lookup',
  CLAIM_ANALYSIS:     '/api/healthcare/claim-analysis',
  DRG_GROUP:          '/api/healthcare/drg-group',
  DRUG_LOOKUP:        '/api/healthcare/drug-lookup',
  RISK_ADJUST:        '/api/healthcare/risk-adjust',
  MEDICAL_CALC:       '/api/healthcare/medical-calc',
  EDI_PARSE:          '/api/healthcare/edi-parse',
  EDI_STATUS:         '/api/healthcare/edi-status',

  // Skills
  SKILLS:             '/api/skills',
  SKILL_EXECUTE:      (name) => `/api/skills/${name}/execute`,

  // Plugins
  PLUGINS:            '/api/plugins',
  PLUGIN_ENABLE:      (name) => `/api/plugins/${name}/enable`,
  PLUGIN_DISABLE:     (name) => `/api/plugins/${name}/disable`,
  PLUGIN_CONFIG:      (name) => `/api/plugins/${name}/config`,

  // Connectors
  CONNECTORS:         '/api/connectors',

  // Memory
  MEMORY_SEARCH:      '/api/memory/search',
  MEMORY_FORGET:      '/api/memory/forget',
  MEMORY_KNOWLEDGE_GRAPH: '/api/memory/knowledge-graph',
  MEMORY_CONSOLIDATE: '/api/memory/consolidate',

  // Memory — Profile
  MEMORY_PROFILE:     (userId) => `/api/memory/profile/${userId}`,

  // Memory — Facts
  MEMORY_FACTS:             '/api/memory/facts',
  MEMORY_FACTS_STATS:       '/api/memory/facts/stats',
  MEMORY_FACTS_CONTRADICTIONS: '/api/memory/facts/contradictions',
  MEMORY_FACTS_EXPIRE:      '/api/memory/facts/expire-outdated',

  // Memory — Health Records
  MEMORY_HEALTH_RECORDS:         (userId) => `/api/memory/health-records/${userId}`,
  MEMORY_HEALTH_RECORDS_ADD:     '/api/memory/health-records',
  MEMORY_HEALTH_RECORDS_TIMELINE: (userId) => `/api/memory/health-records/${userId}/timeline`,
  MEMORY_HEALTH_RECORDS_EXPORT:  (userId) => `/api/memory/health-records/${userId}/export-deidentified`,

  // Memory — Learning
  MEMORY_LEARNING_PREFERENCES:  (userId) => `/api/memory/learning/preferences/${userId}`,
  MEMORY_LEARNING_INTERACTIONS: '/api/memory/learning/interactions',
  MEMORY_LEARNING_PREDICT:      (userId) => `/api/memory/learning/predict/${userId}`,
  MEMORY_LEARNING_STATS:        '/api/memory/learning/stats',

  // Memory — Knowledge Gaps
  MEMORY_KNOWLEDGE_GAPS:            '/api/memory/knowledge-gaps',
  MEMORY_KNOWLEDGE_GAPS_DETECT:    '/api/memory/knowledge-gaps/detect',
  MEMORY_KNOWLEDGE_GAPS_RESEARCH:  (id) => `/api/memory/knowledge-gaps/${id}/research`,
  MEMORY_KNOWLEDGE_GAPS_FILL:      (id) => `/api/memory/knowledge-gaps/${id}/fill`,
  MEMORY_KNOWLEDGE_GAPS_STATS:     '/api/memory/knowledge-gaps/stats',

  // Upload
  UPLOAD:              '/api/upload',

  // Dashboard, Alerts, Queue
  DASHBOARD:          '/api/dashboard',
  BACKUP:             '/api/backup',
  BACKUP_LIST:        '/api/backup/list',
  BACKUP_RESTORE:     '/api/backup/restore',
  ALERTS:             '/api/alerts',
  ALERT_ACK:          (id) => `/api/alerts/${id}/acknowledge`,
  QUEUE:              '/api/queue',
  QUEUE_ADD:          '/api/queue',
  QUEUE_COMPLETE:     (id) => `/api/queue/${id}/complete`,
  QUEUE_STATS:        '/api/queue/stats',

  // Temporal
  TEMPORAL_UPCOMING:  '/api/temporal/upcoming',
  TEMPORAL_OVERDUE:   '/api/temporal/overdue',
  TEMPORAL_ITEMS:     '/api/temporal/items',
  TEMPORAL_EXTRACT:   '/api/temporal/extract',
  TEMPORAL_HEALTHCARE:'/api/temporal/healthcare-deadline',

  // Briefing & News
  BRIEFING:           '/api/briefing',
  NEWS:               '/api/news',

  // Settings
  SETTINGS:           '/api/settings',

  // Audit
  AUDIT:              '/api/audit',
  AUDIT_STATS:        '/api/audit/stats',
  AUDIT_EXPORT:       '/api/audit/export',

  // Voice
  VOICE_STREAM:       '/api/voice/stream',
  VOICE_TRANSCRIBE:   '/api/voice/stt',
  VOICE_TTS:          '/api/voice/tts',
  VOICE_TRANSCRIBE_ALIAS: '/api/voice/transcribe',

  // Clipboard
  CLIPBOARD_ANALYZE:  '/api/clipboard/analyze',
  CODE_LOOKUP:        (type, code) => `/api/codes/${type}/${code}`,

  // Cloudflare
  CLOUDFLARE_STATUS:  '/api/cloudflare/status',
  TUNNEL_STATUS:      '/api/cloudflare/tunnel/status',

  // System
  HEALTH:             '/api/health',
  MODELS:             '/api/models',
  VERSION:            '/api/version',

  // Automations
  AUTOMATIONS:        '/api/automations',
  AUTOMATION_ENABLE:  (id) => `/api/automations/${id}/enable`,
  AUTOMATION_DISABLE: (id) => `/api/automations/${id}/disable`,
};

// ---------------------------------------------------------------------------
// Keyboard shortcuts
// ---------------------------------------------------------------------------

export const KEYBOARD_SHORTCUTS = {
  COMMAND_PALETTE: { key: 'k',  modifiers: ['ctrl', 'meta'], label: 'Command Palette' },
  NEW_CHAT:        { key: 'n',  modifiers: ['ctrl', 'meta'], label: 'New Chat' },
  CLOSE_PANEL:     { key: 'Escape', modifiers: [],           label: 'Close Panel' },
  HELP:            { key: '/',  modifiers: ['ctrl', 'meta'], label: 'Help' },
  SEARCH:          { key: 'f',  modifiers: ['ctrl', 'meta'], label: 'Search' },
  TOGGLE_SIDEBAR:  { key: 'b',  modifiers: ['ctrl', 'meta'], label: 'Toggle Sidebar' },
  SEND_MESSAGE:    { key: 'Enter', modifiers: [],             label: 'Send Message' },
  NEWLINE:         { key: 'Enter', modifiers: ['shift'],     label: 'New Line' },
};

// ---------------------------------------------------------------------------
// Default settings
// ---------------------------------------------------------------------------

export const DEFAULT_SETTINGS = {
  theme: 'system',
  model: DEFAULT_MODEL,
  specialist: 'general',
  streamResponses: true,
  showConfidence: true,
  fontSize: 'medium',
  language: 'en',
  autoSave: true,
  maxTokens: 4096,
  temperature: 0.7,
};

// ---------------------------------------------------------------------------
// Feature flags
// ---------------------------------------------------------------------------

export const FEATURE_FLAGS = {
  VOICE_INPUT:            true,
  VOICE_STREAM:          true,
  OFFLINE_MODE:          true,
  PWA:                   true,
  CODE_EXECUTION:        false,
  FILE_UPLOAD:           true,
  MULTI_MODEL_COMPARE:   false,
  HEALTHCARE_DASHBOARD:  true,
  CLAIM_ANALYZER:        true,
  CONVERSATION_EXPORT:   true,
  MEMORY_SEARCH:         true,
  SKILLS_MARKETPLACE:    false,
};

// ---------------------------------------------------------------------------
// UI constants
// ---------------------------------------------------------------------------

export const MAX_MESSAGE_LENGTH = 32000;
export const MAX_FILE_SIZE_MB = 10;
export const DEBOUNCE_MS = 300;
export const TOAST_DURATION_MS = 5000;
export const ANIMATION_DURATION_MS = 200;

export const CONFIDENCE_THRESHOLDS = {
  HIGH:   0.85,
  MEDIUM: 0.60,
  LOW:    0,
};

export const CONFIDENCE_LABELS = {
  HIGH:   'High',
  MEDIUM: 'Medium',
  LOW:    'Low',
};