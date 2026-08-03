from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import MemberView, get_current_user, get_member_for_project, get_project_member, require_project_role
from app.models.core import User
from app.models.content import BoardColumn
from app.schemas.kanban_column import KanbanColumnCreate, KanbanColumnUpdate, KanbanColumnPublic

router = APIRouter(tags=["kanban_columns"])

_MANAGE_ROLES = ("owner", "admin", "editor")


def _column_to_public(column: BoardColumn) -> KanbanColumnPublic:
    return KanbanColumnPublic(
        id=column.id,
        project_id=column.project_id,
        label=column.label or "",
        status=column.custom_key or str(column.status_reason_id),
        color=column.color,
        sort_order=column.sort_order,
    )


@router.get("/projects/{project_id}/kanban-columns", response_model=list[KanbanColumnPublic])
def list_kanban_columns(
    project_id: str,
    member: MemberView = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    columns = db.execute(
        select(BoardColumn)
        .where(BoardColumn.project_id == project_id)
        .order_by(BoardColumn.sort_order, BoardColumn.id)
    ).scalars().all()
    return [_column_to_public(c) for c in columns]


@router.post("/projects/{project_id}/kanban-columns", response_model=KanbanColumnPublic, status_code=201)
def create_kanban_column(
    project_id: str,
    data: KanbanColumnCreate,
    member: MemberView = Depends(require_project_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    custom_key = data.status or f"custom_{data.label.lower().replace(' ', '_')}"
    existing = db.execute(
        select(BoardColumn).where(BoardColumn.project_id == project_id, BoardColumn.label == data.label)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Une colonne avec ce nom existe déjà.")
    column = BoardColumn(
        project_id=project_id,
        custom_key=custom_key,
        label=data.label,
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
    column = db.get(BoardColumn, column_id)
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
    column = db.get(BoardColumn, column_id)
    if not column:
        raise HTTPException(status_code=404, detail="Colonne introuvable.")
    member = get_member_for_project(db, current_user.id, column.project_id)
    if not member:
        raise HTTPException(status_code=403, detail="Accès refusé.")
    if member.role not in _MANAGE_ROLES:
        raise HTTPException(status_code=403, detail="Permissions insuffisantes.")
    db.delete(column)
    db.commit()
