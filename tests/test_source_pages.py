

def test_primary_queries_add_official_sources_first():
    from app.services.seo.source_pages_service import search_primary_candidates, select_source_urls

    def fake_search(query, limit):
        return [
            {"url": "https://www.francenum.gouv.fr/guide-prix", "title": "France Num"},
            {"url": "https://blog-concurrent.fr/prix", "title": "Blog"},
        ]

    extra = search_primary_candidates("prix site vitrine", fake_search)
    assert extra == [("https://www.francenum.gouv.fr/guide-prix", "France Num")]
    brief = {"sources_consulted": [{"url": f"https://blog{i}.fr/a", "title": ""} for i in range(6)]}
    selected = select_source_urls(brief, "prix site vitrine", extra_candidates=extra)
    assert [s["role"] for s in selected].count("primary") == 1
    assert selected[5]["url"].startswith("https://www.francenum.gouv.fr")


def test_primary_search_failure_is_ignored():
    from app.services.seo.source_pages_service import search_primary_candidates

    def boom(query, limit):
        raise RuntimeError("quota")

    assert search_primary_candidates("x", boom) == []
