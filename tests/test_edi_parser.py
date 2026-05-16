"""Tests for the EDI X12 parser skill."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


class TestEDIParserStructure:
    """Test EDI parsing when the module is available."""

    @pytest.fixture(autouse=True)
    def _import_check(self):
        try:
            from skills.healthcare.edi_parser import EDIParserSkill
            self.skill = EDIParserSkill()
        except ImportError:
            pytest.skip("EDI Parser skill not yet available")

    def test_837p_header_detection(self):
        """837P claims should be detected by ISA/GS/ST segments."""
        sample = "ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *240101*1200*^*00501*000000001*0*P*:~GS*HC*SENDER*RECEIVER*20240101*1200*1*X*005010X222~ST*837*0001*005010X222~"
        result = self.skill.detect_transaction_type(sample)
        assert result == "837p" or result == "837"

    def test_835_remittance_detection(self):
        """835 remittance advices should be detected."""
        sample = "ISA*00*          *00*          *ZZ*PAYER         *ZZ*PROVIDER       *240101*1200*^*00501*000000001*0*P*:~GS*HP*PAYER*PROVIDER*20240101*1200*1*X*005010X221~ST*835*0001*005010X221~"
        result = self.skill.detect_transaction_type(sample)
        assert result == "835"

    def test_270_eligibility_detection(self):
        """270 eligibility inquiries should be detected."""
        sample = "ISA*00*          *00*          *ZZ*PROVIDER       *ZZ*PAYER         *240101*1200*^*00501*000000001*0*P*:~GS*BE*PROVIDER*PAYER*20240101*1200*1*X*005010X279~ST*270*0001*005010X279~"
        result = self.skill.detect_transaction_type(sample)
        assert result == "270"

    def test_segment_parsing(self):
        """Segments should be split by delimiters."""
        sample = "ISA*00*AAA*00*BBB~GS*HC*SRC*DST~ST*837*0001~"
        segments = self.skill.parse_segments(sample)
        assert len(segments) >= 1
        assert segments[0]["segment_id"] == "ISA"

    def test_nm1_segment_parsing(self):
        """NM1 segments should extract entity name info."""
        sample = "NM1*85*2*SMITH*****MD*1234567890~"
        result = self.skill.parse_nm1(sample)
        assert result is not None
        assert result.get("name", "").lower() == "smith" or result.get("last_name", "").lower() == "smith"

    def test_clm_segment_parsing(self):
        """CLM segments should extract claim amount."""
        sample = "CLM*PROV123*150.00***11:B:1Y:Y~"
        result = self.skill.parse_clm(sample)
        assert result is not None
        assert abs(result.get("total_charge", 0) - 150.00) < 0.01

    def test_invalid_edi_handling(self):
        """Invalid/non-EDI data should be handled gracefully."""
        result = self.skill.detect_transaction_type("This is not EDI data at all")
        assert result is None or result == "unknown"

    def test_empty_input(self):
        """Empty input should not crash."""
        result = self.skill.detect_transaction_type("")
        assert result is None or result == "unknown"


class TestEDISegmentParser:
    """Test individual segment parsers."""

    @pytest.fixture(autouse=True)
    def _import_check(self):
        try:
            from skills.healthcare.edi_parser import EDIParserSkill
            self.skill = EDIParserSkill()
        except ImportError:
            pytest.skip("EDI Parser skill not yet available")

    def test_isa_interchange_header(self):
        isa = "ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *240101*1200*^*00501*000000001*0*P*:~"
        result = self.skill.parse_isa(isa)
        assert result is not None
        assert result.get("sender_id") or result.get("sender")

    def test_gs_functional_group(self):
        gs = "GS*HC*SENDER*RECEIVER*20240101*1200*1*X*005010X222~"
        result = self.skill.parse_gs(gs)
        assert result is not None
        assert result.get("functional_id") == "HC" or result.get("type") == "HC"

    def test_ref_segment(self):
        ref = "REF*EI*123456789~"
        result = self.skill.parse_ref(ref)
        assert result is not None
        assert result.get("reference") == "123456789" or result.get("value") == "123456789"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])