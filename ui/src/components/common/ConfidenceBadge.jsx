import React from 'react';

export default function ConfidenceBadge({ confidence }) {
  const { color, label } = getConfidenceInfo(confidence);

  return (
    <span className={`text-xs px-1.5 py-0.5 rounded ${color}`}>
      {label}
    </span>
  );
}

function getConfidenceInfo(confidence) {
  if (confidence >= 0.8) {
    return { color: 'bg-green-500/20 text-green-400', label: 'High' };
  } else if (confidence >= 0.5) {
    return { color: 'bg-amber-500/20 text-amber-400', label: 'Medium' };
  } else {
    return { color: 'bg-red-500/20 text-red-400', label: 'Low' };
  }
}
