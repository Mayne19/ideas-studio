from app.services.seo.agent_generation import assembly_errors, structure_errors

GOOD = {
    "title": "T",
    "content_html": ("<p>Réponse directe au lecteur, avec ce qu'il doit faire tout de suite.</p>"
                     "<h2>Pourquoi</h2><p>Parce que le gras repousse l'eau, il faut un produit qui l'attrape.</p>"
                     "<h2>Le geste qui sauve votre vêtement</h2><p>Agissez avant le premier lavage.</p>"),
    "faq": [{"question": f"q{i}", "answer": "a"} for i in range(4)],
}


def test_assembly_accepts_clean_article():
    assert assembly_errors(GOOD) == []


def test_assembly_flags_faq_count_body_faq_and_duplicates():
    bad = {**GOOD, "faq": [], "content_html": GOOD["content_html"]
           + "<h2>Pourquoi</h2><p>x</p><h2>Questions fréquentes</h2><p>q</p>"}
    errors = " | ".join(assembly_errors(bad))
    assert "3 à 5 questions" in errors and "section FAQ" in errors and "répété" in errors


def test_only_hard_faults_trigger_corrections():
    from app.services.seo.agent_generation import (
        announced_count_errors, html_render_errors, link_errors,
    )

    assert structure_errors("<p>Intro.</p><h2>A</h2><h3>B</h3><p>x</p><h3>C</h3><p>y</p>", "T") == []
    assert any("tiret" in e.lower() for e in structure_errors("<p>Un texte — avec un tiret long.</p><h2>A</h2><p>x</p>", "T"))
    long_intro = "<p>" + "mot " * 160 + "</p><h2>A</h2><p>" + "corps " * 1200 + "</p>"
    assert structure_errors(long_intro, "T") == []  # 160 mots mais moins de 15 %
    assert len(link_errors('<a href="https://w.be/x">a</a> <a href="https://w.be/x/">b</a>')) == 1
    html = ("<p>i</p><h2>La méthode en quatre gestes</h2><p>x</p><ul><li>a</li><li>b</li><li>c</li><li>d</li></ul>"
            "<table><tr><td>a</td><td>b</td></tr><tr><td>c</td></tr></table>")
    render = " | ".join(html_render_errors(html))
    assert "liste numérotée" in render and "en-tête" in render and "longueurs différentes" in render
    assert announced_count_errors("<p>i</p><h2>Les trois erreurs à éviter</h2><ol><li>a</li><li>b</li></ol>")
    assert not announced_count_errors("<p>i</p><h2>Les trois erreurs à éviter</h2><ol><li>a</li><li>b</li><li>c</li></ol>")


def test_competitor_and_prose_count_hard_faults():
    from app.services.seo.agent_generation import competitor_errors, fact_errors, prose_count_errors

    candidate = {
        "content_html": ('<p>Idéal le reconnaît, et <a href="https://www.linge-net.com/blog/x">ce guide</a> aussi. '
                         "Les sites concurrents se trompent.</p>"),
        "competitors": [{"url": "https://www.ideal.fr/a"}, {"url": "https://www.linge-net.com/blog/x"}],
        "sources": [{"url": "https://www.60millions-mag.com/a"}, {"url": "https://www.ideal.fr/a"}],
    }
    errors = " | ".join(competitor_errors(candidate))
    assert "Lien vers un concurrent" in errors and "linge-net" in errors
    assert "sites concurrents" in errors and "Seulement 1 domaine" in errors
    assert "concurrent apparaît dans" in errors
    assert prose_count_errors("<p>Retenez deux gestes à faire dans l'ordre :</p><ol><li>a</li><li>b</li><li>c</li></ol>")
    assert prose_count_errors("<p>Retenez 2 gestes :</p><ol><li>a</li><li>b</li><li>c</li></ol>")
    assert prose_count_errors("<p>Retenez un seul geste :</p><ol><li>a</li><li>b</li></ol>")
    assert not prose_count_errors("<p>Retenez trois gestes :</p><ol><li>a</li><li>b</li><li>c</li></ol>")
    assert not prose_count_errors("<p>Attendez deux heures avant de recommencer.</p>")
    assert not prose_count_errors("<blockquote>Les deux gestes sont parfois confondus.</blockquote>"
                                  "<ol><li>a</li><li>b</li></ol>")
    assert not prose_count_errors("<p>La dose est de 2 mg.</p><ol><li>a</li><li>b</li></ol>")
    assert not prose_count_errors("<table><tr><td>Deux gestes</td></tr></table>"
                                  "<ol><li>a</li><li>b</li></ol>")
    assert not prose_count_errors("<p>Retenez deux gestes dans cette phrase, sans liste à suivre.</p>")


