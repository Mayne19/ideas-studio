# Ideas Studio

**Headless AI-assisted SEO CMS pour blogs codés.**

Ideas Studio est une plateforme SaaS qui automatise la création de contenu SEO pour blogs et sites web. Elle combine génération IA, analyse SEO/GEO automatisée, pipeline éditorial et suivi de performance.

## Description

Ideas Studio centralise la stratégie, la production, la validation, la publication et l'amélioration continue des articles. Le produit est pensé pour piloter un blog ou un média connecté depuis une interface unique, tout en gardant le site public séparé du studio.

## Vision produit

Le studio doit aider une équipe éditoriale à produire plus vite sans abandonner le contrôle humain. L'IA assiste la recherche, les idées, les briefs, la rédaction et les rapports qualité ; l'humain garde la validation, la publication et les arbitrages éditoriaux.

---

## Fonctionnalités principales

- **Gestion de projets multi-sites** — Créez et gérez plusieurs blogs depuis un seul compte
- **Génération IA d'articles** — Idées, rédaction, SEO, callouts, FAQ, métadonnées
- **Orchestrateur IA** — 27 agents spécialisés (recherche, stratégie, création, révision)
- **7 scores éditoriaux** — Global, SEO, Qualité, Lisibilité, Originalité, GEO, EEAT
- **Pipeline éditorial automatisé** — Planification, priorisation, exécution quotidienne
- **Workflow éditorial complet** — Idée → Brouillon → Relecture → Validation → Publication
- **Kanban & Calendrier** — Vue visuelle et planification des publications
- **Éditeur riche** — TipTap avec sauvegarde automatique, historique, commentaires inline
- **Tracking analytics** — Script maison pour collecter vues, temps, engagement
- **Dashboards performance & trafic** — Vues, sources, appareils, tendances
- **API publique** — Exposez articles et catégories sur votre blog
- **Webhooks** — Notifications d'événements vers vos services
- **Gestion d'équipe** — Rôles (owner, admin, editor, writer, viewer), invitations
- **Notifications** — Alertes temps réel sur l'activité du projet
- **Providers IA multiples** — Gemini, OpenAI, OpenRouter, Ollama, Custom

---

## Workflow éditorial

```
Catégories → Idées → Production → Validation → Articles publiés → Performance → Optimisations
```

Chaque étape est pilotée par des agents IA spécialisés, mais la validation humaine reste obligatoire avant publication. Le pipeline ne publie jamais sans relecture.

### Cycle de vie d'un article

```
Idée proposée → Prioritaire → En rédaction → Brouillon prêt → À relire
→ Prêt → Programmé → Publié → Archivé
```

---

## Architecture technique

```
┌─────────────────────────────────────────────────────┐
│                 Frontend React 19                    │
│            (Vite + Tailwind + TipTap)                │
└──────────────────────┬──────────────────────────────┘
                       │ API REST (JWT)
┌──────────────────────▼──────────────────────────────┐
│                FastAPI Backend                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │
│  │ Auth JWT │ │ Routers  │ │  Services             │ │
│  └──────────┘ └──────────┘ └──────────────────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │
│  │ Workers  │ │ Providers│ │  SEO Engine           │ │
│  │ APSched. │ │ LLM/     │ │  Analyzer, Review     │ │
│  │          │ │ Search   │ │  Orchestrator         │ │
│  └──────────┘ └──────────┘ └──────────────────────┘ │
│  ┌──────────────────────────────────────────────────┐│
│  │         SQLite / PostgreSQL                       ││
│  └──────────────────────────────────────────────────┘│
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
         ┌──────────────────────────┐
         │   Blog connecté          │
         │ (Tracking + API pub.)    │
         └──────────────────────────┘
```

---

## Backend

- **Python 3.11+** — Langage principal
- **FastAPI** — Framework web asynchrone
- **SQLAlchemy** — ORM base de données
- **Alembic** — Migrations (1 tête, 27 révisions)
- **APScheduler** — Tâches planifiées (publications, pipeline)
- **Pydantic** — Validation et settings
- **OpenAI-compatible** — Architecture provider IA flexible
- **SQLite / PostgreSQL** — Support multi-base

### Routers API

