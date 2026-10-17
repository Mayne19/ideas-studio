"""Exécution réelle, isolée, du rédacteur éditorial.

Ce module ne modifie pas le CMS et ne publie rien. Il réutilise seulement ses
adaptateurs de recherche/lecture et son client OpenRouter/Anthropic. La
rédaction produit du Markdown, l'extraction structurée et la relecture de style
sont deux appels séparés. Les contrôles qui suivent sont déterministes et ne
réécrivent jamais le texte, sauf la correction ciblée déjà prévue pour une
similarité détectée.
"""

from __future__ import annotations

import json
import os
import re
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


EXTRACTION_SYSTEM = """Tu es chargé d'extraire les données éditoriales d'un article.
À partir de l'article Markdown et de la recherche fournie, retourne uniquement un
objet JSON valide avec les clés title, meta_title, meta_description, slug, faq,
sources, facts et self_review. Ne réécris pas l'article. N'invente aucune source,
aucun fait ni aucune donnée absente de l'article ou de la recherche.

Le champ faq est une liste d'objets question et answer. Le champ sources est une
liste d'objets url, title et used_for. Le champ facts est une liste d'objets value
et source_url. Le champ self_review contient les contrôles éditoriaux nécessaires.
"""

STYLE_REVIEW_INSTRUCTION = "Relis cet article uniquement pour la fluidité. Relie les phrases juxtaposées, ajoute les transitions manquantes entre paragraphes, allège les paragraphes trop denses, garde un ton calme et naturel. Ne modifie aucun fait, chiffre, source, lien, titre ni l'ordre du plan. N'ajoute aucune information."


def _content_text(value: Any) -> str:
    """Extrait le texte de blocs Anthropic/OpenRouter sans conserver les outils."""

    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return "".join(_content_text(item) for item in value)
    if isinstance(value, dict):
        if value.get("text"):
            return str(value["text"])
        return _content_text(value.get("content"))
    text = getattr(value, "text", None)
    if text:
        return str(text)
    return _content_text(getattr(value, "content", None))


def _research_snapshot(agent: Any) -> str:
    """Prépare la recherche déjà menée pour l'appel d'extraction séparé."""

    parts = []
    for message in getattr(agent, "messages", []):
        role = message.get("role", "message") if isinstance(message, dict) else "message"
        text = _content_text(message.get("content") if isinstance(message, dict) else message)
        if text.strip():
            parts.append(f"{role}:\n{text}")
    snapshot = "\n\n".join(parts)
    return snapshot[:80000]


def _run_markdown_draft(client: Any, model: str, system: str, user: str) -> tuple[str, Any]:
    """Fait la rédaction avec les outils de recherche, sans contrat JSON."""

    from app.services.seo.agent_writer import AgentWriter, AgentWriterError

    writer = AgentWriter(client, model=model, system=system)
    writer.messages.append({"role": "user", "content": user})
    try:
        markdown = writer._run_turn().strip()
    except AgentWriterError as exc:
        raise LiveRunError(f"Le rédacteur réel n'a pas produit de Markdown exploitable : {exc}") from exc
    if not markdown:
        raise LiveRunError("Le rédacteur réel a renvoyé un article Markdown vide.")
    return markdown, writer


def _complete_separate(
    client: Any,
    model: str,
    system: str,
    user: str,
    *,
    reasoning_effort: str,
    max_tokens: int,
) -> str:
    """Exécute un appel neuf, sans outils ni historique de rédaction."""

    if hasattr(client, "complete"):
        previous = getattr(client, "reasoning_effort", None)
        try:
            client.reasoning_effort = reasoning_effort
            return str(client.complete(system, user, max_tokens=max_tokens) or "").strip()
        finally:
            if previous is not None:
                client.reasoning_effort = previous
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        tools=[],
    )
    return _content_text(getattr(response, "content", None)).strip()


def _extract_article_data(raw: str) -> dict[str, Any]:
    from app.services.seo.html_text_ops import extract_json_object

    data = extract_json_object(raw)
    if not isinstance(data, dict):
        raise LiveRunError("L'appel d'extraction n'a pas produit un JSON valide.")
    required = ("title", "meta_title", "meta_description", "slug", "faq", "sources", "facts", "self_review")
    missing = [key for key in required if key not in data]
    if missing:
        raise LiveRunError("Le JSON extrait ne contient pas les clés suivantes : " + ", ".join(missing))
    return data


def _markdown_without_h1(markdown: str) -> str:
    cleaned = re.sub(r"^```(?:markdown)?\s*|\s*```$", "", markdown.strip(), flags=re.IGNORECASE)
    return re.sub(r"^\s*#\s+[^\n]+\n+", "", cleaned, count=1)


