import React, { useState, useCallback } from 'react';
import { api } from '../../utils/api';

export default function DrugLookup() {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedSections, setExpandedSections] = useState({
    interactions: false,
    warnings: false,
    formulary: false,
  });

  const handleSearch = useCallback(async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await api.lookupDrug(query.trim());
      setResult(data);
    } catch (err) {
      setError(err.message || 'Drug lookup failed');
    } finally {
      setLoading(false);
    }
  }, [query]);

  const toggleSection = (section) => {
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  const interactions = result?.interactions || result?.drug_interactions || [];
  const warnings = result?.black_box_warnings || result?.boxed_warnings || [];
  const formulary = result?.formulary_info || result?.formulary || null;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-aethera-foreground">Drug Lookup</h1>
        <p className="text-aethera-text-secondary mt-1">Search drug information, interactions, and formulary status</p>
      </div>

      {/* Search Form */}
      <form onSubmit={handleSearch} className="flex gap-3">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter drug name (e.g., Metformin, Lisinopril)"
          className="flex-1 bg-aethera-surface border border-aethera-border rounded-lg px-4 py-2.5 text-aethera-foreground placeholder-aethera-text-secondary focus:border-aethera-primary focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="px-6 py-2.5 bg-aethera-primary hover:bg-cyan-600 disabled:bg-aethera-tertiary disabled:text-aethera-text-secondary text-white rounded-lg font-medium transition-colors flex items-center gap-2"
        >
          {loading && (
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
          )}
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Results */}
      {result && !loading && (
        <div className="space-y-6 animate-fade-in">
          {/* Drug Overview */}
          <div className="bg-aethera-surface rounded-xl border border-aethera-border p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h2 className="text-lg font-semibold text-aethera-foreground">
                  {result.brand_name || result.generic_name || query}
                </h2>
                {result.generic_name && result.brand_name && result.generic_name !== result.brand_name && (
                  <p className="text-sm text-aethera-text-secondary mt-0.5">
                    Generic: {result.generic_name}
                  </p>
                )}
              </div>
              {result.schedule && (
                <span className="px-3 py-1 bg-amber-500/20 text-amber-400 rounded-full text-xs font-medium border border-amber-500/30">
                  Schedule {result.schedule}
                </span>
              )}
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {result.drug_class && (
                <InfoItem label="Drug Class" value={result.drug_class} />
              )}
              {result.ndc && (
                <InfoItem label="NDC" value={result.ndc} mono />
              )}
              {result.rxcui && (
                <InfoItem label="RxCUI" value={result.rxcui} mono />
              )}
              {result.manufacturer && (
                <InfoItem label="Manufacturer" value={result.manufacturer} />
              )}
              {result.route && (
                <InfoItem label="Route" value={Array.isArray(result.route) ? result.route.join(', ') : result.route} />
              )}
              {result.dosage_form && (
                <InfoItem label="Dosage Form" value={result.dosage_form} />
              )}
              {result.strength && (
                <InfoItem label="Strength" value={result.strength} />
              )}
              {result.status && (
                <InfoItem label="Status" value={result.status} />
              )}
            </div>
          </div>

          {/* Indications */}
          {result.indications && (Array.isArray(result.indications) ? result.indications.length > 0 : result.indications) && (
            <div className="bg-aethera-surface rounded-xl border border-aethera-border p-6">
              <h3 className="text-sm font-semibold text-aethera-foreground mb-3">Indications</h3>
              {Array.isArray(result.indications) ? (
                <ul className="space-y-2">
                  {result.indications.map((ind, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-aethera-primary mt-2 flex-shrink-0" />
                      <span className="text-sm text-aethera-text-secondary">{typeof ind === 'string' ? ind : ind.description || JSON.stringify(ind)}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-aethera-text-secondary leading-relaxed">{result.indications}</p>
              )}
            </div>
          )}

          {/* Black Box Warnings */}
          {warnings.length > 0 && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6">
              <button
                onClick={() => toggleSection('warnings')}
                className="w-full flex items-center gap-2 text-left"
              >
                <svg className="w-5 h-5 text-red-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <h3 className="text-sm font-semibold text-red-400">Black Box Warnings ({warnings.length})</h3>
                <svg className={`w-4 h-4 text-red-400 ml-auto transition-transform ${expandedSections.warnings ? 'rotate-90' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
              {expandedSections.warnings && (
                <div className="mt-3 space-y-2 animate-fade-in">
                  {warnings.map((warning, i) => (
                    <div key={i} className="p-3 bg-red-500/5 border border-red-500/20 rounded-lg">
                      <p className="text-sm text-red-300 leading-relaxed">
                        {typeof warning === 'string' ? warning : warning.description || JSON.stringify(warning)}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Drug Interactions */}
          {interactions.length > 0 && (
            <div className="bg-aethera-surface rounded-xl border border-aethera-border overflow-hidden">
              <button
                onClick={() => toggleSection('interactions')}
                className="w-full flex items-center gap-2 px-6 py-4 text-left hover:bg-aethera-tertiary/50 transition-colors"
              >
                <svg className="w-5 h-5 text-amber-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <h3 className="text-sm font-semibold text-aethera-foreground">Drug Interactions ({interactions.length})</h3>
                <svg className={`w-4 h-4 text-aethera-text-secondary ml-auto transition-transform ${expandedSections.interactions ? 'rotate-90' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
              {expandedSections.interactions && (
                <div className="px-6 pb-4 space-y-3 animate-fade-in">
                  {interactions.map((interaction, i) => {
                    const severity = interaction.severity || interaction.level || 'moderate';
                    const severityColor = severity === 'major' || severity === 'severe' || severity === 'high'
                      ? 'bg-red-500/20 text-red-400 border-red-500/30'
                      : severity === 'moderate'
                        ? 'bg-amber-500/20 text-amber-400 border-amber-500/30'
                        : 'bg-blue-500/20 text-blue-400 border-blue-500/30';

                    return (
                      <div key={i} className="p-3 bg-aethera-background rounded-lg border border-aethera-border">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-sm text-aethera-foreground">
                            {interaction.drug || interaction.interacting_drug || interaction.name}
                          </span>
                          <span className={`text-xs px-2 py-0.5 rounded-full border ${severityColor}`}>
                            {severity}
                          </span>
                        </div>
                        <p className="text-xs text-aethera-text-secondary">
                          {interaction.description || interaction.effect || ''}
                        </p>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Formulary Info */}
          {formulary && (
            <div className="bg-aethera-surface rounded-xl border border-aethera-border overflow-hidden">
              <button
                onClick={() => toggleSection('formulary')}
                className="w-full flex items-center gap-2 px-6 py-4 text-left hover:bg-aethera-tertiary/50 transition-colors"
              >
                <svg className="w-5 h-5 text-green-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <h3 className="text-sm font-semibold text-aethera-foreground">Formulary Information</h3>
                <svg className={`w-4 h-4 text-aethera-text-secondary ml-auto transition-transform ${expandedSections.formulary ? 'rotate-90' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
              {expandedSections.formulary && (
                <div className="px-6 pb-4 animate-fade-in">
                  {Array.isArray(formulary) ? (
                    <div className="space-y-3">
                      {formulary.map((item, i) => (
                        <div key={i} className="p-3 bg-aethera-background rounded-lg border border-aethera-border">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-sm font-medium text-aethera-foreground">
                              {item.plan || item.payer || 'Plan'}
                            </span>
                            {item.tier && (
                              <span className="text-xs px-2 py-0.5 rounded-full bg-aethera-tertiary text-aethera-text-secondary">
                                Tier {item.tier}
                              </span>
                            )}
                            {item.pa_required && (
                              <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">
                                PA Required
                              </span>
                            )}
                          </div>
                          {item.copay && (
                            <p className="text-xs text-aethera-text-secondary mt-1">Copay: {typeof item.copay === 'number' ? `$${item.copay}` : item.copay}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : typeof formulary === 'object' ? (
                    <div className="p-3 bg-aethera-background rounded-lg border border-aethera-border">
                      <div className="space-y-1.5">
                        {Object.entries(formulary).map(([key, value]) => (
                          <div key={key} className="flex gap-2 text-xs">
                            <span className="text-aethera-text-secondary font-medium min-w-[120px]">{key.replace(/_/g, ' ')}:</span>
                            <span className="text-aethera-foreground">{typeof value === 'object' ? JSON.stringify(value) : String(value)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-aethera-text-secondary">{String(formulary)}</p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function InfoItem({ label, value, mono = false }) {
  return (
    <div>
      <p className="text-xs text-aethera-text-secondary">{label}</p>
      <p className={`text-sm text-aethera-foreground mt-0.5 ${mono ? 'font-mono' : ''}`}>{value}</p>
    </div>
  );
}