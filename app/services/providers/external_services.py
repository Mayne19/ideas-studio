"""Services externes non-IA (recherche web, banques d'images) — catalogue,
résolution des clés et test de connexion.

Règle produit : tout ce qu'un éditeur peut avoir à changer doit l'être depuis
le CMS (Paramètres → Services externes), les variables d'environnement ne
servent qu'à l'infrastructure. Ordre de résolution d'une clé :

1. ligne ai.external_service_credentials du projet ;
2. ligne globale (project_id NULL) ;
3. variables d'environnement historiques (SERPER_API_KEY, BRAVE_SEARCH_API_KEY,
   SERP_API_KEY, GOOGLE_SEARCH_API_KEY/CX, UNSPLASH_ACCESS_KEY) — repli
   conservé pour ne pas casser une production configurée uniquement par env.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# Catalogue : service -> provider -> métadonnées affichées par le front.
# "fields" liste les paramètres non secrets supplémentaires (stockés dans
# ExternalServiceCredential.config).
EXTERNAL_SERVICES: dict[str, dict] = {
    "search": {
        "label": "Recherche web",
        "description": "Analyse SERP, recherche d'idées et de sources pour la rédaction.",
        "providers": {
            "serper": {"label": "Serper (Google)", "fields": [], "docs_url": "https://serper.dev/"},
            "brave": {"label": "Brave Search", "fields": [], "docs_url": "https://api-dashboard.search.brave.com/"},
            "serpapi": {"label": "SerpAPI", "fields": [], "docs_url": "https://serpapi.com/"},
            "google_cse": {
                "label": "Google Custom Search",
                "fields": ["cx"],
                "docs_url": "https://programmablesearchengine.google.com/",
            },
        },
    },
    "images": {
        "label": "Images d'illustration",
        "description": "Photos libres de droits insérées automatiquement dans les articles.",
        "providers": {
            "unsplash": {"label": "Unsplash", "fields": [], "docs_url": "https://unsplash.com/developers"},
        },
    },
    "brand_images": {
        "label": "Images officielles des marques",
        "description": "Captures et visuels publiés sur le site officiel d'un outil ou d'une marque cité.",
        "providers": {
            "brave": {"label": "Brave Image Search", "fields": [], "docs_url": "https://api-dashboard.search.brave.com/"},
        },
    },
}


@dataclass
class ServiceCredential:
    service: str
    provider: str
    api_key: str
    config: dict = field(default_factory=dict)
    # "project" | "global" | "env"
    source: str = "env"


def is_valid_provider(service: str, provider: str) -> bool:
    return provider in (EXTERNAL_SERVICES.get(service) or {}).get("providers", {})


def mask_key(api_key: str | None) -> str | None:
    if not api_key:
        return None
    return api_key[-4:] if len(api_key) > 4 else None


# ── Résolution ─────────────────────────────────────────────────────────────


def find_row(db, service: str, project_id: str | None):
    """Ligne exacte (projet, service) — sans repli sur la ligne globale."""
    from sqlalchemy import select
    from app.models.ai import ExternalServiceCredential

    query = select(ExternalServiceCredential).where(ExternalServiceCredential.service == service)
    if project_id:
        query = query.where(ExternalServiceCredential.project_id == project_id)
    else:
        query = query.where(ExternalServiceCredential.project_id.is_(None))
    return db.execute(query).scalar_one_or_none()


def row_to_credential(row) -> ServiceCredential | None:
    from app.core.security import decrypt_secret

    api_key = decrypt_secret(row.secret_ref)
    if not api_key:
        return None
    return ServiceCredential(
        service=row.service,
        provider=row.provider,
        api_key=api_key,
        config=dict(row.config or {}),
        source="project" if row.project_id else "global",
    )


def _scoped_credential(db, service: str, project_id: str | None) -> ServiceCredential | None:
    row = find_row(db, service, project_id)
    if row is None:
        return None
    cred = row_to_credential(row)
    if cred is None or not is_valid_provider(service, cred.provider):
        return None
    return cred


def lookup_db_credential(db, service: str, project_id: str | None) -> ServiceCredential | None:
    """Clé configurée dans le CMS avec la session fournie : projet, puis
    globale. Pour brand_images, une clé Brave saisie pour la recherche web
    sert aussi (même abonnement Brave Search API)."""
    for scope in ([project_id, None] if project_id else [None]):
        cred = _scoped_credential(db, service, scope)
        if cred is not None:
            return cred
    if service == "brand_images":
        search = lookup_db_credential(db, "search", project_id)
        if search is not None and search.provider == "brave":
            return ServiceCredential("brand_images", "brave", search.api_key, source=search.source)
    return None


def resolve_db_credential(service: str, project_id: str | None = None) -> ServiceCredential | None:
    """Clé configurée dans le CMS (projet puis globale), None sinon.

    project_id absent : on lit le project_id de la requête/job en cours
    (current_project_id, posé par les dépendances et les workers) pour que
    les appelants historiques sans paramètre profitent quand même de la
    config projet. Session dédiée (comme get_llm_provider) : une erreur ici
    (table absente, clé indéchiffrable) ne doit jamais empoisonner la
    transaction de l'appelant — repli silencieux sur l'environnement."""
    from app.core.config import settings

    if settings.APP_ENV == "test":
        return None
    if project_id is None:
        from app.core.database import current_project_id
        project_id = current_project_id.get()

    try:
        from app.core.database import SessionLocal
    except Exception:
        return None

    db = SessionLocal()
    try:
        return lookup_db_credential(db, service, project_id)
    except Exception as exc:
        logger.warning("external_services: lecture config %s impossible (%s), repli env", service, exc)
        return None
    finally:
        db.close()


def env_credential(service: str) -> ServiceCredential | None:
    """Repli variables d'environnement — même ordre de préférence que
    l'ancien SerpAdapter (Serper > SerpAPI > Brave > Google CSE)."""
    from app.core.config import settings

    if service == "search":
        if settings.SERPER_API_KEY:
            return ServiceCredential("search", "serper", settings.SERPER_API_KEY)
        if settings.SERP_API_KEY:
            return ServiceCredential("search", "serpapi", settings.SERP_API_KEY)
        if settings.BRAVE_SEARCH_API_KEY:
            return ServiceCredential("search", "brave", settings.BRAVE_SEARCH_API_KEY)
        if settings.GOOGLE_SEARCH_API_KEY and settings.GOOGLE_SEARCH_CX:
            return ServiceCredential(
                "search", "google_cse", settings.GOOGLE_SEARCH_API_KEY, {"cx": settings.GOOGLE_SEARCH_CX}
            )
        return None
    if service == "images":
        if settings.UNSPLASH_ACCESS_KEY:
            return ServiceCredential("images", "unsplash", settings.UNSPLASH_ACCESS_KEY)
        return None
    if service == "brand_images":
        if settings.BRAVE_SEARCH_API_KEY:
            return ServiceCredential("brand_images", "brave", settings.BRAVE_SEARCH_API_KEY)
        return None
    return None


