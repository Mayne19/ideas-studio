from fastapi import FastAPI
from app.core.config import settings
from app.routers import auth, projects, health

app = FastAPI(
    title=settings.APP_NAME,
    description="Headless AI-assisted SEO CMS for coded blogs.",
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(projects.router)
