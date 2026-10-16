import json

from app.services.seo.figure_reconciler import format_reference_figures, reconcile_figures

FACTS = [
    {"fact_id": "F1", "claim": "Un site vitrine pro coûte 900 à 5 000 €", "figure": "900 à 5 000 €", "source_tier": "strong"},
    {"fact_id": "F2", "claim": "Un freelance facture 1 500 à 2 000 €", "figure": "1 500 à 2 000 €"},
    {"fact_id": "F3", "claim": "Webflow est simple", "figure": ""},
]


def test_reconcile_keeps_only_known_fact_ids():
    reply = json.dumps({"figures": [
        {"quantity": "prix freelance", "reference": "900 à 5 000 €", "fact_ids": ["F1", "F2", "F9"]},
        {"quantity": "inventé", "reference": "42 €", "fact_ids": ["F9"]},
    ]})
    calls = []
    report = reconcile_figures(FACTS, "site vitrine", lambda p, s, t: calls.append(p) or reply)
    assert report["figures"] == [{"quantity": "prix freelance", "reference": "900 à 5 000 €", "fact_ids": ["F1", "F2"]}]
    assert "F3" not in calls[0]
    assert "Chiffres de référence" in format_reference_figures(report["figures"])


def test_no_call_without_enough_figures():
    report = reconcile_figures(FACTS[:1], "x", lambda p, s, t: (_ for _ in ()).throw(AssertionError()))
    assert report["figures"] == []


def test_call_failure_is_reported():
    def boom(p, s, t):
        raise RuntimeError("timeout")

    report = reconcile_figures(FACTS, "x", boom)
    assert report["figures"] == [] and "timeout" in report["error"]
