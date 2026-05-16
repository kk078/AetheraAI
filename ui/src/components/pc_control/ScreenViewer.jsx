/**
 * Aethera AI — Screen Viewer
 * Take screenshots and perform OCR on the host PC.
 */
import { useState } from 'react';

export default function ScreenViewer({ pc }) {
  const [screenshot, setScreenshot] = useState(null);
  const [ocrText, setOcrText] = useState('');
  const [loading, setLoading] = useState(false);

  const capture = async (withOcr = false) => {
    setLoading(true);
    const result = await pc.sendCommand('screen.capture', { include_base64: true, include_ocr: withOcr });
    if (result?.success) {
      setScreenshot(result.data);
      if (result.data.ocr_text) setOcrText(result.data.ocr_text);
    }
    setLoading(false);
  };

  const ocr = async () => {
    setLoading(true);
    const result = await pc.sendCommand('screen.ocr', {});
    if (result?.success) {
      setOcrText(result.data?.text || '');
    }
    setLoading(false);
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <button onClick={() => capture(false)} disabled={loading}
          className="px-4 py-2 bg-cyan-500/20 text-cyan-400 rounded-lg text-sm font-medium
            hover:bg-cyan-500/30 transition-colors disabled:opacity-50">
          {loading ? 'Capturing...' : '📸 Screenshot'}
        </button>
        <button onClick={() => capture(true)} disabled={loading}
          className="px-4 py-2 bg-emerald-500/20 text-emerald-400 rounded-lg text-sm font-medium
            hover:bg-emerald-500/30 transition-colors disabled:opacity-50">
          📝 Screenshot + OCR
        </button>
        <button onClick={ocr} disabled={loading}
          className="px-4 py-2 bg-yellow-500/20 text-yellow-400 rounded-lg text-sm font-medium
            hover:bg-yellow-500/30 transition-colors disabled:opacity-50">
          🔍 OCR Only
        </button>
      </div>

      {screenshot && (
        <div className="rounded-lg border border-[var(--color-border)] overflow-hidden">
          <img
            src={`data:image/png;base64,${screenshot.base64}`}
            alt="Screen capture"
            className="w-full"
          />
          <div className="px-3 py-2 text-xs text-[var(--color-text-secondary)] bg-[var(--color-tertiary)]">
            {screenshot.width}x{screenshot.height} • {(screenshot.size_bytes / 1024).toFixed(1)}KB
          </div>
        </div>
      )}

      {ocrText && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-medium text-[var(--color-text-secondary)]">OCR Text</h4>
            <button onClick={() => navigator.clipboard.writeText(ocrText)}
              className="text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors">
              Copy
            </button>
          </div>
          <pre className="bg-[var(--color-tertiary)] rounded-lg p-3 text-xs text-[var(--color-text-primary)] overflow-auto max-h-64 whitespace-pre-wrap">
            {ocrText}
          </pre>
        </div>
      )}
    </div>
  );
}