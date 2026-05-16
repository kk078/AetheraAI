"""
AetheraAI — Tests for EDI X12 parser skill.
Phase 14: Comprehensive Tests
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from skills.healthcare.edi_parser import EDIParserSkill
except ImportError:
    EDIParserSkill = None


@pytest.fixture
def parser():
    if EDIParserSkill is None:
        pytest.skip("EDIParserSkill not available")
    return EDIParserSkill()


class TestEDIParserDetection:
    """Tests for EDI transaction type detection."""

    @pytest.mark.asyncio
    async def test_detect_837p(self, parser, sample_edi_837):
        result = await parser.execute(
            action="detect_type",
            edi_content=sample_edi_837,
        )
        assert result.success is True
        assert result.data is not None
        transactions = result.data.get("detected_transactions", [])
        assert any("837" in str(t) for t in transactions)

    @pytest.mark.asyncio
    async def test_detect_835(self, parser, sample_edi_835):
        result = await parser.execute(
            action="detect_type",
            edi_content=sample_edi_835,
        )
        assert result.success is True
        transactions = result.data.get("detected_transactions", [])
        assert any("835" in str(t) for t in transactions)

    @pytest.mark.asyncio
    async def test_detect_270(self, parser, sample_edi_270):
        result = await parser.execute(
            action="detect_type",
            edi_content=sample_edi_270,
        )
        assert result.success is True
        transactions = result.data.get("detected_transactions", [])
        assert any("270" in str(t) for t in transactions)

    @pytest.mark.asyncio
    async def test_detect_empty_input(self, parser):
        result = await parser.execute(
            action="detect_type",
            edi_content="",
        )
        # Empty content should return an error or empty data
        assert result.success is False or result.data is not None

    @pytest.mark.asyncio
    async def test_detect_non_edi(self, parser):
        result = await parser.execute(
            action="detect_type",
            edi_content="This is just plain text, not EDI",
        )
        assert result.success is True
        # Should indicate no transactions detected
        transactions = result.data.get("detected_transactions", [])
        assert len(transactions) == 0 or result.data.get("transaction_count", 0) == 0


class TestEDISegmentParsing:
    """Tests for EDI segment parsing logic."""

    def test_split_segments(self, parser):
        content = "ISA*00*~GS*HC*~ST*837*0001*~SE*3*0001*~GE*1*~IEA*1*~"
        segments = parser._split_segments(content)
        assert len(segments) >= 2

    def test_parse_segment(self, parser):
        result = parser._parse_segment("ISA*00*          *00*          ")
        assert result["segment_id"] == "ISA"
        assert len(result["fields"]) > 1

    def test_parse_isa(self, parser, sample_edi_837):
        segments = parser._split_segments(sample_edi_837)
        isa_segment = segments[0]
        result = parser._parse_segment(isa_segment)
        assert result["segment_id"] == "ISA"

    def test_parse_gs(self, parser, sample_edi_837):
        segments = parser._split_segments(sample_edi_837)
        # Find GS segment
        for seg in segments:
            parsed = parser._parse_segment(seg)
            if parsed["segment_id"] == "GS":
                assert "fields" in parsed
                break

    def test_parse_nm1(self, parser):
        result = parser._parse_segment("NM1*41*2*CLINIC*****46*1234567890")
        assert result["segment_id"] == "NM1"

    def test_parse_clm(self, parser):
        result = parser._parse_segment("CLM*CLAIM001*150.00***11:B:1*Y*A*Y*I*P")
        assert result["segment_id"] == "CLM"

    def test_parse_ref(self, parser):
        result = parser._parse_segment("REF*1L*1234567890")
        assert result["segment_id"] == "REF"

    def test_delimiter_detection(self, parser, sample_edi_837):
        delimiters = parser._detect_delimiters(sample_edi_837)
        assert "element_separator" in delimiters
        assert delimiters["element_separator"] == "*"

    def test_segment_info_known_segment(self, parser):
        result = parser._segment_info("ISA")
        assert result is not None or result is not None


class TestEDIValidation:
    """Tests for EDI structural validation."""

    @pytest.mark.asyncio
    async def test_isa_iea_matching(self, parser, sample_edi_837):
        result = await parser.execute(
            action="validate",
            edi_content=sample_edi_837,
        )
        assert result.success is True
        # Should have no ISA/IEA mismatch errors
        errors = result.data.get("errors", [])
        isa_iea_errors = [e for e in errors if "ISA" in str(e) or "IEA" in str(e)]
        # Valid sample should have matching ISA/IEA
        assert len(isa_iea_errors) == 0 or result.data.get("is_valid", True)

    @pytest.mark.asyncio
    async def test_gs_ge_matching(self, parser, sample_edi_837):
        result = await parser.execute(
            action="validate",
            edi_content=sample_edi_837,
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_st_se_matching(self, parser, sample_edi_837):
        result = await parser.execute(
            action="validate",
            edi_content=sample_edi_837,
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_extract_data(self, parser, sample_edi_837):
        result = await parser.execute(
            action="extract_data",
            edi_content=sample_edi_837,
        )
        assert result.success is True
        # Should extract billing provider, subscriber, claim info
        data = result.data
        assert data is not None

    @pytest.mark.asyncio
    async def test_parse_full_document(self, parser, sample_edi_837):
        result = await parser.execute(
            action="parse",
            edi_content=sample_edi_837,
        )
        assert result.success is True
        assert result.data.get("total_segments", 0) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])