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
    from app.services.seo.agent_generation import competitor_errors, prose_count_errors

    candidate = {
        "content_html": ('<p>Idéal le reconnaît, et <a href="https://www.linge-net.com/blog/x">ce guide</a> aussi. '
                         "Les sites concurrents se trompent.</p>"),
        "competitors": [{"url": "https://www.ideal.fr/a"}, {"url": "https://www.linge-net.com/blog/x"}],
        "sources": [{"url": "https://www.60millions-mag.com/a"}, {"url": "https://www.ideal.fr/a"}],
    }
    errors = " | ".join(competitor_errors(candidate))
    assert "Lien vers un concurrent" in errors and "linge-net" in errors
    assert "sites concurrents" in errors and "Seulement 1 domaine" in errors
    assert prose_count_errors("<p>Retenez deux gestes à faire dans l'ordre :</p><ol><li>a</li><li>b</li><li>c</li></ol>")
    assert not prose_count_errors("<p>Retenez trois gestes :</p><ol><li>a</li><li>b</li><li>c</li></ol>")
