"""A0 IdeaHandoff : le pré-brief de l'idée atteint l'intention et le brief."""
from app.services.production_brief_service import build_production_brief
from app.services.seo.idea_handoff import (
    apply_prebrief_to_idea,
    apply_prebrief_to_intent,
    apply_prebrief_to_keyword_brief,
    normalize_prebrief,
)

RAW = {
    "angle": "Le coût caché de la maintenance",
    "recommended_format": "comparatif",
    "main_answer_summary": "Webflow coûte plus cher au départ, WordPress plus cher à maintenir.",
    "search_questions": ["Webflow est-il plus cher que WordPress ?", "Peut-on migrer facilement ?"],
    "secondary_keywords": ["prix webflow", "hébergement wordpress"],
    "audience": "Indépendants",
}


def test_normalize_maps_idea_format_to_pipeline_format():
    prebrief = normalize_prebrief(RAW)
    assert prebrief["recommended_format"] == "comparison"
    assert prebrief["search_questions"][0].startswith("Webflow")
    assert normalize_prebrief(None) == {}


def test_heuristic_intent_takes_prebrief_format_answer_and_questions():
    prebrief = normalize_prebrief(RAW)
    intent = {"recommended_format": "explainer", "expected_answer": "", "sub_questions": []}
    merged = apply_prebrief_to_intent(intent, prebrief)
    assert merged["recommended_format"] == "comparison"
    assert merged["article_type"] == "comparison"
    assert merged["expected_answer"] == RAW["main_answer_summary"]
    assert merged["recommended_angle"] == RAW["angle"]
    assert "Peut-on migrer facilement ?" in merged["sub_questions"]


def test_refined_intent_keeps_its_own_format_and_answer():
    prebrief = normalize_prebrief(RAW)
    intent = {
        "refined_by_llm": True, "recommended_format": "how_to",
        "expected_answer": "Réponse LLM.", "sub_questions": ["Q LLM ?"],
    }
    merged = apply_prebrief_to_intent(intent, prebrief)
    assert merged["recommended_format"] == "how_to"
    assert merged["expected_answer"] == "Réponse LLM."
    assert merged["sub_questions"][0] == "Q LLM ?"
    assert len(merged["sub_questions"]) == 3


def test_production_brief_contains_idea_angle():
    prebrief = normalize_prebrief(RAW)
    intent = apply_prebrief_to_intent({"sub_questions": []}, prebrief)
    brief = build_production_brief(keyword="webflow ou wordpress", title="T", intent_analysis=intent)
    assert brief["main_angle"] == RAW["angle"]
    assert brief["idea_prebrief"]["angle"] == RAW["angle"]
    assert "Peut-on migrer facilement ?" in brief["sub_questions"]


def test_keywords_and_idea_merge_without_overwriting_user_values():
    prebrief = normalize_prebrief(RAW)
    kb = apply_prebrief_to_keyword_brief({"secondary_keywords": ["prix webflow"]}, prebrief)
    assert kb["secondary_keywords"] == ["prix webflow", "hébergement wordpress"]
    idea = apply_prebrief_to_idea({"angle": "Angle utilisateur", "secondary_keywords": []}, prebrief)
    assert idea["angle"] == "Angle utilisateur"
    assert idea["search_questions"] == RAW["search_questions"]
