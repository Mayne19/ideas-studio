"""fact_ledger : la citation doit être une sous-chaîne exacte de la page."""
from app.services.seo.fact_ledger_service import (
    build_fact_ledger,
    citation_candidates_from_markers,
    figure_in_quote,
    ledger_to_evidence_pack,
    quote_in_page,
)
from app.services.seo.section_writer import strip_fact_markers

PAGE_TEXT = (
    "Tarifs 2026.\nLe plan Basic coûte 14 $ par mois en facturation annuelle.\n"
    "Le plan CMS coûte 23 $ par mois et inclut 2 000 éléments de collection."
)
PAGES = {"pages": [
    {"url": "https://concurrent.fr/prix", "role": "competitor", "title": "Prix", "text": "Webflow coûte cher selon nous, environ 30 $ par mois.", "source_tier": "neutral"},
    {"url": "https://webflow.com/pricing", "role": "primary", "title": "Pricing", "text": PAGE_TEXT, "source_tier": "neutral"},
]}


def test_quote_must_be_an_exact_substring():
    assert quote_in_page("Le plan Basic coûte 14 $ par mois", PAGE_TEXT)
    # Seuls les blancs sont normalisés (saut de ligne dans la page).
    assert quote_in_page("Tarifs 2026. Le plan Basic coûte 14 $", PAGE_TEXT)
    # Un seul mot ou chiffre changé suffit à rejeter.
    assert not quote_in_page("Le plan Basic coûte 15 $ par mois", PAGE_TEXT)
    assert not quote_in_page("le plan basic coûte 14 $ par mois", PAGE_TEXT)
    assert not quote_in_page("Basic 14 $", PAGE_TEXT)  # trop court


def test_figure_must_appear_in_its_quote():
    assert figure_in_quote("2 000", "inclut 2 000 éléments")
    assert figure_in_quote("2000", "inclut 2 000 éléments")
    assert not figure_in_quote("3 000", "inclut 2 000 éléments")


def _fake_llm(prompt: str) -> dict:
    if "webflow.com/pricing" in prompt:
        return {"facts": [
            {"claim": "Le plan Basic coûte 14 $ par mois.", "quote_verbatim": "Le plan Basic coûte 14 $ par mois",
             "figure": "14 $", "date_or_as_of": "2026", "usage_hint": "prix"},
            {"claim": "Le plan CMS coûte 25 $.", "quote_verbatim": "Le plan CMS coûte 25 $ par mois",
             "figure": "25 $"},
            {"claim": "Le plan CMS inclut 2 000 éléments.", "quote_verbatim": "inclut 2 000 éléments de collection",
             "figure": "5 000"},
        ]}
    return {"facts": [{"claim": "Webflow coûte 30 $.", "quote_verbatim": "environ 30 $ par mois.", "figure": "30 $"}]}


def test_ledger_drops_invented_quotes_and_numbers_facts():
    ledger = build_fact_ledger(PAGES, "prix webflow", _fake_llm)
    claims = [f["claim"] for f in ledger["facts"]]
    assert "Le plan CMS coûte 25 $." not in claims
    assert ledger["rejected_count"] == 1
    assert ledger["rejected"][0]["reason"] == "quote_not_in_page"
    # Sources primaires d'abord, identifiants continus, URL conservée.
    assert [f["fact_id"] for f in ledger["facts"]] == ["F1", "F2", "F3"]
    assert ledger["facts"][0]["url"] == "https://webflow.com/pricing"
    # Chiffre absent de la citation : retiré du fait, le fait reste.
    assert ledger["facts"][1]["figure"] == ""
    assert ledger["llm_calls"] == 2
    for fact in ledger["facts"]:
        page = next(p for p in PAGES["pages"] if p["url"] == fact["url"])
        assert quote_in_page(fact["quote_verbatim"], page["text"])
    assert ledger_to_evidence_pack(ledger)["evidence_items"][0]["fact_id"] == "F1"


def test_ledger_survives_llm_errors():
    def broken(prompt):
        raise RuntimeError("timeout")
    ledger = build_fact_ledger(PAGES, "prix webflow", broken)
    assert ledger["facts"] == [] and ledger["status"] == "error"


def test_markers_are_stripped_and_traced():
    html = "<p>Le plan Basic coûte 14 $ par mois [F1]. Le CMS est limité [F2, F9].</p>"
    cleaned, markers = strip_fact_markers(html, {"F1", "F2"})
    assert cleaned == "<p>Le plan Basic coûte 14 $ par mois. Le CMS est limité.</p>"
    assert [(m["fact_id"], m["known"]) for m in markers] == [("F1", True), ("F2", True), ("F9", False)]
    assert markers[0]["sentence"] == "Le plan Basic coûte 14 $ par mois"


def test_citation_candidates_follow_used_facts_and_skip_competitors():
    ledger = build_fact_ledger(PAGES, "prix webflow", _fake_llm)
    markers = [{"fact_id": "F3"}, {"fact_id": "F2"}, {"fact_id": "F1"}, {"fact_id": "F99"}]
    links = citation_candidates_from_markers(ledger, markers, "prix webflow", {"concurrent.fr"})
    assert [link["url"] for link in links] == ["https://webflow.com/pricing"]
    assert links[0]["excerpt"].startswith("inclut 2 000")
