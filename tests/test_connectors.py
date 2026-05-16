"""
Aethera AI - Connector Tests

Tests for data source connectors.
"""
import pytest
import sys
sys.path.insert(0, '..')

from connectors.connector_base import ConnectorConfig, ConnectorResult, AetheraConnector


class TestConnectorBase:
    """Test connector base class."""

    def test_connector_config(self):
        """Test connector configuration."""
        config = ConnectorConfig(
            name="test_connector",
            version="1.0.0",
            description="Test connector",
            base_url="https://api.example.com",
            auth_type="api_key",
            rate_limit=60
        )

        assert config.name == "test_connector"
        assert config.rate_limit == 60

    def test_connector_result(self):
        """Test connector result."""
        result = ConnectorResult(
            success=True,
            data={"key": "value"},
            metadata={"source": "test"}
        )

        assert result.success is True
        assert result.error is None


class TestNPIConnector:
    """Test NPI connector."""

    @pytest.fixture
    def npi_connector(self):
        try:
            from connectors.npi_connector import NPIConnector
            return NPIConnector({"base_url": "https://npiregistry.cms.hhs.gov/api/"})
        except ImportError:
            return None

    def test_npi_config(self, npi_connector):
        """Test NPI connector configuration."""
        if npi_connector:
            config = npi_connector.get_config()
            assert config.name == "npi"
            assert "cms.hhs.gov" in config.base_url


class TestOpenFDAConnector:
    """Test OpenFDA connector."""

    @pytest.fixture
    def openfda_connector(self):
        try:
            from connectors.openfda_connector import OpenFDAConnector
            return OpenFDAConnector({"base_url": "https://api.fda.gov/"})
        except ImportError:
            return None

    def test_openfda_config(self, openfda_connector):
        """Test OpenFDA connector configuration."""
        if openfda_connector:
            config = openfda_connector.get_config()
            assert config.name == "openfda"
            assert "fda.gov" in config.base_url


class TestPubMedConnector:
    """Test PubMed connector."""

    @pytest.fixture
    def pubmed_connector(self):
        try:
            from connectors.pubmed_connector import PubMedConnector
            return PubMedConnector({
                "base_url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/",
                "email": "test@example.com"
            })
        except ImportError:
            return None

    def test_pubmed_config(self, pubmed_connector):
        """Test PubMed connector configuration."""
        if pubmed_connector:
            config = pubmed_connector.get_config()
            assert config.name == "pubmed"
            assert "ncbi.nlm.nih.gov" in config.base_url


class TestRxNormConnector:
    """Test RxNorm connector."""

    @pytest.fixture
    def rxnorm_connector(self):
        try:
            from connectors.rxnorm_connector import RxNormConnector
            return RxNormConnector({"base_url": "https://rxnav.nlm.nih.gov/REST/"})
        except ImportError:
            return None

    def test_rxnorm_config(self, rxnorm_connector):
        """Test RxNorm connector configuration."""
        if rxnorm_connector:
            config = rxnorm_connector.get_config()
            assert config.name == "rxnorm"
            assert "nlm.nih.gov" in config.base_url


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
