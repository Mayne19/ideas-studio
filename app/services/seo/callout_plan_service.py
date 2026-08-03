from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.content import CalloutTemplate
from app.schemas.seo_workflow import CalloutPlan, asdict


def build_callout_plan(db: Session, project_id: str, keyword: str, outline: dict | None = None) -> CalloutPlan:
    plan = CalloutPlan()

    templates = db.execute(
        select(CalloutTemplate).where(CalloutTemplate.project_id == project_id)
    ).scalars().all()

    if templates:
        for t in templates[:3]:
            style = t.style or {}
            plan.callouts.append({
                "title": t.label,
                "text": style.get("text", ""),
                "type": style.get("callout_type", "information"),
                "main_color": style.get("main_color"),
                "background_color": style.get("background_color"),
                "border_color": style.get("border_color"),
                "text_color": style.get("text_color"),
                "placement": "auto",
                "reason": f"Template existant : {t.label}",
                "source_template_id": t.id,
                "is_ai_generated": False,
            })
    else:
        plan.callouts.append({
            "title": "À retenir",
            "text": f"Le mot-clé principal de cet article est : {keyword}. Gardez-le en tête pendant la lecture.",
            "type": "information importante",
            "main_color": "#2563eb",
            "background_color": "#eff6ff",
            "border_color": "#93c5fd",
            "text_color": "#1e40af",
            "placement": "auto",
            "reason": "Callout générique par défaut",
            "source_template_id": None,
            "is_ai_generated": True,
        })

    return plan


def build_callout_plan_dict(db: Session, project_id: str, keyword: str, outline: dict | None = None) -> dict:
    return asdict(build_callout_plan(db, project_id, keyword, outline))
