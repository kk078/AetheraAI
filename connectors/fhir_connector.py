"""
FHIR Connector for Aethera
Fetches healthcare data from FHIR-compliant EHR systems.
https://www.hl7.org/fhir/
"""
import aiohttp
import time
from typing import Any, Dict, Optional
from .connector_base import AetheraConnector, ConnectorConfig, ConnectorResult


class FHIRConnector(AetheraConnector):
    """FHIR API connector for EHR data access."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', '')
        self.auth_type = config.get('auth_type', 'bearer')
        self.access_token = config.get('access_token', '')
        self.client_id = config.get('client_id', '')
        self.client_secret = config.get('client_secret', '')
        self.token_url = config.get('token_url', '')
        self._token_expires: float = 0.0

    def get_config(self) -> ConnectorConfig:
        return ConnectorConfig(
            name='fhir',
            version='1.0.0',
            description='FHIR R4 - Healthcare data exchange standard',
            base_url=self.base_url,
            auth_type=self.auth_type,
            rate_limit=100,
            timeout=30,
        )

    async def initialize(self) -> bool:
        """Initialize HTTP session and validate connection."""
        if not self.base_url:
            raise ValueError("FHIR base URL required")

        headers = {}
        if self.auth_type == 'oauth2' and self.client_id:
            await self._refresh_token()
        elif self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'

        self._session = aiohttp.ClientSession(
            base_url=self.base_url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=self.get_config().timeout)
        )

        # Validate connection
        try:
            async with self._session.get('/metadata') as resp:
                if resp.status != 200:
                    return False
        except Exception:
            return False

        return True

    async def _refresh_token(self) -> None:
        """Refresh OAuth2 access token using client credentials flow."""
        if not self.token_url or not self.client_id:
            return

        async with aiohttp.ClientSession() as session:
            data = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
            }
            if self.client_secret:
                data['client_secret'] = self.client_secret

            async with session.post(self.token_url, data=data) as resp:
                if resp.status == 200:
                    token_data = await resp.json()
                    self.access_token = token_data.get('access_token', '')
                    expires_in = token_data.get('expires_in', 3600)
                    self._token_expires = time.monotonic() + expires_in - 60  # Refresh 60s early

    async def _ensure_token(self) -> None:
        """Ensure the access token is valid, refreshing if needed."""
        if self.auth_type == 'oauth2' and self._token_expires and time.monotonic() >= self._token_expires:
            await self._refresh_token()
            if self._session:
                self._session.headers.update({
                    'Authorization': f'Bearer {self.access_token}'
                })

    async def cleanup(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def fetch(self, endpoint: str, params: Optional[Dict] = None) -> ConnectorResult:
        """Fetch from FHIR server."""
        try:
            await self._ensure_token()
            resource_type = params.get('resource_type', endpoint)

            if resource_type == 'Patient':
                return await self._fetch_resource('Patient', params)
            elif resource_type == 'Observation':
                return await self._fetch_resource('Observation', params)
            elif resource_type == 'Condition':
                return await self._fetch_resource('Condition', params)
            elif resource_type == 'MedicationRequest':
                return await self._fetch_resource('MedicationRequest', params)
            elif resource_type == 'Procedure':
                return await self._fetch_resource('Procedure', params)
            elif resource_type == 'DiagnosticReport':
                return await self._fetch_resource('DiagnosticReport', params)
            elif resource_type == 'Encounter':
                return await self._fetch_resource('Encounter', params)
            elif resource_type == 'Claim':
                return await self._fetch_resource('Claim', params)
            elif resource_type == 'ExplanationOfBenefit':
                return await self._fetch_resource('ExplanationOfBenefit', params)
            elif resource_type == 'Coverage':
                return await self._fetch_resource('Coverage', params)
            elif resource_type == 'Practitioner':
                return await self._fetch_resource('Practitioner', params)
            elif resource_type == 'Organization':
                return await self._fetch_resource('Organization', params)
            else:
                return ConnectorResult(success=False, error=f"Unknown resource type: {resource_type}")
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    async def _fetch_resource(self, resource_type: str, params: Dict) -> ConnectorResult:
        """Fetch FHIR resource."""
        url = f"{resource_type}"

        query_params = {}

        # Add FHIR search parameters
        if params.get('id'):
            url = f"{resource_type}/{params['id']}"
        elif params.get('patient'):
            query_params['patient'] = params['patient']
        if params.get('identifier'):
            query_params['identifier'] = params['identifier']
        if params.get('name'):
            query_params['name'] = params['name']
        if params.get('birthdate'):
            query_params['birthdate'] = params['birthdate']
        if params.get('gender'):
            query_params['gender'] = params['gender']
        if params.get('status'):
            query_params['status'] = params['status']
        if params.get('date'):
            query_params['date'] = params['date']
        if params.get('code'):
            query_params['code'] = params['code']
        if params.get('category'):
            query_params['category'] = params['category']
        if params.get('_count'):
            query_params['_count'] = min(params['_count'], 100)
        if params.get('_sort'):
            query_params['_sort'] = params['_sort']
        if params.get('_lastUpdated'):
            query_params['_lastUpdated'] = params['_lastUpdated']

        async with self._session.get(url, params=query_params) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                return ConnectorResult(success=False, error=f"FHIR API error ({resp.status}): {error_text}")

            data = await resp.json()

            # Handle single resource vs Bundle
            if data.get('resourceType') == 'Bundle':
                entries = data.get('entry', [])
                resources = [e.get('resource', {}) for e in entries]
                return ConnectorResult(
                    success=True,
                    data=resources,
                    metadata={
                        'source': 'FHIR',
                        'resource_type': resource_type,
                        'total': data.get('total', len(resources)),
                        'next': self._get_next_link(data),
                    }
                )
            else:
                return ConnectorResult(
                    success=True,
                    data=data,
                    metadata={'source': 'FHIR', 'resource_type': resource_type}
                )

    def _get_next_link(self, bundle: Dict) -> Optional[str]:
        """Get next page link from Bundle."""
        for link in bundle.get('link', []):
            if link.get('relation') == 'next':
                return link.get('url')
        return None


class EpicFHIRConnector(FHIRConnector):
    """Epic-specific FHIR connector with SMART on FHIR OAuth2 support."""

    EPIC_ENVIRONMENTS = {
        'production': 'https://fhir.epic.com/interconnect/fhir/R4',
        'sandbox': 'https://fhir.epic.com/interconnect/fhir/R4',
    }

    def __init__(self, config: Dict[str, Any]):
        config.setdefault('auth_type', 'oauth2')
        super().__init__(config)
        self.environment = config.get('environment', 'production')
        if not self.base_url:
            self.base_url = self.EPIC_ENVIRONMENTS.get(self.environment, self.EPIC_ENVIRONMENTS['production'])
        if not self.token_url:
            self.token_url = config.get('token_url', f'{self.base_url}/.well-known/smart-configuration')

    def get_config(self) -> ConnectorConfig:
        return ConnectorConfig(
            name='fhir_epic',
            version='1.0.0',
            description='Epic FHIR API - Interconnect and SMART on FHIR',
            base_url=self.base_url,
            auth_type='oauth2',
            rate_limit=100,
            timeout=30,
        )

    async def _discover_token_url(self) -> str:
        """Discover OAuth2 token URL from Epic's SMART configuration."""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(self.token_url) as resp:
                    if resp.status == 200:
                        smart_config = await resp.json()
                        return smart_config.get('token_endpoint', '')
            except Exception:
                pass
        return ''

    async def initialize(self) -> bool:
        """Initialize with SMART on FHIR discovery."""
        if self.client_id and not self.token_url.endswith('/oauth2/token'):
            discovered_url = await self._discover_token_url()
            if discovered_url:
                self.token_url = discovered_url
        return await super().initialize()

    async def _fetch_resource(self, resource_type: str, params: Dict) -> ConnectorResult:
        """Epic-specific resource fetch with USCDI profile support."""
        # Epic supports _profile parameter for USCDI profiles
        if params.get('profile'):
            params.setdefault('_profile', params.pop('profile'))

        return await super()._fetch_resource(resource_type, params)


