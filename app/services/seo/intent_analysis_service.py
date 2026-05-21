from __future__ import annotations

from app.schemas.seo_workflow import IntentAnalysis, asdict


def analyze_intent(
    title: str,
    keyword: str,
    context_hint: str | None = None,
    category_name: str | None = None,
    idea_discovery: dict | None = None,
    project_context: dict | None = None,
) -> IntentAnalysis:
    title_lower = (title or "").lower()
    keyword_lower = (keyword or "").lower()

    analysis = IntentAnalysis(
        explicit_intent="informational",
        reader_real_question=title,
        expected_answer="",
        first_block_goal="",
    )

    comparison_markers = ["vs", "ou", "comparer", "différence", "meilleur", "choisir"]
    guide_markers = ["comment", "guide", "tutoriel", "étapes", "créer", "configurer"]
    question_markers = ["quoi", "qu'est-ce", "pourquoi", "quand", "quel", "comment"]

    for m in comparison_markers:
        if m in title_lower or m in keyword_lower:
            analysis.explicit_intent = "commercial"
            analysis.article_type = "comparison"
            analysis.first_block_goal = "Cadrer les critères de comparaison pour aider le lecteur à comprendre les différences essentielles."
            analysis.recommended_angle = "Comparer objectivement les options disponibles."
            break

    if analysis.article_type == "evergreen_information":
        for m in guide_markers:
            if m in title_lower or m in keyword_lower:
                analysis.explicit_intent = "informational"
                analysis.article_type = "guide"
                analysis.first_block_goal = "Donner une première action utile que le lecteur peut appliquer immédiatement."
                analysis.recommended_angle = "Guide pratique avec étapes concrètes."
                break

    if analysis.article_type == "evergreen_information":
        for m in question_markers:
            if m in title_lower or m in keyword_lower:
                analysis.explicit_intent = "informational"
                analysis.article_type = "simple_question"
                analysis.first_block_goal = "Répondre directement à la question principale du lecteur."
                analysis.recommended_angle = "Réponse claire et directe avec explications."

    if analysis.article_type == "evergreen_information":
        analysis.first_block_goal = "Présenter le sujet et donner une première information utile au lecteur."
        analysis.recommended_angle = "Contenu informatif complet et utile."

    analysis.implicit_intent = f"Le lecteur cherche des informations pratiques et fiables sur {keyword or title}"
    analysis.expected_answer = f"Un guide complet expliquant {keyword or title} avec des conseils pratiques"
    analysis.sub_questions = [
        f"Qu'est-ce que {keyword or title} ?",
        f"Pourquoi {keyword or title} est-il important ?",
        f"Comment appliquer {keyword or title} concrètement ?",
    ]
    analysis.what_to_avoid = [
        "Réponse trop générique sans conseil pratique",
        "Contenu trop technique sans explication",
        "Absence d'exemples concrets",
    ]

    return analysis


def analyze_intent_dict(
    title: str,
    keyword: str,
    context_hint: str | None = None,
    category_name: str | None = None,
    idea_discovery: dict | None = None,
    project_context: dict | None = None,
) -> dict:
    return asdict(analyze_intent(title, keyword, context_hint, category_name, idea_discovery, project_context))
