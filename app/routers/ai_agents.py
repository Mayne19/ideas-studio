import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_member_for_project
from app.models.user import User
from app.models.ai_provider_config import AIProviderConfig
from app.schemas.ai_agent import AgentInfo, AgentAssignmentPublic, AgentAssignmentCreate, AgentAssignmentUpdate, AgentAssignmentWithDetails
from app.services.agents.agent_registry import list_agents, serialize_agent, get_agent
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings/ai-agents", tags=["ai_agents"])


def _ensure_admin(current_user: User, db: Session) -> None:
    if current_user.is_platform_admin:
        return
    admin_exists = db.query(User.id).filter(User.is_platform_admin == True).first()
    if not admin_exists:
        current_user.is_platform_admin = True
        db.commit()
        db.refresh(current_user)
        return
    raise HTTPException(status_code=403, detail="Admin access required")


def _ensure_project_admin(project_id: str | None, current_user: User, db: Session) -> None:
    if not project_id:
        _ensure_admin(current_user, db)
        return
    if current_user.is_platform_admin:
        return
    member = get_member_for_project(db, current_user.id, project_id)
    if not member or member.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Project admin access required")


def _assignment_public(ass, db: Session) -> AgentAssignmentWithDetails:
    agent = get_agent(ass.agent_id)
    provider = db.query(AIProviderConfig).filter(AIProviderConfig.id == ass.provider_id).first()
    return AgentAssignmentWithDetails(
        id=ass.id,
        project_id=ass.project_id,
        agent_id=ass.agent_id,
        provider_id=ass.provider_id,
        enabled=ass.enabled,
        priority=ass.priority,
        created_at=ass.created_at.isoformat() if hasattr(ass.created_at, 'isoformat') else str(ass.created_at),
        updated_at=ass.updated_at.isoformat() if hasattr(ass.updated_at, 'isoformat') else str(ass.updated_at),
        agent=serialize_agent(agent) if agent else AgentInfo(agent_id=ass.agent_id, name=ass.agent_id, description="", category="other"),
        provider_name=provider.provider if provider else "",
        provider_label=provider.label if provider else "",
    )


@router.get("", response_model=list[AgentInfo])
def list_all_agents(
    project_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the canonical list of all 27 agents."""
    _ensure_project_admin(project_id, current_user, db)
    return [serialize_agent(a) for a in list_agents()]


@router.get("/assignments", response_model=list[AgentAssignmentWithDetails])
def list_assignments(
    project_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_project_admin(project_id, current_user, db)
    try:
        from app.models.agent_assignment import AgentAssignment
    except ImportError:
        return []

    query = db.query(AgentAssignment)
    if project_id:
        query = query.filter(AgentAssignment.project_id == project_id)
    else:
        query = query.filter(AgentAssignment.project_id.is_(None))
    assignments = query.order_by(AgentAssignment.agent_id).all()
    return [_assignment_public(ass, db) for ass in assignments]


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

    provider = db.query(AIProviderConfig).filter(AIProviderConfig.id == data.provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{data.provider_id}' not found")
    if provider.project_id != data.project_id:
        raise HTTPException(status_code=403, detail="Provider does not belong to this project")

    try:
        from app.models.agent_assignment import AgentAssignment
    except ImportError:
        raise HTTPException(status_code=500, detail="AgentAssignment model not available")

    existing = db.query(AgentAssignment).filter(
        AgentAssignment.project_id == data.project_id,
        AgentAssignment.agent_id == data.agent_id,
    ).first()
    if existing:
        existing.provider_id = data.provider_id
        existing.enabled = data.enabled
        existing.priority = data.priority
        db.commit()
        db.refresh(existing)
        ass = existing
    else:
        from app.models.agent_assignment import AgentAssignment as AA
        ass = AA(
            project_id=data.project_id,
            agent_id=data.agent_id,
            provider_id=data.provider_id,
            enabled=data.enabled,
            priority=data.priority or 0,
        )
        db.add(ass)
        db.commit()
        db.refresh(ass)

    return _assignment_public(ass, db)


@router.patch("/assignments/{assignment_id}", response_model=AgentAssignmentWithDetails)
def patch_assignment(
    assignment_id: str,
    data: AgentAssignmentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        from app.models.agent_assignment import AgentAssignment
    except ImportError:
        raise HTTPException(status_code=500, detail="AgentAssignment model not available")

    ass = db.query(AgentAssignment).filter(AgentAssignment.id == assignment_id).first()
    if not ass:
        raise HTTPException(status_code=404, detail="Assignment not found")
    _ensure_project_admin(ass.project_id, current_user, db)

    update_data = data.model_dump(exclude_unset=True)
    if "provider_id" in update_data:
        provider = db.query(AIProviderConfig).filter(AIProviderConfig.id == update_data["provider_id"]).first()
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        if provider.project_id != ass.project_id:
            raise HTTPException(status_code=403, detail="Provider does not belong to this project")

    from datetime import datetime, timezone
    for field, value in update_data.items():
        setattr(ass, field, value)
    ass.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ass)

    return _assignment_public(ass, db)


@router.delete("/assignments/{assignment_id}", status_code=204)
def delete_assignment(
    assignment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        from app.models.agent_assignment import AgentAssignment
    except ImportError:
        raise HTTPException(status_code=500, detail="AgentAssignment model not available")

    ass = db.query(AgentAssignment).filter(AgentAssignment.id == assignment_id).first()
    if not ass:
        raise HTTPException(status_code=404, detail="Assignment not found")
    _ensure_project_admin(ass.project_id, current_user, db)
    db.delete(ass)
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
