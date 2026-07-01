from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class ScraplingAdapter:
    """Scrapling-backed content extractor used across the SEO pipeline."""

    provider_name = "scrapling"
    enabled = False
    configured = False
    requires_api_key = False
    last_error: str | None = None
    real_data_available = False
    fallback_mode = "not_configured"
    trust_level = "none"

    def __init__(self):
        self._check_scrapling()

    def _check_scrapling(self):
        try:
            import scrapling  # noqa: F401
            self.configured = True
            self.enabled = True
            self.real_data_available = True
            self.fallback_mode = "scrapling"
            self.trust_level = "high"
        except ImportError:
            pass

    # ------------------------------------------------------------------
    # Core fetch
    # ------------------------------------------------------------------

    def _fetch_page(self, url: str, timeout: int = 20) -> Any | None:
        """Return a Scrapling Page object or None on failure."""
        if not self.configured:
            return None
        try:
            from scrapling.fetchers import Fetcher
            fetcher = Fetcher(auto_match=True)
            page = fetcher.get(url, timeout=timeout)
            return page
        except Exception as exc:
            self.last_error = str(exc)
            logger.debug("scrapling fetch failed for %s: %s", url, exc)
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, url: str) -> dict | None:
        """Extract main text content from a URL."""
        page = self._fetch_page(url)
        if page is None:
            return None
        try:
            # Prefer <article> or <main>, fallback to <body>
            containers = page.css("article, main, [role='main']")
            if containers:
                text = containers[0].get_text(separator="\n", strip=True)
            else:
                text = page.get_text(separator="\n", strip=True)

            title = ""
            title_els = page.css("title")
            if title_els:
                title = title_els[0].text

            if not text or len(text) < 50:
                return None

            return {
                "text": text,
                "title": title,
                "url": url,
                "method": "scrapling",
            }
        except Exception as exc:
            self.last_error = str(exc)
            logger.debug("scrapling extract failed for %s: %s", url, exc)
            return None

    def extract_headings(self, url: str) -> list[dict]:
        """Extract all headings (H1–H4) from a page."""
        page = self._fetch_page(url)
        if page is None:
            return []
        headings = []
        try:
            for level in range(1, 5):
                for el in page.css(f"h{level}"):
                    text = el.text.strip() if el.text else ""
                    if text:
                        headings.append({"level": level, "text": text})
        except Exception as exc:
            self.last_error = str(exc)
            logger.debug("scrapling headings failed for %s: %s", url, exc)
        return headings

    def extract_links(self, url: str, base_domain: str | None = None) -> list[dict]:
        """
        Extract all <a> links from a page.
        If base_domain is given, splits into internal/external.
        """
        page = self._fetch_page(url)
        if page is None:
            return []
        links = []
        try:
            for el in page.css("a[href]"):
                href = el.attrib.get("href", "")
                text = (el.text or "").strip()
                if not href or href.startswith("#") or href.startswith("javascript:"):
                    continue
                link_type = "external"
                if base_domain and base_domain in href:
                    link_type = "internal"
                links.append({"url": href, "anchor_text": text, "type": link_type})
        except Exception as exc:
            self.last_error = str(exc)
            logger.debug("scrapling links failed for %s: %s", url, exc)
        return links

    def extract_meta(self, url: str) -> dict:
        """Extract meta title, description, og:*, and canonical from a page."""
        page = self._fetch_page(url)
        if page is None:
            return {}
        meta: dict = {}
        try:
            title_els = page.css("title")
            if title_els:
                meta["title"] = title_els[0].text

            for el in page.css("meta"):
                name = el.attrib.get("name", "") or el.attrib.get("property", "")
                content = el.attrib.get("content", "")
                if name and content:
                    meta[name] = content

            canonical_els = page.css('link[rel="canonical"]')
            if canonical_els:
                meta["canonical"] = canonical_els[0].attrib.get("href", "")
        except Exception as exc:
            self.last_error = str(exc)
            logger.debug("scrapling meta failed for %s: %s", url, exc)
        return meta

    def scrape_competitor(self, url: str) -> dict:
        """
        Full competitor analysis: text, headings, links, meta, word count.
        Returns a dict ready to be stored in research_brief.sources_consulted.
        """
        page = self._fetch_page(url)
        if page is None:
            return {"url": url, "error": self.last_error or "fetch_failed"}
        result: dict = {"url": url}
        try:
            title_els = page.css("title")
            result["title"] = title_els[0].text if title_els else ""

            for el in page.css("meta"):
                name = el.attrib.get("name", "") or el.attrib.get("property", "")
                content = el.attrib.get("content", "")
                if name == "description":
                    result["meta_description"] = content
                elif name == "og:title":
                    result["og_title"] = content

            headings = []
            for level in range(1, 5):
                for el in page.css(f"h{level}"):
                    text = (el.text or "").strip()
                    if text:
                        headings.append({"level": level, "text": text})
            result["headings"] = headings

            containers = page.css("article, main, [role='main']")
            if containers:
                text = containers[0].get_text(separator=" ", strip=True)
            else:
                text = page.get_text(separator=" ", strip=True)
            result["text_preview"] = text[:500]
            result["word_count"] = len(re.findall(r"\w+", text))

            links = []
            for el in page.css("a[href]"):
                href = el.attrib.get("href", "")
                anchor = (el.text or "").strip()
                if href and not href.startswith(("#", "javascript:")):
                    links.append({"url": href, "anchor_text": anchor})
            result["external_links_discovered"] = [
                lk for lk in links if not href.startswith("/")
            ][:20]

        except Exception as exc:
            self.last_error = str(exc)
            result["error"] = str(exc)
            logger.debug("scrapling competitor failed for %s: %s", url, exc)
        return result

    def validate_url(self, url: str) -> dict:
        """Check if URL is reachable and return basic quality signals."""
        page = self._fetch_page(url)
        if page is None:
            return {"url": url, "reachable": False, "error": self.last_error}
        try:
            title_els = page.css("title")
            title = title_els[0].text if title_els else ""
            text = page.get_text(separator=" ", strip=True)
            word_count = len(re.findall(r"\w+", text))
            return {
                "url": url,
                "reachable": True,
                "title": title,
                "word_count": word_count,
                "quality": "high" if word_count > 300 else "low",
            }
        except Exception as exc:
            self.last_error = str(exc)
            return {"url": url, "reachable": False, "error": str(exc)}

    def get_status(self) -> dict:
        return {
            "provider_name": self.provider_name,
            "enabled": self.enabled,
            "configured": self.configured,
            "requires_api_key": self.requires_api_key,
            "last_error": self.last_error,
            "real_data_available": self.real_data_available,
            "fallback_mode": self.fallback_mode,
            "trust_level": self.trust_level,
        }


scrapling_adapter = ScraplingAdapter()
