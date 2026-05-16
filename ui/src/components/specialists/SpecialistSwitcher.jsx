import React, { useState, useEffect } from 'react';
import SpecialistBadge from './SpecialistBadge';

const ALL_SPECIALISTS = [
  { id: 'healthcare_provider', name: 'Provider Ops', description: 'Hospital, physician, and facility operations', icon: 'hospital' },
  { id: 'healthcare_payer', name: 'Payer Ops', description: 'Insurance, claims adjudication, and reimbursement', icon: 'shield' },
  { id: 'healthcare_regulatory', name: 'Regulatory', description: 'HIPAA, CMS, OIG, and compliance rules', icon: 'scale' },
  { id: 'healthcare_clinical', name: 'Clinical', description: 'Clinical documentation, medical necessity, care pathways', icon: 'heartbeat' },
  { id: 'healthcare_analytics', name: 'Analytics', description: 'Revenue cycle analytics and reporting', icon: 'chart' },
  { id: 'healthcare_it', name: 'Health IT', description: 'EHR/EMR systems, HL7, FHIR, EDI transactions', icon: 'server' },
  { id: 'healthcare_pharmacy', name: 'Pharmacy', description: 'Drug interactions, formularies, NDC codes', icon: 'pill' },
  { id: 'healthcare_behavioral', name: 'Behavioral Health', description: 'Mental health, substance abuse, BH parity', icon: 'brain' },
  { id: 'healthcare_dental_vision', name: 'Dental/Vision', description: 'Dental and vision coding, coverage, claims', icon: 'eye' },
  { id: 'healthcare_workers_comp', name: 'Workers Comp', description: 'Workers compensation, OWCP, state regulations', icon: 'hardhat' },
  { id: 'finance', name: 'Finance', description: 'Financial analysis, revenue optimization', icon: 'dollar' },
  { id: 'legal', name: 'Legal', description: 'Healthcare law, malpractice, appeals', icon: 'gavel' },
  { id: 'software_engineering', name: 'Engineering', description: 'Software development, API integrations', icon: 'code' },
  { id: 'media_marketing', name: 'Marketing', description: 'Healthcare marketing, patient engagement', icon: 'megaphone' },
  { id: 'research', name: 'Research', description: 'Medical research, clinical trials, evidence', icon: 'microscope' },
  { id: 'personal_assistant', name: 'Personal', description: 'General tasks, scheduling, reminders', icon: 'user' },
  { id: 'cloudflare_ops', name: 'Cloudflare', description: 'Cloud infrastructure and tunnel management', icon: 'cloud' },
  { id: 'data_analytics', name: 'Data', description: 'Data pipelines, ETL, statistical modeling', icon: 'database' },
  { id: 'general', name: 'General', description: 'General-purpose AI assistant', icon: 'sparkles' },
];

const SPECIALIST_HEX_COLORS = {
  healthcare_provider: '#06B6D4',
  healthcare_payer: '#8B5CF6',
  healthcare_regulatory: '#F43F5E',
  healthcare_clinical: '#10B981',
  healthcare_analytics: '#F59E0B',
  healthcare_it: '#3B82F6',
  healthcare_pharmacy: '#EC4899',
  healthcare_behavioral: '#A855F7',
  healthcare_dental_vision: '#14B8A6',
  healthcare_workers_comp: '#F97316',
  finance: '#22C55E',
  legal: '#EF4444',
  software_engineering: '#6366F1',
  media_marketing: '#F43F5E',
  research: '#14B8A6',
  personal_assistant: '#A855F7',
  cloudflare_ops: '#F97316',
  data_analytics: '#0EA5E9',
  general: '#6B7280',
};

