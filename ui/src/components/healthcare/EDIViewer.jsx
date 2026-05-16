import React, { useState, useMemo, useCallback } from 'react';

// EDI segment definitions for common healthcare transaction sets
const SEGMENT_DEFINITIONS = {
  ISA: { name: 'Interchange Control Header', description: 'Identifies the beginning of an interchange' },
  GS: { name: 'Functional Group Header', description: 'Identifies the beginning of a functional group' },
  ST: { name: 'Transaction Set Header', description: 'Identifies the beginning of a transaction set' },
  BHT: { name: 'Beginning of Hierarchical Transaction', description: 'Identifies the business transaction purpose' },
  NM1: { name: 'Individual or Organization Name', description: 'Identifies a party by name and ID' },
  PER: { name: 'Administrative Communications Contact', description: 'Identifies a communications contact' },
  N3: { name: 'Party Location', description: 'Identifies the street address of a party' },
  N4: { name: 'Geographic Location', description: 'Identifies the city, state, and ZIP of a party' },
  DMG: { name: 'Demographic Information', description: 'Identifies demographic information about a party' },
  DTP: { name: 'Date/Time Period', description: 'Specifies date/time and related period' },
  CLM: { name: 'Claim Information', description: 'Identifies claim-level information' },
  CN1: { name: 'Contract Information', description: 'Identifies contract information' },
  HI: { name: 'Health Care Diagnosis Codes', description: 'Identifies diagnosis codes' },
  SV1: { name: 'Professional Service', description: 'Identifies a professional service line' },
  SV2: { name: 'Institutional Service', description: 'Identifies an institutional service line' },
  LX: { name: 'Transaction Set Line Number', description: 'Identifies a line item' },
  LIN: { name: 'Item Identification', description: 'Identifies an item by ID number' },
  CTP: { name: 'Pricing Information', description: 'Identifies pricing information' },
  REF: { name: 'Reference Identification', description: 'Identifies a reference by ID' },
  AMT: { name: 'Monetary Amount', description: 'Identifies a monetary amount' },
  QTY: { name: 'Quantity Information', description: 'Identifies quantity information' },
  OI: { name: 'Other Insurance', description: 'Identifies other insurance information' },
  CAS: { name: 'Claim Adjustment', description: 'Identifies claim adjustments' },
  MOA: { name: 'Medicare Outpatient Adjudication', description: 'Identifies Medicare outpatient adjudication' },
  SBR: { name: 'Subscriber Information', description: 'Identifies subscriber information' },
  TRN: { name: 'Trace Number', description: 'Identifies a trace number for tracking' },
  PLB: { name: 'Provider Level Adjustment', description: 'Identifies provider-level adjustments' },
  SE: { name: 'Transaction Set Trailer', description: 'Identifies the end of a transaction set' },
  GE: { name: 'Functional Group Trailer', description: 'Identifies the end of a functional group' },
  IEA: { name: 'Interchange Control Trailer', description: 'Identifies the end of an interchange' },
  LQ: { name: 'Health Care Code', description: 'Identifies a health care code' },
  HCP: { name: 'Health Care Pricing', description: 'Identifies health care pricing' },
  TS3: { name: 'Transaction Set Statistics', description: 'Identifies transaction statistics' },
  N1: { name: 'Party Identification', description: 'Identifies a party by entity ID code' },
  NTE: { name: 'Note/Special Instruction', description: 'Identifies a note or special instruction' },
  PRV: { name: 'Provider Information', description: 'Identifies provider information' },
  CUR: { name: 'Currency', description: 'Identifies currency information' },
  PAT: { name: 'Patient Information', description: 'Identifies patient demographic info' },
  CLP: { name: 'Claim Level Data', description: 'Identifies claim-level payment data' },
  SVC: { name: 'Service Payment Information', description: 'Identifies service-level payment info' },
  SVD: { name: 'Service Line Adjudication', description: 'Identifies service line adjudication' },
  DTM: { name: 'Date/Time Reference', description: 'Identifies a date/time reference' },
  ID: { name: 'Identification', description: 'Identifies an entity by code' },
  HL: { name: 'Hierarchical Level', description: 'Identifies a hierarchical level' },
};

