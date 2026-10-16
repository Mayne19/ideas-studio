"""Validateur de structure : une règle par test, sur un article de base qui
respecte toutes les règles."""
from app.services.seo.structure_validator import validate_structure

TITLE = "Combien coûte Webflow en 2026 ?"


def _para(n_sentences: int, words_per_sentence: int = 9, seed: str = "Webflow") -> str:
    sentence = " ".join([seed] + ["tarif"] * (words_per_sentence - 2) + ["mensuel."])
    return "<p>" + " ".join([sentence] * n_sentences) + "</p>"


def _section(heading: str, sizes=(3, 1, 2, 4), seed: str = "Webflow") -> str:
    return f"<h2>{heading}</h2>\n" + "\n".join(_para(n, seed=seed) for n in sizes)


INTRO = "<p>Webflow coûte entre 14 et 39 dollars par mois. Le bon plan dépend du nombre de pages.</p>"
SECTIONS = [
    _section("Les plans de site", seed="Plans"),
    _section("Les plans e-commerce", sizes=(2, 4, 1, 3), seed="Boutique"),
    _section("Les coûts cachés", sizes=(1, 3, 4, 2), seed="Coûts"),
    _section("Ce que nous recommandons", sizes=(4, 2, 1, 3), seed="Choix"),
]
GOOD = INTRO + "\n" + "\n".join(SECTIONS)


def _rule(report: dict, name: str) -> dict:
    return next(r for r in report["rules"] if r["rule"] == name)


def test_reference_article_passes_every_rule():
    report = validate_structure(GOOD, TITLE, "explainer")
    failed = [r["rule"] for r in report["rules"] if not r["passed"]]
    assert failed == []
    assert report["status"] == "pass"
    assert report["stats"]["sections"] == 4


def test_h1_in_body_or_missing_title_fails():
    report = validate_structure("<h1>Titre</h1>" + GOOD, TITLE)
    rule = _rule(report, "single_h1")
    assert not rule["passed"] and rule["severity"] == "hard"
    assert rule["violations"][0]["detail"].startswith("H1 dans le corps")
    assert not _rule(validate_structure(GOOD, ""), "single_h1")["passed"]


def test_heading_hierarchy_detects_orphan_h3_skips_and_h5():
    orphan = INTRO + "<h3>Avant tout</h3>" + _para(2) + "\n".join(SECTIONS)
    details = [v["detail"] for v in _rule(validate_structure(orphan, TITLE), "heading_hierarchy")["violations"]]
    assert "H3 sans H2 parent" in details
    skipped = GOOD + "<h2>Annexe</h2><h4>Détail</h4>" + _para(2) + "<h5>Note</h5>" + _para(1)
    details = [v["detail"] for v in _rule(validate_structure(skipped, TITLE), "heading_hierarchy")["violations"]]
    assert "Niveau sauté : H2 puis H4" in details
    assert any(d.startswith("H5 interdit") for d in details)
    assert _rule(validate_structure(GOOD, TITLE), "heading_hierarchy")["passed"]


def test_paragraph_longer_than_five_sentences_fails_with_location():
    long_section = _section("Un paragraphe trop long", sizes=(6, 1, 2))
    report = validate_structure(GOOD + long_section, TITLE)
    rule = _rule(report, "paragraph_length")
    assert not rule["passed"]
    assert rule["violations"][0]["section"] == "Un paragraphe trop long"
    assert rule["violations"][0]["unit"] == "section:5"
    assert rule["violations"][0]["detail"].startswith("6 phrases")


def test_sentence_over_45_words_fails_and_long_share_warns():
    section = "<h2>Une phrase fleuve</h2>" + _para(1, words_per_sentence=50) + _para(3) + _para(1)
    report = validate_structure(GOOD + section, TITLE)
    assert not _rule(report, "sentence_length")["passed"]
    assert "50 mots" in _rule(report, "sentence_length")["violations"][0]["detail"]
    wordy = "<h2>Des phrases longues</h2>" + _para(2, words_per_sentence=35) + _para(1) + _para(3, words_per_sentence=33)
    share = _rule(validate_structure(GOOD + wordy, TITLE), "long_sentence_share")
    assert not share["passed"] and share["severity"] == "warning"


def test_four_paragraphs_of_same_length_fail():
    uniform = _section("Un rythme mécanique", sizes=(3, 3, 3, 3))
    rule = _rule(validate_structure(GOOD + uniform, TITLE), "paragraph_variation")
    assert not rule["passed"]
    assert rule["violations"][0]["section"] == "Un rythme mécanique"


