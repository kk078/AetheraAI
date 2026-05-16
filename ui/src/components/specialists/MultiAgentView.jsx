import React, { useState, useMemo } from 'react';
import SpecialistBadge from './SpecialistBadge';
import ConfidenceBadge from '../common/ConfidenceBadge';

export default function MultiAgentView({ result, loading = false, error = null }) {
  const [expandedSpecialist, setExpandedSpecialist] = useState(null);
  const [showAll, setShowAll] = useState(false);

  const { summary, specialistResponses } = useMemo(() => {
    if (!result) return { summary: null, specialistResponses: [] };

    const summary = result.summary || result.synthesized_summary || null;
    const responses = result.specialist_responses || result.responses || result.specialists || [];
    return { summary, specialistResponses: Array.isArray(responses) ? responses : [] };
  }, [result]);

  if (loading) {
    return (
      <div className="bg-aethera-surface rounded-xl border border-aethera-border p-6 animate-fade-in">
        <div className="flex items-center gap-3 mb-4">
          <svg className="w-5 h-5 text-aethera-primary animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <span className="text-sm font-medium text-aethera-foreground">Multiple specialists are reasoning...</span>
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse">
              <div className="flex items-center gap-2 mb-2">
                <div className="h-5 w-20 bg-aethera-tertiary rounded-full" />
                <div className="h-4 w-16 bg-aethera-tertiary rounded" />
              </div>
              <div className="h-3 bg-aethera-tertiary rounded w-full mb-1" />
              <div className="h-3 bg-aethera-tertiary rounded w-3/4" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400 text-sm">
        Multi-agent reasoning failed: {error}
      </div>
    );
  }

  if (!result && !loading) {
    return null;
  }

  const visibleResponses = showAll ? specialistResponses : specialistResponses.slice(0, 4);
  const hasMore = specialistResponses.length > 4;

  return (
    <div className="bg-aethera-surface rounded-xl border border-aethera-border overflow-hidden animate-fade-in">
      {/* Synthesized Summary */}
      {summary && (
        <div className="p-4 border-b border-aethera-border bg-aethera-primary/5">
          <div className="flex items-center gap-2 mb-2">
            <svg className="w-5 h-5 text-aethera-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <h3 className="text-sm font-semibold text-aethera-foreground">Synthesized Summary</h3>
            {result.confidence !== undefined && (
              <ConfidenceBadge confidence={result.confidence} />
            )}
          </div>
          <p className="text-sm text-aethera-foreground leading-relaxed">{summary}</p>
          {result.key_findings && result.key_findings.length > 0 && (
            <div className="mt-3 space-y-1">
              {result.key_findings.map((finding, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-aethera-primary mt-1.5 flex-shrink-0" />
                  <span className="text-xs text-aethera-text-secondary">{finding}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Specialist Responses Header */}
      <div className="px-4 py-3 border-b border-aethera-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-aethera-text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
          <span className="text-sm font-medium text-aethera-foreground">
            {specialistResponses.length} Specialist{specialistResponses.length !== 1 ? 's' : ''} Consulted
          </span>
        </div>
        {hasMore && (
          <button
            onClick={() => setShowAll(!showAll)}
            className="text-xs text-aethera-primary hover:underline"
          >
            {showAll ? 'Show less' : `+${specialistResponses.length - 4} more`}
          </button>
        )}
      </div>

      {/* Specialist Response Cards */}
      <div className="divide-y divide-aethera-border">
        {visibleResponses.length === 0 ? (
          <div className="p-4 text-center text-sm text-aethera-text-secondary">
            No specialist responses available
          </div>
        ) : (
          visibleResponses.map((response, index) => {
            const specialist = response.specialist || response.specialist_id || 'general';
            const isExpanded = expandedSpecialist === index;

            return (
              <div key={index} className="px-4 py-3">
                <button
                  onClick={() => setExpandedSpecialist(isExpanded ? null : index)}
                  className="w-full flex items-center gap-3 text-left"
                >
                  <SpecialistBadge specialist={specialist} size="sm" />
                  <span className="text-sm text-aethera-foreground font-medium flex-1 truncate">
                    {response.title || response.specialist_name || specialist}
                  </span>
                  {response.confidence !== undefined && (
                    <ConfidenceBadge confidence={response.confidence} />
                  )}
                  {response.model && (
                    <span className="text-xs text-aethera-text-secondary bg-aethera-tertiary px-1.5 py-0.5 rounded">
                      {response.model.replace('aethera-', '')}
                    </span>
                  )}
                  <svg
                    className={`w-3.5 h-3.5 text-aethera-text-secondary transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                    fill="none" stroke="currentColor" viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>

                {/* Collapsed preview */}
                {!isExpanded && response.content && (
                  <p className="mt-1.5 text-xs text-aethera-text-secondary line-clamp-2 leading-relaxed pl-[88px]">
                    {response.content}
                  </p>
                )}

                {/* Expanded content */}
                {isExpanded && (
                  <div className="mt-3 pl-0 animate-fade-in">
                    <div className="p-3 bg-aethera-background rounded-lg border border-aethera-border">
                      <p className="text-sm text-aethera-foreground leading-relaxed whitespace-pre-wrap">
                        {response.content || response.response || 'No response content'}
                      </p>
                    </div>

                    {/* Metadata */}
                    {response.metadata && Object.keys(response.metadata).length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-2">
                        {response.metadata.duration_ms && (
                          <span className="text-xs text-aethera-text-secondary bg-aethera-tertiary px-2 py-0.5 rounded">
                            {response.metadata.duration_ms < 1000
                              ? `${response.metadata.duration_ms}ms`
                              : `${(response.metadata.duration_ms / 1000).toFixed(1)}s`}
                          </span>
                        )}
                        {response.metadata.tokens && (
                          <span className="text-xs text-aethera-text-secondary bg-aethera-tertiary px-2 py-0.5 rounded">
                            {response.metadata.tokens} tokens
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}