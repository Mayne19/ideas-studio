"""Cache de pages partagé et lecture des pages complètes (hors ligne)."""
from app.services.seo.adapters.content_extraction_adapter import basic_main_text
from app.services.seo.page_cache import PageCache, active_page_cache, page_cache_scope
from app.services.seo.source_pages_service import build_source_pages, is_primary_source, select_source_urls

BODY = " ".join(["Le plan Basic de Webflow coûte 14 dollars par mois en facturation annuelle."] * 20)
PAGE = (
    "<html><head><title>Prix Webflow</title><script>var x = 1;</script></head><body>"
    "<nav><a href='/'>Accueil</a> Menu du site</nav>"
    f"<main><h1>Prix</h1><p>{BODY}</p><ul><li>Plan CMS : 23 dollars</li></ul></main>"
    "<footer>Mentions légales</footer></body></html>"
)


class CountingFetcher:
    def __init__(self, pages: dict[str, str | None]):
        self.pages = pages
        self.calls: list[str] = []

    def __call__(self, url, timeout):
        self.calls.append(url)
        return self.pages.get(url)


def _cache(pages, robots=None):
    fetcher = CountingFetcher(pages)
    cache = PageCache(fetcher=fetcher, robots_fetcher=lambda url, t: (robots or {}).get(url))
    return cache, fetcher


def test_each_url_is_fetched_once_failures_included():
    cache, fetcher = _cache({"https://a.fr/p": PAGE})
    assert cache.get_html("https://a.fr/p") == PAGE
    assert cache.get_html("https://a.fr/p#ancre") == PAGE
    assert cache.get_html("https://b.fr/down") is None
    assert cache.get_html("https://b.fr/down") is None
    assert fetcher.calls == ["https://a.fr/p", "https://b.fr/down"]
    assert cache.stats()["cache_hits"] == 2


def test_robots_disallow_is_respected():
    robots = {"https://c.fr/robots.txt": "User-agent: *\nDisallow: /prive"}
    cache, fetcher = _cache({"https://c.fr/prive/x": PAGE, "https://c.fr/public": PAGE}, robots)
    assert cache.get_html("https://c.fr/prive/x") is None
    assert cache.get_html("https://c.fr/public") == PAGE
    assert fetcher.calls == ["https://c.fr/public"]
    assert cache.blocked_by_robots == ["https://c.fr/prive/x"]


def test_scrapling_reads_through_the_active_cache():
    from app.services.seo.adapters import scrapling_adapter as mod

    cache, fetcher = _cache({"https://a.fr/p": PAGE})
    with page_cache_scope(cache):
        assert active_page_cache() is cache
        mod._fetch_adaptor("https://a.fr/p")
        mod._fetch_adaptor("https://a.fr/p")
    assert active_page_cache() is None
    assert fetcher.calls == ["https://a.fr/p"]


def test_basic_main_text_drops_navigation_and_scripts():
    text, title = basic_main_text(PAGE)
    assert title == "Prix Webflow"
    assert "14 dollars" in text and "Plan CMS : 23 dollars" in text
    assert "Menu du site" not in text and "var x" not in text and "Mentions" not in text


RESEARCH = {
    "sources_consulted": [{"url": f"https://concurrent{i}.fr/prix-webflow", "title": f"C{i}"} for i in range(7)]
    + [{"url": "https://webflow.com/pricing", "title": "Webflow pricing"}],
    "discovered_links": ["https://www.service-public.fr/professionnels", "https://reddit.com/r/webflow"],
    "people_also_ask": [{"question": "Q ?", "url": "https://docs.webflow.com/plans"}],
}


def test_select_source_urls_takes_top5_and_up_to_3_primaries():
    selected = select_source_urls(RESEARCH, "prix webflow")
    roles = [s["role"] for s in selected]
    assert roles[:5] == ["competitor"] * 5
    primaries = [s["url"] for s in selected if s["role"] == "primary"]
    assert primaries == [
        "https://webflow.com/pricing", "https://www.service-public.fr/professionnels",
        "https://docs.webflow.com/plans",
    ]
    assert not is_primary_source("https://reddit.com/r/webflow", "prix webflow")


def test_build_source_pages_truncates_and_skips_failures():
    pages = {s["url"]: PAGE for s in select_source_urls(RESEARCH, "prix webflow")}
    pages["https://concurrent1.fr/prix-webflow"] = None
    cache, fetcher = _cache(pages)

    class Extractor:
        def extract_from_html(self, html, url):
            text, title = basic_main_text(html)
            return {"text": text, "title": title, "method": "basic_html"}

    result = build_source_pages(RESEARCH, "prix webflow", cache, max_chars=500, extractor=Extractor())
    assert len(result["pages"]) == 7
    assert all(p["chars"] <= 500 for p in result["pages"])
    assert result["skipped"] == [{"url": "https://concurrent1.fr/prix-webflow", "reason": "fetch_failed"}]
    assert result["pages"][0]["word_count"] > 200
    # Une seconde lecture (ex. liens externes) ne retélécharge rien.
    build_source_pages(RESEARCH, "prix webflow", cache, extractor=Extractor())
    assert len(fetcher.calls) == 8
