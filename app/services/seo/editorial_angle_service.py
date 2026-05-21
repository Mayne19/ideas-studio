from __future__ import annotations

from app.schemas.seo_workflow import EditorialAngle, asdict


def define_editorial_angle(
    title: str,
    keyword: str,
    intent_analysis: dict | None = None,
    research_brief: dict | None = None,
    category_name: str | None = None,
) -> EditorialAngle:
    intent = intent_analysis or {}
    article_type = intent.get("article_type", "evergreen_information")

    angle = EditorialAngle(
        editorial_promise=f"Un article complet et utile sur {keyword}",
        main_angle=f"Expliquer {keyword} de manière pratique et accessible",
        reader_benefit=f"Le lecteur comprendra {keyword} et pourra l'appliquer concrètement",
        differentiation="Approche pratique avec conseils concrets et exemples réels",
        tone="Direct, clair et utile",
    )

    if article_type == "comparison":
        angle.main_angle = f"Comparer objectivement les options liées à {keyword}"
        angle.reader_benefit = "Le lecteur pourra choisir en connaissance de cause"
        angle.differentiation = "Analyse équilibrée avec critères de choix clairs et concrets"

    if article_type == "guide":
        angle.main_angle = f"Guide étape par étape sur {keyword}"
        angle.reader_benefit = "Le lecteur pourra appliquer immédiatement les étapes"
        angle.differentiation = "Étapes actionnables avec conseils de terrain"

    if article_type == "simple_question":
        angle.main_angle = f"Réponse directe et complète à la question sur {keyword}"
        angle.reader_benefit = "Le lecteur obtient une réponse claire et utile"

    angle.eeat_opportunities = [
        "Ajouter des sources fiables",
        "Inclure des exemples concrets",
        "Citer des données vérifiables si disponibles",
        "Montrer des cas pratiques d'application",
    ]

    return angle


def define_editorial_angle_dict(
    title: str,
    keyword: str,
    intent_analysis: dict | None = None,
    research_brief: dict | None = None,
    category_name: str | None = None,
) -> dict:
    return asdict(define_editorial_angle(title, keyword, intent_analysis, research_brief, category_name))
