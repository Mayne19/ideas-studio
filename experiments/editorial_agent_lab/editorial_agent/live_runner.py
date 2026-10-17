"""Exécution réelle, isolée, du rédacteur unique.

Ce module ne modifie pas le CMS et ne publie rien. Il réutilise seulement ses
adaptateurs de recherche/lecture et son client OpenRouter/Anthropic. Le modèle
fait la recherche, la lecture, l'analyse sémantique, le plan, la rédaction et
la relecture dans une même conversation, comme le processus observé dans
Claude. Les contrôles qui suivent sont déterministes et ne réécrivent jamais
le texte.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import Any

from dotenv import load_dotenv

from .existing_pipeline_adapter import ExistingPipelineWebAdapter, from_ideas_studio
from .prompting import load_system_prompt


class LiveRunError(RuntimeError):
    """La configuration ou le fournisseur réel empêche l'essai."""


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
# L'interface locale est un processus séparé du backend FastAPI. Charger le
# fichier du dépôt permet toutefois de réutiliser exactement les variables du
# runtime quand il existe, sans jamais les recopier dans le laboratoire.
load_dotenv(REPOSITORY_ROOT / ".env", override=False)


@dataclass(frozen=True)
class LiveRunConfig:
    keyword: str
    site_name: str
    domain: str
    language: str = "français"
    country: str = "France"
    category: str = ""
    editor_notes: str = ""
    project_id: str | None = None
    model: str | None = None
    max_cost_usd: float = 3.0
    max_searches: int = 10
    max_fetches: int = 15
    output_dir: Path = Path("experiments/editorial_agent_lab/run")


def _env_value(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return None


def resolve_model_route(project_id: str | None = None) -> tuple[str, str, str]:
    """Résout la route sans afficher ni écrire de secret.

    Priorité : variables d'environnement explicites, puis credentials déjà
    configurées dans le CMS si le runtime de l'application est disponible.
    """

    anthropic_key = _env_value("ANTHROPIC_API_KEY")
    if anthropic_key:
        return "anthropic", anthropic_key, _env_value("ANTHROPIC_MODEL") or "claude-opus-5-5"

    openrouter_key = _env_value("OPENROUTER_API_KEY")
    if openrouter_key:
        return "openrouter", openrouter_key, (
            _env_value("OPENROUTER_WRITER_MODEL", "OPENROUTER_MODEL")
            or "anthropic/claude-opus-5.5"
        )

    try:
        from app.core.database import SessionLocal
        from app.services.seo.agent_writer import resolve_agent_route

        with SessionLocal() as db:
            provider, api_key, model = resolve_agent_route(db, project_id)
        if provider and api_key:
            return provider, api_key, model
    except Exception as exc:
        detail = str(exc)
        if "DATABASE_URL doit pointer vers PostgreSQL" in detail:
            raise LiveRunError(
                "Le runtime du CMS n'est pas chargé : DATABASE_URL doit pointer "
                "vers la base PostgreSQL du CMS. Lance le laboratoire depuis le "
                "runtime configuré du CMS ou renseigne ce runtime dans .env."
            ) from exc
        raise LiveRunError(
            "Impossible de lire les credentials du CMS. Vérifie DATABASE_URL, "
            "SECRET_KEY et la connexion à PostgreSQL ; la clé n'est jamais "
            "affichée ni copiée dans le laboratoire."
        ) from exc
    raise LiveRunError(
        "Aucune clé Anthropic/OpenRouter accessible. La clé n'est jamais demandée "
        "dans le code et ne doit pas être écrite dans le dépôt."
    )


def build_search_adapter(project_id: str | None = None) -> ExistingPipelineWebAdapter:
    """Construit l'adaptateur réel du pipeline existant."""

    try:
        adapter = from_ideas_studio(project_id)
    except Exception as exc:
        raise LiveRunError(
            "La recherche réelle du pipeline ne peut pas être initialisée. "
            "Vérifie la configuration du service de recherche et du runtime CMS."
        ) from exc
    if not getattr(adapter, "search_fn", None):
        raise LiveRunError("L'adaptateur de recherche réel est absent.")
    return adapter


def _build_user_message(config: LiveRunConfig, published_articles: list[dict[str, str]] | None = None) -> str:
    lines = [f"Mot-clé : {config.keyword}"]
    if config.category:
        lines.append(f"Catégorie : {config.category}")
    if config.editor_notes:
        lines.append(f"Consignes de l'éditeur : {config.editor_notes}")
    articles = [item for item in (published_articles or []) if item.get("title") and item.get("url")]
    if articles:
        lines.append("Articles déjà publiés sur le site (liens internes autorisés uniquement ici) :")
        lines.extend(f"- {item['title']} : {item['url']}" for item in articles[:60])
    else:
        lines.append("Aucun article publié fourni : n'ajoute pas de lien interne.")
    return "\n".join(lines)


def _load_published_articles(project_id: str | None) -> list[dict[str, str]]:
    """Récupère les articles publiés du projet quand son contexte est disponible."""

    if not project_id:
        return []
    try:
        from sqlalchemy import select
        from app.core.database import SessionLocal
        from app.models.content import Article, ArticleRevision
        from app.models.core import Project

        with SessionLocal() as db:
            project = db.get(Project, project_id)
            if project is None or not project.domain:
                return []
            rows = db.execute(
                select(Article.slug, ArticleRevision.title)
                .join(ArticleRevision, ArticleRevision.id == Article.current_revision_id)
                .where(Article.project_id == project_id, Article.published_at.is_not(None))
                .order_by(Article.published_at.desc())
                .limit(60)
            ).all()
            base = project.domain if project.domain.startswith("http") else f"https://{project.domain}"
        return [
            {"title": title, "url": f"{base.rstrip('/')}/blog/{slug}"}
            for slug, title in rows
            if slug and title
        ]
    except Exception:
        # Le laboratoire reste utilisable sans CMS ; le prompt indiquera alors
        # qu'aucun lien interne n'est disponible.
        return []


def _make_client(route: str, key: str, model: str, config: LiveRunConfig, adapter: ExistingPipelineWebAdapter):
    model = config.model or model
    if route == "anthropic":
        from app.services.seo.agent_writer import anthropic_client

        return anthropic_client(key, timeout_seconds=900.0)
    if route == "openrouter":
        from app.services.seo.agent_writer_openrouter import OpenRouterAgentClient, page_fetcher, reader_get

        fetch = page_fetcher(fallback=reader_get)
        return OpenRouterAgentClient(
            api_key=key,
            model=model,
            search_fn=adapter.search_fn,
            fetch_fn=fetch,
            max_searches=config.max_searches,
            max_fetches=config.max_fetches,
            max_cost_usd=config.max_cost_usd,
            # Le laboratoire doit mesurer la qualité de rédaction avec le
            # niveau de raisonnement maximal demandé pour ce test.
            reasoning_effort="high",
        )
    raise LiveRunError(f"Fournisseur non supporté pour le laboratoire : {route}")


def _structure_report(data: dict[str, Any]) -> dict[str, Any]:
    try:
        from app.services.seo.structure_validator import validate_structure

        return validate_structure(data.get("content_html") or "", data.get("title") or "")
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc)}


