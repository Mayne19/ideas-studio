

def test_primary_queries_add_official_sources_first():
    from app.services.seo.source_pages_service import search_primary_candidates, select_source_urls

    def fake_search(query, limit):
        return [
            {"url": "https://www.francenum.gouv.fr/guide-prix", "title": "Prix d'un site vitrine - France Num"},
            {"url": "https://blog-concurrent.fr/prix", "title": "Blog"},
        ]

    extra = search_primary_candidates("prix site vitrine", fake_search)
    assert extra == [("https://www.francenum.gouv.fr/guide-prix", "Prix d'un site vitrine - France Num")]
    brief = {"sources_consulted": [{"url": f"https://blog{i}.fr/a", "title": ""} for i in range(6)]}
    selected = select_source_urls(brief, "prix site vitrine", extra_candidates=extra)
    assert [s["role"] for s in selected].count("primary") == 1
    assert selected[5]["url"].startswith("https://www.francenum.gouv.fr")


def test_primary_search_failure_is_ignored():
    from app.services.seo.source_pages_service import search_primary_candidates

    def boom(query, limit):
        raise RuntimeError("quota")

    assert search_primary_candidates("x", boom) == []


def test_primary_search_drops_job_ads_vendor_listings_and_off_topic_pages():
    from app.services.seo.source_pages_service import search_primary_candidates

    def fake_search(query, limit):
        return [
            {"link": "https://www.jeveuxaider.gouv.fr/missions-benevolat/95087/x", "title": "Bénévolat CMS headless"},
            {"link": "https://choisirleservicepublic.gouv.fr/offre-emploi/2026-1/", "title": "Développeur CMS headless"},
            {"link": "https://www.francenum.gouv.fr/activateurs/next-impact", "title": "Next Impact CMS headless"},
            {"link": "https://www.numerique.gouv.fr/guide-accessibilite", "title": "Guide accessibilité", "snippet": "RGAA"},
            {"link": "https://www.francenum.gouv.fr/guides/cms-headless", "title": "Le CMS headless expliqué"},
        ]

    assert search_primary_candidates("qu'est-ce qu'un cms headless", fake_search) == [
        ("https://www.francenum.gouv.fr/guides/cms-headless", "Le CMS headless expliqué")]
