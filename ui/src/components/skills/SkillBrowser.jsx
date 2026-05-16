import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../../utils/api';

const CATEGORY_ICONS = {
  healthcare: 'M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z',
  finance: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  productivity: 'M13 10V3L4 14h7v7l9-11h-7z',
  analytics: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
  integration: 'M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z',
  automation: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z',
};

export default function SkillBrowser() {
  const [skills, setSkills] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedSkill, setSelectedSkill] = useState(null);
  const [executing, setExecuting] = useState(false);
  const [executeResult, setExecuteResult] = useState(null);

  const fetchSkills = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/skills');
      const json = await res.json();
      setSkills(json.skills || json || []);
    } catch (err) {
      setError(err.message || 'Failed to load skills');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchSkills(); }, [fetchSkills]);

  const categories = ['all', ...new Set(skills.map((s) => s.category).filter(Boolean))];

  const filteredSkills = skills.filter((skill) => {
    const matchesSearch = !search || skill.name.toLowerCase().includes(search.toLowerCase()) || skill.description?.toLowerCase().includes(search.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || skill.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const handleExecute = async (skill) => {
    setExecuting(true);
    setExecuteResult(null);
    try {
      const result = await api.executeSkill(skill.name, skill.parameters || {});
      setExecuteResult(result);
    } catch (err) {
      setExecuteResult({ error: err.message });
    } finally {
      setExecuting(false);
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
          <p className="font-medium">Failed to load skills</p>
          <p className="text-sm mt-1">{error}</p>
          <button onClick={fetchSkills} className="mt-2 text-sm underline hover:no-underline">Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-aethera-foreground">Skills</h1>
        <p className="text-aethera-text-secondary mt-1">Browse and execute available AI skills</p>
      </div>

      {/* Search & Filter */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex-1 relative">
          <svg className="w-5 h-5 text-aethera-text-secondary absolute left-3 top-1/2 -translate-y-1/2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search skills..."
            className="w-full bg-aethera-surface border border-aethera-border rounded-lg pl-10 pr-4 py-2 text-sm text-aethera-foreground placeholder-aethera-text-secondary focus:outline-none focus:border-aethera-primary"
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`text-xs px-3 py-1.5 rounded-full font-medium transition-colors ${
                selectedCategory === cat
                  ? 'bg-aethera-primary text-white'
                  : 'bg-aethera-surface border border-aethera-border text-aethera-text-secondary hover:text-aethera-foreground'
              }`}
            >
              {cat.charAt(0).toUpperCase() + cat.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Skills Grid */}
      {filteredSkills.length === 0 ? (
        <div className="bg-aethera-surface rounded-xl border border-aethera-border p-8 text-center">
          <svg className="w-12 h-12 text-aethera-text-secondary mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
          </svg>
          <p className="text-aethera-text-secondary">No skills found</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredSkills.map((skill) => (
            <button
              key={skill.name}
              onClick={() => { setSelectedSkill(skill); setExecuteResult(null); }}
              className="bg-aethera-surface rounded-xl border border-aethera-border p-4 text-left hover:border-aethera-primary transition-colors group"
            >
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-aethera-primary/20 flex items-center justify-center flex-shrink-0">
                  <svg className="w-5 h-5 text-aethera-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={CATEGORY_ICONS[skill.category] || CATEGORY_ICONS.productivity} />
                  </svg>
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="text-sm font-medium text-aethera-foreground group-hover:text-aethera-primary transition-colors">{skill.name}</h3>
                  <p className="text-xs text-aethera-text-secondary mt-1 line-clamp-2">{skill.description}</p>
                </div>
              </div>
              {skill.category && (
                <span className="mt-3 inline-block text-xs px-2 py-0.5 rounded-full bg-aethera-tertiary text-aethera-text-secondary">
                  {skill.category}
                </span>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Skill Detail Modal */}
      {selectedSkill && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setSelectedSkill(null)}>
          <div className="bg-aethera-surface rounded-xl border border-aethera-border max-w-lg w-full max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="p-5 border-b border-aethera-border flex items-center justify-between">
              <h2 className="text-lg font-semibold text-aethera-foreground">{selectedSkill.name}</h2>
              <button onClick={() => setSelectedSkill(null)} className="text-aethera-text-secondary hover:text-aethera-foreground">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-5 space-y-4">
              <p className="text-sm text-aethera-text-secondary">{selectedSkill.description}</p>
              {selectedSkill.category && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-aethera-primary/20 text-aethera-primary">{selectedSkill.category}</span>
              )}
              {selectedSkill.parameters && Object.keys(selectedSkill.parameters).length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-aethera-foreground mb-2">Parameters</h3>
                  <div className="bg-aethera-tertiary/50 rounded-lg p-3 space-y-1">
                    {Object.entries(selectedSkill.parameters).map(([key, val]) => (
                      <p key={key} className="text-xs"><span className="text-aethera-text-secondary">{key}:</span> <span className="text-aethera-foreground">{String(val)}</span></p>
                    ))}
                  </div>
                </div>
              )}
              <button
                onClick={() => handleExecute(selectedSkill)}
                disabled={executing}
                className="w-full py-2 rounded-lg bg-aethera-primary text-white font-medium hover:bg-cyan-600 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
              >
                {executing ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                    Executing...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.867v4.266a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Execute Skill
                  </>
                )}
              </button>
              {executeResult && (
                <div className={`rounded-lg p-3 text-sm ${executeResult.error ? 'bg-red-500/10 text-red-400' : 'bg-green-500/10 text-green-400'}`}>
                  {executeResult.error ? `Error: ${executeResult.error}` : 'Skill executed successfully'}
                  {executeResult.output && <pre className="mt-2 text-xs whitespace-pre-wrap">{JSON.stringify(executeResult.output, null, 2)}</pre>}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}