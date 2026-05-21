from __future__ import annotations

import re


class ContentExtractionAdapter:
    provider_name = "content_extraction"
    enabled = False
    configured = False
    requires_api_key = False
    last_error: str | None = None
    real_data_available = False
    fallback_mode = "not_configured"
    trust_level = "none"

    def __init__(self):
        self._check_trafilatura()
        if not self.configured:
            self._check_readability()

    def _check_trafilatura(self):
        try:
            import trafilatura  # noqa: F401
            self.configured = True
            self.enabled = True
            self.real_data_available = True
            self.fallback_mode = "trafilatura"
            self.trust_level = "medium"
        except ImportError:
            pass

    def _check_readability(self):
        try:
            import readability  # noqa: F401
            self.configured = True
            self.enabled = True
            self.real_data_available = True
            self.fallback_mode = "readability"
            self.trust_level = "medium"
        except ImportError:
            pass

    def extract(self, url: str) -> dict | None:
        if not self.configured:
            return None
        try:
            import httpx
            resp = httpx.get(url, timeout=15, headers={"User-Agent": "IdeasStudio/1.0"})
            resp.raise_for_status()
            html = resp.text
            if self.fallback_mode == "trafilatura":
                import trafilatura
                extracted = trafilatura.extract(html)
                if extracted:
                    return {"text": extracted, "url": url, "method": "trafilatura"}
            if self.fallback_mode == "readability":
                from readability import Document
                doc = Document(html)
                return {"text": doc.summary(), "title": doc.title(), "url": url, "method": "readability"}
        except Exception as exc:
            self.last_error = str(exc)
        return None

    def extract_headings(self, url: str) -> list[dict]:
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


content_extraction_adapter = ContentExtractionAdapter()
