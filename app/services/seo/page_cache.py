from __future__ import annotations

"""Cache de pages partagé par une génération (chaîne v2, étape 5).

Avant : le research brief, la qualité des sources et le plan de liens
externes téléchargeaient chacun les mêmes URLs (jusqu'à 3 fois la même page).
Ici une génération ouvre un PageCache (page_cache_scope) : chaque URL est
téléchargée au plus une fois, échec compris, et tous les lecteurs
(scrapling_adapter, source_pages) passent par lui. robots.txt est respecté
(lu une fois par hôte) ; un robots.txt illisible n'interdit rien.
"""

import logging
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Callable
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

logger = logging.getLogger(__name__)

ROBOTS_USER_AGENT = "IdeasStudio"
DEFAULT_TIMEOUT_SECONDS = 8
ROBOTS_TIMEOUT_SECONDS = 4
MAX_HTML_BYTES = 3_000_000

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 IdeasStudio"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

Fetcher = Callable[[str, float], "str | None"]


def _http_get(url: str, timeout: float) -> str | None:
    import httpx

    resp = httpx.get(url, timeout=timeout, follow_redirects=True, headers=_HEADERS)
    resp.raise_for_status()
    ctype = resp.headers.get("content-type", "")
    if ctype and "html" not in ctype and "xml" not in ctype and "text" not in ctype:
        return None
    return resp.text[:MAX_HTML_BYTES]


def _robots_get(url: str, timeout: float) -> str | None:
    import httpx

    resp = httpx.get(url, timeout=timeout, follow_redirects=True, headers=_HEADERS)
    if resp.status_code >= 400:
        return None
    return resp.text


class PageCache:
    def __init__(
        self,
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        respect_robots: bool = True,
        fetcher: Fetcher | None = None,
        robots_fetcher: Fetcher | None = None,
    ):
        self.timeout = timeout
        self.respect_robots = respect_robots
        self._fetcher = fetcher or _http_get
        self._robots_fetcher = robots_fetcher or _robots_get
        self._html: dict[str, str | None] = {}
        self._robots: dict[str, RobotFileParser | None] = {}
        self.fetch_count = 0
        self.hit_count = 0
        self.blocked_by_robots: list[str] = []
        self.failures: list[str] = []

    @staticmethod
    def _key(url: str) -> str:
        return (url or "").strip().split("#", 1)[0]

    def allowed(self, url: str) -> bool:
        if not self.respect_robots:
            return True
        try:
            parsed = urlparse(url)
        except ValueError:
            return False
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return False
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in self._robots:
            parser: RobotFileParser | None = None
            try:
                body = self._robots_fetcher(origin + "/robots.txt", ROBOTS_TIMEOUT_SECONDS)
                if body is not None:
                    parser = RobotFileParser()
                    parser.parse(body.splitlines())
            except Exception as exc:
                logger.debug("robots.txt illisible pour %s : %s", origin, exc)
                parser = None
            self._robots[origin] = parser
        parser = self._robots[origin]
        return True if parser is None else parser.can_fetch(ROBOTS_USER_AGENT, url)

    def get_html(self, url: str) -> str | None:
        """HTML de la page, téléchargé au plus une fois par génération ;
        None si interdite par robots.txt, injoignable ou non HTML."""
        key = self._key(url)
        if not key:
            return None
        if key in self._html:
            self.hit_count += 1
            return self._html[key]
        html: str | None = None
        if not self.allowed(key):
            self.blocked_by_robots.append(key)
        else:
            self.fetch_count += 1
            try:
                html = self._fetcher(key, self.timeout)
            except Exception as exc:
                logger.debug("page_cache: échec %s : %s", key, exc)
                html = None
            if html is None:
                self.failures.append(key)
        self._html[key] = html
        return html

    def stats(self) -> dict:
        return {
            "network_fetches": self.fetch_count,
            "cache_hits": self.hit_count,
            "urls": len(self._html),
            "blocked_by_robots": list(self.blocked_by_robots),
            "failures": list(self.failures),
        }


_CURRENT: ContextVar[PageCache | None] = ContextVar("ideas_studio_page_cache", default=None)


def active_page_cache() -> PageCache | None:
    return _CURRENT.get()


@contextmanager
def page_cache_scope(cache: PageCache | None = None):
    """Active un cache pour la durée d'une génération."""
    cache = cache or PageCache()
    token = _CURRENT.set(cache)
    try:
        yield cache
    finally:
        _CURRENT.reset(token)
