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


def refine_keyword_brief_with_research(
    base: dict,
    main_keyword: str,
    research_brief: dict | None = None,
    intent_analysis: dict | None = None,
    db=None,
    project_id: str | None = None,
) -> dict:
    """Enrichit le brief mots-clés heuristique avec une vraie recherche de
    mots-clés LLM appuyée sur les résultats SERP du research brief. Point 8 du
    pipeline : l'heuristique ne produit que des variantes stéréotypées
    ('keyword guide', 'keyword conseils', 'keyword débutant') ; ici l'agent
    keyword_research extrait les mots-clés secondaires, variantes longue traîne,
    questions et entités réellement présents dans les pages classées. Repli
    sur le brief de base si le provider est indisponible — jamais bloquant."""
    result = dict(base)
    if db is None:
        return result
    try:
        from app.services.agents.agent_router import get_router
    except Exception:
        return result
    router = get_router(db)
    if router is None:
        return result
    try:
        provider = router.get_provider("keyword_research", project_id=project_id)
        if provider is None or provider.is_mock:
            return result
    except Exception:
        return result

    sources = (research_brief or {}).get("sources_consulted") or []
    serp_context = ""
    if sources:
        lines = []
        for source in sources[:12]:
            if isinstance(source, dict):
                snippet = (source.get("snippet") or "")[:200]
                lines.append(f"- {source.get('title', '')} — {snippet}")
        serp_context = "\n".join(lines)

    intent_type = (intent_analysis or {}).get("explicit_intent") or "informational"
    prompt = (
        "Fais une vraie recherche de mots-clés pour cet article à partir des résultats Google "
        "réels (SERP) ci-dessous. Extrais : secondary_keywords (mots-clés secondaires pertinents "
        "réellement présents dans les pages classées, 4 à 8), long_tail_variants (variantes "
        "longue traîne avec modificateurs réalistes), related_questions (questions réellement "
        "posées, issues des titres/snippets, 4 à 6), entities (marques, outils, organismes, "
        "personnes, lieux cités par les concurrents), synonyms (tournures équivalentes naturelles).\n\n"
        f"Mot-clé principal : {main_keyword}\nIntention : {intent_type}\n\n"
        + (f"Résultats SERP réels :\n{serp_context}\n\n" if serp_context else "Aucun résultat SERP disponible.\n\n")
        + "Réponds UNIQUEMENT avec un JSON valide :\n"
        '{"secondary_keywords": ["...", "..."], "long_tail_variants": ["...", "..."], '
        '"related_questions": ["...", "..."], "entities": ["...", "..."], "synonyms": ["...", "..."], '
        '"keyword_risk_notes": ["...", "..."]}'
    )
    try:
        enriched = provider.generate_json(prompt, schema_hint="json keyword research object")
    except Exception:
        return result
    if not isinstance(enriched, dict):
        return result

    for list_field in ("secondary_keywords", "long_tail_variants", "related_questions", "entities", "synonyms", "keyword_risk_notes"):
        value = enriched.get(list_field)
        if isinstance(value, list) and value:
            cleaned = [str(x).strip() for x in value if str(x).strip()]
            if cleaned:
                result[list_field] = cleaned[:10]
    if result.get("secondary_keywords") and main_keyword not in result["secondary_keywords"]:
        result["secondary_keywords"].insert(0, main_keyword)
    result["usage_strategy"] = (
        f"Utiliser '{main_keyword}' naturellement dans le titre, l'introduction et quelques "
        "headings ; intégrer les variantes longue traîne et les questions réelles de la SERP "
        "dans le développement et les sous-titres."
    )
    result["refined_by_llm"] = True
    return result
