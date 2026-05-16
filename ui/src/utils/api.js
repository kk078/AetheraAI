const API_BASE = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE || 'http://localhost:8000';

class ApiClient {
  constructor(baseURL) {
    this.baseURL = baseURL;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    };

    const response = await fetch(url, config);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response;
  }

  async get(endpoint) {
    return this.request(endpoint, { method: 'GET' });
  }

  async post(endpoint, data) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async del(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  }

  // Streaming chat with SSE
  async *streamChat(message, options = {}) {
    const response = await this.request('/api/chat/stream', {
      method: 'POST',
      body: JSON.stringify({ message, ...options }),
      signal: options.signal,
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') continue;
          try {
            yield JSON.parse(data);
          } catch (e) {
            console.warn('Failed to parse SSE data:', data);
          }
        }
      }
    }
  }

  // Chat
  async chat(message, options = {}) {
    const response = await this.post('/api/chat', { message, ...options });
    return response.json();
  }

  async chatWithSpecialist(specialistName, message, options = {}) {
    const response = await this.post(`/api/chat/specialist/${specialistName}`, { message, ...options });
    return response.json();
  }

  async chatMultiAgent(message, options = {}) {
    const response = await this.post('/api/chat/multi-agent', { message, ...options });
    return response.json();
  }

  // Conversations
  async listConversations(limit = 50, offset = 0) {
    const response = await this.get(`/api/conversations?limit=${limit}&offset=${offset}`);
    return response.json();
  }

  async getConversation(conversationId) {
    const response = await this.get(`/api/conversations/${conversationId}`);
    return response.json();
  }

  async deleteConversation(conversationId) {
    const response = await this.del(`/api/conversations/${conversationId}`);
    return response.json();
  }

  // File upload
  async uploadFile(file, onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', `${this.baseURL}/api/upload`);

      if (onProgress) {
        xhr.upload.addEventListener('progress', (e) => {
          if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100));
        });
      }

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try { resolve(JSON.parse(xhr.responseText)); }
          catch { resolve({ url: xhr.responseText }); }
        } else {
          reject(new Error(`Upload failed: HTTP ${xhr.status}`));
        }
      });
      xhr.addEventListener('error', () => reject(new Error('Network error during upload')));

      const formData = new FormData();
      formData.append('file', file);
      xhr.send(formData);
    });
  }

  // Specialists
  async getSpecialists() {
    const response = await this.get('/api/specialists');
    return response.json();
  }

  async querySpecialist(specialist, query, options = {}) {
    const response = await this.post(`/api/specialists/${specialist}/query`, {
      query,
      ...options,
    });
    return response.json();
  }

  // Healthcare Tools
  async lookupHealthcareCode(code, codeType) {
    const response = await this.post('/api/healthcare/code-lookup', { code, codeType });
    return response.json();
  }

  async searchCodes(search, codeType) {
    const response = await this.post('/api/healthcare/code-search', { search, codeType });
    return response.json();
  }

  async analyzeDenial(carCode, rarcCode) {
    const response = await this.post('/api/healthcare/denial-analyze', { car_code: carCode, rarc_code: rarcCode });
    return response.json();
  }

  async predictDenial(claimData) {
    const response = await this.post('/api/healthcare/denial-predict', claimData);
    return response.json();
  }

  async generateAppeal(denialInfo) {
    const response = await this.post('/api/healthcare/appeal-generate', denialInfo);
    return response.json();
  }

  async getFeeSchedule(cptCode, payerId) {
    const response = await this.post('/api/healthcare/fee-schedule', { cptCode, payerId });
    return response.json();
  }

  async checkNPI(npi) {
    const response = await this.post('/api/healthcare/npi-lookup', { npi });
    return response.json();
  }

  async analyzeClaim(claimId) {
    const response = await this.post('/api/healthcare/claim-analysis', { claimId });
    return response.json();
  }

  async checkCCI(codes) {
    const response = await this.post('/api/healthcare/cci-check', { codes });
    return response.json();
  }

  async checkCoverage(code, payer) {
    const response = await this.post('/api/healthcare/coverage', { code, payer });
    return response.json();
  }

  async groupDRG(claimData) {
    const response = await this.post('/api/healthcare/drg-group', claimData);
    return response.json();
  }

  async lookupDrug(drugName) {
    const response = await this.post('/api/healthcare/drug-lookup', { drug_name: drugName });
    return response.json();
  }

  async riskAdjust(patientData) {
    const response = await this.post('/api/healthcare/risk-adjust', patientData);
    return response.json();
  }

  async calculateMedical(params) {
    const response = await this.post('/api/healthcare/medical-calc', params);
    return response.json();
  }

  async parseEDI(transactionSet, controlNumber) {
    const response = await this.post('/api/healthcare/edi-parse', { transaction_set: transactionSet, control_number: controlNumber });
    return response.json();
  }

  // Skills
  async executeSkill(skillName, parameters) {
    const response = await this.post(`/api/skills/${skillName}/execute`, parameters);
    return response.json();
  }

  async getSkills() {
    const response = await this.get('/api/skills');
    return response.json();
  }

  // Plugins
  async getPlugins() {
    const response = await this.get('/api/plugins');
    return response.json();
  }

  async enablePlugin(pluginName) {
    const response = await this.post(`/api/plugins/${pluginName}/enable`, {});
    return response.json();
  }

  async disablePlugin(pluginName) {
    const response = await this.post(`/api/plugins/${pluginName}/disable`, {});
    return response.json();
  }

  async configurePlugin(pluginName, config) {
    const response = await this.post(`/api/plugins/${pluginName}/config`, config);
    return response.json();
  }

  // Connectors
  async getConnectors() {
    const response = await this.get('/api/connectors');
    return response.json();
  }

  async connectConnector(connectorName) {
    const response = await this.post(`/api/connectors/${connectorName}/connect`, {});
    return response.json();
  }

  async disconnectConnector(connectorName) {
    const response = await this.post(`/api/connectors/${connectorName}/disconnect`, {});
    return response.json();
  }

  async testConnector(connectorName) {
    const response = await this.post(`/api/connectors/${connectorName}/test`, {});
    return response.json();
  }

  // Memory — Profile
  async getMemoryProfile(userId = 'default_user') {
    const response = await this.get(`/api/memory/profile/${userId}`);
    return response.json();
  }

  async updateMemoryProfile(userId, updates) {
    const response = await this.post(`/api/memory/profile/${userId}`, updates);
    return response.json();
  }

  // Memory — Search & Knowledge Graph
  async searchMemory(query, collection = 'user_memories', topK = 10) {
    const params = new URLSearchParams({ query, collection, top_k: String(topK) });
    const response = await this.get(`/api/memory/search?${params}`);
    return response.json();
  }

  async getKnowledgeGraph(entityType, limit = 50) {
    const params = new URLSearchParams({ limit: String(limit) });
    if (entityType) params.set('entity_type', entityType);
    const response = await this.get(`/api/memory/knowledge-graph?${params}`);
    return response.json();
  }

  async forgetMemory(topic) {
    const response = await this.post('/api/memory/forget', { topic });
    return response.json();
  }

  // Memory — Facts
  async storeFact(fact) {
    const response = await this.post('/api/memory/facts', fact);
    return response.json();
  }

  async searchFacts(query, { category, minConfidence, limit } = {}) {
    const params = new URLSearchParams({ query, limit: String(limit || 20) });
    if (category) params.set('category', category);
    if (minConfidence) params.set('min_confidence', String(minConfidence));
    const response = await this.get(`/api/memory/facts?${params}`);
    return response.json();
  }

  async getFactStats() {
    const response = await this.get('/api/memory/facts/stats');
    return response.json();
  }

  async findContradictions() {
    const response = await this.post('/api/memory/facts/contradictions', {});
    return response.json();
  }

  async expireOutdatedFacts(dryRun = true) {
    const response = await this.post('/api/memory/facts/expire-outdated', { dry_run: dryRun });
    return response.json();
  }

  // Memory — Learning
  async getLearningPreferences(userId = 'default_user') {
    const response = await this.get(`/api/memory/learning/preferences/${userId}`);
    return response.json();
  }

  async recordInteraction(interaction) {
    const response = await this.post('/api/memory/learning/interactions', interaction);
    return response.json();
  }

  async predictPreferences(userId = 'default_user') {
    const response = await this.get(`/api/memory/learning/predict/${userId}`);
    return response.json();
  }

  async getLearningStats() {
    const response = await this.get('/api/memory/learning/stats');
    return response.json();
  }

  // Memory — Knowledge Gaps
  async getKnowledgeGaps() {
    const response = await this.get('/api/memory/knowledge-gaps');
    return response.json();
  }

  async detectKnowledgeGaps(context) {
    const response = await this.post('/api/memory/knowledge-gaps/detect', { context });
    return response.json();
  }

  async researchKnowledgeGap(gapId) {
    const response = await this.post(`/api/memory/knowledge-gaps/${gapId}/research`, {});
    return response.json();
  }

  async fillKnowledgeGap(gapId, content) {
    const response = await this.post(`/api/memory/knowledge-gaps/${gapId}/fill`, { content });
    return response.json();
  }

  async getKnowledgeGapStats() {
    const response = await this.get('/api/memory/knowledge-gaps/stats');
    return response.json();
  }

  // Memory — Health Records
  async getHealthRecords(userId = 'default_user') {
    const response = await this.get(`/api/memory/health-records/${userId}`);
    return response.json();
  }

  async addHealthRecord(record) {
    const response = await this.post('/api/memory/health-records', record);
    return response.json();
  }

  async getHealthRecordTimeline(userId = 'default_user') {
    const response = await this.get(`/api/memory/health-records/${userId}/timeline`);
    return response.json();
  }

  async exportDeidentifiedRecords(userId = 'default_user') {
    const response = await this.get(`/api/memory/health-records/${userId}/export-deidentified`);
    return response.json();
  }

  // Memory — Consolidation
  async consolidateMemories(options = {}) {
    const response = await this.post('/api/memory/consolidate', options);
    return response.json();
  }

  // Dashboard, Alerts, Queue
  async getDashboard() {
    const response = await this.get('/api/dashboard');
    return response.json();
  }

  // Temporal — Deadlines & Time-Sensitive Items
  async getUpcomingDeadlines(days = 7) {
    const response = await this.get(`/api/temporal/upcoming?days=${days}`);
    return response.json();
  }

  async getOverdueDeadlines() {
    const response = await this.get('/api/temporal/overdue');
    return response.json();
  }

  async createTemporalItem(item) {
    const response = await this.post('/api/temporal/items', item);
    return response.json();
  }

  async extractDeadlines(text) {
    const response = await this.post('/api/temporal/extract', { text });
    return response.json();
  }

  async getHealthcareDeadline(eventType, eventDate) {
    const params = new URLSearchParams({ event_type: eventType });
    if (eventDate) params.set('event_date', eventDate);
    const response = await this.get(`/api/temporal/healthcare-deadline?${params}`);
    return response.json();
  }

  async completeTemporalItem(itemId) {
    const response = await this.post(`/api/temporal/items/${itemId}/complete`, {});
    return response.json();
  }

  async deleteTemporalItem(itemId) {
    const response = await this.del(`/api/temporal/items/${itemId}`);
    return response.json();
  }

  // Proactive — Alerts, Action Queue, Automations
  async getAlerts(activeOnly = true) {
    const response = await this.get(`/api/alerts?active_only=${activeOnly}`);
    return response.json();
  }

  async acknowledgeAlert(alertId) {
    const response = await this.post(`/api/alerts/${alertId}/acknowledge`, {});
    return response.json();
  }

  async getActionQueue() {
    const response = await this.get('/api/queue');
    return response.json();
  }

  async completeActionItem(itemId) {
    const response = await this.post(`/api/queue/${itemId}/complete`, {});
    return response.json();
  }

  async addActionItem(item) {
    const response = await this.post('/api/queue', item);
    return response.json();
  }

  async getQueueStats() {
    const response = await this.get('/api/queue/stats');
    return response.json();
  }

  async getAutomations() {
    const response = await this.get('/api/automations');
    return response.json();
  }

  async createAutomation(description) {
    const response = await this.post('/api/automations', { description });
    return response.json();
  }

  async deleteAutomation(automationId) {
    const response = await this.del(`/api/automations/${automationId}`);
    return response.json();
  }

  async enableAutomation(automationId) {
    const response = await this.post(`/api/automations/${automationId}/enable`, {});
    return response.json();
  }

  async disableAutomation(automationId) {
    const response = await this.post(`/api/automations/${automationId}/disable`, {});
    return response.json();
  }

  // Briefing & News
  async getBriefing() {
    const response = await this.get('/api/briefing');
    return response.json();
  }

  async getNews(limit = 10) {
    const response = await this.get(`/api/news?limit=${limit}`);
    return response.json();
  }

  // Settings
  async getSettings() {
    const response = await this.get('/api/settings');
    return response.json();
  }

  async updateSettings(settings) {
    const response = await this.post('/api/settings', settings);
    return response.json();
  }

  // Audit
  async getAuditLog(params = {}) {
    const query = new URLSearchParams(params).toString();
    const response = await this.get(`/api/audit${query ? '?' + query : ''}`);
    return response.json();
  }

  async getAuditStats() {
    const response = await this.get('/api/audit/stats');
    return response.json();
  }

  async exportAudit(format = 'json') {
    const response = await this.post('/api/audit/export', { format });
    return response.json();
  }

  // Voice
  async transcribeAudio(audioBlob, filename = 'recording.webm') {
    const formData = new FormData();
    formData.append('audio', audioBlob, filename);
    const response = await this.request('/api/voice/stt', {
      method: 'POST',
      body: formData,
      headers: {}, // Let browser set Content-Type for FormData
    });
    return response.json();
  }

  async synthesizeSpeech(text, voice = 'default') {
    const response = await this.request('/api/voice/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `text=${encodeURIComponent(text)}&voice=${encodeURIComponent(voice)}`,
    });
    return response.json();
  }

  // Clipboard
  async analyzeClipboard(text) {
    const formData = new FormData();
    formData.append('text', text);
    const response = await this.request('/api/clipboard/analyze', {
      method: 'POST',
      body: formData,
      headers: {},
    });
    return response.json();
  }

  async lookupCode(codeType, code) {
    const response = await this.get(`/api/codes/${codeType}/${encodeURIComponent(code)}`);
    return response.json();
  }

  // System
  async getHealth() {
    const response = await this.get('/api/health');
    return response.json();
  }

  async getModels() {
    const response = await this.get('/api/models');
    return response.json();
  }

  async backup() {
    const response = await this.post('/api/backup', {});
    return response.json();
  }

  async listBackups() {
    const response = await this.get('/api/backup/list');
    return response.json();
  }

  async restoreBackup(backupPath) {
    const response = await this.post('/api/backup/restore', { backup_path: backupPath });
    return response.json();
  }

  // Cloudflare
  async getCloudflareStatus() {
    const response = await this.get('/api/cloudflare/status');
    return response.json();
  }

  async getTunnelStatus() {
    const response = await this.get('/api/cloudflare/tunnel/status');
    return response.json();
  }
}

export const api = new ApiClient(API_BASE);
export default api;