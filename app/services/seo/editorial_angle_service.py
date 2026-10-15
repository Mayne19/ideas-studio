from __future__ import annotations

from app.schemas.seo_workflow import EditorialAngle, asdict


def define_editorial_angle(
    title: str,
    keyword: str,
    intent_analysis: dict | None = None,
    research_brief: dict | None = None,
    category_name: str | None = None,
) -> EditorialAngle:
    """Angle dérivé du brief d'intention affiné (question réelle, réponse
    attendue, pièges) plutôt que d'un gabarit générique par type d'article."""
    intent = intent_analysis or {}
    question = (intent.get("reader_real_question") or title or keyword or "").strip()
    expected = (intent.get("expected_answer") or "").strip()
    avoid = [str(x) for x in (intent.get("must_avoid") or intent.get("what_to_avoid") or []) if str(x).strip()]

    return EditorialAngle(
        editorial_promise=f"Répondre précisément à : {question}",
        main_angle=(intent.get("recommended_angle") or "").strip() or f"Réponse directe à : {question}",
        reader_benefit=expected,
        differentiation=("Éviter : " + " ; ".join(avoid[:3])) if avoid else "",
        tone="",
        eeat_opportunities=[str(x) for x in (intent.get("must_include") or [])][:5],
    )


def define_editorial_angle_dict(
    title: str,
    keyword: str,
    intent_analysis: dict | None = None,
    research_brief: dict | None = None,
    category_name: str | None = None,
) -> dict:
    return asdict(define_editorial_angle(title, keyword, intent_analysis, research_brief, category_name))