const TRANSACTION_SET_NAMES = {
  '837': 'Health Care Claim',
  '835': 'Health Care Claim Payment/Remittance',
  '270': 'Eligibility Inquiry',
  '271': 'Eligibility Response',
  '276': 'Claim Status Inquiry',
  '277': 'Claim Status Response',
  '278': 'Prior Authorization',
  '820': 'Premium Payment',
  '999': 'Implementation Acknowledgment',
  '997': 'Functional Acknowledgment',
  '824': 'Application Advice',
};

function parseEDISegment(line) {
  // Standard EDI delimiter is *
  // Segment terminator is ~
  const cleaned = line.replace(/[\r\n]+/g, '').replace(/~$/, '').trim();
  if (!cleaned) return null;

  const elements = cleaned.split('*');
  const segmentId = elements[0]?.trim();
  if (!segmentId) return null;

  return {
    id: segmentId,
    elements: elements.slice(1).map((el) => el.trim()),
    raw: cleaned + '~',
  };
}

function detectTransactionSet(segments) {
  for (const seg of segments) {
    if (seg.id === 'ST' && seg.elements.length > 0) {
      return seg.elements[0];
    }
    if (seg.id === 'BHT' && seg.elements.length > 1) {
      // BHT01 can also indicate transaction type
    }
  }
  return null;
}

function formatElementValue(value, index, segmentId) {
  // Common element formatting based on segment context
  if (!value) return '--';

  // Date formatting for DTP/DTM segments
  if ((segmentId === 'DTP' || segmentId === 'DTM') && value.length === 8 && /^\d{8}$/.test(value)) {
    return `${value.slice(4, 6)}/${value.slice(6, 8)}/${value.slice(0, 4)}`;
  }

  // Amount formatting for AMT segments
  if (segmentId === 'AMT' && index === 1 && !isNaN(value)) {
    return `$${parseFloat(value).toFixed(2)}`;
  }

  return value;
}

function getElementLabel(segmentId, elementIndex) {
  // Provide meaningful labels for common element positions
  const labels = {
    ISA: ['Authorization Info Qualifier', 'Authorization Info', 'Security Info Qualifier', 'Security Info', 'Interchange ID Qualifier', 'Sender ID', 'Interchange ID Qualifier', 'Receiver ID', 'Interchange Date', 'Interchange Time', 'Repetition Separator', 'Interchange Control Version', 'Interchange Control Number', 'Acknowledgment Requested', 'Usage Indicator', 'Component Element Separator'],
    ST: ['Transaction Set Identifier', 'Transaction Set Control Number', 'Implementation Convention Reference'],
    NM1: ['Entity Identifier Code', 'Entity Type Qualifier', 'Name Last/Organization', 'Name First', 'Name Middle', 'Name Prefix', 'Name Suffix', 'Identification Code Qualifier', 'Identification Code'],
    CLM: ['Claim ID', 'Total Claim Charge Amount', 'FID Code', 'Provider Accepts Assignment', 'Provider Signature Source Code', 'Claim Frequency Type Code'],
    SV1: ['Product/Service ID Qualifier', 'Product/Service ID', 'Line Item Charge Amount', 'Units', 'Unit Basis', 'Place of Service Code', 'Service Type Code'],
    CAS: ['Claim Adjustment Group Code', 'Adjustment Reason 1', 'Adjustment Amount 1', 'Adjustment Quantity 1', 'Adjustment Reason 2', 'Adjustment Amount 2', 'Adjustment Quantity 2', 'Adjustment Reason 3', 'Adjustment Amount 3', 'Adjustment Quantity 3'],
    REF: ['Reference Identification Qualifier', 'Reference Identification'],
    DTP: ['Date/Time Qualifier', 'Date Time Period Format Qualifier', 'Date/Time Period'],
    CLP: ['Claim Number', 'Claim Status Code', 'Total Charged Amount', 'Total Paid Amount', 'Total Patient Responsibility', 'Payer Claim Control Number', 'Filing Indicator Code'],
    SVC: ['Product/Service ID Qualifier', 'Product/Service ID (CPT)', 'Line Item Paid Amount', 'Line Item Billed Amount', 'Units', 'Original Claim Number'],
  };

  const segmentLabels = labels[segmentId];
  if (segmentLabels && elementIndex < segmentLabels.length) {
    return segmentLabels[elementIndex];
  }
  return `Element ${elementId(segmentId, elementIndex)}`;
}