Tous les routers sont organisés par domaine avec des tags Swagger cohérents :

`auth`, `profile`, `projects`, `categories`, `callouts`, `articles`, `public` (API publique), `tracking`, `ideas`, `seo`, `performance`, `recommendations`, `notifications`, `members`, `editor`, `versions`, `media`, `invitations`, `editorial_setup`, `pipeline`, `generation`, `comments`, `search`, `search_console`, `ai_providers`, `ai_agents`, `monitoring`, `activity`, `webhooks`, `kanban_columns`, `health`

---

## Frontend

- **React 19** — Bibliothèque UI
- **TypeScript** — Typage strict
- **Vite** — Bundler
- **Tailwind CSS** — Styles utilitaires
- **TipTap / ProseMirror** — Éditeur riche

### Pages principales

| Page | Route | Description |
|---|---|---|
| Dashboard | `/projects/:id/dashboard` | Vue d'ensemble du projet |
| Articles | `/projects/:id/articles` | Gestion des articles publiés et brouillons |
| Archives | `/projects/:id/archives` | Articles archivés |
| Catégories | `/projects/:id/categories` | Gestion des catégories |
| Idées | `/projects/:id/ideas` | Idées d'articles SEO |
| Production | `/projects/:id/production` | Kanban de production |
| Validation | `/projects/:id/validation` | Validation avant publication |
| Médias | `/projects/:id/media` | Médiathèque du projet |
| Calendrier | `/projects/:id/calendar` | Planification éditoriale |
| Performance | `/projects/:id/performance` | Analytics et métriques |
| Trafic | `/projects/:id/traffic` | Sources de trafic détaillées |
| Optimisations | `/projects/:id/recommendations` | Recommandations SEO (`/optimizations` redirige vers cette page) |
| Génération IA | `/projects/:id/generate` | Lancement et test du pipeline IA |
| Notifications | `/projects/:id/notifications` | Alertes activité |
| Paramètres | `/projects/:id/settings/*` | Configuration projet |
| Profil | `/account` ou `/projects/:id/settings/profile` | Compte utilisateur |

---

## Base de données et migrations

```bash
# Voir la tête de migration actuelle
./venv/bin/python -m alembic heads

# Appliquer les migrations
./venv/bin/python -m alembic upgrade head

# Créer une nouvelle migration
./venv/bin/python -m alembic revision --autogenerate -m "description"
```

---

## Variables d'environnement

| Variable | Description | Défaut |
|---|---|---|
| `SECRET_KEY` | Clé de chiffrement JWT + Fernet | Générée au démarrage |
| `DATABASE_URL` | URL de connexion DB | `sqlite:///./ideas_studio.db` |
| `APP_ENV` | Environnement (`development`, `test`, `production`) | `development` |
| `APP_URL` | URL publique du backend | `http://localhost:8000` |
| `FRONTEND_URL` | URL publique du frontend | vide |
| `CORS_ORIGINS` | Origines CORS autorisées, séparées par virgule | vide |
| `DEFAULT_LLM_PROVIDER` | Provider IA global | `auto` |
| `VITE_API_URL` | URL backend utilisée par le frontend | `http://localhost:8000` côté client |

---

## Installation locale

### Prérequis

- Python 3.11+
- Node.js 18+
- Ollama (optionnel, génération IA locale)

### Backend

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Éditez .env selon votre configuration
alembic upgrade head
```

### Frontend

```bash
cd frontend
npm install
```

---

## Lancement

```bash
# Backend (terminal 1)
./venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Frontend (terminal 2)
npm --prefix frontend run dev

# Worker tâches de fond (terminal 3, optionnel)
python worker.py
```

### Accès

- API : `http://localhost:8000`
- Documentation API (Swagger) : `http://localhost:8000/docs`
- Documentation ReDoc : `http://localhost:8000/redoc`
- Schéma OpenAPI : `http://localhost:8000/openapi.json`
- Frontend : `http://localhost:5173`
- Documentation utilisateur : `http://localhost:5173/documentation`

---

## Tests

```bash
# Backend — suite complète
./venv/bin/python -m pytest tests/ -q

# Backend — tests spécifiques
./venv/bin/python -m pytest tests/test_auth.py tests/test_permissions.py tests/test_projects.py tests/test_generation.py -q

# Frontend — build
npm --prefix frontend run build

# Frontend — lint
npm --prefix frontend run lint
```

