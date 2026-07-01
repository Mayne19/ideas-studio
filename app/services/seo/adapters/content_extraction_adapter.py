from __future__ import annotations

from app.services.seo.adapters.scrapling_adapter import scrapling_adapter


class ContentExtractionAdapter:
    """Thin facade — delegates to ScraplingAdapter with trafilatura/readability fallback."""

    @property
    def provider_name(self) -> str:
        return scrapling_adapter.provider_name

    @property
    def enabled(self) -> bool:
        return scrapling_adapter.enabled

    @property
    def configured(self) -> bool:
        return scrapling_adapter.configured

    @property
    def requires_api_key(self) -> bool:
        return scrapling_adapter.requires_api_key

    @property
    def last_error(self) -> str | None:
        return scrapling_adapter.last_error

    @property
    def real_data_available(self) -> bool:
        return scrapling_adapter.real_data_available

    @property
    def fallback_mode(self) -> str:
        return scrapling_adapter.fallback_mode

    @property
    def trust_level(self) -> str:
        return scrapling_adapter.trust_level

    def extract(self, url: str) -> dict | None:
        result = scrapling_adapter.extract(url)
        if result is not None:
            return result
        return self._legacy_extract(url)

    def _legacy_extract(self, url: str) -> dict | None:
        try:
            import httpx
            resp = httpx.get(url, timeout=15, headers={"User-Agent": "IdeasStudio/1.0"})
            resp.raise_for_status()
            html = resp.text
            try:
                import trafilatura
                extracted = trafilatura.extract(html)
                if extracted:
                    return {"text": extracted, "url": url, "method": "trafilatura"}
            except ImportError:
                pass
            try:
                from readability import Document
                doc = Document(html)
                return {"text": doc.summary(), "title": doc.title(), "url": url, "method": "readability"}
            except ImportError:
                pass
        except Exception:
            pass
        return None

    def extract_headings(self, url: str) -> list[dict]:
        result = scrapling_adapter.extract_headings(url)
        if result:
            return result
        return self._legacy_extract_headings(url)

    def _legacy_extract_headings(self, url: str) -> list[dict]:
        import re
        headings = []
        try:
            import httpx
            resp = httpx.get(url, timeout=15, headers={"User-Agent": "IdeasStudio/1.0"})
            resp.raise_for_status()
            html = resp.text
            for level in range(1, 5):
                for m in re.finditer(rf"<h{level}[^>]*>(.*?)</h{level}>", html, re.IGNORECASE | re.DOTALL):
                    text = re.sub(r"<[^>]+>", " ", m.group(1)).strip()
                    if text:
                        headings.append({"level": level, "text": text})
        except Exception:
            pass
        return headings

    def get_status(self) -> dict:
        return scrapling_adapter.get_status()


content_extraction_adapter = ContentExtractionAdapter()
