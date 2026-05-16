/**
 * Aethera AI — Confirmation Dialog
 * Safety approval modal for destructive PC control actions.
 */
import { useState, useEffect } from 'react';

const RISK_COLORS = {
  high: { bg: 'bg-red-500/10', border: 'border-red-500/30', text: 'text-red-400', badge: 'bg-red-500/20 text-red-300' },
  medium: { bg: 'bg-yellow-500/10', border: 'border-yellow-500/30', text: 'text-yellow-400', badge: 'bg-yellow-500/20 text-yellow-300' },
  low: { bg: 'bg-blue-500/10', border: 'border-blue-500/30', text: 'text-blue-400', badge: 'bg-blue-500/20 text-blue-300' },
};

export default function ConfirmationDialog({ confirmation, onConfirm, onDeny, onDismiss }) {
  const { command_id, action, description, risk_level, parameters, timestamp } = confirmation;
  const [countdown, setCountdown] = useState(60);
  const colors = RISK_COLORS[risk_level] || RISK_COLORS.high;

  // Auto-deny countdown
  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          onDeny();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [onDeny]);

  return (
    <div className={`mx-4 mb-3 rounded-lg border ${colors.border} ${colors.bg} p-4`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className={`px-2 py-0.5 rounded text-xs font-semibold ${colors.badge}`}>
              {risk_level.toUpperCase()} RISK
            </span>
            <span className="text-xs text-[var(--color-text-secondary)]">
              {action}
            </span>
          </div>
          <p className={`text-sm ${colors.text} font-medium mb-1`}>
            {description}
          </p>
          {parameters && Object.keys(parameters).length > 0 && (
            <div className="mt-2 px-3 py-2 bg-black/20 rounded text-xs text-[var(--color-text-secondary)] font-mono">
              {Object.entries(parameters).slice(0, 5).map(([k, v]) => (
                <div key={k}>
                  <span className="text-[var(--color-text-secondary)]">{k}:</span>{' '}
                  <span className="text-[var(--color-text-primary)]">{String(v).slice(0, 80)}</span>
                </div>
              ))}
            </div>
          )}
          <p className="text-xs text-[var(--color-text-secondary)] mt-2">
            Auto-denied in {countdown}s. This action will be logged.
          </p>
        </div>
      </div>
      <div className="flex gap-2 mt-3">
        <button
          onClick={onConfirm}
          className={`px-4 py-1.5 rounded-lg text-sm font-medium bg-red-500/20 text-red-300
            hover:bg-red-500/30 transition-colors`}
        >
          Approve
        </button>
        <button
          onClick={onDeny}
          className="px-4 py-1.5 rounded-lg text-sm font-medium bg-[var(--color-tertiary)] text-[var(--color-text-secondary)]
            hover:bg-[var(--color-tertiary)]/80 transition-colors"
        >
          Deny
        </button>
        <button
          onClick={onDismiss}
          className="px-4 py-1.5 rounded-lg text-sm font-medium text-[var(--color-text-secondary)]
            hover:text-[var(--color-text-primary)] transition-colors"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}