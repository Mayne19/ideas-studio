# Ideas Studio — Backend V1

Headless AI-assisted SEO CMS for coded blogs.

## Installation

```bash
python3 -m venv venv
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
| `IDEAS_PER_DAY` | Nombre d'idées générées par jour par projet (défaut : 1) |
| `DEFAULT_LLM_PROVIDER` | `mock` ou `ollama` |
| `DEFAULT_SEARCH_PROVIDER` | `mock` ou `searxng` |
| `OLLAMA_URL` | URL Ollama (ex: `http://localhost:11434`) |
| `OLLAMA_MODEL` | Modèle Ollama (ex: `llama3.2`) |
| `SEARXNG_URL` | URL SearXNG auto-hébergé |

## Migrations

```bash
alembic upgrade head
alembic revision --autogenerate -m "description"
alembic downgrade -1
```

## Lancement local

```bash
uvicorn app.main:app --reload
```

API : `http://localhost:8000` — Docs : `http://localhost:8000/docs`

## Tests

```bash
pytest tests/ -v
# 97 tests — Jours 1 à 5
```

## CLI tâches de fond

```bash
# Lancer toutes les tâches quotidiennes (idées + review)
python -m app.cli daily

# Générer des idées pour un projet
python -m app.cli generate-ideas --project-id <project_id>

# Analyser les articles publiés d'un projet
python -m app.cli review --project-id <project_id>
```

---

## Workflow complet V1

```
1. Création compte → POST /auth/register
2. Création projet → POST /projects
3. Connexion blog → GET /projects/{id}/connect (snippet)
4. Générer idée → POST /projects/{id}/ideas/generate
5. Valider idée → POST /articles/{id}/start-writing
6. Éditer → PATCH /articles/{id}/editor
7. Analyser SEO → POST /articles/{id}/analyze
8. Ready check → POST /articles/{id}/ready-check
9. Publier → POST /articles/{id}/publish
10. Suivre → GET /projects/{id}/performance/summary
11. Recommandations → GET /projects/{id}/recommendations
12. Optimiser → POST /recommendations/{id}/accept
```

---

## Routes disponibles

### Auth
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/logout`

### Projects
- `GET /projects`
- `POST /projects`
- `GET /projects/{id}`
- `PATCH /projects/{id}`
- `GET /projects/{id}/connect`
- `POST /projects/{id}/members`

### Members
- `GET /projects/{id}/members` — liste les membres (tout rôle)
- `POST /projects/{id}/members` — ajoute un membre (owner/admin)
- `PATCH /projects/{id}/members/{user_id}` — modifie le rôle (owner/admin)
- `DELETE /projects/{id}/members/{user_id}` — retire un membre (owner/admin)

**Body POST** : `{"user_id": "...", "role": "admin|editor|writer|viewer"}`  
**Body PATCH** : `{"role": "admin|editor|writer|viewer"}`  
**Règles** : rôle `owner` non assignable via API · doublon bloqué (409) · owner principal non supprimable · non-membre → 403

### Catégories
- `GET /projects/{id}/categories`
- `POST /projects/{id}/categories`
- `GET /categories/{id}`
- `PATCH /categories/{id}`
- `DELETE /categories/{id}`

### Articles (CMS)
- `GET /projects/{id}/articles?status=&category_id=&search=&published_only=&limit=&offset=`
- `POST /projects/{id}/articles`
- `GET /articles/{id}`
- `PATCH /articles/{id}`
- `POST /articles/{id}/publish`
- `POST /articles/{id}/schedule`
- `POST /articles/{id}/unpublish`
- `POST /articles/{id}/mark-ready` — status → ready_to_publish (owner/admin/editor/writer)
- `POST /articles/{id}/archive` — status → archived (owner/admin/editor)

### Editor Backend (Day 6)
- `GET /articles/{id}/editor` — données complètes pour l'éditeur (auth + membre)
- `PATCH /articles/{id}/editor` — sauvegarde éditoriale + crée une version manual si contenu change
- `POST /articles/{id}/autosave` — sauvegarde sans publier + version autosave si contenu différent
- `GET /articles/{id}/preview` — preview privée (draft inclus, auth + membre)

### Version History
- `GET /articles/{id}/versions` — liste les versions (auth + membre)
- `POST /articles/{id}/versions/{version_id}/restore` — restaure une version (owner/admin/editor/writer non-publié)

### Media Manager (URL-based)
- `GET /projects/{id}/media` — liste les médias (auth + membre) · filtre `?article_id=`
- `POST /projects/{id}/media/upload` — enregistre un media URL (owner/admin/editor/writer)
- `PATCH /media/{id}` — modifie alt_text/caption/source/article_id (non-viewer)
- `DELETE /media/{id}` — supprime (owner/admin/editor · writer si article non published)

### Idea Engine
- `POST /projects/{id}/ideas/generate`
- `POST /projects/{id}/launch` _(mode=idea_only|full_article, dry_run)_
- `POST /articles/{id}/start-writing`
- `POST /articles/{id}/reject`
- `POST /articles/{id}/priority`
- `POST /articles/{id}/manual-draft`
- `POST /articles/{id}/rerun`

### SEO Analyzer
- `POST /articles/{id}/analyze`
- `GET /articles/{id}/analysis/latest`
- `GET /articles/{id}/analyses`
- `PATCH /articles/{id}/editor` _(voir Editor Backend)_
- `POST /articles/{id}/ready-check`

### Performance
- `GET /projects/{id}/performance/summary?period=30d`
- `GET /projects/{id}/performance/articles?period=30d`
- `GET /articles/{id}/performance?period=30d`

### Recommendations
- `GET /projects/{id}/recommendations`
- `POST /projects/{id}/recommendations/review`
- `POST /recommendations/{id}/accept`
- `POST /recommendations/{id}/reject`
- `POST /recommendations/{id}/apply`

### Notifications
- `GET /projects/{id}/notifications`
- `POST /notifications/{id}/read`
- `POST /projects/{id}/notifications/read-all`

### API Publique (sans auth — pour le blog)
- `GET /api/public/projects/{id}/articles`
- `GET /api/public/projects/{id}/articles/{slug}`

### Tracking
- `GET /traffic.js`
- `POST /api/traffic/collect`

### Health
- `GET /health`

---

## Snippet tracking

```html
<script
  src="http://localhost:8000/traffic.js"
  data-project-id="VOTRE_PROJECT_ID"
  data-tracking-key="VOTRE_PUBLIC_TRACKING_KEY"
  async>
