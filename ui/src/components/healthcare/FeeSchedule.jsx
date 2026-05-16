import React, { useState, useCallback } from 'react';
import { api } from '../../utils/api';

const LOCALITIES = [
  { value: '00', label: 'National' },
  { value: '01', label: 'Alabama' },
  { value: '02', label: 'Alaska' },
  { value: '04', label: 'Arizona' },
  { value: '05', label: 'Arkansas' },
  { value: '06', label: 'California - Northern' },
  { value: '07', label: 'California - Southern' },
  { value: '08', label: 'Colorado' },
  { value: '09', label: 'Connecticut' },
  { value: '10', label: 'Delaware' },
  { value: '11', label: 'DC' },
  { value: '12', label: 'Florida' },
  { value: '13', label: 'Georgia' },
  { value: '15', label: 'Hawaii' },
  { value: '16', label: 'Idaho' },
  { value: '17', label: 'Illinois - Chicago' },
  { value: '18', label: 'Illinois - Downstate' },
  { value: '19', label: 'Indiana' },
  { value: '20', label: 'Iowa' },
  { value: '21', label: 'Kansas' },
  { value: '22', label: 'Kentucky' },
  { value: '23', label: 'Louisiana' },
  { value: '24', label: 'Maine' },
  { value: '25', label: 'Maryland' },
  { value: '26', label: 'Massachusetts - Boston' },
  { value: '99', label: 'Rest of US (sample)' },
];

function formatCurrency(value) {
  if (value === null || value === undefined) return '$0.00';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
}

