/**
 * Aethera AI — Clipboard Panel
 * Read from and write to the system clipboard.
 */
import { useState } from 'react';

export default function ClipboardPanel({ pc }) {
  const [clipboardContent, setClipboardContent] = useState('');
  const [writeContent, setWriteContent] = useState('');
  const [loading, setLoading] = useState(false);

  const readClipboard = async () => {
    setLoading(true);
    const result = await pc.sendCommand('clipboard.read', {});
    if (result?.success) {
      setClipboardContent(result.data.content || '');
    }
    setLoading(false);
  };

  const writeClipboard = async () => {
    if (!writeContent) return;
    setLoading(true);
    await pc.sendCommand('clipboard.write', { content: writeContent });
    setWriteContent('');
    setLoading(false);
  };

  return (
    <div className="space-y-4">
      {/* Read clipboard */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-medium text-[var(--color-text-secondary)]">Clipboard Content</h4>
          <button onClick={readClipboard} disabled={loading}
            className="px-3 py-1 text-xs bg-cyan-500/20 text-cyan-400 rounded-lg font-medium
              hover:bg-cyan-500/30 transition-colors disabled:opacity-50">
            {loading ? 'Reading...' : 'Read Clipboard'}
          </button>
        </div>
        <div className="bg-[var(--color-tertiary)] rounded-lg border border-[var(--color-border)] p-3 min-h-[80px]">
          {clipboardContent ? (
            <pre className="text-xs text-[var(--color-text-primary)] whitespace-pre-wrap break-all">{clipboardContent}</pre>
          ) : (
            <span className="text-xs text-[var(--color-text-secondary)]">Click "Read Clipboard" to get current content</span>
          )}
        </div>
        {clipboardContent && (
          <button onClick={() => navigator.clipboard.writeText(clipboardContent)}
            className="mt-2 text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors">
            Copy to browser clipboard
          </button>
        )}
      </div>

      {/* Write to clipboard */}
      <div>
        <h4 className="text-sm font-medium text-[var(--color-text-secondary)] mb-2">Write to Clipboard</h4>
        <textarea
          value={writeContent}
          onChange={(e) => setWriteContent(e.target.value)}
          placeholder="Enter text to copy to clipboard..."
          className="w-full h-24 px-3 py-2 bg-[var(--color-tertiary)] border border-[var(--color-border)] rounded-lg
            text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-secondary)] resize-none"
        />
        <div className="flex justify-end mt-2">
          <button onClick={writeClipboard} disabled={loading || !writeContent}
            className="px-4 py-1.5 bg-emerald-500/20 text-emerald-400 rounded-lg text-sm font-medium
              hover:bg-emerald-500/30 transition-colors disabled:opacity-50">
            Write
          </button>
        </div>
      </div>
    </div>
  );
}