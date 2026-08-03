import re
import uuid
from datetime import datetime, timezone
from time import perf_counter
from sqlalchemy.orm import Session
from sqlalchemy import select

from typing import Any
from app.core.utils import slugify
from app.models.content import Article, ArticleRevision, Category
from app.models.reference import ArticleStatus, RevisionSource, set_article_status
from app.services.article_service import set_primary_keyword
from app.services.providers.llm_provider import LLMProvider, GenerationFailedError
from app.services.providers.search_provider import SearchProvider
from app.services.log_service import log_step
from app.services.seo.artifacts import save_artifact


_MOCK_IDEA_TEMPLATES = [
    {
        "title": "Comment optimiser votre stratégie de contenu SEO en {year}",
        "keyword": "stratégie contenu SEO",
        "angle": "Guide pratique avec étapes concrètes",
        "search_intent": "informational",
        "audience": "Marketeurs et blogueurs débutants",
        "main_answer_summary": "Une stratégie de contenu SEO repose sur 5 piliers : recherche de mots-clés, analyse d'intention, production de contenu, optimisation technique et mesure des performances.",
        "opportunity_justification": "Fort potentiel car sujet lié à une catégorie prioritaire et manque de contenu existant.",
        "recommended_format": "guide",
        "target_word_count": 2500,
        "needs_faq": True,
        "needs_images": True,
        "estimated_difficulty": "moyenne",
        "secondary_keywords": ["content marketing", "SEO stratégique", "calendrier éditorial"],
    },
    {
        "title": "Les meilleures pratiques pour accélérer votre site web",
        "keyword": "optimisation vitesse site web",
        "angle": "Checklist technique actionnable",
        "search_intent": "informational",
        "audience": "Développeurs web",
        "main_answer_summary": "Les 7 optimisations clés : mise en cache, compression des images, minification CSS/JS, chargement différé, CDN, optimisation du temps de réponse serveur et réduction des requêtes HTTP.",
        "opportunity_justification": "Sujet toujours recherché avec fort volume et concurrence modérée.",
        "recommended_format": "list",
        "target_word_count": 2000,
        "needs_faq": True,
        "needs_images": True,
        "estimated_difficulty": "moyenne",
        "secondary_keywords": ["Core Web Vitals", "Lighthouse", "PageSpeed Insights"],
    },
    {
        "title": "Guide complet : créer un blog rentable en partant de zéro",
        "keyword": "créer blog rentable",
        "angle": "Étapes détaillées du débutant à l'expert",
        "search_intent": "informational",
        "audience": "Entrepreneurs en ligne",
        "main_answer_summary": "Un blog rentable nécessite : une niche bien choisie, du contenu régulier de qualité, une stratégie SEO solide, des sources de monétisation diversifiées et une audience engagée.",
        "opportunity_justification": "Sujet intemporel avec fort potentiel de conversion.",
        "recommended_format": "guide",
        "target_word_count": 3000,
        "needs_faq": True,
        "needs_images": True,
        "estimated_difficulty": "faible",
        "secondary_keywords": ["monétisation blog", "choisir niche blog", "SEO débutant"],
    },
]

_mock_template_index = 0

_QUESTION_PREFIXES = {
    "comment", "pourquoi", "quand", "quel", "quelle", "quels", "quelles",
    "que", "quoi", "où", "ou", "combien", "est-ce",
}

_KEYWORD_STOP_WORDS = {
    "comment", "pourquoi", "quand", "quel", "quelle", "quels", "quelles",
    "que", "quoi", "est", "ce", "est-ce", "faire", "fait", "peut", "peuvent",
    "votre", "vos", "notre", "nos", "mon", "ma", "mes", "son", "sa", "ses",
    "leur", "leurs", "le", "la", "les", "un", "une", "des", "du", "au", "aux",
    "pour", "par", "avec", "sans", "dans", "sur", "en", "et", "ou",
    "qui", "dont", "il", "elle", "ils", "elles", "on", "nous", "vous",
    "cette", "cet", "ces", "sont", "être",
}

# Inversions interrogatives françaises : est-il, sont-elles, a-t-on, peut-on…
_INVERSION_RE = re.compile(r"(est|sont|a|ont|peut|doit|faut|va|vont)(-t)?-(il|elle|ils|elles|on)")

_USEFUL_PREPOSITIONS = {"de", "d", "à"}

