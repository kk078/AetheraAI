"""
Aethera AI - News Aggregator

RSS/Atom feed monitoring and summarization.
Reads feeds.yaml for feed URLs.
Fetches, deduplicates, categorizes, and summarizes articles.

Categories:
- healthcare_regulatory
- healthcare_payment
- technology
- security

Supports: fetch feeds, get digest, mark read, search articles.
"""

import hashlib
import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree

import httpx

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.environ.get("NEWS_AGGREGATOR_DB_PATH", "/data/proactive_news.db")
DEFAULT_FEEDS_PATH = os.path.join(os.path.dirname(__file__), "feeds.yaml")

# RSS/Atom namespace map
NS = {
    "rss": "http://purl.org/rss/1.0/",
    "atom": "http://www.w3.org/2005/Atom",
    "dc": "http://purl.org/dc/elements/1.1/",
    "content": "http://purl.org/rss/1.0/modules/content/",
}

# Category keyword mapping for auto-classification
CATEGORY_KEYWORDS = {
    "healthcare_regulatory": [
        "cms", "medicare", "medicaid", "fda", "regulation", "compliance",
        "hipaa", "oig", "hhs", "transmittal", "rulemaking", "federal register",
        "credentialing", "accreditation", "joint commission",
    ],
    "healthcare_payment": [
        "reimbursement", "billing", "coding", "claim", "denial", "appeal",
        "payer", "revenue cycle", "cpt", "icd", "drm", "fee schedule",
        "prior authorization", "payment model", "value-based",
    ],
    "technology": [
        "ai", "machine learning", "cloud", "api", "software", "kubernetes",
        "docker", "serverless", "devops", "infrastructure", "openai",
        "llm", "vector", "embedding", "rag", "automation",
    ],
    "security": [
        "cve", "vulnerability", "cybersecurity", "ransomware", "breach",
        "phishing", "zero-day", "patch", "exploit", "cisa", "nvd",
        "firewall", "encryption", "incident",
    ],
}


class Article:
    """Represents a fetched news article."""

    __slots__ = (
        "id", "feed_url", "feed_name", "title", "link", "summary",
        "content", "author", "category", "published_at", "fetched_at",
        "is_read", "read_at", "fingerprint", "metadata",
    )

    def __init__(
        self,
        id: str,
        feed_url: str,
        feed_name: str,
        title: str,
        link: str = "",
        summary: str = "",
        content: str = "",
        author: str = "",
        category: str = "uncategorized",
        published_at: Optional[str] = None,
        fetched_at: Optional[str] = None,
        is_read: bool = False,
        read_at: Optional[str] = None,
        fingerprint: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.id = id
        self.feed_url = feed_url
        self.feed_name = feed_name
        self.title = title
        self.link = link
        self.summary = summary
        self.content = content
        self.author = author
        self.category = category
        self.published_at = published_at
        self.fetched_at = fetched_at or datetime.now(timezone.utc).isoformat()
        self.is_read = is_read
        self.read_at = read_at
        self.fingerprint = fingerprint
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "feed_url": self.feed_url,
            "feed_name": self.feed_name,
            "title": self.title,
            "link": self.link,
            "summary": self.summary,
            "content": self.content,
            "author": self.author,
            "category": self.category,
            "published_at": self.published_at,
            "fetched_at": self.fetched_at,
            "is_read": self.is_read,
            "read_at": self.read_at,
            "fingerprint": self.fingerprint,
            "metadata": self.metadata,
        }


