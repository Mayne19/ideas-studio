from __future__ import annotations

from sqlalchemy.orm import Session
from app.models.article import Article
from app.models.category import Category
from app.schemas.seo_workflow import CannibalizationCheck, asdict
from app.services.seo.helpers import normalize_text


def check_cannibalization(
    db: Session,
    project_id: str,
    title: str,
    keyword: str,
    category_id: str | None = None,
    exclude_article_id: str | None = None,
) -> CannibalizationCheck:
    result = CannibalizationCheck()

    articles = db.query(Article).filter(
        Article.project_id == project_id,
        Article.status.in_(["published", "draft", "draft_ready", "idea_proposed", "idea_priority"]),
    ).all()

    if exclude_article_id:
        articles = [a for a in articles if a.id != exclude_article_id]

    normalized_title = normalize_text(title)
    normalized_keyword = normalize_text(keyword)

    for a in articles:
        a_title = normalize_text(a.title or "")
        a_keyword = normalize_text(a.keyword or "")

        title_similar = a_title and (a_title == normalized_title or normalized_title in a_title or a_title in normalized_title)
        keyword_similar = a_keyword and (a_keyword == normalized_keyword or normalized_keyword in a_keyword or a_keyword in normalized_keyword)

        if title_similar or keyword_similar:
            cat_name = None
            if a.category_id:
                cat = db.query(Category).filter(Category.id == a.category_id).first()
                cat_name = cat.name if cat else None

            entry = {
                "article_id": a.id,
                "title": a.title,
                "keyword": a.keyword,
                "status": a.status,
                "category": cat_name,
                "similarity_reason": "title" if title_similar else "keyword",
            }
            result.similar_articles.append(entry)
            if a.keyword and a.keyword not in result.similar_keywords:
                result.similar_keywords.append(a.keyword)

    if result.similar_articles:
        result.risk_level = "high" if len(result.similar_articles) > 2 else "medium"
        if result.risk_level == "high":
            result.recommendation = "update_existing"
        else:
            result.recommendation = "change_angle"
    else:
        result.risk_level = "none"
        result.recommendation = "create_new"

    return result


def check_cannibalization_dict(
    db: Session,
    project_id: str,
    title: str,
    keyword: str,
    category_id: str | None = None,
    exclude_article_id: str | None = None,
) -> dict:
    return asdict(check_cannibalization(db, project_id, title, keyword, category_id, exclude_article_id))


# --- Scoring v2.1 : détection lightweight pour analyze_article() ---

import re as _re

_SEO_CAP_SCORE = 70

_STOP_TOKENS = frozenset({
    "un", "une", "le", "la", "les", "de", "du", "des", "d", "pour",
    "au", "aux", "sur", "dans", "en", "par", "avec", "est", "sont",
    "ce", "cet", "cette", "ces", "et", "ou", "mais", "donc", "comment",
    "quoi", "quand", "qui", "que", "quel", "quelle", "the", "a", "an",
    "of", "to", "in", "for", "on", "with", "is", "are", "how", "what",
})

_ACCENT = str.maketrans({
    "à": "a", "â": "a", "ä": "a", "é": "e", "è": "e", "ê": "e", "ë": "e",
    "î": "i", "ï": "i", "ô": "o", "ö": "o", "ù": "u", "û": "u", "ü": "u", "ç": "c",
})


def _kw_tokens(kw: str) -> list[str]:
    kw = kw.lower().translate(_ACCENT)
    return [t for t in _re.split(r"[^a-z0-9]+", kw) if len(t) > 2 and t not in _STOP_TOKENS]


def _soft_match(t1: str, t2: str) -> bool:
    if t1 == t2:
        return True
    # 5-char prefix stem (covers French inflections: technique/techniques, etc.)
    if len(t1) >= 5 and len(t2) >= 5 and t1[:5] == t2[:5]:
        return True
    return False


def _overlap(a: list[str], b: list[str]) -> float:
    if not a or not b:
        return 0.0
    # Count soft-matched pairs
    matched_a = set()
    matched_b = set()
    for i, ta in enumerate(a):
        for j, tb in enumerate(b):
            if _soft_match(ta, tb):
                matched_a.add(i)
                matched_b.add(j)
    intersection = len(matched_a)
    union = len(set(range(len(a))) | {len(a) + j for j in range(len(b))})
    # Jaccard on token counts
    return intersection / (len(a) + len(b) - intersection)


def score_cannibalization(article: object, project_articles: list[object]) -> dict:
    """
    Lightweight cannibalization check for scoring v2.1.
    Uses already-loaded project articles — no DB session required.

    Returns:
        {
            "detected": bool,
            "severity": "none" | "warning" | "critical",
            "competing_articles": [...],
            "cap_applied": bool,
            "seo_score_cap": int | None,
            "version": "2.1"
        }
    """
    current_kw = (getattr(article, "keyword", None) or "").strip()
    current_id = getattr(article, "id", None)

    empty_result = {
        "detected": False, "severity": "none",
        "competing_articles": [], "cap_applied": False,
        "seo_score_cap": None, "version": "2.1",
    }

    if not current_kw:
        return empty_result

    current_tokens = _kw_tokens(current_kw)
    if not current_tokens:
        return empty_result

    competing = []
    for other in project_articles:
        if getattr(other, "id", None) == current_id:
            continue
        other_kw = (getattr(other, "keyword", None) or "").strip()
        if not other_kw:
            continue
        ratio = _overlap(current_tokens, _kw_tokens(other_kw))
        if ratio >= 0.60:
            competing.append({
                "id": str(getattr(other, "id", "")),
                "title": (getattr(other, "title", None) or "")[:120],
                "keyword": other_kw,
                "overlap": round(ratio, 2),
                "status": getattr(other, "status", "draft"),
            })

    competing.sort(key=lambda x: -x["overlap"])
    detected = len(competing) > 0

    severity = "none"
    if detected:
        severity = "critical" if any(c["overlap"] >= 0.85 for c in competing) else "warning"

    return {
        "detected": detected,
        "severity": severity,
        "competing_articles": competing[:10],
        "cap_applied": detected,
        "seo_score_cap": _SEO_CAP_SCORE if detected else None,
        "version": "2.1",
    }


def apply_cannibalization_cap(seo_score: float, result: dict) -> float:
    """Cap SEO score at 70 if cannibalization is detected."""
    if result.get("cap_applied") and seo_score > _SEO_CAP_SCORE:
        return float(_SEO_CAP_SCORE)
    return seo_score
