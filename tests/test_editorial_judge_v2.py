"""Juge v2 : grille sur 100, mesures du code, plafonds de fautes graves."""
import json

from app.services.seo.editorial_judge_v2 import (CAP_ONE_GRAVE, CAP_TWO_GRAVE, MODEL_CRITERIA, apply_caps,
                                                 ensure_html, judge_v2, measurements)

ARTICLE = ("<p>Si vous venez d'atterrir à Tokyo, sortez au soleil le matin et couchez-vous à l'heure locale. "
           "Votre horloge interne se recale d'environ une heure par jour.</p>"
           "<h2>Pourquoi la lumière compte</h2><p>La lumière du matin avance votre horloge interne, ce qui vous "
           "aide à vous endormir plus tôt le soir.</p>")


def reply(scores, grave=()):
    return json.dumps({"criteria": {k: {"score": v, "evidence": "preuve"} for k, v in scores.items()},
                       "grave_faults": list(grave), "summary": "ok"})


def full_scores():
    return {k: pts for k, (pts, _d) in MODEL_CRITERIA.items()}


def test_grid_totals_100_and_perfect_article_scores_100():
    assert sum(p for p, _ in MODEL_CRITERIA.values()) == 90
    out = judge_v2(ARTICLE, lambda p, s, t: reply(full_scores()), title="Décalage horaire", keyword="décalage")
    assert out["total"] == 100 and out["caps"] == {"grave_faults": 0, "cap": None}
    assert set(out["criteria"]) == set(MODEL_CRITERIA) | {"seo", "form"}
    assert out["status"] == "non étalonné"


def test_grave_faults_cap_the_score():
    one = [{"type": "false_fact", "passage": "sortez au soleil le matin", "detail": "y"}]
    two = one + [{"type": "central_contradiction", "passage": "La lumière du matin avance", "detail": "b"}]
    assert apply_caps(97, one)[0] == CAP_ONE_GRAVE == 85
    assert apply_caps(97, two)[0] == CAP_TWO_GRAVE == 75
    assert apply_caps(70, one)[0] == 70
    out = judge_v2(ARTICLE, lambda p, s, t: reply(full_scores(), two + [{"type": "style", "passage": "z"}]),
                   title="Décalage horaire")
    assert out["total"] == 75 and out["raw_total"] == 100 and len(out["grave_faults"]) == 2


def defects_reply(defects, coherence=()):
    return json.dumps({"coherence": list(coherence), "grave_faults": [], "summary": "ok",
                       "criteria": {k: {"defects": defects.get(k, []), "evidence": "preuve"} for k in MODEL_CRITERIA}})


def test_scores_are_deduced_from_defects_and_bad_json_is_an_error():
    major = {"severity": "majeur", "passage": "sortez au soleil le matin", "detail": "y"}
    out = judge_v2(ARTICLE, lambda p, s, t: defects_reply({
        "accuracy_sources": [major, {"severity": "mineur", "passage": "La lumière du matin avance", "detail": "b"}],
        "faq": [major] * 10, "tone": [{"severity": "inconnu", "passage": "", "detail": ""}]},
        coherence=[{"rule": "1 h par jour", "passage": "chaque matinée", "detail": "faux vers l'ouest"}]),
        title="Décalage horaire")
    assert out["criteria"]["accuracy_sources"]["score"] == 13.0   # 20 - 6 - 1
    assert out["criteria"]["faq"]["score"] == 0.0 and out["criteria"]["tone"]["score"] == 5.0
    assert out["coherence"][0]["passage"] == "chaque matinée"
    assert "error" in judge_v2(ARTICLE, lambda p, s, t: "pas de json")


def test_code_defects_lower_readability_and_accuracy():
    from app.services.seo.editorial_judge_v2 import code_defects

    measured = {"quote_faults": ["Citations absentes : « une phrase inventée de cinq mots » | « autre citation là »"],
                "balance_faults": ["Le domaine vidal.fr porte 10 faits sur 17"], "mention_faults": ["Source nommée 12 fois"],
                "meta_commentary": ["cet article"], "choppy_runs": 1}
    defects = code_defects(measured)
    assert [d["severity"] for d in defects["accuracy_sources"]] == ["mineur", "mineur", "moyen"]
    assert [d["severity"] for d in defects["readability"]] == ["moyen", "moyen", "mineur"]
    out = judge_v2("<p>Dans cet article, nous retenons une règle simple pour le lecteur.</p>",
                   lambda p, s, t: defects_reply({}), title="T")
    assert out["measurements"]["meta_commentary"] and out["criteria"]["readability"]["score"] == 12.8


