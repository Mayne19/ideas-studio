"""ContentGapIdentifier — Compare les insights humains, les angles concurrents
et le contenu déjà publié par le projet pour identifier les manques éditoriaux.

Un article ne gagne pas en référencement en répétant ce qui existe déjà : il
gagne en couvrant ce que personne ne couvre encore dans le projet (et
idéalement dans les SERP). Ce service recoupe trois sources :
  - human_insights : vraies questions, douleurs, objections des utilisateurs
  - research_brief.competitor_angles : angles traités par les concurrents
  - articles existants du projet (outlines + mots-clés) : déjà couvert

Chaque gap détecté est formulé comme une opportunité actionnable pour le plan
ou la rédaction. Heuristique pur — aucune dépendance LLM.
"""
from __future__ import annotations

import logging
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Article, ArticleKeyword, ArticleRevision, Keyword, KeywordRole
from app.models.reference import ArticleStatus
from app.services.seo.artifacts import get_latest_artifacts_bulk
from app.services.seo.helpers import normalize_text

logger = logging.getLogger(__name__)

_RELEVANT_STATUSES = (
    ArticleStatus.PUBLISHED,
    ArticleStatus.DRAFT,
    ArticleStatus.DRAFT_READY,
    ArticleStatus.IDEA_PROPOSED,
    ArticleStatus.IDEA_PRIORITY,
)

_STOPWORDS = {
    "de", "des", "le", "la", "les", "du", "un", "une", "et", "ou", "en", "au", "aux",
    "pour", "dans", "sur", "par", "avec", "sans", "plus", "moins", "que", "qui", "quoi",
    "dont", "est", "sont", "ce", "cette", "ces", "son", "sa", "ses", "mon", "ma", "mes",
    "ton", "ta", "tes", "notre", "vos", "leur", "leurs", "the", "a", "an", "and", "or",
    "of", "to", "in", "for", "with", "on", "at", "from", "how", "why", "what", "which",
    "when", "where", "i", "you", "it", "is", "are", "do", "does",
}


def _keywords(text: str) -> set[str]:
    words = re.findall(r"\w{3,}", normalize_text(text))
    return {w for w in words if w not in _STOPWORDS}


def _lexical_overlap(a: str, b: str) -> float:
    ka, kb = _keywords(a), _keywords(b)
    if not ka or not kb:
        return 0.0
    return len(ka & kb) / min(len(ka), len(kb))


def _collect_existing_coverage(db: Session, project_id: str, exclude_article_id: str | None) -> dict[str, list[dict]]:
    """Récupère pour chaque article existant du projet son outline et ses mots-clés."""
    rows = db.execute(
        select(Article.id)
        .where(
            Article.project_id == project_id,
            Article.status_reason_id.in_(_RELEVANT_STATUSES),
            Article.id != exclude_article_id if exclude_article_id else Article.id.isnot(None),
        )
    ).all()
    article_ids = [r[0] for r in rows]
    if not article_ids:
        return {}

    outlines = get_latest_artifacts_bulk(db, article_ids, ["outline"])

    title_rows = db.execute(
        select(Article.id, ArticleRevision.title)
        .join(ArticleRevision, ArticleRevision.id == Article.current_revision_id)
        .where(Article.id.in_(article_ids))
    ).all()
    titles = {r[0]: r[1] for r in title_rows}

    kw_rows = db.execute(
        select(ArticleKeyword.article_id, Keyword.term)
        .join(Keyword, Keyword.id == ArticleKeyword.keyword_id)
        .where(
            ArticleKeyword.article_id.in_(article_ids),
            ArticleKeyword.role == KeywordRole.PRIMARY,
        )
    ).all()
    keywords: dict[str, list[str]] = {}
    for article_id, term in kw_rows:
        keywords.setdefault(article_id, []).append(term or "")

    coverage: dict[str, list[dict]] = {}
    for article_id in article_ids:
        sections = outlines.get(article_id, {}).get("outline", {}).get("sections", []) if outlines.get(article_id) else []
        headings = [
            normalize_text(s.get("heading", ""))
            for s in sections
            if isinstance(s, dict) and s.get("heading")
        ]
        coverage[article_id] = {
            "title": titles.get(article_id, ""),
            "headings": headings,
            "keywords": keywords.get(article_id, []),
        }
    return coverage


