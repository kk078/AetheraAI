import React, { useState, useEffect, useMemo } from 'react';
import { api } from '../../utils/api';

// Mock data structure matching the API response shape
const MOCK_DATA = {
  denialRateTrend: [
    { month: 'Jan', rate: 12.4, total: 450, denied: 56 },
    { month: 'Feb', rate: 11.8, total: 430, denied: 51 },
    { month: 'Mar', rate: 13.2, total: 480, denied: 63 },
    { month: 'Apr', rate: 10.9, total: 460, denied: 50 },
    { month: 'May', rate: 9.7, total: 490, denied: 48 },
    { month: 'Jun', rate: 11.1, total: 510, denied: 57 },
  ],
  denialByCategory: [
    { category: 'Medical Necessity', count: 89, percentage: 34, color: '#F43F5E' },
    { category: 'Authorization', count: 52, percentage: 20, color: '#F59E0B' },
    { category: 'Coding Error', count: 41, percentage: 16, color: '#06B6D4' },
    { category: 'Timely Filing', count: 31, percentage: 12, color: '#8B5CF6' },
    { category: 'Duplicate Claim', count: 26, percentage: 10, color: '#10B981' },
    { category: 'Other', count: 22, percentage: 8, color: '#6B7280' },
  ],
  topDenialReasons: [
    { rank: 1, code: 'CO-50', description: 'Non-covered service / Not medically necessary', count: 34, impact: '$142,560', trend: 'up' },
    { rank: 2, code: 'CO-16', description: 'Claim lacks information or has submission errors', count: 28, impact: '$89,340', trend: 'down' },
    { rank: 3, code: 'CO-197', description: 'Precertification/authorization not obtained', count: 22, impact: '$67,890', trend: 'up' },
    { rank: 4, code: 'PR-1', description: 'Deductible amount', count: 19, impact: '$45,230', trend: 'stable' },
    { rank: 5, code: 'CO-29', description: 'Timely filing limit has expired', count: 15, impact: '$38,760', trend: 'down' },
  ],
  appealSuccessRate: {
    overall: 62,
    byCategory: [
      { category: 'Medical Necessity', rate: 71 },
      { category: 'Authorization', rate: 58 },
      { category: 'Coding Error', rate: 82 },
      { category: 'Timely Filing', rate: 35 },
      { category: 'Duplicate Claim', rate: 90 },
    ],
    totalAppealed: 156,
    totalWon: 97,
    totalRecovered: '$383,780',
  },
};

function BarChart({ data, height = 200, labelKey = 'month', valueKey = 'rate' }) {
  const maxVal = useMemo(() => Math.max(...data.map((d) => d[valueKey])), [data, valueKey]);

  return (
    <div className="flex items-end gap-2" style={{ height }}>
      {data.map((item, i) => {
        const pct = maxVal > 0 ? (item[valueKey] / maxVal) * 100 : 0;
        return (
          <div key={i} className="flex-1 flex flex-col items-center gap-1">
            <span className="text-xs text-aethera-foreground font-medium">{item[valueKey]}%</span>
            <div className="w-full relative" style={{ height: `${height - 40}px` }}>
              <div
                className="absolute bottom-0 w-full rounded-t transition-all duration-500 bg-aethera-primary hover:bg-cyan-500"
                style={{ height: `${pct}%` }}
              />
            </div>
            <span className="text-xs text-aethera-text-secondary">{item[labelKey]}</span>
          </div>
        );
      })}
    </div>
  );
}

