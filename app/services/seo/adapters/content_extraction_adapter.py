from __future__ import annotations

import html as html_lib
import re
from html.parser import HTMLParser

from app.services.seo.adapters.scrapling_adapter import scrapling_adapter

# Balises dont le texte n'est jamais du contenu principal.
_SKIP_TAGS = {"script", "style", "noscript", "nav", "header", "footer", "aside", "form", "svg",
              "button", "iframe", "template"}
_BLOCK_TAGS = {"p", "li", "h1", "h2", "h3", "h4", "td", "th", "blockquote", "pre", "dd", "dt", "figcaption"}


class _MainTextParser(HTMLParser):
    """Repli sans dépendance quand trafilatura est absent : texte des blocs
    (paragraphes, titres, listes, cellules) hors navigation, en-têtes et
    pieds de page ; le contenu d'<article> ou <main> est préféré."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.main_depth = 0
        self.block: list[str] | None = None
        self.blocks: list[tuple[bool, str]] = []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self.skip_depth += 1
        elif tag in ("article", "main"):
            self.main_depth += 1
        elif tag == "title":
            self._in_title = True
        if tag in _BLOCK_TAGS and not self.skip_depth:
            self.flush()
            self.block = []

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
        elif tag in ("article", "main") and self.main_depth:
            self.flush()
            self.main_depth -= 1
        elif tag == "title":
            self._in_title = False
        if tag in _BLOCK_TAGS:
            self.flush()

    def handle_data(self, data):
        if self._in_title:
            self.title += data
            return
        if self.skip_depth or self.block is None:
            return
        self.block.append(data)

    def flush(self):
        if self.block is not None:
            text = re.sub(r"\s+", " ", "".join(self.block)).strip()
            if text:
                self.blocks.append((self.main_depth > 0, text))
        self.block = None


def basic_main_text(html: str) -> tuple[str, str]:
    """(texte principal, titre) d'une page HTML, sans dépendance externe."""
    parser = _MainTextParser()
    try:
        parser.feed(html or "")
        parser.close()
    except Exception:
        pass
    parser.flush()
    in_main = [t for flag, t in parser.blocks if flag]
    blocks = in_main if sum(len(t) for t in in_main) >= 400 else [t for _, t in parser.blocks]
    return "\n".join(blocks), html_lib.unescape(parser.title.strip())


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

    def extract_from_html(self, html: str, url: str = "") -> dict | None:
        """Texte principal d'une page déjà téléchargée (cache de génération) :
        trafilatura si installé, sinon repli sur un parseur sans dépendance."""
        if not html:
            return None
        try:
            import trafilatura

            text = trafilatura.extract(html, url=url or None, include_comments=False, include_tables=True,
                                       favor_precision=True)
            if text and len(text) >= 200:
                title = ""
                try:
                    meta = trafilatura.extract_metadata(html)
                    title = (meta.title if meta else "") or ""
                except Exception:
                    pass
                return {"text": text, "title": title, "url": url, "method": "trafilatura"}
        except ImportError:
            pass
        except Exception:
            pass
        text, title = basic_main_text(html)
        if len(text) < 200:
            return None
        return {"text": text, "title": title, "url": url, "method": "basic_html"}

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