_ACTIVE_IDEA_STATUSES = (
    ArticleStatus.IDEA_PROPOSED, ArticleStatus.IDEA_PRIORITY, ArticleStatus.OUTLINE_READY,
    ArticleStatus.WRITING_REQUESTED, ArticleStatus.WRITING_IN_PROGRESS, ArticleStatus.DRAFT,
    ArticleStatus.DRAFT_READY, ArticleStatus.REVIEW_NEEDED, ArticleStatus.CORRECTION_NEEDED,
    ArticleStatus.SCHEDULED, ArticleStatus.PUBLISHED,
)


def _next_mock_idea(project_audience: str | None) -> dict:
    global _mock_template_index
    tpl = _MOCK_IDEA_TEMPLATES[_mock_template_index % len(_MOCK_IDEA_TEMPLATES)]
    _mock_template_index += 1
    year = datetime.now(timezone.utc).year
    return {
        "title": tpl["title"].format(year=year),
        "keyword": tpl["keyword"],
        "angle": tpl["angle"],
        "search_intent": tpl["search_intent"],
        "audience": project_audience or tpl["audience"],
        "opportunity_score": 0.75,
        "serp_summary": {"mock": True, "top_results": []},
        "main_answer_summary": tpl["main_answer_summary"],
        "opportunity_justification": tpl["opportunity_justification"],
        "recommended_format": tpl["recommended_format"],
        "target_word_count": tpl["target_word_count"],
        "needs_faq": tpl["needs_faq"],
        "needs_images": tpl["needs_images"],
        "estimated_difficulty": tpl["estimated_difficulty"],
        "secondary_keywords": tpl["secondary_keywords"],
    }


def _normalize_match(value: str | None) -> str:
    return slugify((value or "").strip()).lower()


def _project_categories(db: Session, project_id: str) -> list[Category]:
    return db.execute(
        select(Category)
        .where(Category.project_id == project_id)
        .order_by(Category.priority_score.desc().nullslast(), Category.name.asc())
    ).scalars().all()


def _category_prompt(categories: list[Category]) -> str:
    if not categories:
        return "Aucune catégorie existante."
    return "\n".join(f"- id={c.id} | slug={c.slug} | name={c.name}" for c in categories)