class CernerFHIRConnector(FHIRConnector):
    """Cerner (Oracle Health) FHIR connector with OAuth2 support."""

    CERNER_ENVIRONMENTS = {
        'production': 'https://fhir-myrecord.cerner.com/R4',
        'sandbox': 'https://fhir-myrecord.stu3.cerner.com/R4',
    }

    def __init__(self, config: Dict[str, Any]):
        config.setdefault('auth_type', 'oauth2')
        super().__init__(config)
        self.principal = config.get('principal', '')
        if not self.base_url:
            self.base_url = self.CERNER_ENVIRONMENTS.get('production', config.get('base_url', ''))
        if not self.token_url:
            self.token_url = config.get('token_url', f'{self.base_url}/auth/token')

    def get_config(self) -> ConnectorConfig:
        return ConnectorConfig(
            name='fhir_cerner',
            version='1.0.0',
            description='Cerner (Oracle Health) FHIR API',
            base_url=self.base_url,
            auth_type='oauth2',
            rate_limit=100,
            timeout=30,
        )

    async def initialize(self) -> bool:
        """Initialize Cerner FHIR connection."""
        return await super().initialize()

    async def _fetch_resource(self, resource_type: str, params: Dict) -> ConnectorResult:
        """Cerner-specific resource fetch with tenant header support."""
        # Cerner requires BAHMNI-TENANT header for multi-tenant setups
        headers = {}
        if self.principal:
            headers['X-BAHMNI-TENANT'] = self.principal

        result = await super()._fetch_resource(resource_type, params)

        # Cerner may wrap errors in OperationOutcome
        if result.success and isinstance(result.data, dict):
            if result.data.get('resourceType') == 'OperationOutcome':
                issues = result.data.get('issue', [])
                if issues:
                    severity = issues[0].get('severity', 'error')
                    if severity in ('error', 'fatal'):
                        return ConnectorResult(
                            success=False,
                            error=f"Cerner FHIR error: {issues[0].get('diagnostics', 'Unknown error')}"
                        )
        return result


def register_connector():
    """Register the FHIR connector."""
    import os
    return FHIRConnector, {
        'base_url': os.getenv('FHIR_BASE_URL', ''),
        'auth_type': 'bearer',
        'access_token': os.getenv('FHIR_ACCESS_TOKEN', ''),
    }
