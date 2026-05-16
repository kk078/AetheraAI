"""
Aethera AI - Sensitivity Detection Tests

Tests for PHI/PII detection and redaction.
"""
import pytest
import sys
sys.path.insert(0, '..')

from orchestrator.sensitivity import SensitivityDetector, PHIResult


class TestSensitivityDetector:
    """Test PHI/PII detection."""

    @pytest.fixture
    def detector(self):
        return SensitivityDetector()

    def test_ssn_detection(self, detector):
        """Test SSN detection."""
        text = "Patient SSN: 123-45-6789"
        result = detector.detect_phi(text)

        assert result.contains_phi is True
        assert 'SSN' in result.phi_types

    def test_medical_record_detection(self, detector):
        """Test medical record number detection."""
        text = "MRN: 1234567890"
        result = detector.detect_phi(text)

        assert result.contains_phi is True
        assert 'Medical Record Number' in result.phi_types

    def test_date_detection(self, detector):
        """Test date of service detection."""
        text = "Date of service: 01/15/2024"
        result = detector.detect_phi(text)

        assert result.contains_phi is True
        assert 'Date of Service' in result.phi_types

    def test_name_detection(self, detector):
        """Test patient name detection."""
        text = "Patient: John Smith"
        result = detector.detect_phi(text)

        assert result.contains_phi is True
        assert 'Patient Name' in result.phi_types

    def test_non_phi_text(self, detector):
        """Test non-PHI text."""
        text = "The weather is nice today."
        result = detector.detect_phi(text)

        assert result.contains_phi is False
        assert len(result.phi_types) == 0

    def test_redaction(self, detector):
        """Test PHI redaction."""
        text = "Patient SSN: 123-45-6789, MRN: 1234567890"
        redacted = detector.redact_phi(text)

        assert "123-45-6789" not in redacted
        assert "1234567890" not in redacted
        assert "[SSN]" in redacted or "[REDACTED]" in redacted

    def test_multiple_phi_types(self, detector):
        """Test detection of multiple PHI types."""
        text = "Patient John Smith (SSN: 123-45-6789) was seen on 01/15/2024"
        result = detector.detect_phi(text)

        assert result.contains_phi is True
        assert len(result.phi_types) >= 3  # Name, SSN, Date

    def test_healthcare_codes_not_phi(self, detector):
        """Test that healthcare codes alone are not PHI."""
        text = "ICD-10 code E11.9 for Type 2 Diabetes"
        result = detector.detect_phi(text)

        # Codes without patient identifiers are not PHI
        assert result.contains_phi is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
