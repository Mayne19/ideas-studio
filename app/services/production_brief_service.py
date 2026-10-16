"""ProductionBriefService — Verrouille le brief final transmis au writer.

Consolide en un seul document structuré toutes les briques produites en amont
du pipeline : contexte projet, analyse d'intention, brief de mot-clé, brief de
recherche, angle éditorial, plan, insights humains, dossier de preuves, manques
de contenu et indications de volume.

Avant : le writer recevait des blocs épars du contexte (tone, reader_level,
human_insights, outline...), sans synthèse ni priorités claires. Ce service
produit un brief ordonné et complet, avec une section d'instructions prioritaires
qui résume ce qu'il faut absolument traiter.
"""
from __future__ import annotations



def build_production_brief(
    *,
    keyword: str = "",
    title: str = "",
    category_name: str | None = None,
    project_context: dict | None = None,
    intent_analysis: dict | None = None,
    keyword_brief: dict | None = None,
    research_brief: dict | None = None,
    evidence_pack: dict | None = None,
    editorial_angle: dict | None = None,
    outline: dict | None = None,
    human_insights: dict | None = None,
    content_gaps: dict | None = None,
    word_count_range: str | None = None,
    audience: str | None = None,
    tone: str | None = None,
    reader_level: str | None = None,
    writing_style: str | None = None,
) -> dict:
    """Assemble un brief de production unique pour le writer."""
    project_context = project_context or {}
    intent_analysis = intent_analysis or {}
    keyword_brief = keyword_brief or {}
    research_brief = research_brief or {}
    evidence_pack = evidence_pack or {}
    editorial_angle = editorial_angle or {}
    outline = outline or {}
    human_insights = human_insights or {}
    content_gaps = content_gaps or {}

    reader_question = intent_analysis.get("reader_real_question") or title or keyword
    idea_prebrief = intent_analysis.get("idea_prebrief") or {}
    angle = editorial_angle.get("main_angle") or idea_prebrief.get("angle")
    top_priorities: list[str] = [f"Répondre à la question réelle du lecteur : {reader_question}"]
    if intent_analysis.get("expected_answer"):
        top_priorities.append(f"Réponse attendue : {intent_analysis['expected_answer']}")

    intent = intent_analysis.get("explicit_intent") or "informational"
    article_type = intent_analysis.get("article_type") or "evergreen_information"
    commercial_score = intent_analysis.get("commercial_intent_score") or 0.0

    return {
        "keyword": keyword,
        "title": title,
        "category_name": category_name,
        "audience": audience or project_context.get("target_audience") or "Grand public",
        "tone": tone or project_context.get("tone") or "",
        "reader_level": reader_level or project_context.get("reader_level") or "",
        "writing_style": writing_style or project_context.get("writing_style") or "",
        "intent": intent,
        "article_type": article_type,
        "commercial_intent_score": commercial_score,
        "sub_questions": intent_analysis.get("sub_questions") or [],
        "reader_real_question": reader_question,
        "expected_answer": intent_analysis.get("expected_answer") or "",
        "recommended_format": intent_analysis.get("recommended_format") or "",
        "must_include": intent_analysis.get("must_include") or [],
        "must_avoid": intent_analysis.get("must_avoid") or intent_analysis.get("what_to_avoid") or [],
        "editorial_promise": editorial_angle.get("editorial_promise") or "",
        "main_angle": angle or "",
        "differentiation": editorial_angle.get("differentiation") or "",
        "idea_prebrief": idea_prebrief,
        "word_count_range": word_count_range,
        "top_priorities": top_priorities,
        "secondary_keywords": keyword_brief.get("secondary_keywords") or [],
        "long_tail_variants": keyword_brief.get("long_tail_variants") or [],
        "related_questions": keyword_brief.get("related_questions") or [],
        "sections": outline.get("sections") or [],
        "intro_goal": outline.get("intro_goal") or "",
        "first_block_goal": outline.get("first_block_goal") or "",
        "conclusion_title": outline.get("conclusion_title") or "",
        "faq_planned": bool(outline.get("faq_planned")),
        "callouts_planned": bool(outline.get("callouts_planned")),
        "evidence_items": evidence_pack.get("evidence_items") or [],
        "human_insights": {
            "questions": (human_insights.get("questions") or [])[:10],
            "pain_points": (human_insights.get("pain_points") or [])[:8],
            "real_examples": (human_insights.get("real_examples") or [])[:6],
            "objections": (human_insights.get("objections") or [])[:6],
            "positive_experiences": (human_insights.get("positive_experiences") or [])[:6],
            "debates": (human_insights.get("debates") or [])[:5],
            "vocabulary": (human_insights.get("vocabulary") or [])[:8],
        },
        "content_gaps": {
            "suggestions": content_gaps.get("suggestions") or [],
            "uncovered_angles": (content_gaps.get("uncovered_angles") or [])[:5],
        },
        "competitor_angles": (research_brief.get("competitor_angles") or [])[:6],
        "field_signals": (research_brief.get("field_signals") or [])[:6],
        "limitations": (research_brief.get("limitations") or [])[:5],
        "sources_consulted": [
            {"url": s.get("url", ""), "title": s.get("title", "")}
            for s in (research_brief.get("sources_consulted") or [])[:8]
        ],
    }


