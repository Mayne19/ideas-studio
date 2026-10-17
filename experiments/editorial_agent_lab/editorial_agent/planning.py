"""Contrôles du dossier éditorial avant rédaction."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from .models import ArticlePlan, CompetitorPage, FactRecord, ReaderIntent, ValidationIssue


def _domain(url: str) -> str:
    return (urlsplit(url).hostname or "").lower().removeprefix("www.")


def _tokens(value: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"[A-Za-zÀ-ÿ0-9]+", value or "")
        if len(token) > 3
    }


def validate_competitor_dossier(
    competitors: list[CompetitorPage],
    *,
    expected: int = 3,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if len(competitors) < expected:
        issues.append(ValidationIssue(
            code="not_enough_competitors",
            message=f"Le dossier doit contenir {expected} concurrents lisibles.",
            blocking=True,
            location="competitors",
        ))
    for index, competitor in enumerate(competitors):
        if not competitor.content.strip():
            issues.append(ValidationIssue(
                code="competitor_not_read",
                message="Le concurrent n'a pas de contenu lisible.",
                blocking=True,
                location=f"competitors[{index}]",
            ))
        if not competitor.strengths:
            issues.append(ValidationIssue(
                code="missing_competitor_strengths",
                message="Les points forts du concurrent ne sont pas analysés.",
                blocking=True,
                location=f"competitors[{index}].strengths",
            ))
        if not competitor.weaknesses and not competitor.missing_topics:
            issues.append(ValidationIssue(
                code="missing_competitor_weaknesses",
                message="Les faiblesses ou les lacunes du concurrent ne sont pas analysées.",
                blocking=True,
                location=f"competitors[{index}].weaknesses",
            ))
    return issues


def validate_source_diversity(
    facts: list[FactRecord],
    competitor_urls: list[str] | None = None,
    *,
    minimum_domains: int = 3,
) -> list[ValidationIssue]:
    competitor_domains = {_domain(url) for url in competitor_urls or []}
    domains = {
        _domain(str(fact.source_url))
        for fact in facts
        if fact.verified and _domain(str(fact.source_url)) not in competitor_domains
    }
    issues: list[ValidationIssue] = []
    if len(domains) < minimum_domains:
        issues.append(ValidationIssue(
            code="insufficient_source_diversity",
            message=f"Le registre contient {len(domains)} domaine(s) admissible(s), il en faut au moins {minimum_domains}.",
            blocking=True,
            location="facts",
        ))
    if facts:
        counts = {_domain(str(fact.source_url)): 0 for fact in facts}
        for fact in facts:
            counts[_domain(str(fact.source_url))] += 1
        dominant_domain, dominant_count = max(counts.items(), key=lambda item: item[1])
        if dominant_count * 2 > len(facts):
            issues.append(ValidationIssue(
                code="dominant_source",
                message=f"La source {dominant_domain} porte plus de la moitié des faits.",
                blocking=True,
                location="facts",
            ))
    return issues


def validate_plan_coverage(plan: ArticlePlan) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    body_fact_ids: set[str] = set()
    for index, section in enumerate(plan.sections):
        if not section.heading.strip() or not section.promise.strip() or not section.reader_question.strip():
            issues.append(ValidationIssue(
                code="incomplete_section_contract",
                message="Une section n'a pas de titre, de promesse ou de question lecteur.",
                blocking=True,
                location=f"sections[{index}]",
            ))
        body_fact_ids.update(section.facts_to_use)
        for h3_index, heading in enumerate(section.h3_sections):
            if not heading.strip():
                issues.append(ValidationIssue(
                    code="empty_h3_contract",
                    message="Un H3 est présent dans le plan sans contenu défini.",
                    blocking=True,
                    location=f"sections[{index}].h3_sections[{h3_index}]",
                ))

    for index, faq in enumerate(plan.faq):
        if not faq.question.strip() or not faq.reason_not_in_article.strip():
            issues.append(ValidationIssue(
                code="incomplete_faq_contract",
                message="Chaque question FAQ doit expliquer pourquoi elle n'est pas dans le corps.",
                blocking=True,
                location=f"faq[{index}]",
            ))
        if body_fact_ids.intersection(faq.facts_to_use):
            issues.append(ValidationIssue(
                code="faq_fact_overlap",
                message="La FAQ réutilise un fait prévu dans le corps sans justification distincte.",
                blocking=True,
                location=f"faq[{index}]",
            ))
        for section_index, section in enumerate(plan.sections):
            overlap = _tokens(faq.question) & _tokens(section.reader_question)
            if len(overlap) >= 2:
                issues.append(ValidationIssue(
                    code="faq_question_overlap",
                    message="Une question FAQ recouvre la question principale d'une section.",
                    blocking=True,
                    location=f"faq[{index}] vs sections[{section_index}]",
                ))
    return issues


def build_reader_intent(keyword: str, competitors: list[CompetitorPage]) -> ReaderIntent:
    """Construction déterministe minimale avant l'analyse sémantique du modèle."""

    missing = next(
        (topic for competitor in competitors for topic in competitor.missing_topics if topic.strip()),
        "une réponse concrète",
    )
    return ReaderIntent(
        real_question=f"Comment résoudre le problème lié à « {keyword} » ?",
        reader_level="débutant",
        main_problem=keyword,
        likely_trap=missing,
        concrete_gain="savoir quelle décision prendre après la lecture",
    )
