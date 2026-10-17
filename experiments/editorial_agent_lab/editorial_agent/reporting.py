"""Rapport d'exécution sérialisable du laboratoire."""

from __future__ import annotations

from typing import Any

from .models import GenerationResult


def build_run_report(
    result: GenerationResult,
    *,
    model: str = "fake",
    duration_s: float = 0.0,
    cost_usd: float = 0.0,
    searches: list[str] | None = None,
    pages: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Inclut le plan, les faits, les sources, les contrôles et le brouillon."""

    return {
        "model": model,
        "duration_s": duration_s,
        "cost_usd": cost_usd,
        "keyword": result.report.keyword,
        "searches": searches or [],
        "pages": pages or [],
        "plan": result.plan.model_dump(mode="json"),
        "angle": result.angle.model_dump(mode="json") if result.angle else None,
        "draft": result.draft.model_dump(mode="json"),
        "blocking_issues": [issue.model_dump(mode="json") for issue in result.report.blocking_issues],
        "warnings": [issue.model_dump(mode="json") for issue in result.report.warnings],
        "similarity_findings": [finding.model_dump(mode="json") for finding in result.report.similarity_findings],
        "selected_version": result.report.selected_version,
    }
