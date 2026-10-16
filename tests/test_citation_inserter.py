"""Insertion des citations : tests hors ligne avec un faux provider."""
import json
import re

from app.services.seo.citation_inserter import eligible_external_sources, insert_citations, insert_link
from app.services.seo.section_writer import extract_h2_texts

ARTICLE = (
    "<p>WordPress reste le choix le plus courant pour un blog qui grossit.</p>\n"
    "<h2>Ce que dit l'État sur le numérique des TPE</h2>\n"
    "<p>Près d'une TPE sur trois n'a toujours pas de site internet en France. "
    "Les dispositifs publics accompagnent la création d'un premier site.</p>\n"
    "<h2>Les prix réels</h2>\n"
    "<p>L'abonnement Webflow le moins cher pour un site vitrine démarre autour de 14 € par mois. "
    "WordPress est un logiciel libre publié sous licence GPL.</p>\n"
    "<h2>Le SEO</h2>\n"
    "<p>Bien choisir son hébergement influence directement le temps de chargement des pages.</p>\n"
)

EXTERNAL = [
    {"url": "https://www.francenum.gouv.fr/guides-et-conseils/site-internet", "anchor_text": "France Num",
     "domain_tier": "strong", "source_reliability": "high",
     "excerpt": "Une TPE sur trois ne dispose pas encore d'un site internet."},
    {"url": "https://fr.wikipedia.org/wiki/WordPress", "anchor_text": "WordPress — Wikipédia",
     "domain_tier": "strong", "source_reliability": "high",
     "excerpt": "WordPress est un système de gestion de contenu libre distribué sous licence GPL."},
    {"url": "https://webflow.com/pricing", "anchor_text": "Webflow Pricing", "domain_tier": "neutral",
     "source_reliability": "high", "excerpt": "Basic site plan from $14/mo billed yearly."},
    {"url": "https://blog-concurrent.example.com/avis", "anchor_text": "Avis", "domain_tier": "neutral",
     "source_reliability": "medium", "excerpt": "Notre avis sur Webflow."},
    {"url": "https://www.legifrance.gouv.fr/", "anchor_text": "Légifrance", "domain_tier": "strong",
     "source_reliability": "high", "excerpt": ""},
]
INTERNAL = [
    {"target_url": "/articles/choisir-hebergement-web", "anchor_text": "Choisir son hébergement web",
     "context": {"target_excerpt": "Comparatif des hébergeurs pour un site WordPress."}},
    {"target_url": "/articles/seo-local", "anchor_text": "SEO local", "context": {}},
]

PICKS = {
    "links": [
        {"id": "E1", "sentence": "Près d'une TPE sur trois n'a toujours pas de site internet en France.",
         "anchor": "une TPE sur trois"},
        {"id": "E2", "sentence": "WordPress est un logiciel libre publié sous licence GPL.",
         "anchor": "logiciel libre publié sous licence GPL"},
        {"id": "E3", "sentence": "L'abonnement Webflow le moins cher pour un site vitrine démarre autour de 14 € par mois.",
         "anchor": "abonnement Webflow le moins cher"},
        {"id": "I1", "sentence": "Bien choisir son hébergement influence directement le temps de chargement des pages.",
         "anchor": "choisir son hébergement"},
    ]
}


class FakeLinker:
    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts: list[str] = []

    def __call__(self, prompt: str, step: str, temperature: float) -> str:
        self.prompts.append(prompt)
        response = self.responses.pop(0) if self.responses else {"links": []}
        return json.dumps(response, ensure_ascii=False)


def _links(content: str) -> list[str]:
    return re.findall(r"<a\b[^>]*>.*?</a>", content)


def test_only_reliable_sources_with_excerpts_are_candidates():
    urls = [link["url"] for link in eligible_external_sources(EXTERNAL, keyword="webflow ou wordpress")]
    assert urls == [
        "https://www.francenum.gouv.fr/guides-et-conseils/site-internet",
        "https://fr.wikipedia.org/wiki/WordPress",
        "https://webflow.com/pricing",
    ]


def test_inserts_up_to_three_citations_and_internal_link():
    fake = FakeLinker([PICKS])
    content, report = insert_citations(ARTICLE, fake, EXTERNAL, INTERNAL, keyword="webflow ou wordpress")
    links = _links(content)
    assert len(links) == 4
    assert ('<a href="https://www.francenum.gouv.fr/guides-et-conseils/site-internet" target="_blank" '
            'rel="noopener">une TPE sur trois</a>') in content
    assert 'rel="noopener">logiciel libre publié sous licence GPL</a>' in content
    # Page tarifs officielle (entité du mot-clé) : pas de nofollow.
    assert '<a href="https://webflow.com/pricing" target="_blank" rel="noopener">abonnement Webflow le moins cher</a>' in content
    assert '<a href="/articles/choisir-hebergement-web">choisir son hébergement</a>' in content
    assert "nofollow" not in content
    assert extract_h2_texts(content) == extract_h2_texts(ARTICLE)
    assert len(report["inserted"]) == 4
    assert len(fake.prompts) == 1  # minimum atteint : pas de seconde tentative
    # Le texte n'a pas bougé hors des balises <a>.
    assert re.sub(r"</?a\b[^>]*>", "", content) == ARTICLE


