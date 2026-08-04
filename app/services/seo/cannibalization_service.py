from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.content import Article, ArticleKeyword, ArticleRevision, Category, Keyword, KeywordRole
from app.models.reference import ArticleStatus
from app.schemas.seo_workflow import CannibalizationCheck, asdict
from app.services.seo.helpers import normalize_text

_RELEVANT_STATUSES = (
    ArticleStatus.PUBLISHED,
    ArticleStatus.DRAFT,
    ArticleStatus.DRAFT_READY,
    ArticleStatus.IDEA_PROPOSED,
    ArticleStatus.IDEA_PRIORITY,
)


def check_cannibalization(
    db: Session,
    project_id: str,
    title: str,
    keyword: str,
    category_id: str | None = None,
    exclude_article_id: str | None = None,
) -> CannibalizationCheck:
    result = CannibalizationCheck()

    rows = db.execute(
        select(Article, ArticleRevision.title, Keyword.term)
        .outerjoin(ArticleRevision, ArticleRevision.id == Article.current_revision_id)
        .outerjoin(
            ArticleKeyword,
            (ArticleKeyword.article_id == Article.id) & (ArticleKeyword.role == KeywordRole.PRIMARY),
        )
        .outerjoin(Keyword, Keyword.id == ArticleKeyword.keyword_id)
        .where(
            Article.project_id == project_id,
            Article.status_reason_id.in_(_RELEVANT_STATUSES),
        )
    ).all()

    if exclude_article_id:
        rows = [r for r in rows if r[0].id != exclude_article_id]

    normalized_title = normalize_text(title)
    normalized_keyword = normalize_text(keyword)

    category_names: dict[str, str] = {}

    for article, a_title_raw, a_keyword_raw in rows:
        a_title = normalize_text(a_title_raw or "")
        a_keyword = normalize_text(a_keyword_raw or "")

        title_similar = a_title and (a_title == normalized_title or normalized_title in a_title or a_title in normalized_title)
        keyword_similar = a_keyword and (a_keyword == normalized_keyword or normalized_keyword in a_keyword or a_keyword in normalized_keyword)

        if title_similar or keyword_similar:
            cat_name = None
            if article.category_id:
                if article.category_id not in category_names:
                    cat = db.get(Category, article.category_id)
                    category_names[article.category_id] = cat.name if cat else None
                cat_name = category_names[article.category_id]

            entry = {
                "article_id": article.id,
                "title": a_title_raw,
                "keyword": a_keyword_raw,
                "status": article.status_reason_id,
                "category": cat_name,
                "similarity_reason": "title" if title_similar else "keyword",
            }
            result.similar_articles.append(entry)
            if a_keyword_raw and a_keyword_raw not in result.similar_keywords:
                result.similar_keywords.append(a_keyword_raw)

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


def check_section_cannibalization(
    db: Session,
    project_id: str,
    outline: dict,
    exclude_article_id: str | None = None,
    similarity_threshold: float = 0.6,
) -> dict:
    """Compare les H2/H3 du plan proposé (outline) aux plans déjà publiés/en
    cours du projet — la vérification titre/mot-clé de check_cannibalization
    ne détecte pas deux articles différents qui traitent en réalité les mêmes
    sous-sujets. Similarité = mots communs / mots du plus court des deux
    headings normalisés (Jaccard simplifié, aucune dépendance externe)."""
    from app.services.seo.artifacts import get_latest_artifacts_bulk

    proposed_headings = [
        normalize_text(s.get("heading", ""))
        for s in outline.get("sections", [])
        if s.get("heading")
    ]
    proposed_headings = [h for h in proposed_headings if h]
    if not proposed_headings:
        return {"overlapping_sections": [], "risk_level": "none"}

    article_ids = [
        row.id for row in db.execute(
            select(Article.id).where(
                Article.project_id == project_id,
                Article.status_reason_id.in_(_RELEVANT_STATUSES),
                Article.id != exclude_article_id if exclude_article_id else True,
            )
        ).all()
    ]
    if not article_ids:
        return {"overlapping_sections": [], "risk_level": "none"}

    outlines_by_article = get_latest_artifacts_bulk(db, article_ids, ["outline"])

    titles_by_article = {
        row.id: row.title for row in db.execute(
            select(Article.id, ArticleRevision.title)
            .join(ArticleRevision, ArticleRevision.id == Article.current_revision_id)
            .where(Article.id.in_(article_ids))
        ).all()
    }

    def _similarity(a: str, b: str) -> float:
        words_a, words_b = set(a.split()), set(b.split())
        if not words_a or not words_b:
            return 0.0
        shorter = min(len(words_a), len(words_b))
        return len(words_a & words_b) / shorter

    overlaps: list[dict] = []
    for article_id, artifacts in outlines_by_article.items():
        existing_outline = artifacts.get("outline")
        if not existing_outline:
            continue
        existing_headings = [
            normalize_text(s.get("heading", ""))
            for s in existing_outline.get("sections", [])
            if s.get("heading")
        ]
        matched_pairs = []
        for proposed in proposed_headings:
            for existing in existing_headings:
                if not existing:
                    continue
                score = _similarity(proposed, existing)
                if score >= similarity_threshold:
                    matched_pairs.append({"proposed": proposed, "existing": existing, "score": round(score, 2)})
        if matched_pairs:
            overlaps.append({
                "article_id": article_id,
                "title": titles_by_article.get(article_id),
                "overlapping_sections": matched_pairs,
            })

    risk_level = "none"
    if overlaps:
        max_overlap = max(len(o["overlapping_sections"]) for o in overlaps)
        risk_level = "high" if max_overlap >= 3 else "medium"

    return {"overlapping_sections": overlaps, "risk_level": risk_level}
