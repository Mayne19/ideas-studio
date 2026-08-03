from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.content import Article, ArticleKeyword, ArticleRevision, Category, Keyword, KeywordRole
from app.models.reference import ArticleStatus
from app.schemas.seo_workflow import InternalLinkPlan, asdict
from app.services.seo.helpers import normalize_text


def build_internal_link_plan(
    db: Session,
    project_id: str,
    keyword: str,
    category_id: str | None = None,
    exclude_article_id: str | None = None,
    limit: int = 5,
    cannibalization_hints: list[dict] | None = None,
) -> InternalLinkPlan:
    plan = InternalLinkPlan()

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
            Article.status_reason_id == ArticleStatus.PUBLISHED,
        )
    ).all()

    if exclude_article_id:
        rows = [r for r in rows if r[0].id != exclude_article_id]

    normalized_keyword = normalize_text(keyword)
    scored = []

    # Priority IDs from cannibalization hints (section overlap detected)
    hint_ids: set[str] = set()
    if cannibalization_hints:
        for hint in cannibalization_hints:
            aid = hint.get("article_id")
            if aid:
                hint_ids.add(aid)
                # Add hint entries directly with high relevance
                scored.append({
                    "target_article_id": aid,
                    "target_url": f"/articles/{hint.get('article_id', aid)}",
                    "anchor_text": hint.get("title") or "Article connexe",
                    "placement": "auto",
                    "reason": "section overlap detected",
                    "relevance_score": 20,
                    "category": hint.get("category"),
                })

    category_names: dict[str, str] = {}

    for article, a_title_raw, a_keyword_raw in rows:
        if article.id in hint_ids:
            continue
        score = 0
        a_title = normalize_text(a_title_raw or "")
        a_keyword = normalize_text(a_keyword_raw or "")

        if a_keyword and normalized_keyword in a_keyword:
            score += 10
        if a_title and normalized_keyword in a_title:
            score += 5
        if article.category_id and category_id and article.category_id == category_id:
            score += 3

        if score > 0:
            cat_name = None
            if article.category_id:
                if article.category_id not in category_names:
                    cat = db.get(Category, article.category_id)
                    category_names[article.category_id] = cat.name if cat else None
                cat_name = category_names[article.category_id]

            scored.append({
                "target_article_id": article.id,
                "target_url": f"/articles/{article.slug}",
                "anchor_text": a_title_raw or "Article connexe",
                "placement": "auto",
                "reason": f"Pertinence {score}/10",
                "relevance_score": score,
                "category": cat_name,
            })

    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    plan.links = scored[:limit]

    if not plan.links:
        plan.limitations.append("No relevant internal articles found")

    return plan


def build_internal_link_plan_dict(
    db: Session,
    project_id: str,
    keyword: str,
    category_id: str | None = None,
    exclude_article_id: str | None = None,
    limit: int = 5,
    cannibalization_hints: list[dict] | None = None,
) -> dict:
    return asdict(build_internal_link_plan(
        db, project_id, keyword, category_id, exclude_article_id, limit, cannibalization_hints
    ))
