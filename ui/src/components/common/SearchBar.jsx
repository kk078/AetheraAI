import React, { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../../utils/api';

const SEARCH_CATEGORIES = [
  { key: 'all', label: 'All' },
  { key: 'conversations', label: 'Conversations' },
  { key: 'skills', label: 'Skills' },
  { key: 'connectors', label: 'Connectors' },
  { key: 'knowledge', label: 'Knowledge' },
];

export default function SearchBar() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [activeCategory, setActiveCategory] = useState('all');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef(null);
  const containerRef = useRef(null);
  const debounceRef = useRef(null);

  const performSearch = useCallback(async (searchQuery, category) => {
    if (!searchQuery.trim()) {
      setResults(null);
      return;
    }
    setLoading(true);
    try {
      const params = new URLSearchParams({ q: searchQuery });
      if (category !== 'all') params.set('category', category);
      const res = await api.get(`/api/search?${params.toString()}`);
      const json = await res.json();
      setResults(json.results || json || []);
    } catch (err) {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      performSearch(query, activeCategory);
    }, 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [query, activeCategory, performSearch]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const flatResults = results
    ? Object.entries(results).flatMap(([category, items]) =>
        Array.isArray(items) ? items.map((item) => ({ ...item, category })) : []
      )
    : [];

  useEffect(() => {
    setSelectedIndex(0);
  }, [flatResults.length]);

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, flatResults.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && flatResults[selectedIndex]) {
      e.preventDefault();
      handleSelect(flatResults[selectedIndex]);
    } else if (e.key === 'Escape') {
      setIsOpen(false);
      inputRef.current?.blur();
    }
  };

  const handleSelect = (item) => {
    window.dispatchEvent(new CustomEvent('aethera-navigate', { detail: { category: item.category, id: item.id } }));
    setIsOpen(false);
    setQuery('');
    setResults(null);
  };

  return (
    <div ref={containerRef} className="relative w-full max-w-xl">
      {/* Input */}
      <div className="relative">
        <svg className="w-5 h-5 text-aethera-text-secondary absolute left-3 top-1/2 -translate-y-1/2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => { setQuery(e.target.value); setIsOpen(true); }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder="Search conversations, skills, connectors..."
          className="w-full bg-aethera-surface border border-aethera-border rounded-lg pl-10 pr-10 py-2.5 text-sm text-aethera-foreground placeholder-aethera-text-secondary focus:outline-none focus:border-aethera-primary transition-colors"
        />
        {query && (
          <button
            onClick={() => { setQuery(''); setResults(null); }}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-aethera-text-secondary hover:text-aethera-foreground"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Results Dropdown */}
      {isOpen && query.trim() && (
        <div className="absolute top-full mt-2 w-full bg-aethera-surface rounded-xl border border-aethera-border shadow-xl z-50 overflow-hidden animate-slide-up">
          {/* Category Tabs */}
          <div className="px-3 pt-3 pb-2 border-b border-aethera-border flex gap-1 flex-wrap">
            {SEARCH_CATEGORIES.map((cat) => (
              <button
                key={cat.key}
                onClick={() => setActiveCategory(cat.key)}
                className={`text-xs px-2.5 py-1 rounded-full transition-colors ${
                  activeCategory === cat.key
                    ? 'bg-aethera-primary text-white'
                    : 'text-aethera-text-secondary hover:text-aethera-foreground'
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>

          {/* Results List */}
          <div className="max-h-80 overflow-y-auto">
            {loading ? (
              <div className="p-6 text-center">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-aethera-primary mx-auto" />
              </div>
            ) : flatResults.length === 0 ? (
              <div className="p-6 text-center text-aethera-text-secondary text-sm">
                No results found for "{query}"
              </div>
            ) : (
              flatResults.map((item, index) => (
                <button
                  key={`${item.category}-${item.id || index}`}
                  onClick={() => handleSelect(item)}
                  className={`w-full px-4 py-3 flex items-center gap-3 text-left transition-colors ${
                    index === selectedIndex ? 'bg-aethera-primary/20' : 'hover:bg-aethera-tertiary/50'
                  }`}
                >
                  <CategoryIcon category={item.category} />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-aethera-foreground truncate">{item.title || item.name}</p>
                    <p className="text-xs text-aethera-text-secondary truncate">{item.description || item.summary || item.category}</p>
                  </div>
                  <span className="text-xs text-aethera-text-secondary flex-shrink-0 px-1.5 py-0.5 rounded bg-aethera-tertiary">
                    {item.category}
                  </span>
                </button>
              ))
            )}
          </div>

          {/* Footer */}
          <div className="px-4 py-2 border-t border-aethera-border flex justify-between text-xs text-aethera-text-secondary">
            <span>Enter to select</span>
            <span>Esc to close</span>
          </div>
        </div>
      )}
    </div>
  );
}

function CategoryIcon({ category }) {
  const paths = {
    conversations: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z',
    skills: 'M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z',
    connectors: 'M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1',
    knowledge: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253',
  };

  return (
    <div className="w-8 h-8 rounded-lg bg-aethera-primary/20 flex items-center justify-center flex-shrink-0">
      <svg className="w-4 h-4 text-aethera-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={paths[category] || paths.knowledge} />
      </svg>
    </div>
  );
}