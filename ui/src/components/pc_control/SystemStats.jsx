/**
 * Aethera AI — System Stats Panel
 * Displays CPU, RAM, GPU, disk, and network statistics.
 */
import { useState, useEffect } from 'react';

export default function SystemStats({ pc }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    setLoading(true);
    const result = await pc.sendCommand('system.stats', {});
    if (result?.success) setStats(result.data);
    setLoading(false);
  };

  useEffect(() => { refresh(); }, []);

  const StatCard = ({ title, value, unit, icon, color = 'cyan' }) => (
    <div className={`rounded-lg border border-[var(--color-border)] p-4`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-[var(--color-text-secondary)]">{icon} {title}</span>
        <span className="text-lg font-bold text-[var(--color-text-primary)]">
          {value ?? '—'}<span className="text-xs text-[var(--color-text-secondary)] ml-1">{unit}</span>
        </span>
      </div>
      {typeof value === 'number' && (
        <div className="w-full bg-[var(--color-tertiary)] rounded-full h-2 mt-1">
          <div
            className={`h-2 rounded-full ${color === 'cyan' ? 'bg-cyan-400' : color === 'green' ? 'bg-emerald-400' : color === 'yellow' ? 'bg-yellow-400' : 'bg-red-400'}`}
            style={{ width: `${Math.min(value, 100)}%` }}
          />
        </div>
      )}
    </div>
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-[var(--color-text-secondary)]">System Statistics</h3>
        <button
          onClick={refresh}
          disabled={loading}
          className="px-3 py-1 text-xs bg-[var(--color-tertiary)] rounded-lg text-[var(--color-text-secondary)]
            hover:text-[var(--color-text-primary)] transition-colors disabled:opacity-50"
        >
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {stats ? (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <StatCard title="CPU" value={stats.cpu?.percent} unit="%" icon="🔲" color="cyan" />
          <StatCard title="Memory" value={stats.memory?.percent} unit="%" icon="💾" color={stats.memory?.percent > 80 ? 'red' : 'green'} />
          <StatCard title="Disk" value={stats.disk?.percent} unit="%" icon="💿" color={stats.disk?.percent > 90 ? 'red' : 'yellow'} />

          <div className="col-span-2 md:col-span-3 rounded-lg border border-[var(--color-border)] p-4">
            <h4 className="text-xs font-medium text-[var(--color-text-secondary)] mb-2">Details</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
              <div>
                <span className="text-[var(--color-text-secondary)]">Hostname</span>
                <div className="text-[var(--color-text-primary)] font-mono">{stats.hostname}</div>
              </div>
              <div>
                <span className="text-[var(--color-text-secondary)]">Memory</span>
                <div className="text-[var(--color-text-primary)]">{stats.memory?.used_gb} / {stats.memory?.total_gb} GB</div>
              </div>
              <div>
                <span className="text-[var(--color-text-secondary)]">Disk</span>
                <div className="text-[var(--color-text-primary)]">{stats.disk?.used_gb} / {stats.disk?.total_gb} GB</div>
              </div>
              <div>
                <span className="text-[var(--color-text-secondary)]">CPU Cores</span>
                <div className="text-[var(--color-text-primary)]">{stats.cpu?.count_logical} logical / {stats.cpu?.count_physical} physical</div>
              </div>
            </div>
          </div>

          {stats.gpu && Array.isArray(stats.gpu) && stats.gpu.length > 0 && (
            <div className="col-span-2 md:col-span-3 rounded-lg border border-[var(--color-border)] p-4">
              <h4 className="text-xs font-medium text-[var(--color-text-secondary)] mb-2">GPU</h4>
              {stats.gpu.map((gpu, i) => (
                <div key={i} className="flex items-center gap-4 text-xs mb-2">
                  <span className="text-[var(--color-text-primary)] font-medium">{gpu.name}</span>
                  <span className="text-[var(--color-text-secondary)]">Load: {gpu.load_percent}%</span>
                  <span className="text-[var(--color-text-secondary)]">VRAM: {gpu.memory_used_mb}/{gpu.memory_total_mb} MB ({gpu.memory_percent}%)</span>
                  <span className="text-[var(--color-text-secondary)]">Temp: {gpu.temperature_c}°C</span>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="text-center py-8 text-[var(--color-text-secondary)]">
          {loading ? 'Loading system stats...' : 'No data available'}
        </div>
      )}
    </div>
  );
}