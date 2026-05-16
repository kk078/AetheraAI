import React, { useState, useRef } from 'react';

export default function InputBar({ onSend, disabled, onAttachClick }) {
  const [input, setInput] = useState('');
  const textareaRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !disabled) {
      onSend(input.trim());
      setInput('');
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleInput = (e) => {
    setInput(e.target.value);
    // Auto-resize textarea
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`;
  };

  return (
    <form onSubmit={handleSubmit} className="relative">
      <div className="relative flex items-end gap-2 bg-aethera-background border border-aethera-border rounded-xl p-2 focus-within:border-aethera-primary transition-colors">
        {/* File upload button */}
        <button
          type="button"
          onClick={onAttachClick}
          className="p-2 text-aethera-text-secondary hover:text-aethera-foreground hover:bg-aethera-tertiary rounded-lg transition-colors"
          title="Attach file"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
          </svg>
        </button>

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Ask Aethera anything... (Try: 'What's the ICD-10 code for type 2 diabetes?')"
          disabled={disabled}
          rows={1}
          className="flex-1 bg-transparent border-none outline-none resize-none text-aethera-foreground placeholder-aethera-text-secondary max-h-[200px] py-2"
          style={{ minHeight: '24px' }}
        />

        {/* Send button */}
        <button
          type="submit"
          disabled={!input.trim() || disabled}
          className="p-2 bg-aethera-primary hover:bg-cyan-600 disabled:bg-aethera-tertiary disabled:text-aethera-text-secondary text-white rounded-lg transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
        </button>
      </div>

      {/* Quick suggestions */}
      <div className="flex gap-2 mt-3 overflow-x-auto pb-1">
        <QuickSuggestion text="ICD-10 code for hypertension" onClick={() => setInput('ICD-10 code for hypertension')} />
        <QuickSuggestion text="Medicare prior auth rules" onClick={() => setInput('Medicare prior auth rules')} />
        <QuickSuggestion text="NCCI edit check" onClick={() => setInput('How do I check NCCI edits?')} />
        <QuickSuggestion text="DRG assignment" onClick={() => setInput('How is DRG calculated?')} />
      </div>
    </form>
  );
}

function QuickSuggestion({ text, onClick }) {
  return (
    <button
      onClick={onClick}
      className="flex-shrink-0 px-3 py-1.5 text-xs bg-aethera-tertiary hover:bg-aethera-primary/20 text-aethera-text-secondary hover:text-aethera-primary rounded-full transition-colors border border-aethera-border"
    >
      {text}
    </button>
  );
}