export default function FeeSchedule() {
  const [cptCode, setCptCode] = useState('');
  const [locality, setLocality] = useState('00');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleLookup = useCallback(async (e) => {
    e.preventDefault();
    if (!cptCode.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const data = await api.getFeeSchedule(cptCode.trim(), locality);
      setResult(data);
    } catch (err) {
      setError(err.message || 'Fee schedule lookup failed');
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, [cptCode, locality]);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-aethera-foreground">Fee Schedule</h1>
        <p className="text-aethera-text-secondary mt-1">Medicare fee schedule lookup with RVU breakdown</p>
      </div>

      {/* Search Form */}
      <form onSubmit={handleLookup} className="space-y-3">
        <div className="flex gap-3">
          <input
            type="text"
            value={cptCode}
            onChange={(e) => setCptCode(e.target.value)}
            placeholder="Enter CPT code (e.g., 99213)"
            className="flex-1 bg-aethera-surface border border-aethera-border rounded-lg px-4 py-2.5 text-aethera-foreground placeholder-aethera-text-secondary focus:border-aethera-primary focus:outline-none font-mono"
          />
          <div className="relative">
            <select
              value={locality}
              onChange={(e) => setLocality(e.target.value)}
              className="appearance-none bg-aethera-surface border border-aethera-border rounded-lg px-4 py-2.5 pr-8 text-sm text-aethera-foreground focus:border-aethera-primary focus:outline-none cursor-pointer min-w-[180px]"
            >
              {LOCALITIES.map((loc) => (
                <option key={loc.value} value={loc.value}>{loc.label}</option>
              ))}
            </select>
            <svg className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-aethera-text-secondary pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
          <button
            type="submit"
            disabled={loading || !cptCode.trim()}
            className="px-6 py-2.5 bg-aethera-primary hover:bg-cyan-600 disabled:bg-aethera-tertiary disabled:text-aethera-text-secondary text-white rounded-lg font-medium transition-colors"
          >
            {loading ? 'Looking up...' : 'Lookup'}
          </button>
        </div>
      </form>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className="bg-aethera-surface rounded-xl border border-aethera-border p-6 space-y-4 animate-pulse">
          <div className="h-6 bg-aethera-tertiary rounded w-1/3" />
          <div className="grid grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="space-y-2">
                <div className="h-4 bg-aethera-tertiary rounded w-1/2" />
                <div className="h-6 bg-aethera-tertiary rounded w-2/3" />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Results */}
      {result && !loading && (
        <div className="space-y-6 animate-fade-in">
          {/* CPT Info */}
          <div className="bg-aethera-surface rounded-xl border border-aethera-border p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h2 className="text-lg font-semibold text-aethera-foreground">
                  CPT {result.cpt_code || cptCode}
                </h2>
                <p className="text-sm text-aethera-text-secondary mt-1">
                  {result.description || result.long_description || 'No description available'}
                </p>
              </div>
              {result.status && (
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                  result.status === 'active'
                    ? 'bg-green-500/20 text-green-400'
                    : 'bg-red-500/20 text-red-400'
                }`}>
                  {result.status.toUpperCase()}
                </span>
              )}
            </div>

            {/* Locality info */}
            <p className="text-xs text-aethera-text-secondary mb-4">
              Locality: {LOCALITIES.find((l) => l.value === locality)?.label || locality}
              {result.year && ` | Year: ${result.year}`}
            </p>

            {/* RVU Breakdown */}
            {(result.work_rvu !== undefined || result.pe_rvu !== undefined || result.mp_rvu !== undefined) && (
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-aethera-foreground">RVU Breakdown</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <RVUCard
                    label="Work RVU"
                    value={result.work_rvu}
                    gpc={result.work_gpc}
                    payment={result.work_payment}
                    color="text-blue-400"
                    bgColor="bg-blue-500/10"
                  />
                  <RVUCard
                    label="Practice Expense RVU"
                    value={result.pe_rvu}
                    gpc={result.pe_gpc}
                    payment={result.pe_payment}
                    color="text-purple-400"
                    bgColor="bg-purple-500/10"
                  />
                  <RVUCard
                    label="Malpractice RVU"
                    value={result.mp_rvu}
                    gpc={result.mp_gpc}
                    payment={result.mp_payment}
                    color="text-amber-400"
                    bgColor="bg-amber-500/10"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Reimbursement Summary */}
          <div className="bg-aethera-surface rounded-xl border border-aethera-border p-6">
            <h3 className="text-sm font-semibold text-aethera-foreground mb-4">Reimbursement Calculation</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <SummaryItem
                label="Total RVUs"
                value={result.total_rvu !== undefined ? result.total_rvu.toFixed(2) : '--'}
              />
              <SummaryItem
                label="Conversion Factor"
                value={result.conversion_factor !== undefined ? formatCurrency(result.conversion_factor) : '--'}
              />
              <SummaryItem
                label="Facility Rate"
                value={result.facility_rate !== undefined ? formatCurrency(result.facility_rate) : formatCurrency(result.total_payment)}
              />
              <SummaryItem
                label="Non-Facility Rate"
                value={result.non_facility_rate !== undefined ? formatCurrency(result.non_facility_rate) : '--'}
              />
            </div>

            {/* Modifiers */}
            {result.modifiers && result.modifiers.length > 0 && (
              <div className="mt-4 pt-4 border-t border-aethera-border">
                <h4 className="text-xs font-medium text-aethera-text-secondary mb-2">Applicable Modifiers</h4>
                <div className="flex flex-wrap gap-2">
                  {result.modifiers.map((mod) => (
                    <span key={mod.code || mod} className="text-xs font-mono bg-aethera-tertiary px-2 py-1 rounded text-aethera-foreground">
                      {typeof mod === 'string' ? mod : `${mod.code}: ${mod.description}`}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Calculation detail */}
          {result.calculation && (
            <div className="bg-aethera-surface rounded-xl border border-aethera-border p-6">
              <h3 className="text-sm font-semibold text-aethera-foreground mb-3">Calculation Detail</h3>
              <pre className="text-xs text-aethera-text-secondary font-mono whitespace-pre-wrap bg-aethera-background rounded-lg p-4 border border-aethera-border overflow-x-auto">
                {typeof result.calculation === 'string'
                  ? result.calculation
                  : JSON.stringify(result.calculation, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function RVUCard({ label, value, gpc, payment, color, bgColor }) {
  return (
    <div className={`${bgColor} rounded-lg p-4 border border-aethera-border`}>
      <p className="text-xs text-aethera-text-secondary mb-1">{label}</p>
      <p className={`text-xl font-bold ${color}`}>{value !== undefined ? value.toFixed(2) : '--'}</p>
      <div className="mt-2 space-y-1">
        {gpc !== undefined && (
          <div className="flex justify-between text-xs">
            <span className="text-aethera-text-secondary">GPC</span>
            <span className="text-aethera-foreground">{gpc.toFixed(4)}</span>
          </div>
        )}
        {payment !== undefined && (
          <div className="flex justify-between text-xs">
            <span className="text-aethera-text-secondary">Payment</span>
            <span className="text-aethera-foreground font-medium">{formatCurrency(payment)}</span>
          </div>
        )}
      </div>
    </div>
  );
}

function SummaryItem({ label, value }) {
  return (
    <div>
      <p className="text-xs text-aethera-text-secondary">{label}</p>
      <p className="text-lg font-semibold text-aethera-foreground mt-1">{value}</p>
    </div>
  );
}