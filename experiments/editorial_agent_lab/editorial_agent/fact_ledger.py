"""Registre de faits sourcés avant la rédaction."""

from __future__ import annotations

from urllib.parse import urlsplit

from .models import FactRecord, ValidationIssue


def _domain(url: str) -> str:
    return (urlsplit(url).hostname or "").lower().removeprefix("www.")


def validate_fact_ledger(
    facts: list[FactRecord],
    source_urls: set[str],
    *,
    competitor_urls: set[str] | None = None,
) -> list[ValidationIssue]:
    """Contrôle la traçabilité sans prétendre vérifier le Web lui-même."""

    competitor_domains = {_domain(url) for url in competitor_urls or set()}
    issues: list[ValidationIssue] = []
    seen_ids: set[str] = set()
    for index, fact in enumerate(facts, start=1):
        fact_id = fact.fact_id or f"fact-{index}"
        if fact_id in seen_ids:
            issues.append(ValidationIssue(
                code="duplicate_fact_id",
                message=f"L'identifiant de fait {fact_id} est utilisé plusieurs fois.",
                blocking=True,
                location=f"facts[{index - 1}]",
            ))
        seen_ids.add(fact_id)
        if not fact.quote.strip():
            issues.append(ValidationIssue(
                code="missing_fact_quote",
                message=f"Le fait {fact_id} n'a pas de citation exacte.",
                blocking=True,
                location=f"facts[{index - 1}]",
            ))
        if not fact.verified:
            issues.append(ValidationIssue(
                code="unverified_fact",
                message=f"Le fait {fact_id} n'est pas marqué comme vérifié.",
                blocking=True,
                location=f"facts[{index - 1}]",
            ))
        source = str(fact.source_url)
        if source not in source_urls:
            issues.append(ValidationIssue(
                code="fact_source_not_loaded",
                message=f"La source du fait {fact_id} ne figure pas dans les pages lues.",
                blocking=True,
                location=f"facts[{index - 1}].source_url",
            ))
        if _domain(source) in competitor_domains:
            issues.append(ValidationIssue(
                code="competitor_used_as_fact_source",
                message=f"Le fait {fact_id} utilise un concurrent comme source.",
                blocking=True,
                location=f"facts[{index - 1}].source_url",
            ))
    return issues


def assign_fact_ids(facts: list[FactRecord]) -> list[FactRecord]:
    """Retourne des copies stables pour référencer les faits dans le plan."""

    return [
        fact.model_copy(update={"fact_id": fact.fact_id or f"fact-{index}"})
        for index, fact in enumerate(facts, start=1)
    ]