def _plagiarism_report(data: dict[str, Any], adapter: ExistingPipelineWebAdapter | None, domain: str) -> dict[str, Any]:
    if adapter is None:
        return {"status": "skipped", "reason": "adaptateur SERP absent ; la recherche native du modèle a été utilisée"}
    try:
        from app.services.seo.plagiarism_check import SerpPlagiarismBackend, check_plagiarism

        backend = SerpPlagiarismBackend(adapter.search_fn, own_domain=domain)
        return check_plagiarism(data.get("content_html") or "", backend)
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc)}


def _live_score(structure: dict[str, Any], plagiarism: dict[str, Any]) -> tuple[int, int]:
    """Classe une version sur les fautes structurelles puis le plagiat."""

    hard = int(structure.get("hard_failures") or 0) if isinstance(structure, dict) else 999
    matches = len(plagiarism.get("matches") or []) if isinstance(plagiarism, dict) else 999
    return hard, matches


def _plagiarism_correction_errors(plagiarism: dict[str, Any]) -> list[str]:
    errors = []
    for match in plagiarism.get("matches") or []:
        sentence = str(match.get("sentence") or "").strip()
        url = str(match.get("url") or "").strip()
        if sentence:
            errors.append(
                "Réécris uniquement cette phrase ou le passage minimal qui la contient, "
                f"sans modifier le reste : « {sentence} » (source détectée : {url})."
            )
    return errors