---

## Documentation API / Swagger

La documentation API est générée automatiquement par FastAPI :

- **Swagger UI** : `{APP_URL}/docs`
- **ReDoc** : `{APP_URL}/redoc`
- **Schema JSON** : `{APP_URL}/openapi.json`

Les endpoints sont regroupés par tags OpenAPI : Auth, Profile, Projects, Articles, Ideas, Pipeline, AI Providers, AI Agents, Tracking, Public API, Health, etc. Les réponses sensibles masquent les clés providers et exposent uniquement des indicateurs comme `api_key_configured`.

En environnement de développement, Swagger est accessible sans restriction. En production, il est recommandé de restreindre l'accès à `/docs`, `/redoc` et `/openapi.json` via proxy inverse ou configuration d'hébergement si l'instance est publique.

---

## Sécurité

- **Authentification** : JWT tokens avec expiration configurable
- **Clés API providers** : Chiffrées avec AES (Fernet) avant stockage DB
- **Frontend** : Ne reçoit jamais les clés en clair (booléen `api_key_configured` uniquement)
- **Permissions** : Rôles projet (owner, admin, editor, writer, viewer) + platform_admin global
- **CSRF** : Les appels privés utilisent un token JWT dans l'en-tête `Authorization`, pas des cookies de session
- **Données tracking** : Aucune donnée personnelle identifiable stockée

---

## Providers IA

| Provider | Type | Coût | Modèle par défaut |
|---|---|---|---|
| **Ollama** | Local | Gratuit | `qwen3:14b` |
| **Gemini** | Cloud | Gratuit (quota) | `gemini-2.5-flash` |
| **OpenRouter** | Cloud | Gratuit/payant | Configurable |
| **OpenAI** | Cloud | Payant | `gpt-4o-mini` |
| **Anthropic** | Cloud | Payant | Configurable |
| **Mistral AI** | Cloud | Gratuit/payant | Configurable |
| **Custom** | Variable | Variable | OpenAI-compatible |

---

## Statut actuel

**Verdict : lançable avec réserves pour une phase de test réelle.**

### Ce qui est vérifié

- Frontend : routes principales déclarées et page documentation modernisée
- Backend : API structurée par domaines, 31 routers, métadonnées OpenAPI ajoutées
- Auth : login, JWT, rôles projet
- Providers IA : clés chiffrées, fallback, test de connexion
- Workflow éditorial complet : idées → production → validation → publication
- 7 scores éditoriaux documentés : Global, SEO, Qualité, Lisibilité, Originalité, GEO, EEAT
- Dernière validation complète connue : tests backend 300+ passés, 20 skipped ; à relancer après installation des dépendances locales

### Réserves avant exploitation complète

- Configurer une `SECRET_KEY` stable en production (ne pas utiliser la valeur par défaut)
- Configurer `DATABASE_URL`, `APP_ENV`, `APP_URL`, `FRONTEND_URL`, `CORS_ORIGINS`
- Connecter au moins un provider IA réel
- Le test de génération IA complète avec provider réel n'a pas été exécuté pendant l'audit
- Search Console, emails transactionnels, workers : partiels ou à connecter
- Le build signale un chunk éditeur TipTap volumineux (530 KB) — à surveiller

---

## Déploiement

- **Backend** : Compatible Render, Railway, ou tout hébergeur Python
- **Frontend** : Compatible Vercel, Netlify, ou tout hébergeur statique
- **Base de données** : PostgreSQL recommandé en production (via `DATABASE_URL`)
- **Migrations** : Exécutées automatiquement au démarrage du backend

## Points restants / prochaines étapes

- Relancer `npm install` puis `npm run build` et `npm run lint` dans `frontend` si `node_modules` est absent localement.
- Tester un cycle IA léger avec un provider réel configuré.
- Connecter Search Console et emails transactionnels si nécessaires pour l'exploitation.
- Surveiller la taille du chunk éditeur TipTap et découper davantage si le chargement devient sensible.

---

## Licence et contribution

Projet privé — Ideas Studio. Toute contribution doit passer par une revue de code.
