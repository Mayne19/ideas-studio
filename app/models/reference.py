"""Tables ref.* — lecture seule côté application.

Ces tables sont peuplées uniquement par db/migration-v3/01-schema.sql, jamais
par l'ORM. Les IntEnum ci-dessous en sont le miroir Python : un test dédié
(tests/test_reference_sync.py) compare les deux et échoue si elles divergent —
c'est la seule discipline à tenir dans la durée (plan-migration-v3.md §2).
"""
from __future__ import annotations

from enum import IntEnum, StrEnum

from sqlalchemy import Boolean, ForeignKey, SmallInteger, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


# ── Miroirs Python des tables ref.* (valeurs = id en base) ────────────────────


class State(IntEnum):
    ACTIVE = 0
    INACTIVE = 1


class ProjectStatus(IntEnum):
    NOT_CONNECTED = 10
    CONNECTED = 20
    ARCHIVED = 30


# state_id à poser en même temps que status_reason_id — la FK composite
# ref.project_status_reasons(id, state_id) rejette toute autre paire
# (voir db/migration-v3/01-schema.sql).
STATE_ID_BY_PROJECT_STATUS: dict[int, int] = {
    ProjectStatus.NOT_CONNECTED: State.ACTIVE,
    ProjectStatus.CONNECTED: State.ACTIVE,
    ProjectStatus.ARCHIVED: State.INACTIVE,
}


class ArticleStatus(IntEnum):
    DRAFT = 10
    IDEA_PROPOSED = 20
    IDEA_PRIORITY = 30
    OUTLINE_READY = 40
    WRITING_REQUESTED = 50
    WRITING_IN_PROGRESS = 60
    DRAFT_READY = 70
    REVIEW_NEEDED = 80
    CORRECTION_NEEDED = 90
    READY_TO_PUBLISH = 100
    SCHEDULED = 110
    PUBLISHED = 120
    UNPUBLISHED = 130
    UPDATE_RECOMMENDED = 140
    IMPROVEMENT_PROPOSED = 150
    IMPROVEMENT_IN_PROGRESS = 160
    IMPROVEMENT_READY = 170
    FAILED = 180
    BLOCKED_COST_LIMIT = 190
    IDEA_REJECTED = 200
    ARCHIVED = 210


# status_reason_id pour lesquels published_revision_id est obligatoire
# (trigger content.enforce_publication_rules). "scheduled" en est exclu :
# voir le commentaire sur ref.article_status_reasons dans le DDL.
ARTICLE_STATUSES_REQUIRING_REVISION = frozenset({ArticleStatus.PUBLISHED, ArticleStatus.UNPUBLISHED})

# status_reason_id éditable par un rôle "designer" (DESIGNER_EDITABLE_STATUSES historique)
ARTICLE_STATUSES_DESIGNER_EDITABLE = frozenset({
    ArticleStatus.DRAFT,
    ArticleStatus.DRAFT_READY,
    ArticleStatus.REVIEW_NEEDED,
    ArticleStatus.CORRECTION_NEEDED,
    ArticleStatus.READY_TO_PUBLISH,
})

# Motifs qui font d'un article une "idée" (page /projects/:id/ideas)
IDEA_ARTICLE_STATUSES = frozenset({
    ArticleStatus.DRAFT,
    ArticleStatus.IDEA_PROPOSED,
    ArticleStatus.IDEA_PRIORITY,
    ArticleStatus.IDEA_REJECTED,
})

# state_id à poser en même temps que status_reason_id — la FK composite
# ref.article_status_reasons(id, state_id) rejette toute autre paire. Seuls
# IDEA_REJECTED et ARCHIVED sont INACTIVE, tout le reste est ACTIVE (voir
# db/migration-v3/01-schema.sql, bloc ref.article_status_reasons).
STATE_ID_BY_ARTICLE_STATUS: dict[int, int] = {
    status: (State.INACTIVE if status in (ArticleStatus.IDEA_REJECTED, ArticleStatus.ARCHIVED) else State.ACTIVE)
    for status in ArticleStatus
}


class MembershipStatus(IntEnum):
    INVITED = 10
    ACTIVE = 20
    SUSPENDED = 30
    REMOVED = 40


STATE_ID_BY_MEMBERSHIP_STATUS: dict[int, int] = {
    MembershipStatus.INVITED: State.ACTIVE,
    MembershipStatus.ACTIVE: State.ACTIVE,
    MembershipStatus.SUSPENDED: State.INACTIVE,
    MembershipStatus.REMOVED: State.INACTIVE,
}


class RunStatus(IntEnum):
    QUEUED = 10
    RUNNING = 20
    SUCCEEDED = 30
    FAILED = 40
    CANCELLED = 50


STATE_ID_BY_RUN_STATUS: dict[int, int] = {
    RunStatus.QUEUED: State.ACTIVE,
    RunStatus.RUNNING: State.ACTIVE,
    RunStatus.SUCCEEDED: State.INACTIVE,
    RunStatus.FAILED: State.INACTIVE,
    RunStatus.CANCELLED: State.INACTIVE,
}


class StepStatus(IntEnum):
    PENDING = 10
    RUNNING = 20
    SUCCEEDED = 30
    FAILED = 40
    SKIPPED = 50


