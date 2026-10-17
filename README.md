# Ideas Studio

Ideas Studio est un studio éditorial pour gérer des sites de contenu : idées,
rédaction locale, relecture humaine, publication planifiée et mises à jour.
Le rédacteur local est le seul composant qui produit les articles. Le CMS
conserve les sujets, les versions, les sources, les fiches et les contrôles
nécessaires à la publication.

## Parcours éditorial

Un article suit les états suivants :

```text
idée → en rédaction → à relire → validé → programmé → publié → à mettre à jour
```

La publication reste bloquée tant qu'une personne n'a pas validé l'article.
Les contrôles techniques affichés dans l'écran de relecture sont ceux du
parcours éditorial : encadré « En résumé », absence de tiret cadratin et fiche
valide. Le plagiat et la cannibalisation sont des alertes, pas des scores de
publication.

## Écrans

Chaque projet expose un parcours réduit à cinq écrans :

| Écran | Route | Rôle |
|---|---|---|
| Idées | `/projects/:projectId/editorial/ideas` | Ajouter des sujets et les envoyer en rédaction |
| Rédaction | `/projects/:projectId/editorial/writing` | Suivre la file et l'état des rédactions |
| Relecture | `/projects/:projectId/editorial/review` | Lire, modifier et valider un article |
| Publication | `/projects/:projectId/editorial/publication` | Voir les articles validés et leurs dates |
| Mises à jour | `/projects/:projectId/editorial/updates` | Revoir les informations devenues obsolètes |

Les réglages du projet restent accessibles séparément. Les anciennes routes
restent présentes tant que la migration des intégrations qui les utilisent
n'est pas terminée, mais elles ne font plus partie du parcours visible.

## Architecture

```text
Frontend React + TypeScript
          │ API REST / JWT
          ▼
FastAPI + SQLAlchemy + worker local
          │
          ▼
PostgreSQL (schémas ref, core, content, ai, analytics, ops)
```

Le backend est en Python 3.12 avec FastAPI, SQLAlchemy 2, Pydantic 2 et
Alembic. Le frontend utilise React 19, React Router, Vite et Tailwind CSS.
Les migrations de la base sont dans `alembic/versions/`.

Le rédacteur local se trouve dans `experiments/editorial_agent_lab/`. Il
récupère un sujet, reçoit les données éditoriales nécessaires, rédige avec le
skill local, puis dépose l'article et sa fiche par les routes du parcours
éditorial. Les fichiers de référence et les données de calibration ne sont
pas envoyés au rédacteur.

## Installation

Prérequis : Python 3.12, Node.js 18 ou plus récent et PostgreSQL.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head

cd frontend
npm install
```

`DATABASE_URL` doit pointer vers PostgreSQL. Les tests peuvent utiliser leur
configuration dédiée avec `APP_ENV=test`.

## Lancement

```bash
# depuis la racine
npm run dev

# backend seul
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# frontend seul
npm run dev:frontend
```

Le backend est disponible sur `http://127.0.0.1:8000`, sa documentation sur
`/docs`, et le frontend sur `http://localhost:5173`.

Pour lancer le rédacteur local après le démarrage du CMS :

```bash
.venv/bin/python -m experiments.editorial_agent_lab.local_worker <project_id>
```

Le worker utilise l'abonnement Claude local et ne nécessite pas de clé API
Anthropic ou OpenRouter dans le dépôt.

## Configuration

Les variables sont documentées dans `.env.example`. Les principales sont :

| Variable | Usage |
|---|---|
| `DATABASE_URL` | Connexion PostgreSQL |
| `SECRET_KEY` | Sessions et chiffrement |
| `APP_ENV` | Environnement d'exécution |
| `APP_URL` | URL du backend |
| `FRONTEND_URL` | URL du frontend |
| `CORS_ORIGINS` | Origines autorisées |
| `SUPABASE_URL` | Stockage permanent des médias, si utilisé |

Les clés de fournisseurs IA sont gérées par projet dans le CMS lorsqu'un
fournisseur distant est nécessaire. Le parcours local de rédaction n'en a
pas besoin.

## Tests

```bash
# backend
DATABASE_URL=postgresql://test:test@localhost/test \
APP_ENV=test .venv/bin/python -m pytest -q tests

# frontend
npm run build
```

Les tests E2E se trouvent dans `tests/e2e/` et nécessitent un backend et un
frontend démarrés.

## Déploiement

Le backend et le worker sont déployés selon l'environnement du projet. Les
migrations doivent être appliquées avec `alembic upgrade head` avant d'utiliser
une version qui introduit un nouveau schéma. Le frontend peut être construit
avec `npm run build` depuis la racine.
