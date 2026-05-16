import React, { useState, useMemo } from 'react';
import ConfidenceBadge from '../common/ConfidenceBadge';

const STEP_ICONS = {
  sensitivity_check: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
    </svg>
  ),
  routing: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
    </svg>
  ),
  model_selection: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
  ),
  tool_call: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  ),
  confidence: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
    </svg>
  ),
};

const STEP_COLORS = {
  sensitivity_check: 'text-amber-400 bg-amber-500/20',
  routing: 'text-purple-400 bg-purple-500/20',
  model_selection: 'text-blue-400 bg-blue-500/20',
  tool_call: 'text-cyan-400 bg-cyan-500/20',
  confidence: 'text-green-400 bg-green-500/20',
};

const STEP_LABELS = {
  sensitivity_check: 'Sensitivity Check',
  routing: 'Query Routing',
  model_selection: 'Model Selection',
  tool_call: 'Tool Call',
  confidence: 'Confidence Assessment',
};

function formatDuration(ms) {
  if (ms === null || ms === undefined) return '--';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

function formatStepLabel(type) {
  return STEP_LABELS[type] || type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function ReasoningChain({ reasoningChain, confidence }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [expandedStep, setExpandedStep] = useState(null);

  const steps = useMemo(() => {
    if (!reasoningChain || !Array.isArray(reasoningChain)) return [];
    return reasoningChain;
  }, [reasoningChain]);

  const totalDuration = useMemo(() => {
    return steps.reduce((sum, step) => sum + (step.duration_ms || 0), 0);
  }, [steps]);

  if (steps.length === 0 && confidence === undefined) {
    return null;
  }

  return (
    <div className="mt-2">
      {/* Collapsed summary row */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 text-xs text-aethera-text-secondary hover:text-aethera-foreground transition-colors group"
      >
        <svg
          className={`w-3.5 h-3.5 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <span className="font-medium">Reasoning Chain</span>
        <span className="text-aethera-text-secondary/60">
          {steps.length} step{steps.length !== 1 ? 's' : ''} &middot; {formatDuration(totalDuration)}
        </span>
        {confidence !== undefined && <ConfidenceBadge confidence={confidence} />}
      </button>

      {/* Expanded detail panel */}
      {isExpanded && (
        <div className="mt-2 ml-1 space-y-1.5 animate-fade-in">
          {steps.map((step, index) => {
            const stepType = step.type || step.step || 'unknown';
            const colorClass = STEP_COLORS[stepType] || 'text-aethera-text-secondary bg-aethera-tertiary';
            const [textColor, bgColor] = colorClass.split(' ');
            const isStepExpanded = expandedStep === index;

            return (
              <div key={index} className="relative">
                {/* Timeline connector */}
                {index < steps.length - 1 && (
                  <div className="absolute left-[15px] top-8 bottom-0 w-px bg-aethera-border" />
                )}

                <button
                  onClick={() => setExpandedStep(isStepExpanded ? null : index)}
                  className="w-full flex items-start gap-2.5 p-2 rounded-lg hover:bg-aethera-tertiary/50 transition-colors text-left"
                >
                  {/* Step icon */}
                  <div className={`w-[30px] h-[30px] rounded-full flex items-center justify-center flex-shrink-0 ${bgColor} ${textColor}`}>
                    {STEP_ICONS[stepType] || STEP_ICONS.tool_call}
                  </div>

                  {/* Step info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-aethera-foreground">
                        {formatStepLabel(stepType)}
                      </span>
                      {step.duration_ms !== undefined && (
                        <span className="text-xs text-aethera-text-secondary font-mono">
                          {formatDuration(step.duration_ms)}
                        </span>
                      )}
                      {step.status && (
                        <StatusDot status={step.status} />
                      )}
                    </div>
                    {step.summary && (
                      <p className="text-xs text-aethera-text-secondary mt-0.5 truncate">
                        {step.summary}
                      </p>
                    )}

                    {/* Expanded details */}
                    {isStepExpanded && step.details && (
                      <div className="mt-2 p-3 bg-aethera-background rounded-lg border border-aethera-border animate-fade-in">
                        {typeof step.details === 'string' ? (
                          <p className="text-xs text-aethera-foreground whitespace-pre-wrap">{step.details}</p>
                        ) : (
                          <div className="space-y-1.5">
                            {Object.entries(step.details).map(([key, value]) => (
                              <div key={key} className="flex gap-2 text-xs">
                                <span className="text-aethera-text-secondary font-medium min-w-[120px]">
                                  {key.replace(/_/g, ' ')}:
                                </span>
                                <span className="text-aethera-foreground font-mono">
                                  {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Expand chevron */}
                  <svg
                    className={`w-3.5 h-3.5 text-aethera-text-secondary transition-transform flex-shrink-0 mt-1 ${
                      isStepExpanded ? 'rotate-90' : ''
                    }`}
                    fill="none" stroke="currentColor" viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function StatusDot({ status }) {
  const colors = {
    completed: 'bg-green-400',
    running: 'bg-amber-400 animate-pulse',
    failed: 'bg-red-400',
    skipped: 'bg-aethera-text-secondary',
  };

  return (
    <span
      className={`w-1.5 h-1.5 rounded-full inline-block ${colors[status] || colors.completed}`}
      title={status}
    />
  );
}