def _markdown_to_html(markdown: str) -> str:
    try:
        from app.core.markdown import markdown_to_html

        return markdown_to_html(_markdown_without_h1(markdown))
    except Exception as exc:
        raise LiveRunError(f"Conversion du Markdown en HTML impossible : {exc}") from exc


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

        report = validate_structure(data.get("content_html") or "", data.get("title") or "")
        removed = {"paragraph_length", "paragraph_variation"}
        rules = [rule for rule in report.get("rules", []) if rule.get("rule") not in removed]
        hard_failed = [rule["rule"] for rule in rules if not rule.get("passed", True) and rule.get("severity") == "hard"]
        warnings = [rule["rule"] for rule in rules if not rule.get("passed", True) and rule.get("severity") != "hard"]
        report.update({
            "rules": rules,
            "status": "fail" if hard_failed else "pass",
            "hard_failures": len(hard_failed),
            "warning_count": len(warnings),
            "failed_hard_rules": hard_failed,
            "failed_warning_rules": warnings,
            "passed_count": sum(1 for rule in rules if rule.get("passed", True)),
            "rule_count": len(rules),
        })
        return report
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


def _correct_markdown_similarity(client: Any, model: str, markdown: str, errors: list[str]) -> str:
    system = (
        "Tu corriges uniquement les passages signalés pour une similarité textuelle. "
        "Retourne l'article complet en Markdown, sans JSON, sans modifier les autres passages."
    )
    user = (
        "Corrige uniquement ces passages et conserve tous les faits, chiffres, sources, liens, titres et l'ordre du plan.\n"
        + "\n".join(f"- {error}" for error in errors)
        + "\n\nArticle Markdown :\n\n"
        + markdown
    )
    return _complete_separate(
        client,
        model,
        system,
        user,
        reasoning_effort="high",
        max_tokens=32000,
    )


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
    context_articles = published_articles if published_articles is not None else _load_published_articles(config.project_id)

    # 1. Rédaction : le modèle dispose des outils de recherche et ne renvoie
    # que l'article complet en Markdown.
    draft_markdown, writer = _run_markdown_draft(
        client,
        model,
        system,
        _build_user_message(config, context_articles),
    )

    # 2. Extraction : appel neuf, sans outils ni historique, avec un
    # raisonnement bas pour produire uniquement les métadonnées structurées.
    extraction_user = (
        "Article Markdown :\n\n"
        + draft_markdown
        + "\n\nRecherche et échanges de recherche disponibles :\n\n"
        + _research_snapshot(writer)
    )
    extraction_raw = _complete_separate(
        client,
        model,
        EXTRACTION_SYSTEM,
        extraction_user,
        reasoning_effort="low",
        max_tokens=16000,
    )
    data = _extract_article_data(extraction_raw)

    # 3. Relecture de style : appel neuf, limité à la fluidité, dont le
    # Markdown relu devient la version de référence de l'article.
    style_system = "Tu es un relecteur de style. Tu respectes strictement la consigne et tu retournes uniquement le Markdown relu."
    reviewed_markdown = _complete_separate(
        client,
        model,
        style_system,
        STYLE_REVIEW_INSTRUCTION + "\n\nArticle Markdown :\n\n" + draft_markdown,
        reasoning_effort="high",
        max_tokens=32000,
    )
    if not reviewed_markdown:
        raise LiveRunError("L'appel de relecture de style a renvoyé un article vide.")
    data["content_html"] = _markdown_to_html(reviewed_markdown)

    structure = _structure_report(data)
    plagiarism = _plagiarism_report(data, adapter, config.domain)
    versions = [(1, reviewed_markdown, data, structure, plagiarism)]
    correction_errors = _plagiarism_correction_errors(plagiarism)
    if correction_errors:
        corrected_markdown = _correct_markdown_similarity(client, model, reviewed_markdown, correction_errors)
        if corrected_markdown:
            corrected_data = dict(data)
            corrected_data["content_html"] = _markdown_to_html(corrected_markdown)
            corrected_structure = _structure_report(corrected_data)
            corrected_plagiarism = _plagiarism_report(corrected_data, adapter, config.domain)
            candidate = (2, corrected_markdown, corrected_data, corrected_structure, corrected_plagiarism)
            if _live_score(candidate[3], candidate[4]) < _live_score(structure, plagiarism):
                versions.append(candidate)
    selected_version, reviewed_markdown, data, structure, plagiarism = min(
        versions,
        key=lambda item: _live_score(item[3], item[4]) + (item[0] - 1,),
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
        "pipeline": {
            "draft_format": "markdown",
            "extraction": "separate_json_low_reasoning",
            "style_review": "separate_markdown_replacement",
        },
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
