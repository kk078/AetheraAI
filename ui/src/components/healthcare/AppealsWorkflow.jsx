import React, { useState, useCallback } from 'react';
import { api } from '../../utils/api';

const STEPS = [
  { id: 'denial', title: 'Enter Denial', description: 'Provide denial codes and details' },
  { id: 'analysis', title: 'Denial Analysis', description: 'Review AI analysis of the denial' },
  { id: 'rationale', title: 'Clinical Rationale', description: 'Provide clinical justification' },
  { id: 'review', title: 'Review Letter', description: 'Review and edit the appeal letter' },
  { id: 'export', title: 'Export', description: 'Download or copy the final letter' },
];

export default function AppealsWorkflow() {
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Step 1: Denial info
  const [denialData, setDenialData] = useState({
    carcCode: '',
    rarcCode: '',
    payerName: '',
    patientName: '',
    claimNumber: '',
    denialDate: '',
    serviceDate: '',
    cptCode: '',
    diagnosisCode: '',
    billedAmount: '',
    denialReason: '',
  });

  // Step 2: Analysis
  const [analysis, setAnalysis] = useState(null);

  // Step 3: Clinical rationale
  const [clinicalRationale, setClinicalRationale] = useState({
    medicalNecessity: '',
    clinicalHistory: '',
    supportingEvidence: '',
    providerNotes: '',
  });

  // Step 4: Generated letter
  const [appealLetter, setAppealLetter] = useState('');
  const [letterEdited, setLetterEdited] = useState(false);

  const handleAnalyzeDenial = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await api.analyzeDenial(
        denialData.carcCode,
        denialData.rarcCode,
        {
          claimNumber: denialData.claimNumber,
          cptCode: denialData.cptCode,
          diagnosisCode: denialData.diagnosisCode,
          denialReason: denialData.denialReason,
        }
      );
      setAnalysis(result);
      setCurrentStep(1);
    } catch (err) {
      setError(err.message || 'Denial analysis failed');
    } finally {
      setLoading(false);
    }
  }, [denialData]);

  const handleGenerateLetter = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.post('/api/healthcare/appeal-letter', {
        denial: denialData,
        analysis,
        clinicalRationale,
      });
      const letter = response.letter || response.content || response;
      setAppealLetter(typeof letter === 'string' ? letter : JSON.stringify(letter, null, 2));
      setCurrentStep(3);
    } catch (err) {
      setError(err.message || 'Letter generation failed');
    } finally {
      setLoading(false);
    }
  }, [denialData, analysis, clinicalRationale]);

  const handleCopyLetter = useCallback(() => {
    navigator.clipboard.writeText(appealLetter).catch(() => {});
  }, [appealLetter]);

  const handleDownloadLetter = useCallback(() => {
    const blob = new Blob([appealLetter], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `appeal-letter-${denialData.claimNumber || 'draft'}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [appealLetter, denialData.claimNumber]);

  const canProceed = () => {
    switch (currentStep) {
      case 0:
        return !!denialData.carcCode.trim();
      case 1:
        return !!analysis;
      case 2:
        return !!clinicalRationale.medicalNecessity.trim();
      case 3:
        return !!appealLetter;
      default:
        return true;
    }
  };

  const handleNext = () => {
    if (currentStep === 0) {
      handleAnalyzeDenial();
      return;
    }
    if (currentStep === 2) {
      handleGenerateLetter();
      return;
    }
    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
      setError(null);
    }
  };

  const updateDenialField = (field, value) => {
    setDenialData((prev) => ({ ...prev, [field]: value }));
  };

  const updateRationaleField = (field, value) => {
    setClinicalRationale((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-aethera-foreground">Appeals Workflow</h1>
        <p className="text-aethera-text-secondary mt-1">Build a structured appeal letter step by step</p>
      </div>

      {/* Progress Steps */}
      <div className="flex items-center gap-1">
        {STEPS.map((step, index) => (
          <React.Fragment key={step.id}>
            <button
              onClick={() => index <= currentStep && setCurrentStep(index)}
              disabled={index > currentStep}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                index === currentStep
                  ? 'bg-aethera-primary/20 text-aethera-primary font-medium'
                  : index < currentStep
                    ? 'bg-aethera-tertiary text-aethera-foreground hover:bg-aethera-tertiary/80 cursor-pointer'
                    : 'text-aethera-text-secondary cursor-not-allowed'
              }`}
            >
              <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                index < currentStep
                  ? 'bg-green-500/20 text-green-400'
                  : index === currentStep
                    ? 'bg-aethera-primary text-white'
                    : 'bg-aethera-tertiary text-aethera-text-secondary'
              }`}>
                {index < currentStep ? (
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  index + 1
                )}
              </span>
              <span className="hidden sm:inline">{step.title}</span>
            </button>
            {index < STEPS.length - 1 && (
              <div className={`flex-1 h-px ${index < currentStep ? 'bg-aethera-primary' : 'bg-aethera-border'}`} />
            )}
          </React.Fragment>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Step Content */}
      <div className="bg-aethera-surface rounded-xl border border-aethera-border p-6 animate-fade-in">
        {/* Step 0: Enter Denial */}
        {currentStep === 0 && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-aethera-foreground">Enter Denial Information</h2>
            <p className="text-sm text-aethera-text-secondary">Provide the denial codes and claim details for analysis.</p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <InputField label="CARC Code *" value={denialData.carcCode} onChange={(v) => updateDenialField('carcCode', v)} placeholder="e.g., CO-50" />
              <InputField label="RARC Code" value={denialData.rarcCode} onChange={(v) => updateDenialField('rarcCode', v)} placeholder="e.g., N130" />
              <InputField label="Payer Name" value={denialData.payerName} onChange={(v) => updateDenialField('payerName', v)} placeholder="Insurance company name" />
              <InputField label="Patient Name" value={denialData.patientName} onChange={(v) => updateDenialField('patientName', v)} placeholder="Patient full name" />
              <InputField label="Claim Number" value={denialData.claimNumber} onChange={(v) => updateDenialField('claimNumber', v)} placeholder="CLM-XXXXXX" />
              <InputField label="Denial Date" value={denialData.denialDate} onChange={(v) => updateDenialField('denialDate', v)} placeholder="MM/DD/YYYY" type="date" />
              <InputField label="Service Date" value={denialData.serviceDate} onChange={(v) => updateDenialField('serviceDate', v)} placeholder="MM/DD/YYYY" type="date" />
              <InputField label="CPT Code" value={denialData.cptCode} onChange={(v) => updateDenialField('cptCode', v)} placeholder="e.g., 99213" />
              <InputField label="Diagnosis (ICD-10)" value={denialData.diagnosisCode} onChange={(v) => updateDenialField('diagnosisCode', v)} placeholder="e.g., M54.5" />
              <InputField label="Billed Amount" value={denialData.billedAmount} onChange={(v) => updateDenialField('billedAmount', v)} placeholder="$0.00" />
            </div>

            <div>
              <label className="block text-sm font-medium text-aethera-foreground mb-1.5">Denial Reason</label>
              <textarea
                value={denialData.denialReason}
                onChange={(e) => updateDenialField('denialReason', e.target.value)}
                placeholder="Describe the reason given for denial..."
                rows={3}
                className="w-full bg-aethera-background border border-aethera-border rounded-lg px-4 py-2.5 text-aethera-foreground placeholder-aethera-text-secondary focus:border-aethera-primary focus:outline-none resize-none"
              />
            </div>
          </div>
        )}

        {/* Step 1: Denial Analysis */}
        {currentStep === 1 && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-aethera-foreground">Denial Analysis</h2>
            <p className="text-sm text-aethera-text-secondary">AI-generated analysis of the denial based on the provided codes.</p>

            {loading ? (
              <div className="flex items-center justify-center py-12">
                <svg className="w-8 h-8 text-aethera-primary animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              </div>
            ) : analysis ? (
              <div className="space-y-4">
                {/* Denial category */}
                {analysis.denial_category && (
                  <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                    <p className="text-sm font-medium text-amber-200">Denial Category: {analysis.denial_category}</p>
                  </div>
                )}

                {/* Explanation */}
                {analysis.explanation && (
                  <div>
                    <h3 className="text-sm font-medium text-aethera-foreground mb-2">Explanation</h3>
                    <p className="text-sm text-aethera-text-secondary leading-relaxed">{analysis.explanation}</p>
                  </div>
                )}

                {/* Appealability */}
                {analysis.appealable !== undefined && (
                  <div className={`p-3 rounded-lg ${
                    analysis.appealable
                      ? 'bg-green-500/10 border border-green-500/30'
                      : 'bg-red-500/10 border border-red-500/30'
                  }`}>
                    <p className={`text-sm font-medium ${analysis.appealable ? 'text-green-400' : 'text-red-400'}`}>
                      {analysis.appealable ? 'This denial is appealable' : 'This denial may not be appealable'}
                    </p>
                    {analysis.appeal_deadline && (
                      <p className="text-xs text-aethera-text-secondary mt-1">
                        Appeal deadline: {analysis.appeal_deadline}
                      </p>
                    )}
                  </div>
                )}

                {/* Recommended actions */}
                {analysis.recommended_actions && analysis.recommended_actions.length > 0 && (
                  <div>
                    <h3 className="text-sm font-medium text-aethera-foreground mb-2">Recommended Actions</h3>
                    <ul className="space-y-2">
                      {analysis.recommended_actions.map((action, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className="w-5 h-5 rounded-full bg-aethera-primary/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                            <span className="text-aethera-primary text-xs font-medium">{i + 1}</span>
                          </span>
                          <span className="text-sm text-aethera-text-secondary">{action}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Supporting references */}
                {analysis.references && analysis.references.length > 0 && (
                  <div>
                    <h3 className="text-sm font-medium text-aethera-foreground mb-2">References</h3>
                    <ul className="space-y-1">
                      {analysis.references.map((ref, i) => (
                        <li key={i} className="text-xs text-aethera-text-secondary font-mono">{ref}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-aethera-text-secondary text-sm">
                Analysis will appear after processing the denial codes.
              </div>
            )}
          </div>
        )}

        {/* Step 2: Clinical Rationale */}
        {currentStep === 2 && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-aethera-foreground">Clinical Rationale</h2>
            <p className="text-sm text-aethera-text-secondary">Provide the clinical justification for the appeal.</p>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-aethera-foreground mb-1.5">Medical Necessity *</label>
                <textarea
                  value={clinicalRationale.medicalNecessity}
                  onChange={(e) => updateRationaleField('medicalNecessity', e.target.value)}
                  placeholder="Explain why the service was medically necessary for this patient..."
                  rows={4}
                  className="w-full bg-aethera-background border border-aethera-border rounded-lg px-4 py-2.5 text-aethera-foreground placeholder-aethera-text-secondary focus:border-aethera-primary focus:outline-none resize-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-aethera-foreground mb-1.5">Clinical History</label>
                <textarea
                  value={clinicalRationale.clinicalHistory}
                  onChange={(e) => updateRationaleField('clinicalHistory', e.target.value)}
                  placeholder="Relevant clinical history supporting the appeal..."
                  rows={4}
                  className="w-full bg-aethera-background border border-aethera-border rounded-lg px-4 py-2.5 text-aethera-foreground placeholder-aethera-text-secondary focus:border-aethera-primary focus:outline-none resize-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-aethera-foreground mb-1.5">Supporting Evidence</label>
                <textarea
                  value={clinicalRationale.supportingEvidence}
                  onChange={(e) => updateRationaleField('supportingEvidence', e.target.value)}
                  placeholder="Clinical guidelines, peer-reviewed studies, LCD/NCD references..."
                  rows={3}
                  className="w-full bg-aethera-background border border-aethera-border rounded-lg px-4 py-2.5 text-aethera-foreground placeholder-aethera-text-secondary focus:border-aethera-primary focus:outline-none resize-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-aethera-foreground mb-1.5">Provider Notes</label>
                <textarea
                  value={clinicalRationale.providerNotes}
                  onChange={(e) => updateRationaleField('providerNotes', e.target.value)}
                  placeholder="Any additional notes from the treating provider..."
                  rows={3}
                  className="w-full bg-aethera-background border border-aethera-border rounded-lg px-4 py-2.5 text-aethera-foreground placeholder-aethera-text-secondary focus:border-aethera-primary focus:outline-none resize-none"
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Review Letter */}
        {currentStep === 3 && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-aethera-foreground">Review Appeal Letter</h2>
            <p className="text-sm text-aethera-text-secondary">Review and edit the generated appeal letter before exporting.</p>

            {loading ? (
              <div className="flex items-center justify-center py-12">
                <svg className="w-8 h-8 text-aethera-primary animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              </div>
            ) : (
              <>
                <textarea
                  value={appealLetter}
                  onChange={(e) => { setAppealLetter(e.target.value); setLetterEdited(true); }}
                  rows={20}
                  className="w-full bg-aethera-background border border-aethera-border rounded-lg px-4 py-3 text-aethera-foreground font-mono text-sm focus:border-aethera-primary focus:outline-none resize-y"
                />
                {letterEdited && (
                  <p className="text-xs text-amber-400">Letter has been manually edited</p>
                )}
              </>
            )}
          </div>
        )}

        {/* Step 4: Export */}
        {currentStep === 4 && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-aethera-foreground">Export Appeal Letter</h2>
            <p className="text-sm text-aethera-text-secondary">Your appeal letter is ready for submission.</p>

            <div className="flex flex-col items-center gap-4 py-8">
              <div className="w-24 h-24 rounded-full bg-green-500/20 flex items-center justify-center">
                <svg className="w-12 h-12 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <p className="text-lg font-medium text-aethera-foreground">Appeal Letter Ready</p>

              <div className="flex gap-3">
                <button
                  onClick={handleCopyLetter}
                  className="px-5 py-2.5 bg-aethera-primary hover:bg-cyan-600 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  Copy to Clipboard
                </button>
                <button
                  onClick={handleDownloadLetter}
                  className="px-5 py-2.5 bg-aethera-surface hover:bg-aethera-tertiary text-aethera-foreground rounded-lg font-medium transition-colors border border-aethera-border flex items-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Download as Text
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Navigation Buttons */}
      <div className="flex items-center justify-between">
        <button
          onClick={handleBack}
          disabled={currentStep === 0}
          className="px-4 py-2 text-sm text-aethera-text-secondary hover:text-aethera-foreground disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Back
        </button>
        {currentStep < STEPS.length - 1 && (
          <button
            onClick={handleNext}
            disabled={!canProceed() || loading}
            className="px-6 py-2.5 bg-aethera-primary hover:bg-cyan-600 disabled:bg-aethera-tertiary disabled:text-aethera-text-secondary text-white rounded-lg font-medium transition-colors flex items-center gap-2"
          >
            {loading ? (
              <>
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Processing...
              </>
            ) : (
              <>
                {currentStep === 0 ? 'Analyze Denial' : currentStep === 2 ? 'Generate Letter' : 'Next'}
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
}

function InputField({ label, value, onChange, placeholder, type = 'text' }) {
  return (
    <div>
      <label className="block text-sm font-medium text-aethera-foreground mb-1.5">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full bg-aethera-background border border-aethera-border rounded-lg px-4 py-2.5 text-aethera-foreground placeholder-aethera-text-secondary focus:border-aethera-primary focus:outline-none"
      />
    </div>
  );
}