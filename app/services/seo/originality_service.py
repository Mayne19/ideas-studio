from __future__ import annotations

from app.schemas.seo_workflow import OriginalityReport, asdict
from app.services.seo.adapters.originality_adapter import originality_adapter
from app.services.seo.helpers import strip_html


def check_originality(content: str | None, sources: list[str] | None = None) -> OriginalityReport:
    report = OriginalityReport(
        method="heuristic",
        real_plagiarism_tool_used=False,
    )

    if not content:
        report.manual_review_needed = True
        return report

    text = strip_html(content)
    source_texts = sources or []

    if source_texts:
        ngram_result = originality_adapter.compare_ngrams(text, source_texts)
        report.heuristic_score = ngram_result.get("score", 100)
        report.compared_sources = [{"snippet": s[:200]} for s in source_texts]

        for s in ngram_result.get("suspicious", []):
            report.suspicious_passages.append({
                "text": s.get("ngram", ""),
                "source": s.get("source_snippet", "")[:100],
                "risk": "medium",
            })

        similar_starts = originality_adapter.detect_similar_starts(text, source_texts)
        for s in similar_starts:
            report.suspicious_passages.append({
                "text": s.get("sentence_start", ""),
                "source": s.get("source_snippet", "")[:100],
                "risk": "low",
                "type": "similar_start",
            })

        if report.heuristic_score < 85:
            report.risk_level = "medium"
            report.manual_review_needed = True
        elif report.suspicious_passages:
            report.risk_level = "low"
    else:
        report.heuristic_score = 100
        report.risk_level = "low"
        report.compared_sources = []
        report.suspicious_passages = []

    report.real_plagiarism_tool_used = False

    return report


def check_originality_dict(content: str | None, sources: list[str] | None = None) -> dict:
    return asdict(check_originality(content, sources))
