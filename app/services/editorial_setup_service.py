import httpx
import re
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from app.models.project import Project
from app.schemas.editorial_setup import EditorialSetupSuggestion, EditorialSetupResponse
from app.services.providers.llm_provider import get_llm_provider


def _fetch_blog_categories(domain: str) -> list[dict]:
    try:
        url = f"https://{domain}/api/categories"
        resp = httpx.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def _fetch_blog_homepage(domain: str) -> dict:
    try:
        url = f"https://{domain}"
        resp = httpx.get(url, timeout=10, follow_redirects=True)
        resp.raise_for_status()
        text = resp.text
        title = ""
        m = re.search(r"<title[^>]*>([^<]+)</title>", text, re.IGNORECASE)
        if m:
            title = m.group(1).strip()
        description = ""
        m = re.search(
            r'<meta\s+name="description"\s+content="([^"]*)"',
            text, re.IGNORECASE,
        )
        if m:
            description = m.group(1).strip()
        return {"title": title, "description": description}
    except Exception:
        return {"title": "", "description": ""}


def _domain_to_name(domain: str) -> str:
    parsed = urlparse(f"https://{domain}")
    return parsed.netloc.replace("www.", "").split(".")[0].capitalize()


def _build_default_suggestion(
    domain: str,
    categories: list[dict],
    homepage: dict,
) -> EditorialSetupSuggestion:
    cat_names = [c.get("name", "") for c in categories if c.get("name")]
    domain_name = _domain_to_name(domain)
    site_title = homepage.get("title", domain_name)

    description = (
        f"{site_title} est un blog spécialisé dans la création de sites web, "
        "le web design et le SEO, destiné aux entrepreneurs et indépendants "
        "qui souhaitent développer leur présence en ligne."
    )

    audience = (
        "Entrepreneurs, indépendants et petites entreprises cherchant à "
        "développer leur visibilité en ligne via un site web performant et optimisé SEO."
    )

    tone = "Professionnel et accessible, avec une approche pédagogique"

    positioning = (
        "Accompagner les entrepreneurs dans la création et l'optimisation de leur site web, "
        "en combinant design moderne et stratégie SEO éprouvée."
    )

    main_keywords = [
        "création site web",
        "web design",
        "SEO",
        "site vitrine",
        "landing page",
    ]

    recommended_categories = cat_names[:8] if cat_names else [
        "Web Design",
        "SEO",
        "Site web",
        "Marketing",
        "Performance",
    ]

    seo_writing_guidelines = (
        "Rédiger des articles de 1500 à 2500 mots avec une introduction qui accroche. "
        "Utiliser des titres H2 clairs et des listes à puces pour faciliter la lecture. "
        "Intégrer des mots-clés principaux dans le titre, le H1 et la méta-description. "
        "Ajouter au moins 3 liens internes par article. "
        "Conclure par un appel à l'action ou une question ouverte."
    )

    return EditorialSetupSuggestion(
        description=description,
        audience=audience,
        tone=tone,
        positioning=positioning,
        main_keywords=main_keywords,
        recommended_categories=recommended_categories,
        seo_writing_guidelines=seo_writing_guidelines,
    )


_LLM_SYSTEM_PROMPT = """Tu es un expert en stratégie éditoriale SEO.
Analyse les informations fournies sur un projet de blog et propose une configuration éditoriale complète.
Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ou après.
N'utilise PAS de markdown, pas de ```, pas de commentaires."""


_LLM_USER_PROMPT = """Projet : {project_name}
Domaine : {domain}

Site web :
- Titre : {site_title}
- Description : {site_description}
- Catégories du blog : {categories_str}

Données existantes du projet :
- Audience actuelle : {current_audience}
- Ton actuel : {current_tone}

Génère une configuration éditoriale complète au format JSON avec les champs suivants :
- "description" : description du site (2-3 phrases)
- "audience" : audience cible détaillée (2-3 phrases)
- "tone" : ton éditorial
- "positioning" : positionnement éditorial (1-2 phrases)
- "main_keywords" : liste des 5-8 mots-clés principaux
- "recommended_categories" : liste des 5-10 catégories recommandées
- "seo_writing_guidelines" : consignes de rédaction SEO (3-5 phrases)

La réponse doit être UNIQUEMENT un objet JSON valide."""


def _build_llm_prompt(
    project: Project,
    domain: str,
    categories: list[dict],
    homepage: dict,
) -> str:
    site_title = homepage.get("title", "") or _domain_to_name(domain)
    site_description = homepage.get("description", "")
    categories_str = ", ".join(
        c.get("name", "") for c in categories if c.get("name")
    ) or "Aucune catégorie détectée"

    return _LLM_USER_PROMPT.format(
        project_name=project.name,
        domain=domain,
        site_title=site_title,
        site_description=site_description,
        categories_str=categories_str,
        current_audience=project.audience or "Non défini",
        current_tone=project.tone or "Non défini",
    )


def _parse_llm_json(raw: str) -> dict | None:
    import json
    # Try to extract JSON from the response (handle extra text)
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None


def _llm_to_suggestion(data: dict) -> EditorialSetupSuggestion | None:
    try:
        keywords = data.get("main_keywords", [])
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(",") if k.strip()]
        cats = data.get("recommended_categories", [])
        if isinstance(cats, str):
            cats = [c.strip() for c in cats.split(",") if c.strip()]
        return EditorialSetupSuggestion(
            description=str(data.get("description", "")),
            audience=str(data.get("audience", "")),
            tone=str(data.get("tone", "")),
            positioning=str(data.get("positioning", "")),
            main_keywords=keywords,
            recommended_categories=cats,
            seo_writing_guidelines=str(data.get("seo_writing_guidelines", "")),
        )
    except (ValueError, TypeError):
        return None


def generate_setup_suggestions(
    db: Session,
    project: Project,
) -> EditorialSetupResponse:
    domain = project.domain or ""
    categories = _fetch_blog_categories(domain) if domain else []
    homepage = _fetch_blog_homepage(domain) if domain else {}

    project_has_data = bool(project.audience or project.tone)

    llm = get_llm_provider()

    if not llm.is_mock:
        prompt = _build_llm_prompt(project, domain, categories, homepage)
        raw = llm.generate_text(prompt, system=_LLM_SYSTEM_PROMPT, temperature=0.7)
        data = _parse_llm_json(raw)
        if data:
            suggestion = _llm_to_suggestion(data)
            if suggestion:
                return EditorialSetupResponse(
                    suggestion=suggestion,
                    source="llm",
                    project_has_data=project_has_data,
                )

    suggestion = _build_default_suggestion(domain, categories, homepage)
    return EditorialSetupResponse(
        suggestion=suggestion,
        source="default",
        project_has_data=project_has_data,
    )
