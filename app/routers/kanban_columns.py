from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_member_for_project, get_project_member, require_project_role
from app.models.user import User
from app.models.project_member import ProjectMember
from app.models.kanban_column import KanbanColumn
from app.schemas.kanban_column import KanbanColumnCreate, KanbanColumnUpdate, KanbanColumnPublic

router = APIRouter(tags=["kanban_columns"])

_MANAGE_ROLES = ("owner", "admin", "editor")


def _column_to_public(column: KanbanColumn) -> KanbanColumnPublic:
    return KanbanColumnPublic(
        id=column.id,
        project_id=column.project_id,
        label=column.label,
        status=column.status,
        color=column.color,
        sort_order=column.sort_order,
        created_at=column.created_at,
        updated_at=column.updated_at,
    )


@router.get("/projects/{project_id}/kanban-columns", response_model=list[KanbanColumnPublic])
def list_kanban_columns(
    project_id: str,
    member: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    columns = (
        db.query(KanbanColumn)
        .filter(KanbanColumn.project_id == project_id)
        .order_by(KanbanColumn.sort_order, KanbanColumn.created_at)
        .all()
    )
    return [_column_to_public(c) for c in columns]


@router.post("/projects/{project_id}/kanban-columns", response_model=KanbanColumnPublic, status_code=201)
def create_kanban_column(
    project_id: str,
    data: KanbanColumnCreate,
    member: ProjectMember = Depends(require_project_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    status = data.status or f"custom_{data.label.lower().replace(' ', '_')}"
    existing = (
        db.query(KanbanColumn)
        .filter(KanbanColumn.project_id == project_id, KanbanColumn.label == data.label)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Une colonne avec ce nom existe déjà.")
    column = KanbanColumn(
        project_id=project_id,
        label=data.label,
        status=status,
        color=data.color,
        sort_order=data.sort_order,
    )
    db.add(column)
    db.commit()
    db.refresh(column)
    return _column_to_public(column)


@router.patch("/kanban-columns/{column_id}", response_model=KanbanColumnPublic)
def update_kanban_column(
    column_id: str,
    data: KanbanColumnUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    column = db.query(KanbanColumn).filter(KanbanColumn.id == column_id).first()
    if not column:
        raise HTTPException(status_code=404, detail="Colonne introuvable.")
    member = get_member_for_project(db, current_user.id, column.project_id)
    if not member:
        raise HTTPException(status_code=403, detail="Accès refusé.")
    if member.role not in _MANAGE_ROLES:
        raise HTTPException(status_code=403, detail="Permissions insuffisantes.")
    if data.label is not None:
        column.label = data.label
    if data.color is not None:
        column.color = data.color
    if data.sort_order is not None:
        column.sort_order = data.sort_order
    db.commit()
    db.refresh(column)
    return _column_to_public(column)


@router.delete("/kanban-columns/{column_id}", status_code=204)
def delete_kanban_column(
    column_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    column = db.query(KanbanColumn).filter(KanbanColumn.id == column_id).first()
    if not column:
        raise HTTPException(status_code=404, detail="Colonne introuvable.")
    member = get_member_for_project(db, current_user.id, column.project_id)
    if not member:
        raise HTTPException(status_code=403, detail="Accès refusé.")
    if member.role not in _MANAGE_ROLES:
        raise HTTPException(status_code=403, detail="Permissions insuffisantes.")
    db.delete(column)
    db.commit()