function elementId(segmentId, index) {
  return `${segmentId}${String(index + 1).padStart(2, '0')}`;
}

export default function EDIViewer() {
  const [rawEDI, setRawEDI] = useState('');
  const [parsedSegments, setParsedSegments] = useState(null);
  const [expandedSegment, setExpandedSegment] = useState(null);
  const [error, setError] = useState(null);

  const transactionSet = useMemo(() => {
    if (!parsedSegments || parsedSegments.length === 0) return null;
    return detectTransactionSet(parsedSegments);
  }, [parsedSegments]);

  const segmentCounts = useMemo(() => {
    if (!parsedSegments) return {};
    const counts = {};
    for (const seg of parsedSegments) {
      counts[seg.id] = (counts[seg.id] || 0) + 1;
    }
    return counts;
  }, [parsedSegments]);

  const handleParse = useCallback(() => {
    if (!rawEDI.trim()) {
      setError('Please paste EDI text to parse');
      return;
    }

    setError(null);

    try {
      const lines = rawEDI.split(/~/).filter((l) => l.trim());
      const segments = [];

      for (const line of lines) {
        const segment = parseEDISegment(line.trim());
        if (segment) {
          segments.push(segment);
        }
      }

      if (segments.length === 0) {
        setError('No valid EDI segments found. Ensure segments are separated by ~ (tilde).');
        setParsedSegments(null);
        return;
      }

      setParsedSegments(segments);
      setExpandedSegment(null);
    } catch (err) {
      setError(`Parse error: ${err.message}`);
      setParsedSegments(null);
    }
  }, [rawEDI]);

  const handleClear = useCallback(() => {
    setRawEDI('');
    setParsedSegments(null);
    setError(null);
    setExpandedSegment(null);
  }, []);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-aethera-foreground">EDI Viewer</h1>
        <p className="text-aethera-text-secondary mt-1">Parse and view EDI X12 healthcare transactions</p>
      </div>

      {/* Input Area */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-aethera-foreground">Paste EDI Content</label>
          <div className="flex gap-2">
            <button
              onClick={handleParse}
              disabled={!rawEDI.trim()}
              className="px-4 py-2 bg-aethera-primary hover:bg-cyan-600 disabled:bg-aethera-tertiary disabled:text-aethera-text-secondary text-white rounded-lg font-medium transition-colors text-sm"
            >
              Parse EDI
            </button>
            <button
              onClick={handleClear}
              className="px-4 py-2 bg-aethera-surface hover:bg-aethera-tertiary text-aethera-foreground rounded-lg font-medium transition-colors text-sm border border-aethera-border"
            >
              Clear
            </button>
          </div>
        </div>
        <textarea
          value={rawEDI}
          onChange={(e) => setRawEDI(e.target.value)}
          placeholder={`Paste EDI X12 content here...\n\nExample:\nISA*00*          *00*          *ZZ*SENDER       *ZZ*RECEIVER     *240101*1200*^*00501*000000001*0*P*~\nGS*HC*SENDER*RECEIVER*20240101*1200*1*X*005010X222A2~\nST*837*0001*005010X222A2~`}
          rows={8}
          className="w-full bg-aethera-surface border border-aethera-border rounded-lg px-4 py-3 text-aethera-foreground font-mono text-sm placeholder-aethera-text-secondary focus:border-aethera-primary focus:outline-none resize-y"
        />
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Parsed Results */}
      {parsedSegments && (
        <div className="space-y-4 animate-fade-in">
          {/* Summary Bar */}
          <div className="bg-aethera-surface rounded-xl border border-aethera-border p-4">
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-4">
                {transactionSet && (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-aethera-text-secondary">Transaction:</span>
                    <span className="text-sm font-medium text-aethera-foreground font-mono">
                      {transactionSet}
                    </span>
                    <span className="text-xs text-aethera-primary">
                      {TRANSACTION_SET_NAMES[transactionSet] || 'Unknown'}
                    </span>
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <span className="text-xs text-aethera-text-secondary">Segments:</span>
                  <span className="text-sm font-medium text-aethera-foreground">{parsedSegments.length}</span>
                </div>
              </div>

              {/* Segment type badges */}
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(segmentCounts)
                  .sort(([, a], [, b]) => b - a)
                  .slice(0, 8)
                  .map(([id, count]) => (
                    <span key={id} className="text-xs bg-aethera-tertiary text-aethera-text-secondary px-2 py-0.5 rounded font-mono">
                      {id} ({count})
                    </span>
                  ))}
              </div>
            </div>
          </div>

          {/* Segment Table */}
          <div className="bg-aethera-surface rounded-xl border border-aethera-border overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-aethera-border bg-aethera-background">
                    <th className="text-left py-3 px-4 text-aethera-text-secondary font-medium w-10">#</th>
                    <th className="text-left py-3 px-4 text-aethera-text-secondary font-medium w-20">Segment</th>
                    <th className="text-left py-3 px-4 text-aethera-text-secondary font-medium">Name</th>
                    <th className="text-left py-3 px-4 text-aethera-text-secondary font-medium">Values</th>
                    <th className="text-left py-3 px-4 text-aethera-text-secondary font-medium w-12" />
                  </tr>
                </thead>
                <tbody>
                  {parsedSegments.map((segment, index) => {
                    const def = SEGMENT_DEFINITIONS[segment.id];
                    const isExpanded = expandedSegment === index;
                    const isEnvelope = ['ISA', 'IEA', 'GS', 'GE', 'ST', 'SE'].includes(segment.id);

                    return (
                      <React.Fragment key={index}>
                        <tr
                          className={`border-b border-aethera-border last:border-0 hover:bg-aethera-tertiary/50 transition-colors cursor-pointer ${
                            isEnvelope ? 'bg-aethera-primary/5' : ''
                          }`}
                          onClick={() => setExpandedSegment(isExpanded ? null : index)}
                        >
                          <td className="py-3 px-4 text-aethera-text-secondary font-mono text-xs">{index + 1}</td>
                          <td className="py-3 px-4">
                            <span className={`font-mono font-medium ${isEnvelope ? 'text-aethera-primary' : 'text-aethera-foreground'}`}>
                              {segment.id}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-aethera-text-secondary text-xs max-w-[200px] truncate">
                            {def?.name || '--'}
                          </td>
                          <td className="py-3 px-4 text-aethera-text-secondary font-mono text-xs max-w-[300px] truncate">
                            {segment.elements.slice(0, 4).join('*')}
                            {segment.elements.length > 4 && '...'}
                          </td>
                          <td className="py-3 px-4">
                            <svg
                              className={`w-3.5 h-3.5 text-aethera-text-secondary transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                              fill="none" stroke="currentColor" viewBox="0 0 24 24"
                            >
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                            </svg>
                          </td>
                        </tr>

                        {/* Expanded element detail */}
                        {isExpanded && (
                          <tr>
                            <td colSpan="5" className="p-0">
                              <div className="p-4 bg-aethera-background border-b border-aethera-border animate-fade-in">
                                {/* Segment description */}
                                {def?.description && (
                                  <p className="text-xs text-aethera-text-secondary mb-3">{def.description}</p>
                                )}

                                {/* Raw segment */}
                                <div className="mb-3">
                                  <span className="text-xs text-aethera-text-secondary font-medium">Raw:</span>
                                  <pre className="text-xs text-aethera-foreground font-mono mt-1 bg-aethera-surface rounded p-2 border border-aethera-border overflow-x-auto">
                                    {segment.raw}
                                  </pre>
                                </div>

                                {/* Element breakdown */}
                                <div className="space-y-2">
                                  <span className="text-xs text-aethera-text-secondary font-medium">Elements:</span>
                                  {segment.elements.map((value, ei) => (
                                    <div key={ei} className="flex gap-3 text-xs">
                                      <span className="text-aethera-primary font-mono font-medium min-w-[60px]">
                                        {elementId(segment.id, ei)}
                                      </span>
                                      <span className="text-aethera-text-secondary min-w-[160px]">
                                        {getElementLabel(segment.id, ei)}
                                      </span>
                                      <span className="text-aethera-foreground font-mono">
                                        {formatElementValue(value || '', ei, segment.id) || '--'}
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Footer */}
            <div className="px-4 py-2 border-t border-aethera-border text-xs text-aethera-text-secondary">
              {parsedSegments.length} segment{parsedSegments.length !== 1 ? 's' : ''} parsed
            </div>
          </div>
        </div>
      )}
    </div>
  );
}