def resolve_credential(service: str, project_id: str | None = None) -> ServiceCredential | None:
    """Clé effectivement utilisée à l'exécution : CMS (projet, global) puis env."""
    return resolve_db_credential(service, project_id) or env_credential(service)


def effective_credential(db, service: str, project_id: str | None) -> ServiceCredential | None:
    """Même résolution que resolve_credential mais avec la session fournie
    (affichage dans les paramètres, y compris en environnement de test)."""
    return lookup_db_credential(db, service, project_id) or env_credential(service)


# ── Test de connexion ──────────────────────────────────────────────────────


def _http_error_message(exc: Exception) -> str:
    import httpx

    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code in (401, 403):
            return f"Clé refusée par le service (HTTP {code}) — vérifiez la clé API."
        if code == 429:
            return "Quota dépassé ou trop de requêtes (HTTP 429)."
        return f"Le service a répondu HTTP {code}."
    if isinstance(exc, httpx.TimeoutException):
        return "Délai dépassé en contactant le service."
    return str(exc) or exc.__class__.__name__


def check_credential(cred: ServiceCredential) -> tuple[bool, str | None]:
    """Appel réel minimal au service. Retourne (ok, message d'erreur)."""
    import httpx

    timeout = 15
    try:
        if cred.provider == "serper":
            resp = httpx.post(
                "https://google.serper.dev/search",
                json={"q": "test", "num": 1},
                headers={"X-API-KEY": cred.api_key, "Content-Type": "application/json"},
                timeout=timeout,
            )
        elif cred.provider == "brave" and cred.service == "brand_images":
            resp = httpx.get(
                "https://api.search.brave.com/res/v1/images/search",
                params={"q": "test", "count": 1},
                headers={"X-Subscription-Token": cred.api_key, "Accept": "application/json"},
                timeout=timeout,
            )
        elif cred.provider == "brave":
            resp = httpx.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": "test", "count": 1},
                headers={"X-Subscription-Token": cred.api_key, "Accept": "application/json"},
                timeout=timeout,
            )
        elif cred.provider == "serpapi":
            # /account.json ne consomme aucun crédit de recherche.
            resp = httpx.get("https://serpapi.com/account.json", params={"api_key": cred.api_key}, timeout=timeout)
        elif cred.provider == "google_cse":
            cx = (cred.config or {}).get("cx")
            if not cx:
                return False, "Identifiant du moteur (cx) manquant."
            resp = httpx.get(
                "https://www.googleapis.com/customsearch/v1",
                params={"key": cred.api_key, "cx": cx, "q": "test", "num": 1},
                timeout=timeout,
            )
        elif cred.provider == "unsplash":
            resp = httpx.get(
                "https://api.unsplash.com/search/photos",
                params={"query": "test", "per_page": 1},
                headers={"Authorization": f"Client-ID {cred.api_key}"},
                timeout=timeout,
            )
        else:
            return False, f"Provider '{cred.provider}' non supporté."
        resp.raise_for_status()
        return True, None
    except Exception as exc:
        return False, _http_error_message(exc)


