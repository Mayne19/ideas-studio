from __future__ import annotations

from app.schemas.seo_workflow import KeywordBrief, asdict


def build_keyword_brief(
    main_keyword: str,
    secondary_keywords: list[str] | None = None,
    related_questions: list[str] | None = None,
    intent_analysis: dict | None = None,
    research_brief: dict | None = None,
) -> KeywordBrief:
    brief = KeywordBrief(main_keyword=main_keyword)

    if secondary_keywords:
        brief.secondary_keywords = secondary_keywords
    else:
        words = main_keyword.split()
        if len(words) > 1:
            brief.secondary_keywords = [main_keyword] + [w for w in words if len(w) > 3]

    brief.long_tail_variants = [
        f"{main_keyword} guide",
        f"{main_keyword} conseils",
        f"{main_keyword} débutant",
    ]

    if related_questions:
        brief.related_questions = related_questions
    else:
        brief.related_questions = [
            f"Qu'est-ce que {main_keyword} ?",
            f"Comment utiliser {main_keyword} ?",
            f"Pourquoi {main_keyword} est important ?",
        ]

    brief.entities = [w for w in main_keyword.split() if w[0].isupper()] if main_keyword else []
    brief.synonyms = [main_keyword]
    brief.usage_strategy = f"Utiliser '{main_keyword}' naturellement dans le titre, l'introduction, et quelques headings. Intégrer les variantes longue traîne dans le développement."
    brief.keyword_risk_notes = []

    return brief


def build_keyword_brief_dict(
    main_keyword: str,
    secondary_keywords: list[str] | None = None,
    related_questions: list[str] | None = None,
    intent_analysis: dict | None = None,
    research_brief: dict | None = None,
) -> dict:
    return asdict(build_keyword_brief(main_keyword, secondary_keywords, related_questions, intent_analysis, research_brief))