def build_production_brief_dict(**kwargs) -> dict:
    return build_production_brief(**kwargs)


def production_brief_to_text(brief: dict) -> str:
    """Sérialise le brief en un bloc unique pour le prompt du writer : la
    question du lecteur et la réponse attendue d'abord, puis le plan. Le plan
    n'est affiché qu'ici (le prompt du writer ne le répète pas). Les consignes
    de longueur et de style vivent dans le prompt du writer, pas ici."""
    lines: list[str] = ["=== BRIEF ==="]
    for label, key in (
        ("Titre", "title"), ("Mot-clé principal", "keyword"), ("Audience", "audience"),
        ("Ton", "tone"), ("Niveau du lecteur", "reader_level"), ("Style", "writing_style"),
        ("Format", "recommended_format"), ("Angle", "main_angle"),
    ):
        if brief.get(key):
            lines.append(f"{label} : {brief[key]}")

    lines.append(f"Question réelle du lecteur : {brief.get('reader_real_question') or brief.get('title', '')}")
    if brief.get("expected_answer"):
        lines.append(f"Réponse attendue : {brief['expected_answer']}")
    if brief.get("must_include"):
        lines.append("À inclure :")
        lines.extend(f"- {x}" for x in brief["must_include"])
    if brief.get("must_avoid"):
        lines.append("À éviter :")
        lines.extend(f"- {x}" for x in brief["must_avoid"])
    questions = list(brief.get("sub_questions") or [])
    for q in brief.get("related_questions") or []:
        if q not in questions:
            questions.append(q)
    if questions:
        lines.append(f"Questions de suivi possibles : {'; '.join(questions[:6])}")
    if brief.get("secondary_keywords"):
        lines.append(f"Mots-clés secondaires : {', '.join(brief['secondary_keywords'][:8])}")

    if brief.get("sections"):
        lines.append("Plan :")
        for section in brief["sections"]:
            purpose = section.get("purpose", "")
            line = f"- H{section.get('level', 2)} : {section.get('heading', '')}"
            lines.append(f"{line} ({purpose})" if purpose else line)
            if section.get("key_points"):
                lines.append(f"  Points : {', '.join(str(k) for k in section['key_points'])}")

    if brief.get("evidence_items"):
        lines.append(
            "Faits disponibles dans les sources (optionnels : seulement s'ils aident à répondre, "
            "sans les déformer) :"
        )
        for item in brief["evidence_items"]:
            line = f"- {item.get('fact', '')} : {item.get('source_url', '')}"
            if item.get("figure"):
                line += f" [chiffre : {item['figure']}]"
            if item.get("figure_context"):
                line += f" ({item['figure_context']})"
            lines.append(line)

    gaps = brief.get("content_gaps") or {}
    if gaps.get("suggestions"):
        lines.append("Pistes complémentaires (seulement si elles servent la question) :")
        lines.extend(f"- {s}" for s in gaps["suggestions"][:4])

    return "\n".join(lines)
