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


def test_unverified_figures_flags_only_unknown_amounts():
    from app.services.seo.targeted_revision import figure_fixes, unverified_figures

    html = ("<p>Un site coûte 900 à 5 000 €.</p><h2>Prix</h2><p>Hébergement mutualisé : 5-15 $/mois. "
            "Un freelance facture 1 500 à 2 000 €. Comptez 2 ans et 3 devis.</p>")
    found = unverified_figures(html, "900 à 5 000 € ; 1 500 à 2 000 €")
    assert list(found) == [1] and "15 $" in found[1][0]
    assert figure_fixes(html, "900 à 5 000 € ; 1 500 à 2 000 €")[0]["section"] == "Prix"


def test_locate_unit_accepts_digest_label_and_small_numbers_pass_guard():
    from app.services.seo.html_text_ops import split_units
    units = split_units(ARTICLE)
    assert locate_unit(units, "SECTION « Les coûts cachés »") == 2
    before = "<h2>Prix</h2><p>Un freelance facture 1 500 à 2 000 €.</p>"
    assert guard_revision(before, "<h2>Prix</h2><p>En 2 étapes, un freelance facture 1 500 à 2 000 € en 2026.</p>", "") is None


def test_guard_rejects_meta_commentary_leak():
    before = "<h2>Architecture</h2><p>Payload CMS expose une API REST consommée par Next.js.</p>"
    after = ("<h2>Architecture</h2><p>Payload CMS expose une API REST consommée par Next.js. Cette architecture "
             "dépasse les simples mentions théoriques de React.</p>")
    assert guard_revision(before, after, "").startswith("commentaire interne")


def test_guard_rejects_revision_that_duplicates_a_section():
    before = "<h2>Définition</h2><p>Un CMS headless sépare le contenu de son affichage.</p>"
    after = before + "<h2>Comment fonctionne un CMS headless ?</h2><p>Le contenu passe par une API.</p>"
    assert guard_revision(before, after, "") == "sections H2 ajoutées ou supprimées"


def test_judge_prompt_accepts_calculated_figures_but_checks_math():
    from app.services.seo.editorial_judge import build_judge_prompt

    prompt = build_judge_prompt("<p>x</p>", title="t", keyword="k", brief={}, facts=[], reference_figures=[])
    assert "chiffre calculé à partir des faits" in prompt and "un calcul faux est un blocage contradiction" in prompt


def test_calculated_and_example_figures_are_not_flagged():
    from app.services.seo.targeted_revision import unverified_figures

    html = ("<p>Intro.</p><h2>Coût</h2><p>Typeform coûte 39 $ pour 100 réponses, soit 0,39 $ par réponse. "
            "Prenons un loyer de 600 € par mois. Un freelance facture 3 200 €.</p>")
    found = unverified_figures(html, "Typeform coûte 39 $ pour 100 réponses")
    assert found == {1: ["Un freelance facture 3 200 €."]}


def test_exemption_is_strict_for_population_figures_and_examples():
    from app.services.seo.targeted_revision import unverified_figures

    def flagged(sentence, allowed=""):
        return bool(unverified_figures(f"<p>Intro.</p><h2>S</h2><p>{sentence}</p>", allowed))

    assert flagged("Par exemple, 73 % des Français abandonnent leur budget.")
    assert not flagged("Prenons un loyer de 600 € par mois.")
    assert not flagged("Le forfait revient à soit 0,39 $ par réponse.", "Typeform coûte 39 $ pour 100 réponses")
    assert flagged("Selon une étude, cela coûte 0,39 $ par réponse.", "39 $ pour 100 réponses")
    assert flagged("Prenons un loyer de 613 € par mois.")
