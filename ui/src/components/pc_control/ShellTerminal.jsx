/**
 * Aethera AI — Shell Terminal
 * Execute PowerShell/CMD commands with safety confirmations.
 */
import { useState } from 'react';

export default function ShellTerminal({ pc }) {
  const [command, setCommand] = useState('');
  const [output, setOutput] = useState([]);
  const [shell, setShell] = useState('powershell');
  const [loading, setLoading] = useState(false);

  const execute = async () => {
    if (!command.trim()) return;
    setLoading(true);
    const entry = { type: 'input', command, shell, timestamp: new Date().toISOString() };
    setOutput(prev => [...prev, entry]);

    const result = await pc.sendCommand('shell.execute', { command, shell });
    setOutput(prev => [...prev, {
      type: 'output',
      success: result?.success,
      stdout: result?.data?.stdout || '',
      stderr: result?.data?.stderr || result?.error || '',
      returncode: result?.data?.returncode,
    }]);
    setCommand('');
    setLoading(false);
  };

  return (
    <div className="space-y-4 h-full flex flex-col">
      <div className="flex gap-2 items-center">
        <select value={shell} onChange={(e) => setShell(e.target.value)}
          className="px-2 py-1.5 bg-[var(--color-tertiary)] border border-[var(--color-border)] rounded-lg
            text-xs text-[var(--color-text-primary)]">
          <option value="powershell">PowerShell</option>
          <option value="cmd">CMD</option>
        </select>
        <span className="text-xs text-[var(--color-text-secondary)]">
          Commands requiring destructive actions will need confirmation.
        </span>
      </div>

      {/* Output area */}
      <div className="flex-1 bg-[#0d1117] rounded-lg border border-[var(--color-border)] p-3 overflow-auto font-mono text-xs">
        {output.length === 0 ? (
          <div className="text-gray-500">Ready. Type a command and press Enter.</div>
        ) : (
          output.map((entry, i) => (
            <div key={i} className="mb-2">
              {entry.type === 'input' ? (
                <div className="text-cyan-400">
                  <span className="text-gray-500">[{entry.shell}]</span> {entry.command}
                </div>
              ) : (
                <div>
                  {entry.stdout && (
                    <pre className="text-green-400 whitespace-pre-wrap">{entry.stdout}</pre>
                  )}
                  {entry.stderr && (
                    <pre className="text-red-400 whitespace-pre-wrap">{entry.stderr}</pre>
                  )}
                  <div className="text-gray-500 text-[10px]">
                    Exit code: {entry.returncode ?? 'N/A'}
                  </div>
                </div>
              )}
            </div>
          ))
        )}
        {loading && <div className="text-yellow-400 animate-pulse">Executing...</div>}
      </div>

      {/* Input */}
      <div className="flex gap-2">
        <input
          type="text"
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && execute()}
          placeholder="Enter command..."
          disabled={loading}
          className="flex-1 px-3 py-2 bg-[#0d1117] border border-[var(--color-border)] rounded-lg
            text-sm text-green-400 font-mono placeholder:text-gray-600"
        />
        <button onClick={execute} disabled={loading || !command}
          className="px-4 py-2 bg-cyan-500/20 text-cyan-400 rounded-lg text-sm font-medium
            hover:bg-cyan-500/30 transition-colors disabled:opacity-50">
          Run
        </button>
        <button onClick={() => setOutput([])}
          className="px-3 py-2 bg-[var(--color-tertiary)] text-[var(--color-text-secondary)] rounded-lg text-sm
            hover:text-[var(--color-text-primary)] transition-colors">
          Clear
        </button>
      </div>
    </div>
  );
}