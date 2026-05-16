"""
Aethera Built-in Connectors Package
Production-ready connectors for common data sources.
"""
from .cms_npi import CMSNPIConnector
from .cms_coverage import CMSCoverageConnector
from .openfda import OpenFDAConnector
from .pubmed import PubMedConnector
from .rxnorm import RxNormConnector
from .snomed import SNOMEDConnector
from .loinc import LOINCConnector
from .umls import UMLSConnector
from .fhir_client import FHIRClientConnector
from .cms_data import CMSDataConnector
from .federal_register import FederalRegisterConnector
from .hcpcs_api import HCPCSConnector
from .nucc_taxonomy import NUCCTaxonomyConnector
from .cloudflare_api import CloudflareConnector
from .github_api import GitHubConnector
from .searxng import SearXNGConnector
from .wikipedia import WikipediaConnector
from .arxiv import ArXivConnector
from .weather import WeatherConnector

__all__ = [
    "CMSNPIConnector",
    "CMSCoverageConnector",
    "OpenFDAConnector",
    "PubMedConnector",
    "RxNormConnector",
    "SNOMEDConnector",
    "LOINCConnector",
    "UMLSConnector",
    "FHIRClientConnector",
    "CMSDataConnector",
    "FederalRegisterConnector",
    "HCPCSConnector",
    "NUCCTaxonomyConnector",
    "CloudflareConnector",
    "GitHubConnector",
    "SearXNGConnector",
    "WikipediaConnector",
    "ArXivConnector",
    "WeatherConnector",
]

CONNECTOR_REGISTRY = {
    "cms_npi": (CMSNPIConnector, {"base_url": "https://npiregistry.cms.hhs.gov/api/"}),
    "cms_coverage": (CMSCoverageConnector, {"base_url": "https://www.cms.gov/medicare-coverage-database"}),
    "openfda": (OpenFDAConnector, {"base_url": "https://api.fda.gov/"}),
    "pubmed": (PubMedConnector, {"base_url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"}),
    "rxnorm": (RxNormConnector, {"base_url": "https://rxnav.nlm.nih.gov/REST/"}),
    "snomed": (SNOMEDConnector, {"base_url": "https://browser.ihtsdotools.org/snowstorm/snomed-ct/"}),
    "loinc": (LOINCConnector, {"base_url": "https://fhir.loinc.org/"}),
    "umls": (UMLSConnector, {"base_url": "https://uts-ws.nlm.nih.gov/rest/"}),
    "fhir_client": (FHIRClientConnector, {}),
    "cms_data": (CMSDataConnector, {"base_url": "https://data.cms.gov/provider-data/api/1/datastore/query/"}),
    "federal_register": (FederalRegisterConnector, {"base_url": "https://www.federalregister.gov/api/v1/"}),
    "hcpcs": (HCPCSConnector, {"base_url": "https://www.cms.gov/Medicare/Coding/HCPCSReleaseCodeSets/"}),
    "nucc_taxonomy": (NUCCTaxonomyConnector, {"base_url": "https://www.nucc.org/static/"}),
    "cloudflare": (CloudflareConnector, {"base_url": "https://api.cloudflare.com/client/v4/"}),
    "github": (GitHubConnector, {"base_url": "https://api.github.com/"}),
    "searxng": (SearXNGConnector, {"base_url": "http://localhost:8080/"}),
    "wikipedia": (WikipediaConnector, {"base_url": "https://en.wikipedia.org/w/api.php"}),
    "arxiv": (ArXivConnector, {"base_url": "http://export.arxiv.org/api/"}),
    "weather": (WeatherConnector, {"base_url": "https://api.open-meteo.com/v1/"}),
}