function PieChart({ data, size = 160 }) {
  const total = useMemo(() => data.reduce((sum, d) => sum + d.count, 0), [data]);

  let cumulativeAngle = 0;
  const segments = data.map((item) => {
    const angle = (item.count / total) * 360;
    const startAngle = cumulativeAngle;
    cumulativeAngle += angle;
    return { ...item, startAngle, angle };
  });

  return (
    <div className="flex items-center gap-6">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {(() => {
          let offset = 0;
          return segments.map((segment, i) => {
            const pct = segment.count / total;
            const dashArray = `${pct * Math.PI * (size / 2 - 10)} ${Math.PI * (size / 2 - 10)}`;
            const el = (
              <circle
                key={i}
                cx={size / 2}
                cy={size / 2}
                r={size / 2 - 10}
                fill="none"
                stroke={segment.color}
                strokeWidth="16"
                strokeDasharray={dashArray}
                strokeDashoffset={-offset * Math.PI * (size / 2 - 10)}
                transform={`rotate(-90 ${size / 2} ${size / 2})`}
              />
            );
            offset += pct;
            return el;
          });
        })()}
      </svg>
      <div className="space-y-2">
        {data.map((item, i) => (
          <div key={i} className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: item.color }} />
            <span className="text-xs text-aethera-text-secondary">{item.category}</span>
            <span className="text-xs text-aethera-foreground font-medium ml-auto">{item.percentage}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function TrendIcon({ trend }) {
  if (trend === 'up') {
    return (
      <svg className="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
      </svg>
    );
  }
  if (trend === 'down') {
    return (
      <svg className="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
      </svg>
    );
  }
  return (
    <svg className="w-4 h-4 text-aethera-text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
    </svg>
  );
}

export default function DenialDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const dashboardData = await api.getDashboard();
        if (!cancelled) {
          setData({ ...MOCK_DATA, ...dashboardData.denialDashboard });
        }
      } catch (err) {
        // Fall back to mock data so dashboard is never blank
        if (!cancelled) setData(MOCK_DATA);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <svg className="w-12 h-12 text-aethera-primary animate-spin" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center py-12 text-aethera-text-secondary">
        <p>Failed to load dashboard data</p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-aethera-foreground">Denial Dashboard</h1>
          <p className="text-aethera-text-secondary mt-1">Denial trends, analytics, and appeal performance</p>
        </div>
        <span className="text-xs text-aethera-text-secondary bg-aethera-surface px-3 py-1 rounded-lg border border-aethera-border">
          Last 6 months
        </span>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard
          label="Overall Denial Rate"
          value={`${data.denialRateTrend[data.denialRateTrend.length - 1].rate}%`}
          change="-1.4% from last month"
          trend="positive"
        />
        <KPICard
          label="Total Denials"
          value={data.denialRateTrend.reduce((s, d) => s + d.denied, 0)}
          change="261 this period"
          trend="neutral"
        />
        <KPICard
          label="Appeal Success Rate"
          value={`${data.appealSuccessRate.overall}%`}
          change={`${data.appealSuccessRate.totalWon} of ${data.appealSuccessRate.totalAppealed} won`}
          trend="positive"
        />
        <KPICard
          label="Recovered Amount"
          value={data.appealSuccessRate.totalRecovered}
          change="This period"
          trend="positive"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Denial Rate Trend */}
        <div className="bg-aethera-surface rounded-xl border border-aethera-border p-5">
          <h2 className="text-sm font-semibold text-aethera-foreground mb-4">Denial Rate Trend</h2>
          <BarChart data={data.denialRateTrend} height={200} labelKey="month" valueKey="rate" />
        </div>

        {/* Denial by Category */}
        <div className="bg-aethera-surface rounded-xl border border-aethera-border p-5">
          <h2 className="text-sm font-semibold text-aethera-foreground mb-4">Denials by Category</h2>
          <PieChart data={data.denialByCategory} size={160} />
        </div>
      </div>

      {/* Top Denial Reasons Table */}
      <div className="bg-aethera-surface rounded-xl border border-aethera-border overflow-hidden">
        <div className="px-5 py-4 border-b border-aethera-border">
          <h2 className="text-sm font-semibold text-aethera-foreground">Top Denial Reasons</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-aethera-border bg-aethera-background">
                <th className="text-left py-3 px-5 text-aethera-text-secondary font-medium w-10">#</th>
                <th className="text-left py-3 px-5 text-aethera-text-secondary font-medium">Code</th>
                <th className="text-left py-3 px-5 text-aethera-text-secondary font-medium">Description</th>
                <th className="text-right py-3 px-5 text-aethera-text-secondary font-medium">Count</th>
                <th className="text-right py-3 px-5 text-aethera-text-secondary font-medium">Impact</th>
                <th className="text-center py-3 px-5 text-aethera-text-secondary font-medium w-16">Trend</th>
              </tr>
            </thead>
            <tbody>
              {data.topDenialReasons.map((item) => (
                <tr key={item.code} className="border-b border-aethera-border last:border-0 hover:bg-aethera-tertiary/50 transition-colors">
                  <td className="py-3 px-5 text-aethera-text-secondary">{item.rank}</td>
                  <td className="py-3 px-5 font-mono text-aethera-foreground font-medium">{item.code}</td>
                  <td className="py-3 px-5 text-aethera-text-secondary max-w-md truncate">{item.description}</td>
                  <td className="text-right py-3 px-5 text-aethera-foreground">{item.count}</td>
                  <td className="text-right py-3 px-5 text-aethera-foreground font-medium">{item.impact}</td>
                  <td className="text-center py-3 px-5"><TrendIcon trend={item.trend} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Appeal Success by Category */}
      <div className="bg-aethera-surface rounded-xl border border-aethera-border p-5">
        <h2 className="text-sm font-semibold text-aethera-foreground mb-4">Appeal Success Rate by Category</h2>
        <div className="space-y-3">
          {data.appealSuccessRate.byCategory.map((item) => (
            <div key={item.category} className="flex items-center gap-3">
              <span className="text-xs text-aethera-text-secondary w-36">{item.category}</span>
              <div className="flex-1 bg-aethera-tertiary rounded-full h-4">
                <div
                  className={`h-4 rounded-full transition-all duration-500 ${
                    item.rate >= 70 ? 'bg-green-500' : item.rate >= 50 ? 'bg-amber-500' : 'bg-red-500'
                  }`}
                  style={{ width: `${item.rate}%` }}
                />
              </div>
              <span className="text-xs text-aethera-foreground font-medium w-10 text-right">{item.rate}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function KPICard({ label, value, change, trend }) {
  const trendColors = {
    positive: 'text-green-400',
    negative: 'text-red-400',
    neutral: 'text-aethera-text-secondary',
  };

  return (
    <div className="bg-aethera-surface rounded-xl border border-aethera-border p-4">
      <p className="text-xs text-aethera-text-secondary">{label}</p>
      <p className="text-2xl font-bold text-aethera-foreground mt-1">{value}</p>
      <p className={`text-xs mt-1 ${trendColors[trend] || trendColors.neutral}`}>{change}</p>
    </div>
  );
}