/**
 * Aethera AI — Browser Automation Panel
 * Playwright-based web navigation and data extraction.
 */
import { useState } from 'react';

export default function BrowserAutomation({ pc }) {
  const [url, setUrl] = useState('https://');
  const [pageContent, setPageContent] = useState(null);
  const [loading, setLoading] = useState(false);
  const [extractSelectors, setExtractSelectors] = useState('');

  const navigate = async () => {
    if (!url || url === 'https://') return;
    setLoading(true);
    const result = await pc.sendCommand('browser.navigate', { url });
    if (result?.success) setPageContent(result.data);
    setLoading(false);
  };

  const extract = async () => {
    if (!url || url === 'https://') return;
    const selectors = {};
    if (extractSelectors) {
      extractSelectors.split(',').forEach(s => {
        const [name, sel] = s.trim().split('=');
        if (name && sel) selectors[name.trim()] = sel.trim();
      });
    }
    setLoading(true);
    const result = await pc.sendCommand('browser.extract', { url, selectors });
    if (result?.success) setPageContent(result.data);
    setLoading(false);
  };

  const screenshot = async () => {
    if (!url || url === 'https://') return;
    setLoading(true);
    const result = await pc.sendCommand('browser.screenshot', { url });
    if (result?.success) setPageContent(result.data);
    setLoading(false);
  };

  return (
    <div className="space-y-4">
      {/* URL bar */}
      <div className="flex gap-2">
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && navigate()}
          placeholder="Enter URL..."
          className="flex-1 px-3 py-2 bg-[var(--color-tertiary)] border border-[var(--color-border)] rounded-lg
            text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-secondary)]"
        />
        <button onClick={navigate} disabled={loading}
          className="px-4 py-2 bg-cyan-500/20 text-cyan-400 rounded-lg text-sm font-medium
            hover:bg-cyan-500/30 transition-colors disabled:opacity-50">
          Go
        </button>
        <button onClick={screenshot} disabled={loading}
          className="px-4 py-2 bg-yellow-500/20 text-yellow-400 rounded-lg text-sm font-medium
            hover:bg-yellow-500/30 transition-colors disabled:opacity-50">
          📸
        </button>
      </div>

      {/* Extract selectors */}
      <div className="flex gap-2">
        <input
          type="text"
          value={extractSelectors}
          onChange={(e) => setExtractSelectors(e.target.value)}
          placeholder="CSS selectors: title=h1, links=a[href]"
          className="flex-1 px-3 py-1.5 bg-[var(--color-tertiary)] border border-[var(--color-border)] rounded-lg
            text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-secondary)]"
        />
        <button onClick={extract} disabled={loading}
          className="px-3 py-1.5 bg-emerald-500/20 text-emerald-400 rounded-lg text-xs font-medium
            hover:bg-emerald-500/30 transition-colors disabled:opacity-50">
          Extract
        </button>
      </div>

      {/* Results */}
      {pageContent && (
        <div className="bg-[var(--color-tertiary)] rounded-lg border border-[var(--color-border)] p-3">
          {pageContent.title && (
            <div className="text-sm font-medium text-[var(--color-text-primary)] mb-2">
              {pageContent.title}
            </div>
          )}
          {pageContent.url && (
            <div className="text-xs text-[var(--color-text-secondary)] mb-2 font-mono">{pageContent.url}</div>
          )}
          {pageContent.base64 && (
            <img src={`data:image/png;base64,${pageContent.base64}`} alt="Browser" className="w-full rounded" />
          )}
          {pageContent.extracted && Object.keys(pageContent.extracted).length > 0 && (
            <div className="mt-2">
              <div className="text-xs font-medium text-[var(--color-text-secondary)] mb-1">Extracted Data:</div>
              <pre className="text-xs text-[var(--color-text-primary)] overflow-auto max-h-64">
                {JSON.stringify(pageContent.extracted, null, 2)}
              </pre>
            </div>
          )}
          {pageContent.full_text && !pageContent.base64 && (
            <pre className="text-xs text-[var(--color-text-primary)] overflow-auto max-h-64 whitespace-pre-wrap">
              {pageContent.full_text?.slice(0, 5000)}
            </pre>
          )}
        </div>
      )}

      {loading && (
        <div className="text-center py-4 text-[var(--color-text-secondary)] text-sm animate-pulse">
          Loading page...
        </div>
      )}
    </div>
  );
}