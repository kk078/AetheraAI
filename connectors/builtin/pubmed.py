"""
PubMed/NCBI E-utilities Connector for Aethera
Fetches biomedical literature from PubMed.
API: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
Optional API key increases rate limits (3/sec -> 10/sec).
NCBI recommends providing an email address.
"""
import asyncio
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..connector_base import AetheraConnector, ConnectorConfig, ConnectorResult


class PubMedConnector(AetheraConnector):
    """PubMed E-utilities connector for biomedical literature search."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/")
        self.email = config.get("email", "")
        self.api_key = config.get("api_key", "")
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit_lock = asyncio.Lock()
        self._last_request_time: float = 0.0

    def get_config(self) -> ConnectorConfig:
        return ConnectorConfig(
            name="pubmed",
            version="1.0.0",
            description="PubMed - Biomedical literature search via NCBI E-utilities",
            base_url=self.base_url,
            auth_type="api_key" if self.api_key else "none",
            rate_limit=10 if self.api_key else 3,
            timeout=30,
        )

    async def initialize(self) -> bool:
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.get_config().timeout,
            headers={"Accept": "application/json"},
        )
        return True

    async def cleanup(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _base_params(self) -> Dict[str, str]:
        """Return common E-utilities query params."""
        p: Dict[str, str] = {}
        if self.email:
            p["email"] = self.email
        if self.api_key:
            p["api_key"] = self.api_key
        return p

    async def _rate_limited_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        config = self.get_config()
        if config.rate_limit:
            min_interval = 60.0 / config.rate_limit
            async with self._rate_limit_lock:
                now = asyncio.get_event_loop().time()
                elapsed = now - self._last_request_time
                if elapsed < min_interval:
                    await asyncio.sleep(min_interval - elapsed)
                self._last_request_time = asyncio.get_event_loop().time()

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
            reraise=True,
        )
        async def _do_request() -> httpx.Response:
            response = await self._client.request(method, url, **kwargs)
            response.raise_for_status()
            return response

        return await _do_request()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def search(self, query: str = "", **params) -> ConnectorResult:
        """Search PubMed articles.

        Keyword Args:
            limit: Max results (1-100, default 20).
            sort: 'relevance', 'date', or 'author' (default 'relevance').
            mindate: Start date YYYY/MM/DD.
            maxdate: End date YYYY/MM/DD.
        """
        if not query:
            return ConnectorResult(success=False, error="Search query required")

        qp: Dict[str, Any] = {
            **self._base_params(),
            "db": "pubmed",
            "term": query,
            "retmax": min(int(params.get("limit", 20)), 100),
            "retmode": "json",
            "sort": params.get("sort", "relevance"),
        }
        if params.get("mindate"):
            qp["mindate"] = params["mindate"]
        if params.get("maxdate"):
            qp["maxdate"] = params["maxdate"]

        try:
            response = await self._rate_limited_request("GET", "esearch.fcgi", params=qp)
            data = response.json()
            esearch = data.get("esearchresult", {})
            id_list = esearch.get("idlist", [])

            if not id_list:
                return ConnectorResult(
                    success=True,
                    data=[],
                    metadata={"source": "PubMed", "query": query, "total": 0},
                )

            # Fetch article details for the returned IDs
            fetch_result = await self.get(",".join(id_list[:10]))
            articles = fetch_result.data if fetch_result.success else []

            return ConnectorResult(
                success=True,
                data=articles,
                metadata={
                    "source": "PubMed",
                    "query": query,
                    "total": int(esearch.get("count", 0)),
                    "ids": id_list,
                },
            )
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"PubMed API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def get(self, item_id: str, **params) -> ConnectorResult:
        """Fetch article details by PMID (comma-separated for multiple).

        Args:
            item_id: PMID or comma-separated PMIDs (max 10).
        """
        if not item_id:
            return ConnectorResult(success=False, error="PMID required")

        # Limit to 10 articles at a time
        pmids = item_id.split(",")
        pmid_str = ",".join(p.strip() for p in pmids[:10])

        qp: Dict[str, Any] = {
            **self._base_params(),
            "db": "pubmed",
            "id": pmid_str,
            "retmode": "json",
        }

        try:
            response = await self._rate_limited_request("GET", "efetch.fcgi", params=qp)
            data = response.json()
            articles = data.get("PubmedArticle", [])
            return ConnectorResult(
                success=True,
                data=[self._normalize_article(a) for a in articles],
                metadata={"source": "PubMed", "count": len(articles)},
            )
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"PubMed API error: {exc.response.status_code}")
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def related(self, pmid: str) -> ConnectorResult:
        """Find articles related to a given PMID."""
        if not pmid:
            return ConnectorResult(success=False, error="PMID required")

        qp: Dict[str, Any] = {
            **self._base_params(),
            "db": "pubmed",
            "dbfrom": "pubmed",
            "linkname": "pubmed_pubmed",
            "id": pmid,
            "retmode": "json",
        }

        try:
            response = await self._rate_limited_request("GET", "elink.fcgi", params=qp)
            data = response.json()
            linksets = data.get("linksets", [])
            related_ids: List[str] = []
            if linksets and linksets[0].get("linksetdb"):
                for link in linksets[0]["linksetdb"][0].get("link", []):
                    related_ids.append(link.get("id", ""))
            return ConnectorResult(
                success=True,
                data={"pmid": pmid, "related_pmids": related_ids},
                metadata={"source": "PubMed", "count": len(related_ids)},
            )
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def cited_by(self, pmid: str) -> ConnectorResult:
        """Find articles that cite a given PMID."""
        if not pmid:
            return ConnectorResult(success=False, error="PMID required")

        qp: Dict[str, Any] = {
            **self._base_params(),
            "db": "pubmed",
            "dbfrom": "pubmed",
            "linkname": "pubmed_pubmed_citedin",
            "id": pmid,
            "retmode": "json",
        }

        try:
            response = await self._rate_limited_request("GET", "elink.fcgi", params=qp)
            data = response.json()
            linksets = data.get("linksets", [])
            cited_ids: List[str] = []
            if linksets and linksets[0].get("linksetdb"):
                for link in linksets[0]["linksetdb"][0].get("link", []):
                    cited_ids.append(link.get("id", ""))
            return ConnectorResult(
                success=True,
                data={"pmid": pmid, "cited_by_pmids": cited_ids},
                metadata={"source": "PubMed", "count": len(cited_ids)},
            )
        except Exception as exc:
            return ConnectorResult(success=False, error=str(exc))

    async def fetch(self, endpoint: str, params: Optional[Dict] = None) -> ConnectorResult:
        params = params or {}
        if endpoint == "search":
            return await self.search(query=params.pop("query", ""), **params)
        if endpoint == "fetch":
            pmids = params.pop("pmids", params.pop("id", ""))
            if isinstance(pmids, list):
                pmids = ",".join(str(p) for p in pmids)
            return await self.get(pmids, **params)
        if endpoint == "related":
            return await self.related(params.get("pmid", ""))
        if endpoint == "cited_by":
            return await self.cited_by(params.get("pmid", ""))
        return ConnectorResult(success=False, error=f"Unknown endpoint: {endpoint}")

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_article(article: Dict) -> Dict:
        medline = article.get("MedlineCitation", {})
        pubmed_data = article.get("PubmedData", {})
        article_info = medline.get("Article", {})
        journal = article_info.get("Journal", {})

        pmid_val = medline.get("PMID", "")
        if isinstance(pmid_val, dict):
            pmid_val = pmid_val.get("#text", str(pmid_val))

        return {
            "pmid": pmid_val,
            "title": article_info.get("ArticleTitle", ""),
            "abstract": PubMedConnector._get_abstract(medline),
            "authors": PubMedConnector._get_authors(medline),
            "journal": journal.get("Title", ""),
            "pubdate": journal.get("JournalIssue", {}).get("PubDate", {}).get("Year", ""),
            "doi": PubMedConnector._get_doi(pubmed_data),
            "mesh_terms": [
                m.get("DescriptorName", "")
                if isinstance(m.get("DescriptorName"), str)
                else m.get("DescriptorName", {}).get("#text", "")
                for m in medline.get("MeshHeadingList", [])
            ],
        }

    @staticmethod
    def _get_abstract(medline: Dict) -> str:
        abstract = medline.get("Article", {}).get("Abstract", {})
        texts: List[str] = []
        abstract_text = abstract.get("AbstractText", [])
        if isinstance(abstract_text, list):
            for section in abstract_text:
                if isinstance(section, dict):
                    texts.append(section.get("#text", ""))
                elif isinstance(section, str):
                    texts.append(section)
        elif isinstance(abstract_text, str):
            texts.append(abstract_text)
        return " ".join(texts)

    @staticmethod
    def _get_authors(medline: Dict) -> List[str]:
        authors: List[str] = []
        for author in medline.get("Article", {}).get("AuthorList", []):
            parts = []
            if author.get("ForeName"):
                parts.append(author["ForeName"])
            if author.get("LastName"):
                parts.append(author["LastName"])
            if parts:
                authors.append(" ".join(parts))
        return authors[:10]

    @staticmethod
    def _get_doi(pubmed_data: Dict) -> str:
        for aid in pubmed_data.get("ArticleIdList", []):
            if aid.get("IdType") == "doi":
                return aid.get("#text", aid.get("id", ""))
        return ""

    def to_tool_definition(self) -> Dict[str, Any]:
        config = self.get_config()
        return {
            "type": "connector",
            "name": config.name,
            "description": config.description,
            "base_url": config.base_url,
            "auth_type": config.auth_type,
            "endpoints": [
                {
                    "name": "search",
                    "description": "Search PubMed articles",
                    "parameters": [
                        {"name": "query", "type": "string", "description": "Search query"},
                        {"name": "limit", "type": "integer", "description": "Max results (1-100)"},
                        {"name": "sort", "type": "string", "description": "relevance, date, or author"},
                    ],
                },
                {
                    "name": "get",
                    "description": "Fetch article details by PMID",
                    "parameters": [
                        {"name": "pmid", "type": "string", "required": True, "description": "PMID"},
                    ],
                },
                {
                    "name": "related",
                    "description": "Find articles related to a PMID",
                    "parameters": [
                        {"name": "pmid", "type": "string", "required": True, "description": "PMID"},
                    ],
                },
                {
                    "name": "cited_by",
                    "description": "Find articles citing a PMID",
                    "parameters": [
                        {"name": "pmid", "type": "string", "required": True, "description": "PMID"},
                    ],
                },
            ],
        }


def register_connector():
    import os
    return PubMedConnector, {
        "base_url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/",
        "email": os.getenv("NCBI_EMAIL", ""),
        "api_key": os.getenv("NCBI_API_KEY", ""),
    }