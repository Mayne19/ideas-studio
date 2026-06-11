from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.article import Article
from app.models.category import Category
from app.models.media_asset import MediaAsset

router = APIRouter(tags=["search"])


@router.get("/search")
def global_search(
    q: str,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not q or not q.strip():
        return {"results": [], "total": 0}

    query = q.strip()
    member_project_ids = [
        m.project_id for m in db.query(ProjectMember)
        .filter(ProjectMember.user_id == current_user.id, ProjectMember.status == "active")
        .all()
    ]

    if not member_project_ids:
        return {"results": [], "total": 0}

    results = []

    # Search articles
    articles = (
        db.query(Article)
        .filter(
            Article.project_id.in_(member_project_ids),
            or_(
                Article.title.ilike(f"%{query}%"),
                Article.slug.ilike(f"%{query}%"),
                Article.content.ilike(f"%{query}%"),
                Article.keyword.ilike(f"%{query}%"),
                Article.excerpt.ilike(f"%{query}%"),
            ),
        )
        .limit(limit)
        .all()
    )
    for a in articles:
        project = db.query(Project).filter(Project.id == a.project_id).first()
        results.append({
            "type": "article",
            "id": a.id,
            "title": a.title,
            "slug": a.slug,
            "excerpt": a.excerpt,
            "url": f"/projects/{a.project_id}/articles/{a.id}",
            "project_id": a.project_id,
            "project_name": project.name if project else None,
            "status": a.status,
            "updated_at": a.updated_at.isoformat() if a.updated_at else None,
        })

    # Search categories
    categories = (
        db.query(Category)
        .filter(
            Category.project_id.in_(member_project_ids),
            or_(
                Category.name.ilike(f"%{query}%"),
                Category.description.ilike(f"%{query}%"),
            ),
        )
        .limit(limit)
        .all()
    )
    for c in categories:
        project = db.query(Project).filter(Project.id == c.project_id).first()
        results.append({
            "type": "category",
            "id": c.id,
            "title": c.name,
            "slug": c.slug,
            "excerpt": c.description,
            "url": f"/projects/{c.project_id}/categories",
            "project_id": c.project_id,
            "project_name": project.name if project else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        })

    # Search projects
    projects = (
        db.query(Project)
        .filter(
            Project.id.in_(member_project_ids),
            Project.name.ilike(f"%{query}%"),
        )
        .limit(limit)
        .all()
    )
    for p in projects:
        results.append({
            "type": "project",
            "id": p.id,
            "title": p.name,
            "slug": p.name,
            "excerpt": p.domain,
            "url": f"/projects/{p.id}",
            "project_id": p.id,
            "project_name": p.name,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        })

    return {"results": results, "total": len(results)}
