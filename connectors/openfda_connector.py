"""
OpenFDA Connector for Aethera
Fetches drug, device, and food safety data from FDA.
https://open.fda.gov/
"""
import aiohttp
from typing import Any, Dict, Optional
from .connector_base import AetheraConnector, ConnectorConfig, ConnectorResult


class OpenFDAConnector(AetheraConnector):
    """OpenFDA API connector for drug/device safety data."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', 'https://api.fda.gov/')
        self.api_key = config.get('api_key', '')  # Optional, increases rate limits

    def get_config(self) -> ConnectorConfig:
        return ConnectorConfig(
            name='openfda',
            version='1.0.0',
            description='OpenFDA - Drug, device, and food safety data',
            base_url=self.base_url,
            auth_type='api_key',
            rate_limit=240 if self.api_key else 4,  # 4/sec without key, 240/sec with key
            timeout=30,
        )

    async def initialize(self) -> bool:
        """Initialize HTTP session."""
        headers = {}
        if self.api_key:
            headers['X-Api-Key'] = self.api_key

        self._session = aiohttp.ClientSession(
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=self.get_config().timeout)
        )
        return True

    async def cleanup(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def fetch(self, endpoint: str, params: Optional[Dict] = None) -> ConnectorResult:
        """Fetch from OpenFDA API."""
        try:
            if endpoint == 'drug/label':
                return await self._fetch_drug_label(params)
            elif endpoint == 'drug/event':
                return await self._fetch_adverse_events(params)
            elif endpoint == 'device/event':
                return await self._fetch_device_events(params)
            elif endpoint == 'device/recall':
                return await self._fetch_device_recalls(params)
            elif endpoint == 'food/event':
                return await self._fetch_food_events(params)
            else:
                return ConnectorResult(success=False, error=f"Unknown endpoint: {endpoint}")
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    async def _fetch_drug_label(self, params: Dict) -> ConnectorResult:
        """Fetch drug label information."""
        search = params.get('search', '')
        if not search:
            return ConnectorResult(success=False, error="Search query required")

        return await self._query('drug/label.json', search, params)

    async def _fetch_adverse_events(self, params: Dict) -> ConnectorResult:
        """Fetch drug adverse event reports."""
        search = params.get('search', '')
        if not search:
            return ConnectorResult(success=False, error="Search query required")

        return await self._query('drug/event.json', search, params)

    async def _fetch_device_events(self, params: Dict) -> ConnectorResult:
        """Fetch medical device event reports."""
        search = params.get('search', '')
        if not search:
            return ConnectorResult(success=False, error="Search query required")

        return await self._query('device/event.json', search, params)

    async def _fetch_device_recalls(self, params: Dict) -> ConnectorResult:
        """Fetch medical device recalls."""
        search = params.get('search', '')
        if not search:
            return ConnectorResult(success=False, error="Search query required")

        return await self._query('device/recall.json', search, params)

    async def _fetch_food_events(self, params: Dict) -> ConnectorResult:
        """Fetch food adverse event reports."""
        search = params.get('search', '')
        if not search:
            return ConnectorResult(success=False, error="Search query required")

        return await self._query('food/event.json', search, params)

    async def _query(self, endpoint: str, search: str, params: Dict) -> ConnectorResult:
        """Execute OpenFDA query."""
        url = f"{self.base_url}{endpoint}"

        query_params = {
            'search': search,
            'limit': min(params.get('limit', 10), 1000),  # Max 1000
        }

        if params.get('skip'):
            query_params['skip'] = params['skip']

        async with self._session.get(url, params=query_params) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                return ConnectorResult(success=False, error=f"FDA API error ({resp.status}): {error_text}")

            data = await resp.json()

            # Parse results
            results = data.get('results', [])
            meta = data.get('meta', {})

            return ConnectorResult(
                success=True,
                data=results,
                metadata={
                    'source': 'OpenFDA',
                    'endpoint': endpoint.split('.')[0],
                    'total_results': meta.get('results', {}).get('total', 0),
                    'returned': len(results),
                    'skip': meta.get('results', {}).get('skip', 0),
                }
            )


def register_connector():
    """Register the OpenFDA connector."""
    import os
    return OpenFDAConnector, {
        'base_url': 'https://api.fda.gov/',
        'api_key': os.getenv('FDA_API_KEY', ''),
    }
