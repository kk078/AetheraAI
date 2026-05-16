"""
AetheraAI — Tests for data source connectors (CMS NPI, OpenFDA, PubMed).
Phase 14: Comprehensive Tests
"""
import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from connectors.connector_base import ConnectorConfig, ConnectorResult

try:
    from connectors.builtin.cms_npi import CMSNPIConnector
except ImportError:
    CMSNPIConnector = None

try:
    from connectors.builtin.openfda import OpenFDAConnector
except ImportError:
    OpenFDAConnector = None

try:
    from connectors.builtin.pubmed import PubMedConnector
except ImportError:
    PubMedConnector = None


class TestConnectorBase:
    """Tests for ConnectorConfig and ConnectorResult."""

    def test_config_creation(self):
        config = ConnectorConfig(
            name="test",
            version="1.0.0",
            description="Test connector",
            base_url="https://api.example.com",
        )
        assert config.name == "test"
        assert config.base_url == "https://api.example.com"

    def test_config_defaults(self):
        config = ConnectorConfig(
            name="test",
            version="1.0.0",
            description="Test connector",
            base_url="https://api.example.com",
        )
        assert config.auth_type == "none"
        assert config.rate_limit is None
        assert config.timeout == 30

    def test_config_custom_values(self):
        config = ConnectorConfig(
            name="test",
            version="1.0.0",
            description="Test connector",
            base_url="https://api.example.com",
            auth_type="api_key",
            rate_limit=100,
            timeout=60,
        )
        assert config.auth_type == "api_key"
        assert config.rate_limit == 100
        assert config.timeout == 60

    def test_connector_result_success(self):
        result = ConnectorResult(success=True, data={"key": "value"})
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None

    def test_connector_result_failure(self):
        result = ConnectorResult(success=False, error="API error")
        assert result.success is False
        assert result.error == "API error"
        assert result.data is None

    def test_connector_result_timestamp(self):
        result = ConnectorResult(success=True)
        assert result.timestamp is not None

    def test_connector_result_metadata(self):
        result = ConnectorResult(success=True, metadata={"source": "test"})
        assert result.metadata == {"source": "test"}

    def test_connector_result_default_metadata(self):
        result = ConnectorResult(success=True)
        assert result.metadata == {}


class TestCMSNPIConnector:
    """Tests for CMS NPI connector with mocked HTTP."""

    @pytest.fixture
    def connector(self):
        if CMSNPIConnector is None:
            pytest.skip("CMSNPIConnector not available")
        return CMSNPIConnector(config={"base_url": "https://npiregistry.cms.hhs.gov/api/"})

    def test_config_fields(self, connector):
        config = connector.get_config()
        assert config.name == "cms_npi"
        assert config.auth_type == "none"
        assert config.rate_limit == 100

    @pytest.mark.asyncio
    async def test_search_provider_by_name(self, connector):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={
            "result_count": 1,
            "results": [{
                "number": ["1234567890"],
                "basic": {"first_name": "John", "last_name": "Smith", "organization_name": None},
                "addresses": [{"address_purpose": "LOCATION", "city": "Springfield", "state": "IL"}],
                "taxonomies": [{"code": "207Q00000X", "desc": "Family Medicine", "primary": True}],
            }]
        })
        mock_response.raise_for_status = MagicMock()

        connector._client = MagicMock()
        connector._client.request = AsyncMock(return_value=mock_response)
        result = await connector.search(query="Smith", first_name="John")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_get_provider_by_npi(self, connector):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={
            "result_count": 1,
            "results": [{"number": ["1234567890"]}]
        })
        mock_response.raise_for_status = MagicMock()

        connector._client = MagicMock()
        connector._client.request = AsyncMock(return_value=mock_response)
        result = await connector.get(item_id="1234567890")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_error_handling(self, connector):
        connector._client = MagicMock()
        connector._client.request = AsyncMock(side_effect=Exception("Connection error"))
        result = await connector.search(query="test")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_cleanup_closes_client(self, connector):
        connector._client = MagicMock()
        connector._client.aclose = AsyncMock()
        await connector.cleanup()
        assert connector._client is None

    @pytest.mark.asyncio
    async def test_fetch_lookup_endpoint(self, connector):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={
            "result_count": 1,
            "results": [{"number": ["1234567890"]}]
        })
        mock_response.raise_for_status = MagicMock()

        connector._client = MagicMock()
        connector._client.request = AsyncMock(return_value=mock_response)
        result = await connector.fetch("lookup", params={"npi": "1234567890"})
        assert result.success is True

    @pytest.mark.asyncio
    async def test_fetch_unknown_endpoint(self, connector):
        result = await connector.fetch("unknown_endpoint_xyz")
        assert result.success is False


