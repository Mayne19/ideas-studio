"""Schéma content — catégories, articles et tout ce qui s'y rattache.

Voir db/migration-v3/REPRENDRE-LA-MAIN.md §5 (bloc `Article` → éclaté en 7)
pour la correspondance avec l'ancien modèle Article.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, ForeignKey, ForeignKeyConstraint, Index, Integer, Numeric, SmallInteger, Text, UniqueConstraint, text,
)
from sqlalchemy.dialects.postgresql import CITEXT, ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.reference import KeywordRole, LinkKind, MediaRole, RevisionSource


def _uuid_pk() -> Mapped[str]:
    return mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("project_id", "slug"),
        Index("categories_project_idx", "project_id"),
        {"schema": "content"},
    )

    id: Mapped[str] = _uuid_pk()
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("core.projects.id", ondelete="CASCADE"), nullable=False
    )
    parent_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("content.categories.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(CITEXT, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    monthly_target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_pipeline_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    overrides: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)


class Article(Base):
    """Un article "à plat" (contenu, méta, scores) s'obtient via les vues
    content.v_articles_current / v_articles_published, pas via ce modèle seul —
    voir REPRENDRE-LA-MAIN.md §6, dernier paragraphe."""

    __tablename__ = "articles"
    __table_args__ = (
        UniqueConstraint("project_id", "slug"),
        ForeignKeyConstraint(
            ["status_reason_id", "state_id"],
            ["ref.article_status_reasons.id", "ref.article_status_reasons.state_id"],
        ),
        Index("articles_project_status_idx", "project_id", "state_id", "status_reason_id", text("updated_at DESC")),
        Index("articles_project_cat_idx", "project_id", "category_id"),
        Index("articles_scheduled_idx", "scheduled_for", postgresql_where=text("status_reason_id = 110")),
        {"schema": "content"},
    )

    id: Mapped[str] = _uuid_pk()
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("core.projects.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("content.categories.id", ondelete="SET NULL"), nullable=True
    )
    derived_from_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("content.articles.id", ondelete="SET NULL"), nullable=True
    )
    slug: Mapped[str] = mapped_column(CITEXT, nullable=False)
    state_id: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    status_reason_id: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=10)
    sub_niche: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    search_intent: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_format: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    opportunity_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    author_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_revision_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("content.article_revisions.id", ondelete="SET NULL", use_alter=True), nullable=True
    )
    published_revision_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("content.article_revisions.id", ondelete="SET NULL", use_alter=True), nullable=True
    )
    scheduled_for: Mapped[datetime | None] = mapped_column(nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(nullable=True)
    next_review_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)
    archived_at: Mapped[datetime | None] = mapped_column(nullable=True)

    revisions: Mapped[list["ArticleRevision"]] = relationship(
        foreign_keys="ArticleRevision.article_id", back_populates="article", passive_deletes=True
    )
    current_revision: Mapped["ArticleRevision | None"] = relationship(
        foreign_keys=[current_revision_id], viewonly=True
    )
    published_revision: Mapped["ArticleRevision | None"] = relationship(
        foreign_keys=[published_revision_id], viewonly=True
    )
    seo: Mapped["ArticleSeo | None"] = relationship(back_populates="article", uselist=False, passive_deletes=True)
    scores: Mapped[list["ArticleScore"]] = relationship(back_populates="article", passive_deletes=True)
    comments: Mapped[list["ArticleComment"]] = relationship(back_populates="article", passive_deletes=True)


class ArticleRevision(Base):
    __tablename__ = "article_revisions"
    __table_args__ = (
        UniqueConstraint("article_id", "revision_no"),
        Index("revisions_article_idx", "article_id", text("revision_no DESC")),
        {"schema": "content"},
    )

    id: Mapped[str] = _uuid_pk()
    article_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("content.articles.id", ondelete="CASCADE"), nullable=False
    )
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[RevisionSource] = mapped_column(
        ENUM(RevisionSource, name="revision_source", schema="content", create_type=False),
        nullable=False, default=RevisionSource.AI,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    blocks: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    faq: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    callouts: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reading_time_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("core.users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(default=_now)

    article: Mapped["Article"] = relationship(foreign_keys=[article_id], back_populates="revisions")


class ArticleSeo(Base):
    __tablename__ = "article_seo"
    __table_args__ = {"schema": "content"}

    article_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("content.articles.id", ondelete="CASCADE"), primary_key=True
    )
    meta_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    structured_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)

    article: Mapped["Article"] = relationship(back_populates="seo")


class Keyword(Base):
    __tablename__ = "keywords"
    __table_args__ = (
        UniqueConstraint("project_id", "term"),
        {"schema": "content"},
    )

    id: Mapped[str] = _uuid_pk()
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("core.projects.id", ondelete="CASCADE"), nullable=False
    )
    term: Mapped[str] = mapped_column(CITEXT, nullable=False)
    volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    difficulty: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)


class ArticleKeyword(Base):
    __tablename__ = "article_keywords"
    __table_args__ = (
        Index("article_keywords_one_primary", "article_id", unique=True, postgresql_where=text("role = 'primary'")),
        {"schema": "content"},
    )

    article_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("content.articles.id", ondelete="CASCADE"), primary_key=True
    )
    keyword_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("content.keywords.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[KeywordRole] = mapped_column(
        ENUM(KeywordRole, name="keyword_role", schema="content", create_type=False),
        nullable=False, default=KeywordRole.SECONDARY,
    )


class ArticleLink(Base):
    __tablename__ = "article_links"
    __table_args__ = (
        CheckConstraint(
            "(kind = 'internal' AND target_article_id IS NOT NULL) OR "
            "(kind = 'external' AND target_url IS NOT NULL)"
        ),
        {"schema": "content"},
    )

    id: Mapped[str] = _uuid_pk()
    article_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("content.articles.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[LinkKind] = mapped_column(
        ENUM(LinkKind, name="link_kind", schema="content", create_type=False),
        nullable=False,
    )
    target_article_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("content.articles.id", ondelete="SET NULL"), nullable=True
    )
    target_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    anchor_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_suggested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class MediaAsset(Base):
    __tablename__ = "media_assets"
    __table_args__ = {"schema": "content"}

    id: Mapped[str] = _uuid_pk()
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("core.projects.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    byte_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    alt_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)


class ArticleMedia(Base):
    __tablename__ = "article_media"
    __table_args__ = {"schema": "content"}

    article_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("content.articles.id", ondelete="CASCADE"), primary_key=True
    )
    media_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("content.media_assets.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[MediaRole] = mapped_column(
        ENUM(MediaRole, name="media_role", schema="content", create_type=False),
        nullable=False, default=MediaRole.INLINE, primary_key=True,
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)


class ArticleScore(Base):
    __tablename__ = "article_scores"
    __table_args__ = (
        Index("scores_article_idx", "article_id", text("evaluated_at DESC")),
        {"schema": "content"},
    )

    id: Mapped[str] = _uuid_pk()
    article_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("content.articles.id", ondelete="CASCADE"), nullable=False
    )
    revision_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("content.article_revisions.id", ondelete="SET NULL"), nullable=True
    )
    seo_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    readability_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    eeat_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    geo_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    global_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    readiness_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    issues: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    suggestions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    evaluated_at: Mapped[datetime] = mapped_column(default=_now)

    article: Mapped["Article"] = relationship(back_populates="scores")


class ArticleComment(Base):
    __tablename__ = "article_comments"
    __table_args__ = (
        Index("comments_article_open_idx", "article_id", postgresql_where=text("resolved_at IS NULL")),
        {"schema": "content"},
    )

    id: Mapped[str] = _uuid_pk()
    article_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("content.articles.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("core.users.id", ondelete="SET NULL"), nullable=True
    )
    parent_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("content.article_comments.id", ondelete="CASCADE"), nullable=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    quoted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)

    article: Mapped["Article"] = relationship(back_populates="comments")


class BoardColumn(Base):
    """Colonne kanban : soit liée à un motif de statut réel, soit une voie
    libre (custom_key) — voir app/routers/kanban_columns.py."""

    __tablename__ = "board_columns"
    __table_args__ = (
        CheckConstraint(
            "(status_reason_id IS NOT NULL AND custom_key IS NULL) OR "
            "(status_reason_id IS NULL AND custom_key IS NOT NULL)"
        ),
        UniqueConstraint("project_id", "status_reason_id"),
        UniqueConstraint("project_id", "custom_key"),
        {"schema": "content"},
    )

    id: Mapped[str] = _uuid_pk()
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("core.projects.id", ondelete="CASCADE"), nullable=False
    )
    status_reason_id: Mapped[int | None] = mapped_column(
        SmallInteger, ForeignKey("ref.article_status_reasons.id"), nullable=True
    )
    custom_key: Mapped[str | None] = mapped_column(CITEXT, nullable=True)
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    is_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CalloutTemplate(Base):
    __tablename__ = "callout_templates"
    __table_args__ = (
        UniqueConstraint("project_id", "slug"),
        {"schema": "content"},
    )

    id: Mapped[str] = _uuid_pk()
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("core.projects.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(CITEXT, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    style: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    external_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)
