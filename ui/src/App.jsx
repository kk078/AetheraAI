import React, { useState, useEffect } from 'react';
import api from './utils/api';
import ChatInterface from './components/chat/ChatInterface';
import HealthcareDashboard from './components/dashboards/HealthcareDashboard';
import FinanceDashboard from './components/dashboards/FinanceDashboard';
import SystemDashboard from './components/dashboards/SystemDashboard';
import AlertsFeed from './components/dashboards/AlertsFeed';
import ActionQueue from './components/dashboards/ActionQueue';
import ClaimAnalyzer from './components/healthcare/ClaimAnalyzer';
import CodeLookup from './components/healthcare/CodeLookup';
import AppealsWorkflow from './components/healthcare/AppealsWorkflow';
import DenialDashboard from './components/healthcare/DenialDashboard';
import FeeSchedule from './components/healthcare/FeeSchedule';
import DrugLookup from './components/healthcare/DrugLookup';
import SkillBrowser from './components/skills/SkillBrowser';
import PluginManager from './components/skills/PluginManager';
import ConnectorPanel from './components/skills/ConnectorPanel';
import AutomationBuilder from './components/skills/AutomationBuilder';
import CoverageChecker from './components/healthcare/CoverageChecker';
import EDIViewer from './components/healthcare/EDIViewer';
import SettingsPanel from './components/settings/SettingsPanel';
import PCControlPanel from './components/pc_control/PCControlPanel';
import Sidebar from './components/common/Sidebar';
import CommandPalette from './components/common/CommandPalette';

// Map of all view keys to their labels for command handling
const VIEW_LABELS = {
  chat: 'Chat',
  dashboard: 'Healthcare Dashboard',
  'finance-dashboard': 'Finance Dashboard',
  'system-dashboard': 'System Dashboard',
  alerts: 'Alerts Feed',
  'action-queue': 'Action Queue',
  'code-lookup': 'Code Lookup',
  'claim-analyzer': 'Claim Analyzer',
  appeals: 'Appeals Workflow',
  'denial-dashboard': 'Denial Dashboard',
  'fee-schedule': 'Fee Schedule',
  'drug-lookup': 'Drug Lookup',
  'coverage-checker': 'Coverage Checker',
  'edi-viewer': 'EDI Viewer',
  skills: 'Skill Browser',
  plugins: 'Plugin Manager',
  connectors: 'Connectors',
  automations: 'Automation Builder',
  'pc-control': 'PC Control',
  conversations: 'Conversations',
  settings: 'Settings',
};

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [currentView, setCurrentView] = useState('chat');

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setCommandPaletteOpen(true);
      }
      if (e.key === 'Escape') {
        setCommandPaletteOpen(false);
      }
    };

    const handleCommand = (e) => {
      const command = e.detail;
      // Support both slash commands and label names for all views
      const slashMap = {
        '/dashboard': 'dashboard',
        '/finance': 'finance-dashboard',
        '/system': 'system-dashboard',
        '/alerts': 'alerts',
        '/actions': 'action-queue',
        '/code': 'code-lookup',
        '/claim': 'claim-analyzer',
        '/appeals': 'appeals',
        '/denial': 'denial-dashboard',
        '/fee': 'fee-schedule',
        '/drug': 'drug-lookup',
        '/coverage': 'coverage-checker',
        '/edi': 'edi-viewer',
        '/skills': 'skills',
        '/plugins': 'plugins',
        '/connectors': 'connectors',
        '/automations': 'automations',
        '/pc': 'pc-control',
        '/chat': 'chat',
        '/conversations': 'conversations',
        '/settings': 'settings',
      };

      // Direct slash-command match
      if (slashMap[command]) {
        setCurrentView(slashMap[command]);
        return;
      }

      // Match by label name (case-insensitive)
      const lowerCmd = command.toLowerCase();
      for (const [key, label] of Object.entries(VIEW_LABELS)) {
        if (lowerCmd === label.toLowerCase() || lowerCmd === key) {
          setCurrentView(key);
          return;
        }
      }

      // Legacy backward-compatible aliases
      if (command === 'Dashboard') setCurrentView('dashboard');
      else if (command === 'New Chat') setCurrentView('chat');
    };

    window.addEventListener('aethera-command', handleCommand);
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('aethera-command', handleCommand);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  const handleViewChange = (view) => {
    setCurrentView(view);
    if (window.innerWidth < 768) {
      setSidebarOpen(false);
    }
  };

  const renderView = () => {
    switch (currentView) {
      case 'dashboard':
        return <HealthcareDashboard />;
      case 'finance-dashboard':
        return <FinanceDashboard />;
      case 'system-dashboard':
        return <SystemDashboard />;
      case 'alerts':
        return <AlertsFeed />;
      case 'action-queue':
        return <ActionQueue />;
      case 'code-lookup':
        return <CodeLookup />;
      case 'claim-analyzer':
        return <ClaimAnalyzer />;
      case 'appeals':
        return <AppealsWorkflow />;
      case 'denial-dashboard':
        return <DenialDashboard />;
      case 'fee-schedule':
        return <FeeSchedule />;
      case 'drug-lookup':
        return <DrugLookup />;
      case 'coverage-checker':
        return <CoverageChecker />;
      case 'edi-viewer':
        return <EDIViewer />;
      case 'skills':
        return <SkillBrowser />;
      case 'plugins':
        return <PluginManager />;
      case 'connectors':
        return <ConnectorPanel />;
      case 'automations':
        return <AutomationBuilder />;
      case 'pc-control':
        return <PCControlPanel />;
      case 'conversations':
        return <ConversationsList onViewChange={setCurrentView} />;
      case 'settings':
        return <SettingsPanel />;
      case 'chat':
      default:
        return <ChatInterface />;
    }
  };

  return (
    <div className="flex h-screen bg-aethera-background">
      <Sidebar
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        currentView={currentView}
        onViewChange={handleViewChange}
      />

      <main className="flex-1 flex flex-col min-w-0">
        <header className="flex items-center justify-between px-4 py-3 border-b border-aethera-border">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 hover:bg-aethera-surface rounded-lg transition-colors"
              aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <h1 className="text-xl font-bold text-aethera-primary">Aethera</h1>
            <span className="text-xs text-aethera-text-secondary bg-aethera-surface px-2 py-0.5 rounded">
              {VIEW_LABELS[currentView] || 'Healthcare AI'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCommandPaletteOpen(true)}
              className="p-2 hover:bg-aethera-surface rounded-lg transition-colors"
              title="Command Palette (Ctrl+K)"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </button>
            <button
              onClick={() => setCurrentView('settings')}
              className="p-2 hover:bg-aethera-surface rounded-lg transition-colors"
              title="Settings"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </button>
          </div>
        </header>

        <div className="flex-1 overflow-auto">{renderView()}</div>
      </main>

      {commandPaletteOpen && <CommandPalette onClose={() => setCommandPaletteOpen(false)} onViewChange={setCurrentView} />}
    </div>
  );
}

