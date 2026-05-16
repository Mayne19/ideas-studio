from datetime import datetime, timezone
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
    return db.query(Article).filter(Article.id == article_id).first()


def list_articles(
    db: Session,
    project_id: str,
    status: str | None = None,
    category_id: str | None = None,
    search: str | None = None,
    published_only: bool = False,
    limit: int = 20,
    offset: int = 0,
) -> list[Article]:
    q = db.query(Article).filter(Article.project_id == project_id)
    if published_only:
        q = q.filter(Article.status == "published")
    elif status:
        q = q.filter(Article.status == status)
    if category_id:
        q = q.filter(Article.category_id == category_id)
    if search:
        term = f"%{search}%"
        q = q.filter(Article.title.ilike(term))
    return q.order_by(Article.created_at.desc()).limit(limit).offset(offset).all()


def update_article(db: Session, article: Article, data: ArticleUpdate) -> Article:
    update_dict = data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(article, field, value)
    if "content" in update_dict:
        article.word_count = calculate_word_count(article.content)
        article.callouts_json = extract_callouts_from_content(article.content)
    db.commit()
    db.refresh(article)
    return article


def publish_article(db: Session, article: Article) -> Article:
    article.status = "published"
    now = datetime.now(timezone.utc)
    if article.published_at is None:
        article.published_at = now
    article.updated_at = now
    db.commit()
    db.refresh(article)
    return article


def schedule_article(db: Session, article: Article, scheduled_at: datetime) -> Article:
    article.status = "scheduled"
    article.scheduled_at = scheduled_at
    db.commit()
    db.refresh(article)
    return article


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


def _to_public_response(article: Article, category: Category | None) -> ArticlePublicApiResponse:
    return ArticlePublicApiResponse(
        id=article.id,
        title=article.title,
        slug=article.slug,
        excerpt=article.excerpt,
        content=article.content,
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
        meta_description=article.meta_description,
        cover_image_url=article.cover_image_url,
        author_name=article.author_name,
        reading_time_minutes=article.reading_time_minutes,
        faq_json=article.faq_json,
        callouts_json=article.callouts_json,
        published_at=article.published_at,
        updated_at=article.updated_at,
    )
