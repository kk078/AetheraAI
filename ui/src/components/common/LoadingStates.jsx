import React from 'react';

/**
 * MessageSkeleton - skeleton loader for chat message bubbles
 */
export function MessageSkeleton({ count = 1, isUser = false }) {
  return (
    <>
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'} animate-pulse`}>
          {!isUser && (
            <div className="w-8 h-8 rounded-full bg-aethera-tertiary flex-shrink-0" />
          )}
          <div className={`max-w-[70%] space-y-2 ${isUser ? 'items-end' : 'items-start'}`}>
            <div className={`h-4 rounded skeleton`} style={{ width: `${60 + Math.random() * 30}%` }} />
            <div className={`h-4 rounded skeleton`} style={{ width: `${40 + Math.random() * 40}%` }} />
            <div className={`h-3 rounded skeleton`} style={{ width: `${20 + Math.random() * 20}%` }} />
          </div>
        </div>
      ))}
    </>
  );
}

/**
 * CardSkeleton - skeleton loader for dashboard/stat cards
 */
export function CardSkeleton({ count = 1 }) {
  return (
    <>
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="bg-aethera-surface rounded-xl border border-aethera-border p-4 animate-pulse">
          <div className="flex items-center justify-between">
            <div className="w-6 h-6 rounded skeleton" />
            <div className="w-16 h-3 rounded skeleton" />
          </div>
          <div className="mt-3">
            <div className="w-20 h-7 rounded skeleton" />
            <div className="w-24 h-4 rounded skeleton mt-2" />
          </div>
        </div>
      ))}
    </>
  );
}

/**
 * TableSkeleton - skeleton loader for table rows
 */
export function TableSkeleton({ rows = 5, columns = 4 }) {
  return (
    <div className="bg-aethera-surface rounded-xl border border-aethera-border overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-aethera-border flex gap-4">
        {Array.from({ length: columns }, (_, i) => (
          <div key={i} className="flex-1 h-4 rounded skeleton" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }, (_, rowIdx) => (
        <div key={rowIdx} className="px-4 py-3 border-b border-aethera-border last:border-b-0 flex gap-4 animate-pulse">
          {Array.from({ length: columns }, (_, colIdx) => (
            <div
              key={colIdx}
              className="flex-1 h-4 rounded skeleton"
              style={{ width: `${50 + Math.random() * 40}%` }}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

/**
 * StreamingDots - animated dots for streaming/in-progress responses
 */
export function StreamingDots({ size = 'md', color = 'aethera-primary' }) {
  const sizeClasses = {
    sm: 'w-1.5 h-1.5',
    md: 'w-2 h-2',
    lg: 'w-2.5 h-2.5',
  };

  const dotSize = sizeClasses[size];

  return (
    <div className="flex items-center gap-1.5">
      <span className={`${dotSize} bg-${color} rounded-full animate-pulse`} style={{ animationDelay: '0ms' }} />
      <span className={`${dotSize} bg-${color} rounded-full animate-pulse`} style={{ animationDelay: '200ms' }} />
      <span className={`${dotSize} bg-${color} rounded-full animate-pulse`} style={{ animationDelay: '400ms' }} />
    </div>
  );
}

/**
 * InlineSpinner - small spinner for button loading states
 */
export function InlineSpinner({ className = '' }) {
  return (
    <div className={`animate-spin rounded-full h-4 w-4 border-b-2 border-current ${className}`} />
  );
}

/**
 * PageLoader - full page loading indicator
 */
export function PageLoader() {
  return (
    <div className="flex flex-col items-center justify-center h-64 gap-3">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-aethera-primary" />
      <p className="text-sm text-aethera-text-secondary">Loading...</p>
    </div>
  );
}

/**
 * EmptyState - reusable empty state component
 */
export function EmptyState({ icon, title, description, action, onAction }) {
  return (
    <div className="bg-aethera-surface rounded-xl border border-aethera-border p-8 text-center">
      {icon && <div className="text-aethera-text-secondary mx-auto mb-3 w-12 h-12 flex items-center justify-center">{icon}</div>}
      <h3 className="text-sm font-medium text-aethera-foreground">{title}</h3>
      {description && <p className="text-sm text-aethera-text-secondary mt-1">{description}</p>}
      {action && onAction && (
        <button onClick={onAction} className="mt-4 text-sm text-aethera-primary hover:underline">{action}</button>
      )}
    </div>
  );
}

/**
 * ErrorState - reusable error state component
 */
export function ErrorState({ title, message, onRetry }) {
  return (
    <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400">
      <p className="font-medium">{title || 'Something went wrong'}</p>
      {message && <p className="text-sm mt-1">{message}</p>}
      {onRetry && <button onClick={onRetry} className="mt-2 text-sm underline hover:no-underline">Retry</button>}
    </div>
  );
}