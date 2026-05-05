# Ideas Studio — Backend

Headless AI-assisted SEO CMS for coded blogs.

## Installation

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Variables d'environnement (.env)

| Variable | Description |
|---|---|
| `APP_NAME` | Nom affiché dans l'API |
| `APP_ENV` | `development` ou `production` |
| `APP_URL` | URL publique de l'app |
| `DATABASE_URL` | SQLite (`sqlite:///./ideas_studio.db`) ou PostgreSQL (`postgresql://user:pass@host/db`) |
| `SECRET_KEY` | Clé secrète JWT — **changer en prod** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Durée de vie du token (défaut : 1440 = 24h) |

## Migrations

```bash
# Appliquer toutes les migrations
alembic upgrade head

# Créer une nouvelle migration (après modification des modèles)
alembic revision --autogenerate -m "description"

# Rollback
alembic downgrade -1
```

## Lancement local

```bash
uvicorn app.main:app --reload
```

API disponible sur `http://localhost:8000`  
Documentation interactive : `http://localhost:8000/docs`

## Tests

```bash
pytest tests/ -v
```

## Routes disponibles (Jour 1)

### Health
- `GET /health`

### Auth
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/logout`

### Projects
- `GET /projects`
- `POST /projects`
- `GET /projects/{project_id}`
- `PATCH /projects/{project_id}`
- `GET /projects/{project_id}/connect`
