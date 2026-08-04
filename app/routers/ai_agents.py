import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_member_for_project
from app.models.core import User
from app.models.ai import Agent, AgentBinding, Provider, ProviderCredential
from app.schemas.ai_agent import AgentInfo, AgentAssignmentPublic, AgentAssignmentCreate, AgentAssignmentUpdate, AgentAssignmentWithDetails
from app.services.agents.agent_registry import list_agents, serialize_agent, get_agent
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings/ai-agents", tags=["ai_agents"])


def _ensure_platform_admin(current_user: User) -> None:
    """Vue plateforme (sans project_id) : réservée aux admins.

    Le premier utilisateur inscrit reçoit is_staff dans auth_service ;
    aucune promotion implicite n'a lieu ici (une lecture ne doit jamais élever
    les privilèges de l'appelant).
    """
    if current_user.is_staff:
        return
    raise HTTPException(status_code=403, detail="Admin access required")


def _ensure_project_admin(project_id: str | None, current_user: User, db: Session) -> None:
    if not project_id:
        _ensure_platform_admin(current_user)
        return
    if current_user.is_staff:
        return
    member = get_member_for_project(db, current_user.id, project_id)
    if not member or member.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Project admin access required")


def _assignment_public(db: Session, binding: AgentBinding) -> AgentAssignmentWithDetails:
    agent_row = db.get(Agent, binding.agent_id)
    agent_key = agent_row.key if agent_row else binding.agent_id
    agent = get_agent(agent_key)
    provider_row = db.get(Provider, binding.provider_id)
    # Modèle affiché : celui de l'agent s'il en a un, sinon celui par défaut
    # du provider (ai.provider_credentials.model) — voir provider_config.py.
    effective_model = binding.model
    if not effective_model and provider_row:
        credential = db.execute(
            select(ProviderCredential).where(
                ProviderCredential.provider_id == provider_row.id,
                ProviderCredential.project_id == binding.project_id,
            )
        ).scalar_one_or_none()
        if credential is None and binding.project_id is not None:
            credential = db.execute(
                select(ProviderCredential).where(
                    ProviderCredential.provider_id == provider_row.id,
                    ProviderCredential.project_id.is_(None),
                )
            ).scalar_one_or_none()
        effective_model = credential.model if credential else None
    return AgentAssignmentWithDetails(
        id=binding.id,
        project_id=binding.project_id,
        agent_id=agent_key,
        provider_code=provider_row.code if provider_row else "",
        model=effective_model,
        enabled=binding.is_enabled,
        priority=binding.priority,
        agent=serialize_agent(agent) if agent else AgentInfo(agent_id=agent_key, name=agent_key, description="", category="other"),
        provider_name=provider_row.code if provider_row else "",
        provider_label=provider_row.label if provider_row else "",
    )


@router.get("", response_model=list[AgentInfo])
def list_all_agents(
    project_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the full canonical agent list — project settings and the global
    admin view both show all 62 agents, aucun n'est masqué."""
    _ensure_project_admin(project_id, current_user, db)
    return [serialize_agent(a) for a in list_agents()]


@router.get("/assignments", response_model=list[AgentAssignmentWithDetails])
def list_assignments(
    project_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_project_admin(project_id, current_user, db)
    query = select(AgentBinding)
    if project_id:
        query = query.where(AgentBinding.project_id == project_id)
    else:
        query = query.where(AgentBinding.project_id.is_(None))
    bindings = db.execute(query.order_by(AgentBinding.agent_id)).scalars().all()
    return [_assignment_public(db, b) for b in bindings]


@router.put("/assignments", response_model=AgentAssignmentWithDetails, status_code=201)
def create_or_update_assignment(
    data: AgentAssignmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_project_admin(data.project_id, current_user, db)
    agent = get_agent(data.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{data.agent_id}' not found")
    if not agent.requires_llm:
        raise HTTPException(
            status_code=400,
            detail=f"L'agent '{data.agent_id}' fonctionne sans LLM (heuristique) — aucun provider ne peut lui être assigné.",
        )
    agent_row = db.execute(select(Agent).where(Agent.key == data.agent_id)).scalar_one_or_none()
    if not agent_row:
        raise HTTPException(status_code=404, detail=f"Agent '{data.agent_id}' not synced (ai.agents)")

    provider_row = db.execute(select(Provider).where(Provider.code == data.provider_code)).scalar_one_or_none()
    if not provider_row:
        raise HTTPException(status_code=404, detail=f"Provider '{data.provider_code}' not found")

    existing = db.execute(
        select(AgentBinding).where(
            AgentBinding.project_id == data.project_id,
            AgentBinding.agent_id == agent_row.id,
        )
    ).scalar_one_or_none()
    if existing:
        existing.provider_id = provider_row.id
        existing.model = data.model
        existing.is_enabled = data.enabled
        existing.priority = data.priority
        db.commit()
        db.refresh(existing)
        binding = existing
    else:
        binding = AgentBinding(
            project_id=data.project_id,
            agent_id=agent_row.id,
            provider_id=provider_row.id,
            model=data.model,
            is_enabled=data.enabled,
            priority=data.priority or 0,
        )
        db.add(binding)
        db.commit()
        db.refresh(binding)

    return _assignment_public(db, binding)


@router.patch("/assignments/{assignment_id}", response_model=AgentAssignmentWithDetails)
def patch_assignment(
    assignment_id: str,
    data: AgentAssignmentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    binding = db.get(AgentBinding, assignment_id)
    if not binding:
        raise HTTPException(status_code=404, detail="Assignment not found")
    _ensure_project_admin(binding.project_id, current_user, db)

    update_data = data.model_dump(exclude_unset=True)
    if "provider_code" in update_data:
        provider_row = db.execute(select(Provider).where(Provider.code == update_data.pop("provider_code"))).scalar_one_or_none()
        if not provider_row:
            raise HTTPException(status_code=404, detail="Provider not found")
        binding.provider_id = provider_row.id
    if "model" in update_data:
        binding.model = update_data.pop("model")
    if "enabled" in update_data:
        binding.is_enabled = update_data.pop("enabled")
    for field, value in update_data.items():
        setattr(binding, field, value)
    db.commit()
    db.refresh(binding)

    return _assignment_public(db, binding)


@router.delete("/assignments/{assignment_id}", status_code=204)
def delete_assignment(
    assignment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    binding = db.get(AgentBinding, assignment_id)
    if not binding:
        raise HTTPException(status_code=404, detail="Assignment not found")
    _ensure_project_admin(binding.project_id, current_user, db)
    db.delete(binding)
    db.commit()
    return None


@router.get("/{agent_id}", response_model=AgentInfo)
def get_agent_info(
    agent_id: str,
    project_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_project_admin(project_id, current_user, db)
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return serialize_agent(agent)
