from sqlalchemy.orm import Session
from app.models.article import Article
from app.models.article_version import ArticleVersion

_EDITORIAL_FIELDS = frozenset({
    "content", "title", "slug", "excerpt", "meta_title", "meta_description",
    "faq_json", "callouts_json", "internal_links_json", "external_links_json",
    "content_blocks_json",
})


def create_version(
    db: Session,
    article: Article,
    version_type: str,
    created_by: str | None = None,
) -> ArticleVersion:
    last = (
        db.query(ArticleVersion)
        .filter(ArticleVersion.article_id == article.id)
        .order_by(ArticleVersion.version_number.desc())
        .first()
    )
    version_number = (last.version_number + 1) if last else 1

    version = ArticleVersion(
        project_id=article.project_id,
        article_id=article.id,
        title=article.title,
        slug=article.slug,
        content=article.content,
        excerpt=article.excerpt,
        meta_title=article.meta_title,
        meta_description=article.meta_description,
        cover_image_url=article.cover_image_url,
        faq_json=article.faq_json,
        callouts_json=article.callouts_json,
        internal_links_json=article.internal_links_json,
        external_links_json=article.external_links_json,
        content_blocks_json=article.content_blocks_json,
        version_number=version_number,
        version_type=version_type,
        created_by=created_by,
    )
    db.add(version)
    db.flush()
    return version


def should_create_manual_version(update_data: dict) -> bool:
    return bool(_EDITORIAL_FIELDS & update_data.keys())


def is_duplicate_autosave(db: Session, article_id: str, incoming_content: str | None) -> bool:
    last = (
        db.query(ArticleVersion)
        .filter(
            ArticleVersion.article_id == article_id,
            ArticleVersion.version_type == "autosave",
        )
        .order_by(ArticleVersion.created_at.desc())
        .first()
    )
    if not last:
        return False
    return last.content == incoming_content
