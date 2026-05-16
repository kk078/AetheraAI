import React, { useState, useEffect } from 'react';

const commands = [
  { category: 'Navigation', items: [
    { label: 'New Chat', shortcut: 'Ctrl+N', view: 'chat' },
    { label: 'Conversations', shortcut: '', view: 'conversations' },
    { label: 'Settings', shortcut: '', view: 'settings' },
  ]},
  { category: 'Dashboards', items: [
    { label: 'Healthcare Dashboard', shortcut: '', view: 'dashboard' },
    { label: 'Finance Dashboard', shortcut: '', view: 'finance-dashboard' },
    { label: 'System Dashboard', shortcut: '', view: 'system-dashboard' },
    { label: 'Alerts Feed', shortcut: '', view: 'alerts' },
    { label: 'Action Queue', shortcut: '', view: 'action-queue' },
  ]},
  { category: 'Healthcare Tools', items: [
    { label: 'Claim Analyzer', shortcut: '', view: 'claim-analyzer' },
    { label: 'Code Lookup', shortcut: '', view: 'code-lookup' },
    { label: 'Appeals Workflow', shortcut: '', view: 'appeals' },
    { label: 'Denial Dashboard', shortcut: '', view: 'denial-dashboard' },
    { label: 'Fee Schedule', shortcut: '', view: 'fee-schedule' },
    { label: 'Drug Lookup', shortcut: '', view: 'drug-lookup' },
    { label: 'Coverage Checker', shortcut: '', view: 'coverage-checker' },
    { label: 'EDI Viewer', shortcut: '', view: 'edi-viewer' },
  ]},
  { category: 'Extensions', items: [
    { label: 'Skill Browser', shortcut: '', view: 'skills' },
    { label: 'Plugin Manager', shortcut: '', view: 'plugins' },
    { label: 'Connectors', shortcut: '', view: 'connectors' },
    { label: 'Automation Builder', shortcut: '', view: 'automations' },
  ]},
  { category: 'Specialists', items: [
    { label: 'Provider Ops', shortcut: '', specialist: 'healthcare_provider' },
    { label: 'Payer Ops', shortcut: '', specialist: 'healthcare_payer' },
    { label: 'Clinical', shortcut: '', specialist: 'healthcare_clinical' },
    { label: 'Regulatory', shortcut: '', specialist: 'healthcare_regulatory' },
    { label: 'Finance', shortcut: '', specialist: 'finance' },
    { label: 'Legal', shortcut: '', specialist: 'legal' },
  ]},
  { category: 'Chat Commands', items: [
    { label: '/code -- Search codes', shortcut: '', command: '/code' },
    { label: '/denial -- Denial analysis', shortcut: '', command: '/denial' },
    { label: '/fee -- Fee schedule', shortcut: '', command: '/fee' },
    { label: '/drug -- Drug lookup', shortcut: '', command: '/drug' },
    { label: '/npi -- NPI lookup', shortcut: '', command: '/npi' },
    { label: '/coverage -- Coverage check', shortcut: '', command: '/coverage' },
    { label: '/edi -- EDI parse', shortcut: '', command: '/edi' },
  ]},
];

export default function CommandPalette({ onClose, onViewChange }) {
  const [search, setSearch] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);

  const filteredCommands = commands
    .flatMap((cat) => cat.items.map((item) => ({ ...item, category: cat.category })))
    .filter((item) =>
      item.label.toLowerCase().includes(search.toLowerCase())
    );

  useEffect(() => {
    setSelectedIndex(0);
  }, [search]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, filteredCommands.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const cmd = filteredCommands[selectedIndex];
        if (cmd) {
          executeCommand(cmd);
          onClose();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedIndex, filteredCommands, onClose]);

  const executeCommand = (cmd) => {
    if (cmd.view && onViewChange) {
      onViewChange(cmd.view);
    } else if (cmd.command) {
      // Dispatch custom event for chat input
      window.dispatchEvent(new CustomEvent('aethera-command', { detail: cmd.command }));
      // Also switch to chat view so the command is visible
      if (onViewChange) onViewChange('chat');
    } else if (cmd.specialist) {
      window.dispatchEvent(new CustomEvent('aethera-specialist', { detail: cmd.specialist }));
      if (onViewChange) onViewChange('chat');
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-start justify-center pt-[20vh]" onClick={onClose} role="dialog" aria-modal="true" aria-label="Command palette">
      <div
        className="w-full max-w-xl bg-aethera-surface rounded-xl shadow-2xl overflow-hidden border border-aethera-border"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search */}
        <div className="p-4 border-b border-aethera-border">
          <input
            type="text"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setSelectedIndex(0); }}
            placeholder="Type a command or search..."
            autoFocus
            aria-label="Search commands"
            className="w-full bg-transparent border-none outline-none text-aethera-foreground placeholder-aethera-text-secondary"
          />
        </div>

        {/* Results */}
        <div className="max-h-[400px] overflow-y-auto p-2">
          {filteredCommands.length === 0 ? (
            <div className="p-4 text-center text-aethera-text-secondary">
              No commands found
            </div>
          ) : (
            filteredCommands.map((cmd, index) => (
              <button
                key={`${cmd.category}-${cmd.label}`}
                onClick={() => { executeCommand(cmd); onClose(); }}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-left transition-colors ${
                  index === selectedIndex
                    ? 'bg-aethera-primary/20 text-aethera-foreground'
                    : 'hover:bg-aethera-tertiary text-aethera-text-secondary'
                }`}
              >
                <div>
                  <div className="text-sm font-medium">{cmd.label}</div>
                  <div className="text-xs text-aethera-text-secondary">{cmd.category}</div>
                </div>
                {cmd.shortcut && (
                  <span className="text-xs text-aethera-text-secondary bg-aethera-tertiary px-1.5 py-0.5 rounded">
                    {cmd.shortcut}
                  </span>
                )}
              </button>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-aethera-border flex justify-between text-xs text-aethera-text-secondary">
          <span>Up/Down to navigate</span>
          <span>Enter to select</span>
          <span>Esc to close</span>
        </div>
      </div>
    </div>
  );
}