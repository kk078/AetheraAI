"""
CMS Connector for Aethera
Fetches data from CMS APIs (NPPES, PECOS, etc.).
"""
import aiohttp
from typing import Any, Dict, Optional
from .connector_base import AetheraConnector, ConnectorConfig, ConnectorResult


class CMSConnector(AetheraConnector):
    """CMS API connector for various CMS data sources."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', 'https://data.cms.gov/')

    def get_config(self) -> ConnectorConfig:
        return ConnectorConfig(
            name='cms',
            version='1.0.0',
            description='CMS Data - Medicare provider, payment, and quality data',
            base_url=self.base_url,
            auth_type='none',
            rate_limit=60,
            timeout=30,
        )

    async def initialize(self) -> bool:
        """Initialize HTTP session."""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.get_config().timeout)
        )
        return True

    async def cleanup(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def fetch(self, endpoint: str, params: Optional[Dict] = None) -> ConnectorResult:
        """Fetch from CMS data APIs."""
        try:
            if endpoint == 'provider':
                return await self._fetch_provider_data(params)
            elif endpoint == 'payment':
                return await self._fetch_payment_data(params)
            elif endpoint == 'quality':
                return await self._fetch_quality_data(params)
            elif endpoint == 'pfs':
                return await self._fetch_fee_schedule(params)
            elif endpoint == 'ncci':
                return await self._fetch_ncci_edits(params)
            else:
                return ConnectorResult(success=False, error=f"Unknown endpoint: {endpoint}")
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    async def _fetch_provider_data(self, params: Dict) -> ConnectorResult:
        """Fetch CMS provider data."""
        dataset = params.get('dataset', 'provider-of-service')

        url = f"{self.base_url}provider-data/{dataset}.json"

        query_params = {}
        if params.get('npi'):
            query_params['npi'] = params['npi']
        if params.get('state'):
            query_params['state'] = params['state']
        if params.get('city'):
            query_params['city'] = params['city']
        if params.get('limit'):
            query_params['_limit'] = min(params['limit'], 100)

        async with self._session.get(url, params=query_params) as resp:
            if resp.status != 200:
                return ConnectorResult(success=False, error=f"CMS API error: {resp.status}")

            data = await resp.json()

            return ConnectorResult(
                success=True,
                data=data,
                metadata={'source': 'CMS.gov', 'dataset': dataset}
            )

    async def _fetch_payment_data(self, params: Dict) -> ConnectorResult:
        """Fetch Medicare payment data."""
        year = params.get('year', '2024')
        dataset = params.get('dataset', f'medicare-provider-util-pay-reimbursement-{year}')

        url = f"{self.base_url}provider-data/{dataset}.json"

        query_params = {}
        if params.get('npi'):
            query_params['npi'] = params['npi']
        if params.get('hcpcs_code'):
            query_params['hcpcs_code'] = params['hcpcs_code']
        if params.get('place_of_service'):
            query_params['place_of_service'] = params['place_of_service']

        async with self._session.get(url, params=query_params) as resp:
            if resp.status != 200:
                return ConnectorResult(success=False, error=f"CMS API error: {resp.status}")

            data = await resp.json()

            return ConnectorResult(
                success=True,
                data=data,
                metadata={'source': 'CMS.gov', 'dataset': dataset, 'year': year}
            )

    async def _fetch_quality_data(self, params: Dict) -> ConnectorResult:
        """Fetch CMS quality measures data."""
        program = params.get('program', 'hospital-compare')
        dataset = params.get('dataset', f'{program}-current')

        url = f"{self.base_url}quality-data/{dataset}.json"

        query_params = {}
        if params.get('provider_id'):
            query_params['provider_id'] = params['provider_id']
        if params.get('measure'):
            query_params['measure'] = params['measure']

        async with self._session.get(url, params=query_params) as resp:
            if resp.status != 200:
                return ConnectorResult(success=False, error=f"CMS API error: {resp.status}")

            data = await resp.json()

            return ConnectorResult(
                success=True,
                data=data,
                metadata={'source': 'CMS.gov', 'program': program}
            )

    async def _fetch_fee_schedule(self, params: Dict) -> ConnectorResult:
        """Fetch Medicare Physician Fee Schedule."""
        year = params.get('year', '2024')
        url = f"{self.base_url}rate-setting/data/{year}-medicare-physician-fee-schedule.json"

        query_params = {}
        if params.get('hcpcs_code'):
            query_params['hcpcs_code'] = params['hcpcs_code']
        if params.get('locality'):
            query_params['locality'] = params['locality']

        async with self._session.get(url, params=query_params) as resp:
            if resp.status != 200:
                return ConnectorResult(success=False, error=f"CMS API error: {resp.status}")

            data = await resp.json()

            return ConnectorResult(
                success=True,
                data=data,
                metadata={'source': 'CMS.gov', 'year': year, 'type': 'PFS'}
            )

    async def _fetch_ncci_edits(self, params: Dict) -> ConnectorResult:
        """Fetch NCCI edit data."""
        quarter = params.get('quarter', 'Q1')
        year = params.get('year', '2024')

        # NCCI edits are typically downloaded as files
        # This is a placeholder for the actual endpoint
        url = f"{self.base_url}ncci-data/ncci-edits-{year}-{quarter}.json"

        query_params = {}
        if params.get('cpt1'):
            query_params['cpt1'] = params['cpt1']
        if params.get('cpt2'):
            query_params['cpt2'] = params['cpt2']

        async with self._session.get(url, params=query_params) as resp:
            if resp.status != 200:
                return ConnectorResult(success=False, error=f"CMS API error: {resp.status}")

            data = await resp.json()

            return ConnectorResult(
                success=True,
                data=data,
                metadata={'source': 'CMS.gov', 'year': year, 'quarter': quarter}
            )


def register_connector():
    """Register the CMS connector."""
    return CMSConnector, {'base_url': 'https://data.cms.gov/'}
