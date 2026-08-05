# Ideas Studio

**CMS éditorial SEO/GEO assisté par IA pour blogs codés.**

Ideas Studio est une plateforme qui aide une équipe éditoriale à gérer projets, idées, pipeline de génération IA, analyse SEO, médias et performance depuis une interface unique, tout en gardant le site public séparé du studio.

## Vision produit

Le studio aide une équipe éditoriale à produire plus vite sans abandonner le contrôle humain. L'IA assiste la recherche, les idées, les briefs, la rédaction et les rapports qualité ; l'humain garde la validation, la publication et les arbitrages éditoriaux.

---

## Fonctionnalités principales

- **Gestion de projets multi-sites** — plusieurs blogs depuis un seul compte
- **Génération IA d'articles** — idées, rédaction, SEO, callouts, FAQ, métadonnées, ~62 agents spécialisés (recherche, stratégie, création, révision)
- **Scores éditoriaux** — Global, SEO, Qualité, Lisibilité, Originalité, GEO, EEAT
- **Pipeline éditorial automatisé** — planification par fréquence (quotidienne/hebdomadaire/mensuelle/trimestrielle), à une date et heure précises configurées par projet
- **Production** — vue unifiée idées → rédaction → validation (remplace les anciennes pages Kanban/Idées/Validation séparées)
- **Éditeur riche** — TipTap avec sauvegarde automatique, historique de versions, commentaires inline
- **Tracking analytics** — script maison pour collecter vues, temps, engagement
- **Analytics** — vues, sources, appareils, tendances, performance par article
- **API publique** — expose articles et catégories au blog connecté
- **Revalidation à la demande** — secret de revalidation propre à chaque projet, généré automatiquement
- **Webhooks** — notifications d'événements vers des services externes
- **Gestion d'équipe** — rôles (owner, admin, editor, writer, viewer), invitations
- **Notifications** — alertes temps réel sur l'activité du projet
- **Catalogue de providers IA extensible** — Ollama (local ou cloud), OpenRouter, OpenAI, Gemini, Mistral, Anthropic ; catalogue géré par les administrateurs plateforme (`is_staff`), clés API par projet

---

## Cycle de vie d'un article

```
Idée proposée → Prioritaire → En rédaction → Brouillon prêt → À relire
→ Prêt → Programmé → Publié → Archivé
```

La validation humaine reste obligatoire avant publication : le pipeline ne publie jamais sans relecture.

---

## Architecture technique

```
┌─────────────────────────────────────────────────────┐
│                 Frontend React 19                    │
│            (Vite 8 + Tailwind 4 + TipTap 3)          │
└──────────────────────┬──────────────────────────────┘
                       │ API REST (JWT)
┌──────────────────────▼──────────────────────────────┐
│                FastAPI Backend (Python 3.12)          │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │
│  │ Auth JWT │ │ Routers  │ │  Services             │ │
│  └──────────┘ └──────────┘ └──────────────────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │
│  │ Worker   │ │ Providers│ │  SEO Engine           │ │
│  │ APSched. │ │ LLM/     │ │  Analyzer, Review     │ │
│  │          │ │ Search   │ │  Orchestrator         │ │
│  └──────────┘ └──────────┘ └──────────────────────┘ │
│  ┌──────────────────────────────────────────────────┐│
│  │   PostgreSQL (schémas ref/core/content/ai/        ││
│  │   analytics/ops)                                  ││
│  └──────────────────────────────────────────────────┘│
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
         ┌──────────────────────────┐
         │   Blog connecté          │
         │ (Tracking + API pub.)    │
         └──────────────────────────┘
```

Base de données : PostgreSQL uniquement (schéma v3 : schémas nommés, RLS, JSONB, ENUM natifs, partitionnement). SQLite n'est plus supporté, y compris en développement.

---

## Backend