class NewsAggregator:
    """
    RSS/Atom feed monitor with deduplication, categorization, and summarization.
    Feed URLs are loaded from feeds.yaml.
    """

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        feeds_path: str = DEFAULT_FEEDS_PATH,
        http_timeout: int = 30,
        user_agent: str = "AetheraAI-NewsAggregator/1.0",
        max_articles_per_feed: int = 50,
        dedup_window_days: int = 30,
    ):
        self._db_path = db_path
        self._feeds_path = feeds_path
        self._http_timeout = http_timeout
        self._user_agent = user_agent
        self._max_articles_per_feed = max_articles_per_feed
        self._dedup_window_days = dedup_window_days
        self._conn: Optional[sqlite3.Connection] = None
        self._feeds_config: Optional[Dict[str, Any]] = None
        self._initialize_db()
        self._load_feeds_config()

    def _initialize_db(self) -> None:
        """Create the articles table."""
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS articles (
                id TEXT PRIMARY KEY,
                feed_url TEXT NOT NULL,
                feed_name TEXT NOT NULL,
                title TEXT NOT NULL,
                link TEXT DEFAULT '',
                summary TEXT DEFAULT '',
                content TEXT DEFAULT '',
                author TEXT DEFAULT '',
                category TEXT NOT NULL DEFAULT 'uncategorized',
                published_at TEXT,
                fetched_at TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                read_at TEXT,
                fingerprint TEXT NOT NULL DEFAULT '',
                metadata JSON DEFAULT '{}'
            );

            CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);
            CREATE INDEX IF NOT EXISTS idx_articles_fetched ON articles(fetched_at);
            CREATE INDEX IF NOT EXISTS idx_articles_feed ON articles(feed_url);
            CREATE INDEX IF NOT EXISTS idx_articles_read ON articles(is_read);
            CREATE INDEX IF NOT EXISTS idx_articles_fingerprint ON articles(fingerprint);
        """)
        self._conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    # ---------------------------------------------------------------------------
    # Feed Configuration
    # ---------------------------------------------------------------------------

    def _load_feeds_config(self) -> None:
        """Load feed configuration from feeds.yaml."""
        try:
            import yaml
            with open(self._feeds_path, "r", encoding="utf-8") as f:
                self._feeds_config = yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning("feeds.yaml not found at %s", self._feeds_path)
            self._feeds_config = {"feeds": {}}
        except Exception as exc:
            logger.error("Failed to load feeds.yaml: %s", exc)
            self._feeds_config = {"feeds": {}}

    def reload_feeds(self) -> Dict[str, Any]:
        """Reload the feeds configuration from disk."""
        self._load_feeds_config()
        return self.get_feeds()

    def get_feeds(self) -> Dict[str, Any]:
        """Return the current feed configuration."""
        if not self._feeds_config:
            return {"feeds": {}}
        return dict(self._feeds_config)

    # ---------------------------------------------------------------------------
    # Fetch Feeds
    # ---------------------------------------------------------------------------

    def fetch_feeds(
        self,
        categories: Optional[List[str]] = None,
        feed_urls: Optional[List[str]] = None,
    ) -> Dict[str, List[Article]]:
        """
        Fetch articles from all configured feeds.

        Args:
            categories: Only fetch feeds in these categories.
            feed_urls: Only fetch these specific feed URLs.

        Returns:
            Dict mapping feed URL to list of new Article objects.
        """
        results: Dict[str, List[Article]] = {}
        feeds_by_url = self._get_feeds_to_fetch(categories, feed_urls)

        for feed_url, feed_info in feeds_by_url.items():
            try:
                new_articles = self._fetch_single_feed(feed_url, feed_info)
                if new_articles:
                    results[feed_url] = new_articles
                    logger.info("Feed %s: %d new articles", feed_info.get("name", feed_url), len(new_articles))
            except Exception as exc:
                logger.error("Feed %s fetch failed: %s", feed_url, exc)

        return results

    def _get_feeds_to_fetch(
        self,
        categories: Optional[List[str]] = None,
        feed_urls: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Determine which feeds to fetch based on filters."""
        if not self._feeds_config:
            return {}

        feeds: Dict[str, Dict[str, Any]] = {}
        feeds_data = self._feeds_config.get("feeds", {})

        for category, category_feeds in feeds_data.items():
            if categories and category not in categories:
                continue

            if isinstance(category_feeds, list):
                for feed in category_feeds:
                    url = feed.get("url", "") if isinstance(feed, dict) else str(feed)
                    if not url:
                        continue
                    if feed_urls and url not in feed_urls:
                        continue
                    feeds[url] = {
                        "category": category,
                        "name": feed.get("name", url) if isinstance(feed, dict) else url,
                    }
            elif isinstance(category_feeds, dict):
                for name, url in category_feeds.items():
                    if not url:
                        continue
                    if feed_urls and url not in feed_urls:
                        continue
                    feeds[url] = {"category": category, "name": name}

        return feeds

    def _fetch_single_feed(self, feed_url: str, feed_info: Dict[str, Any]) -> List[Article]:
        """Fetch and parse a single RSS/Atom feed."""
        feed_name = feed_info.get("name", feed_url)
        default_category = feed_info.get("category", "uncategorized")

        try:
            with httpx.Client(
                timeout=self._http_timeout,
                headers={"User-Agent": self._user_agent},
                follow_redirects=True,
            ) as client:
                resp = client.get(feed_url)
                resp.raise_for_status()
                content = resp.text
        except Exception as exc:
            logger.error("HTTP fetch for %s failed: %s", feed_url, exc)
            return []

        # Parse the feed
        entries = self._parse_feed(content, feed_url, feed_name, default_category)

        # Deduplicate and store
        new_articles: List[Article] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        for article in entries:
            # Compute fingerprint for dedup
            fp = self._compute_fingerprint(article.title, article.link)
            article.fingerprint = fp

            # Check for existing article with same fingerprint
            existing = self._conn.execute(
                "SELECT id FROM articles WHERE fingerprint = ?",
                (fp,),
            ).fetchone()

            if existing:
                continue

            article.fetched_at = now_iso
            article.id = f"art_{uuid.uuid4().hex[:12]}"

            self._conn.execute(
                """INSERT INTO articles
                   (id, feed_url, feed_name, title, link, summary, content,
                    author, category, published_at, fetched_at, is_read,
                    fingerprint, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)""",
                (
                    article.id, article.feed_url, article.feed_name,
                    article.title, article.link, article.summary,
                    article.content, article.author, article.category,
                    article.published_at, article.fetched_at,
                    article.fingerprint, json.dumps(article.metadata),
                ),
            )
            new_articles.append(article)

        if new_articles:
            self._conn.commit()

        return new_articles[:self._max_articles_per_feed]

    def _parse_feed(
        self,
        content: str,
        feed_url: str,
        feed_name: str,
        default_category: str,
    ) -> List[Article]:
        """Parse RSS or Atom feed content into Article objects."""
        articles: List[Article] = []

        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError:
            logger.warning("Failed to parse XML from %s", feed_url)
            return []

        # Detect feed format
        if root.tag.endswith("feed"):  # Atom
            articles = self._parse_atom(root, feed_url, feed_name, default_category)
        elif root.tag.endswith("RSS") or root.tag.endswith("rss") or "channel" in root.tag.lower():
            articles = self._parse_rss(root, feed_url, feed_name, default_category)
        elif root.tag == "rss" or root.tag.endswith(":rss"):
            # Handle namespaced RSS
            channel = root.find("channel")
            if channel is not None:
                articles = self._parse_rss_channel(channel, feed_url, feed_name, default_category)
        else:
            # Try RSS channel approach
            channel = root.find("channel")
            if channel is not None:
                articles = self._parse_rss_channel(channel, feed_url, feed_name, default_category)
            else:
                # Try Atom with namespace
                ns_entries = root.findall(".//atom:entry", NS) or root.findall(".//{http://www.w3.org/2005/Atom}entry")
                for entry in ns_entries:
                    article = self._parse_atom_entry(entry, feed_url, feed_name, default_category)
                    if article:
                        articles.append(article)

        return articles

    def _parse_atom(
        self,
        root: ElementTree.Element,
        feed_url: str,
        feed_name: str,
        default_category: str,
    ) -> List[Article]:
        """Parse an Atom feed."""
        articles = []
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        # Try with and without namespace
        entries = root.findall("atom:entry", ns)
        if not entries:
            entries = root.findall("{http://www.w3.org/2005/Atom}entry")
        if not entries:
            entries = root.findall("entry")

        for entry in entries:
            article = self._parse_atom_entry(entry, feed_url, feed_name, default_category)
            if article:
                articles.append(article)

        return articles

    def _parse_atom_entry(
        self,
        entry: ElementTree.Element,
        feed_url: str,
        feed_name: str,
        default_category: str,
    ) -> Optional[Article]:
        """Parse a single Atom entry."""
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        def _text(el, tag):
            node = el.find(f"atom:{tag}", ns) or el.find(tag) or el.find(f"{{{ns['atom']}}}{tag}")
            return node.text.strip() if node is not None and node.text else ""

        title = _text(entry, "title")
        if not title:
            return None

        link_el = entry.find("atom:link", ns) or entry.find("link")
        link = ""
        if link_el is not None:
            link = link_el.get("href", link_el.text or "")

        summary = _text(entry, "summary")
        content = _text(entry, "content")
        author = _text(entry, "author")
        if not author:
            author_name = entry.find("atom:author/atom:name", ns)
            author = author_name.text if author_name is not None and author_name.text else ""

        published = _text(entry, "published") or _text(entry, "updated")

        # Auto-classify
        combined_text = f"{title} {summary} {content}".lower()
        category = self._classify_article(combined_text, default_category)

        return Article(
            id="",
            feed_url=feed_url,
            feed_name=feed_name,
            title=title,
            link=link,
            summary=summary[:1000],
            content=content[:2000],
            author=author,
            category=category,
            published_at=published,
        )

    def _parse_rss(
        self,
        root: ElementTree.Element,
        feed_url: str,
        feed_name: str,
        default_category: str,
    ) -> List[Article]:
        """Parse an RSS 2.0 feed."""
        channel = root.find("channel")
        if channel is None:
            return []
        return self._parse_rss_channel(channel, feed_url, feed_name, default_category)

    def _parse_rss_channel(
        self,
        channel: ElementTree.Element,
        feed_url: str,
        feed_name: str,
        default_category: str,
    ) -> List[Article]:
        """Parse items from an RSS channel."""
        articles = []

        items = channel.findall("item")
        for item in items:
            title_el = item.find("title")
            title = title_el.text.strip() if title_el is not None and title_el.text else ""
            if not title:
                continue

            link_el = item.find("link")
            link = link_el.text.strip() if link_el is not None and link_el.text else ""

            desc_el = item.find("description")
            summary = desc_el.text.strip() if desc_el is not None and desc_el.text else ""

            # Try content:encoded
            content_el = item.find("content:encoded", NS)
            if content_el is None:
                content_el = item.find("{http://purl.org/rss/1.0/modules/content/}encoded")
            content = content_el.text.strip() if content_el is not None and content_el.text else summary

            author_el = item.find("dc:creator", NS)
            if author_el is None:
                author_el = item.find("{http://purl.org/dc/elements/1.1/}creator")
            if author_el is None:
                author_el = item.find("author")
            author = author_el.text.strip() if author_el is not None and author_el.text else ""

            pub_el = item.find("pubDate")
            published = pub_el.text.strip() if pub_el is not None and pub_el.text else ""
            if not published:
                dc_date = item.find("dc:date", NS)
                if dc_date is not None and dc_date.text:
                    published = dc_date.text.strip()

            # Auto-classify
            combined_text = f"{title} {summary} {content}".lower()
            category = self._classify_article(combined_text, default_category)

            articles.append(Article(
                id="",
                feed_url=feed_url,
                feed_name=feed_name,
                title=title,
                link=link,
                summary=summary[:1000],
                content=content[:2000],
                author=author,
                category=category,
                published_at=published,
            ))

        return articles

    # ---------------------------------------------------------------------------
    # Classification
    # ---------------------------------------------------------------------------

    def _classify_article(self, text: str, default: str) -> str:
        """
        Auto-classify an article based on keyword matching.

        Returns the category with the most keyword matches, or the default.
        """
        text_lower = text.lower()
        scores: Dict[str, int] = {}

        for category, keywords in CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[category] = score

        if not scores:
            return default

        return max(scores, key=scores.get)

    # ---------------------------------------------------------------------------
    # Deduplication
    # ---------------------------------------------------------------------------

    @staticmethod
    def _compute_fingerprint(title: str, link: str) -> str:
        """Compute a dedup fingerprint from title + link."""
        normalized = f"{title.strip().lower()}|{link.strip().lower()}"
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]

    # ---------------------------------------------------------------------------
    # Get Digest
    # ---------------------------------------------------------------------------

    def get_digest(
        self,
        category: Optional[str] = None,
        unread_only: bool = True,
        limit: int = 20,
        since: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get a digest of recent articles.

        Args:
            category: Filter by category.
            unread_only: Only include unread articles.
            limit: Maximum articles to return.
            since: ISO 8601 datetime; only articles fetched after this time.

        Returns:
            List of article dicts ordered by fetch time (newest first).
        """
        query = "SELECT * FROM articles WHERE 1=1"
        params: List[Any] = []

        if category:
            query += " AND category = ?"
            params.append(category)
        if unread_only:
            query += " AND is_read = 0"
        if since:
            query += " AND fetched_at >= ?"
            params.append(since)

        query += " ORDER BY fetched_at DESC LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(query, params).fetchall()
        return [dict(self._row_to_article(r).to_dict()) for r in rows]

    # ---------------------------------------------------------------------------
    # Mark Read
    # ---------------------------------------------------------------------------

    def mark_read(self, article_ids: List[str]) -> int:
        """
        Mark articles as read.

        Args:
            article_ids: List of article IDs to mark.

        Returns:
            Number of articles actually updated.
        """
        if not article_ids:
            return 0

        now_iso = datetime.now(timezone.utc).isoformat()
        placeholders = ", ".join("?" for _ in article_ids)
        cursor = self._conn.execute(
            f"UPDATE articles SET is_read = 1, read_at = ? WHERE id IN ({placeholders})",
            [now_iso] + article_ids,
        )
        self._conn.commit()
        return cursor.rowcount

    def mark_all_read(self, category: Optional[str] = None) -> int:
        """Mark all (or all in a category) articles as read."""
        now_iso = datetime.now(timezone.utc).isoformat()
        if category:
            cursor = self._conn.execute(
                "UPDATE articles SET is_read = 1, read_at = ? WHERE category = ? AND is_read = 0",
                (now_iso, category),
            )
        else:
            cursor = self._conn.execute(
                "UPDATE articles SET is_read = 1, read_at = ? WHERE is_read = 0",
                (now_iso,),
            )
        self._conn.commit()
        return cursor.rowcount

    # ---------------------------------------------------------------------------
    # Search
    # ---------------------------------------------------------------------------

    def search_articles(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Search articles by title and summary text.

        Uses SQLite LIKE for simple matching.
        """
        sql = "SELECT * FROM articles WHERE (title LIKE ? OR summary LIKE ?)"
        params: List[Any] = [f"%{query}%", f"%{query}%"]

        if category:
            sql += " AND category = ?"
            params.append(category)

        sql += " ORDER BY fetched_at DESC LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(sql, params).fetchall()
        return [dict(self._row_to_article(r).to_dict()) for r in rows]

    # ---------------------------------------------------------------------------
    # Stats
    # ---------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get news aggregator statistics."""
        total = self._conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        unread = self._conn.execute("SELECT COUNT(*) FROM articles WHERE is_read = 0").fetchone()[0]

        by_category = {}
        for cat in ["healthcare_regulatory", "healthcare_payment", "technology", "security", "uncategorized"]:
            count = self._conn.execute(
                "SELECT COUNT(*) FROM articles WHERE category = ? AND is_read = 0",
                (cat,),
            ).fetchone()[0]
            if count > 0:
                by_category[cat] = count

        by_feed = {}
        rows = self._conn.execute(
            "SELECT feed_name, COUNT(*) as cnt FROM articles WHERE is_read = 0 GROUP BY feed_name ORDER BY cnt DESC LIMIT 15"
        ).fetchall()
        for row in rows:
            by_feed[row["feed_name"]] = row["cnt"]

        return {
            "total": total,
            "unread": unread,
            "by_category": by_category,
            "by_feed": by_feed,
        }

    # ---------------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------------

    @staticmethod
    def _row_to_article(row: sqlite3.Row) -> Article:
        """Convert a database row to an Article."""
        d = dict(row)
        metadata_raw = d.get("metadata", "{}")
        if isinstance(metadata_raw, str):
            try:
                metadata = json.loads(metadata_raw)
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        else:
            metadata = metadata_raw or {}

        return Article(
            id=d["id"],
            feed_url=d["feed_url"],
            feed_name=d["feed_name"],
            title=d["title"],
            link=d.get("link", ""),
            summary=d.get("summary", ""),
            content=d.get("content", ""),
            author=d.get("author", ""),
            category=d.get("category", "uncategorized"),
            published_at=d.get("published_at"),
            fetched_at=d["fetched_at"],
            is_read=bool(d.get("is_read", 0)),
            read_at=d.get("read_at"),
            fingerprint=d.get("fingerprint", ""),
            metadata=metadata,
        )


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_aggregator: Optional[NewsAggregator] = None


def get_news_aggregator(**kwargs) -> NewsAggregator:
    """Get or create the singleton NewsAggregator instance."""
    global _aggregator
    if _aggregator is None:
        _aggregator = NewsAggregator(**kwargs)
    return _aggregator