def _write_html(path: Path, data: dict[str, Any], report: dict[str, Any]) -> None:
    import html

    content = data.get("content_html") or "<p>Article vide.</p>"
    title = html.escape(str(data.get("title") or "Article généré"))
    meta = html.escape(str(data.get("meta_description") or ""))
    warnings = "".join(
        f"<li><strong>{html.escape(str(item.get('code', '')))}</strong> — "
        f"{html.escape(str(item.get('message', '')))}</li>"
        for item in report.get("blocking_issues", []) + report.get("warnings", [])
    ) or "<li>Aucun contrôle bloquant enregistré.</li>"
    path.write_text(
        "<!doctype html><html lang='fr'><head><meta charset='utf-8'>"
        f"<meta name='description' content='{meta}'><title>{title}</title>"
        "<style>body{max-width:820px;margin:40px auto;padding:0 24px;"
        "font:18px/1.65 system-ui,sans-serif;color:#202124}h1{font-size:2.2rem;"
        "line-height:1.15}h2{margin-top:2.4em}h3{margin-top:1.8em}.summary,.summary-callout{"
        "padding:16px 20px;background:#f0f4f8;border-left:4px solid #526b82;"
        "border-radius:4px}.report{margin-top:60px;padding-top:24px;border-top:1px solid #ddd;"
        "font-size:14px;color:#555}</style></head><body>"
        f"<h1>{title}</h1>{content}<section class='report'><h2>Rapport de contrôle</h2>"
        f"<p>Modèle : {html.escape(str(report.get('model', '')))} · "
        f"Coût estimé : {html.escape(str(report.get('cost_usd', 0)))} $</p>"
        f"<ul>{warnings}</ul></section></body></html>",
        encoding="utf-8",
    )


def run_live(config: LiveRunConfig, *, published_articles: list[dict[str, str]] | None = None) -> dict[str, Any]:
    """Exécute un seul essai réel et sauvegarde son rendu local."""

    started = perf_counter()
    route, key, model = resolve_model_route(config.project_id)
    adapter: ExistingPipelineWebAdapter | None = None
    try:
        adapter = build_search_adapter(config.project_id)
    except LiveRunError:
        # Anthropic possède ses propres outils web. L'adaptateur SERP reste
        # nécessaire pour le contrôle de similarité, mais son absence ne doit
        # pas empêcher l'essai éditorial principal. OpenRouter, lui, exécute
        # les outils via le pipeline existant et ne peut pas continuer sans lui.
        if route == "openrouter":
            raise
    system = load_system_prompt(
        site_name=config.site_name,
        site_domain=config.domain,
        language=config.language,
        country=config.country,
        today=date.today(),
    )
    if route == "openrouter" and adapter is None:
        raise LiveRunError("OpenRouter nécessite l'adaptateur de recherche réel du pipeline.")
    client = _make_client(route, key, model, config, adapter)
    from app.services.seo.agent_writer import AgentWriter, AgentWriterError

    writer = AgentWriter(client, model=model, system=system)
    try:
        # Une seule production éditoriale. Une réponse JSON invalide est un
        # échec technique du run, pas une invitation à discuter ou à réécrire
        # le contenu dans un second tour.
        context_articles = published_articles if published_articles is not None else _load_published_articles(config.project_id)
        data = writer.write(_build_user_message(config, context_articles), json_retries=0)
    except AgentWriterError as exc:
        raise LiveRunError(f"Le rédacteur réel n'a pas produit un JSON exploitable : {exc}") from exc

    structure = _structure_report(data)
    plagiarism = _plagiarism_report(data, adapter, config.domain)
    versions = [(1, data, structure, plagiarism)]
    correction_errors = _plagiarism_correction_errors(plagiarism)
    if correction_errors:
        corrected = writer.correct(correction_errors)
        if corrected:
            corrected_structure = _structure_report(corrected)
            corrected_plagiarism = _plagiarism_report(corrected, adapter, config.domain)
            candidate = (2, corrected, corrected_structure, corrected_plagiarism)
            if _live_score(candidate[2], candidate[3]) < _live_score(structure, plagiarism):
                versions.append(candidate)
    selected_version, data, structure, plagiarism = min(
        versions,
        key=lambda item: _live_score(item[2], item[3]) + (item[0] - 1,),
    )
    agent_report = writer.report()
    blocking = []
    for rule in structure.get("rules", []) if isinstance(structure, dict) else []:
        if rule.get("severity") == "hard" and not rule.get("passed", True):
            blocking.append({"code": rule.get("rule", "structure"), "message": rule.get("label", "Règle non respectée")})
    report = {
        "algorithm": "editorial-agent-lab/live-claude-style",
        "keyword": config.keyword,
        "model": model,
        "route": route,
        "duration_s": round(perf_counter() - started, 2),
        "cost_usd": agent_report.get("cost_usd") or agent_report.get("real_cost_usd") or 0.0,
        "agent": agent_report,
        "structure": structure,
        "plagiarism": plagiarism,
        "blocking_issues": blocking,
        "warnings": [],
        "correction_rounds": 1 if correction_errors else 0,
        "selected_version": selected_version,
        "article": data,
        "seo": {
            "title": data.get("title", ""),
            "meta_title": data.get("meta_title", ""),
            "meta_description": data.get("meta_description", ""),
            "slug": data.get("slug", ""),
        },
    }
    config.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = config.output_dir / "report.json"
    html_path = config.output_dir / "article.html"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    _write_html(html_path, data, report)
    report["output"] = {"report_json": str(json_path), "article_html": str(html_path)}
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return report