def test_intro_over_ten_percent_or_generic_fails():
    long_intro = _para(4) + _para(3) + _para(4) + _para(3)
    body = "\n".join(SECTIONS * 2)
    report = validate_structure(long_intro + body, TITLE)
    assert report["stats"]["words"] >= 600
    assert not _rule(report, "intro_length")["passed"]
    generic = "<p>Dans cet article, nous allons voir combien coûte Webflow.</p>" + "\n".join(SECTIONS)
    rule = _rule(validate_structure(generic, TITLE), "intro_generic_opening")
    assert not rule["passed"] and rule["violations"][0]["unit"] == "intro"
    missing = _rule(validate_structure("\n".join(SECTIONS), TITLE), "intro_length")
    assert missing["violations"][0]["detail"] == "Introduction absente"


def test_em_dash_banned_words_and_vous_saturation_fail():
    dashed = GOOD.replace("Le bon plan dépend", "Le bon plan — souvent — dépend")
    assert not _rule(validate_structure(dashed, TITLE), "no_em_dash")["passed"]
    banned = GOOD + "<h2>Un outil</h2><p>Webflow est un outil incontournable pour sortir du lot.</p>" + _para(3)
    detail = _rule(validate_structure(banned, TITLE), "banned_vocabulary")["violations"][0]["detail"]
    assert "incontournable" in detail and "sortir du lot" in detail
    vous = GOOD + ("<h2>Votre choix</h2><p>Vous comparez les plans. Vous lisez les limites. "
                   "Vous choisissez trop vite.</p>" + _para(2))
    assert not _rule(validate_structure(vous, TITLE), "vous_saturation")["passed"]


def test_conclusion_starting_with_en_conclusion_fails():
    ending = "<h2>Le mot de la fin</h2><p>En conclusion, Webflow vaut son prix.</p>" + _para(2)
    rule = _rule(validate_structure(GOOD + ending, TITLE), "conclusion_opening")
    assert not rule["passed"] and rule["violations"][0]["section"] == "Le mot de la fin"


def test_lists_and_tables_formatting():
    one_item = GOOD.replace("</p>\n<h2>Les coûts cachés", "</p><ul><li>Seul point</li></ul>\n<h2>Les coûts cachés", 1)
    lists = _rule(validate_structure(one_item, TITLE), "list_format")
    assert not lists["passed"] and lists["violations"][0]["detail"] == "Liste d'un seul élément"
    bad_table = GOOD + ("<h2>Tableau</h2>" + _para(2)
                        + "<table><tr><td>Plan</td><td>Prix</td></tr><tr><td>Basic</td></tr></table>")
    details = [v["detail"] for v in _rule(validate_structure(bad_table, TITLE), "table_format")["violations"]]
    assert "Tableau sans ligne d'en-tête (<th>)" in details
    assert any(d.startswith("Nombre de colonnes irrégulier") for d in details)
    good_table = GOOD + ("<h2>Tableau</h2>" + _para(2)
                         + "<table><tr><th>Plan</th><th>Prix</th></tr><tr><td>Basic</td><td>14 $</td></tr></table>")
    assert _rule(validate_structure(good_table, TITLE), "table_format")["passed"]


def test_section_balance_flags_thin_and_oversized_sections():
    thin = GOOD + "<h2>Trop court</h2><p>Une phrase.</p>"
    rule = _rule(validate_structure(thin, TITLE), "section_balance")
    assert not rule["passed"] and rule["severity"] == "warning"
    huge = GOOD + _section("Énorme", sizes=(4, 1, 3, 2, 4, 1, 3, 2, 4, 1, 3, 2, 4, 1, 3, 2, 4, 1, 3, 2, 4, 1, 3, 2, 4, 1, 3, 2, 4, 1, 3, 2))
    details = [v["detail"] for v in _rule(validate_structure(huge, TITLE), "section_balance")["violations"]]
    assert any("fois la médiane" in d for d in details)


def test_required_elements_follow_recommended_format():
    comparison = _rule(validate_structure(GOOD, TITLE, "comparison"), "required_elements")
    assert not comparison["passed"] and comparison["section_fixable"]
    with_table = GOOD + "<table><tr><th>A</th></tr><tr><td>B</td></tr></table>"
    assert _rule(validate_structure(with_table, TITLE, "comparison"), "required_elements")["passed"]
    how_to = _rule(validate_structure(GOOD, TITLE, "how_to"), "required_elements")
    assert not how_to["passed"]
    steps = GOOD.replace("</p>\n<h2>Les coûts", "</p><ol><li>Créer un compte</li><li>Choisir un plan</li></ol>\n<h2>Les coûts", 1)
    assert _rule(validate_structure(steps, TITLE, "how_to"), "required_elements")["passed"]
    assert _rule(validate_structure(GOOD, TITLE, "explainer"), "required_elements")["passed"]


