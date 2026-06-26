# CLAUDE.md — Ideas Studio

> Référence technique principale pour toute session de développement.  
> À consulter en premier. À maintenir à jour après chaque modification structurelle.

---

## Présentation du projet

**Ideas Studio** est un CMS éditorial SEO/GEO assisté par IA.  
Il permet à des équipes éditoriales de gérer projets, articles, idées, pipeline de génération IA, analyse SEO, médias, et performance — le tout dans une interface unifiée.

- Backend : API REST FastAPI (Python 3.12)
- Frontend : SPA React 19 (Vite 8 + TypeScript 6 + TailwindCSS 4)
- IA : multi-provider (Ollama, OpenRouter, OpenAI, Gemini, Mistral)
- Base : SQLite (dev) / PostgreSQL (prod)
- Déploiement cible : Render (backend) + Vercel (frontend)

---

## Stack technique

### Backend

| Composant | Technologie | Version |
|---|---|---|
| Framework | FastAPI | ≥ 0.115 |
| Runtime | Python | 3.12 |
| ORM | SQLAlchemy | 2.0 |
| Migrations | Alembic | ≥ 1.13 |
| Auth | JWT (python-jose) + bcrypt (passlib) | — |
| Validation | Pydantic v2 + pydantic-settings | ≥ 2.0 |
| Serveur | Uvicorn (standard) | ≥ 0.30 |
| Planificateur | APScheduler | ≥ 3.10 |
| Upload | python-multipart | — |
| Markdown | markdown | 3.7 |
| Tests | pytest + httpx | ≥ 8.0 |

### Frontend

| Composant | Technologie | Version |
|---|---|---|
| Framework | React | 19 |
| Build | Vite | 8 |
| TypeScript | TypeScript | 6 |
| CSS | TailwindCSS | 4 |
| Routing | React Router | 7 |
| Éditeur riche | TipTap | 3 |
| Graphiques | Recharts | 3 |
| Drag & Drop | dnd-kit | — |
| Icônes | HugeIcons | — |
| UI Kit | @mayne/ui-kit (GitHub) | — |

### Outillage de développement

| Outil | Usage |
|---|---|
| Playwright 1.61 | Tests E2E (Chromium + Mobile Chrome) |
| Lighthouse 13 | Audit SEO/accessibilité/performance |
| pytest | Tests unitaires et d'intégration backend |
| ESLint | Linting frontend |

---

## Structure du projet

```
ideas-studio/
├── app/                        # Backend FastAPI
│   ├── core/                   # Config, DB, security, utils
│   ├── models/                 # SQLAlchemy models (25+ modèles)
│   ├── routers/                # Routes API (31 routers)
│   ├── services/               # Logique métier
│   │   ├── seo/                # Pipeline SEO (20+ services)
│   │   ├── providers/          # LLM providers (Ollama, OpenAI, OpenRouter, Gemini)
│   │   └── agents/             # Agent registry & router
│   ├── dependencies/           # DI (auth)
│   └── main.py                 # Entrée app, CORS, migrations au démarrage
├── frontend/
│   └── src/
│       ├── api/                # Couche API (22 modules axios)
│       ├── components/
│       │   ├── editor/         # Panneaux éditeur (SEO, Media, Versions, etc.)
│       │   ├── layout/         # AppShell, Sidebar, Topbar
│       │   └── ui/             # Design system interne (30+ composants)
│       ├── context/            # AuthContext, ProjectContext, ThemeContext
│       ├── lib/                # TipTap extensions, utilitaires
│       ├── pages/              # Pages par domaine (34 pages)
│       └── routes/             # Définition des routes React Router
├── tests/                      # Tests backend (20 fichiers, 131+ tests)
│   └── e2e/                    # Tests Playwright (nouveau)
│       ├── specs/              # Tests par domaine
│       ├── fixtures/           # Helpers auth E2E
│       └── playwright.config.ts
├── alembic/                    # Migrations DB (30 révisions)
├── scripts/                    # dev.sh, seed_demo.py
├── docs/                       # Documentation AI, déploiement, API
├── uploads/                    # Médias uploadés (ignoré par git)
└── .claude/                    # Configuration MCP servers
```

---

## Modèles de données (SQLAlchemy)

