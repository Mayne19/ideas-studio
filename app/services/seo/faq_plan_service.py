from __future__ import annotations

from app.schemas.seo_workflow import FAQPlan, asdict


def build_faq_plan(keyword: str, intent_analysis: dict | None = None) -> FAQPlan:
    plan = FAQPlan()

    intent = intent_analysis or {}
    sub_questions = intent.get("sub_questions", [])

    if sub_questions and len(sub_questions) >= 2:
        for q in sub_questions[:6]:
            plan.faq.append({
                "question": q,
                "answer": f"Réponse à : {q}. (à développer)",
            })
        plan.faq_generated = True
        plan.faq_reason = f"{len(plan.faq)} questions générées depuis l'analyse d'intention"
    else:
        plan.faq_generated = False
        plan.faq_reason = "Pas assez de questions utiles pour générer une FAQ"

    return plan


def build_faq_plan_dict(keyword: str, intent_analysis: dict | None = None) -> dict:
    return asdict(build_faq_plan(keyword, intent_analysis))


def generate_faq_list(faq_from_plan: list[dict] | None, llm_faq: str | None) -> list[dict]:
    if faq_from_plan and len(faq_from_plan) >= 2:
        return faq_from_plan[:6]
    if llm_faq:
        import json
        try:
            items = json.loads(llm_faq)
            if isinstance(items, list):
                return items[:6]
        except (json.JSONDecodeError, TypeError):
            pass
    return []
