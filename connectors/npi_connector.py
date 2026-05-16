"""
NPI Connector for Aethera
Fetches provider information from CMS NPI Registry.
https://npiregistry.cms.hhs.gov/
"""
import aiohttp
from typing import Any, Dict, Optional
from .connector_base import AetheraConnector, ConnectorConfig, ConnectorResult


class NPIConnector(AetheraConnector):
    """CMS NPI Registry connector for provider lookup."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', 'https://npiregistry.cms.hhs.gov/api/')

    def get_config(self) -> ConnectorConfig:
        return ConnectorConfig(
            name='npi',
            version='1.0.0',
            description='CMS NPI Registry - National Provider Identifier lookup',
            base_url=self.base_url,
            auth_type='none',
            rate_limit=100,  # Free API has reasonable limits
            timeout=30,
        )

    async def initialize(self) -> bool:
        """Initialize HTTP session."""
        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.get_config().timeout))
        return True

    async def cleanup(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def fetch(self, endpoint: str, params: Optional[Dict] = None) -> ConnectorResult:
        """Fetch from NPI registry."""
        try:
            if endpoint == 'lookup':
                return await self._lookup_npi(params)
            elif endpoint == 'search':
                return await self._search_providers(params)
            else:
                return ConnectorResult(success=False, error=f"Unknown endpoint: {endpoint}")
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    async def _lookup_npi(self, params: Dict) -> ConnectorResult:
        """Lookup provider by NPI number."""
        npi = params.get('npi')
        if not npi:
            return ConnectorResult(success=False, error="NPI number required")

        async with self._session.get(self.base_url, params={'number': npi, 'version': '2.1'}) as resp:
            if resp.status != 200:
                return ConnectorResult(success=False, error=f"NPI API error: {resp.status}")

            data = await resp.json()

            if not data.get('results'):
                return ConnectorResult(success=False, error="Provider not found")

            provider = data['results'][0]
            return ConnectorResult(
                success=True,
                data=self._normalize_provider(provider),
                metadata={'source': 'CMS NPI Registry', 'version': '2.1'}
            )

    async def _search_providers(self, params: Dict) -> ConnectorResult:
        """Search providers by criteria."""
        search_params = {'version': '2.1'}

        # Map common params
        if params.get('first_name'):
            search_params['first_name'] = params['first_name']
        if params.get('last_name'):
            search_params['last_name'] = params['last_name']
        if params.get('organization_name'):
            search_params['organization_name'] = params['organization_name']
        if params.get('city'):
            search_params['city'] = params['city']
        if params.get('state'):
            search_params['state'] = params['state']
        if params.get('zip'):
            search_params['postal_code'] = params['zip']
        if params.get('taxonomy'):
            search_params['taxonomy'] = params['taxonomy']
        if params.get('type'):
            search_params['type'] = params['type']  # 'NPI-1' or 'NPI-2'
        if params.get('limit'):
            search_params['limit'] = min(params['limit'], 200)  # Max 200

        url = f"{self.base_url}"
        async with self._session.get(url, params=search_params) as resp:
            if resp.status != 200:
                return ConnectorResult(success=False, error=f"NPI API error: {resp.status}")

            data = await resp.json()
            results = data.get('results', [])

            return ConnectorResult(
                success=True,
                data=[self._normalize_provider(p) for p in results],
                metadata={
                    'source': 'CMS NPI Registry',
                    'total': data.get('result_count', 0),
                    'limit': params.get('limit', 200)
                }
            )

    def _normalize_provider(self, provider: Dict) -> Dict:
        """Normalize provider data."""
        return {
            'npi': provider.get('number', ''),
            'type': provider.get('type', ''),  # NPI-1 (individual) or NPI-2 (organization)
            'name': self._get_provider_name(provider),
            'addresses': self._get_addresses(provider),
            'taxonomies': self._get_taxonomies(provider),
            'phone': provider.get('telephone_number', ''),
            'fax': provider.get('fax_number', ''),
            'email': provider.get('email', ''),
            'certification': provider.get('certification', ''),
            'other_names': provider.get('other_names', []),
        }

    def _get_provider_name(self, provider: Dict) -> str:
        """Extract provider name."""
        if provider.get('basic', {}).get('first_name'):
            basic = provider['basic']
            return f"{basic.get('first_name', '')} {basic.get('middle_name', '')} {basic.get('last_name', '')}".strip()
        return provider.get('organization_name', 'Unknown')

    def _get_addresses(self, provider: Dict) -> Dict:
        """Extract addresses."""
        addresses = {}

        if provider.get('addresses'):
            for addr in provider['addresses']:
                if addr.get('address_purpose') == 'LOCATION':
                    addresses['location'] = addr
                elif addr.get('address_purpose') == 'MAILING':
                    addresses['mailing'] = addr
                elif addr.get('address_purpose') == 'PRIMARY':
                    addresses['primary'] = addr

        return addresses

    def _get_taxonomies(self, provider: Dict) -> list:
        """Extract taxonomy codes."""
        taxonomies = []
        if provider.get('taxonomies'):
            for tax in provider['taxonomies']:
                taxonomies.append({
                    'code': tax.get('code', ''),
                    'name': tax.get('desc', ''),
                    'primary': tax.get('primary', False),
                    'state': tax.get('state', ''),
                })
        return taxonomies


def register_connector():
    """Register the NPI connector."""
    return NPIConnector, {'base_url': 'https://npiregistry.cms.hhs.gov/api/'}