def identify_content_gaps(
    keyword: str,
    title: str | None = None,
    research_brief: dict | None = None,
    human_insights: dict | None = None,
    db: Session | None = None,
    project_id: str | None = None,
    exclude_article_id: str | None = None,
    overlap_threshold: float = 0.6,
) -> dict:
    """
    Identifie les angles, questions et douleurs pas encore couverts par le
    projet, en croisant les sources externes (concurrents + humains) avec les
    articles existants.
    """
    research_brief = research_brief or {}
    human_insights = human_insights or {}

    competitor_angles = research_brief.get("competitor_angles") or []
    field_signals = research_brief.get("field_signals") or []
    questions = human_insights.get("questions") or []
    pain_points = human_insights.get("pain_points") or []
    objections = human_insights.get("objections") or []
    debates = human_insights.get("debates") or []
    vocabulary = human_insights.get("vocabulary") or []

    existing_coverage: dict[str, dict] = {}
    if db is not None and project_id:
        try:
            existing_coverage = _collect_existing_coverage(db, project_id, exclude_article_id)
        except Exception as exc:
            logger.warning("ContentGap: existing coverage collection failed: %s", exc)

    covered_headings: list[str] = []
    covered_keywords: list[str] = []
    covered_titles: list[str] = []
    for article_id, cov in existing_coverage.items():
        covered_headings.extend(cov["headings"])
        covered_keywords.extend(cov["keywords"])
        covered_titles.append(cov["title"] or "")

    def _is_already_covered(text: str) -> bool:
        norm = normalize_text(text)
        if not norm:
            return True
        for h in covered_headings:
            if norm == h or norm in h or h in norm:
                return True
            if _lexical_overlap(norm, h) >= overlap_threshold:
                return True
        for t in covered_titles:
            if t and (norm == t or _lexical_overlap(norm, t) >= overlap_threshold):
                return True
        return False

    gaps: list[dict] = []
    seen: set[str] = set()

    def _add_gap(gap_type: str, label: str, source: str, priority: str = "medium"):
        key = normalize_text(label)
        if not key or key in seen:
            return
        seen.add(key)
        gaps.append({
            "type": gap_type,
            "label": label,
            "source": source,
            "priority": priority,
        })

    for q in questions:
        if not _is_already_covered(q):
            _add_gap("question", q, "human_insights", "high")
    for p in pain_points:
        if not _is_already_covered(p):
            _add_gap("pain_point", p, "human_insights", "high")
    for o in objections:
        if not _is_already_covered(o):
            _add_gap("objection", o, "human_insights", "medium")
    for d in debates:
        if not _is_already_covered(d):
            _add_gap("debate", d, "human_insights", "medium")
    for v in vocabulary[:15]:
        if not _is_already_covered(v):
            _add_gap("vocabulary", v, "human_insights", "low")

    if competitor_angles:
        keyword_norm = normalize_text(keyword)
        for angle in competitor_angles:
            angle_norm = normalize_text(angle)
            if not angle_norm or angle_norm == keyword_norm:
                continue
            if _is_already_covered(angle):
                continue
            _add_gap("competitor_angle", angle, "competitor_analysis", "medium")

    if field_signals and not covered_titles:
        for signal in field_signals:
            _add_gap("field_signal", signal, "competitor_analysis", "low")

    uncovered_questions = [g["label"] for g in gaps if g["type"] == "question"]
    uncovered_pain_points = [g["label"] for g in gaps if g["type"] == "pain_point"]
    uncovered_angles = [g["label"] for g in gaps if g["type"] == "competitor_angle"]

    suggestions: list[str] = []
    if uncovered_questions:
        suggestions.append(
            "Couvre les questions suivantes que le projet ne traite pas encore : "
            + "; ".join(uncovered_questions[:5])
        )
    if uncovered_pain_points:
        suggestions.append(
            "Adresse ces douleurs non couvertes par le projet : "
            + "; ".join(uncovered_pain_points[:5])
        )
    if uncovered_angles:
        suggestions.append(
            "Traite ces angles qu'aucun article du projet ne couvre encore : "
            + "; ".join(uncovered_angles[:5])
        )
    if existing_coverage and not gaps:
        suggestions.append(
            "Sujet déjà bien couvert par le projet — privilégie un angle nouveau ou "
            "une mise à jour d'un article existant plutôt qu'un nouvel article redondant."
        )

    priority_order = {"high": 0, "medium": 1, "low": 2}
    gaps.sort(key=lambda g: priority_order.get(g["priority"], 2))

    status = "gaps_found" if gaps else "no_gaps"
    if existing_coverage and not gaps:
        status = "saturated"

    return {
        "keyword": keyword,
        "status": status,
        "total_gaps": len(gaps),
        "gaps": gaps,
        "uncovered_questions": uncovered_questions,
        "uncovered_pain_points": uncovered_pain_points,
        "uncovered_angles": uncovered_angles,
        "suggestions": suggestions,
        "existing_articles_checked": len(existing_coverage),
    }


def identify_content_gaps_dict(
    keyword: str,
    title: str | None = None,
    research_brief: dict | None = None,
    human_insights: dict | None = None,
    db: Session | None = None,
    project_id: str | None = None,
    exclude_article_id: str | None = None,
    overlap_threshold: float = 0.6,
) -> dict:
    return identify_content_gaps(
        keyword,
        title,
        research_brief,
        human_insights,
        db,
        project_id,
        exclude_article_id,
        overlap_threshold,
    )
