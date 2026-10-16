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


def test_structure_errors_are_readable_instructions():
    errors = structure_errors("<p>Intro.</p><h2>A</h2><h3>B</h3><p>x</p><h3>C</h3><p>y</p>", "T")
    assert any("H2" in e and "H3" in e for e in errors)