def _resolve_category_id(
    categories: list[Category],
    category_id: str | None = None,
    idea_data: dict | None = None,
) -> str | None:
    if category_id:
        for category in categories:
            if category.id == category_id:
                return category.id
        return None

    data = idea_data or {}
    raw_values: list[str] = []
    for key in ("category_id", "category_slug", "category_name", "category"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            raw_values.append(value.strip())
        elif isinstance(value, dict):
            raw_values.extend(
                str(value.get(k)).strip()
                for k in ("id", "slug", "name")
                if value.get(k)
            )

    if not raw_values:
        return None

    by_id = {category.id: category.id for category in categories}
    by_slug = {_normalize_match(category.slug): category.id for category in categories}
    by_name = {_normalize_match(category.name): category.id for category in categories}

    for raw in raw_values:
        if raw in by_id:
            return by_id[raw]
        normalized = _normalize_match(raw)
        if normalized in by_slug:
            return by_slug[normalized]
        if normalized in by_name:
            return by_name[normalized]
    return None


def _resolve_word_count_range(
    db: Session,
    project_id: str,
    category: Category | None,
) -> tuple[int | None, int | None, str | None]:
    """Plage de mots applicable : override catégorie, sinon profil éditorial projet."""
    if category:
        overrides = category.overrides or {}
        wc_min, wc_max = overrides.get("word_count_min"), overrides.get("word_count_max")
        if wc_min or wc_max:
            return wc_min, wc_max, "categorie"
    from app.models.core import Project
    project = db.get(Project, project_id)
    profile = project.active_editorial_profile if project else None
    if profile and (profile.word_count_min or profile.word_count_max):
        return profile.word_count_min, profile.word_count_max, "projet"
    return None, None, None


def _clamp_target_word_count(value, wc_min: int | None, wc_max: int | None) -> int | None:
    """target_word_count ne doit jamais sortir de la plage configurée."""
    try:
        target = int(value) if value is not None else None
    except (TypeError, ValueError):
        target = None
    if wc_min is None and wc_max is None:
        return target
    if target is None:
        if wc_min and wc_max:
            return (wc_min + wc_max) // 2
        return wc_max or wc_min
    if wc_max and target > wc_max:
        return wc_max
    if wc_min and target < wc_min:
        return wc_min
    return target


def _keyword_words(value: str) -> list[str]:
    return [word for word in re.split(r"\s+", value.strip()) if word]


def _is_keyword_clean(value: str) -> bool:
    words = _keyword_words(value)
    if len(words) < 2 or len(words) > 6:
        return False
    lower = value.lower()
    if "?" in value:
        return False
    if any(lower.startswith(prefix + " ") for prefix in _QUESTION_PREFIXES):
        return False
    return True


def _extract_keyword(value: str) -> str:
    text = re.sub(r"https?://\S+", " ", value or "")
    text = re.split(r"[?!.]\s+", text, maxsplit=1)[0]
    text = re.sub(r"^[\"'«»“”]+|[\"'«»“”]+$", "", text.strip())
    text = re.sub(r"[:;|/]", " ", text)
    text = re.sub(r"[^\wÀ-ÿ' -]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    tokens: list[str] = []
    for token in _keyword_words(text):
        clean = token.strip("'’").strip("-")
        if not clean:
            continue
        normalized = clean.lower().replace("’", "'").strip("'")
        normalized = normalized.replace("l'", "").replace("d'", "")
        if _INVERSION_RE.fullmatch(normalized):
            continue
        if normalized in _KEYWORD_STOP_WORDS and normalized not in _USEFUL_PREPOSITIONS:
            continue
        if normalized.isdigit() and len(normalized) == 4:
            continue
        tokens.append(clean)
        if len(tokens) >= 6:
            break

    if len(tokens) < 2:
        fallback = [word.strip("'’").strip("-") for word in _keyword_words(text) if word.strip("'’").strip("-")]
        tokens = fallback[:6]

    # Un mot-clé ne doit pas se terminer par un mot-outil (préposition, pronom…)
    weak_endings = _KEYWORD_STOP_WORDS | _USEFUL_PREPOSITIONS
    while tokens and tokens[-1].lower().strip("'’") in weak_endings:
        tokens.pop()
    return " ".join(tokens[:6]).strip()


def _sanitize_keyword(raw_keyword: str | None, *, title: str | None = None, secondary_keywords: list[str] | None = None) -> str:
    candidates = [raw_keyword or ""]
    candidates.extend(secondary_keywords or [])
    if title:
        candidates.append(title)

    for candidate in candidates:
        extracted = _extract_keyword(candidate)
        if _is_keyword_clean(extracted):
            return extracted[:255]

    extracted = _extract_keyword(candidates[0] if candidates else "")
    return extracted[:255]


def _keyword_already_active(db: Session, project_id: str, keyword: str) -> bool:
    from app.models.content import ArticleKeyword, Keyword
    from app.models.reference import KeywordRole

    stmt = (
        select(Article.id)
        .join(ArticleKeyword, ArticleKeyword.article_id == Article.id)
        .join(Keyword, Keyword.id == ArticleKeyword.keyword_id)
        .where(
            Article.project_id == project_id,
            Keyword.term == keyword,
            ArticleKeyword.role == KeywordRole.PRIMARY,
            Article.status_reason_id.in_(_ACTIVE_IDEA_STATUSES),
        )
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none() is not None


def generate_idea(
    db: Session,
    project_id: str,
    project_audience: str | None,
    project_language: str,
    llm: LLMProvider,
    search: SearchProvider,
    context_hint: str | None = None,
    preferred_title: str | None = None,
    keyword: str | None = None,
    category_id: str | None = None,
    audience: str | None = None,
    angle: str | None = None,
    search_intent: str | None = None,
    agent_router: Any | None = None,
) -> Article | None:
    started_at = perf_counter()
    categories = _project_categories(db, project_id)

    if agent_router is not None:
        try:
            llm = agent_router.get_provider("idea_generator", project_id=project_id)
        except Exception:
            pass
    log_step(
        db,
        project_id,
        f"Génération d'idée lancée avec LLM={llm.describe()} et search={search.describe()}",
        level="info",
        step="generate_idea",
    )
    if llm.is_mock:
        log_step(
            db,
            project_id,
            "Mode mock actif pour la génération d'idée. Résultat non destiné à la production.",
            level="warning",
            step="generate_idea",
        )
        idea_data = _next_mock_idea(audience or project_audience)
        if not category_id and categories:
            idea_data["category_id"] = categories[0].id
    else:
        query = keyword or context_hint or f"idées d'articles SEO pour {audience or project_audience or 'un blog'} en {project_language}"
        search_results = search.search(query, limit=5)
        serp_snippets = "\n".join(f"- {r.title}: {r.snippet}" for r in search_results)

        from app.models.core import Project
        project = db.get(Project, project_id)
        profile = project.active_editorial_profile if project else None
        imposed_category = next((c for c in categories if c.id == category_id), None) if category_id else None
        wc_min, wc_max, _ = _resolve_word_count_range(db, project_id, imposed_category)

        project_lines = []
        if project:
            for label, value in (("Projet", project.name), ("Domaine", project.domain)):
                if value:
                    project_lines.append(f"{label} : {value}")
        if profile:
            rules = profile.rules or {}
            constraints = profile.constraints or {}
            for label, value in (
                ("Ton éditorial", profile.tone),
                ("Vertical", profile.vertical),
                ("Objectif éditorial", rules.get("editorial_goal")),
                ("Sujets interdits", constraints.get("forbidden_topics")),
                ("Contraintes SEO", rules.get("seo_rules")),
                ("Contraintes GEO", rules.get("geo_rules")),
            ):
                if value:
                    project_lines.append(f"{label} : {value}")
        project_context = "\n".join(project_lines) or "aucun"

        if wc_min and wc_max:
            wc_instruction = (
                f"Longueur cible imposée : entre {wc_min} et {wc_max} mots. "
                f"target_word_count DOIT être compris entre {wc_min} et {wc_max}. Ne propose jamais une longueur hors de cette plage.\n"
            )
        elif wc_min or wc_max:
            bound = wc_max or wc_min
            wc_instruction = f"Longueur cible imposée : environ {bound} mots (target_word_count = {bound}).\n"
        else:
            wc_instruction = ""

        schema_hint = '{"title": "...", "keyword": "expression courte 2-6 mots", "category_id": "id exact si catégorie fiable", "category_slug": "slug exact si catégorie fiable", "category_name": "nom exact si catégorie fiable", "angle": "...", "search_intent": "informational|commercial|transactional|navigational", "audience": "...", "main_answer_summary": "...", "opportunity_justification": "...", "recommended_format": "guide|list|comparatif|tutoriel|analyse|definition", "target_word_count": 2000, "needs_faq": true, "needs_images": true, "estimated_difficulty": "faible|moyenne|forte", "secondary_keywords": ["kw1", "kw2"], "search_questions": ["question longue ici"]}'
        prompt = (
            f"Génère une idée d'article SEO originale pour un blog en langue '{project_language}'.\n"
            f"Contexte projet :\n{project_context}\n"
            f"Audience cible : {audience or project_audience or 'grand public'}.\n"
            f"Titre souhaité : {preferred_title or 'à proposer librement'}.\n"
            f"Mot-clé prioritaire : {keyword or 'à déduire du contexte'}.\n"
            f"Catégorie imposée : {category_id or 'aucune'}.\n"
            f"Catégories existantes du projet :\n{_category_prompt(categories)}\n"
            f"Angle éditorial souhaité : {angle or 'à proposer librement'}.\n"
            f"Intention de recherche souhaitée : {search_intent or 'à estimer'}.\n"
            f"{wc_instruction}"
            f"Contexte utilisateur : {context_hint or 'aucun contexte additionnel'}.\n"
            f"Contexte SERP actuel :\n{serp_snippets}\n\n"
            f"L'idée doit inclure un pré-brief complet : résumé de la réponse principale, justification du score d'opportunité, format recommandé, longueur cible, besoin FAQ/images, difficulté estimée et mots-clés secondaires.\n"
            f"Si une catégorie est imposée, retourne exactement cette catégorie. Sinon, choisis une catégorie uniquement parmi les catégories existantes et retourne son id/slug/name exact. Si aucune catégorie ne correspond clairement, laisse les champs catégorie vides.\n"
            f"Le champ keyword doit être une expression courte de 2 à 6 mots, pas une question ni un titre complet. Les questions longues doivent aller dans search_questions ou secondary_keywords.\n"
            f"Réponds uniquement en JSON."
        )
        idea_data = llm.generate_json(prompt, schema_hint=schema_hint)
        if not isinstance(idea_data, dict) or not idea_data:
            raise GenerationFailedError("La génération IA n'a pas produit de proposition d'idée exploitable.")
        if not idea_data.get("keyword") and not keyword:
            log_step(db, project_id, "LLM n'a pas retourné de keyword valide", level="warning", step="generate_idea")
            return None

        idea_data["opportunity_score"] = min(1.0, len(search_results) / 10.0 + 0.3)
        idea_data["serp_summary"] = {"top_results": [{"title": r.title, "url": r.url} for r in search_results]}

    generated_title = idea_data.get("title", keyword or "")
    raw_secondary_keywords = idea_data.get("secondary_keywords", [])
    secondary_keywords = raw_secondary_keywords if isinstance(raw_secondary_keywords, list) else []
    final_keyword = _sanitize_keyword(keyword or idea_data.get("keyword", ""), title=generated_title, secondary_keywords=[str(item) for item in secondary_keywords])
    if not final_keyword:
        return None

    if _keyword_already_active(db, project_id, final_keyword):
        log_step(db, project_id, f"Idée ignorée (keyword déjà actif) : {final_keyword}", level="info", step="generate_idea")
        return None

    final_title = preferred_title or generated_title
    final_category_id = _resolve_category_id(categories, category_id=category_id, idea_data=idea_data)

    # Respect strict des paramètres projet/catégorie : clamp de la longueur cible
    final_category = next((c for c in categories if c.id == final_category_id), None)
    wc_min, wc_max, _wc_source = _resolve_word_count_range(db, project_id, final_category)
    idea_data["target_word_count"] = _clamp_target_word_count(idea_data.get("target_word_count"), wc_min, wc_max)
    final_audience = audience or idea_data.get("audience") or project_audience
    final_angle = angle or idea_data.get("angle")
    final_search_intent = search_intent or idea_data.get("search_intent")
    if (keyword or idea_data.get("keyword")) and final_keyword != (keyword or idea_data.get("keyword", "")).strip():
        existing_secondary = [str(item) for item in secondary_keywords]
        raw_keyword = str(keyword or idea_data.get("keyword", "")).strip()
        if raw_keyword and raw_keyword not in existing_secondary:
            existing_secondary.append(raw_keyword)
        idea_data["secondary_keywords"] = existing_secondary

    article = Article(
        id=str(uuid.uuid4()),
        project_id=project_id,
        category_id=final_category_id,
        slug=f"idea-{uuid.uuid4().hex[:8]}",
        search_intent=final_search_intent,
        opportunity_score=idea_data.get("opportunity_score", 0.5),
        priority=0,
        target_word_count=idea_data.get("target_word_count"),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    set_article_status(article, ArticleStatus.IDEA_PROPOSED)
    db.add(article)
    db.flush()

    revision = ArticleRevision(
        article_id=article.id,
        revision_no=1,
        source=RevisionSource.AI,
        title=final_title,
        word_count=0,
    )
    db.add(revision)
    db.flush()
    article.current_revision_id = revision.id

    set_primary_keyword(db, project_id, article.id, final_keyword)

    save_artifact(db, article.id, "idea_prebrief", {
        "title": final_title,
        "keyword": final_keyword,
        "category_id": final_category_id,
        "angle": final_angle,
        "search_intent": final_search_intent,
        "audience": final_audience,
        "main_answer_summary": idea_data.get("main_answer_summary"),
        "opportunity_score": idea_data.get("opportunity_score", 0.5),
        "opportunity_justification": idea_data.get("opportunity_justification"),
        "recommended_format": idea_data.get("recommended_format"),
        "target_word_count": idea_data.get("target_word_count"),
        "needs_faq": idea_data.get("needs_faq"),
        "needs_images": idea_data.get("needs_images"),
        "estimated_difficulty": idea_data.get("estimated_difficulty"),
        "secondary_keywords": idea_data.get("secondary_keywords", []),
        "serp_summary": idea_data.get("serp_summary", {}),
        "proposal_source": "ia_generation",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    })

    log_step(db, project_id, f"Idée générée : {final_title}", level="info", step="generate_idea", article_id=article.id)
    duration_ms = int((perf_counter() - started_at) * 1000)
    log_step(
        db,
        project_id,
        f"Génération d'idée terminée en {duration_ms} ms via {llm.describe()}",
        level="info",
        step="generate_idea",
        article_id=article.id,
    )
    db.flush()
    return article
