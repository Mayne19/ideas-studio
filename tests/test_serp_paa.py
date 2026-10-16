"""Réponse Serper complète : PAA, recherches associées, encadrés ; la FAQ et
les sous-questions s'appuient sur les vraies questions de la SERP."""
from types import SimpleNamespace

from app.services.production_brief_service import build_production_brief
from app.services.seo.adapters.serp_adapter import SerpAdapter, parse_serper_extras
from app.services.seo.faq_builder import article_digest, build_faq_prompt, select_faq_questions
from app.services.seo.research_brief_service import build_research_brief_dict

SERPER_PAYLOAD = {
    "organic": [{"title": "Prix Webflow 2026", "link": "https://exemple.fr/prix-webflow", "snippet": "Le plan Basic coûte 14 $."}],
    "peopleAlsoAsk": [
        {"question": "Webflow est-il gratuit ?", "snippet": "Webflow propose un plan Starter gratuit.",
         "title": "Pricing", "link": "https://webflow.com/pricing"},
        {"question": "Webflow est-il gratuit ?", "snippet": "doublon"},
        {"question": "Quel est le prix de Webflow ?", "snippet": "À partir de 14 $ par mois."},
    ],
    "relatedSearches": [{"query": "webflow vs wordpress"}, {"query": "webflow ecommerce prix"}],
    "answerBox": {"title": "Webflow pricing", "snippet": "Basic : 14 $/mois", "link": "https://webflow.com/pricing"},
    "knowledgeGraph": {"title": "Webflow", "type": "Logiciel", "attributes": {"Fondation": "2013"}},
}


def test_parse_serper_extras_keeps_every_block():
    extras = parse_serper_extras(SERPER_PAYLOAD)
    assert [q["question"] for q in extras["people_also_ask"]] == [
        "Webflow est-il gratuit ?", "Quel est le prix de Webflow ?",
    ]
    assert extras["people_also_ask"][0]["url"] == "https://webflow.com/pricing"
    assert extras["related_searches"] == ["webflow vs wordpress", "webflow ecommerce prix"]
    assert extras["answer_box"]["snippet"] == "Basic : 14 $/mois"
    assert extras["knowledge_graph"]["attributes"] == {"Fondation": "2013"}


def test_search_full_returns_paa_with_organic(monkeypatch):
    import httpx

    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return SERPER_PAYLOAD

    monkeypatch.setattr(httpx, "post", lambda *a, **k: Resp())
    adapter = SerpAdapter(SimpleNamespace(provider="serper", api_key="k", config={}, source="test"))
    full = adapter.search_full("prix webflow", limit=5)
    assert full["organic"][0]["url"] == "https://exemple.fr/prix-webflow"
    assert len(full["people_also_ask"]) == 2
    # Compat : search() renvoie toujours la liste organique.
    assert adapter.search("prix webflow")[0]["title"] == "Prix Webflow 2026"


class _FakeSerp:
    configured = True

    def search_full(self, query, limit=10):
        return {"organic": [], **parse_serper_extras(SERPER_PAYLOAD)}


def test_research_brief_stores_paa_even_without_organic():
    brief = build_research_brief_dict("prix webflow", serp_adapter=_FakeSerp())
    assert brief["people_also_ask"][0]["question"] == "Webflow est-il gratuit ?"
    assert brief["related_searches"]


def test_production_brief_uses_paa_as_related_questions():
    research = {"people_also_ask": parse_serper_extras(SERPER_PAYLOAD)["people_also_ask"]}
    brief = build_production_brief(keyword="prix webflow", research_brief=research,
                                   keyword_brief={"related_questions": ["Webflow est-il gratuit ?"]})
    assert brief["related_questions"] == ["Webflow est-il gratuit ?", "Quel est le prix de Webflow ?"]


CONTENT = (
    "<p>Webflow coûte 14 $ par mois au minimum.</p>"
    "<h2>Quel est le prix de Webflow ?</h2><p>Le plan Basic coûte 14 $.</p>"
    "<h2>Les limites</h2><p>Le CMS plafonne à 2 000 éléments.</p>"
    "<h2>Notre verdict</h2><p>Pour un site vitrine, Webflow suffit largement.</p>"
)


def test_faq_questions_come_from_paa_and_skip_h2_duplicates():
    paa = parse_serper_extras(SERPER_PAYLOAD)["people_also_ask"]
    questions = select_faq_questions(paa, ["Quel est le prix de Webflow ?", "Les limites"], ["Webflow et le SEO ?"])
    assert [q["question"] for q in questions] == ["Webflow est-il gratuit ?", "Webflow et le SEO ?"]
    assert questions[0]["source"] == "people_also_ask"


def test_faq_prompt_uses_paa_and_the_whole_article_not_a_prefix():
    paa = parse_serper_extras(SERPER_PAYLOAD)["people_also_ask"]
    prompt = build_faq_prompt("Prix Webflow", "prix webflow", CONTENT, select_faq_questions(paa, []))
    assert "Webflow est-il gratuit ?" in prompt
    assert "Webflow propose un plan Starter gratuit." in prompt
    # La fin de l'article est visible (l'ancien content[:1500] la coupait).
    assert "Notre verdict" in prompt and "site vitrine" in prompt
    assert "<p>" not in article_digest(CONTENT)