function SpecialistIcon({ icon, color }) {
  const icons = {
    hospital: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
      </svg>
    ),
    shield: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    ),
    scale: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
      </svg>
    ),
    heartbeat: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
      </svg>
    ),
    chart: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
    server: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
      </svg>
    ),
    pill: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
      </svg>
    ),
    brain: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
    eye: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
      </svg>
    ),
    hardhat: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
      </svg>
    ),
    dollar: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    gavel: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
      </svg>
    ),
    code: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
      </svg>
    ),
    megaphone: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5.882V19.118a1 1 0 01-1.66.812L5.28 16H3a1 1 0 01-1-1v-6a1 1 0 011-1h2.28l4.06-3.93A1 1 0 0111 5.882zm8.04 7.198l2.34-2.34m0 0l2.34-2.34m-2.34 2.34l-2.34-2.34m2.34 2.34l2.34 2.34" />
      </svg>
    ),
    microscope: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
    ),
    user: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
      </svg>
    ),
    cloud: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
      </svg>
    ),
    database: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
      </svg>
    ),
    sparkles: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
      </svg>
    ),
  };

  return icons[icon] || icons.sparkles;
}

export default function SpecialistSwitcher({ activeSpecialist, onSelect }) {
  const [search, setSearch] = useState('');
  const [selectedId, setSelectedId] = useState(activeSpecialist || null);

  useEffect(() => {
    if (activeSpecialist) {
      setSelectedId(activeSpecialist);
    }
  }, [activeSpecialist]);

  const filteredSpecialists = ALL_SPECIALISTS.filter((spec) => {
    const query = search.toLowerCase();
    return (
      spec.name.toLowerCase().includes(query) ||
      spec.description.toLowerCase().includes(query) ||
      spec.id.toLowerCase().includes(query)
    );
  });

  const handleSelect = (spec) => {
    setSelectedId(spec.id);
    onSelect?.(spec.id);
    window.dispatchEvent(new CustomEvent('aethera-specialist', { detail: spec.id }));
  };

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-aethera-foreground">Specialist Switcher</h2>
        {selectedId && (
          <SpecialistBadge specialist={selectedId} size="sm" />
        )}
      </div>

      {/* Search */}
      <div className="relative">
        <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-aethera-text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search specialists..."
          className="w-full bg-aethera-surface border border-aethera-border rounded-lg pl-10 pr-4 py-2 text-sm text-aethera-foreground placeholder-aethera-text-secondary focus:border-aethera-primary focus:outline-none"
        />
      </div>

      {/* Cards grid */}
      {filteredSpecialists.length === 0 ? (
        <div className="text-center py-8 text-aethera-text-secondary">
          <p className="text-sm">No specialists match your search</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
          {filteredSpecialists.map((spec) => {
            const color = SPECIALIST_HEX_COLORS[spec.id] || '#6B7280';
            const isSelected = selectedId === spec.id;

            return (
              <button
                key={spec.id}
                onClick={() => handleSelect(spec)}
                className={`
                  relative p-3 rounded-lg border text-left transition-all duration-200 group
                  ${isSelected
                    ? 'border-aethera-primary bg-aethera-primary/10 shadow-lg shadow-aethera-primary/10'
                    : 'border-aethera-border bg-aethera-surface hover:border-aethera-primary/50'
                  }
                `}
              >
                {/* Active indicator */}
                {isSelected && (
                  <div
                    className="absolute top-2 right-2 w-2 h-2 rounded-full bg-aethera-primary"
                  />
                )}

                {/* Color bar */}
                <div
                  className="w-full h-1 rounded-full mb-2 opacity-60 group-hover:opacity-100 transition-opacity"
                  style={{ backgroundColor: color }}
                />

                {/* Icon */}
                <div style={{ color }} className="mb-2">
                  <SpecialistIcon icon={spec.icon} color={color} />
                </div>

                {/* Name */}
                <p className="text-sm font-medium text-aethera-foreground truncate">{spec.name}</p>

                {/* Description */}
                <p className="text-xs text-aethera-text-secondary mt-0.5 line-clamp-2 leading-tight">
                  {spec.description}
                </p>
              </button>
            );
          })}
        </div>
      )}

      {/* Hint */}
      <p className="text-xs text-aethera-text-secondary text-center">
        Select a specialist to force it for the next message
      </p>
    </div>
  );
}