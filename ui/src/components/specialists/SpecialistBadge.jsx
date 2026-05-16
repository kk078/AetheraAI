import React from 'react';

const specialistColors = {
  healthcare_provider: 'bg-specialist-provider',
  healthcare_payer: 'bg-specialist-payer',
  healthcare_regulatory: 'bg-specialist-regulatory',
  healthcare_clinical: 'bg-specialist-clinical',
  healthcare_analytics: 'bg-specialist-analytics',
  healthcare_it: 'bg-specialist-it',
  healthcare_pharmacy: 'bg-specialist-pharmacy',
  healthcare_behavioral: 'bg-specialist-behavioral',
  healthcare_dental_vision: 'bg-specialist-dental',
  healthcare_workers_comp: 'bg-specialist-workersComp',
  finance: 'bg-specialist-finance',
  legal: 'bg-specialist-legal',
  software_engineering: 'bg-specialist-software',
  media_marketing: 'bg-specialist-marketing',
  research: 'bg-specialist-research',
  personal_assistant: 'bg-specialist-personal',
  cloudflare_ops: 'bg-specialist-cloudflare',
  data_analytics: 'bg-specialist-data',
  general: 'bg-specialist-general',
};

const specialistLabels = {
  healthcare_provider: 'Provider',
  healthcare_payer: 'Payer',
  healthcare_regulatory: 'Regulatory',
  healthcare_clinical: 'Clinical',
  healthcare_analytics: 'Analytics',
  healthcare_it: 'IT',
  healthcare_pharmacy: 'Pharmacy',
  healthcare_behavioral: 'Behavioral',
  healthcare_dental_vision: 'Dental/Vision',
  healthcare_workers_comp: 'Workers Comp',
  finance: 'Finance',
  legal: 'Legal',
  software_engineering: 'Engineering',
  media_marketing: 'Marketing',
  research: 'Research',
  personal_assistant: 'Personal',
  cloudflare_ops: 'Cloudflare',
  data_analytics: 'Data',
  general: 'General',
};

export default function SpecialistBadge({ specialist, size = 'md' }) {
  const color = specialistColors[specialist] || specialistColors.general;
  const label = specialistLabels[specialist] || specialist;

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-sm px-2.5 py-1',
    lg: 'text-base px-3 py-1.5',
  };

  return (
    <span className={`${color} ${sizeClasses[size]} text-white rounded-full font-medium inline-flex items-center gap-1`}>
      {label}
    </span>
  );
}
