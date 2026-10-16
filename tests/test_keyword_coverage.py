from app.services.seo.seo_final_checklist_service import keyword_covered


def test_question_keyword_covered_in_any_order():
    assert keyword_covered("combien coûte un site vitrine", "Site vitrine : combien ça coûte en 2026")
    assert keyword_covered("combien coûte un site vitrine", "Un site vitrine professionnel coûte entre 900 et 5 000 €")
    assert keyword_covered("webflow ou wordpress pour un freelance", "Webflow ou WordPress pour freelance : comment trancher")


def test_missing_term_fails():
    assert not keyword_covered("combien coûte un site vitrine", "Site vitrine : le vrai budget")
    assert not keyword_covered("", "texte")


def test_noun_form_of_verb_counts():
    assert keyword_covered("combien coûte un site vitrine", "Coût d'un site vitrine en 2026")
