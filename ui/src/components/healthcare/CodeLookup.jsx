import React, { useState, useCallback } from 'react';
import { api } from '../../utils/api';

const CODE_TYPES = [
  { value: 'icd10', label: 'ICD-10' },
  { value: 'cpt', label: 'CPT' },
  { value: 'hcpcs', label: 'HCPCS' },
];

const CODE_TYPE_COLORS = {
  icd10: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  cpt: 'bg-green-500/20 text-green-400 border-green-500/30',
  hcpcs: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
};

export default function CodeLookup() {
  const [query, setQuery] = useState('');
  const [codeType, setCodeType] = useState('icd10');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = useCallback(async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setHasSearched(true);

    try {
      const response = await api.searchCodes(query.trim(), codeType);
      const data = Array.isArray(response) ? response : response.results || response.codes || [];
      setResults(data);
    } catch (err) {
      setError(err.message || 'Code lookup failed');
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [query, codeType]);

  const handleCodeClick = useCallback(async (code) => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.lookupCode(code, codeType);
      if (response && !Array.isArray(response)) {
        setResults((prev) =>
          prev.map((r) =>
            r.code === code ? { ...r, ...response, expanded: true } : { ...r, expanded: false }
          )
        );
      }
    } catch (err) {
      // Silently fail - detail lookup is optional
    } finally {
      setLoading(false);
    }
  }, [codeType]);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-aethera-foreground">Code Lookup</h1>
        <p className="text-aethera-text-secondary mt-1">Search ICD-10, CPT, and HCPCS codes</p>
      </div>

      {/* Search Form */}
      <form onSubmit={handleSearch} className="space-y-3">
        <div className="flex gap-3">
          {/* Code type selector */}
          <div className="relative">
            <select
              value={codeType}
              onChange={(e) => setCodeType(e.target.value)}
              className="appearance-none bg-aethera-surface border border-aethera-border rounded-lg px-4 py-2.5 pr-8 text-sm text-aethera-foreground focus:border-aethera-primary focus:outline-none cursor-pointer"
            >
              {CODE_TYPES.map((ct) => (
                <option key={ct.value} value={ct.value}>{ct.label}</option>
              ))}
            </select>
            <svg className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-aethera-text-secondary pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>

          {/* Search input */}
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={
              codeType === 'icd10'
                ? 'Search ICD-10 (e.g., E11.9, type 2 diabetes)'
                : codeType === 'cpt'
                  ? 'Search CPT (e.g., 99213, office visit)'
                  : 'Search HCPCS (e.g., J0585, Botox injection)'
            }
            className="flex-1 bg-aethera-surface border border-aethera-border rounded-lg px-4 py-2.5 text-aethera-foreground placeholder-aethera-text-secondary focus:border-aethera-primary focus:outline-none"
          />

          {/* Search button */}
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="px-6 py-2.5 bg-aethera-primary hover:bg-cyan-600 disabled:bg-aethera-tertiary disabled:text-aethera-text-secondary text-white rounded-lg font-medium transition-colors flex items-center gap-2"
          >
            {loading ? (
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            )}
            Search
          </button>
        </div>

        {/* Quick code type tabs */}
        <div className="flex gap-2">
          {CODE_TYPES.map((ct) => (
            <button
              key={ct.value}
              onClick={() => setCodeType(ct.value)}
              className={`px-3 py-1.5 text-xs rounded-full border transition-colors ${
                codeType === ct.value
                  ? `${CODE_TYPE_COLORS[ct.value]} border`
                  : 'border-aethera-border text-aethera-text-secondary hover:text-aethera-foreground'
              }`}
            >
              {ct.label}
            </button>
          ))}
        </div>
      </form>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Results */}
      {loading && results.length === 0 && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse bg-aethera-surface rounded-lg border border-aethera-border p-4">
              <div className="h-4 bg-aethera-tertiary rounded w-24 mb-2" />
              <div className="h-3 bg-aethera-tertiary rounded w-full mb-1" />
              <div className="h-3 bg-aethera-tertiary rounded w-2/3" />
            </div>
          ))}
        </div>
      )}

      {hasSearched && !loading && results.length === 0 && !error && (
        <div className="text-center py-12 text-aethera-text-secondary">
          <svg className="w-12 h-12 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <p className="text-lg font-medium">No codes found</p>
          <p className="text-sm mt-1">Try a different search term or code type</p>
        </div>
      )}

      {results.length > 0 && (
        <div className="bg-aethera-surface rounded-xl border border-aethera-border overflow-hidden">
          {/* Results table */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-aethera-border bg-aethera-background">
                  <th className="text-left py-3 px-4 text-aethera-text-secondary font-medium">Code</th>
                  <th className="text-left py-3 px-4 text-aethera-text-secondary font-medium">Description</th>
                  <th className="text-left py-3 px-4 text-aethera-text-secondary font-medium">Category</th>
                  <th className="text-left py-3 px-4 text-aethera-text-secondary font-medium w-12" />
                </tr>
              </thead>
              <tbody>
                {results.map((item, index) => (
                  <React.Fragment key={item.code || index}>
                    <tr
                      className="border-b border-aethera-border last:border-0 hover:bg-aethera-tertiary/50 transition-colors cursor-pointer"
                      onClick={() => handleCodeClick(item.code)}
                    >
                      <td className="py-3 px-4">
                        <span className="font-mono text-aethera-foreground font-medium">{item.code}</span>
                      </td>
                      <td className="py-3 px-4 text-aethera-text-secondary max-w-md">
                        {item.description || item.short_description || '--'}
                      </td>
                      <td className="py-3 px-4">
                        {item.category && (
                          <span className={`text-xs px-2 py-0.5 rounded-full border ${CODE_TYPE_COLORS[codeType] || 'border-aethera-border text-aethera-text-secondary'}`}>
                            {item.category}
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <svg
                          className={`w-4 h-4 text-aethera-text-secondary transition-transform ${item.expanded ? 'rotate-90' : ''}`}
                          fill="none" stroke="currentColor" viewBox="0 0 24 24"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </td>
                    </tr>

                    {/* Expanded detail row */}
                    {item.expanded && (
                      <tr>
                        <td colSpan="4" className="p-0">
                          <div className="p-4 bg-aethera-background border-b border-aethera-border animate-fade-in">
                            <div className="grid grid-cols-2 gap-3 text-xs">
                              {item.long_description && (
                                <div className="col-span-2">
                                  <span className="text-aethera-text-secondary font-medium">Full Description:</span>
                                  <p className="text-aethera-foreground mt-1">{item.long_description}</p>
                                </div>
                              )}
                              {item.chapter && (
                                <div>
                                  <span className="text-aethera-text-secondary font-medium">Chapter:</span>
                                  <p className="text-aethera-foreground mt-0.5">{item.chapter}</p>
                                </div>
                              )}
                              {item.section && (
                                <div>
                                  <span className="text-aethera-text-secondary font-medium">Section:</span>
                                  <p className="text-aethera-foreground mt-0.5">{item.section}</p>
                                </div>
                              )}
                              {item.code_type && (
                                <div>
                                  <span className="text-aethera-text-secondary font-medium">Type:</span>
                                  <p className="text-aethera-foreground mt-0.5">{item.code_type.toUpperCase()}</p>
                                </div>
                              )}
                              {item.status && (
                                <div>
                                  <span className="text-aethera-text-secondary font-medium">Status:</span>
                                  <p className="text-aethera-foreground mt-0.5">{item.status}</p>
                                </div>
                              )}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>

          {/* Results footer */}
          <div className="px-4 py-2 border-t border-aethera-border text-xs text-aethera-text-secondary">
            {results.length} result{results.length !== 1 ? 's' : ''} found
          </div>
        </div>
      )}
    </div>
  );
}