from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decrypt_secret
from app.models.core import Project, PublishingTarget


def _primary_target(db: Session, project_id: str) -> PublishingTarget | None:
    return db.execute(
        select(PublishingTarget)
        .where(PublishingTarget.project_id == project_id)
        .order_by(PublishingTarget.is_primary.desc(), PublishingTarget.created_at.asc())
        .limit(1)
    ).scalar_one_or_none()


def trigger_project_revalidation(
    db: Session,
    project: Project,
    *,
    article: Any | None = None,
    event_type: str = "article.published",
) -> dict:
    target = _primary_target(db, project.id)
    url = (target.revalidate_url if target else None) or settings.BLOG_REVALIDATE_URL
    # Secret propre au projet en priorité (ai.publishing_targets.revalidate_secret),
    # repli sur la variable globale pour compat ascendante — voir docstring du champ.
    secret = (decrypt_secret(target.revalidate_secret) if target else None) or settings.BLOG_REVALIDATE_SECRET

    if not url or not secret:
        if target:
            target.last_sync_status = "not_configured"
            target.last_sync_error = "Aucun endpoint de revalidation configuré."
            target.last_synced_at = datetime.now(timezone.utc)
            db.commit()
        return {"revalidated": False, "status": "not_configured", "message": "Aucun endpoint de revalidation configuré."}

    payload = {
        "secret": secret,
        "projectId": project.id,
        "project_id": project.id,
        "type": event_type,
        "event": event_type,
    }
    if article is not None:
        payload.update({
            "articleId": article.id,
            "article_id": article.id,
            "slug": article.slug,
            "path": f"/{article.slug}",
        })

    headers = {
        "Authorization": f"Bearer {secret}",
        "Cache-Control": "no-store",
        "X-Ideas-Studio-Secret": secret,
        "X-Revalidate-Secret": secret,
    }
    params = {"secret": secret}

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(url, params=params, json=payload, headers=headers)
            resp.raise_for_status()
        if target:
            target.last_sync_status = "success"
            target.last_sync_error = None
            target.last_synced_at = datetime.now(timezone.utc)
            db.commit()
        return {"revalidated": True, "status": "success"}
    except Exception as exc:
        if target:
            target.last_sync_status = "error"
            target.last_sync_error = str(exc)
            target.last_synced_at = datetime.now(timezone.utc)
            db.commit()
        return {"revalidated": False, "status": "error", "message": str(exc)}
