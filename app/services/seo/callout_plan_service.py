from __future__ import annotations

from sqlalchemy.orm import Session
from app.models.project_callout_template import ProjectCalloutTemplate
from app.schemas.seo_workflow import CalloutPlan, asdict


def build_callout_plan(db: Session, project_id: str, keyword: str, outline: dict | None = None) -> CalloutPlan:
    plan = CalloutPlan()

    templates = db.query(ProjectCalloutTemplate).filter(
        ProjectCalloutTemplate.project_id == project_id,
    ).all()

    if templates:
        for t in templates[:3]:
            plan.callouts.append({
                "title": t.title,
                "text": t.text,
                "type": t.callout_type,
                "main_color": t.main_color,
                "background_color": t.background_color,
                "border_color": t.border_color,
                "text_color": t.text_color,
                "placement": "auto",
                "reason": f"Template existant : {t.title}",
                "source_template_id": t.id,
                "is_ai_generated": False,
            })
    else:
        plan.callouts.append({
            "title": "À retenir",
            "text": f"Le mot-clé principal de cet article est : {keyword}. Gardez-le en tête pendant la lecture.",
            "type": "information importante",
            "main_color": "#2563eb",
            "background_color": "#eff6ff",
            "border_color": "#93c5fd",
            "text_color": "#1e40af",
            "placement": "auto",
            "reason": "Callout générique par défaut",
            "source_template_id": None,
            "is_ai_generated": True,
        })

    return plan


def build_callout_plan_dict(db: Session, project_id: str, keyword: str, outline: dict | None = None) -> dict:
    return asdict(build_callout_plan(db, project_id, keyword, outline))
