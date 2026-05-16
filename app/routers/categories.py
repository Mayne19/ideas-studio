import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_project_member, require_project_role, get_member_for_project
from app.models.user import User
from app.models.article import Article
from app.models.category import Category
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryPublic
from app.services.category_service import (
    get_categories_for_project,
    get_category_by_id,
    create_category,
    update_category,
    delete_category,
)
from app.core.utils import slugify

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


@router.post("/projects/{project_id}/categories/sync", response_model=list[CategoryPublic])
def sync_categories(
    project_id: str,
    member: ProjectMember = Depends(require_project_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    from fastapi.responses import JSONResponse

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    if not project.domain:
        raise HTTPException(status_code=400, detail="Aucun domaine configuré pour ce projet. Renseignez d'abord le domaine dans les paramètres.")
    synced: list[str] = []

    existing_slugs = {c.slug for c in get_categories_for_project(db, project_id)}
    existing_names = {c.name.lower() for c in get_categories_for_project(db, project_id)}

    # Step 1: fetch categories from the blog via its public API
    blog_fetch_error = None
    if project and project.domain:
        url = f"https://{project.domain}/api/categories"
        try:
            resp = httpx.get(url, timeout=10)
            resp.raise_for_status()
            blog_categories = resp.json()
            if not isinstance(blog_categories, list):
                blog_fetch_error = f"L'API du site a répondu un format inattendu (attendu: liste, reçu: {type(blog_categories).__name__})"
            else:
                for cat in blog_categories:
                    name = cat.get("name", "").strip()
                    slug = cat.get("slug", "").strip()
                    if not name or not slug:
                        continue
                    if name.lower() in existing_names or slug in existing_slugs:
                        continue
                    create_category(db, CategoryCreate(name=name, slug=slug), project_id)
                    existing_names.add(name.lower())
                    existing_slugs.add(slug)
                    synced.append(name)
                if not blog_categories:
                    blog_fetch_error = "Aucune catégorie détectée sur le site connecté."
        except httpx.TimeoutException:
            blog_fetch_error = f"Impossible de joindre le site {project.domain} (timeout)."
        except httpx.HTTPStatusError as e:
            blog_fetch_error = f"L'API du site a retourné une erreur HTTP {e.response.status_code}."
        except Exception:
            blog_fetch_error = f"Erreur de connexion au site {project.domain}."

    # Step 2 (fallback): extract categories from existing articles
    articles = db.query(Article).filter(
        Article.project_id == project_id,
        Article.category_id.isnot(None),
    ).all()

    for article in articles:
        category_obj = db.query(Category).filter(Category.id == article.category_id).first()
        if not category_obj:
            continue
        name = category_obj.name
        if name.lower() in existing_names:
            continue
        new_slug = slugify(name)
        if new_slug in existing_slugs:
            continue
        create_category(db, CategoryCreate(name=name, slug=new_slug, color=category_obj.color), project_id)
        existing_names.add(name.lower())
        existing_slugs.add(new_slug)
        synced.append(name)

    categories = get_categories_for_project(db, project_id)

    # If blog fetch failed and we have no categories at all, surface the error
    if blog_fetch_error and not categories:
        raise HTTPException(status_code=502, detail=blog_fetch_error)

    return JSONResponse(
        content=[CategoryPublic.model_validate(c).model_dump() for c in categories],
        headers={"X-Sync-Message": f"{len(synced)} catégorie(s) importée(s)."} if synced else
                {"X-Sync-Message": blog_fetch_error or "Aucune nouvelle catégorie détectée."},
    )


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
