"""Validations déterministes du laboratoire."""

from __future__ import annotations

import re
from html import unescape

from .models import ArticleDraft, ArticlePlan, FactRecord, ValidationIssue


def plain_text(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\wÀ-ÿ'’-]+\b", text))


def validate_plan(plan: ArticlePlan) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not plan.summary_callout.strip():
        issues.append(ValidationIssue(
            code="missing_summary_callout",
            message="Le call out de résumé est obligatoire avant le premier H2.",
            blocking=True,
            location="summary_callout",
        ))
    if len(plan.summary_callout.split(".")) > 4:
        issues.append(ValidationIssue(
            code="summary_callout_too_long",
            message="Le call out doit rester une réponse courte.",
            blocking=True,
            location="summary_callout",
        ))
    if not plan.conclusion_heading.strip():
        issues.append(ValidationIssue(
            code="missing_conclusion",
            message="La conclusion doit être planifiée avant la FAQ.",
            blocking=True,
            location="conclusion",
        ))
    for index, section in enumerate(plan.sections):
        if not section.promise.strip() or not section.reader_question.strip():
            issues.append(ValidationIssue(
                code="incomplete_section_contract",
                message="Chaque section doit définir sa promesse et sa question lecteur.",
                blocking=True,
                location=f"sections[{index}]",
            ))
    return issues


def validate_draft(draft: ArticleDraft, plan: ArticlePlan) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    html = draft.content_html
    body = plain_text(html)
    if not body:
        issues.append(ValidationIssue(
            code="empty_content",
            message="Le contenu de l'article est vide.",
            blocking=True,
            location="content_html",
        ))
        return issues

    intro_html = html.split("<h2>", 1)[0]
    intro_words = word_count(plain_text(intro_html))
    total_words = word_count(body)
    if total_words and intro_words / total_words > 0.10:
        issues.append(ValidationIssue(
            code="intro_over_limit",
            message="L'introduction dépasse 10 % du contenu.",
            blocking=True,
            location="content_html",
        ))

    if "en résumé" not in html.lower():
        issues.append(ValidationIssue(
            code="missing_summary_callout",
            message="Le call out prévu dans le plan n'est pas présent.",
            blocking=True,
            location="content_html",
        ))

    faq_position = html.lower().find("faq")
    conclusion_position = html.lower().find(plan.conclusion_heading.lower())
    if conclusion_position < 0 or (faq_position >= 0 and conclusion_position > faq_position):
        issues.append(ValidationIssue(
            code="conclusion_after_faq",
            message="La conclusion doit précéder la FAQ.",
            blocking=True,
            location="content_html",
        ))
    return issues


def validate_facts(facts: list[FactRecord]) -> list[ValidationIssue]:
    return [
        ValidationIssue(
            code="unverified_fact",
            message=f"Le fait '{fact.value}' n'est pas vérifié.",
            blocking=True,
            location="facts",
        )
        for fact in facts
        if not fact.verified
    ]


def choose_best_version(
    versions: list[tuple[int, ArticleDraft, list[ValidationIssue]]],
) -> tuple[int, ArticleDraft, list[ValidationIssue]]:
    """Conserve la version la plus sûre sans réécriture automatique."""

    return min(
        versions,
        key=lambda item: (
            sum(issue.blocking for issue in item[2]),
            len(item[2]),
            item[0],
        ),
    )
