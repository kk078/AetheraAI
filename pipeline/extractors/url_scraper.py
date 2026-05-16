"""
Aethera AI — URL Scraper
Fetches web pages and extracts main content using httpx + BeautifulSoup.
"""
import logging
from typing import Dict, Any, Optional

import httpx

logger = logging.getLogger("aethera.pipeline.url_scraper")

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


async def scrape_url(url: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Fetch a URL and extract its main text content.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Dict with text, title, metadata
    """
    result = {
        "text": "",
        "title": "",
        "metadata": {},
        "url": url,
        "success": False,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, headers={
                "User-Agent": "AetheraAI/1.0 (Knowledge Crawler)"
            })
            response.raise_for_status()
            html = response.text

        if not HAS_BS4:
            # Fallback: strip tags with regex
            import re
            text = re.sub(r"<[^>]+>", " ", html)
            text = re.sub(r"\s+", " ", text).strip()
            result["text"] = text[:100000]
            result["success"] = True
            return result

        soup = BeautifulSoup(html, "html.parser")

        # Title
        title_tag = soup.find("title")
        result["title"] = title_tag.get_text(strip=True) if title_tag else ""

        # Remove script, style, nav, footer, header elements
        for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        # Try to find main content area
        main = soup.find("main") or soup.find("article") or soup.find("div", class_="content")
        if main:
            text = main.get_text(separator="\n", strip=True)
        else:
            body = soup.find("body")
            text = body.get_text(separator="\n", strip=True) if body else soup.get_text(strip=True)

        result["text"] = text[:100000]

        # Extract metadata
        meta_tags = soup.find_all("meta")
        for tag in meta_tags:
            name = tag.get("name") or tag.get("property", "")
            content = tag.get("content", "")
            if name and content:
                result["metadata"][name] = content[:500]

        result["success"] = True

    except Exception as e:
        logger.error(f"URL scrape failed for {url}: {e}")
        result["error"] = str(e)

    return result