def test_section_fix_is_targeted_and_guarded():
    from app.services.seo.structure_fixer import fix_failing_sections, replace_em_dashes

    assert replace_em_dashes("<p>Le plan — souvent — suffit.</p>") == "<p>Le plan, souvent, suffit.</p>"
    bad = INTRO + "\n" + SECTIONS[0] + "\n" + _section("Les coûts cachés", sizes=(6, 1, 2))
    report = validate_structure(bad, TITLE)
    calls = []

    def fixer(prompt, step, temperature):
        calls.append(step)
        return "<h2>Les coûts cachés</h2>" + _para(3) + _para(1) + _para(2) + _para(3)

    fixed, fix = fix_failing_sections(bad, report, fixer, title=TITLE)
    assert calls == ["StructureFix_section:2"]
    assert fix["applied"] == ["section:2"]
    assert _rule(validate_structure(fixed, TITLE), "paragraph_length")["passed"]

    def drops_heading(prompt, step, temperature):
        return _para(3) + _para(1)

    kept, fix = fix_failing_sections(bad, report, drops_heading, title=TITLE)
    assert kept == bad and fix["rejected"][0]["reason"] == "titres H2/H3 modifiés"

    with_number = bad.replace("<h2>Les coûts cachés</h2>", "<h2>Les coûts cachés</h2><p>Le domaine coûte 12 € par an.</p>")
    loses_number = fix_failing_sections(with_number, validate_structure(with_number, TITLE), fixer, title=TITLE)[1]
    assert loses_number["rejected"][0]["reason"].startswith("chiffre(s) perdu(s)")


def test_h2_directly_followed_by_h3_fails():
    from app.services.seo.structure_validator import validate_structure

    bad = "<p>Intro courte.</p><h2>Choisir</h2><h3>Freelance</h3><p>Texte.</p><h3>Agence</h3><p>Texte.</p>"
    good = "<p>Intro courte.</p><h2>Choisir</h2><p>Cela dépend du budget.</p><h3>Freelance</h3><p>Texte.</p><h3>Agence</h3><p>Texte.</p>"
    rule = lambda r: next(x for x in r["rules"] if x["rule"] == "h2_lead_paragraph")
    assert not rule(validate_structure(bad, "Titre"))["passed"]
    assert rule(validate_structure(good, "Titre"))["passed"]


def test_h2_h3_helper_only_flags_direct_succession():
    from app.services.seo.helpers import detect_h2_directly_followed_by_h3

    assert detect_h2_directly_followed_by_h3("<h2>A</h2><h3>B</h3><p>x</p>")
    assert detect_h2_directly_followed_by_h3("<h2>A</h2><figure><img src='x'></figure><h3>B</h3>")
    assert not detect_h2_directly_followed_by_h3("<h2>A</h2><p>Réponse.</p><h3>B</h3><p>x</p>")


def test_isolated_h3_is_demoted_without_losing_text():
    from app.services.seo.structure_fixer import demote_isolated_h3

    html = ("<p>Intro.</p><h2>Prix</h2><p>Réponse.</p><h3>Ce que chaque option inclut</h3><p>Détail.</p>"
            "<h2>Devis</h2><p>R.</p><h3>Un</h3><p>a</p><h3>Deux</h3><p>b</p>")
    out = demote_isolated_h3(html)
    assert "<p><strong>Ce que chaque option inclut</strong></p>" in out
    assert out.count("<h3") == 2


def test_verbal_tics_limited_and_stripped_from_headings():
    from app.services.seo.structure_fixer import strip_heading_tics
    from app.services.seo.structure_validator import validate_structure

    html = ("<p>Concrètement, un CMS sépare deux choses.</p><h2>Fonctionnement</h2>"
            "<p>Concrètement, le contenu passe par une API. En effet, c'est simple.</p>")
    rule = next(r for r in validate_structure(html, "T")["rules"] if r["rule"] == "verbal_tics")
    assert not rule["passed"] and len(rule["violations"]) == 1
    assert strip_heading_tics("<h2>Comment fonctionne concrètement un CMS headless ?</h2>") == \
        "<h2>Comment fonctionne un CMS headless ?</h2>"


def test_duplicate_sections_and_paragraphs_are_removed():
    from app.services.seo.structure_fixer import remove_duplicates

    p = "<p>La confusion la plus courante est de croire qu'il faut être développeur pour l'utiliser.</p>"
    html = ("<p>Intro.</p><h2>Comment fonctionne un CMS headless ?</h2>" + p +
            "<h2>Comment fonctionne un CMS headless ?</h2><p>Autre version.</p><h2>Avantages</h2>" + p + "<p>Fin.</p>")
    out = remove_duplicates(html)
    assert out.count("<h2>Comment fonctionne") == 1 and "Autre version" not in out
    assert out.count("La confusion la plus courante") == 1 and "<h2>Avantages</h2>" in out


def test_body_faq_section_is_removed():
    from app.services.seo.structure_fixer import remove_body_faq

    html = "<p>Intro.</p><h2>Choisir</h2><p>A.</p><h2>Questions fréquentes sur le sujet</h2><p>Q ? R.</p><h2>Fin</h2><p>B.</p>"
    out = remove_body_faq(html)
    assert "Questions fréquentes" not in out and "<h2>Fin</h2>" in out
