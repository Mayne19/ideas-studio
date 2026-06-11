# Ideas Studio

**Headless AI-assisted SEO CMS pour blogs codés.**

Ideas Studio est une plateforme SaaS complète qui automatise la création de contenu SEO pour blogs et sites web. Elle combine génération IA, analyse SEO automatisée, pipeline éditorial et suivi de performance — le tout depuis une interface unique.

---

## Stack technique

### Backend

- **Python 3.11+** — Langage principal
- **FastAPI** — Framework web asynchrone
- **SQLAlchemy** — ORM base de données
- **Alembic** — Migrations
- **APScheduler** — Tâches planifiées (publications, pipelines)
- **Pydantic** — Validation et settings
- **OpenAI-compatible** — Architecture provider IA flexible
- **SQLite / PostgreSQL** — Support multi-base

### Frontend

- **React 18** — Bibliothèque UI
- **TypeScript** — Typage
- **Vite** — Bundler
- **Tailwind CSS** — Styles
- **TipTap / ProseMirror** — Éditeur riche

---

## Démarrage rapide

### Prérequis

- Python 3.11+
- Node.js 18+
- Ollama (optionnel, pour génération IA locale)

### Installation

```bash
# Backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Éditez .env selon votre configuration

# Frontend
cd frontend
npm install

# Base de données
cd ..
alembic upgrade head
```

### Lancement

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
- Documentation API : `http://localhost:8000/docs`
- Frontend : `http://localhost:5173`

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   Frontend React                │
│              (Vite + Tailwind + TipTap)         │
└──────────────────────┬──────────────────────────┘
                       │ API REST (JWT)
┌──────────────────────▼──────────────────────────┐
│              FastAPI Backend                     │
│                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ Auth JWT │ │ Routers  │ │  Services         │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ Workers  │ │ Providers│ │  SEO Engine       │ │
│  │ APSched. │ │ LLM/     │ │  Analyzer, Review │ │
│  │          │ │ Search   │ │  Orchestrator     │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
│  ┌─────────────────────────────────────────────┐ │
│  │         SQLite / PostgreSQL                 │ │
│  └─────────────────────────────────────────────┘ │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
         ┌─────────────────────────┐
         │    Blog connecté        │
         │  (Tracking + API pub.)  │
         └─────────────────────────┘
```

### Flux de génération d'article

```
1. Contexte projet → 2. Stratégie catégorie → 3. Découverte idée
→ 4. Vérification cannibalisation → 5. Analyse intention → 6. Brief recherche
→ 7. Brief keyword → 8. Angle éditorial → 9. Plan structuré
→ 10. Plan images → 11. Plan callouts → 12. Plan FAQ
→ 13. Liens internes → 14. Liens externes → 15. Rédaction
→ 16. Qualité linguistique → 17. Originalité → 18. Humanisation
→ 19. EEAT → 20. Qualité éditoriale → 21. Checklist SEO finale
→ 22. Review SEO agrégée → 23. Rapport de génération
```

### Flux pipeline automatisé

```
Worker (chaque heure ou 6h00)
  ├── Vérification publications planifiées (toutes les 5 min)
  │     └── Articles scheduled → publish
  ├── Tâches quotidiennes (6h00)
  │     └── Pour chaque projet → idées, optimisations
  └── Pipeline automatisé (chaque heure)
        └── Pour chaque projet avec pipeline enabled
              └── Idées → brouillons → review
```

---

## Documentation

| Document | Contenu |
|---|---|
| [Guide de déploiement](docs/DEPLOYMENT.md) | Installation production, Render, Vercel, variables d'env |
| [Documentation API](docs/API.md) | Tous les endpoints, authentification, exemples |
| [Guide IA Providers](docs/AI_PROVIDERS.md) | Configuration Ollama, Gemini, OpenAI, OpenRouter |
| [Guide utilisateur](docs/USER_GUIDE.md) | Projets, articles, SEO, pipeline, équipe |
| [Roadmap](docs/roadmap.md) | Fonctionnalités à venir |
| [Workflow article](docs/article-generation-workflow.md) | Processus détaillé de génération |

---

## Fonctionnalités principales

- **Gestion de projets multi-sites** — Créez et gérez plusieurs blogs depuis un seul compte
- **Génération IA d'idées SEO** — Idées d'articles avec analyse SERP, intention de recherche et scoring
- **Rédaction automatique** — Génération d'articles complets avec plan, FAQ, callouts, métadonnées
- **Orchestrateur SEO complet** — 23 étapes de la découverte au rapport de génération
- **Analyse SEO automatisée** — 4 scores (SEO, lisibilité, qualité, EEAT) + statut readiness
- **Pipeline éditorial automatisé** — Planification, priorisation des catégories, exécution quotidienne
- **Éditeur riche** — TipTap avec sauvegarde automatique, historique des versions, preview
- **Commentaires inline** — Révision collaborative avec sélection de texte
- **Tracking de trafic** — Script analytics maison intégré
- **API publique** — Exposez articles et catégories sur votre blog
- **Webhooks** — Notifications d'événements vers vos services externes
- **Gestion d'équipe** — Rôles (owner, admin, editor, writer, viewer) et invitations
- **Notifications** — Alertes en temps réel sur l'activité du projet

---

## Providers IA supportés

| Provider | Type | Coût | Configuration |
|---|---|---|---|
| **Ollama** | Local | Gratuit | `DEFAULT_LLM_PROVIDER=ollama` |
| **Google Gemini** | Cloud | Gratuit (quota) | `DEFAULT_LLM_PROVIDER=gemini` |
| **OpenRouter** | Cloud | Gratuit (modèles `:free`) | `DEFAULT_LLM_PROVIDER=openrouter` |
| **OpenAI** | Cloud | Payant | `DEFAULT_LLM_PROVIDER=openai` |
| **Anthropic** | Cloud | Payant | Via CMS providers |
| **Mistral AI** | Cloud | Gratuit/payant | Via CMS providers |
| **Custom** | Variable | Variable | OpenAI-compatible |

---

## Tests

```bash
pytest tests/ -v
```

---

## Licence et contribution

Projet privé — Ideas Studio. Toute contribution doit passer par une revue de code.
