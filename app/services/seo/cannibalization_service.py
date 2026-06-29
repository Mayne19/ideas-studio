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
