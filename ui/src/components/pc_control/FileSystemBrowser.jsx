/**
 * Aethera AI — File System Browser
 * Browse, read, and manage files on the host PC.
 */
import { useState } from 'react';

export default function FileSystemBrowser({ pc }) {
  const [currentPath, setCurrentPath] = useState('');
  const [entries, setEntries] = useState([]);
  const [fileContent, setFileContent] = useState(null);
  const [loading, setLoading] = useState(false);

  const browse = async (path) => {
    setLoading(true);
    const result = await pc.sendCommand('filesystem.browse', { path });
    if (result?.success) {
      setCurrentPath(result.data.path);
      setEntries(result.data.entries || []);
      setFileContent(null);
    }
    setLoading(false);
  };

  const readFile = async (path) => {
    setLoading(true);
    const result = await pc.sendCommand('filesystem.read', { path });
    if (result?.success) {
      setFileContent(result.data);
    }
    setLoading(false);
  };

  return (
    <div className="space-y-4">
      {/* Path bar */}
      <div className="flex gap-2">
        <input
          type="text"
          value={currentPath}
          onChange={(e) => setCurrentPath(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && browse(currentPath)}
          placeholder="C:\Users\..."
          className="flex-1 px-3 py-2 bg-[var(--color-tertiary)] border border-[var(--color-border)] rounded-lg
            text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-secondary)]"
        />
        <button
          onClick={() => browse(currentPath || 'C:\\')}
          disabled={loading}
          className="px-4 py-2 bg-cyan-500/20 text-cyan-400 rounded-lg text-sm font-medium
            hover:bg-cyan-500/30 transition-colors disabled:opacity-50"
        >
          Browse
        </button>
      </div>

      {/* Quick access */}
      <div className="flex gap-2">
        {['C:\\', 'C:\\Users', 'C:\\Program Files'].map(p => (
          <button key={p} onClick={() => browse(p)}
            className="px-3 py-1 text-xs bg-[var(--color-tertiary)] rounded-lg text-[var(--color-text-secondary)]
              hover:text-[var(--color-text-primary)] transition-colors">
            {p}
          </button>
        ))}
      </div>

      {/* File list or content viewer */}
      {fileContent ? (
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-[var(--color-text-secondary)] font-mono">{fileContent.path}</span>
            <button onClick={() => setFileContent(null)}
              className="text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]">
              Back to list
            </button>
          </div>
          <pre className="bg-[var(--color-tertiary)] rounded-lg p-3 text-xs text-[var(--color-text-primary)] overflow-auto max-h-96 font-mono whitespace-pre-wrap">
            {fileContent.content}
          </pre>
        </div>
      ) : (
        <div className="bg-[var(--color-tertiary)] rounded-lg border border-[var(--color-border)] overflow-hidden">
          <div className="grid grid-cols-[auto_1fr_auto_auto] gap-x-3 px-3 py-2 border-b border-[var(--color-border)] text-xs text-[var(--color-text-secondary)] font-medium">
            <span>Type</span><span>Name</span><span>Size</span><span>Modified</span>
          </div>
          {loading ? (
            <div className="py-8 text-center text-[var(--color-text-secondary)] text-sm">Loading...</div>
          ) : entries.length === 0 ? (
            <div className="py-8 text-center text-[var(--color-text-secondary)] text-sm">
              {currentPath ? 'Empty directory' : 'Click Browse to explore files'}
            </div>
          ) : (
            entries.slice(0, 100).map((entry, i) => (
              <div key={i}
                onClick={() => entry.is_dir ? browse(entry.path) : readFile(entry.path)}
                className="grid grid-cols-[auto_1fr_auto_auto] gap-x-3 px-3 py-1.5 text-xs hover:bg-[var(--color-border)]/50 cursor-pointer transition-colors"
              >
                <span>{entry.is_dir ? '📁' : '📄'}</span>
                <span className="text-[var(--color-text-primary)] truncate">{entry.name}</span>
                <span className="text-[var(--color-text-secondary)]">
                  {entry.is_dir ? '—' : entry.size > 1024*1024 ? `${(entry.size/1024/1024).toFixed(1)}M` : entry.size > 1024 ? `${(entry.size/1024).toFixed(1)}K` : `${entry.size}B`}
                </span>
                <span className="text-[var(--color-text-secondary)]">
                  {entry.modified ? new Date(entry.modified * 1000).toLocaleDateString() : '—'}
                </span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}