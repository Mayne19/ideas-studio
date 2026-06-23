import logging
import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url
from alembic.config import Config
from alembic import command
from app.core.config import settings
from app.routers import auth, projects, health, categories, articles, public_api, tracking, ideas, seo, performance, recommendations, notifications, members, editor, versions, media, invitations, editorial_setup, callouts, pipeline, generation, comments, search, search_console, profile, ai_providers, activity, webhooks, kanban_columns, ai_agents, monitoring

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

OPENAPI_TAGS = [
    {"name": "auth", "description": "Inscription, connexion, session utilisateur et récupération du profil courant."},
    {"name": "profile", "description": "Profil utilisateur, avatar et mot de passe."},
    {"name": "projects", "description": "Création, configuration générale, connexion publique et suppression de projets."},
    {"name": "members", "description": "Membres projet, rôles, invitations et permissions collaboratives."},
    {"name": "invitations", "description": "Lecture et acceptation des invitations par token."},
    {"name": "articles", "description": "Articles, publication, dépublication, planification, archives et validation en lot."},
    {"name": "editor", "description": "Données éditeur, autosave et preview d'article."},
    {"name": "versions", "description": "Historique et restauration des versions d'articles."},
    {"name": "comments", "description": "Commentaires éditoriaux associés aux articles."},
    {"name": "categories", "description": "Catégories éditoriales, priorités et synchronisation."},
    {"name": "callouts", "description": "Templates de callouts réutilisables dans l'éditeur."},
    {"name": "ideas", "description": "Idées, opportunités SEO, passage en production et file de production."},
    {"name": "generation", "description": "Génération IA, rapports de génération, découverte d'idées et planning."},
    {"name": "pipeline", "description": "Configuration, exécution et logs du pipeline éditorial."},
    {"name": "seo", "description": "Analyse SEO, readiness checks et scores éditoriaux."},
    {"name": "recommendations", "description": "Recommandations d'optimisation et actions associées."},
    {"name": "performance", "description": "Métriques de performance projet et article."},
    {"name": "tracking", "description": "Snippet analytics et collecte d'événements publics."},
    {"name": "public", "description": "API publique pour exposer articles et catégories publiés."},
    {"name": "media", "description": "Médiathèque, uploads et métadonnées des fichiers."},
    {"name": "notifications", "description": "Notifications projet et actions de lecture/suppression."},
    {"name": "ai_providers", "description": "Providers IA, tests de connexion et statut des clés masquées."},
    {"name": "ai_agents", "description": "Registre des agents IA et assignations aux providers."},
    {"name": "search", "description": "Recherche globale dans le studio."},
    {"name": "search_console", "description": "Intégration Google Search Console, partielle selon configuration."},
    {"name": "editorial_setup", "description": "Assistant de configuration éditoriale initiale."},
    {"name": "activity", "description": "Journal d'activité projet."},
    {"name": "webhooks", "description": "Webhooks sortants, secrets partagés et tests."},
    {"name": "kanban_columns", "description": "Colonnes personnalisées du workflow de production."},
    {"name": "monitoring", "description": "Analyse d'amélioration et brouillons d'optimisation."},
    {"name": "health", "description": "Santé backend et vérification légère des providers."},
]

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Ideas Studio est un CMS editorial SEO/GEO assiste par IA. "
        "L'API couvre les projets, articles, workflow editorial, providers IA, "
        "agents, pipeline, tracking, analytics et API publique. Les routes privees "
        "necessitent un token JWT ; les cles providers restent cote backend et ne "
        "sont jamais exposees en clair."
    ),
    version="0.2.0",
    openapi_tags=OPENAPI_TAGS,
)


def _read_alembic_revision() -> str:
    engine = None
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as connection:
            result = connection.execute(text("select version_num from alembic_version"))
            versions = [row[0] for row in result]
        return ",".join(versions) if versions else "<empty>"
    except Exception as exc:
        return f"<unavailable: {exc.__class__.__name__}>"
    finally:
        if engine is not None:
            engine.dispose()


def _database_dialect() -> str:
    try:
        return make_url(settings.database_url).get_backend_name()
    except Exception:
        return "<unknown>"


@app.on_event("startup")
def run_migrations():
    if settings.APP_ENV == "test":
        return
    root_dir = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(root_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(root_dir / "alembic"))
    logger.info(
        "Running Alembic migrations at startup. env=%s database=%s dialect=%s target_revision=%s",
        settings.APP_ENV,
        settings.safe_database_url,
        _database_dialect(),
        "head",
    )
    logger.info("Alembic current revision before startup upgrade: %s", _read_alembic_revision())
    try:
        command.upgrade(alembic_cfg, "head")
    except SystemExit as exc:
        logger.exception(
            "Alembic exited during startup. code=%s env=%s database=%s dialect=%s current_revision=%s target_revision=%s",
            exc.code,
            settings.APP_ENV,
            settings.safe_database_url,
            _database_dialect(),
            _read_alembic_revision(),
            "head",
        )
        sys.stderr.flush()
        raise
    except BaseException as exc:
        logger.exception(
            "Alembic migration failed during startup. exception=%s env=%s database=%s dialect=%s current_revision=%s target_revision=%s action=%s",
            repr(exc),
            settings.APP_ENV,
            settings.safe_database_url,
            _database_dialect(),
            _read_alembic_revision(),
            "head",
            "Check the failing revision in Render logs, then run `python -m alembic upgrade head` against a PostgreSQL test database.",
        )
        sys.stderr.flush()
        raise
    logger.info("Alembic migrations completed successfully. current_revision=%s", _read_alembic_revision())

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(projects.router)
app.include_router(categories.router)
app.include_router(callouts.router)
app.include_router(articles.router)
app.include_router(public_api.router)
app.include_router(tracking.router)
app.include_router(ideas.router)
app.include_router(seo.router)
app.include_router(performance.router)
app.include_router(recommendations.router)
app.include_router(notifications.router)
app.include_router(members.router)
app.include_router(editor.router)
app.include_router(versions.router)
app.include_router(media.router)
app.include_router(invitations.router)
app.include_router(editorial_setup.router)
app.include_router(pipeline.router)
app.include_router(generation.router)
app.include_router(comments.router)
app.include_router(search.router)
app.include_router(search_console.router)
app.include_router(ai_providers.router)
app.include_router(ai_agents.router)
app.include_router(monitoring.router)
app.include_router(activity.router)
app.include_router(webhooks.router)
app.include_router(kanban_columns.router)
