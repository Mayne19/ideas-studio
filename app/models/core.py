"""Schéma core — utilisateurs, organisations, projets et leur périmètre.

Voir db/migration-v3/REPRENDRE-LA-MAIN.md §5 pour la correspondance avec les
anciens modèles (app/models/user.py, project.py, project_member.py, etc.),
qui restent en place tant que app/routers/ et app/services/ ne sont pas
réécrits (REPRENDRE-LA-MAIN.md §6, étapes 4+).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, ForeignKey, ForeignKeyConstraint, Index, Integer, LargeBinary, SmallInteger, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import CITEXT, ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.reference import CredentialKind


def _uuid_pk() -> Mapped[str]:
    return mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "core"}

    id: Mapped[str] = _uuid_pk()
    email: Mapped[str] = mapped_column(CITEXT, nullable=False, unique=True)
    username: Mapped[str | None] = mapped_column(CITEXT, unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    first_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_staff: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = {"schema": "core"}

    id: Mapped[str] = _uuid_pk()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(CITEXT, nullable=False, unique=True)
    plan: Mapped[str] = mapped_column(Text, nullable=False, default="free")
    created_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)


class OrganizationMember(Base):
    __tablename__ = "organization_members"
    __table_args__ = (
        ForeignKeyConstraint(
            ["status_reason_id", "state_id"],
            ["ref.membership_status_reasons.id", "ref.membership_status_reasons.state_id"],
        ),
        {"schema": "core"},
    )

    organization_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("core.organizations.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("core.users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("ref.member_roles.id"), nullable=False)
    state_id: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    status_reason_id: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=20)
    created_at: Mapped[datetime] = mapped_column(default=_now)


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug"),
        ForeignKeyConstraint(
            ["status_reason_id", "state_id"],
            ["ref.project_status_reasons.id", "ref.project_status_reasons.state_id"],
        ),
        Index("projects_org_status_idx", "organization_id", "state_id", "status_reason_id"),
        {"schema": "core"},
    )

    id: Mapped[str] = _uuid_pk()
    organization_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("core.organizations.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(CITEXT, nullable=False)
    domain: Mapped[str | None] = mapped_column(Text, nullable=True)
    locale: Mapped[str] = mapped_column(Text, nullable=False, default="fr-FR")
    timezone: Mapped[str] = mapped_column(Text, nullable=False, default="Europe/Paris")
    state_id: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    status_reason_id: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=10)
    created_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)
    archived_at: Mapped[datetime | None] = mapped_column(nullable=True)

    editorial_profiles: Mapped[list["EditorialProfile"]] = relationship(back_populates="project", passive_deletes=True)
    publishing_targets: Mapped[list["PublishingTarget"]] = relationship(back_populates="project", passive_deletes=True)
    credentials: Mapped[list["ProjectCredential"]] = relationship(back_populates="project", passive_deletes=True)
    members: Mapped[list["ProjectMember"]] = relationship(back_populates="project", passive_deletes=True)

    @property
    def active_editorial_profile(self) -> "EditorialProfile | None":
        return next((p for p in self.editorial_profiles if p.is_active), None)


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (
        ForeignKeyConstraint(
            ["status_reason_id", "state_id"],
            ["ref.membership_status_reasons.id", "ref.membership_status_reasons.state_id"],
        ),
        {"schema": "core"},
    )

    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("core.projects.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("core.users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("ref.member_roles.id"), nullable=False, default=20)
    state_id: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    status_reason_id: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=20)
    created_at: Mapped[datetime] = mapped_column(default=_now)

    project: Mapped["Project"] = relationship(back_populates="members")


class EditorialProfile(Base):
    """Remplace les colonnes éditoriales éclatées de l'ancien Project (voir
    REPRENDRE-LA-MAIN.md §5, bloc `Project` → éclaté en 5)."""

    __tablename__ = "editorial_profiles"
    __table_args__ = (
        UniqueConstraint("project_id", "version"),
        Index("editorial_profiles_one_active", "project_id", unique=True, postgresql_where=text("is_active")),
        {"schema": "core"},
    )

    id: Mapped[str] = _uuid_pk()
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("core.projects.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    tone: Mapped[str | None] = mapped_column(Text, nullable=True)
    reader_level: Mapped[str | None] = mapped_column(Text, nullable=True)
    writing_style: Mapped[str | None] = mapped_column(Text, nullable=True)
    vertical: Mapped[str | None] = mapped_column(Text, nullable=True)
    word_count_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    word_count_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rules: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    constraints: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("core.users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(default=_now)

    project: Mapped["Project"] = relationship(back_populates="editorial_profiles")


class PublishingTarget(Base):
    __tablename__ = "publishing_targets"
    __table_args__ = {"schema": "core"}

    id: Mapped[str] = _uuid_pk()
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("core.projects.id", ondelete="CASCADE"), nullable=False
    )
    site_url: Mapped[str] = mapped_column(Text, nullable=False)
    revalidate_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Secret propre à ce site, chiffré (Fernet, voir app.core.security). Généré
    # automatiquement à la première configuration — permet à chaque projet
    # d'avoir un secret indépendant plutôt que de partager BLOG_REVALIDATE_SECRET
    # (settings.BLOG_REVALIDATE_SECRET reste le repli si cette colonne est vide).
    revalidate_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Google Analytics 4 propre à ce projet — repli sur settings.GA4_PROPERTY_ID/
    # GOOGLE_SERVICE_ACCOUNT_JSON (variables globales) si absents. Le JSON de
    # service account est chiffré (Fernet), même mécanisme que revalidate_secret.
    ga4_property_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    ga4_service_account_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_sync_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)

    project: Mapped["Project"] = relationship(back_populates="publishing_targets")


class ProjectCredential(Base):
    """Clés de projet en SHA-256 (token_sha256), pas bcrypt : lookup O(1) sur
    chaque événement /tracking/* (voir app/services/tracking_service.py)."""

    __tablename__ = "project_credentials"
    __table_args__ = (
        UniqueConstraint("project_id", "kind", "label"),
        Index("project_credentials_sha_idx", "token_sha256", unique=True, postgresql_where=text("revoked_at IS NULL")),
        {"schema": "core"},
    )

    id: Mapped[str] = _uuid_pk()
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("core.projects.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[CredentialKind] = mapped_column(
        "kind", ENUM(CredentialKind, values_callable=lambda e: [m.value for m in e], name="credential_kind", schema="core", create_type=False), nullable=False
    )
    label: Mapped[str] = mapped_column(Text, nullable=False)
    token_prefix: Mapped[str] = mapped_column(Text, nullable=False)
    token_sha256: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)

    project: Mapped["Project"] = relationship(back_populates="credentials")


class Invitation(Base):
    __tablename__ = "invitations"
    __table_args__ = (
        Index("invitations_token_idx", "token_sha256"),
        {"schema": "core"},
    )

    id: Mapped[str] = _uuid_pk()
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("core.projects.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(CITEXT, nullable=False)
    role_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("ref.member_roles.id"), nullable=False, default=20)
    token_sha256: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    invited_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("core.users.id", ondelete="SET NULL"), nullable=True
    )
    accepted_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("core.users.id", ondelete="SET NULL"), nullable=True
    )
    accepted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=_now)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    __table_args__ = (
        Index("password_reset_token_idx", "token_sha256"),
        {"schema": "core"},
    )

    id: Mapped[str] = _uuid_pk()
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("core.users.id", ondelete="CASCADE"), nullable=False
    )
    token_sha256: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)
