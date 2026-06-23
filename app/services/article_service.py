from datetime import datetime, timezone
import json
import re
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.article import Article
from app.models.article_log import ArticleLog
from app.models.article_version import ArticleVersion
from app.models.category import Category
from app.models.media_asset import MediaAsset
from app.models.optimization_recommendation import OptimizationRecommendation
from app.models.seo_analysis import SeoAnalysis
from app.schemas.article import ArticleCreate, ArticleUpdate, ArticlePublicApiResponse, CategoryBrief
from app.core.utils import slugify, generate_unique_slug, calculate_word_count
from app.services.callout_template_service import extract_callouts_from_content

_EMPTY_CONTENT_MESSAGE = "Protection : contenu vide non sauvegardé pour éviter d'écraser un article existant."


def _is_effectively_empty_content(value: str | None) -> bool:
    if value is None:
        return True
    text = re.sub(r"<[^>]+>", " ", value)
    text = text.replace("&nbsp;", " ").replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text == ""


def _unique_slug(db: Session, project_id: str, title: str, exclude_id: str | None = None) -> str:
    base = slugify(title)
    q = db.query(Article.slug).filter(
        Article.project_id == project_id,
        Article.slug.like(f"{base}%"),
    )
    if exclude_id:
        q = q.filter(Article.id != exclude_id)
    existing = {row[0] for row in q.all()}
    return generate_unique_slug(base, existing)


def _snapshot_published_fields(article: Article) -> None:
    article.published_content = article.content
    article.published_title = article.title
    article.published_excerpt = article.excerpt
    article.published_meta_description = article.meta_description
    article.published_cover_image_url = article.cover_image_url
    article.published_faq_json = article.faq_json
    article.published_callouts_json = article.callouts_json


