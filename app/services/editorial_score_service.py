"""Deterministic quality score used by the editorial workflow.

This score deliberately does not call an AI provider. It only inspects the
article HTML, its publication sheet and the reports already stored for the
article.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models.content import Article, ArticleScore
from app.services.seo.artifacts import get_latest_artifact
from experiments.editorial_agent_lab.editorial_agent.checks import fiche_valid


DEFAULT_MIN_SCORE = 90
_TAG_RE = re.compile(r"<(h2|h3|p|ul|ol|table)\b[^>]*>(.*?)</\1\s*>", re.IGNORECASE | re.DOTALL)
_HEADING_RE = re.compile(r"<h2\b[^>]*>(.*?)</h2\s*>", re.IGNORECASE | re.DOTALL)
_LINK_RE = re.compile(r"<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>", re.IGNORECASE)
_HTML_RE = re.compile(r"<[^>]+>")


def _text(value: str) -> str:
    return re.sub(r"\s+", " ", _HTML_RE.sub(" ", value or "")).strip().lower()


def _source_url(source: dict) -> str:
    return str(source.get("url") or source.get("source") or "").strip()


def _is_primary_or_official(source: dict) -> bool:
    kind = str(source.get("type") or source.get("source_type") or "").lower()
    if kind in {"primary", "official", "primaire", "officielle"}:
        return True
    url = _source_url(source).lower()
    host = (urlparse(url).hostname or "").removeprefix("www.")
    official_hosts = (".gouv.fr", ".gov", ".gov.uk", ".europa.eu", ".who.int", ".int")
    if host.endswith(official_hosts) or host in {"service-public.fr", "insee.fr"}:
        return True
    title = str(source.get("titre") or source.get("title") or "").lower()
    return any(marker in title for marker in ("site officiel", "ministère", "institution", "service public"))


def _linked_sources(body: str, fiche: dict | None) -> tuple[int, bool]:
    sources = [item for item in (fiche or {}).get("sources", []) if isinstance(item, dict)]
    links = {url.rstrip("/") for url in _LINK_RE.findall(body or "") if url.startswith(("http://", "https://"))}
    linked: list[dict] = []
    for source in sources:
        source_url = _source_url(source).rstrip("/")
        if source_url and any(link == source_url or link.startswith(source_url + "#") for link in links):
            linked.append(source)
    return len(linked), any(_is_primary_or_official(source) for source in linked)


def _structure_is_valid(body: str, faq: list) -> tuple[bool, list[str]]:
    tokens = [(kind.lower(), _text(content)) for kind, content in _TAG_RE.findall(body or "")]
    issues: list[str] = []
    for index, (kind, _) in enumerate(tokens):
        if kind != "h2":
            continue
        end = next((j for j in range(index + 1, len(tokens)) if tokens[j][0] == "h2"), len(tokens))
        first_h3 = next((j for j in range(index + 1, end) if tokens[j][0] == "h3"), None)
        if first_h3 is not None and not any(tokens[j][0] == "p" for j in range(index + 1, first_h3)):
            issues.append("un paragraphe doit introduire le premier H3 de chaque H2")
            break
    for index, (kind, _) in enumerate(tokens):
        if kind in {"ul", "ol", "table"} and (index == 0 or tokens[index - 1][0] != "p"):
            issues.append("chaque liste ou tableau doit être introduit par un paragraphe")
            break
    headings = [_text(value) for value in _HEADING_RE.findall(body or "")]
    faq_index = next((i for i, heading in enumerate(headings) if "faq" in heading or "questions fréquentes" in heading), None)
    conclusion_index = next((i for i, heading in enumerate(headings) if "conclusion" in heading or "pour retenir" in heading), None)
    if faq_index is not None and (conclusion_index is None or conclusion_index > faq_index):
        issues.append("la conclusion doit précéder la FAQ")
    if not isinstance(faq, list) or not 3 <= len(faq) <= 5:
        issues.append("la FAQ doit contenir de 3 à 5 questions")
    return not issues, issues


def _plagiarism_alert(db: Session, article_id: str) -> bool:
    for key in ("plagiarism_report", "originality_report"):
        report = get_latest_artifact(db, article_id, key) or {}
        if report.get("status") in {"plagiarism", "flagged"}:
            return True
        if report.get("matches") or report.get("findings") or report.get("suspicious_passages"):
            return True
        v2 = report.get("v2") if isinstance(report.get("v2"), dict) else {}
        if v2.get("status") in {"plagiarism", "flagged"}:
            return True
    return False


def compute_editorial_score(
    db: Session,
    article: Article,
    fiche: dict | None,
    fiche_error: str = "",
) -> dict:
    body = article.current_revision.body if article.current_revision else ""
    fiche_check = fiche_valid(fiche, fiche_error)
    source_count, has_primary_source = _linked_sources(body, fiche)
    structure_ok, structure_issues = _structure_is_valid(body, (fiche or {}).get("faq", []))
    plagiarism = _plagiarism_alert(db, article.id)
    summary_ok = '<aside class="summary">' in body
    em_dash_ok = "—" not in body

    components = [
        {"name": "encadré « En résumé »", "points": 15, "earned": 15 if summary_ok else 0, "passed": summary_ok},
        {"name": "aucun tiret cadratin", "points": 10, "earned": 10 if em_dash_ok else 0, "passed": em_dash_ok},
        {"name": "fiche complète et valide", "points": 15, "earned": 15 if fiche_check["passed"] else 0, "passed": fiche_check["passed"]},
        {"name": "sources liées", "points": 20, "earned": 20 if source_count >= 3 and has_primary_source else 0,
         "passed": source_count >= 3 and has_primary_source, "detail": f"{source_count} source(s), primaire/officielle: {'oui' if has_primary_source else 'non'}"},
        {"name": "aucune alerte de plagiat", "points": 20, "earned": 0 if plagiarism else 20, "passed": not plagiarism},
        {"name": "structure respectée", "points": 20, "earned": 20 if structure_ok else 0, "passed": structure_ok,
         "detail": " ; ".join(structure_issues)},
    ]
    global_score = sum(component["earned"] for component in components)
    blocking_passed = summary_ok and em_dash_ok and fiche_check["passed"]
    issues = [component.get("detail") or component["name"] for component in components if not component["passed"]]
    return {
        "global_score": global_score,
        "global_score_valid": blocking_passed,
        "blocking_passed": blocking_passed,
        "components": components,
        "blocking_checks": [components[0], components[1], components[2]],
        "issues": issues,
        "plagiarism_alert": plagiarism,
        "source_count": source_count,
        "has_primary_source": has_primary_source,
    }


def store_editorial_score(db: Session, article: Article, report: dict) -> ArticleScore:
    score = ArticleScore(
        article_id=article.id,
        revision_id=article.current_revision_id,
        global_score=report["global_score"],
        quality_score=report["global_score"],
        readiness_status="ready" if report["blocking_passed"] else "blocked",
        issues=report["issues"],
    )
    db.add(score)
    db.flush()
    return score
