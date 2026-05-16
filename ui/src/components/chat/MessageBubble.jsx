import React from 'react';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import SpecialistBadge from '../specialists/SpecialistBadge';
import ConfidenceBadge from '../common/ConfidenceBadge';

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user';

  const rawHtml = marked.parse(message.content || '', { async: false }) || '';
  const safeHtml = DOMPurify.sanitize(rawHtml);

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[85%] ${isUser ? 'order-1' : 'order-2'}`}>
        {/* Header */}
        {!isUser && (
          <div className="flex items-center gap-2 mb-1.5">
            <SpecialistBadge specialist={message.specialist || 'general'} size="sm" />
            {message.confidence !== undefined && (
              <ConfidenceBadge confidence={message.confidence} />
            )}
            {message.model && (
              <span className="text-xs text-aethera-text-secondary bg-aethera-tertiary px-1.5 py-0.5 rounded">
                {message.model.replace('aethera-', '')}
              </span>
            )}
          </div>
        )}

        {/* Content */}
        <div
          className={`
            ${isUser
              ? 'message-user bg-aethera-tertiary'
              : 'message-assistant prose prose-invert max-w-none'
            }
            text-sm leading-relaxed
          `}
          dangerouslySetInnerHTML={{ __html: safeHtml }}
        />

        {/* Timestamp */}
        <div className={`mt-1.5 text-xs text-aethera-text-secondary ${isUser ? 'text-right' : 'text-left'}`}>
          {new Date(message.timestamp).toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
}
