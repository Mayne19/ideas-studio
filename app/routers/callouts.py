import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.utils import slugify
from app.core.database import get_db
from app.dependencies.auth import get_project_member, require_project_role
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.schemas.callout_template import (
    CalloutTemplateCreate,
    CalloutTemplatePublic,
    CalloutTemplateUpdate,
)
from app.services.callout_template_service import (
    create_callout_template,
    delete_callout_template,
    get_callout_template_by_id,
    list_callout_templates,
    update_callout_template,
)


logger = logging.getLogger("ideas_studio.callouts.sync")
router = APIRouter(tags=["callouts"])
_MANAGE_ROLES = ("owner", "admin", "editor")


def _build_config_url(raw_domain: str) -> str:
    domain = raw_domain.strip()
    if "://" in domain:
        domain = domain.split("://", 1)[1]
    domain = domain.rstrip("/").lstrip("/")
    return f"https://{domain}/api/ideas-studio/config"


def _normalize_site_callout(payload: dict) -> CalloutTemplateCreate:
    colors = payload.get("colors") or {}
    external_id = str(payload.get("id") or payload.get("key") or payload.get("slug") or "").strip() or None
    label = str(payload.get("label") or payload.get("name") or external_id or "").strip()
    if not label:
        raise ValueError("Callout sans label")

    slug = (
        str(payload.get("slug") or payload.get("key") or external_id or slugify(label)).strip()
        or slugify(label)
    )
    style = str(payload.get("style") or payload.get("type") or slug).strip() or None
    return CalloutTemplateCreate(
        slug=slug,
        label=label,
        style=style,
        default_title=(str(payload.get("defaultTitle") or payload.get("default_title") or "").strip() or None),
        color_background=colors.get("background") or payload.get("color_background"),
        color_border=colors.get("border") or payload.get("color_border"),
        color_text=colors.get("text") or payload.get("color_text"),
        icon=(str(payload.get("icon") or "").strip() or None),
        class_name=(str(payload.get("className") or payload.get("class_name") or "").strip() or None),
        source="imported",
        external_id=external_id,
        settings_json=None,
    )


@router.get("/projects/{project_id}/callouts", response_model=list[CalloutTemplatePublic])
def list_project_callouts(
    project_id: str,
    member: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    return list_callout_templates(db, project_id)


@router.post("/projects/{project_id}/callouts", response_model=CalloutTemplatePublic, status_code=201)
def create_project_callout(
    project_id: str,
    data: CalloutTemplateCreate,
    member: ProjectMember = Depends(require_project_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    return create_callout_template(db, data, project_id)


@router.patch("/projects/{project_id}/callouts/{callout_id}", response_model=CalloutTemplatePublic)
def patch_project_callout(
    project_id: str,
    callout_id: str,
    data: CalloutTemplateUpdate,
    member: ProjectMember = Depends(require_project_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    template = get_callout_template_by_id(db, project_id, callout_id)
    if not template:
        raise HTTPException(status_code=404, detail="Callout introuvable.")
    return update_callout_template(db, template, data)


@router.delete("/projects/{project_id}/callouts/{callout_id}", status_code=204)
def delete_project_callout(
    project_id: str,
    callout_id: str,
    member: ProjectMember = Depends(require_project_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    template = get_callout_template_by_id(db, project_id, callout_id)
    if not template:
        raise HTTPException(status_code=404, detail="Callout introuvable.")
    delete_callout_template(db, template)
    return None


@router.post("/projects/{project_id}/callouts/sync", response_model=list[CalloutTemplatePublic])
def sync_project_callouts(
    project_id: str,
    member: ProjectMember = Depends(require_project_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    if not project.domain:
        raise HTTPException(status_code=400, detail="Aucun site externe configuré pour synchroniser les callouts.")

    url = _build_config_url(project.domain)

    try:
        resp = httpx.get(url, timeout=10, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(
                status_code=502,
                detail="Le site connecte n'expose pas encore /api/ideas-studio/config.",
            ) from exc
        raise HTTPException(
            status_code=502,
            detail=f"Impossible de recuperer la configuration callouts du site (HTTP {exc.response.status_code}).",
        ) from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=502, detail="Le site connecte ne repond pas pour la configuration callouts.") from exc
    except Exception as exc:
        logger.warning("Callout sync failed for project_id=%s url=%s error=%s", project_id, url, exc)
        raise HTTPException(status_code=502, detail="Impossible de contacter le site connecte pour les callouts.") from exc

    payload = resp.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=502, detail="Format de configuration callouts invalide.")
    callouts = payload.get("callouts")
    if not isinstance(callouts, list):
        raise HTTPException(status_code=502, detail="La configuration du site ne contient pas de liste callouts valide.")

    existing = list_callout_templates(db, project_id)
    by_external_id = {item.external_id: item for item in existing if item.external_id}
    by_slug = {item.slug: item for item in existing}
    imported = 0
    updated = 0

    for raw in callouts:
        if not isinstance(raw, dict):
            continue
        normalized = _normalize_site_callout(raw)
        template = None
        if normalized.external_id and normalized.external_id in by_external_id:
            template = by_external_id[normalized.external_id]
        elif normalized.slug and normalized.slug in by_slug:
            template = by_slug[normalized.slug]

        if template:
            update_callout_template(
                db,
                template,
                CalloutTemplateUpdate(
                    slug=normalized.slug,
                    label=normalized.label,
                    style=normalized.style,
                    default_title=normalized.default_title,
                    color_background=normalized.color_background,
                    color_border=normalized.color_border,
                    color_text=normalized.color_text,
                    icon=normalized.icon,
                    source="imported",
                    external_id=normalized.external_id,
                    class_name=normalized.class_name,
                ),
            )
            updated += 1
        else:
            created = create_callout_template(db, normalized, project_id)
            by_slug[created.slug] = created
            if created.external_id:
                by_external_id[created.external_id] = created
            imported += 1

    templates = list_callout_templates(db, project_id)
    message = (
        f"{imported} callout(s) importe(s), {updated} mis a jour."
        if (imported or updated)
        else "Aucun nouveau callout detecte."
    )
    return JSONResponse(
        content=[CalloutTemplatePublic.model_validate(item).model_dump(mode="json") for item in templates],
        headers={"X-Sync-Message": message},
    )
