import json

from app.services.seo.information_gain_designer import (
    assign_gain_elements, check_calculations, design_information_gain, format_gain_block, validate_design,
)

FACTS = [{"fact_id": "F1", "claim": "Typeform coûte 39 $ par mois pour 100 réponses", "figure": "39 $"}]
GOOD = {
    "direct_answer": "Deux outils suffisent.", "trap": "Typeform bloque à 10 réponses.", "promise": "Ce comparatif…",
    "decision_tool": {"type": "tableau de décision", "columns": ["Besoin", "Outil"], "rows": [["Gratuit", "Tally"]]},
    "worked_example": {"situation": "100 réponses", "calculation": ["39 / 100 = 0,39"], "result": "0,39 $ par réponse"},
    "surprising_fact": {"fact": "…", "fact_id": "F1"},
    "common_mistakes": ["Oublier la limite de réponses"],
}


def test_calculations_checked():
    assert check_calculations(["39 / 100 = 0,39", "1 478 + 522 = 2 000", "68 % de 1 500 = 1 020"]) == []
    assert check_calculations(["39 / 100 = 3,9"]) == ["39 / 100 = 3,9"]


def test_unknown_fact_id_is_dropped():
    design, problems = validate_design({**GOOD, "surprising_fact": {"fact": "x", "fact_id": "F99"}}, {"F1"})
    assert design["surprising_fact"] is None and problems


def test_wrong_calculation_retried_then_removed():
    bad = {**GOOD, "worked_example": {"situation": "s", "calculation": ["39 / 100 = 3,9"], "result": "r"}}
    calls = []
    report = design_information_gain("k", "q", FACTS, [], lambda p, s, t: calls.append(1) or json.dumps(bad))
    assert len(calls) == 2 and report["design"]["worked_example"] is None


def test_failure_falls_back_without_error():
    def boom(p, s, t):
        raise RuntimeError("timeout")

    assert design_information_gain("k", "q", FACTS, [], boom)["design"] is None


def test_elements_assigned_to_matching_sections():
    design, _ = validate_design(GOOD, {"F1"})
    out = assign_gain_elements(design, ["Comment ça marche", "Combien ça coûte", "Quel outil choisir", "Les erreurs à éviter"])
    assert "decision_tool" in out[2] and "worked_example" in out[1] and "common_mistakes" in out[3]
    assert out["intro"]["promise"] == "Ce comparatif…"
    assert "0,39" in format_gain_block(out[1])
