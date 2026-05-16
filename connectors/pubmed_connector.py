"""
PubMed Connector for Aethera
Fetches biomedical literature from PubMed via E-utilities.
https://www.ncbi.nlm.nih.gov/books/NBK25501/
"""
import aiohttp
from typing import Any, Dict, Optional
from .connector_base import AetheraConnector, ConnectorConfig, ConnectorResult


class PubMedConnector(AetheraConnector):
    """PubMed E-utilities connector for biomedical literature search."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/')
        self.email = config.get('email', '')  # Required by NCBI
        self.api_key = config.get('api_key', '')  # Optional, increases rate limits

    def get_config(self) -> ConnectorConfig:
        return ConnectorConfig(
            name='pubmed',
            version='1.0.0',
            description='PubMed - Biomedical literature search via NCBI E-utilities',
            base_url=self.base_url,
            auth_type='api_key',
            rate_limit=10 if self.api_key else 3,  # 3/sec without key, 10/sec with key
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
        """Fetch from PubMed."""
        try:
            if endpoint == 'search':
                return await self._search(params)
            elif endpoint == 'fetch':
                return await self._fetch_articles(params)
            elif endpoint == 'related':
                return await self._find_related(params)
            elif endpoint == 'cited_by':
                return await self._find_cited_by(params)
            else:
                return ConnectorResult(success=False, error=f"Unknown endpoint: {endpoint}")
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    async def _search(self, params: Dict) -> ConnectorResult:
        """Search PubMed articles."""
        query = params.get('query', '')
        if not query:
            return ConnectorResult(success=False, error="Search query required")

        # Build E-utilities URL
        url = f"{self.base_url}esearch.fcgi"
        query_params = {
            'db': 'pubmed',
            'term': query,
            'retmax': min(params.get('limit', 20), 100),
            'retmode': 'json',
            'sort': params.get('sort', 'relevance'),  # relevance, date, author
        }

        if self.email:
            query_params['email'] = self.email
        if self.api_key:
            query_params['api_key'] = self.api_key
        if params.get('mindate'):
            query_params['mindate'] = params['mindate']
        if params.get('maxdate'):
            query_params['maxdate'] = params['maxdate']

        async with self._session.get(url, params=query_params) as resp:
            if resp.status != 200:
                return ConnectorResult(success=False, error=f"PubMed API error: {resp.status}")

            data = await resp.json()
            esearch = data.get('esearchresult', {})

            return ConnectorResult(
                success=True,
                data={
                    'ids': esearch.get('idlist', []),
                    'count': int(esearch.get('count', 0)),
                    'retmax': int(esearch.get('retmax', 0)),
                },
                metadata={'source': 'PubMed', 'query': query}
            )

    async def _fetch_articles(self, params: Dict) -> ConnectorResult:
        """Fetch article details by PMID."""
        pmids = params.get('pmids', [])
        if not pmids:
            return ConnectorResult(success=False, error="PMID list required")

        # Convert to comma-separated string
        if isinstance(pmids, list):
            pmid_str = ','.join(str(p) for p in pmids[:10])  # Max 10 at a time
        else:
            pmid_str = str(pmids)[:200]  # Limit length

        url = f"{self.base_url}efetch.fcgi"
        query_params = {
            'db': 'pubmed',
            'id': pmid_str,
            'retmode': 'json',
        }

        if self.email:
            query_params['email'] = self.email
        if self.api_key:
            query_params['api_key'] = self.api_key

        async with self._session.get(url, params=query_params) as resp:
            if resp.status != 200:
                return ConnectorResult(success=False, error=f"PubMed API error: {resp.status}")

            data = await resp.json()
            articles = data.get('PubmedArticle', [])

            return ConnectorResult(
                success=True,
                data=[self._normalize_article(a) for a in articles],
                metadata={'source': 'PubMed', 'count': len(articles)}
            )

    async def _find_related(self, params: Dict) -> ConnectorResult:
        """Find articles related to a PMID."""
        pmid = params.get('pmid')
        if not pmid:
            return ConnectorResult(success=False, error="PMID required")

        url = f"{self.base_url}elink.fcgi"
        query_params = {
            'db': 'pubmed',
            'dbfrom': 'pubmed',
            'linkname': 'pubmed_pubmed',
            'id': pmid,
            'retmode': 'json',
        }

        if self.email:
            query_params['email'] = self.email
        if self.api_key:
            query_params['api_key'] = self.api_key

        async with self._session.get(url, params=query_params) as resp:
            if resp.status != 200:
                return ConnectorResult(success=False, error=f"PubMed API error: {resp.status}")

            data = await resp.json()
            linksets = data.get('linksets', [])

            related_ids = []
            if linksets and linksets[0].get('linksetdb'):
                for link in linksets[0]['linksetdb'][0].get('link', []):
                    related_ids.append(link.get('id'))

            return ConnectorResult(
                success=True,
                data={'pmid': pmid, 'related_pmids': related_ids},
                metadata={'source': 'PubMed', 'count': len(related_ids)}
            )

    async def _find_cited_by(self, params: Dict) -> ConnectorResult:
        """Find articles that cite a given PMID."""
        pmid = params.get('pmid')
        if not pmid:
            return ConnectorResult(success=False, error="PMID required")

        # Use cited_by linkname
        url = f"{self.base_url}elink.fcgi"
        query_params = {
            'db': 'pubmed',
            'dbfrom': 'pubmed',
            'linkname': 'pubmed_pubmed_citedin',
            'id': pmid,
            'retmode': 'json',
        }

        if self.email:
            query_params['email'] = self.email
        if self.api_key:
            query_params['api_key'] = self.api_key

        async with self._session.get(url, params=query_params) as resp:
            if resp.status != 200:
                return ConnectorResult(success=False, error=f"PubMed API error: {resp.status}")

            data = await resp.json()
            linksets = data.get('linksets', [])

            cited_by_ids = []
            if linksets and linksets[0].get('linksetdb'):
                for link in linksets[0]['linksetdb'][0].get('link', []):
                    cited_by_ids.append(link.get('id'))

            return ConnectorResult(
                success=True,
                data={'pmid': pmid, 'cited_by_pmids': cited_by_ids},
                metadata={'source': 'PubMed', 'count': len(cited_by_ids)}
            )

    def _normalize_article(self, article: Dict) -> Dict:
        """Normalize PubMed article data."""
        medline = article.get('MedlineCitation', {})
        pubmed = article.get('PubmedData', {})

        pmid_data = medline.get('PMID', '')
        if isinstance(pmid_data, dict):
            pmid = pmid_data.get('#text', str(pmid_data))
        else:
            pmid = str(pmid_data)

        doi_data = ''
        eloc_ids = medline.get('Article', {}).get('ELocationID', [])
        if eloc_ids:
            first = eloc_ids[0] if isinstance(eloc_ids, list) else eloc_ids
            if isinstance(first, dict):
                doi_data = first.get('#text', '')

        mesh_terms = []
        for m in medline.get('MeshHeadingList', []):
            desc = m.get('DescriptorName', '')
            if isinstance(desc, dict):
                mesh_terms.append(desc.get('#text', ''))
            elif desc:
                mesh_terms.append(str(desc))

        return {
            'pmid': pmid,
            'title': medline.get('Article', {}).get('ArticleTitle', ''),
            'abstract': self._get_abstract(medline),
            'authors': self._get_authors(medline),
            'journal': medline.get('Article', {}).get('Journal', {}).get('Title', ''),
            'pubdate': medline.get('Article', {}).get('Journal', {}).get('JournalIssue', {}).get('PubDate', {}).get('Year', ''),
            'doi': doi_data,
            'mesh_terms': mesh_terms,
        }

    def _get_abstract(self, medline: Dict) -> str:
        """Extract abstract text."""
        article = medline.get('Article', {})
        abstract = article.get('Abstract', {})
        texts = []

        if isinstance(abstract.get('AbstractText'), list):
            for section in abstract['AbstractText']:
                texts.append(section.get('#text', ''))
        elif isinstance(abstract.get('AbstractText'), str):
            texts.append(abstract['AbstractText'])

        return ' '.join(texts)

    def _get_authors(self, medline: Dict) -> list:
        """Extract author list."""
        article = medline.get('Article', {})
        authors = []

        for author in article.get('AuthorList', []):
            name = []
            if author.get('ForeName'):
                name.append(author['ForeName'])
            if author.get('LastName'):
                name.append(author['LastName'])
            if name:
                authors.append(' '.join(name))

        return authors[:10]  # Limit to 10 authors


def register_connector():
    """Register the PubMed connector."""
    import os
    return PubMedConnector, {
        'base_url': 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/',
        'email': os.getenv('NCBI_EMAIL', ''),
        'api_key': os.getenv('NCBI_API_KEY', ''),
    }