class TestOpenFDAConnector:
    """Tests for OpenFDA connector with mocked HTTP."""

    @pytest.fixture
    def connector(self):
        if OpenFDAConnector is None:
            pytest.skip("OpenFDAConnector not available")
        return OpenFDAConnector(config={"base_url": "https://api.fda.gov/"})

    def test_config_fields(self, connector):
        config = connector.get_config()
        assert config.name == "openfda"

    @pytest.mark.asyncio
    async def test_search_drug_label(self, connector):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={
            "meta": {"results": {"total": 1}},
            "results": [{"id": "test-id", "openfda": {"brand_name": ["Aspirin"]}}]
        })
        mock_response.raise_for_status = MagicMock()

        connector._client = MagicMock()
        connector._client.request = AsyncMock(return_value=mock_response)
        result = await connector.search(query="aspirin", category="drug_label")
        assert result.success is True

    def test_config_with_api_key(self):
        if OpenFDAConnector is None:
            pytest.skip("OpenFDAConnector not available")
        conn = OpenFDAConnector(config={
            "base_url": "https://api.fda.gov/",
            "api_key": "test-key",
        })
        config = conn.get_config()
        assert config.name == "openfda"
        assert config.auth_type == "api_key"
        assert config.rate_limit == 240

    @pytest.mark.asyncio
    async def test_search_unknown_category(self, connector):
        result = await connector.search(query="test", category="nonexistent_category")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_get_by_id(self, connector):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={
            "meta": {"results": {"total": 1}},
            "results": [{"id": "test-id"}]
        })
        mock_response.raise_for_status = MagicMock()

        connector._client = MagicMock()
        connector._client.request = AsyncMock(return_value=mock_response)
        result = await connector.get(item_id="test-id", category="drug_label")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_cleanup_closes_client(self, connector):
        connector._client = MagicMock()
        connector._client.aclose = AsyncMock()
        await connector.cleanup()
        assert connector._client is None


class TestPubMedConnector:
    """Tests for PubMed connector with mocked HTTP."""

    @pytest.fixture
    def connector(self):
        if PubMedConnector is None:
            pytest.skip("PubMedConnector not available")
        return PubMedConnector(config={"base_url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"})

    def test_config_fields(self, connector):
        config = connector.get_config()
        assert config.name == "pubmed"

    @pytest.mark.asyncio
    async def test_search_articles(self, connector):
        mock_search_response = MagicMock()
        mock_search_response.status_code = 200
        mock_search_response.json = MagicMock(return_value={
            "esearchresult": {"idlist": ["12345678"], "count": "1"}
        })
        mock_search_response.raise_for_status = MagicMock()

        mock_fetch_response = MagicMock()
        mock_fetch_response.status_code = 200
        mock_fetch_response.json = MagicMock(return_value={"PubmedArticle": []})
        mock_fetch_response.raise_for_status = MagicMock()

        connector._client = MagicMock()
        connector._client.request = AsyncMock(side_effect=[mock_search_response, mock_fetch_response])
        result = await connector.search(query="diabetes treatment")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_error_handling(self, connector):
        connector._client = MagicMock()
        connector._client.request = AsyncMock(side_effect=Exception("Connection error"))
        result = await connector.search(query="test")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_search_empty_query(self, connector):
        result = await connector.search(query="")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_get_article(self, connector):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={"PubmedArticle": []})
        mock_response.raise_for_status = MagicMock()

        connector._client = MagicMock()
        connector._client.request = AsyncMock(return_value=mock_response)
        result = await connector.get(item_id="12345678")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_cleanup_closes_client(self, connector):
        connector._client = MagicMock()
        connector._client.aclose = AsyncMock()
        await connector.cleanup()
        assert connector._client is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])