/**
 * Aethera AI — Application Launcher
 * Open, close, list, and switch applications on the host PC.
 */
import { useState } from 'react';

export default function AppLauncher({ pc }) {
  const [processes, setProcesses] = useState([]);
  const [nameFilter, setNameFilter] = useState('');
  const [loading, setLoading] = useState(false);
  const [appName, setAppName] = useState('');

  const listApps = async () => {
    setLoading(true);
    const result = await pc.sendCommand('app.list', { name_filter: nameFilter });
    if (result?.success) setProcesses(result.data.processes || []);
    setLoading(false);
  };

  const openApp = async () => {
    if (!appName) return;
    await pc.sendCommand('app.open', { name: appName });
    setAppName('');
    setTimeout(listApps, 2000);
  };

  return (
    <div className="space-y-4">
      {/* Open app */}
      <div className="flex gap-2">
        <input
          type="text"
          value={appName}
          onChange={(e) => setAppName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && openApp()}
          placeholder="Application name or path..."
          className="flex-1 px-3 py-2 bg-[var(--color-tertiary)] border border-[var(--color-border)] rounded-lg
            text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-secondary)]"
        />
        <button onClick={openApp} disabled={!appName}
          className="px-4 py-2 bg-emerald-500/20 text-emerald-400 rounded-lg text-sm font-medium
            hover:bg-emerald-500/30 transition-colors disabled:opacity-50">
          Open
        </button>
      </div>

      {/* Process list */}
      <div className="flex items-center justify-between">
        <div className="flex gap-2 items-center">
          <input
            type="text"
            value={nameFilter}
            onChange={(e) => setNameFilter(e.target.value)}
            placeholder="Filter processes..."
            className="px-3 py-1.5 bg-[var(--color-tertiary)] border border-[var(--color-border)] rounded-lg
              text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-secondary)] w-48"
          />
          <button onClick={listApps} disabled={loading}
            className="px-3 py-1.5 text-xs bg-cyan-500/20 text-cyan-400 rounded-lg font-medium
              hover:bg-cyan-500/30 transition-colors disabled:opacity-50">
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>
        <span className="text-xs text-[var(--color-text-secondary)]">
          {processes.length} processes
        </span>
      </div>

      <div className="bg-[var(--color-tertiary)] rounded-lg border border-[var(--color-border)] overflow-hidden">
        <div className="grid grid-cols-[60px_1fr_80px_80px] gap-x-2 px-3 py-2 border-b border-[var(--color-border)] text-xs text-[var(--color-text-secondary)] font-medium">
          <span>PID</span><span>Name</span><span>CPU %</span><span>Mem %</span>
        </div>
        <div className="max-h-80 overflow-auto">
          {processes.map((proc, i) => (
            <div key={i}
              className="grid grid-cols-[60px_1fr_80px_80px] gap-x-2 px-3 py-1 text-xs hover:bg-[var(--color-border)]/50">
              <span className="text-[var(--color-text-secondary)] font-mono">{proc.pid}</span>
              <span className="text-[var(--color-text-primary)] truncate">{proc.name}</span>
              <span className="text-[var(--color-text-secondary)]">{proc.cpu_percent}%</span>
              <span className="text-[var(--color-text-secondary)]">{proc.memory_percent}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}