"""Illustrations générées par IA pour un article (mode "ai" des images).

Déroulé, APRÈS la rédaction (on illustre le texte réel, pas le plan) :
1. un appel LLM court (agent media_planner, modèle planner) lit chaque
   section H2 et choisit au plus N-1 sections où une illustration apporte
   vraiment quelque chose, plus une image de couverture ; pour chacune il
   décrit une scène visuelle (en anglais) et rédige l'alt dans la langue de
   l'article ;
2. chaque scène est complétée par le style de marque du projet (preset,
   palette, aucune lettre/logo) puis envoyée au modèle d'image OpenRouter ;
3. l'image est convertie en WebP, stockée (Supabase Storage ou /uploads en
   dev) et enregistrée comme média de l'article.

Les sources renvoyées ont le même format que celles du plan Unsplash
(image_url, section_heading, alt_localized...) : insert_images_in_content,
pick_cover_source et set_cover_image_if_missing les traitent sans cas
particulier côté orchestrateur. Toute erreur est absorbée : au pire,
l'article n'a pas d'image.
"""
from __future__ import annotations

import logging
import re
import time
from html import unescape

from app.services.illustration_settings_service import (
    STYLE_PRESETS,
    IllustrationConfig,
    compose_image_prompt,
)

logger = logging.getLogger(__name__)

GENERATED_SOURCE_NAME = "ai_generated"
GENERATED_RIGHTS = "generated"
IMAGE_AGENT_KEY = "image_generator"