def test_code_measures_form_choppy_sentences_and_markdown():
    measured = measurements("<p>Il fait jour. Vous êtes las. Le corps hésite. Tout — vraiment tout — change.</p>",
                            title="T")
    assert measured["choppy_runs"] >= 1 and measured["form_faults"]
    assert ensure_html("## Titre\n\nUn paragraphe.").startswith("<h2>")
    seen = []
    out = judge_v2("# Mon titre\n\nUn paragraphe sans tiret.\n\n## Une section\n\nDu texte.",
                   lambda p, s, t: seen.append(p) or reply(full_scores()))
    assert out["criteria"]["form"]["score"] == 5 and "Titre : Mon titre" in seen[0]


def test_prompt_contains_measures_facts_and_competitors():
    seen = []
    judge_v2(ARTICLE, lambda p, s, t: seen.append(p) or reply(full_scores()),
             facts=[{"value": "1 h", "quote": "une heure par jour", "source_url": "https://cdc.gov/x"}],
             competitors=["lonelyplanet.fr"], faq=[{"question": "Q ?", "answer": "R."}])
    prompt = seen[0]
    assert "une heure par jour" in prompt and "lonelyplanet.fr" in prompt and "Q ?" in prompt
    assert "mots par phrase" in prompt and "calcul montré" in prompt


def test_without_facts_the_judge_does_not_require_verbatim_quotes():
    seen = []
    out = judge_v2("# Basilic\n\nSi votre basilic meurt, arrosez moins. Selon [l'Inrae](https://inrae.fr/x), "
                   "il aime la chaleur.", lambda p, s, t: seen.append(p) or reply(full_scores()))
    assert "aucune liste fournie" in seen[0] and "N'exige aucune citation mot pour mot" in seen[0]
    assert out["measurements"]["quote_faults"] == [] and out["measurements"]["balance_faults"] == []


def test_criteria_carry_the_house_writing_rules():
    intro, readability = MODEL_CRITERIA["introduction"][1], MODEL_CRITERIA["readability"][1]
    assert "moment que vit le lecteur" in intro and "découle logiquement" in intro and "gain précis" in intro
    assert "phrase isolée" in readability and "cet article" in readability and "Voici" in readability


def test_defects_without_a_real_passage_are_ignored_and_scores_floor_at_zero():
    invented = {"severity": "majeur", "passage": "une phrase qui n'existe nulle part", "detail": "inventé"}
    real = {"severity": "majeur", "passage": "Votre horloge interne se recale", "detail": "réel"}
    empty = {"severity": "majeur", "passage": "", "detail": "sans passage"}
    out = judge_v2(ARTICLE, lambda p, s, t: defects_reply({"intent": [invented, empty], "faq": [real] * 9,
                                                           "structure": [real]}), title="Décalage horaire")
    assert out["criteria"]["intent"]["score"] == 10 and out["criteria"]["intent"]["defects"] == []
    assert out["criteria"]["faq"]["score"] == 0.0
    assert out["criteria"]["structure"]["score"] == 7.0
    perfect = judge_v2(ARTICLE, lambda p, s, t: defects_reply({}), title="Décalage horaire")
    assert perfect["raw_total"] == 100 and all(not c.get("defects") for c in perfect["criteria"].values()
                                               if "defects" in c)


def test_grave_faults_need_a_real_passage_and_ce_guide_is_not_meta_commentary():
    invented = [{"type": "false_fact", "passage": "un passage absent de l'article", "detail": "inventé"}]
    out = judge_v2(ARTICLE, lambda p, s, t: reply(full_scores(), invented), title="Décalage horaire")
    assert out["grave_faults"] == [] and out["caps"]["cap"] is None and out["total"] == 100
    measured = judge_v2("<p>Ce guide vous montre quoi faire dès l'arrivée, sans détour.</p>",
                        lambda p, s, t: defects_reply({}), title="T")["measurements"]
    assert measured["meta_commentary"] == []
