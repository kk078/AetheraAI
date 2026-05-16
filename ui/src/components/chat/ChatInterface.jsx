import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useChat } from '../../hooks/useChat';
import { api } from '../../utils/api';
import { SPECIALIST_NAMES, DEFAULT_MODEL } from '../../utils/constants';
import MessageBubble from './MessageBubble';
import InputBar from './InputBar';
import FileUploadZone from './FileUploadZone';
import ReasoningChain from './ReasoningChain';
import ToolCallDisplay from './ToolCallDisplay';
import VoiceButton from './VoiceButton';
import SpecialistBadge from '../specialists/SpecialistBadge';

export default function ChatInterface() {
  const {
    messages,
    setMessages,
    isLoading,
    error,
    sendMessage,
    loadConversation,
    stopGeneration,
    clearMessages,
  } = useChat();

  const [specialist, setSpecialist] = useState('general');
  const [model, setModel] = useState(DEFAULT_MODEL);
  const [availableModels, setAvailableModels] = useState([]);
  const [showFileUpload, setShowFileUpload] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const messagesEndRef = useRef(null);

  // Load available models on mount
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.getModels();
        if (!cancelled && res.models) {
          setAvailableModels(res.models.map((m) => m.id || m.name || m));
        }
      } catch {
        // Use defaults from constants
      }
    })();
    return () => { cancelled = true; };
  }, []);

  // Listen for conversation load events from App.jsx
  useEffect(() => {
    const handler = async (e) => {
      const conversationId = e.detail;
      if (conversationId) {
        try {
          await loadConversation(conversationId);
        } catch (err) {
          console.error('Failed to load conversation:', err);
        }
      }
    };
    window.addEventListener('aethera-load-conversation', handler);
    return () => window.removeEventListener('aethera-load-conversation', handler);
  }, [loadConversation]);

  // Listen for specialist switch events from Sidebar
  useEffect(() => {
    const handler = (e) => {
      if (e.detail) setSpecialist(e.detail);
    };
    window.addEventListener('aethera-specialist', handler);
    return () => window.removeEventListener('aethera-specialist', handler);
  }, []);

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = useCallback(async (content) => {
    await sendMessage(content, { specialist, model });
  }, [sendMessage, specialist, model]);

  const handleVoiceTranscript = useCallback((transcript) => {
    handleSend(transcript);
  }, [handleSend]);

  const handleNewChat = useCallback(() => {
    clearMessages();
  }, [clearMessages]);

  const handleFileUploadComplete = useCallback((results) => {
    setUploadedFiles((prev) => [...prev, ...results]);
    setShowFileUpload(false);
  }, []);

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-aethera-border bg-aethera-surface">
        {/* Specialist selector */}
        <div className="flex items-center gap-2">
          <label className="text-xs text-aethera-text-secondary">Specialist:</label>
          <select
            value={specialist}
            onChange={(e) => setSpecialist(e.target.value)}
            className="bg-aethera-background border border-aethera-border rounded-lg px-2 py-1 text-sm text-aethera-foreground focus:outline-none focus:border-aethera-primary"
          >
            {Object.entries(SPECIALIST_NAMES).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
        </div>

        {/* Model selector */}
        <div className="flex items-center gap-2">
          <label className="text-xs text-aethera-text-secondary">Model:</label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="bg-aethera-background border border-aethera-border rounded-lg px-2 py-1 text-sm text-aethera-foreground focus:outline-none focus:border-aethera-primary"
          >
            {availableModels.length > 0 ? (
              availableModels.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))
            ) : (
              <option value={model}>{model}</option>
            )}
          </select>
        </div>

        <div className="flex-1" />

        {/* Specialist badge */}
        <SpecialistBadge specialist={specialist} size="sm" />

        {/* New chat button */}
        <button
          onClick={handleNewChat}
          className="p-1.5 hover:bg-aethera-tertiary rounded-lg transition-colors text-aethera-text-secondary hover:text-aethera-foreground"
          title="New chat"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
        </button>

        {/* Stop generation button */}
        {isLoading && (
          <button
            onClick={stopGeneration}
            className="px-3 py-1 text-xs bg-red-500/20 text-red-400 hover:bg-red-500/30 rounded-lg transition-colors"
          >
            Stop
          </button>
        )}
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-3xl mx-auto space-y-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-64 text-aethera-text-secondary">
              <div className="text-4xl mb-4">🏥</div>
              <h2 className="text-lg font-medium text-aethera-foreground mb-2">Welcome to Aethera</h2>
              <p className="text-sm text-center max-w-md">
                Your AI-powered healthcare assistant. Ask about medical coding, claims, denials,
                prior authorization, regulatory compliance, and more.
              </p>
            </div>
          )}

          {messages.map((message) => (
            <div key={message.id}>
              <MessageBubble message={message} />
              {message.reasoningChain && <ReasoningChain steps={message.reasoningChain} />}
              {message.toolCalls && message.toolCalls.length > 0 && (
                <div className="ml-8 mt-2 space-y-2">
                  {message.toolCalls.map((tc, i) => (
                    <ToolCallDisplay key={i} call={tc} />
                  ))}
                </div>
              )}
            </div>
          ))}

          {isLoading && messages[messages.length - 1]?.role !== 'assistant' && (
            <div className="flex items-center gap-3 text-aethera-text-secondary">
              <SpecialistBadge specialist={specialist} size="sm" />
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-aethera-primary rounded-full animate-pulse" />
                <span className="w-2 h-2 bg-aethera-primary rounded-full animate-pulse" style={{ animationDelay: '0.2s' }} />
                <span className="w-2 h-2 bg-aethera-primary rounded-full animate-pulse" style={{ animationDelay: '0.4s' }} />
              </div>
              <span className="text-sm">Aethera is thinking...</span>
            </div>
          )}

          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-400">
              {error}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* File upload zone */}
      {showFileUpload && (
        <div className="max-w-3xl mx-auto px-4">
          <FileUploadZone
            onUploadComplete={handleFileUploadComplete}
            onCancel={() => setShowFileUpload(false)}
          />
        </div>
      )}

      {/* Uploaded files indicator */}
      {uploadedFiles.length > 0 && (
        <div className="max-w-3xl mx-auto px-4 py-1">
          <div className="flex gap-2 flex-wrap">
            {uploadedFiles.map((file, i) => (
              <span key={i} className="text-xs bg-aethera-tertiary px-2 py-1 rounded-lg text-aethera-text-secondary">
                {file.name || file.filename || `File ${i + 1}`}
                <button
                  onClick={() => setUploadedFiles((prev) => prev.filter((_, j) => j !== i))}
                  className="ml-1 text-aethera-text-secondary hover:text-red-400"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Input area */}
      <div className="border-t border-aethera-border p-4 bg-aethera-surface">
        <div className="max-w-3xl mx-auto flex items-end gap-2">
          <div className="flex-1">
            <InputBar
              onSend={handleSend}
              disabled={isLoading}
              onAttachClick={() => setShowFileUpload(!showFileUpload)}
            />
          </div>
          <VoiceButton onTranscript={handleVoiceTranscript} disabled={isLoading} />
        </div>
      </div>
    </div>
  );
}