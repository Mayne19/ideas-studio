"""Point d'entrée unique des contrôles du laboratoire."""

from __future__ import annotations

from .fact_ledger import validate_fact_ledger
from .models import (
    ArticleDraft,
    ArticlePlan,
    CompetitorPage,
    FactRecord,
    SimilarityFinding,
    ValidationIssue,
    ValidationReport,
)
from .planning import (
    validate_competitor_dossier,
    validate_plan_coverage,
    validate_source_diversity,
)
from .validators import validate_draft, validate_plan


def validate_article(
    *,
    plan: ArticlePlan,
    draft: ArticleDraft,
    facts: list[FactRecord],
    competitors: list[CompetitorPage],
    source_urls: set[str],
    competitor_urls: set[str] | None = None,
    similarity_findings: list[SimilarityFinding] | None = None,
) -> ValidationReport:
    """Exécute tous les contrôles et ne modifie jamais le brouillon."""

    issues: list[ValidationIssue] = []
    issues.extend(validate_competitor_dossier(competitors))
    issues.extend(validate_plan(plan))
    issues.extend(validate_plan_coverage(plan))
    issues.extend(validate_fact_ledger(facts, source_urls, competitor_urls=competitor_urls))
    issues.extend(validate_source_diversity(facts, list(competitor_urls or set())))
    issues.extend(validate_draft(draft, plan))
    for finding in similarity_findings or []:
        issues.append(ValidationIssue(
            code="similarity_warning",
            message=f"Phrase similaire détectée vers {finding.source_url}.",
            blocking=False,
            location="content_html",
        ))
    blocking_count = sum(issue.blocking for issue in issues)
    warning_count = len(issues) - blocking_count
    return ValidationReport(
        issues=issues,
        blocking_count=blocking_count,
        warning_count=warning_count,
        passed=blocking_count == 0,
    )