</script>
```

## SEO Scores

- **SEO Score** : keyword placement, meta title/desc, slug, structure H1/H2
- **Readability Score** : longueur phrases/paragraphes, intro, densité sous-titres
- **Quality Score** : détection mock, longueur, conclusion, cover image
- **EEAT Score** : liens externes, exemples, actionabilité

Formule : `100 - 20×critical - 10×warning - 3×info`, clamé [0, 100]

Readiness : `blocked` (any critical) | `needs_improvement` (warnings) | `ready`

## Optimization Engine

`review_published_articles(project_id)` détecte automatiquement :

| Règle | Type de recommandation |
|---|---|
| J+30 ou J+90, < 5 vues | `fix_low_traffic` |
| Sans FAQ | `add_faq` |
| Meta description < 120 car. | `improve_meta_description` |
| SEO score < 50 | `improve_title` |
| Sans liens internes | `add_internal_links` |

Pas de doublon : une recommandation `pending` du même type bloque la création.

## Statuts d'article

`draft` → `idea_proposed` → `idea_priority` / `idea_rejected` → `outline_ready` → `writing_requested` → `writing_in_progress` → `draft_ready` → `review_needed` → `correction_needed` → `scheduled` → `published` → `update_recommended`

## Limites V1

- Tracking : analytics maison (pas Google Analytics / Search Console)
- IA : provider Mock en dev, Ollama optionnel — Claude/OpenAI non configurés par défaut
- Performance : basée sur les traffic_events collectés (pas de données externes)
- Pas de workers Redis/RQ — tâches background appelées via CLI ou scheduler externe
- Pas de webhooks (prévu V2)
- Pas de billing (prévu V2)

## Modules label.md prévus pour plus tard

- **V1 renforcée** : LLM Gateway (LiteLLM), SearXNG, Deep Rewrite Engine, Source Ledger, Originality Engine, Google Fit Score, Safe Publish Gate
- **V1.5** : Anti-Cannibalization, Internal Linking Engine, ContentBrief, Model Router, Article Versioning
- **V2** : Search Console, Google Update Watcher, Topical Authority Engine, Author Profiles, Webhooks, Billing
