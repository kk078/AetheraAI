import React, { useState, useEffect } from 'react';
import { api } from '../../utils/api';
import SpecialistBadge from '../specialists/SpecialistBadge';
import ConfidenceBadge from '../common/ConfidenceBadge';

export default function HealthcareDashboard() {
  const [stats, setStats] = useState({
    claimsPending: 0,
    claimsDenied: 0,
    pendingAuths: 0,
    riskAdjustment: 0,
  });
  const [recentActivity, setRecentActivity] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      const dashboardData = await api.getDashboard();
      const usage = dashboardData?.usage || {};
      setStats({
        claimsPending: usage.queries_today ?? usage.claims_pending ?? 0,
        claimsDenied: usage.denials_today ?? usage.claims_denied ?? 0,
        pendingAuths: usage.pending_auths ?? 0,
        riskAdjustment: usage.risk_score ?? 0,
      });
      setRecentActivity(dashboardData?.recent_activity || []);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
      // Show empty state on error
      setStats({ claimsPending: 0, claimsDenied: 0, pendingAuths: 0, riskAdjustment: 0 });
      setRecentActivity([]);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-aethera-primary"></div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-aethera-foreground">Healthcare Dashboard</h1>
          <p className="text-aethera-text-secondary mt-1">Revenue cycle and operations overview</p>
        </div>
        <SpecialistBadge specialist="healthcare_provider" size="md" />
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Claims Pending"
          value={stats.claimsPending}
          change="+3 from yesterday"
          trend="neutral"
          icon={
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          }
        />
        <StatCard
          title="Claims Denied"
          value={stats.claimsDenied}
          change="-2 from yesterday"
          trend="positive"
          icon={
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />
        <StatCard
          title="Pending Auths"
          value={stats.pendingAuths}
          change="+5 from yesterday"
          trend="negative"
          icon={
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />
        <StatCard
          title="Risk Adjustment"
          value={stats.riskAdjustment.toFixed(3)}
          change="+0.023 from last month"
          trend="positive"
          icon={
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
          }
        />
      </div>

      {/* Recent Activity */}
      <div className="bg-aethera-surface rounded-xl border border-aethera-border overflow-hidden">
        <div className="px-4 py-3 border-b border-aethera-border flex items-center justify-between">
          <h2 className="font-semibold text-aethera-foreground">Recent Activity</h2>
          <button className="text-sm text-aethera-primary hover:underline">View All</button>
        </div>
        <div className="divide-y divide-aethera-border">
          {recentActivity.length === 0 ? (
            <div className="p-8 text-center text-aethera-text-secondary">
              No recent activity. Start by asking a question in the chat.
            </div>
          ) : (
            recentActivity.map((item, index) => (
              <div key={index} className="p-4 hover:bg-aethera-tertiary/50 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <ActivityIcon type={item.type} />
                    <div>
                      <p className="text-sm font-medium text-aethera-foreground">{item.description}</p>
                      <p className="text-xs text-aethera-text-secondary mt-1">{item.code}</p>
                    </div>
                  </div>
                  <span className="text-xs text-aethera-text-secondary">{item.time}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <QuickActionCard
          title="Code Lookup"
          description="Look up ICD-10, CPT, HCPCS codes"
          icon={
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          }
          action="/code"
        />
        <QuickActionCard
          title="Denial Analysis"
          description="Analyze CARC/RARC codes"
          icon={
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          }
          action="/denial"
        />
        <QuickActionCard
          title="Fee Schedule"
          description="Check Medicare fee schedules"
          icon={
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
          action="/fee"
        />
      </div>
    </div>
  );
}

function StatCard({ title, value, change, trend, icon }) {
  const trendColors = {
    positive: 'text-green-400',
    negative: 'text-red-400',
    neutral: 'text-aethera-text-secondary',
  };

  return (
    <div className="bg-aethera-surface rounded-xl border border-aethera-border p-4">
      <div className="flex items-center justify-between">
        <div className="text-aethera-text-secondary">{icon}</div>
        <span className={`text-xs ${trendColors[trend]}`}>{change}</span>
      </div>
      <div className="mt-3">
        <p className="text-2xl font-bold text-aethera-foreground">{value}</p>
        <p className="text-sm text-aethera-text-secondary mt-1">{title}</p>
      </div>
    </div>
  );
}

function QuickActionCard({ title, description, icon, action }) {
  return (
    <button
      onClick={() => window.dispatchEvent(new CustomEvent('aethera-command', { detail: action }))}
      className="bg-aethera-surface rounded-xl border border-aethera-border p-4 hover:border-aethera-primary transition-colors text-left group"
    >
      <div className="text-aethera-primary group-hover:scale-110 transition-transform">{icon}</div>
      <h3 className="font-medium text-aethera-foreground mt-3">{title}</h3>
      <p className="text-sm text-aethera-text-secondary mt-1">{description}</p>
    </button>
  );
}

function ActivityIcon({ type }) {
  const icons = {
    denial: (
      <div className="w-8 h-8 rounded-full bg-red-500/20 flex items-center justify-center">
        <svg className="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </div>
    ),
    auth: (
      <div className="w-8 h-8 rounded-full bg-amber-500/20 flex items-center justify-center">
        <svg className="w-4 h-4 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
        </svg>
      </div>
    ),
    claim: (
      <div className="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center">
        <svg className="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
    ),
    edi: (
      <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center">
        <svg className="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      </div>
    ),
  };

  return icons[type] || icons.claim;
}
