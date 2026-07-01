from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Dossier partagé pour le stockage adaptatif Scrapling (par projet)
ADAPTIVE_STORAGE_DIR = Path(__file__).resolve().parents[4] / "data" / "scrapling"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _fetch_adaptor(url: str, timeout: int = 20) -> Any | None:
    """
    Fetch a URL with httpx and wrap the response in a Scrapling Adaptor.
    Does NOT need curl_cffi or playwright — httpx + Adaptor is enough.
    """
    try:
        import httpx
        from scrapling.parser import Adaptor

        resp = httpx.get(url, timeout=timeout, follow_redirects=True, headers=_HEADERS)
        resp.raise_for_status()
        return Adaptor(resp.text, url=url)
    except Exception as exc:
        logger.debug("_fetch_adaptor failed for %s: %s", url, exc)
        return None


class ScraplingAdapter:
    """Scrapling-backed content extractor — httpx fetching + Adaptor parsing."""

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
        if self.configured:
            ADAPTIVE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    def _check_scrapling(self):
        try:
            from scrapling.parser import Adaptor  # noqa: F401
            import httpx  # noqa: F401
            self.configured = True
            self.enabled = True
            self.real_data_available = True
            self.fallback_mode = "scrapling+httpx"
            self.trust_level = "high"
        except ImportError:
            pass

    # ------------------------------------------------------------------
    # Core fetch
    # ------------------------------------------------------------------

    def _fetch_page(self, url: str, timeout: int = 20) -> Any | None:
        """Return a Scrapling Adaptor or None on failure."""
        if not self.configured:
            return None
        page = _fetch_adaptor(url, timeout=timeout)
        if page is None:
            self.last_error = f"fetch_failed:{url}"
        return page

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, url: str) -> dict | None:
        page = self._fetch_page(url)
        if page is None:
            return None
        try:
            containers = page.css("article, main, [role='main']")
            if containers:
                text = containers[0].get_all_text()
            else:
                text = page.get_all_text()

            title_els = page.css("title::text").getall()
            title = title_els[0] if title_els else ""

            if not text or len(text) < 50:
                return None

            return {"text": text, "title": title, "url": url, "method": "scrapling"}
        except Exception as exc:
            self.last_error = str(exc)
            logger.debug("scrapling extract failed for %s: %s", url, exc)
            return None

    def extract_headings(self, url: str) -> list[dict]:
        page = self._fetch_page(url)
        if page is None:
            return []
        headings = []
        try:
            for level in range(1, 5):
                for text in page.css(f"h{level}::text").getall():
                    text = text.strip()
                    if text:
                        headings.append({"level": level, "text": text})
        except Exception as exc:
            self.last_error = str(exc)
            logger.debug("scrapling headings failed for %s: %s", url, exc)
        return headings

    def extract_links(self, url: str, base_domain: str | None = None) -> list[dict]:
        page = self._fetch_page(url)
        if page is None:
            return []
        links = []
        try:
            for el in page.css("a[href]"):
                href = el.attrib.get("href", "")
                text = (el.text or "").strip()
                if not href or href.startswith(("#", "javascript:")):
                    continue
                link_type = "internal" if (base_domain and base_domain in href) else "external"
                links.append({"url": href, "anchor_text": text, "type": link_type})
        except Exception as exc:
            self.last_error = str(exc)
            logger.debug("scrapling links failed for %s: %s", url, exc)
        return links

    def extract_meta(self, url: str) -> dict:
        page = self._fetch_page(url)
        if page is None:
            return {}
        meta: dict = {}
        try:
            titles = page.css("title::text").getall()
            if titles:
                meta["title"] = titles[0]
            for el in page.css("meta"):
                name = el.attrib.get("name", "") or el.attrib.get("property", "")
                content = el.attrib.get("content", "")
                if name and content:
                    meta[name] = content
            canonicals = page.css('link[rel="canonical"]')
            if canonicals:
                meta["canonical"] = canonicals[0].attrib.get("href", "")
        except Exception as exc:
            self.last_error = str(exc)
            logger.debug("scrapling meta failed for %s: %s", url, exc)
        return meta

    def scrape_competitor(self, url: str) -> dict:
        page = self._fetch_page(url)
        if page is None:
            return {"url": url, "error": self.last_error or "fetch_failed"}
        result: dict = {"url": url}
        try:
            titles = page.css("title::text").getall()
            result["title"] = titles[0] if titles else ""

            for el in page.css("meta"):
                name = el.attrib.get("name", "") or el.attrib.get("property", "")
                content = el.attrib.get("content", "")
                if name == "description":
                    result["meta_description"] = content
                elif name == "og:title":
                    result["og_title"] = content

            headings = []
            for level in range(1, 5):
                for text in page.css(f"h{level}::text").getall():
                    text = text.strip()
                    if text:
                        headings.append({"level": level, "text": text})
            result["headings"] = headings

            containers = page.css("article, main, [role='main']")
            text = containers[0].get_all_text() if containers else page.get_all_text()
            result["text_preview"] = text[:500]
            result["word_count"] = len(re.findall(r"\w+", text))

            external_links = []
            for el in page.css("a[href]"):
                href = el.attrib.get("href", "")
                anchor = (el.text or "").strip()
                if href and href.startswith("http") and not href.startswith(("#", "javascript:")):
                    external_links.append({"url": href, "anchor_text": anchor})
            result["external_links_discovered"] = external_links[:20]

        except Exception as exc:
            self.last_error = str(exc)
            result["error"] = str(exc)
            logger.debug("scrapling competitor failed for %s: %s", url, exc)
        return result

    def validate_url(self, url: str) -> dict:
        page = self._fetch_page(url)
        if page is None:
            return {"url": url, "reachable": False, "error": self.last_error}
        try:
            titles = page.css("title::text").getall()
            title = titles[0] if titles else ""
            text = page.get_all_text()
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
