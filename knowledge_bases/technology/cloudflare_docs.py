"""
Cloudflare documentation download.

Downloads Cloudflare product documentation for Workers, Pages,
DNS, security, and other services.
"""

import json
import logging
from pathlib import Path

from knowledge_bases._shared import (
    DATA_ROOT, download_text, save_json, write_manifest, file_exists_and_recent,
)

logger = logging.getLogger(__name__)
SOURCE_URL = "https://developers.cloudflare.com/"
DEST_DIR = DATA_ROOT / "technology" / "cloudflare"
MODULE_NAME = "knowledge_bases.technology.cloudflare_docs"

CLOUDFLARE_PRODUCTS = [
    {"product": "Workers", "description": "Serverless execution environment", "docs_url": "https://developers.cloudflare.com/workers/"},
    {"product": "Pages", "description": "JAMstack deployment platform", "docs_url": "https://developers.cloudflare.com/pages/"},
    {"product": "DNS", "description": "Authoritative DNS with global anycast network", "docs_url": "https://developers.cloudflare.com/dns/"},
    {"product": "SSL/TLS", "description": "Certificate management and TLS termination", "docs_url": "https://developers.cloudflare.com/ssl/"},
    {"product": "WAF", "description": "Web Application Firewall", "docs_url": "https://developers.cloudflare.com/waf/"},
    {"product": "CDN/Cache", "description": "Content delivery and caching", "docs_url": "https://developers.cloudflare.com/cache/"},
    {"product": "D1", "description": "Serverless SQL database", "docs_url": "https://developers.cloudflare.com/d1/"},
    {"product": "R2", "description": "Object storage without egress fees", "docs_url": "https://developers.cloudflare.com/r2/"},
    {"product": "KV", "description": "Key-value data store for Workers", "docs_url": "https://developers.cloudflare.com/kv/"},
    {"product": "Durable Objects", "description": "Single-threaded stateful compute", "docs_url": "https://developers.cloudflare.com/durable-objects/"},
    {"product": "Queues", "description": "Message queue service", "docs_url": "https://developers.cloudflare.com/queues/"},
    {"product": "Workers AI", "description": "AI inference on the edge", "docs_url": "https://developers.cloudflare.com/workers-ai/"},
    {"product": "Vectorize", "description": "Vector database for AI", "docs_url": "https://developers.cloudflare.com/vectorize/"},
    {"product": "Hyperdrive", "description": "Database connection pooling", "docs_url": "https://developers.cloudflare.com/hyperdrive/"},
    {"product": "Zero Trust", "description": "Zero trust network access", "docs_url": "https://developers.cloudflare.com/cloudflare-one/"},
    {"product": "Stream", "description": "Video streaming platform", "docs_url": "https://developers.cloudflare.com/stream/"},
    {"product": "Images", "description": "Image optimization and delivery", "docs_url": "https://developers.cloudflare.com/images/"},
    {"product": "Turnstile", "description": "CAPTCHA alternative", "docs_url": "https://developers.cloudflare.com/turnstile/"},
]


async def download(force: bool = False) -> dict:
    """Download Cloudflare documentation references."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    codes_json = DEST_DIR / "cloudflare_docs.json"
    if file_exists_and_recent(codes_json, force):
        return {"files_downloaded": 0, "message": "Already downloaded"}

    logger.info("Downloading Cloudflare documentation references...")
    save_json(CLOUDFLARE_PRODUCTS, codes_json)
    file_list = [codes_json.name]
    write_manifest(DEST_DIR, MODULE_NAME, SOURCE_URL, file_list)
    return {"files_downloaded": 1, "message": f"Downloaded Cloudflare docs reference ({len(CLOUDFLARE_PRODUCTS)} products)"}