def test_facts_require_exact_quote_and_declared_source():
    from app.services.seo.agent_generation import fact_errors, self_review_errors

    valid = {
        "sources": [{"url": "https://example.com/guide/?utm_source=test"}],
        "facts": [{"value": "20 minutes", "source_url": "http://www.example.com/guide/#section",
                   "quote": "20 minutes"}],
        "self_review": {"notes": "Chaque fait est relié à sa source."},
    }
    assert fact_errors(valid) == []
    assert self_review_errors(valid) == []

    invalid = {
        "sources": [{"url": "https://example.com/guide"}],
        "facts": [{"value": "20 minutes", "source_url": "https://other.example/guide", "quote": ""}],
    }
    errors = " | ".join(fact_errors(invalid))
    assert "citation exacte" in errors and "n'apparaît pas" in errors
    assert self_review_errors({"self_review": {"notes": "Ce point vient de connaissances générales."}})


def test_fact_url_matching_decodes_path_and_self_review_handles_negation_and_agreement():
    from app.services.seo.agent_generation import fact_errors, self_review_errors

    candidate = {
        "sources": [{"url": "https://example.com/guide/été"}],
        "facts": [{"value": "20 minutes", "source_url": "http://www.example.com/guide/%C3%A9t%C3%A9#details",
                   "quote": "20 minutes"}],
    }
    assert fact_errors(candidate) == []

    assert self_review_errors({"self_review": {"notes": "Aucun fait non sourcé. Rien n'est écrit de mémoire."}}) == []
    assert self_review_errors({"self_review": {"notes": "Deux chiffres non vérifiés."}})
    assert self_review_errors({"self_review": {"notes": "Une mise en garde non sourcée."}})
    assert self_review_errors({"self_review": {"notes": "Les faits viennent de connaissances générales, pas d'une source lue."}})
    assert self_review_errors({"self_review": {"notes": "Il n'y a pas de fait non vérifié."}}) == []
    assert self_review_errors({"self_review": {"notes": "Je n'ai rien écrit de mémoire."}}) == []
    assert self_review_errors({"self_review": {"notes": "Aucun fait non sourcé, mais deux chiffres restent non vérifiés."}})


def test_competitor_matching_uses_registered_domain_without_suffix_false_positive():
    from app.services.seo.agent_generation import competitor_errors

    candidate = {
        "content_html": '<p><a href="https://blog.ideal.fr/guide">guide</a></p>',
        "competitors": [{"url": "https://www.ideal.fr/a"}],
        "sources": [{"url": "https://notideal.fr/a"}, {"url": "https://one.example/a"},
                    {"url": "https://two.example/a"}, {"url": "https://three.example/a"}],
    }
    errors = " | ".join(competitor_errors(candidate))
    assert "Lien vers un concurrent" in errors
    assert "Seulement" not in errors

    clean = {**candidate, "sources": [{"url": "https://notideal.fr/a"}, {"url": "https://one.example/a"},
                                        {"url": "https://two.example/a"}, {"url": "https://three.example/a"}]}
    ideal_text = {**clean, "content_html": "<p>Idéal le reconnaît.</p>"}
    assert any("ideal" in error for error in competitor_errors(ideal_text))
    assert not any("concurrent" in error.lower() for error in competitor_errors(
        {**clean, "content_html": "<p>Le moment idéal arrive.</p>"}))
    assert not any("concurrent" in error.lower() for error in competitor_errors(
        {**clean, "content_html": "<p>La température idéale convient.</p>"}))

    ariel = {**clean, "competitors": [{"url": "https://ariel.co.uk/a"}],
             "content_html": "<p>Ariel conseille cette méthode.</p>"}
    assert any("ariel" in error for error in competitor_errors(ariel))

    public_sources = {**candidate, "competitors": [], "sources": [
        {"url": "https://sante.gouv.fr/a"}, {"url": "https://service-public.gouv.fr/a"},
        {"url": "https://one.example/a"},
    ]}
    assert not any("Seulement" in error for error in competitor_errors(public_sources))
