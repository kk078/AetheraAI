import React from 'react';
import { CONFIDENCE_THRESHOLDS, CONFIDENCE_LABELS } from '../../utils/constants';

export default function ConfidenceBadge({ confidence }) {
  const { color, label } = getConfidenceInfo(confidence);

  return (
    <span className={`text-xs px-1.5 py-0.5 rounded ${color}`}>
      {label}
    </span>
  );
}

function getConfidenceInfo(confidence) {
  if (confidence >= CONFIDENCE_THRESHOLDS.HIGH) {
    return { color: 'bg-green-500/20 text-green-400', label: CONFIDENCE_LABELS.HIGH };
  } else if (confidence >= CONFIDENCE_THRESHOLDS.MEDIUM) {
    return { color: 'bg-amber-500/20 text-amber-400', label: CONFIDENCE_LABELS.MEDIUM };
  } else {
    return { color: 'bg-red-500/20 text-red-400', label: CONFIDENCE_LABELS.LOW };
  }
}