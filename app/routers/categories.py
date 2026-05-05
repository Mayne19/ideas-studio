from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_project_member, require_project_role, get_member_for_project
from app.models.user import User
from app.models.project_member import ProjectMember
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryPublic
from app.services.category_service import (
    get_categories_for_project,
    get_category_by_id,
    create_category,
    update_category,
    delete_category,
)

router = APIRouter(tags=["categories"])

_MANAGE_ROLES = ("owner", "admin", "editor")


@router.get("/projects/{project_id}/categories", response_model=list[CategoryPublic])
def list_categories(
    project_id: str,
    member: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    return get_categories_for_project(db, project_id)


@router.post("/projects/{project_id}/categories", response_model=CategoryPublic, status_code=201)
def create_category_route(
    project_id: str,
    data: CategoryCreate,
    member: ProjectMember = Depends(require_project_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    return create_category(db, data, project_id)


@router.get("/categories/{category_id}", response_model=CategoryPublic)
def get_category_route(
    category_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    category = get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    member = get_member_for_project(db, current_user.id, category.project_id)
    if not member:
        raise HTTPException(status_code=403, detail="Access denied")
    return category


@router.patch("/categories/{category_id}", response_model=CategoryPublic)
def patch_category_route(
    category_id: str,
    data: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    category = get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    member = get_member_for_project(db, current_user.id, category.project_id)
    if not member or member.role not in _MANAGE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return update_category(db, category, data)


@router.delete("/categories/{category_id}", status_code=204)
def delete_category_route(
    category_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    category = get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    member = get_member_for_project(db, current_user.id, category.project_id)
    if not member or member.role not in _MANAGE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    delete_category(db, category)
