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

from .existing_pipeline_adapter import ExistingPipelineWebAdapter, from_ideas_studio
from .prompting import load_system_prompt


class LiveRunError(RuntimeError):
    """La configuration ou le fournisseur réel empêche l'essai."""


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
        raise LiveRunError(
            "Aucun credential de modèle n'est accessible. Configure la clé dans "
            "le runtime du CMS ou exporte-la pour ce lancement."
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
            reasoning_effort="low",
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
        "line-height:1.15}h2{margin-top:2.4em}h3{margin-top:1.8em}.summary-callout{"
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
        data = writer.write(_build_user_message(config, published_articles), json_retries=0)
    except AgentWriterError as exc:
        raise LiveRunError(f"Le rédacteur réel n'a pas produit un JSON exploitable : {exc}") from exc

    structure = _structure_report(data)
    plagiarism = _plagiarism_report(data, adapter, config.domain)
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
        "selected_version": 1,
        "article": data,
    }
    config.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = config.output_dir / "report.json"
    html_path = config.output_dir / "article.html"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    _write_html(html_path, data, report)
    report["output"] = {"report_json": str(json_path), "article_html": str(html_path)}
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return report
