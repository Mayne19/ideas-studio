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
