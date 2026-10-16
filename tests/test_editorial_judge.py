import json

from app.services.seo.editorial_judge import final_score, judge_article, parse_judgement
from app.services.seo.targeted_revision import guard_revision, locate_unit, revise_sections

ARTICLE = (
    "<p>Un site vitrine coûte entre 900 et 5 000 €.</p>"
    "<h2>Les prix par prestataire</h2><p>Un freelance facture 1 500 à 2 000 € en moyenne. "
    "Une agence demande davantage selon le projet et le niveau de finition attendu.</p>"
    "<h2>Les coûts cachés</h2><p>La rédaction coûte 150 à 400 € par page.</p>"
)
REPLY = {
    "criteria": {"intent": {"score": 14}, "accuracy": {"score": 25}, "sources": {"score": 12},
                 "information_gain": {"score": 10}, "depth": {"score": 8}, "clarity": {"score": 9},
                 "freshness": {"score": 4}},
    "blockers": [{"type": "contradiction", "section": "Les prix", "detail": "x"}, {"type": "style", "detail": "y"}],
    "section_fixes": [{"section": "Les prix par prestataire", "instructions": "Aligner la fourchette."}],
    "summary": "ok",
}


def test_parse_clamps_scores_and_filters_blockers():
    j = parse_judgement(json.dumps(REPLY), structure_report={"failed_hard_rules": []})
    assert j["criteria"]["accuracy"]["score"] == 20  # plafonné au maximum
    assert j["content_score"] == 14 + 20 + 12 + 10 + 8 + 9 + 4 + 5
    assert [b["type"] for b in j["blockers"]] == ["contradiction"]
    assert final_score(j, 80) == round(j["content_score"] + 4, 1)


def test_missing_component_becomes_blocker():
    report = {"failed_hard_rules": ["required_elements"],
              "rules": [{"rule": "required_elements", "passed": False, "label": "Tableau"}]}
    j = parse_judgement(json.dumps({**REPLY, "blockers": []}), structure_report=report)
    assert j["blockers"][0]["type"] == "missing_component"
    assert j["structure_points"] == 3


def test_judge_error_is_reported():
    out = judge_article(ARTICLE, lambda p, s, t: "pas du json", title="t", keyword="k", brief={},
                        facts=[], reference_figures=[])
    assert out == {"error": "réponse JSON invalide"}


def test_locate_unit_by_heading_and_intro():
    from app.services.seo.html_text_ops import split_units
    units = split_units(ARTICLE)
    assert locate_unit(units, "INTRODUCTION") == 0
    assert locate_unit(units, "Les coûts cachés") == 2
    assert locate_unit(units, "inconnue") is None


def test_guard_rejects_unverified_new_number_but_allows_fact_numbers():
    before = "<h2>Prix</h2><p>Un freelance facture 1 500 à 2 000 €.</p>"
    assert guard_revision(before, "<h2>Prix</h2><p>Un freelance facture 3 000 €.</p>", "") is not None
    assert guard_revision(before, "<h2>Prix</h2><p>Un freelance facture 900 à 5 000 €, 1 500 à 2 000 € en moyenne.</p>",
                          "900 à 5 000 €") is None
    assert guard_revision(before, "<h2>Autre</h2><p>Un freelance facture 1 500 à 2 000 €.</p>", "") == "titre H2 modifié"


def test_revise_sections_applies_guarded_rewrite():
    def call(prompt, step, temperature):
        return ("<h2>Les prix par prestataire</h2><p>Un freelance facture 900 à 5 000 €, 1 500 à 2 000 € en "
                "moyenne. Une agence demande davantage selon le projet et la finition.</p>")
    out, report = revise_sections(ARTICLE, REPLY["section_fixes"], call, facts_text="900 à 5 000 €")
    assert report["applied"] and "900 à 5 000 €, 1 500" in out
    assert "Les coûts cachés" in out