| Modèle | Rôle |
|---|---|
| User | Utilisateur, auth, profil |
| Project | Projet éditorial, config, stratégie |
| ProjectMember | Membres et rôles (owner/editor/viewer) |
| Article | Article complet avec scores SEO/qualité/geo |
| ArticleVersion | Historique de versions |
| ArticleComment | Commentaires éditoriaux |
| ArticleLog | Journal des actions article |
| Category | Catégories éditoriales |
| Idea | Idées SEO / opportunités |
| Pipeline | Config du pipeline IA |
| PipelineLog | Journal d'exécution pipeline |
| MediaAsset | Médias uploadés |
| SeoAnalysis | Résultats analyse SEO |
| OptimizationRecommendation | Recommandations IA |
| KanbanColumn | Colonnes workflow personnalisées |
| Notification | Notifications projet |
| ActivityLog | Journal d'activité projet |
| AiProviderConfig | Config providers IA par projet |
| AgentAssignment | Assignation agents ↔ providers |
| AiUsageLog | Log coût/token IA |
| Invitation | Invitations par email |
| PasswordResetToken | Tokens reset mot de passe |
| TrafficEvent | Événements analytics tracking |
| Webhook | Webhooks sortants |
| ProjectCalloutTemplate | Templates callouts éditeur |

---

## Routes API principales

```
/health                         # Santé backend
/auth/*                         # Register, login, session
/profile/*                      # Profil utilisateur, avatar
/projects/*                     # CRUD projets
/projects/{id}/members/*        # Membres et rôles
/projects/{id}/invitations/*    # Invitations
/projects/{id}/articles/*       # Articles (CRUD, publish, archive)
/projects/{id}/articles/{id}/editor/*    # Autosave, preview
/projects/{id}/articles/{id}/versions/*  # Historique versions
/projects/{id}/articles/{id}/comments/*  # Commentaires
/projects/{id}/categories/*     # Catégories
/projects/{id}/callouts/*       # Templates callouts
/projects/{id}/ideas/*          # Idées SEO
/projects/{id}/seo/*            # Analyse SEO
/projects/{id}/pipeline/*       # Config pipeline
/projects/{id}/generation/*     # Génération IA
/projects/{id}/media/*          # Médiathèque
/projects/{id}/performance/*    # Métriques
/projects/{id}/recommendations/* # Recommandations IA
/projects/{id}/notifications/*  # Notifications
/projects/{id}/ai-providers/*   # Providers IA
/projects/{id}/agents/*         # Agents IA
/projects/{id}/kanban-columns/* # Colonnes kanban
/projects/{id}/webhooks/*       # Webhooks
/projects/{id}/activity/*       # Journal activité
/public/{slug}/*                # API publique (articles publiés)
/tracking/*                     # Événements analytics
/search/*                       # Recherche globale
/search-console/*               # Google Search Console
```

---

## Pages frontend (React Router)

```
/login, /register               # Auth
/forgot-password, /reset-password
/projects                       # Liste projets
/projects/:id                   # Dashboard projet
/projects/:id/articles          # Liste articles
/projects/:id/articles/:aid/edit  # Éditeur article
/projects/:id/ideas             # Pipeline idées
/projects/:id/kanban            # Vue kanban
/projects/:id/calendar          # Calendrier éditorial
/projects/:id/categories        # Catégories
/projects/:id/media             # Médiathèque
/projects/:id/generate          # Génération IA
/projects/:id/traffic           # Analytics trafic
/projects/:id/performance       # Performance articles
/projects/:id/recommendations   # Recommandations
/projects/:id/validation        # Validation articles
/projects/:id/notifications     # Notifications
/projects/:id/archives          # Archives
/projects/:id/settings          # (plusieurs onglets)
/account                        # Compte utilisateur
/p/:slug                        # Pages publiques
/docs                           # Documentation
```

---

## Commandes de développement

```bash
# Démarrer dev complet (backend + frontend)
npm run dev

# Backend seul
npm run dev:backend
# ou directement :
./venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Frontend seul
npm run dev:frontend

# Frontend Vite seul (si backend déjà lancé)
npm run dev:vite
```

URLs : backend `http://127.0.0.1:8000` · frontend `http://localhost:5173` · API docs `http://127.0.0.1:8000/docs`

---

## Commandes de build

```bash
# Build frontend (TypeScript check + Vite bundle)
npm run build

# Linting frontend
npm run lint

# Prévisualiser le build
npm run preview
```

---

## Commandes de tests

```bash
# Tests backend (pytest, depuis la racine)
./venv/bin/python -m pytest tests/ -v

# Tests par fichier
./venv/bin/python -m pytest tests/test_articles.py -v

# Tests rapides (sans output verbose)
./venv/bin/python -m pytest tests/

# Tests E2E Playwright (app doit tourner)
cd tests/e2e && npm test
cd tests/e2e && npm run test:headed  # mode visible
cd tests/e2e && npm run test:debug   # mode debug
cd tests/e2e && npm run test:report  # rapport HTML

# Audit Lighthouse (app doit tourner)
lighthouse http://localhost:5173 --output html --output-path ./lighthouse-report.html
```

