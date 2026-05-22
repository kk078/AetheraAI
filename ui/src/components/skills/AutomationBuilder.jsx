import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../../utils/api';

const TRIGGER_OPTIONS = [
  { value: 'message_received', label: 'Message Received' },
  { value: 'schedule', label: 'On Schedule' },
  { value: 'alert_created', label: 'Alert Created' },
  { value: 'data_changed', label: 'Data Changed' },
  { value: 'connector_event', label: 'Connector Event' },
];

const CONDITION_OPTIONS = [
  { value: 'always', label: 'Always' },
  { value: 'contains_keyword', label: 'Contains Keyword' },
  { value: 'severity_is', label: 'Severity Is' },
  { value: 'time_between', label: 'Time Between' },
  { value: 'specialist_is', label: 'Specialist Is' },
];

const ACTION_OPTIONS = [
  { value: 'send_message', label: 'Send Message' },
  { value: 'execute_skill', label: 'Execute Skill' },
  { value: 'create_alert', label: 'Create Alert' },
  { value: 'update_data', label: 'Update Data' },
  { value: 'notify_channel', label: 'Notify Channel' },
];

export default function AutomationBuilder() {
  const [automations, setAutomations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [deleting, setDeleting] = useState(new Set());

  const fetchAutomations = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/automations');
      const json = await res.json();
      setAutomations(json.automations || json || []);
    } catch (err) {
      setError(err.message || 'Failed to load automations');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAutomations(); }, [fetchAutomations]);

  const handleCreate = async (automation) => {
    try {
      const res = await api.post('/api/automations', automation);
      const json = await res.json();
      setAutomations((prev) => [...prev, json.automation || json]);
      setShowForm(false);
    } catch (err) {
      console.error('Failed to create automation:', err);
    }
  };

  const handleDelete = async (automationId) => {
    setDeleting((prev) => new Set(prev).add(automationId));
    try {
      await api.deleteAutomation(automationId);
      setAutomations((prev) => prev.filter((a) => a.id !== automationId));
    } catch (err) {
      console.error('Failed to delete automation:', err);
    } finally {
      setDeleting((prev) => {
        const next = new Set(prev);
        next.delete(automationId);
        return next;
      });
    }
  };

  const handleToggle = async (automationId, enabled) => {
    try {
      await api.post(`/api/automations/${automationId}/${enabled ? 'disable' : 'enable'}`, {});
      setAutomations((prev) => prev.map((a) => a.id === automationId ? { ...a, enabled: !enabled } : a));
    } catch (err) {
      console.error('Failed to toggle automation:', err);
    }
  };

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
          <p className="font-medium">Failed to load automations</p>
          <p className="text-sm mt-1">{error}</p>
          <button onClick={fetchAutomations} className="mt-2 text-sm underline hover:no-underline">Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-aethera-foreground">Automations</h1>
          <p className="text-aethera-text-secondary mt-1">Build and manage automated workflows</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-4 py-2 bg-aethera-primary text-white rounded-lg font-medium hover:bg-cyan-600 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Automation
        </button>
      </div>

      {/* Automation List */}
      {automations.length === 0 && !showForm ? (
        <div className="bg-aethera-surface rounded-xl border border-aethera-border p-8 text-center">
          <svg className="w-12 h-12 text-aethera-text-secondary mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <p className="text-aethera-text-secondary">No automations yet</p>
          <button onClick={() => setShowForm(true)} className="mt-3 text-sm text-aethera-primary hover:underline">Create your first automation</button>
        </div>
      ) : (
        <div className="space-y-3">
          {automations.map((automation) => (
            <div key={automation.id} className="bg-aethera-surface rounded-xl border border-aethera-border p-4">
              <div className="flex items-center justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-medium text-aethera-foreground">{automation.name}</h3>
                    {!automation.enabled && (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-gray-500/20 text-gray-400">Disabled</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-2 text-xs text-aethera-text-secondary">
                    <RuleBadge label="When" value={getLabel(TRIGGER_OPTIONS, automation.trigger)} color="text-blue-400 bg-blue-500/20" />
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                    <RuleBadge label="If" value={getLabel(CONDITION_OPTIONS, automation.condition)} color="text-amber-400 bg-amber-500/20" />
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                    <RuleBadge label="Do" value={getLabel(ACTION_OPTIONS, automation.action)} color="text-green-400 bg-green-500/20" />
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  <button
                    onClick={() => handleToggle(automation.id, automation.enabled)}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${automation.enabled ? 'bg-aethera-primary' : 'bg-aethera-tertiary'}`}
                  >
                    <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${automation.enabled ? 'translate-x-6' : 'translate-x-1'}`} />
                  </button>
                  <button
                    onClick={() => handleDelete(automation.id)}
                    disabled={deleting.has(automation.id)}
                    className="p-1.5 text-aethera-text-secondary hover:text-red-400 transition-colors"
                  >
                    {deleting.has(automation.id) ? (
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-red-400" />
                    ) : (
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Automation Modal */}
      {showForm && (
        <AutomationForm
          onSubmit={handleCreate}
          onClose={() => setShowForm(false)}
        />
      )}
    </div>
  );
}

function AutomationForm({ onSubmit, onClose }) {
  const [name, setName] = useState('');
  const [trigger, setTrigger] = useState(TRIGGER_OPTIONS[0].value);
  const [condition, setCondition] = useState(CONDITION_OPTIONS[0].value);
  const [action, setAction] = useState(ACTION_OPTIONS[0].value);
  const [conditionValue, setConditionValue] = useState('');
  const [actionValue, setActionValue] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    await onSubmit({ name, trigger, condition, action, conditionValue, actionValue, enabled: true });
    setSubmitting(false);
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-aethera-surface rounded-xl border border-aethera-border max-w-lg w-full" onClick={(e) => e.stopPropagation()}>
        <div className="p-5 border-b border-aethera-border flex items-center justify-between">
          <h2 className="text-lg font-semibold text-aethera-foreground">New Automation</h2>
          <button onClick={onClose} className="text-aethera-text-secondary hover:text-aethera-foreground">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="block text-sm font-medium text-aethera-foreground mb-1">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              placeholder="My Automation"
              className="w-full bg-aethera-tertiary border border-aethera-border rounded-lg px-3 py-2 text-sm text-aethera-foreground placeholder-aethera-text-secondary focus:outline-none focus:border-aethera-primary"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-aethera-foreground mb-1">When (Trigger)</label>
            <select value={trigger} onChange={(e) => setTrigger(e.target.value)} className="w-full bg-aethera-tertiary border border-aethera-border rounded-lg px-3 py-2 text-sm text-aethera-foreground focus:outline-none focus:border-aethera-primary">
              {TRIGGER_OPTIONS.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-aethera-foreground mb-1">If (Condition)</label>
            <select value={condition} onChange={(e) => setCondition(e.target.value)} className="w-full bg-aethera-tertiary border border-aethera-border rounded-lg px-3 py-2 text-sm text-aethera-foreground focus:outline-none focus:border-aethera-primary">
              {CONDITION_OPTIONS.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
            </select>
            {condition !== 'always' && (
              <input
                type="text"
                value={conditionValue}
                onChange={(e) => setConditionValue(e.target.value)}
                placeholder="Condition value..."
                className="mt-2 w-full bg-aethera-tertiary border border-aethera-border rounded-lg px-3 py-2 text-sm text-aethera-foreground placeholder-aethera-text-secondary focus:outline-none focus:border-aethera-primary"
              />
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-aethera-foreground mb-1">Do (Action)</label>
            <select value={action} onChange={(e) => setAction(e.target.value)} className="w-full bg-aethera-tertiary border border-aethera-border rounded-lg px-3 py-2 text-sm text-aethera-foreground focus:outline-none focus:border-aethera-primary">
              {ACTION_OPTIONS.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
            </select>
            <input
              type="text"
              value={actionValue}
              onChange={(e) => setActionValue(e.target.value)}
              placeholder="Action details..."
              className="mt-2 w-full bg-aethera-tertiary border border-aethera-border rounded-lg px-3 py-2 text-sm text-aethera-foreground placeholder-aethera-text-secondary focus:outline-none focus:border-aethera-primary"
            />
          </div>

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 py-2 rounded-lg border border-aethera-border text-aethera-text-secondary hover:text-aethera-foreground transition-colors">
              Cancel
            </button>
            <button type="submit" disabled={submitting || !name} className="flex-1 py-2 rounded-lg bg-aethera-primary text-white hover:bg-cyan-600 disabled:opacity-50 transition-colors">
              {submitting ? 'Creating...' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function RuleBadge({ label, value, color }) {
  return (
    <span className={`text-xs px-1.5 py-0.5 rounded ${color}`}>
      {label}: {value}
    </span>
  );
}

function getLabel(options, value) {
  return options.find((o) => o.value === value)?.label || value;
}