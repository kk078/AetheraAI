"""
RxNorm Connector for Aethera
Fetches drug terminology from NLM RxNorm API.
https://www.nlm.nih.gov/research/umls/rxnorm/docs/api.html
"""
import aiohttp
from typing import Any, Dict, Optional
from .connector_base import AetheraConnector, ConnectorConfig, ConnectorResult


class RxNormConnector(AetheraConnector):
    """RxNorm API connector for drug terminology."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', 'https://rxnav.nlm.nih.gov/REST/')

    def get_config(self) -> ConnectorConfig:
        return ConnectorConfig(
            name='rxnorm',
            version='1.0.0',
            description='RxNorm - Normalized drug terminology from NLM',
            base_url=self.base_url,
            auth_type='none',
            rate_limit=60,  # Reasonable limit for free API
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
        """Fetch from RxNorm API."""
        try:
            if endpoint == 'search':
                return await self._search_drug(params)
            elif endpoint == 'rxcui':
                return await self._get_rxcui(params)
            elif endpoint == 'properties':
                return await self._get_properties(params)
            elif endpoint == 'related':
                return await self._get_related(params)
            elif endpoint == 'ndc':
                return await self._get_ndc(params)
            elif endpoint == 'interaction':
                return await self._check_interaction(params)
            else:
                return ConnectorResult(success=False, error=f"Unknown endpoint: {endpoint}")
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    async def _search_drug(self, params: Dict) -> ConnectorResult:
        """Search for drugs by name."""
        query = params.get('query', '')
        if not query:
            return ConnectorResult(success=False, error="Search query required")

        url = f"{self.base_url}spellsuggestions.json"
        async with self._session.get(url, params={'name': query}) as resp:
            if resp.status != 200:
                return ConnectorResult(success=False, error=f"RxNorm API error: {resp.status}")

            data = await resp.json()
            suggestions = data.get('suggestionGroup', [{}])[0].get('suggestionList', [])

            return ConnectorResult(
                success=True,
                data=[
                    {'name': s.get('name', ''), 'rxcui': s.get('rxcui', '')}
                    for s in suggestions[:20]
                ],
                metadata={'source': 'RxNorm', 'query': query}
            )

    async def _get_rxcui(self, params: Dict) -> ConnectorResult:
        """Get RxCUI for a drug name."""
        drug_name = params.get('drug_name', '')
        if not drug_name:
            return ConnectorResult(success=False, error="Drug name required")

        url = f"{self.base_url}rxnames.json"
        async with self._session.get(url, params={'name': drug_name}) as resp:
            if resp.status != 200:
                return ConnectorResult(success=False, error=f"RxNorm API error: {resp.status}")

            data = await resp.json()
            concepts = data.get('idGroup', {}).get('rxnormConcept', [])

            if not concepts:
                return ConnectorResult(success=False, error="Drug not found")

            return ConnectorResult(
                success=True,
                data={'rxcui': concepts[0].get('rxcui', ''), 'drug_name': drug_name},
                metadata={'source': 'RxNorm'}
            )

    async def _get_properties(self, params: Dict) -> ConnectorResult:
        """Get drug properties by RxCUI."""
        rxcui = params.get('rxcui')
        if not rxcui:
            return ConnectorResult(success=False, error="RxCUI required")

        url = f"{self.base_url}rxcui/{rxcui}/properties.json"
        async with self._session.get(url) as resp:
            if resp.status != 200:
                return ConnectorResult(success=False, error=f"RxNorm API error: {resp.status}")

            data = await resp.json()
            props = data.get('properties', {})

            return ConnectorResult(
                success=True,
                data={
                    'rxcui': props.get('rxcui', ''),
                    'name': props.get('name', ''),
                    'tty': props.get('tty', ''),  # Term type
                    'vocab': props.get('vocab', 'RXNORM'),
                    'suppress': props.get('suppress', 'N'),  # N = Not suppressed
                },
                metadata={'source': 'RxNorm'}
            )

    async def _get_related(self, params: Dict) -> ConnectorResult:
        """Get related drugs (generic/brand equivalents)."""
        rxcui = params.get('rxcui')
        if not rxcui:
            return ConnectorResult(success=False, error="RxCUI required")

        url = f"{self.base_url}rxcui/{rxcui}/related.json"
        async with self._session.get(url, params={'tty': 'GBPC'}) as resp:
            if resp.status != 200:
                return ConnectorResult(success=False, error=f"RxNorm API error: {resp.status}")

            data = await resp.json()
            concepts = data.get('relatedGroup', {}).get('conceptGroup', [])

            related = []
            for group in concepts:
                for concept in group.get('conceptProperties', []):
                    related.append({
                        'rxcui': concept.get('rxcui', ''),
                        'name': concept.get('name', ''),
                        'tty': concept.get('tty', ''),
                        'relationship': concept.get('name', ''),
                    })

            return ConnectorResult(
                success=True,
                data={'rxcui': rxcui, 'related': related},
                metadata={'source': 'RxNorm', 'count': len(related)}
            )

    async def _get_ndc(self, params: Dict) -> ConnectorResult:
        """Get NDC codes for a drug."""
        rxcui = params.get('rxcui')
        if not rxcui:
            return ConnectorResult(success=False, error="RxCUI required")

        url = f"{self.base_url}rxcui/{rxcui}/ndcs.json"
        async with self._session.get(url) as resp:
            if resp.status != 200:
                return ConnectorResult(success=False, error=f"RxNorm API error: {resp.status}")

            data = await resp.json()
            ndc_groups = data.get('idGroup', {}).get('ndcGroup', [])

            ndcs = []
            for group in ndc_groups:
                for ndc in group.get('ndcList', []):
                    ndcs.append(ndc.get('ndc', ''))

            return ConnectorResult(
                success=True,
                data={'rxcui': rxcui, 'ndcs': ndcs},
                metadata={'source': 'RxNorm', 'count': len(ndcs)}
            )

    async def _check_interaction(self, params: Dict) -> ConnectorResult:
        """Check drug-drug interactions for a given RxCUI.

        Uses the RxNav interaction API which returns all known interactions
        for a single drug. To check pairwise interactions, call with each
        RxCUI separately and compare.
        """
        rxcui = params.get('rxcui')
        if not rxcui:
            return ConnectorResult(success=False, error="RxCUI required")

        url = f"{self.base_url}interaction/list.json"
        async with self._session.get(url, params={'rxcui': rxcui}) as resp:
            if resp.status != 200:
                return ConnectorResult(success=False, error=f"RxNorm API error: {resp.status}")

            data = await resp.json()
            interaction_types = data.get('fullInteractionTypeGroup', [])

            results = []
            for group in interaction_types:
                for interaction in group.get('fullInteractionType', []):
                    interacting_drugs = []
                    for drug in interaction.get('minConcept', []):
                        interacting_drugs.append({
                            'rxcui': drug.get('rxcui', ''),
                            'name': drug.get('name', ''),
                            'tty': drug.get('tty', ''),
                        })
                    results.append({
                        'interacting_drugs': interacting_drugs,
                        'description': interaction.get('comment', ''),
                        'severity': interaction.get('severity', 'unknown'),
                        'source': group.get('sourceName', ''),
                    })

            return ConnectorResult(
                success=True,
                data={
                    'rxcui': rxcui,
                    'interactions': results,
                },
                metadata={'source': 'RxNorm', 'count': len(results)}
            )


def register_connector():
    """Register the RxNorm connector."""
    return RxNormConnector, {'base_url': 'https://rxnav.nlm.nih.gov/REST/'}
