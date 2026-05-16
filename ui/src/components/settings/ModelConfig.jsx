import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../../utils/api';

const PROVIDER_COLORS = {
  ollama: 'bg-blue-500/20 text-blue-400',
  openai: 'bg-green-500/20 text-green-400',
  anthropic: 'bg-amber-500/20 text-amber-400',
  google: 'bg-red-500/20 text-red-400',
  mistral: 'bg-purple-500/20 text-purple-400',
  cohere: 'bg-teal-500/20 text-teal-400',
};

export default function ModelConfig() {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [preferences, setPreferences] = useState({});
  const [saving, setSaving] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/models');
      const json = await res.json();
      setModels(json.models || json || []);
      setPreferences(json.preferences || {});
    } catch (err) {
      setError(err.message || 'Failed to load models');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleSetPreferred = async (specialist, modelId) => {
    setPreferences((prev) => ({ ...prev, [specialist]: modelId }));
    try {
      await api.post('/api/models/preference', { specialist, modelId });
    } catch (err) {
      console.error('Failed to set preference:', err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-aethera-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400">
        <p className="font-medium">Failed to load model configuration</p>
        <p className="text-sm mt-1">{error}</p>
        <button onClick={fetchData} className="mt-2 text-sm underline hover:no-underline">Retry</button>
      </div>
    );
  }

  const grouped = models.reduce((acc, model) => {
    const provider = model.provider || 'unknown';
    if (!acc[provider]) acc[provider] = [];
    acc[provider].push(model);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-sm font-semibold text-aethera-foreground mb-1">Model Configuration</h2>
        <p className="text-xs text-aethera-text-secondary">Set preferred models per specialist and view rate limits</p>
      </div>

      {/* All Models by Provider */}
      {Object.entries(grouped).map(([provider, providerModels]) => (
        <div key={provider} className="bg-aethera-surface rounded-xl border border-aethera-border overflow-hidden">
          <div className="px-4 py-3 border-b border-aethera-border flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${PROVIDER_COLORS[provider] || 'bg-gray-500/20 text-gray-400'}`}>
                {provider.charAt(0).toUpperCase() + provider.slice(1)}
              </span>
              <span className="text-sm font-medium text-aethera-foreground">{providerModels.length} model{providerModels.length !== 1 ? 's' : ''}</span>
            </div>
          </div>
          <div className="divide-y divide-aethera-border">
            {providerModels.map((model) => {
              const isPreferred = Object.values(preferences).includes(model.id);
              return (
                <div key={model.id} className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium text-aethera-foreground">{model.name || model.id}</p>
                        {model.status === 'available' && (
                          <span className="w-2 h-2 rounded-full bg-green-400" />
                        )}
                        {model.status === 'unavailable' && (
                          <span className="w-2 h-2 rounded-full bg-red-400" />
                        )}
                        {isPreferred && (
                          <span className="text-xs px-1.5 py-0.5 rounded bg-aethera-primary/20 text-aethera-primary">Preferred</span>
                        )}
                      </div>
                      <p className="text-xs text-aethera-text-secondary mt-0.5">
                        {model.description || model.id}
                        {model.contextLength && ` | ${model.contextLength.toLocaleString()} ctx`}
                      </p>
                    </div>
                  </div>

                  {/* Rate Limit */}
                  {model.rateLimit && (
                    <div className="mt-2">
                      <div className="flex items-center justify-between text-xs text-aethera-text-secondary mb-1">
                        <span>Rate Limit</span>
                        <span>{model.rateLimit.used}/{model.rateLimit.limit} requests/min</span>
                      </div>
                      <div className="w-full bg-aethera-tertiary rounded-full h-1.5">
                        <div
                          className={`h-1.5 rounded-full transition-all ${
                            model.rateLimit.used / Math.max(model.rateLimit.limit, 1) > 0.8
                              ? 'bg-red-400'
                              : 'bg-aethera-primary'
                          }`}
                          style={{ width: `${(model.rateLimit.used / Math.max(model.rateLimit.limit, 1)) * 100}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Specialist Preference Selector */}
                  {model.specialists && model.specialists.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {model.specialists.map((spec) => (
                        <button
                          key={spec}
                          onClick={() => handleSetPreferred(spec, model.id)}
                          className={`text-xs px-2 py-0.5 rounded-full transition-colors ${
                            preferences[spec] === model.id
                              ? 'bg-aethera-primary text-white'
                              : 'bg-aethera-tertiary text-aethera-text-secondary hover:text-aethera-foreground'
                          }`}
                        >
                          {spec}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}

      {models.length === 0 && (
        <div className="bg-aethera-surface rounded-xl border border-aethera-border p-8 text-center">
          <p className="text-aethera-text-secondary">No models available</p>
        </div>
      )}
    </div>
  );
}