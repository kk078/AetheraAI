"""
Aethera AI — Browser Automation Handler
Playwright-based web navigation and data extraction.
"""
from typing import Dict, Any

from ..config import BROWSER_HEADLESS, BROWSER_TIMEOUT

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


class BrowserHandler:
    """Handles browser automation via Playwright."""

    def __init__(self):
        self._playwright = None
        self._browser = None

    async def _ensure_browser(self):
        """Launch browser if not already running."""
        if not HAS_PLAYWRIGHT:
            return None
        if self._browser and self._browser.is_connected():
            return self._browser
        if self._playwright is None:
            self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=BROWSER_HEADLESS)
        return self._browser

    async def handle(self, action: str, parameters: dict) -> Dict[str, Any]:
        dispatch = {
            "browser.navigate": self.navigate,
            "browser.extract": self.extract,
            "browser.screenshot": self.browser_screenshot,
            "browser.fill": self.fill,
            "browser.click": self.click,
            "browser.submit": self.submit_form,
        }
        handler = dispatch.get(action)
        if handler is None:
            return {"success": False, "error": f"Unknown action: {action}"}
        if not HAS_PLAYWRIGHT:
            return {"success": False, "error": "Playwright not installed. Run: playwright install chromium"}
        try:
            return await handler(parameters)
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def navigate(self, params: dict) -> Dict[str, Any]:
        """Navigate to a URL and return page info."""
        url = params.get("url", "")
        wait_for = params.get("wait_for", "load")  # "load", "domcontentloaded", "networkidle"

        if not url:
            return {"success": False, "error": "URL is required"}

        browser = await self._ensure_browser()
        if browser is None:
            return {"success": False, "error": "Could not launch browser"}

        page = await browser.new_page()
        try:
            response = await page.goto(url, wait_until=wait_for, timeout=BROWSER_TIMEOUT * 1000)
            title = await page.title()
            content = await page.content()

            return {
                "success": True,
                "data": {
                    "url": page.url,
                    "title": title,
                    "status": response.status if response else None,
                    "content_length": len(content),
                    "content_preview": content[:5000] if len(content) > 5000 else content,
                },
            }
        finally:
            await page.close()

    async def extract(self, params: dict) -> Dict[str, Any]:
        """Extract data from a web page using CSS selectors."""
        url = params.get("url", "")
        selectors = params.get("selectors", {})
        content_type = params.get("content_type", "text")  # "text", "html", "markdown"

        if not url and not selectors:
            return {"success": False, "error": "Either url or selectors required"}

        browser = await self._ensure_browser()
        if browser is None:
            return {"success": False, "error": "Could not launch browser"}

        page = await browser.new_page()
        try:
            if url:
                await page.goto(url, wait_until="domcontentloaded", timeout=BROWSER_TIMEOUT * 1000)

            title = await page.title()
            extracted = {}

            # Extract by selectors
            for name, selector in selectors.items():
                try:
                    elements = await page.query_selector_all(selector)
                    if content_type == "html":
                        extracted[name] = [await el.inner_html() for el in elements[:10]]
                    else:
                        extracted[name] = [await el.inner_text() for el in elements[:10]]
                except Exception as e:
                    extracted[name] = f"Error: {e}"

            # Full page text
            if content_type == "text":
                full_text = await page.inner_text("body")
            else:
                full_text = await page.content()

            return {
                "success": True,
                "data": {
                    "url": page.url,
                    "title": title,
                    "extracted": extracted,
                    "full_text": full_text[:10000] if len(full_text) > 10000 else full_text,
                },
            }
        finally:
            await page.close()

    async def browser_screenshot(self, params: dict) -> Dict[str, Any]:
        """Take a screenshot of a web page."""
        url = params.get("url", "")
        full_page = params.get("full_page", False)

        if not url:
            return {"success": False, "error": "URL is required"}

        browser = await self._ensure_browser()
        if browser is None:
            return {"success": False, "error": "Could not launch browser"}

        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="load", timeout=BROWSER_TIMEOUT * 1000)
            screenshot_bytes = await page.screenshot(full_page=full_page)

            import base64
            img_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

            return {
                "success": True,
                "data": {
                    "url": page.url,
                    "title": await page.title(),
                    "base64": img_b64,
                    "size_bytes": len(screenshot_bytes),
                    "full_page": full_page,
                },
            }
        finally:
            await page.close()

    async def fill(self, params: dict) -> Dict[str, Any]:
        """Fill a form field on a web page."""
        url = params.get("url", "")
        selector = params.get("selector", "")
        value = params.get("value", "")

        if not all([url, selector, value]):
            return {"success": False, "error": "url, selector, and value are required"}

        browser = await self._ensure_browser()
        if browser is None:
            return {"success": False, "error": "Could not launch browser"}

        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=BROWSER_TIMEOUT * 1000)
            await page.fill(selector, value)
            return {"success": True, "data": {"url": page.url, "selector": selector, "filled": True}}
        finally:
            await page.close()

    async def click(self, params: dict) -> Dict[str, Any]:
        """Click an element on a web page."""
        url = params.get("url", "")
        selector = params.get("selector", "")

        if not all([url, selector]):
            return {"success": False, "error": "url and selector are required"}

        browser = await self._ensure_browser()
        if browser is None:
            return {"success": False, "error": "Could not launch browser"}

        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=BROWSER_TIMEOUT * 1000)
            await page.click(selector)
            return {"success": True, "data": {"url": page.url, "selector": selector, "clicked": True}}
        finally:
            await page.close()

    async def submit_form(self, params: dict) -> Dict[str, Any]:
        """Submit a form on a web page."""
        url = params.get("url", "")
        selector = params.get("selector", "form")

        browser = await self._ensure_browser()
        if browser is None:
            return {"success": False, "error": "Could not launch browser"}

        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=BROWSER_TIMEOUT * 1000)
            await page.submit(selector)
            await page.wait_for_load_state("load", timeout=BROWSER_TIMEOUT * 1000)
            return {
                "success": True,
                "data": {
                    "url": page.url,
                    "title": await page.title(),
                    "submitted": True,
                },
            }
        finally:
            await page.close()