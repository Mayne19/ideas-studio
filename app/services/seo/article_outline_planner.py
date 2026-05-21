from __future__ import annotations

from app.schemas.seo_workflow import ArticleOutline, asdict


def build_outline(
    title: str,
    keyword: str,
    intent_analysis: dict | None = None,
    research_brief: dict | None = None,
    keyword_brief: dict | None = None,
    editorial_angle: dict | None = None,
    article_type: str = "evergreen_information",
) -> ArticleOutline:
    outline = ArticleOutline(
        h1=title,
        intro_goal="Présenter le sujet et accrocher le lecteur",
        first_block_goal="",
        conclusion_title="Ce qu'il faut retenir",
        faq_planned=False,
        callouts_planned=False,
    )

    intent = intent_analysis or {}
    first_block = intent.get("first_block_goal", "")

    if article_type == "comparison":
        outline.first_block_goal = first_block or "Cadrer les critères de comparaison essentiels"
        outline.sections = [
            {"heading": "Pourquoi comparer ?", "level": 2, "purpose": "Expliquer l'importance de la comparaison", "key_points": ["Contexte", "Enjeux"], "reader_value": "Comprendre l'enjeu"},
            {"heading": "Critères de comparaison", "level": 2, "purpose": "Définir les critères", "key_points": ["Critère 1", "Critère 2", "Critère 3"], "reader_value": "Savoir quoi regarder"},
            {"heading": "Tableau comparatif", "level": 2, "purpose": "Comparer visuellement", "key_points": ["Points communs", "Différences"], "reader_value": "Voir les différences clairement"},
            {"heading": "Comment choisir ?", "level": 2, "purpose": "Aider à la décision", "key_points": ["Cas d'usage"], "reader_value": "Faire le bon choix"},
        ]
    elif article_type == "guide":
        outline.first_block_goal = first_block or "Donner une première action immédiate"
        outline.sections = [
            {"heading": "Qu'est-ce que c'est ?", "level": 2, "purpose": "Définir le concept", "key_points": [], "reader_value": "Comprendre les bases"},
            {"heading": "Étape 1 : Préparation", "level": 2, "purpose": "Première étape pratique", "key_points": [], "reader_value": "Savoir par où commencer"},
            {"heading": "Étape 2 : Exécution", "level": 2, "purpose": "Étape principale", "key_points": [], "reader_value": "Réaliser l'action principale"},
            {"heading": "Conseils et astuces", "level": 2, "purpose": "Bonnes pratiques", "key_points": ["Astuce 1", "Astuce 2"], "reader_value": "Optimiser son travail"},
        ]
    elif article_type == "simple_question":
        outline.first_block_goal = first_block or "Répondre directement à la question"
        outline.sections = [
            {"heading": "Réponse rapide", "level": 2, "purpose": "Donner la réponse directement", "key_points": ["Réponse principale"], "reader_value": "Obtenir la réponse rapidement"},
            {"heading": "Pourquoi ?", "level": 2, "purpose": "Expliquer le contexte", "key_points": ["Raisons"], "reader_value": "Comprendre le pourquoi"},
            {"heading": "Exemples concrets", "level": 2, "purpose": "Illustrer", "key_points": ["Exemple 1", "Exemple 2"], "reader_value": "Voir des cas réels"},
        ]
    else:
        outline.first_block_goal = first_block or "Donner une information utile au lecteur dès le début"
        outline.sections = [
            {"heading": f"Qu'est-ce que {keyword} ?", "level": 2, "purpose": "Définir le sujet", "key_points": [], "reader_value": "Comprendre les bases"},
            {"heading": f"Pourquoi {keyword} est important ?", "level": 2, "purpose": "Montrer l'importance", "key_points": [], "reader_value": "Saisir les enjeux"},
            {"heading": "Comment faire ?", "level": 2, "purpose": "Guide pratique", "key_points": [], "reader_value": "Savoir appliquer"},
            {"heading": "Bonnes pratiques", "level": 2, "purpose": "Conseils supplémentaires", "key_points": [], "reader_value": "Optimiser ses résultats"},
        ]

    return outline


def build_outline_dict(
    title: str,
    keyword: str,
    intent_analysis: dict | None = None,
    research_brief: dict | None = None,
    keyword_brief: dict | None = None,
    editorial_angle: dict | None = None,
    article_type: str = "evergreen_information",
) -> dict:
    return asdict(build_outline(title, keyword, intent_analysis, research_brief, keyword_brief, editorial_angle, article_type))
