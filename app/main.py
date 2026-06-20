import logging
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from alembic.config import Config
from alembic import command
from app.core.config import settings
from app.routers import auth, projects, health, categories, articles, public_api, tracking, ideas, seo, performance, recommendations, notifications, members, editor, versions, media, invitations, editorial_setup, callouts, pipeline, generation, comments, search, search_console, profile, ai_providers, activity, webhooks, kanban_columns, ai_agents, monitoring

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

app = FastAPI(
    title=settings.APP_NAME,
    description="Headless AI-assisted SEO CMS for coded blogs.",
    version="0.2.0",
)


@app.on_event("startup")
def run_migrations():
    if settings.APP_ENV == "test":
        return
    root_dir = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(root_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(root_dir / "alembic"))
    command.upgrade(alembic_cfg, "head")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
