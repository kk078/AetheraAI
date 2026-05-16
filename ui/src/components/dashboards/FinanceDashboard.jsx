import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../../utils/api';

export default function FinanceDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const json = await api.getDashboard();
      setData(json);
    } catch (err) {
      setError(err.message || 'Failed to load finance data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-aethera-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400">
          <p className="font-medium">Failed to load finance dashboard</p>
          <p className="text-sm mt-1">{error}</p>
          <button onClick={fetchData} className="mt-2 text-sm underline hover:no-underline">Retry</button>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="p-6 text-center text-aethera-text-secondary">
        No finance data available.
      </div>
    );
  }

  const { income = 0, expenses = 0, revenueProjection = 0, cashFlow = [], topExpenseCategories = [], budgetVsActual = [] } = data;
  const netIncome = income - expenses;
  const maxCashFlow = Math.max(...cashFlow.map((c) => Math.abs(c.amount)), 1);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-aethera-foreground">Finance Dashboard</h1>
          <p className="text-aethera-text-secondary mt-1">Income, expenses, and projections overview</p>
        </div>
        <button
          onClick={fetchData}
          className="text-sm text-aethera-primary hover:underline flex items-center gap-1"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard title="Total Income" value={formatCurrency(income)} trend="up" color="text-green-400" icon={<CurrencyIcon />} />
        <SummaryCard title="Total Expenses" value={formatCurrency(expenses)} trend="down" color="text-red-400" icon={<ExpenseIcon />} />
        <SummaryCard title="Net Income" value={formatCurrency(netIncome)} trend={netIncome >= 0 ? 'up' : 'down'} color={netIncome >= 0 ? 'text-green-400' : 'text-red-400'} icon={<NetIcon />} />
        <SummaryCard title="Revenue Projection" value={formatCurrency(revenueProjection)} trend="up" color="text-aethera-primary" icon={<ProjectionIcon />} />
      </div>

      {/* Cash Flow Chart */}
      <div className="bg-aethera-surface rounded-xl border border-aethera-border overflow-hidden">
        <div className="px-4 py-3 border-b border-aethera-border">
          <h2 className="font-semibold text-aethera-foreground">Cash Flow</h2>
        </div>
        <div className="p-4">
          {cashFlow.length === 0 ? (
            <p className="text-aethera-text-secondary text-sm text-center py-8">No cash flow data available</p>
          ) : (
            <div className="flex items-end gap-2 h-48">
              {cashFlow.map((entry, i) => {
                const heightPct = Math.max((Math.abs(entry.amount) / maxCashFlow) * 100, 4);
                const isPositive = entry.amount >= 0;
                return (
                  <div key={i} className="flex-1 flex flex-col items-center gap-1">
                    <span className="text-xs text-aethera-text-secondary">{formatCurrency(entry.amount)}</span>
                    <div
                      className={`w-full rounded-t ${isPositive ? 'bg-green-500/70' : 'bg-red-500/70'}`}
                      style={{ height: `${heightPct}%` }}
                    />
                    <span className="text-xs text-aethera-text-secondary truncate w-full text-center">{entry.label}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Top Expense Categories */}
        <div className="bg-aethera-surface rounded-xl border border-aethera-border overflow-hidden">
          <div className="px-4 py-3 border-b border-aethera-border">
            <h2 className="font-semibold text-aethera-foreground">Top Expense Categories</h2>
          </div>
          <div className="divide-y divide-aethera-border">
            {topExpenseCategories.length === 0 ? (
              <p className="p-4 text-aethera-text-secondary text-sm text-center">No expense data</p>
            ) : (
              topExpenseCategories.map((cat, i) => (
                <div key={i} className="p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-aethera-foreground">{cat.name}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-32 bg-aethera-tertiary rounded-full h-2">
                      <div className="bg-red-400 h-2 rounded-full" style={{ width: `${cat.percentage}%` }} />
                    </div>
                    <span className="text-sm text-aethera-text-secondary w-16 text-right">{cat.percentage}%</span>
                    <span className="text-sm text-aethera-foreground w-24 text-right">{formatCurrency(cat.amount)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Budget vs Actual */}
        <div className="bg-aethera-surface rounded-xl border border-aethera-border overflow-hidden">
          <div className="px-4 py-3 border-b border-aethera-border">
            <h2 className="font-semibold text-aethera-foreground">Budget vs Actual</h2>
          </div>
          <div className="divide-y divide-aethera-border">
            {budgetVsActual.length === 0 ? (
              <p className="p-4 text-aethera-text-secondary text-sm text-center">No budget data</p>
            ) : (
              budgetVsActual.map((item, i) => {
                const variance = item.actual - item.budget;
                const overBudget = variance > 0;
                return (
                  <div key={i} className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-aethera-foreground">{item.category}</span>
                      <span className={`text-xs ${overBudget ? 'text-red-400' : 'text-green-400'}`}>
                        {overBudget ? '+' : ''}{formatCurrency(variance)}
                      </span>
                    </div>
                    <div className="flex gap-2 items-center">
                      <div className="flex-1">
                        <div className="flex items-center gap-1 mb-1">
                          <span className="text-xs text-aethera-text-secondary">Budget</span>
                          <span className="text-xs text-aethera-foreground">{formatCurrency(item.budget)}</span>
                        </div>
                        <div className="w-full bg-aethera-tertiary rounded-full h-2">
                          <div className="bg-aethera-primary h-2 rounded-full" style={{ width: '100%' }} />
                        </div>
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-1 mb-1">
                          <span className="text-xs text-aethera-text-secondary">Actual</span>
                          <span className="text-xs text-aethera-foreground">{formatCurrency(item.actual)}</span>
                        </div>
                        <div className="w-full bg-aethera-tertiary rounded-full h-2">
                          <div
                            className={`${overBudget ? 'bg-red-400' : 'bg-green-400'} h-2 rounded-full`}
                            style={{ width: `${Math.min((item.actual / Math.max(item.budget, 1)) * 100, 100)}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function SummaryCard({ title, value, trend, color, icon }) {
  return (
    <div className="bg-aethera-surface rounded-xl border border-aethera-border p-4">
      <div className="flex items-center justify-between">
        <div className="text-aethera-text-secondary">{icon}</div>
        <span className={`text-xs ${color}`}>
          {trend === 'up' ? (
            <svg className="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
            </svg>
          ) : (
            <svg className="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
          )}
        </span>
      </div>
      <p className={`text-2xl font-bold mt-3 ${color}`}>{value}</p>
      <p className="text-sm text-aethera-text-secondary mt-1">{title}</p>
    </div>
  );
}

function CurrencyIcon() {
  return (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}

function ExpenseIcon() {
  return (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
    </svg>
  );
}

function NetIcon() {
  return (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
    </svg>
  );
}

function ProjectionIcon() {
  return (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
    </svg>
  );
}

function formatCurrency(amount) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(amount);
}