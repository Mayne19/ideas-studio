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

import json


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

    top_priorities: list[str] = []

    reader_question = intent_analysis.get("reader_real_question") or title or keyword
    top_priorities.append(
        f"Répondre à la question principale du lecteur : {reader_question}"
    )

    if editorial_angle.get("editorial_promise"):
        top_priorities.append(f"Tenir la promesse éditoriale : {editorial_angle['editorial_promise']}")

    angle = editorial_angle.get("main_angle")
    if angle:
        top_priorities.append(f"Traiter l'angle : {angle}")

    uncovered_questions = content_gaps.get("uncovered_questions") or []
    if uncovered_questions:
        top_priorities.append(
            "Couvrir les questions non traitées par le projet : "
            + "; ".join(uncovered_questions[:3])
        )
    uncovered_pains = content_gaps.get("uncovered_pain_points") or []
    if uncovered_pains:
        top_priorities.append(
            "Adresser ces douleurs non couvertes : " + "; ".join(uncovered_pains[:3])
        )

    if evidence_pack.get("evidence_items"):
        top_priorities.append(
            "Citer les faits et sources validés du dossier de preuves (pas de données inventées)."
        )

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
        "editorial_promise": editorial_angle.get("editorial_promise") or "",
        "main_angle": angle or "",
        "differentiation": editorial_angle.get("differentiation") or "",
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
    """Serialize le brief en texte lisible à injecter dans un prompt LLM."""
    lines: list[str] = ["=== BRIEF DE PRODUCTION ==="]
    if brief.get("title"):
        lines.append(f"Titre : {brief['title']}")
    if brief.get("keyword"):
        lines.append(f"Mot-clé principal : {brief['keyword']}")
    if brief.get("category_name"):
        lines.append(f"Catégorie : {brief['category_name']}")
    if brief.get("audience"):
        lines.append(f"Audience : {brief['audience']}")
    if brief.get("tone"):
        lines.append(f"Ton : {brief['tone']}")
    if brief.get("reader_level"):
        lines.append(f"Niveau du lecteur : {brief['reader_level']}")
    if brief.get("writing_style"):
        lines.append(f"Style d'écriture : {brief['writing_style']}")
    if brief.get("word_count_range"):
        lines.append(f"Volume cible : {brief['word_count_range']}")
    lines.append(f"Intention : {brief.get('intent', 'informational')} ({brief.get('article_type', 'evergreen_information')})")

    if brief.get("top_priorities"):
        lines.append("Priorités absolues :")
        for p in brief["top_priorities"]:
            lines.append(f"- {p}")

    if brief.get("secondary_keywords"):
        lines.append(f"Mots-clés secondaires : {', '.join(brief['secondary_keywords'])}")
    if brief.get("related_questions"):
        lines.append(f"Questions associées : {'; '.join(brief['related_questions'][:6])}")

    if brief.get("sections"):
        lines.append("Plan :")
        for section in brief["sections"]:
            heading = section.get("heading", "")
            purpose = section.get("purpose", "")
            key_points = section.get("key_points") or []
            lines.append(f"- H{section.get('level', 2)}: {heading} ({purpose})")
            if key_points:
                lines.append(f"  Points: {', '.join(key_points)}")

    if brief.get("evidence_items"):
        lines.append("Faits et sources validés à citer :")
        for item in brief["evidence_items"]:
            fact = item.get("fact", "")
            url = item.get("source_url", "")
            qual = item.get("source_quality") or item.get("reliability") or "unknown"
            lines.append(f"- {fact} ({qual}) — {url}")

    insights = brief.get("human_insights") or {}
    if insights.get("questions"):
        lines.append("Vraies questions d'utilisateurs :")
        lines.extend(f"- {q}" for q in insights["questions"])
    if insights.get("pain_points"):
        lines.append("Vraies douleurs d'utilisateurs :")
        lines.extend(f"- {p}" for p in insights["pain_points"])

    gaps = brief.get("content_gaps") or {}
    if gaps.get("suggestions"):
        lines.append("Manques de contenu à couvrir :")
        lines.extend(f"- {s}" for s in gaps["suggestions"])

    return "\n".join(lines)
