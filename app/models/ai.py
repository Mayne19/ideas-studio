"""Schéma ai — providers, catalogue d'agents, pipelines, exécutions et artefacts.

ai.agents est un cache interrogeable, PAS la source de vérité : celle-ci reste
app/services/agents/agent_registry.py (62 AgentDef). Voir
app/scripts/sync_agent_catalog.py et REPRENDRE-LA-MAIN.md §5/§6.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, ForeignKey, ForeignKeyConstraint, Index, Numeric, SmallInteger, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.reference import AgentCategory, AgentRegistryStatus


def _uuid_pk() -> Mapped[str]:
    return mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Provider(Base):
    __tablename__ = "providers"
    __table_args__ = {"schema": "ai"}

    id: Mapped[str] = _uuid_pk()
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ProviderCredential(Base):
    __tablename__ = "provider_credentials"
    __table_args__ = {"schema": "ai"}

    id: Mapped[str] = _uuid_pk()
    provider_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("ai.providers.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("core.projects.id", ondelete="CASCADE"), nullable=True
    )
    secret_ref: Mapped[str] = mapped_column(Text, nullable=False)
    # Modèle utilisé par défaut à chaque appel de ce provider — voir
    # AgentBinding.model : un agent sans modèle explicite hérite de celui-ci.
    model: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Choix explicite de l'utilisateur, jamais déduit automatiquement (pas de
    # "première clé créée" ni de tri implicite) — un seul is_default=true par
    # projet, voir index partiel dans la migration. resolve_default_provider()
    # ne retourne QUE cette ligne, jamais une credential piochée au hasard.
    # Les agents avec un AgentBinding restent inchangés : ils utilisent leur
    # provider assigné, indépendamment de is_default.
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_test_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_test_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)


class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = {"schema": "ai"}

    id: Mapped[str] = _uuid_pk()
    key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[AgentCategory] = mapped_column(
        ENUM(AgentCategory, values_callable=lambda e: [m.value for m in e], name="agent_category", schema="ai", create_type=False),
        nullable=False,
    )
    phase: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[AgentRegistryStatus] = mapped_column(
        ENUM(AgentRegistryStatus, values_callable=lambda e: [m.value for m in e], name="agent_status", schema="ai", create_type=False),
        nullable=False, default=AgentRegistryStatus.PLANNED,
    )
    output_json_field: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_llm: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    requires_search: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    is_visible_in_frontend: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AgentBinding(Base):
    """Dérogation de provider pour un agent (globale si project_id est NULL,
    sinon spécifique au projet). Le routeur d'agents lit cette table avec la
    règle « ligne projet sinon ligne globale »."""

    __tablename__ = "agent_bindings"
    __table_args__ = (
        # Deux index uniques partiels (pas une contrainte flat) : la ligne
        # globale (project_id NULL) et les lignes projet ont chacune leur
        # propre espace d'unicité sur (agent_id, priority) — voir 01-schema.sql.
        Index("agent_bindings_unique_global", "agent_id", "priority", unique=True, postgresql_where="project_id IS NULL"),
        Index("agent_bindings_unique_project", "agent_id", "project_id", "priority", unique=True, postgresql_where="project_id IS NOT NULL"),
        {"schema": "ai"},
    )

    id: Mapped[str] = _uuid_pk()
    agent_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("ai.agents.id", ondelete="CASCADE"), nullable=False
    )
    provider_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("ai.providers.id", ondelete="RESTRICT"), nullable=False
    )
    project_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("core.projects.id", ondelete="CASCADE"), nullable=True
    )
    # Optionnel : si absent, le modèle du ProviderCredential du provider choisi
    # s'applique — un agent n'a besoin que de choisir un provider, pas un modèle.
    model: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Pipeline(Base):
    __tablename__ = "pipelines"
    __table_args__ = {"schema": "ai"}

    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("core.projects.id", ondelete="CASCADE"), primary_key=True
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    articles_per_week: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=5)
    ideas_per_week: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=5)
    max_pending_drafts: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=10)
    max_parallel_jobs: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=2)
    schedule: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    quality_mode: Mapped[str] = mapped_column(Text, nullable=False, default="quality")
    cost_limit_per_article: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    paused_until: Mapped[datetime | None] = mapped_column(nullable=True)
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["status_reason_id", "state_id"],
            ["ref.run_status_reasons.id", "ref.run_status_reasons.state_id"],
        ),
        {"schema": "ai"},
    )

    id: Mapped[str] = _uuid_pk()
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("core.projects.id", ondelete="CASCADE"), nullable=False
    )
    state_id: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    status_reason_id: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=10)
    ideas_generated: Mapped[int] = mapped_column(nullable=False, default=0)
    articles_created: Mapped[int] = mapped_column(nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["status_reason_id", "state_id"],
            ["ref.run_status_reasons.id", "ref.run_status_reasons.state_id"],
        ),
        Index("workflow_runs_article_idx", "article_id", text("started_at DESC")),
        {"schema": "ai"},
    )

    id: Mapped[str] = _uuid_pk()
    article_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("content.articles.id", ondelete="CASCADE"), nullable=False
    )
    pipeline_run_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("ai.pipeline_runs.id", ondelete="SET NULL"), nullable=True
    )
    phase_id: Mapped[int | None] = mapped_column(SmallInteger, ForeignKey("ref.workflow_phases.id"), nullable=True)
    state_id: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    status_reason_id: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=10)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"
    __table_args__ = (
        UniqueConstraint("run_id", "agent_id", "attempt"),
        ForeignKeyConstraint(
            ["status_reason_id", "state_id"],
            ["ref.step_status_reasons.id", "ref.step_status_reasons.state_id"],
        ),
        Index("workflow_steps_run_idx", "run_id", "status_reason_id"),
        {"schema": "ai"},
    )

    id: Mapped[str] = _uuid_pk()
    run_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("ai.workflow_runs.id", ondelete="CASCADE"), nullable=False
    )
    agent_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("ai.agents.id", ondelete="RESTRICT"), nullable=False
    )
    attempt: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    state_id: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    status_reason_id: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=10)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)


class Artifact(Base):
    """Remplace les ~40 colonnes articles.<x>_json de l'ancien modèle. Une ligne
    par (article, agent_key) — voir app/services/seo/helpers.py:save_artifact."""

    __tablename__ = "artifacts"
    __table_args__ = (
        Index("artifacts_article_agent_idx", "article_id", "agent_key", text("created_at DESC")),
        Index("artifacts_payload_gin", "payload", postgresql_using="gin", postgresql_ops={"payload": "jsonb_path_ops"}),
        {"schema": "ai"},
    )

    id: Mapped[str] = _uuid_pk()
    article_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("content.articles.id", ondelete="CASCADE"), nullable=False
    )
    step_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("ai.workflow_steps.id", ondelete="SET NULL"), nullable=True
    )
    agent_key: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=_now)


class UsageEvent(Base):
    """Table partitionnée par mois (ai.usage_events_2026_08, ...) — voir
    db/migration-v3/01-schema.sql. SQLAlchemy mappe la table logique ;
    la création de nouvelles partitions reste un DDL manuel/cron distinct."""

    __tablename__ = "usage_events"
    __table_args__ = (
        Index("usage_project_time_idx", "project_id", text("occurred_at DESC")),
        {"schema": "ai"},
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    occurred_at: Mapped[datetime] = mapped_column(primary_key=True, default=_now)
    project_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    article_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    step_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    agent_key: Mapped[str] = mapped_column(Text, nullable=False)
    provider_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    status_reason_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("ref.step_status_reasons.id"), nullable=False, default=30
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    actual_cost: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
