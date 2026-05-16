import logging
import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
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

logger = logging.getLogger("ideas_studio.categories.sync")

router = APIRouter(tags=["categories"])

_MANAGE_ROLES = ("owner", "admin", "editor")

_DEFAULT_COLOR = "#2563eb"

HEX_COLOR_RE = __import__("re").compile(r"^#[0-9a-fA-F]{6}$")


def _is_valid_hex(v: str | None) -> bool:
    return bool(v and HEX_COLOR_RE.match(v))


def _build_api_url(raw_domain: str, path: str = "/api/categories") -> str:
    domain = raw_domain.strip()
    # Remove protocol prefix if present
    if "://" in domain:
        domain = domain.split("://", 1)[1]
    # Remove trailing slash
    domain = domain.rstrip("/")
    # Remove leading slash (shouldn't happen, but be safe)
    domain = domain.lstrip("/")
    # Remove www. prefix
    domain = domain.removeprefix("www.")
    # Ensure path starts with /
    clean_path = path if path.startswith("/") else f"/{path}"
    return f"https://{domain}{clean_path}"


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
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    if not project.domain:
        raise HTTPException(status_code=400, detail="Aucun domaine configuré pour ce projet. Renseignez d'abord le domaine dans les paramètres.")

    url = _build_api_url(project.domain)
    domain_clean = project.domain.strip().rstrip("/")
    if "://" in domain_clean:
        domain_clean = domain_clean.split("://", 1)[1]
    domain_clean = domain_clean.removeprefix("www.")
    logger.info("Sync categories — project_id=%s domain=%s url=%s", project_id, domain_clean, url)

    synced: list[str] = []
    blog_fetch_error: str | None = None
    blog_categories_raw: list[dict] = []

    existing = get_categories_for_project(db, project_id)
    existing_slugs = {c.slug for c in existing}
    existing_names = {c.name.lower() for c in existing}
    # Map slug -> existing category to preserve manually set colors
    existing_by_slug: dict[str, Category] = {c.slug: c for c in existing}

    # Step 1: fetch categories from the blog via its public API
    try:
        resp = httpx.get(url, timeout=10)
        logger.info("Sync categories — HTTP %s for %s", resp.status_code, url)
        resp.raise_for_status()
        blog_categories_raw = resp.json()
    except httpx.TimeoutException:
        blog_fetch_error = "Impossible de contacter le site connecté. (timeout)"
        logger.warning("Sync categories — timeout project_id=%s url=%s", project_id, url)
    except httpx.HTTPStatusError as e:
        blog_fetch_error = f"Impossible de contacter le site connecté. (HTTP {e.response.status_code})"
        logger.warning("Sync categories — HTTP error project_id=%s url=%s status=%s", project_id, url, e.response.status_code)
    except Exception as e:
        blog_fetch_error = "Impossible de contacter le site connecté."
        logger.warning("Sync categories — connection error project_id=%s url=%s error=%s", project_id, url, e)

    if not isinstance(blog_categories_raw, list):
        if blog_categories_raw:
            logger.warning("Sync categories — invalid format project_id=%s type=%s raw=%s", project_id, type(blog_categories_raw).__name__, blog_categories_raw)
            blog_fetch_error = f"L'API du site a répondu un format inattendu (attendu: liste, reçu: {type(blog_categories_raw).__name__})"
        blog_categories_raw = []
    elif not blog_categories_raw:
        blog_fetch_error = "Aucune catégorie détectée sur le site connecté."
        logger.info("Sync categories — empty list project_id=%s", project_id)

    for cat in blog_categories_raw:
        name = (cat.get("name") or "").strip()
        slug = (cat.get("slug") or "").strip()
        if not name or not slug:
            logger.info("Sync categories — skipped entry missing name/slug project_id=%s entry=%s", project_id, cat)
            continue
        if name.lower() in existing_names or slug in existing_slugs:
            # Category already exists — optionally update color if blog provides one and user hasn't manually changed it
            existing_cat = existing_by_slug.get(slug)
            color = (cat.get("color") or "").strip() or None
            if color and existing_cat and not _is_valid_hex(existing_cat.color):
                # Only set color if the existing category has no valid color (was auto-assigned)
                existing_cat.color = color.lower()
                logger.info("Sync categories — updated color for existing slug=%s color=%s", slug, color)
            continue
        color = (cat.get("color") or "").strip() or None
        if not _is_valid_hex(color):
            color = None  # Will get default from create_category
        create_category(db, CategoryCreate(name=name, slug=slug, color=color), project_id)
        existing_names.add(name.lower())
        existing_slugs.add(slug)
        synced.append(name)
        logger.info("Sync categories — imported slug=%s name=%s color=%s", slug, name, color or _DEFAULT_COLOR)

    if synced:
        db.commit()

    # Step 2 (fallback): extract categories from existing articles if blog fetch failed
    if blog_fetch_error and not existing:
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
            color = category_obj.color if _is_valid_hex(category_obj.color) else None
            create_category(db, CategoryCreate(name=name, slug=new_slug, color=color), project_id)
            existing_names.add(name.lower())
            existing_slugs.add(new_slug)
            synced.append(name)
            logger.info("Sync categories — fallback imported slug=%s name=%s color=%s", new_slug, name, color or _DEFAULT_COLOR)

    if synced:
        db.commit()

    categories = get_categories_for_project(db, project_id)

    # If blog fetch failed and we have no categories at all, surface the error
    if blog_fetch_error and not categories:
        raise HTTPException(status_code=502, detail=blog_fetch_error)

    message = ""
    if synced:
        count = len(synced)
        message = f"{count} catégorie{'s' if count > 1 else ''} synchronisée{'s' if count > 1 else ''}."
    elif blog_fetch_error:
        message = blog_fetch_error
    else:
        message = "Aucune nouvelle catégorie détectée."

    return JSONResponse(
        content=[CategoryPublic.model_validate(c).model_dump() for c in categories],
        headers={"X-Sync-Message": message},
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
