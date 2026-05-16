import React, { useState, useCallback } from 'react';
import { api } from '../../utils/api';

export default function CoverageChecker() {
  const [cptCode, setCptCode] = useState('');
  const [diagnosisCode, setDiagnosisCode] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedSection, setExpandedSection] = useState(null);

  const handleCheck = useCallback(async (e) => {
    e.preventDefault();
    if (!cptCode.trim() || !diagnosisCode.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await api.post('/api/healthcare/coverage-check', {
        cpt_code: cptCode.trim(),
        diagnosis_code: diagnosisCode.trim(),
      });
      setResult(response);
    } catch (err) {
      setError(err.message || 'Coverage check failed');
    } finally {
      setLoading(false);
    }
  }, [cptCode, diagnosisCode]);

  const coverageStatus = result?.coverage_status || result?.status;
  const isCovered = coverageStatus === 'covered' || coverageStatus === 'yes' || coverageStatus === 'approved';
  const isConditional = coverageStatus === 'conditional' || coverageStatus === 'partial' || coverageStatus === 'requires_pa';
  const isDenied = coverageStatus === 'not_covered' || coverageStatus === 'denied' || coverageStatus === 'no';

  const statusConfig = isCovered
    ? { color: 'bg-green-500/20 text-green-400 border-green-500/30', icon: 'check', label: 'Covered' }
    : isConditional
      ? { color: 'bg-amber-500/20 text-amber-400 border-amber-500/30', icon: 'alert', label: 'Conditional' }
      : isDenied
        ? { color: 'bg-red-500/20 text-red-400 border-red-500/30', icon: 'x', label: 'Not Covered' }
        : { color: 'bg-aethera-tertiary text-aethera-text-secondary border-aethera-border', icon: 'unknown', label: coverageStatus || 'Unknown' };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-aethera-foreground">Coverage Checker</h1>
        <p className="text-aethera-text-secondary mt-1">Check LCD/NCD medical necessity criteria for CPT and diagnosis pairs</p>
      </div>

      {/* Search Form */}
      <form onSubmit={handleCheck} className="space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-aethera-foreground mb-1.5">CPT Code *</label>
            <input
              type="text"
              value={cptCode}
              onChange={(e) => setCptCode(e.target.value)}
              placeholder="e.g., 99213"
              className="w-full bg-aethera-surface border border-aethera-border rounded-lg px-4 py-2.5 text-aethera-foreground placeholder-aethera-text-secondary focus:border-aethera-primary focus:outline-none font-mono"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-aethera-foreground mb-1.5">Diagnosis (ICD-10) *</label>
            <input
              type="text"
              value={diagnosisCode}
              onChange={(e) => setDiagnosisCode(e.target.value)}
              placeholder="e.g., M54.5"
              className="w-full bg-aethera-surface border border-aethera-border rounded-lg px-4 py-2.5 text-aethera-foreground placeholder-aethera-text-secondary focus:border-aethera-primary focus:outline-none font-mono"
            />
          </div>
        </div>
        <button
          type="submit"
          disabled={loading || !cptCode.trim() || !diagnosisCode.trim()}
          className="px-6 py-2.5 bg-aethera-primary hover:bg-cyan-600 disabled:bg-aethera-tertiary disabled:text-aethera-text-secondary text-white rounded-lg font-medium transition-colors flex items-center gap-2"
        >
          {loading && (
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
          )}
          {loading ? 'Checking...' : 'Check Coverage'}
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
          {/* Coverage Status Banner */}
          <div className={`rounded-xl border p-6 ${statusConfig.color}`}>
            <div className="flex items-center gap-3">
              {statusConfig.icon === 'check' && (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              )}
              {statusConfig.icon === 'alert' && (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              )}
              {statusConfig.icon === 'x' && (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              )}
              {statusConfig.icon === 'unknown' && (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.458 2.574-3.014 2.887a1.5 1.5 0 00-.986 1.487V14M12 18h.01" />
                </svg>
              )}
              <div>
                <h2 className="text-lg font-semibold">{statusConfig.label}</h2>
                <p className="text-sm opacity-80 mt-0.5">
                  CPT {cptCode} + ICD-10 {diagnosisCode}
                </p>
              </div>
            </div>
          </div>

          {/* LCD/NCD References */}
          {(result.lcd || result.ncd || result.references) && (
            <div className="bg-aethera-surface rounded-xl border border-aethera-border p-6">
              <h3 className="text-sm font-semibold text-aethera-foreground mb-3">LCD/NCD References</h3>
              <div className="space-y-3">
                {result.ncd && (
                  <ReferenceItem
                    type="NCD"
                    id={result.ncd.number || result.ncd.id || result.ncd}
                    title={result.ncd.title || result.ncd.name || ''}
                    description={result.ncd.description || ''}
                  />
                )}
                {result.lcd && (
                  <ReferenceItem
                    type="LCD"
                    id={result.lcd.number || result.lcd.id || result.lcd}
                    title={result.lcd.title || result.lcd.name || ''}
                    description={result.lcd.description || ''}
                  />
                )}
                {result.references && Array.isArray(result.references) && result.references.map((ref, i) => (
                  <ReferenceItem
                    key={i}
                    type={ref.type || 'Reference'}
                    id={ref.number || ref.id || ''}
                    title={ref.title || ref.name || ''}
                    description={ref.description || ''}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Coverage Criteria */}
          {result.coverage_criteria && (
            <CollapsibleSection
              title="Coverage Criteria"
              isOpen={expandedSection === 'criteria'}
              onToggle={() => setExpandedSection(expandedSection === 'criteria' ? null : 'criteria')}
            >
              {Array.isArray(result.coverage_criteria) ? (
                <ul className="space-y-2">
                  {result.coverage_criteria.map((criterion, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="w-5 h-5 rounded-full bg-aethera-primary/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                        <span className="text-aethera-primary text-xs font-medium">{i + 1}</span>
                      </span>
                      <span className="text-sm text-aethera-text-secondary">
                        {typeof criterion === 'string' ? criterion : criterion.description || criterion.criterion || JSON.stringify(criterion)}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-aethera-text-secondary leading-relaxed">{result.coverage_criteria}</p>
              )}
            </CollapsibleSection>
          )}

          {/* Required Documentation */}
          {result.required_documentation && (
            <CollapsibleSection
              title="Required Documentation"
              isOpen={expandedSection === 'documentation'}
              onToggle={() => setExpandedSection(expandedSection === 'documentation' ? null : 'documentation')}
            >
              {Array.isArray(result.required_documentation) ? (
                <ul className="space-y-2">
                  {result.required_documentation.map((doc, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <svg className="w-4 h-4 text-aethera-primary flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      <span className="text-sm text-aethera-text-secondary">
                        {typeof doc === 'string' ? doc : doc.name || doc.description || JSON.stringify(doc)}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-aethera-text-secondary leading-relaxed">{result.required_documentation}</p>
              )}
            </CollapsibleSection>
          )}

          {/* Limitations */}
          {result.limitations && (
            <CollapsibleSection
              title="Limitations"
              isOpen={expandedSection === 'limitations'}
              onToggle={() => setExpandedSection(expandedSection === 'limitations' ? null : 'limitations')}
            >
              {Array.isArray(result.limitations) ? (
                <ul className="space-y-2">
                  {result.limitations.map((lim, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-400 mt-2 flex-shrink-0" />
                      <span className="text-sm text-aethera-text-secondary">
                        {typeof lim === 'string' ? lim : lim.description || JSON.stringify(lim)}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-aethera-text-secondary leading-relaxed">{result.limitations}</p>
              )}
            </CollapsibleSection>
          )}

          {/* Prior Auth Info */}
          {result.prior_authorization && (
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-6">
              <div className="flex items-center gap-2 mb-2">
                <svg className="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
                <h3 className="text-sm font-semibold text-amber-400">Prior Authorization Required</h3>
              </div>
              <p className="text-sm text-amber-200/80">
                {typeof result.prior_authorization === 'string'
                  ? result.prior_authorization
                  : result.prior_authorization.description || result.prior_authorization.notes || JSON.stringify(result.prior_authorization)}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function CollapsibleSection({ title, isOpen, onToggle, children }) {
  return (
    <div className="bg-aethera-surface rounded-xl border border-aethera-border overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-6 py-4 hover:bg-aethera-tertiary/50 transition-colors"
      >
        <h3 className="text-sm font-semibold text-aethera-foreground">{title}</h3>
        <svg className={`w-4 h-4 text-aethera-text-secondary transition-transform ${isOpen ? 'rotate-90' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </button>
      {isOpen && (
        <div className="px-6 pb-4 animate-fade-in">
          {children}
        </div>
      )}
    </div>
  );
}

function ReferenceItem({ type, id, title, description }) {
  const typeColor = type === 'NCD'
    ? 'bg-blue-500/20 text-blue-400 border-blue-500/30'
    : type === 'LCD'
      ? 'bg-purple-500/20 text-purple-400 border-purple-500/30'
      : 'bg-aethera-tertiary text-aethera-text-secondary border-aethera-border';

  return (
    <div className="p-3 bg-aethera-background rounded-lg border border-aethera-border">
      <div className="flex items-center gap-2 mb-1">
        <span className={`text-xs px-2 py-0.5 rounded-full border ${typeColor}`}>{type}</span>
        <span className="text-sm font-mono text-aethera-foreground">{id}</span>
      </div>
      {title && <p className="text-sm text-aethera-foreground font-medium">{title}</p>}
      {description && <p className="text-xs text-aethera-text-secondary mt-1">{description}</p>}
    </div>
  );
}