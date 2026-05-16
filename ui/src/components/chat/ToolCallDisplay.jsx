import React, { useState } from 'react';

const STATUS_CONFIG = {
  loading: {
    icon: (
      <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
      </svg>
    ),
    color: 'text-amber-400',
    bg: 'bg-amber-500/10 border-amber-500/30',
    label: 'Running',
  },
  success: {
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
    ),
    color: 'text-green-400',
    bg: 'bg-green-500/10 border-green-500/30',
    label: 'Completed',
  },
  error: {
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
      </svg>
    ),
    color: 'text-red-400',
    bg: 'bg-red-500/10 border-red-500/30',
    label: 'Failed',
  },
};

function truncateText(text, maxLen = 80) {
  if (!text) return '';
  const str = typeof text === 'string' ? text : JSON.stringify(text);
  if (str.length <= maxLen) return str;
  return str.slice(0, maxLen) + '...';
}

export default function ToolCallDisplay({ toolCalls = [] }) {
  const [expandedIndex, setExpandedIndex] = useState(null);

  if (!toolCalls || toolCalls.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2 mt-2">
      {toolCalls.map((tool, index) => {
        const status = tool.status || 'loading';
        const config = STATUS_CONFIG[status] || STATUS_CONFIG.loading;
        const isExpanded = expandedIndex === index;
        const hasParams = tool.parameters && Object.keys(tool.parameters).length > 0;
        const hasResult = tool.result !== undefined && tool.result !== null;

        return (
          <div
            key={tool.id || index}
            className={`rounded-lg border p-3 ${config.bg} animate-fade-in`}
          >
            {/* Header row */}
            <button
              onClick={() => setExpandedIndex(isExpanded ? null : index)}
              className="w-full flex items-center gap-2 text-left"
            >
              {/* Status icon / spinner */}
              <span className={config.color}>{config.icon}</span>

              {/* Tool name */}
              <span className="text-sm font-medium text-aethera-foreground font-mono">
                {tool.name || 'unknown_tool'}
              </span>

              {/* Status label */}
              <span className={`text-xs ${config.color} font-medium`}>
                {config.label}
              </span>

              {/* Truncated params preview */}
              {hasParams && !isExpanded && (
                <span className="text-xs text-aethera-text-secondary font-mono ml-auto truncate max-w-[200px]">
                  {truncateText(tool.parameters)}
                </span>
              )}

              {/* Duration */}
              {tool.duration_ms !== undefined && status !== 'loading' && (
                <span className="text-xs text-aethera-text-secondary font-mono ml-auto">
                  {tool.duration_ms < 1000 ? `${tool.duration_ms}ms` : `${(tool.duration_ms / 1000).toFixed(1)}s`}
                </span>
              )}

              {/* Expand chevron */}
              {(hasParams || hasResult) && (
                <svg
                  className={`w-3.5 h-3.5 text-aethera-text-secondary transition-transform ${
                    isExpanded ? 'rotate-90' : ''
                  }`}
                  fill="none" stroke="currentColor" viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              )}
            </button>

            {/* Expanded details */}
            {isExpanded && (
              <div className="mt-3 space-y-2 animate-fade-in">
                {/* Parameters */}
                {hasParams && (
                  <div>
                    <p className="text-xs text-aethera-text-secondary font-medium mb-1">Parameters</p>
                    <div className="bg-aethera-background rounded-md p-2 border border-aethera-border">
                      <pre className="text-xs text-aethera-foreground font-mono whitespace-pre-wrap overflow-x-auto">
                        {typeof tool.parameters === 'string'
                          ? tool.parameters
                          : JSON.stringify(tool.parameters, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}

                {/* Result */}
                {hasResult && (
                  <div>
                    <p className="text-xs text-aethera-text-secondary font-medium mb-1">Result</p>
                    <div className="bg-aethera-background rounded-md p-2 border border-aethera-border">
                      <pre className="text-xs text-aethera-foreground font-mono whitespace-pre-wrap overflow-x-auto max-h-[200px] overflow-y-auto">
                        {typeof tool.result === 'string'
                          ? tool.result
                          : JSON.stringify(tool.result, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}

                {/* Error message */}
                {tool.error && (
                  <div>
                    <p className="text-xs text-red-400 font-medium mb-1">Error</p>
                    <div className="bg-red-500/10 rounded-md p-2 border border-red-500/30">
                      <p className="text-xs text-red-300 font-mono">{tool.error}</p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}