/** Conversations list view -- fetches real conversations from the API */
function ConversationsList({ onViewChange }) {
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await api.listConversations();
        const conversations = data.conversations || data || [];
        if (!cancelled) setConversations(conversations);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-aethera-text-secondary">
        <div className="text-center">
          <div className="animate-spin w-10 h-10 border-2 border-aethera-primary border-t-transparent rounded-full mx-auto mb-4" />
          <p>Loading conversations...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full text-aethera-text-secondary">
        <div className="text-center">
          <svg className="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p>Could not load conversations: {error}</p>
          <button onClick={() => onViewChange('chat')} className="mt-4 px-4 py-2 bg-aethera-primary text-white rounded-lg text-sm hover:bg-cyan-600 transition-colors">
            Start a new chat
          </button>
        </div>
      </div>
    );
  }

  if (conversations.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-aethera-text-secondary">
        <div className="text-center">
          <svg className="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          <p>No conversations yet</p>
          <button onClick={() => onViewChange('chat')} className="mt-4 px-4 py-2 bg-aethera-primary text-white rounded-lg text-sm hover:bg-cyan-600 transition-colors">
            Start your first chat
          </button>
        </div>
      </div>
    );
  }

  const formatDate = (ts) => {
    if (!ts) return '';
    const d = new Date(ts);
    const now = new Date();
    const diffMs = now - d;
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHrs = Math.floor(diffMins / 60);
    if (diffHrs < 24) return `${diffHrs}h ago`;
    return d.toLocaleDateString();
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-aethera-foreground">Conversations</h1>
        <button
          onClick={() => onViewChange('chat')}
          className="px-4 py-2 bg-aethera-primary text-white rounded-lg text-sm font-medium hover:bg-cyan-600 transition-colors"
        >
          New Chat
        </button>
      </div>
      <div className="space-y-2">
        {conversations.map((conv) => (
          <button
            key={conv.id || conv.conversation_id}
            onClick={() => {
              window.dispatchEvent(new CustomEvent('aethera-load-conversation', { detail: conv.id || conv.conversation_id }));
              onViewChange('chat');
            }}
            className="w-full text-left p-4 bg-aethera-surface rounded-xl border border-aethera-border hover:border-aethera-primary/50 transition-colors"
          >
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-aethera-foreground truncate">
                {conv.title || conv.first_message || `Conversation ${(conv.id || conv.conversation_id || '').slice(0, 8)}`}
              </p>
              <span className="text-xs text-aethera-text-secondary ml-3 flex-shrink-0">
                {formatDate(conv.updated_at || conv.created_at)}
              </span>
            </div>
            {conv.specialist && (
              <span className="inline-block mt-1 text-xs bg-aethera-primary/20 text-aethera-primary px-2 py-0.5 rounded">
                {conv.specialist}
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

export default App;