# ── Gestion depuis les paramètres ──────────────────────────────────────────


class ExternalServiceConfigError(ValueError):
    """Requête de configuration invalide (provider inconnu, clé manquante...)."""


def _clean_config(service: str, provider: str, config: dict | None) -> dict:
    allowed = EXTERNAL_SERVICES[service]["providers"][provider].get("fields", [])
    return {k: str(v).strip() for k, v in (config or {}).items() if k in allowed and v is not None and str(v).strip()}


def upsert_credential(db, service: str, project_id: str | None, provider: str, api_key: str | None, config: dict | None):
    """Crée ou met à jour la ligne (projet, service). Une clé n'est jamais
    réutilisée pour un autre provider : changer de provider exige une clé."""
    from app.core.security import encrypt_secret
    from app.models.ai import ExternalServiceCredential

    if service not in EXTERNAL_SERVICES:
        raise ExternalServiceConfigError(f"Service '{service}' inconnu")
    if not is_valid_provider(service, provider):
        raise ExternalServiceConfigError(f"Provider '{provider}' non supporté pour '{service}'")
    api_key = (api_key or "").strip() or None

    row = find_row(db, service, project_id)
    same_provider = row is not None and row.provider == provider
    if not api_key and not same_provider:
        raise ExternalServiceConfigError(
            "Clé API requise" if row is None else "Nouvelle clé API requise pour changer de provider"
        )
    # config absent = conserver les paramètres existants (même provider).
    source_config = config if (config is not None or not same_provider) else row.config
    final_config = _clean_config(service, provider, source_config)
    for required in EXTERNAL_SERVICES[service]["providers"][provider].get("fields", []):
        if required not in final_config:
            raise ExternalServiceConfigError(f"Champ '{required}' requis pour {provider}")

    if row is None:
        row = ExternalServiceCredential(project_id=project_id, service=service)
        db.add(row)
    if api_key or not same_provider or final_config != (row.config or {}):
        # Le dernier test ne porte plus sur la config actuelle.
        row.last_test_ok = None
        row.last_test_at = None
        row.last_test_error = None
    row.provider = provider
    if api_key:
        row.secret_ref = encrypt_secret(api_key) or ""
    row.config = final_config
    db.commit()
    db.refresh(row)
    return row