- **Python 3.12**, **FastAPI** ≥ 0.115, **SQLAlchemy** 2.0, **Alembic** ≥ 1.13
- **APScheduler** — tâches planifiées (publications programmées, génération d'idées selon la fréquence configurée par projet, file de rédaction)
- **Pydantic v2** — validation et settings
- **JWT (python-jose) + bcrypt (passlib)** — authentification
- **Providers IA** — architecture pluggable, catalogue en base (`ai.providers`), clés chiffrées (Fernet) par projet (`ai.provider_credentials`)

### Routers API

`auth`, `profile`, `projects`, `categories`, `callouts`, `articles`, `public` (API publique), `tracking`, `ideas`, `seo`, `performance`, `recommendations`, `notifications`, `members`, `editor`, `versions`, `media`, `invitations`, `editorial_setup`, `pipeline`, `generation`, `comments`, `search`, `search_console`, `ai_providers`, `ai_agents`, `monitoring`, `activity`, `webhooks`, `kanban_columns`, `analytics`, `health`

---

## Frontend

- **React 19**, **TypeScript**, **Vite 8**, **Tailwind CSS 4**, **React Router 7**
- **TipTap 3 / ProseMirror** — éditeur riche

### Pages principales

| Page | Route | Description |
|---|---|---|
| Dashboard | `/projects/:id/dashboard` | Vue d'ensemble du projet |
| Articles | `/projects/:id/articles` | Articles publiés et programmés |
| Archives | `/projects/:id/archives` | Articles archivés |
| Catégories | `/projects/:id/categories` | Gestion des catégories |
| Production | `/projects/:id/production` | Idées, rédaction, validation (vue unifiée) |
| Médias | `/projects/:id/media` | Médiathèque du projet |
| Calendrier | `/projects/:id/calendar` | Planification éditoriale |
| Analytics | `/projects/:id/analytics` | Trafic, performance, sources |
| Recommandations | `/projects/:id/recommendations` | Recommandations SEO |
| Génération IA | `/projects/:id/generate` | Lancement et test du pipeline IA |
| Notifications | `/projects/:id/notifications` | Alertes activité |
| Paramètres | `/projects/:id/settings/*` | Général, stratégie, providers, membres, intégration, callouts, pipeline, agents |
| Profil | `/account` | Compte utilisateur |

Les anciennes routes `/kanban`, `/ideas`, `/validation`, `/performance*`, `/traffic` redirigent automatiquement vers `/production` ou `/analytics`.

---

## Base de données et migrations

L'historique complet de la migration v2 → v3 a été archivé (`alembic/versions_archive_v2/`) ; la révision courante est un point de départ unique (`v3_0001_baseline`), le DDL réel vivant dans `db/migration-v3/01-schema.sql` / `02-donnees.sql`.

```bash
# Voir la révision courante
./venv/bin/python -m alembic current

# Appliquer les migrations
./venv/bin/python -m alembic upgrade head

# Créer une nouvelle migration
./venv/bin/python -m alembic revision --autogenerate -m "description"
```

---

## Variables d'environnement

Voir `.env.example` pour la liste complète et commentée. Les principales :

| Variable | Description | Défaut |
|---|---|---|
| `SECRET_KEY` | Clé de chiffrement JWT + Fernet | requise en production |
| `DATABASE_URL` | URL de connexion PostgreSQL | requise (Postgres uniquement) |
| `APP_ENV` | Environnement (`development`, `test`, `production`) | `development` |
| `APP_URL` | URL publique du backend | `http://localhost:8000` |
| `FRONTEND_URL` | URL publique du frontend | vide |
| `CORS_ORIGINS` | Origines CORS autorisées, séparées par virgule | vide |
| `DEFAULT_LLM_PROVIDER` | Provider IA de repli en développement | `auto` |
| `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` | Stockage médias permanent (sinon disque local) | vide |
| `BLOG_REVALIDATE_URL` / `BLOG_REVALIDATE_SECRET` | Repli global si un projet n'a pas encore son propre secret de revalidation | vide |

Les providers IA réellement utilisés par un projet (clé API, modèle) se configurent en base via **Paramètres → Providers**, pas via variables d'environnement.

---

## Installation locale

### Prérequis

- Python 3.12
- Node.js 18+
- PostgreSQL (local ou instance distante type Supabase)
- Ollama (optionnel, génération IA locale gratuite)

### Backend

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Éditez .env : DATABASE_URL doit pointer vers un PostgreSQL réel
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
# Backend + frontend ensemble
npm run dev

# Backend seul
npm run dev:backend
# ou directement :
./venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Frontend seul
npm run dev:frontend
```

### Accès

- API : `http://127.0.0.1:8000`
- Documentation API (Swagger) : `http://127.0.0.1:8000/docs`
- Documentation ReDoc : `http://127.0.0.1:8000/redoc`
- Frontend : `http://localhost:5173`

---

## Tests

```bash
# Backend (nécessite une base PostgreSQL de test — voir V3_TEST_DATABASE_URL)
./venv/bin/python -m pytest tests/ -q

# Frontend — build
npm run build

# Frontend — lint
npm run lint

# Tests E2E Playwright (app doit tourner)
cd tests/e2e && npm test
```

---

## Sécurité

- **Authentification** : JWT avec expiration configurable
- **Clés API providers** : chiffrées (Fernet) avant stockage DB, jamais renvoyées en clair au frontend
- **Secret de revalidation** : chiffré, propre à chaque projet
- **Permissions** : rôles projet (owner, admin, editor, writer, viewer) + `is_staff` pour les actions d'administration plateforme (catalogue de providers)
- **Données tracking** : aucune donnée personnelle identifiable stockée

---

## Providers IA

Catalogue global (`ai.providers`), extensible par les administrateurs plateforme (`is_staff`) via **Paramètres → Providers → Catalogue des plateformes** :

| Provider | Type | Notes |
|---|---|---|
| **Ollama** | Local ou cloud | Sans clé API : instance locale (`127.0.0.1:11434`). Avec clé API : Ollama Cloud |
| **Gemini** | Cloud | Gratuit avec quota |
| **OpenRouter** | Cloud | Gratuit (modèles `:free`) ou payant |
| **OpenAI** | Cloud | Payant |
| **Anthropic** | Cloud | Payant |
| **Mistral** | Cloud | Gratuit/payant |

Chaque projet connecte ses propres clés API (**Paramètres → Providers**). Un provider par défaut sert de repli partagé pour tous les agents ; un mode avancé (**Paramètres → Agents**) permet d'assigner un provider/modèle spécifique à un agent donné si nécessaire.

---

## Déploiement

- **Backend** : Railway (voir `docs/DEPLOYMENT.md` — Render conservé comme alternative, voir `render.yaml`)
- **Frontend** : Vercel
- **Base de données** : PostgreSQL (Supabase en production)
- **Stockage médias** : Supabase Storage (repli disque local si non configuré)
- **Migrations** : exécutées automatiquement au démarrage du backend (sauf `APP_ENV=test`)

---

## Documentation du projet

| Fichier | Contenu |
|---|---|
| `CLAUDE.md` | Référence technique principale pour le développement |
| `LESSONS_LEARNED.md` | Erreurs rencontrées et comment les éviter |
| `KNOWN_ISSUES.md` | Problèmes connus, priorités et états |
| `DECISIONS.md` | Décisions architecturales et justifications |
| `docs/` | Documentation utilisateur, déploiement, schéma v3 |
| `db/migration-v3/` | Schéma SQL de référence et données de seed |

---

## Licence et contribution

Projet privé — Ideas Studio. Toute contribution doit passer par une revue de code.