STATE_ID_BY_STEP_STATUS: dict[int, int] = {
    StepStatus.PENDING: State.ACTIVE,
    StepStatus.RUNNING: State.ACTIVE,
    StepStatus.SUCCEEDED: State.INACTIVE,
    StepStatus.FAILED: State.INACTIVE,
    StepStatus.SKIPPED: State.INACTIVE,
}


class WorkflowPhase(IntEnum):
    IDEA_PREBRIEF = 10
    PLANNING = 20
    PRODUCTION = 30
    QUALITY = 40
    COMPLETED = 50


class MemberRole(IntEnum):
    VIEWER = 10
    DESIGNER = 20
    EDITOR = 30
    ADMIN = 40
    OWNER = 50


# rank >= MANAGE_ROLE_MIN_RANK reproduit _MANAGE_ROLES ("owner","admin","editor")
MANAGE_ROLE_MIN_RANK = MemberRole.EDITOR
# rank >= DESIGN_ROLE_MIN_RANK : peut éditer un article en attente de design
DESIGN_ROLE_MIN_RANK = MemberRole.DESIGNER


class LogLevel(IntEnum):
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40


# ── Miroirs des ENUM Postgres natifs (core.credential_kind, etc.) ─────────────


class CredentialKind(StrEnum):
    TRACKING = "tracking"
    API = "api"
    REVALIDATE = "revalidate"
    WEBHOOK = "webhook"


class RevisionSource(StrEnum):
    AI = "ai"
    HUMAN = "human"
    IMPORT = "import"
    ROLLBACK = "rollback"


class KeywordRole(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    ENTITY = "entity"


class LinkKind(StrEnum):
    INTERNAL = "internal"
    EXTERNAL = "external"


class MediaRole(StrEnum):
    COVER = "cover"
    INLINE = "inline"
    THUMBNAIL = "thumbnail"
    OG = "og"


class AgentCategory(StrEnum):
    RESEARCH = "research"
    STRATEGY = "strategy"
    CREATION = "creation"
    REVIEW = "review"


class AgentRegistryStatus(StrEnum):
    ACTIVE = "active"
    HEURISTIC = "heuristic"
    PARTIAL = "partial"
    PLANNED = "planned"
    DISABLED = "disabled"
    NOT_IMPLEMENTED = "not_implemented"


# ── Modèles SQLAlchemy en lecture seule (schéma ref) ──────────────────────────


class RefStates(Base):
    __tablename__ = "states"
    __table_args__ = {"schema": "ref"}

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    label: Mapped[str] = mapped_column(Text, nullable=False)


class RefProjectStatusReason(Base):
    __tablename__ = "project_status_reasons"
    __table_args__ = (
        UniqueConstraint("id", "state_id"),
        {"schema": "ref"},
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    state_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("ref.states.id"), nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class RefArticleStatusReason(Base):
    __tablename__ = "article_status_reasons"
    __table_args__ = (
        UniqueConstraint("id", "state_id"),
        {"schema": "ref"},
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    state_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("ref.states.id"), nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_board_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_revision: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    designer_editable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class RefMembershipStatusReason(Base):
    __tablename__ = "membership_status_reasons"
    __table_args__ = (
        UniqueConstraint("id", "state_id"),
        {"schema": "ref"},
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    state_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("ref.states.id"), nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class RefRunStatusReason(Base):
    __tablename__ = "run_status_reasons"
    __table_args__ = (
        UniqueConstraint("id", "state_id"),
        {"schema": "ref"},
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    state_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("ref.states.id"), nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class RefStepStatusReason(Base):
    __tablename__ = "step_status_reasons"
    __table_args__ = (
        UniqueConstraint("id", "state_id"),
        {"schema": "ref"},
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    state_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("ref.states.id"), nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class RefWorkflowPhase(Base):
    __tablename__ = "workflow_phases"
    __table_args__ = {"schema": "ref"}

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)


class RefMemberRole(Base):
    __tablename__ = "member_roles"
    __table_args__ = {"schema": "ref"}

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    rank: Mapped[int] = mapped_column(SmallInteger, nullable=False)


class RefLogLevel(Base):
    __tablename__ = "log_levels"
    __table_args__ = {"schema": "ref"}

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[int] = mapped_column(SmallInteger, nullable=False)


# ── Setters state_id + status_reason_id ────────────────────────────────────
# Toute écriture de status_reason_id doit passer par ces fonctions : les FK
# composites ref.*_status_reasons(id, state_id) rejettent un state_id qui ne
# correspond pas exactement au status_reason_id (voir STATE_ID_BY_* ci-dessus).
# Assigner status_reason_id seul laisse state_id à sa valeur précédente (ou au
# défaut de colonne 0) et casse le flush dès que le statut cible est INACTIVE.


def set_article_status(article, status: "ArticleStatus") -> None:
    article.status_reason_id = status
    article.state_id = STATE_ID_BY_ARTICLE_STATUS[status]


def set_project_status(project, status: "ProjectStatus") -> None:
    project.status_reason_id = status
    project.state_id = STATE_ID_BY_PROJECT_STATUS[status]


def set_run_status(run, status: "RunStatus") -> None:
    run.status_reason_id = status
    run.state_id = STATE_ID_BY_RUN_STATUS[status]


def set_step_status(step, status: "StepStatus") -> None:
    step.status_reason_id = status
    step.state_id = STATE_ID_BY_STEP_STATUS[status]


def set_membership_status(member, status: "MembershipStatus") -> None:
    member.status_reason_id = status
    member.state_id = STATE_ID_BY_MEMBERSHIP_STATUS[status]