def create_article(db: Session, data: ArticleCreate, project_id: str) -> Article:
    slug = data.slug or _unique_slug(db, project_id, data.title)
    article = Article(
        project_id=project_id,
        category_id=data.category_id,
        title=data.title,
        slug=slug,
        content=data.content,
        excerpt=data.excerpt,
        status="draft",
        keyword=data.keyword,
        secondary_keywords_json=data.secondary_keywords_json,
        audience=data.audience,
        angle=data.angle,
        search_intent=data.search_intent,
        meta_title=data.meta_title,
        meta_description=data.meta_description,
        cover_image_url=data.cover_image_url,
        word_count=calculate_word_count(data.content),
        priority=data.priority,
        author_name=data.author_name,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


def get_article_by_id(db: Session, article_id: str) -> Article | None:
    article = db.query(Article).filter(Article.id == article_id).first()
    if article:
        _attach_validation_summary(article)
    return article


def _attach_validation_summary(article: Article) -> Article:
    try:
        from app.services.validation_service import check_validation_thresholds
        result = check_validation_thresholds(article)
        article.global_score = result["global_score"]
        article.global_score_valid = 1 if result["global_score_valid"] else 0
        article.is_validable = result["valid"]
        article.validation_reasons = result["reasons"]
        article.critical_warnings = result["critical_warnings"]
    except Exception:
        article.is_validable = None
        article.validation_reasons = []
        article.critical_warnings = []
    return article


def list_articles(
    db: Session,
    project_id: str,
    status: str | None = None,
    category_id: str | None = None,
    search: str | None = None,
    published_only: bool = False,
    archived: bool = False,
    blocked_cost_limit: float | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Article]:
    q = db.query(Article).filter(Article.project_id == project_id)
    if published_only:
        q = q.filter(Article.status == "published")
    elif archived:
        q = q.filter(Article.status == "archived")
    elif status:
        q = q.filter(Article.status == status)
    if category_id:
        q = q.filter(Article.category_id == category_id)
    if search:
        term = f"%{search}%"
        q = q.filter(Article.title.ilike(term))
    if blocked_cost_limit is not None:
        rows = q.order_by(Article.created_at.desc()).all()
        filtered: list[Article] = []
        for article in rows:
            cost_data = article.estimated_cost_json if isinstance(article.estimated_cost_json, dict) else None
            try:
                cost = float(cost_data.get("estimated_cost_eur")) if cost_data else None
            except (TypeError, ValueError):
                cost = None
            if cost is not None and cost > blocked_cost_limit:
                filtered.append(article)
        return [_attach_validation_summary(a) for a in filtered[offset:offset + limit]]
    return [_attach_validation_summary(a) for a in q.order_by(Article.created_at.desc()).limit(limit).offset(offset).all()]


def update_article(db: Session, article: Article, data: ArticleUpdate) -> Article:
    update_dict = data.model_dump(exclude_unset=True)
    if (
        article.status == "published"
        and "content" in update_dict
        and _is_effectively_empty_content(update_dict.get("content"))
        and not _is_effectively_empty_content(article.content)
    ):
        raise HTTPException(status_code=409, detail=_EMPTY_CONTENT_MESSAGE)
    for field, value in update_dict.items():
        if field.startswith("published_"):
            continue
        setattr(article, field, value)
    if "content" in update_dict:
        article.word_count = calculate_word_count(article.content)
        article.callouts_json = extract_callouts_from_content(article.content)
    db.commit()
    db.refresh(article)
    return article


def publish_article(db: Session, article: Article) -> Article:
    from app.services.scoring_service import compute_global_score
    # Create a publication snapshot before publishing
    from app.services.version_service import create_version
    create_version(db, article, "publish_snapshot")
    _snapshot_published_fields(article)
    article.status = "published"
    now = datetime.now(timezone.utc)
    if article.published_at is None:
        article.published_at = now
    article.updated_at = now
    article.human_validated_at = now
    # Compute and store global score
    scoring = compute_global_score(article)
    article.global_score = scoring["global_score"]
    article.global_score_valid = 1 if scoring["global_score_valid"] else 0
    db.commit()
    db.refresh(article)
    return article


def schedule_article_with_validation(db: Session, article: Article, scheduled_at: datetime) -> Article:
    from app.services.validation_service import check_validation_thresholds
    from app.services.scoring_service import compute_global_score

    result = check_validation_thresholds(article, planned_publish_at=scheduled_at)
    if not result["valid"]:
        reasons = "; ".join(result["reasons"])
        raise HTTPException(
            status_code=400,
            detail=f"Article non validable pour la programmation : {reasons}",
        )

    # Compute and store global score
    scoring = compute_global_score(article)
    article.global_score = scoring["global_score"]
    article.global_score_valid = 1 if scoring["global_score_valid"] else 0

    article.status = "scheduled"
    article.scheduled_at = scheduled_at
    article.human_validated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(article)
    return article


def rollback_article(db: Session, article: Article) -> Article:
    """Rollback to the last publish_snapshot version."""
    from app.models.article_version import ArticleVersion
    last_snapshot = (
        db.query(ArticleVersion)
        .filter(
            ArticleVersion.article_id == article.id,
            ArticleVersion.version_type == "publish_snapshot",
        )
        .order_by(ArticleVersion.created_at.desc())
        .first()
    )
    if not last_snapshot:
        raise HTTPException(status_code=404, detail="Aucun snapshot de publication disponible pour le rollback.")

    # Save current state before rolling back
    from app.services.version_service import create_version
    create_version(db, article, "restore", article.author_name)

    article.title = last_snapshot.title
    article.slug = last_snapshot.slug
    article.content = last_snapshot.content
    article.excerpt = last_snapshot.excerpt
    article.meta_title = last_snapshot.meta_title
    article.meta_description = last_snapshot.meta_description
    article.cover_image_url = last_snapshot.cover_image_url
    article.faq_json = last_snapshot.faq_json
    article.callouts_json = last_snapshot.callouts_json
    article.internal_links_json = last_snapshot.internal_links_json
    article.external_links_json = last_snapshot.external_links_json
    if last_snapshot.content:
        article.word_count = calculate_word_count(last_snapshot.content)
    article.status = "published"
    article.updated_at = datetime.now(timezone.utc)

    # Restore published fields too
    _snapshot_published_fields(article)

    db.commit()
    db.refresh(article)
    return article


def promote_article(db: Session, article: Article) -> Article:
    _snapshot_published_fields(article)
    article.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(article)
    return article


def schedule_article(db: Session, article: Article, scheduled_at: datetime) -> Article:
    return schedule_article_with_validation(db, article, scheduled_at)


def unpublish_article(db: Session, article: Article) -> Article:
    article.status = "draft"
    db.commit()
    db.refresh(article)
    return article


def delete_article(db: Session, article: Article) -> None:
    db.query(SeoAnalysis).filter(SeoAnalysis.article_id == article.id).delete(synchronize_session=False)
    db.query(ArticleVersion).filter(ArticleVersion.article_id == article.id).delete(synchronize_session=False)
    db.query(ArticleLog).filter(ArticleLog.article_id == article.id).update(
        {ArticleLog.article_id: None},
        synchronize_session=False,
    )
    db.query(MediaAsset).filter(MediaAsset.article_id == article.id).update(
        {MediaAsset.article_id: None},
        synchronize_session=False,
    )
    db.query(OptimizationRecommendation).filter(OptimizationRecommendation.article_id == article.id).update(
        {OptimizationRecommendation.article_id: None},
        synchronize_session=False,
    )
    db.delete(article)
    db.commit()


def get_public_articles(
    db: Session, project_id: str, limit: int = 20, offset: int = 0
) -> list[ArticlePublicApiResponse]:
    articles = (
        db.query(Article)
        .filter(Article.project_id == project_id, Article.status == "published")
        .order_by(Article.published_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    category_ids = {a.category_id for a in articles if a.category_id}
    category_map: dict[str, Category] = {}
    if category_ids:
        for cat in db.query(Category).filter(Category.id.in_(category_ids)).all():
            category_map[cat.id] = cat

    return [_to_public_response(a, category_map.get(a.category_id) if a.category_id else None) for a in articles]


def get_public_article_by_slug(db: Session, project_id: str, slug: str) -> ArticlePublicApiResponse | None:
    article = (
        db.query(Article)
        .filter(Article.project_id == project_id, Article.slug == slug, Article.status == "published")
        .first()
    )
    if not article:
        return None
    category = db.query(Category).filter(Category.id == article.category_id).first() if article.category_id else None
    return _to_public_response(article, category)


def _has_draft_changes(article: Article) -> bool:
    return (
        article.content != article.published_content
        or article.title != article.published_title
        or article.excerpt != article.published_excerpt
        or article.meta_description != article.published_meta_description
        or article.cover_image_url != article.published_cover_image_url
        or article.faq_json != article.published_faq_json
        or article.callouts_json != article.published_callouts_json
    )


def _to_public_response(article: Article, category: Category | None) -> ArticlePublicApiResponse:
    return ArticlePublicApiResponse(
        id=article.id,
        title=article.published_title or article.title,
        slug=article.slug,
        excerpt=article.published_excerpt or article.excerpt,
        content=article.published_content or article.content,
        category=CategoryBrief(
            id=category.id,
            name=category.name,
            slug=category.slug,
            color=category.color,
        ) if category else None,
        category_slug=category.slug if category else None,
        category_color=category.color if category else None,
        main_keyword=article.keyword,
        meta_title=article.meta_title,
        meta_description=article.published_meta_description or article.meta_description,
        cover_image_url=article.published_cover_image_url or article.cover_image_url,
        author_name=article.author_name,
        reading_time_minutes=article.reading_time_minutes,
        faq_json=article.published_faq_json or article.faq_json,
        callouts_json=article.published_callouts_json or article.callouts_json,
        published_at=article.published_at,
        updated_at=article.updated_at,
        has_draft_changes=_has_draft_changes(article) if article.status == "published" else None,
    )
