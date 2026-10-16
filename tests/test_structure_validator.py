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
