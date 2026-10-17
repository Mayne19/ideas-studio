"""Choix et validation de l'angle éditorial."""

from __future__ import annotations

from .models import CompetitorPage, EditorialAngle, ReaderIntent, ValidationIssue


def validate_angle(angle: EditorialAngle, facts: set[str]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not angle.title.strip() or not angle.reader_problem.strip():
        issues.append(ValidationIssue(
            code="incomplete_editorial_angle",
            message="L'angle doit définir un titre et un problème lecteur.",
            blocking=True,
            location="angle",
        ))
    if not angle.information_gain.strip():
        issues.append(ValidationIssue(
            code="missing_information_gain",
            message="L'angle doit apporter un gain d'information concret.",
            blocking=True,
            location="angle.information_gain",
        ))
    missing = [fact_id for fact_id in angle.supported_by_facts if fact_id not in facts]
    if missing:
        issues.append(ValidationIssue(
            code="angle_fact_not_found",
            message=f"L'angle cite des faits absents du registre : {', '.join(missing)}.",
            blocking=True,
            location="angle.supported_by_facts",
        ))
    if not angle.distinct_from_competitors:
        issues.append(ValidationIssue(
            code="angle_not_differentiated",
            message="L'angle ne précise pas ce qu'il apporte par rapport aux concurrents.",
            blocking=True,
            location="angle.distinct_from_competitors",
        ))
    return issues


def propose_angle(reader: ReaderIntent, competitors: list[CompetitorPage], fact_ids: list[str]) -> EditorialAngle:
    missing = [topic for competitor in competitors for topic in competitor.missing_topics if topic.strip()]
    strengths = [strength for competitor in competitors for strength in competitor.strengths if strength.strip()]
    return EditorialAngle(
        title=f"Résoudre précisément : {reader.main_problem}",
        reader_problem=reader.main_problem,
        information_gain=reader.concrete_gain,
        distinct_from_competitors=(missing[:2] or strengths[:2] or ["un angle propre au lecteur"]),
        supported_by_facts=fact_ids[:2],
    )