---

## Commandes de migration

```bash
# Créer une migration
./venv/bin/python -m alembic revision --autogenerate -m "description"

# Appliquer les migrations
./venv/bin/python -m alembic upgrade head

# Rollback
./venv/bin/python -m alembic downgrade -1

# Voir la révision courante
./venv/bin/python -m alembic current
```

---

## Configuration environnement

Copier `.env.example` → `.env` et adapter :

```bash
APP_ENV=development
DATABASE_URL=sqlite:///./ideas_studio.db
SECRET_KEY=<générer avec secrets.token_urlsafe(48)>
DEFAULT_LLM_PROVIDER=ollama   # ou openrouter, openai, gemini, mock
```

Les migrations Alembic s'exécutent **automatiquement au démarrage** (sauf en mode `test`).

---

## Conventions de code

### Backend (Python)

- Schemas Pydantic v2 pour toutes les entrées/sorties API
- Dépendance `get_db` injectée via FastAPI DI
- Auth via `get_current_user` dans `app/dependencies/auth.py`
- Permissions vérifiées via `ProjectMember` (owner / editor / viewer)
- Services dans `app/services/` — jamais de logique dans les routers
- Migrations Alembic : une par fonctionnalité, nommées avec numéro séquentiel
- Jamais de clé API exposée en clair dans les réponses

### Frontend (TypeScript/React)

- Alias `@/` → `frontend/src/`
- Un composant = un fichier `.tsx`
- Contextes globaux : `AuthContext`, `ProjectContext`, `ThemeContext`
- Couche API : `frontend/src/api/*.ts` (un fichier par domaine)
- Design system interne : `frontend/src/components/ui/`
- TipTap v3 pour l'éditeur riche
- Tailwind v4 (sans fichier de config — configuration inline)

---

## Workflow Git

```
main               # Branche principale, toujours stable
feature/<name>     # Nouvelles fonctionnalités
fix/<name>         # Corrections de bugs
refactor/<name>    # Refactoring
```

Commits atomiques au format :
```
type(scope): description courte

Corps optionnel si explication nécessaire.
```

Types : `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`

---

## Checklist avant commit

- [ ] `./venv/bin/python -m pytest tests/` → tous les tests passent
- [ ] `npm run lint` → aucune erreur ESLint
- [ ] `npm run build` → build TypeScript sans erreur
- [ ] Aucune clé API ou secret dans le code
- [ ] `.env` non inclus dans le commit
- [ ] Migration Alembic créée si modèle modifié
- [ ] Logique métier dans les services, pas dans les routers

---

## Checklist avant merge

- [ ] Tests backend 100% verts
- [ ] Build frontend sans erreur TypeScript
- [ ] Tests E2E Playwright sur les parcours impactés
- [ ] Pas de régression sur les routes existantes
- [ ] DECISIONS.md mis à jour si décision architecturale
- [ ] KNOWN_ISSUES.md mis à jour si problème connu introduit

---

## Checklist avant release

- [ ] Toutes les checklists merge validées
- [ ] `.env.example` à jour avec les nouvelles variables
- [ ] Migration Alembic `upgrade head` testée sur base vierge
- [ ] Audit Lighthouse ≥ 80 sur toutes les catégories
- [ ] Variables d'environnement Render/Vercel mises à jour
- [ ] README.md à jour

---

## MCP Servers configurés (`.claude/settings.json`)

| Serveur | Usage |
|---|---|
| context7 | Documentation officielle frameworks (React, FastAPI, TipTap, etc.) |
| sequential-thinking | Résolution de problèmes complexes étape par étape |
| filesystem | Navigation, lecture et refactoring du projet |
| git | Commits, branches, historique Git |
| sqlite | Inspection base SQLite : schéma, requêtes, migrations |
| puppeteer | Chrome DevTools : DOM, console, réseau, captures |
| browser-tools | Inspection navigateur avancée, React DevTools |

---

## Fichiers de documentation

| Fichier | Contenu |
|---|---|
| `CLAUDE.md` | Ce fichier — référence technique principale |
| `AGENTS.md` | Rôles des agents de review et leurs procédures |
| `DECISIONS.md` | Décisions architecturales et justifications |
| `LESSONS_LEARNED.md` | Erreurs rencontrées et comment les éviter |
| `KNOWN_ISSUES.md` | Problèmes connus, priorités et états |
| `docs/` | Documentation utilisateur, déploiement, API |
| `external-audit/` | Audit externe, roadmap, stratégies SEO |