def test_source_without_matching_sentence_is_skipped_never_forced():
    picks = {"links": [
        {"id": "E1", "sentence": "Cette phrase n'existe pas dans l'article du tout.", "anchor": "phrase"},
        {"id": "E2", "sentence": "WordPress est un logiciel libre publié sous licence GPL.", "anchor": "licence GPL"},
    ]}
    content, report = insert_citations(ARTICLE, FakeLinker([picks]), EXTERNAL[:2], [], keyword="webflow")
    assert len(_links(content)) == 1
    assert report["skipped"][0]["reason"].startswith("phrase introuvable")


def test_second_attempt_when_first_pass_inserts_nothing():
    first = {"links": []}
    second = {"links": [{"id": "E1", "sentence": "WordPress est un logiciel libre publié sous licence GPL.",
                         "anchor": "logiciel libre"}]}
    fake = FakeLinker([first, second])
    content, report = insert_citations(ARTICLE, fake, EXTERNAL[1:2], INTERNAL, keyword="webflow")
    assert len(fake.prompts) == 2
    assert "Articles internes" not in fake.prompts[1]
    assert '<a href="https://fr.wikipedia.org/wiki/WordPress"' in content
    assert len(report["inserted"]) == 1


def test_no_insertion_when_model_finds_nothing_twice():
    fake = FakeLinker([{"links": []}, {"links": []}])
    content, report = insert_citations(ARTICLE, fake, EXTERNAL, [], keyword="webflow")
    assert content == ARTICLE
    assert report["inserted"] == []


def test_respects_existing_external_links_budget():
    from app.services.seo.citation_inserter import normalize_external_rels

    article = ARTICLE.replace(
        "Les dispositifs publics",
        '<a href="https://a.example.org/x">Les dispositifs</a> <a href="https://b.example.org/y">publics</a> '
        '<a href="https://c.example.org/z">aides</a>',
    )
    fake = FakeLinker([PICKS])
    content, report = insert_citations(article, fake, EXTERNAL, [], keyword="webflow")
    assert content == normalize_external_rels(article, "webflow")
    assert fake.prompts == []
    assert report["existing_external"] == 3


def test_never_links_inside_heading_or_existing_link():
    content, reason = insert_link(
        ARTICLE, "Ce que dit l'État sur le numérique des TPE", "numérique des TPE",
        "https://www.francenum.gouv.fr/", external=True, follow=True,
    )
    assert content == ARTICLE and reason is not None
    linked = ARTICLE.replace("WordPress est un logiciel libre", '<a href="/x">WordPress</a> est un logiciel libre')
    content, reason = insert_link(
        linked, "WordPress est un logiciel libre publié sous licence GPL.", "licence GPL",
        "https://fr.wikipedia.org/wiki/WordPress", external=True, follow=True,
    )
    assert content == linked and reason == "la phrase porte déjà un lien"


def test_non_reference_source_gets_nofollow():
    content, reason = insert_link(
        ARTICLE, "WordPress est un logiciel libre publié sous licence GPL.", "logiciel libre",
        "https://blog.example.com/wordpress", external=True, follow=False,
    )
    assert reason is None
    assert 'rel="noopener nofollow">logiciel libre</a>' in content


def test_normalize_external_rels_follows_reference_sources():
    from app.services.seo.citation_inserter import normalize_external_rels

    html = (
        "<p><a href='https://www.francenum.gouv.fr/guide' target='_blank' rel='nofollow'>France Num</a> "
        "<a href=\"https://blog.example.com/x\">un blog</a> "
        "<a href=\"https://unsplash.com/@p\">Per</a> <a href=\"/interne\">interne</a></p>"
    )
    out = normalize_external_rels(html, "site vitrine")
    assert '<a href="https://www.francenum.gouv.fr/guide" target="_blank" rel="noopener">France Num</a>' in out
    assert '<a href="https://blog.example.com/x" target="_blank" rel="noopener nofollow">un blog</a>' in out
    assert '<a href="https://unsplash.com/@p">Per</a>' in out
    assert '<a href="/interne">interne</a>' in out
