/**
 * Aethera AI — PC Control Panel
 * Main panel with tabs for each PC control capability.
 */
import { useState } from 'react';
import { usePCControl } from '../../hooks/usePCControl';
import ConfirmationDialog from './ConfirmationDialog';
import FileSystemBrowser from './FileSystemBrowser';
import AppLauncher from './AppLauncher';
import ShellTerminal from './ShellTerminal';
import ScreenViewer from './ScreenViewer';
import ClipboardPanel from './ClipboardPanel';
import SystemStats from './SystemStats';
import BrowserAutomation from './BrowserAutomation';

const TABS = [
  { id: 'system', label: 'System', icon: '📊' },
  { id: 'files', label: 'Files', icon: '📁' },
  { id: 'apps', label: 'Apps', icon: '🚀' },
  { id: 'shell', label: 'Shell', icon: '💻' },
  { id: 'screen', label: 'Screen', icon: '🖼️' },
  { id: 'clipboard', label: 'Clipboard', icon: '📋' },
  { id: 'browser', label: 'Browser', icon: '🌐' },
];

export default function PCControlPanel() {
  const [activeTab, setActiveTab] = useState('system');
  const pc = usePCControl();
  const { agentStatus, confirmations, loading, error } = pc;
  const isConnected = agentStatus?.total_agents > 0;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
        <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">PC Control</h2>
        <div className="flex items-center gap-3">
          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
            isConnected ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
          }`}>
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400' : 'bg-red-400'}`} />
            {isConnected ? 'Agent Connected' : 'No Agent'}
          </span>
        </div>
      </div>

      {/* Confirmation dialogs */}
      {confirmations.map(conf => (
        <ConfirmationDialog
          key={conf.command_id}
          confirmation={conf}
          onConfirm={() => pc.confirmAction(conf.command_id, true)}
          onDeny={() => pc.confirmAction(conf.command_id, false)}
          onDismiss={() => pc.dismissConfirmation(conf.command_id)}
        />
      ))}

      {/* Error banner */}
      {error && (
        <div className="mx-4 mt-2 px-3 py-2 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Tab bar */}
      <div className="flex border-b border-[var(--color-border)] overflow-x-auto">
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-cyan-400 text-cyan-400'
                : 'border-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
            }`}
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-auto p-4">
        {!isConnected ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="text-4xl mb-4">🔌</div>
            <h3 className="text-lg font-semibold text-[var(--color-text-primary)] mb-2">
              No Host Agent Connected
            </h3>
            <p className="text-[var(--color-text-secondary)] text-sm max-w-md">
              Start the host agent on your PC to enable PC control features.
              Run: <code className="px-1.5 py-0.5 bg-[var(--color-tertiary)] rounded text-xs">
              python -m host_agent.agent
            </code>
            </p>
          </div>
        ) : (
          <>
            {activeTab === 'system' && <SystemStats pc={pc} />}
            {activeTab === 'files' && <FileSystemBrowser pc={pc} />}
            {activeTab === 'apps' && <AppLauncher pc={pc} />}
            {activeTab === 'shell' && <ShellTerminal pc={pc} />}
            {activeTab === 'screen' && <ScreenViewer pc={pc} />}
            {activeTab === 'clipboard' && <ClipboardPanel pc={pc} />}
            {activeTab === 'browser' && <BrowserAutomation pc={pc} />}
          </>
        )}
      </div>
    </div>
  );
}