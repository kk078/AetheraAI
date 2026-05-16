import React, { useState } from 'react';
import { api } from '../../utils/api';
import SpecialistBadge from '../specialists/SpecialistBadge';
import ConfidenceBadge from '../common/ConfidenceBadge';

export default function ClaimAnalyzer() {
  const [claimId, setClaimId] = useState('');
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const analyzeClaim = async (e) => {
    e.preventDefault();
    if (!claimId.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const result = await api.analyzeClaim(claimId.trim());
      setAnalysis(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-aethera-foreground">Claim Analyzer</h1>
          <p className="text-aethera-text-secondary mt-1">Analyze claims for errors, denials, and optimization</p>
        </div>
        <SpecialistBadge specialist="healthcare_provider" size="md" />
      </div>

      {/* Search Form */}
      <form onSubmit={analyzeClaim} className="flex gap-3">
        <input
          type="text"
          value={claimId}
          onChange={(e) => setClaimId(e.target.value)}
          placeholder="Enter Claim ID (e.g., CLM-2024-001234)"
          className="flex-1 bg-aethera-surface border border-aethera-border rounded-lg px-4 py-2.5 text-aethera-foreground placeholder-aethera-text-secondary focus:border-aethera-primary focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading || !claimId.trim()}
          className="px-6 py-2.5 bg-aethera-primary hover:bg-cyan-600 disabled:bg-aethera-tertiary disabled:text-aethera-text-secondary text-white rounded-lg font-medium transition-colors"
        >
          {loading ? 'Analyzing...' : 'Analyze'}
        </button>
      </form>

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400">
          {error}
        </div>
      )}

      {/* Results */}
      {analysis && (
        <div className="space-y-6">
          {/* Summary */}
          <div className="bg-aethera-surface rounded-xl border border-aethera-border p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h2 className="text-lg font-semibold text-aethera-foreground">Claim Summary</h2>
                <p className="text-sm text-aethera-text-secondary mt-1">{analysis.claimId}</p>
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  analysis.status === 'paid' ? 'bg-green-500/20 text-green-400' :
                  analysis.status === 'denied' ? 'bg-red-500/20 text-red-400' :
                  'bg-amber-500/20 text-amber-400'
                }`}>
                  {analysis.status?.toUpperCase()}
                </span>
                {analysis.confidence && <ConfidenceBadge confidence={analysis.confidence} />}
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <SummaryItem label="Total Charges" value={formatCurrency(analysis.totalCharges)} />
              <SummaryItem label="Allowed Amount" value={formatCurrency(analysis.allowedAmount)} />
              <SummaryItem label="Patient Responsibility" value={formatCurrency(analysis.patientResponsibility)} />
              <SummaryItem label="Payment Amount" value={formatCurrency(analysis.paymentAmount)} />
            </div>
          </div>

          {/* Issues */}
          {analysis.issues?.length > 0 && (
            <div className="bg-aethera-surface rounded-xl border border-aethera-border p-6">
              <h2 className="text-lg font-semibold text-aethera-foreground mb-4">Identified Issues</h2>
              <div className="space-y-3">
                {analysis.issues.map((issue, index) => (
                  <div key={index} className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                    <div className="flex items-start gap-3">
                      <svg className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-amber-200">{issue.description}</p>
                        <p className="text-xs text-amber-300/80 mt-1">{issue.code}</p>
                        {issue.recommendation && (
                          <p className="text-sm text-amber-100/80 mt-2">{issue.recommendation}</p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Line Items */}
          {analysis.lineItems?.length > 0 && (
            <div className="bg-aethera-surface rounded-xl border border-aethera-border p-6">
              <h2 className="text-lg font-semibold text-aethera-foreground mb-4">Line Items</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-aethera-border">
                      <th className="text-left py-3 px-4 text-aethera-text-secondary font-medium">Date</th>
                      <th className="text-left py-3 px-4 text-aethera-text-secondary font-medium">Code</th>
                      <th className="text-left py-3 px-4 text-aethera-text-secondary font-medium">Description</th>
                      <th className="text-right py-3 px-4 text-aethera-text-secondary font-medium">Charges</th>
                      <th className="text-right py-3 px-4 text-aethera-text-secondary font-medium">Allowed</th>
                      <th className="text-right py-3 px-4 text-aethera-text-secondary font-medium">Paid</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analysis.lineItems.map((item, index) => (
                      <tr key={index} className="border-b border-aethera-border last:border-0">
                        <td className="py-3 px-4 text-aethera-foreground">{item.date}</td>
                        <td className="py-3 px-4 text-aethera-foreground font-mono">{item.code}</td>
                        <td className="py-3 px-4 text-aethera-text-secondary">{item.description}</td>
                        <td className="text-right py-3 px-4 text-aethera-foreground">{formatCurrency(item.charges)}</td>
                        <td className="text-right py-3 px-4 text-aethera-foreground">{formatCurrency(item.allowed)}</td>
                        <td className="text-right py-3 px-4 text-green-400">{formatCurrency(item.paid)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Recommendations */}
          {analysis.recommendations?.length > 0 && (
            <div className="bg-aethera-surface rounded-xl border border-aethera-border p-6">
              <h2 className="text-lg font-semibold text-aethera-foreground mb-4">Recommendations</h2>
              <div className="space-y-3">
                {analysis.recommendations.map((rec, index) => (
                  <div key={index} className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-green-500/20 flex items-center justify-center flex-shrink-0">
                      <span className="text-green-400 text-sm font-medium">{index + 1}</span>
                    </div>
                    <p className="text-sm text-aethera-foreground">{rec}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
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

function formatCurrency(value) {
  if (value === null || value === undefined) return '$0.00';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(value);
}
