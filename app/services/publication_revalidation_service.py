from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decrypt_secret
from app.models.project import Project


def trigger_project_revalidation(
    db: Session,
    project: Project,
    *,
    article: Any | None = None,
    event_type: str = "article.published",
) -> dict:
    url = project.revalidate_url or settings.BLOG_REVALIDATE_URL
    secret = decrypt_secret(project.revalidate_secret_encrypted) if project.revalidate_secret_encrypted else settings.BLOG_REVALIDATE_SECRET

    if not url or not secret:
        project.last_revalidate_status = "not_configured"
        project.last_revalidate_error = "Aucun endpoint de revalidation configuré."
        project.last_revalidated_at = datetime.now(timezone.utc)
        db.commit()
        return {"revalidated": False, "status": "not_configured", "message": project.last_revalidate_error}

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
        project.last_revalidate_status = "success"
        project.last_revalidate_error = None
        project.last_revalidated_at = datetime.now(timezone.utc)
        db.commit()
        return {"revalidated": True, "status": "success"}
    except Exception as exc:
        project.last_revalidate_status = "error"
        project.last_revalidate_error = str(exc)
        project.last_revalidated_at = datetime.now(timezone.utc)
        db.commit()
        return {"revalidated": False, "status": "error", "message": str(exc)}