_H2_RE = re.compile(r"<h2[^>]*>(.*?)</h2>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_FIGURE_RE = re.compile(r"<figure\b.*?</figure>", re.IGNORECASE | re.DOTALL)


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", unescape(_TAG_RE.sub(" ", html or ""))).strip()


def extract_sections(content: str, max_chars: int = 700) -> list[dict]:
    """Sections H2 du contenu rédigé : titre + début du texte réel."""
    matches = list(_H2_RE.finditer(content or ""))
    sections = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        body = _FIGURE_RE.sub(" ", content[match.end():end])
        heading = _text(match.group(1))
        if heading:
            sections.append({"heading": heading, "excerpt": _text(body)[:max_chars]})
    return sections


def intro_text(content: str, max_chars: int = 500) -> str:
    first_h2 = _H2_RE.search(content or "")
    head = content[: first_h2.start()] if first_h2 else (content or "")
    head = re.sub(r"<h1[^>]*>.*?</h1>", " ", head, flags=re.IGNORECASE | re.DOTALL)
    return _text(head)[:max_chars]


def build_planner_prompt(
    title: str,
    keyword: str,
    language: str,
    intro: str,
    sections: list[dict],
    section_slots: int,
    include_cover: bool,
    cfg: IllustrationConfig,
) -> str:
    style_label = (
        cfg.custom_style if cfg.style_preset == "custom"
        else (STYLE_PRESETS.get(cfg.style_preset) or {}).get("label", "")
    )
    listing = "\n".join(
        f"{i + 1}. {s['heading']}\n   Texte : {s['excerpt'] or '—'}" for i, s in enumerate(sections)
    )
    cover_rule = (
        "- \"cover\" : une image de couverture qui résume l'idée centrale de l'article.\n"
        if include_cover else "- \"cover\" : null (l'article a déjà une couverture).\n"
    )
    return (
        "Tu es directeur artistique d'une publication sérieuse. Tu prépares des illustrations "
        f"au style constant (« {style_label} »), jamais des photos.\n\n"
        f"Titre : {title}\nMot-clé : {keyword or '—'}\nLangue de l'article : {language}\n"
        f"Introduction : {intro or '—'}\n\nSections rédigées :\n{listing}\n\n"
        "Produis :\n"
        + cover_rule
        + f"- \"sections\" : AU PLUS {section_slots} section(s), uniquement celles où une illustration "
        "aide vraiment à comprendre (un concept, un processus, une comparaison, une situation). "
        "Ignore les sections purement procédurales, les FAQ, les conclusions et les listes. "
        "Liste vide si aucune ne s'y prête.\n\n"
        "Pour chaque image :\n"
        "- \"scene\" : en ANGLAIS, 1 à 3 phrases décrivant une scène ou une métaphore visuelle "
        "concrète tirée du texte de la section (objets, personnages, gestes, schéma), pas un titre "
        "reformulé. Aucun texte, lettre, chiffre, logo ni marque dans l'image. Pas de style ni de "
        "couleurs (ajoutés automatiquement).\n"
        f"- \"alt\" : texte alternatif en langue '{language}', 6 à 15 mots, décrit ce que montre "
        "l'illustration, sans « image de » ni « illustration de ».\n\n"
        "Réponds UNIQUEMENT avec un JSON valide :\n"
        '{"cover": {"scene": "...", "alt": "..."} | null, '
        '"sections": [{"index": 1, "scene": "...", "alt": "..."}]}'
    )


def parse_plan(result, sections: list[dict], section_slots: int, include_cover: bool) -> dict:
    """Plan validé : cover (ou None) + sections (index existants, sans
    doublon, plafonnées à section_slots)."""
    plan: dict = {"cover": None, "sections": []}
    if not isinstance(result, dict):
        return plan

    cover = result.get("cover")
    if include_cover and isinstance(cover, dict) and str(cover.get("scene") or "").strip():
        plan["cover"] = {"scene": str(cover["scene"]).strip(), "alt": str(cover.get("alt") or "").strip()}

    seen: set[int] = set()
    for item in result.get("sections") or []:
        if len(plan["sections"]) >= section_slots:
            break
        if not isinstance(item, dict):
            continue
        try:
            index = int(item.get("index")) - 1
        except (TypeError, ValueError):
            continue
        scene = str(item.get("scene") or "").strip()
        if index in seen or not (0 <= index < len(sections)) or not scene:
            continue
        seen.add(index)
        plan["sections"].append({
            "heading": sections[index]["heading"],
            "scene": scene,
            "alt": str(item.get("alt") or "").strip(),
        })
    return plan


# ── Coûts ──────────────────────────────────────────────────────────────────


def log_usage(
    db,
    *,
    agent_key: str,
    provider_code: str,
    model: str | None,
    project_id: str | None,
    article_id: str | None,
    duration_ms: int,
    estimated_cost: float | None,
    actual_cost: float | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    error: str | None = None,
) -> None:
    """Trace dans ai.usage_events (coût par article). Ne lève jamais."""
    if db is None:
        return
    try:
        from app.models.ai import UsageEvent
        from app.models.reference import StepStatus, set_step_status

        event = UsageEvent(
            agent_key=agent_key,
            provider_code=provider_code,
            model=model,
            project_id=project_id,
            article_id=article_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            duration_ms=duration_ms,
            estimated_cost=round(estimated_cost, 6) if estimated_cost is not None else None,
            actual_cost=round(actual_cost, 6) if actual_cost is not None else None,
            error_message=error,
        )
        set_step_status(event, StepStatus.FAILED if error else StepStatus.SUCCEEDED)
        db.add(event)
        db.commit()
    except Exception:
        logger.warning("illustrations: trace de coût impossible", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass


# ── Planification (LLM) ────────────────────────────────────────────────────


def _planner_provider(db, project_id: str | None):
    """Provider de l'agent media_planner, forcé sur le modèle « planner »
    (OpenRouter) : appel court et bon marché."""
    from app.services.agents.agent_router import get_agent_router

    provider = get_agent_router(db).get_provider("media_planner", project_id=project_id)
    inner = getattr(provider, "_primary", provider)
    if hasattr(inner, "for_role"):
        return inner.for_role("planner")
    return provider


def plan_illustrations(
    db,
    project_id: str | None,
    article_id: str | None,
    prompt: str,
    planner=None,
) -> dict | None:
    """Appel LLM de planification. None si aucun provider réel ou échec."""
    try:
        provider = planner or _planner_provider(db, project_id)
    except Exception as exc:
        logger.warning("illustrations: provider de planification indisponible (%s)", exc)
        return None
    if getattr(provider, "is_mock", False):
        return None

    start = time.perf_counter()
    error = None
    result = None
    try:
        result = provider.generate_json(prompt, schema_hint='{"cover": {...}, "sections": [...]}')
    except Exception as exc:
        error = str(exc)
        logger.warning("illustrations: planification échouée (%s)", exc)

    usage = getattr(provider, "last_usage", None) or {}
    input_tokens = int(usage.get("input_tokens") or 0) or max(1, len(prompt) // 4)
    output_tokens = int(usage.get("output_tokens") or 0) or None
    estimated = None
    try:
        from app.services.cost_estimator import estimate_call_cost

        estimated = estimate_call_cost(
            provider=provider.provider_name, model=provider.model_name,
            input_tokens=input_tokens, output_tokens=output_tokens or 300,
        ).get("estimated_cost_eur")
    except Exception:
        pass
    log_usage(
        db, agent_key="media_planner", provider_code=getattr(provider, "provider_name", None),
        model=getattr(provider, "model_name", None), project_id=project_id, article_id=article_id,
        duration_ms=int((time.perf_counter() - start) * 1000), estimated_cost=estimated,
        actual_cost=estimated if usage else None, prompt_tokens=input_tokens,
        completion_tokens=output_tokens, error=error,
    )
    return result if isinstance(result, dict) else None


# ── Génération + stockage ──────────────────────────────────────────────────


def generate_and_store(
    db,
    image_provider,
    scene: str,
    cfg: IllustrationConfig,
    project_id: str,
    article_id: str | None,
    alt: str,
    store=None,
) -> dict:
    """Génère une image, la stocke et l'enregistre comme média du projet.
    Retourne {"url", "media_id", "prompt", "model", "cost_usd"}. Lève
    ImageGenerationError (ou une erreur de stockage) en cas d'échec — la
    tentative est tracée dans ai.usage_events dans tous les cas."""
    from app.services.providers.image_generation_provider import approx_cost_usd

    if store is None:
        from app.services.storage_service import save_image as store

    full_prompt = compose_image_prompt(scene, cfg)
    start = time.perf_counter()
    try:
        image = image_provider.generate(full_prompt)
    except Exception as exc:
        log_usage(
            db, agent_key=IMAGE_AGENT_KEY, provider_code="openrouter", model=image_provider.model,
            project_id=project_id, article_id=article_id,
            duration_ms=int((time.perf_counter() - start) * 1000), estimated_cost=None, error=str(exc)[:500],
        )
        raise
    estimated = approx_cost_usd(image.model)
    log_usage(
        db, agent_key=IMAGE_AGENT_KEY, provider_code="openrouter", model=image.model,
        project_id=project_id, article_id=article_id,
        duration_ms=int((time.perf_counter() - start) * 1000),
        estimated_cost=image.cost_usd if image.cost_usd is not None else estimated,
        actual_cost=image.cost_usd,
        prompt_tokens=image.usage.get("prompt_tokens"), completion_tokens=image.usage.get("completion_tokens"),
    )

    stored = store(image.data, project_id, image.mime_type, "illustration")
    media_id = None
    if db is not None:
        from app.models.content import MediaAsset

        asset = MediaAsset(
            project_id=project_id,
            url=stored["url"],
            filename=stored.get("filename") or "illustration",
            mime_type=stored.get("mime_type"),
            byte_size=stored.get("byte_size"),
            width=stored.get("width"),
            height=stored.get("height"),
            alt_text=alt or None,
            caption=None,
            source=GENERATED_SOURCE_NAME,
        )
        db.add(asset)
        db.flush()
        media_id = asset.id
    return {
        "url": stored["url"],
        "media_id": media_id,
        "prompt": full_prompt,
        "model": image.model,
        "cost_usd": image.cost_usd if image.cost_usd is not None else estimated,
    }


def _source(stored: dict, heading: str, alt: str, role: str) -> dict:
    return {
        "image_url": stored["url"],
        "media_id": stored.get("media_id"),
        "section_heading": heading,
        "alt_localized": alt,
        "source_name": GENERATED_SOURCE_NAME,
        "usage_rights_status": GENERATED_RIGHTS,
        "role": role,
        "prompt": stored.get("prompt"),
        "model": stored.get("model"),
        "cost_usd": stored.get("cost_usd"),
    }


def generate_illustrations(
    db,
    article,
    content: str,
    title: str,
    keyword: str,
    language: str,
    cfg: IllustrationConfig,
    *,
    image_provider=None,
    planner=None,
    store=None,
    has_cover: bool | None = None,
) -> tuple[list[dict], list[str]]:
    """Retourne (sources d'images, erreurs). Sources vides si rien n'a pu
    être généré (pas de clé OpenRouter, planification vide, échecs)."""
    errors: list[str] = []
    project_id = article.project_id
    article_id = getattr(article, "id", None)

    if cfg.max_images <= 0:
        return [], errors
    if image_provider is None:
        from app.services.providers.image_generation_provider import get_image_provider

        image_provider = get_image_provider(db, project_id, cfg.model)
        if image_provider is None:
            return [], ["Aucune clé OpenRouter configurée (Paramètres → Providers IA)"]

    if has_cover is None:
        has_cover = False
        if db is not None and article_id:
            try:
                from app.services.cover_image_service import get_cover_image_url

                has_cover = bool(get_cover_image_url(db, article_id))
            except Exception:
                has_cover = False
    include_cover = not has_cover
    section_slots = cfg.max_images - (1 if include_cover else 0)

    sections = extract_sections(content)
    prompt = build_planner_prompt(
        title, keyword, language, intro_text(content), sections, section_slots, include_cover, cfg,
    )
    raw_plan = plan_illustrations(db, project_id, article_id, prompt, planner=planner)
    if raw_plan is None:
        return [], ["Planification des illustrations indisponible (provider IA)"]
    plan = parse_plan(raw_plan, sections, section_slots, include_cover)

    jobs: list[tuple[str, str, str, str]] = []  # (role, heading, scene, alt)
    if plan["cover"]:
        jobs.append(("cover", "", plan["cover"]["scene"], plan["cover"]["alt"] or title))
    for item in plan["sections"]:
        jobs.append(("inline", item["heading"], item["scene"], item["alt"] or item["heading"]))

    sources: list[dict] = []
    for role, heading, scene, alt in jobs:
        try:
            stored = generate_and_store(db, image_provider, scene, cfg, project_id, article_id, alt, store=store)
        except Exception as exc:
            errors.append(f"{role} {heading or title}: {exc}")
            logger.warning("illustrations: image %s échouée (%s)", role, exc)
            continue
        source = _source(stored, heading, alt, role)
        if role == "inline" and db is not None and article_id and stored.get("media_id"):
            from app.models.content import ArticleMedia
            from app.models.reference import MediaRole

            db.add(ArticleMedia(
                article_id=article_id, media_id=stored["media_id"], role=MediaRole.INLINE, position=len(sources),
            ))
            db.flush()
        sources.append(source)
    return sources, errors
