# IDEAS STUDIO UCT SPEC V1

## 0. Nom

**Ideas Studio** [ideas-studio.com]

---

## 1. Vision uit

Ideas Studio est un **CMS headless SEO assisté par IA** pour blogs et sites codés.

Le but n'est pas seulement de générer des articles. Le but est de fournir une plateforme complète qui aide un utilisateur à :

1. connecter un site ou un blog codé ;
2. gérer plusieurs projets/blogs depuis une seule interface ;
3. proposer automatiquement des idées de contenus SEO ;
4. rédiger ou assister la rédaction d'articles ;
5. analyser le SEO, la lisibilité, la qualité, l'EEAT et la structure ;
6. publier ou programmer les articles ;
7. suivre les performances après publication ;
8. recommander des mises à jour pour améliorer le ranking.

Le principe central :

```txt
L'IA propose.
L'humain valide.
L'IA rédige.
L'humain corrige.
Le CMS publie.
Le système surveille.
L'IA recommande les optimisations.
```

---

## 2. Problème résolu

Créer, optimiser, publier et suivre des articles SEO prend beaucoup de temps.

Un utilisateur non expert doit normalement comprendre :

- la recherche de mots-clés ;
- l'intention de recherche ;
- le SEO on-page ;
- la structure H1/H2/H3 ;
- les liens internes ;
- les meta titles/descriptions ;
- la lisibilité ;
- le suivi Search Console ;
- la mise à jour des contenus existants.

Ideas Studio réduit cette complexité avec un workflow guidé.

L'utilisateur doit pouvoir uire du contenu publiable à **80–90% prêt**, puis corriger, valider et publier.

---

## 3. Public cible

### V1

- créateurs de blogs ;
- freelances ;
- petites agences ;
- propriétaires de sites codés sans CMS lourd ;
- personnes qui veulent gérer du contenu sans WordPress.

### Plus tard

- agences SEO ;
- équipes marketing ;
- studios web ;
- créateurs de contenu multi-sites.

---

## 4. Positionnement

Ideas Studio est une version simplifiée et actionnable de plusieurs mondes :

```txt
CMS headless + assistant rédaction IA + SEO analyzer + content workflow + performance monitor
```

Il ne doit pas devenir une copie complète de Semrush, Ahrefs ou WordPress.

Il doit faire moins de choses, mais les faire dans un flux beaucoup plus clair.

---

## 5. Décision importante : faut-il créer notre propre IA ?

Non.

Créer un modèle aussi performant que Claude, GPT ou Gemini n'est pas réaliste pour ce projet.

La bonne stratégie est :

```txt
Ne pas créer notre propre LLM.
Créer notre propre système autour des LLM.
```

Automat doit avoir une couche `LLMProvider` interchangeable :

- Ollama local pour réduire les coûts ;
- Claude/GPT/Gemini comme fallback premium ;
- possibilité de changer de modèle selon tâche.

Le vrai uit n'est pas le modèle IA. Le vrai uit est :

- la logique métier ;
- le workflow ;
- les prompts ;
- les règles SEO ;
- l'analyse ;
- le CMS ;
- la publication ;
- le monitoring.

---

## 6. Stratégie outils open source / externes

Objectif : dépendre le moins possible d'outils payants, sans sacrifier la qualité.

### Recherche web

Priorité :

- SearXNG auto-hébergé ;
- extraction via `trafilatura` ;
- fallback Tavily optionnel si activé ;
- Playwright seulement si nécessaire.

### Extraction de contenu

- `trafilatura` ;
- `BeautifulSoup4` ;
- `readability-lxml` si nécessaire.

### Correction grammaticale

- LanguageTool local via Docker.

### Rédaction IA

- Ollama local avec modèle configurable ;
- Claude/GPT comme fallback optionnel.

### SEO Analyzer

À coder nous-mêmes avec règles + scoring.

Le SEO Analyzer ne doit pas dépendre d'un outil externe payant.

### Lisibilité

À coder avec :

- règles maison ;
- longueur phrases ;
- longueur paragraphes ;
- répétitions ;
- structure titres ;
- score lisibilité simple.

### Originalité / unicité

V1 :

- détection de répétitions internes ;
- comparaison avec SERP résumée ;
- détection de sections trop génériques ;
- pas de service plagiat payant obligatoire.

### Analytics / trafic

- script tracking maison ;
- stockage en base ;
- Search Console plus tard.

### Base de données

V1 propre SaaS :

- PostgreSQL recommandé ;
- SQLite possible uniquement pour prototype local ;
- SQLAlchemy ou SQLModel.

### Jobs background

- Redis + RQ/Celery/Arq ;
- pour commencer simple : RQ + Redis.

---

## 7. Stack technique recommandée pour Ideas Studio V1

### Backend

- Python ;
- FastAPI recommandé pour API propre ;
- SQLAlchemy ou SQLModel ;
- PostgreSQL ;
- Alembic pour migrations ;
- Redis + RQ pour workers ;
- Pydantic pour validation.

### Frontend

- Next.js ou React plus tard ;
- pour vitesse : Vite + React possible ;
- design system propre ;
- éditeur WYSIWYG : TipTap recommandé.

### Auth

- email/password en V1 ;
- invitation par token ;
- Google OAuth en V2.

### Déploiement

- Railway / Render / VPS pour backend + worker ;
- PostgreSQL managé ;
- Redis managé ;
- Vercel possible pour frontend seulement.

---

## 8. Architecture globale

```txt
Frontend Dashboard
        ↓
Backend API
        ↓
PostgreSQL
        ↓
Workers background
        ↓
LLM / Search / SEO Analyzer / Publisher / Tracking
```

Modules backend :

```txt
Auth
Projects
CMS
Ideas
Writing
SEO Analyzer
Editor API
Publisher
Tracking
Performance
Optimization
Team/Roles
Notifications
Scheduler
```

---

## 9. Workflow complet du système

### 1. Création compte

L'utilisateur crée un compte ou accepte une invitation.

### 2. Création projet

Il crée un projet :

- nom du site ;
- domaine ;
- langue ;
- pays cible ;
- audience ;
- catégories ;
- ton éditorial ;
- objectifs SEO ;
- fréquence de publication.

### 3. Connexion du site

Le système fournit :

- snippet tracking ;
- project id ;
- public tracking key ;
- API publique articles ;
- secret API key masquée.

### 4. Audit initial

Le système crée un profil du projet.

### 5. Génération d'idées

Le système propose des idées sans rédiger.

### 6. Validation humaine

Le manager valide, modifie, priorise ou rejette.

### 7. Rédaction IA

Le pipeline rédige uniquement après validation.

### 8. Édition

L'utilisateur corrige dans l'éditeur.

### 9. Analyse SEO/lisibilité/qualité/EEAT

Le système vérifie l'article.

### 10. Publication/programming

L'utilisateur publie ou programme.

### 11. Suivi post-publication

Le système observe les performances.

### 12. Optimisation continue

Le système recommande des mises à jour.

---

## 10. Modules détaillés

## 10.1 Auth & Users

Fonctions :

- inscription ;
- connexion ;
- déconnexion ;
- reset password ;
- invitations ;
- rôles ;
- sessions.

Rôles globaux possibles :

- user ;
- admin plateforme.

Rôles projet :

- owner ;
- admin ;
- editor ;
- writer ;
- viewer.

---

## 10.2 Projects / Sites

Chaque projet représente un blog ou site connecté.

Champs projet :

- id ;
- owner_id ;
- name ;
- domain ;
- language ;
- country_target ;
- audience ;
- tone ;
- description ;
- publication_frequency ;
- public_tracking_key ;
- secret_api_key ;
- status ;
- connected_at ;
- last_seen_at.

---

## 10.3 Project Profile / Content Strategy

Le système doit comprendre le projet avant de proposer des idées.

Données :

- catégories ;
- priorité par catégorie ;
- articles existants ;
- audience cible ;
- concurrents ;
- objectifs ;
- style éditorial ;
- sujets à éviter ;
- sujets prioritaires ;
- fréquence cible.

Table possible : `project_strategy`

Champs :

- project_id ;
- target_audience ;
- tone ;
- seo_goal ;
- competitors_json ;
- forbidden_topics_json ;
- preferred_topics_json ;
- internal_linking_rules_json.

---

## 10.4 CMS Content Manager

Gère :

- articles ;
- brouillons ;
- catégories ;
- tags ;
- médias ;
- statuts ;
- publication ;
- programmation.

Statuts principaux :

- idea_proposed ;
- idea_priority ;
- idea_rejected ;
- outline_ready ;
- writing_requested ;
- writing_in_progress ;
- draft_ready ;
- review_needed ;
- correction_needed ;
- scheduled ;
- published ;
- failed ;
- update_recommended.

---

## 10.5 Idea Engine

But : proposer des idées intelligentes sans rédiger l'article complet.

Entrées :

- stratégie du projet ;
- catégories ;
- articles existants ;
- données trafic ;
- Search Console plus tard ;
- SERP ;
- tendances ;
- idées rejetées.

Sortie : carte idée.

Carte idée contient :

- titre proposé ;
- catégorie ;
- keyword principal ;
- keywords secondaires ;
- audience ;
- intention ;
- angle ;
- priorité ;
- opportunity score ;
- plan H2/H3 ;
- SERP summary ;
- raison de recommandation ;
- statut idea_proposed.

---

## 10.6 Writing Pipeline

Le pipeline de rédaction est lancé uniquement après validation.

Étapes :

1. charger la carte idée ;
2. rafraîchir recherche si nécessaire ;
3. rédiger l'article ;
4. ajouter FAQ ;
5. ajouter callouts ;
6. suggérer images ;
7. créer meta title/description ;
8. optimiser SEO ;
9. corriger grammaire ;
10. QA ;
11. sauvegarder brouillon ;
12. statut draft_ready ou review_needed.

---

## 10.7 Editor

L'éditeur est le centre du uit.

Fonctions :

- éditer le contenu ;
- afficher structure H1/H2/H3 ;
- modifier title/meta/slug ;
- gérer image couverture ;
- gérer callouts ;
- gérer FAQ ;
- voir checklist publication ;
- relancer analyse SEO ;
- appliquer suggestions ;
- publier/programmer.

Éditeur recommandé : TipTap.

---

## 10.8 SEO Analyzer

Le SEO Analyzer doit être puissant dans l'analyse, simple dans l'affichage.

### Analyse interne détaillée

Vérifications :

- keyword dans title ;
- keyword dans H1 ;
- keyword dans intro ;
- keyword dans H2/H3 ;
- densité keyword ;
- mots-clés secondaires ;
- longueur article ;
- structure H2/H3 ;
- meta title longueur et pertinence ;
- meta description longueur et pertinence ;
- slug ;
- liens internes ;
- liens externes ;
- FAQ ;
- callouts ;
- images ;
- alt text ;
- lisibilité ;
- phrases trop longues ;
- paragraphes trop longs ;
- répétitions ;
- originalité ;
- EEAT ;
- sources/citations ;
- intention de recherche ;
- adéquation SERP ;
- couverture du sujet ;
- maillage interne ;
- cannibalisation simple ;
- titre trop générique ;
- intro trop faible ;
- conclusion absente ;
- CTA si nécessaire.

### Scores affichés

L'utilisateur voit seulement :

- SEO Score /100 ;
- Readability Score /100 ;
- Quality Score /100 ;
- EEAT Score /100 ;
- Publication Readiness : prêt / à améliorer / bloqué.

### Détail actionnable

Chaque problème doit retourner :

- type ;
- gravité ;
- message clair ;
- suggestion ;
- section concernée ;
- action possible.

Exemple :

```json
{
  "type": "meta_description_missing_keyword",
  "severity": "warning",
  "message": "Le mot-clé principal n'apparaît pas dans la meta description.",
  "suggestion": "Ajoute le mot-clé principal naturellement dans les 150 premiers caractères.",
  "section": "meta_description"
}
```

---

## 10.9 Publisher

Deux stratégies possibles.

### Stratégie V1 recommandée

Automat stocke les articles et expose une API publique.

Le blog lit :

```txt
GET /api/public/projects/{project_id}/articles
GET /api/public/projects/{project_id}/articles/{slug}
```

### Plus tard

- WordPress REST API ;
- GitHub/MDX ;
- custom webhook ;
- publication statique.

---

## 10.10 Tracking

Snippet :

```html
<script
  src="https://ideas-studio.com/traffic.js"
  data-project-id="PROJECT_ID"
  data-tracking-key="PUBLIC_TRACKING_KEY"
  async>
</script>
```

Données collectées :

- page URL ;
- referrer ;
- device ;
- browser ;
- country si disponible ;
- timestamp ;
- anonymous visitor hash.

---

## 10.11 Performance Monitor

Surveille :

- visites ;
- pages vues ;
- articles les plus lus ;
- sources de trafic ;
- pays ;
- Search Console plus tard ;
- clics ;
- impressions ;
- position moyenne ;
- CTR.

Cycles :

- J+7 : observation légère ;
- J+30 : analyse performance ;
- J+90 : optimisation profonde.

---

## 10.12 Optimization Engine

Crée des recommandations :

- améliorer titre ;
- ajouter FAQ ;
- renforcer section ;
- ajouter liens internes ;
- mettre à jour données ;
- répondre mieux à l'intention ;
- améliorer EEAT.

Statut : `update_recommended`.

---

## 11. Tables principales

### users

- id ;
- name ;
- email ;
- password_hash ;
- created_at.

### projects

- id ;
- owner_id ;
- name ;
- domain ;
- language ;
- country_target ;
- audience ;
- tone ;
- status ;
- public_tracking_key ;
- secret_api_key ;
- connected_at ;
- last_seen_at ;
- created_at.

### project_members

- id ;
- project_id ;
- user_id ;
- role ;
- status ;
- created_at.

### categories

- id ;
- project_id ;
- name ;
- slug ;
- priority ;
- target_frequency ;
- created_at.

### articles

- id ;
- project_id ;
- title ;
- slug ;
- content ;
- status ;
- category_id ;
- keyword ;
- secondary_keywords_json ;
- audience ;
- angle ;
- search_intent ;
- outline_json ;
- serp_summary_json ;
- opportunity_score ;
- priority ;
- meta_title ;
- meta_description ;
- cover_image_url ;
- word_count ;
- seo_score ;
- readability_score ;
- quality_score ;
- eeat_score ;
- readiness_status ;
- rejection_reason ;
- rejection_note ;
- published_at ;
- scheduled_at ;
- created_at ;
- updated_at.

### seo_analyses

- id ;
- article_id ;
- project_id ;
- seo_score ;
- readability_score ;
- quality_score ;
- eeat_score ;
- readiness_status ;
- issues_json ;
- suggestions_json ;
- created_at.

### traffic_events

- id ;
- project_id ;
- url ;
- referrer ;
- country ;
- device ;
- browser ;
- created_at.

### optimization_recommendations

- id ;
- project_id ;
- article_id ;
- type ;
- priority ;
- reason ;
- suggestion ;
- status ;
- created_at.

---

## 12. API principales

### Auth

- POST /auth/login ;
- POST /auth/register ;
- POST /auth/logout ;
- GET /invite/{token} ;
- POST /invite/{token}/accept.

### Projects

- GET /projects ;
- POST /projects ;
- GET /projects/{id} ;
- PATCH /projects/{id} ;
- GET /projects/{id}/connect.

### Articles

- GET /projects/{id}/articles ;
- POST /projects/{id}/articles ;
- GET /articles/{id} ;
- PATCH /articles/{id} ;
- POST /articles/{id}/analyze ;
- POST /articles/{id}/publish ;
- POST /articles/{id}/schedule.

### Ideas

- POST /projects/{id}/ideas/generate ;
- POST /articles/{id}/start-writing ;
- POST /articles/{id}/reject ;
- POST /articles/{id}/priority ;
- POST /articles/{id}/manual-draft.

### Public API

- GET /api/public/projects/{id}/articles ;
- GET /api/public/projects/{id}/articles/{slug}.

### Tracking

- GET /traffic.js ;
- POST /api/traffic/collect.

---

## 13. Pages frontend

### Niveau global

- Login ;
- Register ;
- Mes projets ;
- Créer projet ;
- Invitation.

### Niveau projet

- Dashboard ;
- Idées ;
- Kanban ;
- Articles ;
- Éditeur ;
- SEO Analyzer ;
- Performance ;
- Équipe ;
- Paramètres.

---

## 14. Scope V1

V1 doit faire :

- comptes utilisateurs ;
- multi-projets ;
- invitations ;
- CMS articles ;
- catégories ;
- génération idées ;
- rédaction IA ;
- éditeur ;
- SEO Analyzer ;
- publication via API publique ;
- snippet tracking ;
- performance basique ;
- recommandations post-publication basiques ;
- rôles projet.

---

## 15. Scope V2

- billing Stripe ;
- Google OAuth ;
- WordPress integration ;
- GitHub/MDX publishing ;
- Search Console complète ;
- ranking tracker ;
- audit technique SEO ;
- backlinks ;
- analyse concurrents avancée ;
- A/B testing titres ;
- vraie collaboration temps réel.

---

## 16. Ce qu'on ne fait pas en V1

- pas de clone complet de Semrush ;
- pas de clone complet de WordPress ;
- pas de propre LLM entraîné maison ;
- pas de système backlinks complet ;
- pas de billing complet au début ;
- pas de 200 métriques visibles ;
- pas de dashboard ultra complexe.

---

## 17. Roadmap backend sur 5 jours

## Jour 1 — Architecture projet

Objectif : base propre.

À faire :

- créer nouveau repo `ideas-studio` ;
- choisir backend FastAPI ;
- config projet ;
- base PostgreSQL ou SQLite dev ;
- modèles users/projects/members ;
- auth email/password ;
- projets ;
- permissions projet ;
- migrations.

Livrable :

- login/register ;
- création projet ;
- accès projet sécurisé.

## Jour 2 — CMS Core

À faire :

- articles ;
- catégories ;
- statuts ;
- public API articles ;
- tracking keys ;
- snippet traffic ;
- traffic collect.

Livrable :

- créer article ;
- lister articles ;
- publier article ;
- blog peut lire articles published via API.

## Jour 3 — Idea Engine + Writing Pipeline

À faire :

- idea_only ;
- carte idée ;
- start-writing ;
- rejet idée ;
- priorité ;
- writing pipeline ;
- LLMProvider abstraction.

Livrable :

- générer une idée ;
- valider idée ;
- générer article complet.

## Jour 4 — SEO Analyzer + Editor API

À faire :

- SEO Analyzer détaillé ;
- scores simples ;
- suggestions ;
- endpoint analyze ;
- sauvegarde article ;
- meta/slug/cover/FAQ/callouts.

Livrable :

- un article peut être analysé après modification.

## Jour 5 — Performance + Optimization + Stabilisation

À faire :

- traffic dashboard API ;
- performance review J+7/J+30/J+90 ;
- optimization recommendations ;
- scheduler ;
- tests ;
- documentation API ;
- clean architecture.

Livrable :

- backend V1 utilisable pour front-end.

---

## 18. Règles pour les IA qui codent

Chaque IA doit lire ce document avant de coder.

Règles :

1. ne pas inventer une autre vision uit ;
2. respecter les modules ;
3. ne pas ajouter de fonctionnalités hors scope sans validation ;
4. ne pas casser le workflow ;
5. documenter chaque changement ;
6. ajouter ou mettre à jour les tests ;
7. séparer backend et frontend ;
8. ne jamais mettre de secret dans le frontend ;
9. garder le système multi-projets ;
10. toute donnée article/projet doit être liée à `project_id`.

---

## 19. Changelog du document

### 2026-05-04

- création de la spec uit V1 ;
- définition du uit comme CMS headless SEO assisté par IA ;
- décision : ne pas créer notre propre IA ;
- décision : SEO Analyzer puissant mais affichage simple ;
- décision : V2 propre recommandée ;
- ajout roadmap backend 5 jours ;
- renommage du projet : Automat SaaS → Ideas Studio.

## PROMPTS BACKEND

### Prompt Backend Day 1

```txt
Tu travailles sur un nouveau projet nommé Ideas Studio.

Avant de coder, lis entièrement le fichier :

prod.md

Ce fichier est la source de vérité du projet.

Règles :
- ne résume pas `prod.md`
- ne l’ignore pas
- ne pars pas dans une autre architecture
- ne fais pas autre chose que ce qui est demandé ici
- si une consigne de ce prompt contredit `prod.md`, demande confirmation avant d’agir
- travaille uniquement sur le JOUR 1 de la roadmap backend

OBJECTIF JOUR 1

Créer la base backend propre de Ideas Studio.

Ideas Studio est un CMS headless SEO assisté par IA pour blogs codés.

Aujourd’hui, tu dois uniquement mettre en place :
- structure backend
- configuration projet
- base de données
- auth email/password
- users
- projects
- project_members
- permissions projet
- migrations
- routes de base
- tests simples

Ne code pas encore :
- génération IA
- SEO Analyzer
- éditeur
- tracking
- publication
- frontend complet
- billing
- workers
- idées
- articles avancés

STACK DEMANDÉE

Backend :
- Python
- FastAPI
- SQLAlchemy ou SQLModel
- Alembic
- PostgreSQL prêt pour prod
- SQLite accepté en dev local si plus rapide
- Pydantic
- passlib/bcrypt pour password hash
- python-dotenv
- uvicorn

Crée une structure propre :

ideas-studio/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── database.py
│   ├── models/
│   │   ├── user.py
│   │   ├── project.py
│   │   └── project_member.py
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── user.py
│   │   └── project.py
│   ├── routers/
│   │   ├── auth.py
│   │   ├── projects.py
│   │   └── health.py
│   ├── services/
│   │   ├── auth_service.py
│   │   └── project_service.py
│   └── dependencies/
│       └── auth.py
├── alembic/
├── tests/
├── .env.example
├── requirements.txt
├── README.md
└── prod.md

MODÈLES À CRÉER

1. users

Champs :
- id
- name
- email unique
- password_hash
- is_active
- is_platform_admin
- created_at
- updated_at

2. projects

Champs :
- id
- owner_id
- name
- domain
- language
- country_target
- audience
- tone
- status
- public_tracking_key
- secret_api_key
- connected_at
- last_seen_at
- created_at
- updated_at

3. project_members

Champs :
- id
- project_id
- user_id
- role
- status
- created_at

Contrainte :
- un user ne doit pas être deux fois membre du même projet

RÔLES PROJET

Prévoir ces rôles :
- owner
- admin
- editor
- writer
- viewer

PERMISSIONS

Créer des helpers backend :

- get_current_user()
- require_auth()
- get_project_or_404()
- user_can_access_project(user_id, project_id)
- require_project_member(project_id)
- require_project_role(project_id, allowed_roles)

Règle :
Un utilisateur ne doit jamais accéder à un projet où il n’est pas membre.

AUTH

Créer routes :

POST /auth/register
- crée un user
- hash le mot de passe
- retourne user public

POST /auth/login
- vérifie email/password
- retourne access token ou session token

GET /auth/me
- retourne l’utilisateur connecté

POST /auth/logout
- route placeholder propre si JWT stateless

Tu peux utiliser JWT pour commencer.

PROJECTS

Créer routes :

GET /projects
- retourne uniquement les projets de l’utilisateur connecté

POST /projects
- crée un projet
- owner_id = current_user.id
- crée project_member avec role owner
- génère public_tracking_key
- génère secret_api_key
- status = not_connected

GET /projects/{project_id}
- retourne le projet seulement si user membre

PATCH /projects/{project_id}
- modifie projet seulement si owner/admin

GET /projects/{project_id}/connect
- retourne :
  - project_id
  - domain
  - status
  - public_tracking_key
  - snippet tracking
  - public API future endpoints placeholder
  - secret_api_key masquée ou partiellement masquée

SNIPPET À PRÉPARER

Même si tracking n’est pas codé aujourd’hui, prépare le snippet :

<script
  src="{APP_URL}/traffic.js"
  data-project-id="{project_id}"
  data-tracking-key="{public_tracking_key}"
  async>
</script>

HEALTH

Créer :

GET /health
- retourne ok

CONFIG

Créer .env.example avec :
- APP_NAME=Ideas Studio
- APP_ENV=development
- APP_URL=http://localhost:8000
- DATABASE_URL=sqlite:///./ideas_studio.db
- SECRET_KEY=change-me
- ACCESS_TOKEN_EXPIRE_MINUTES=1440

DATABASE / MIGRATIONS

Configurer Alembic.
Créer migration initiale pour :
- users
- projects
- project_members

TESTS MINIMUM

Ajouter ou exécuter tests simples :
1. register user
2. login user
3. create project
4. list projects
5. access own project OK
6. access other user project forbidden
7. project member created as owner

README

Créer un README.md court avec :
- installation
- lancement local
- variables .env
- commandes migration
- commandes test

COMMANDES ATTENDUES

Le projet doit pouvoir démarrer avec :

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload

RÈGLES IMPORTANTES

- Ne fais que le Jour 1.
- Ne code pas les articles aujourd’hui.
- Ne code pas le SEO Analyzer aujourd’hui.
- Ne code pas le tracking aujourd’hui.
- Ne code pas l’IA aujourd’hui.
- Ne fais pas de frontend complet.
- Ne change pas la vision produit.
- Garde le code propre, modulaire, extensible.
- Toute donnée future devra être liée à project_id.
- Ne mets jamais secret_api_key dans un script public.

RAPPORT FINAL

À la fin, donne :
1. fichiers créés
2. modèles créés
3. routes créées
4. commandes pour lancer
5. tests effectués
6. ce qui reste pour Jour 2
```

### Rapport Day 1

```txt
Rapport final — Jour 1
1. Fichiers créés

app/main.py
app/core/config.py, database.py, security.py
app/models/user.py, project.py, project_member.py
app/schemas/auth.py, user.py, project.py
app/routers/auth.py, projects.py, health.py
app/services/auth_service.py, project_service.py
app/dependencies/auth.py
alembic.ini, alembic/env.py, alembic/script.py.mako
alembic/versions/001_initial.py
tests/conftest.py, test_auth.py, test_projects.py
.env.example, requirements.txt, README.md
2. Modèles créés
Modèle	Champs clés
users	id, name, email (unique), password_hash, is_active, is_platform_admin, created_at, updated_at
projects	id, owner_id (FK), name, domain, language, country_target, audience, tone, status, public_tracking_key, secret_api_key, connected_at, last_seen_at, created_at, updated_at
project_members	id, project_id (FK), user_id (FK), role, status, created_at — UniqueConstraint (project_id, user_id)
Rôles projet disponibles : owner, admin, editor, writer, viewer

3. Routes créées

GET  /health
POST /auth/register
POST /auth/login
GET  /auth/me
POST /auth/logout
GET  /projects
POST /projects
GET  /projects/{project_id}
PATCH /projects/{project_id}
GET  /projects/{project_id}/connect
4. Commandes pour lancer

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
5. Tests effectués — 14/14 passent
Test	Résultat
register user	✅
duplicate email rejeté	✅
login user	✅
login mauvais password	✅
GET /auth/me	✅
GET /auth/me sans token	✅
create project	✅
list projects	✅
list ne retourne que ses projets	✅
access own project OK	✅
access other user project → 403	✅
project member créé comme owner	✅
patch project as owner	✅
connect info (snippet + clé masquée)	✅
Note technique : bcrypt doit rester < 4.0.0 — passlib 1.7.4 est incompatible avec bcrypt 4+/5+. Déjà pris en compte dans requirements.txt.

6. Ce qui reste pour Jour 2 (CMS Core)
Modèle articles (statuts complets : idea_proposed → published)
Modèle categories
Routes CRUD articles liées à project_id
Public API : GET /api/public/projects/{id}/articles et /{slug}
Route POST /api/traffic/collect (collecte basique)
Servir GET /traffic.js
Migration Alembic pour articles et categories
```

### Prompt Backend Day 2

```txt
Tu travailles sur le projet Ideas Studio.

Avant de coder, lis entièrement :

prod.md

Ce fichier est la source de vérité du projet.

AVANT DE MODIFIER

Commence par inspecter rapidement l’état actuel du projet :
- structure app/
- modèles existants
- routers existants
- dependencies auth/permissions existantes
- migrations Alembic existantes
- tests existants

Ne réécris pas le Jour 1.
Ne casse pas les routes déjà fonctionnelles.
Réutilise les helpers/services existants quand ils existent.
Si une fonction existe déjà, améliore-la au lieu de créer un doublon.

Avant de commencer le Jour 2, vérifie que les tests Jour 1 passent encore.

Règles :
- ne résume pas prod.md
- ne l’ignore pas
- ne pars pas dans une autre architecture
- ne fais pas autre chose que ce qui est demandé ici
- travaille uniquement sur le JOUR 2 de la roadmap backend
- ne touche pas au frontend sauf si une route API a besoin d’une réponse minimale
- ne code pas encore l’IA, l’Idea Engine, le SEO Analyzer ou les workers avancés

CONTEXTE

Le Jour 1 doit normalement avoir créé :
- structure FastAPI
- users
- auth email/password
- projects
- project_members
- permissions projet
- Alembic
- routes de base
- tests simples

OBJECTIF JOUR 2

Créer le cœur CMS de Ideas Studio.

Aujourd’hui, tu dois mettre en place :
- catégories
- articles
- statuts articles
- API publique articles publiés
- clés de tracking
- script traffic.js préparé
- endpoint traffic collect
- logique de publication simple
- tests backend

Ne code pas encore :
- génération IA
- pipeline d’idées
- rédaction IA
- SEO Analyzer complet
- éditeur frontend
- performance avancée
- recommandations post-publication
- billing

MODÈLES À CRÉER

1. categories

Champs :
- id
- project_id
- name
- slug
- description
- priority
- target_frequency
- created_at
- updated_at

Contraintes :
- category.project_id obligatoire
- slug unique par projet

2. articles

Champs :
- id
- project_id
- category_id
- title
- slug
- content
- excerpt
- status
- keyword
- secondary_keywords_json
- audience
- angle
- search_intent
- outline_json
- serp_summary_json
- opportunity_score
- priority
- meta_title
- meta_description
- cover_image_url
- word_count
- seo_score
- readability_score
- quality_score
- eeat_score
- readiness_status
- rejection_reason
- rejection_note
- published_at
- scheduled_at
- created_at
- updated_at

Statuts à prévoir :
- draft
- idea_proposed
- idea_priority
- idea_rejected
- outline_ready
- writing_requested
- writing_in_progress
- draft_ready
- review_needed
- correction_needed
- scheduled
- published
- failed
- update_recommended

Important :
Même si certains statuts seront surtout utilisés au Jour 3, la base doit déjà les accepter.

3. traffic_events

Champs :
- id
- project_id
- url
- path
- referrer
- country
- device
- browser
- visitor_hash
- user_agent
- created_at

ROUTES CATEGORIES

Créer :

GET /projects/{project_id}/categories
- liste les catégories du projet
- user doit être membre du projet

POST /projects/{project_id}/categories
- crée une catégorie
- owner/admin/editor autorisés
- génère slug automatiquement si absent

GET /categories/{category_id}
- retourne une catégorie si user membre du projet

PATCH /categories/{category_id}
- modifie catégorie
- owner/admin/editor autorisés

DELETE /categories/{category_id}
- supprimer seulement si aucun article lié
- sinon retourner erreur claire

ROUTES ARTICLES

Créer :

GET /projects/{project_id}/articles
- liste les articles du projet
- filtres possibles :
  - status
  - category_id
  - search
  - published_only
- pagination simple : limit / offset

POST /projects/{project_id}/articles
- crée un article manuel
- status par défaut = draft
- génère slug depuis title si absent

GET /articles/{article_id}
- retourne article si user membre du projet

PATCH /articles/{article_id}
- met à jour article
- editor/admin/owner ou writer si brouillon
- recalcul optionnel word_count si content modifié

POST /articles/{article_id}/publish
- status = published
- published_at = now
- uniquement owner/admin/editor

POST /articles/{article_id}/schedule
- status = scheduled
- scheduled_at requis
- uniquement owner/admin/editor

POST /articles/{article_id}/unpublish
- status = draft ou review_needed
- published_at peut rester comme historique ou être null selon choix documenté

API PUBLIQUE ARTICLES

Créer :

GET /api/public/projects/{project_id}/articles
- retourne uniquement les articles status=published
- ne retourne jamais les brouillons, idées, erreurs, contenus internes
- champs publics :
  - title
  - slug
  - excerpt
  - content
  - category
  - meta_title
  - meta_description
  - cover_image_url
  - published_at
  - updated_at

GET /api/public/projects/{project_id}/articles/{slug}
- retourne un article publié par slug
- 404 si non publié ou inexistant

Important :
Cette API est destinée au blog public.

TRACKING

Créer ou préparer :

GET /traffic.js

Ce script doit :
- lire data-project-id
- lire data-tracking-key
- collecter :
  - url
  - path
  - referrer
  - userAgent
  - screen/device minimal si possible
- envoyer POST vers /api/traffic/collect

POST /api/traffic/collect

Doit :
- recevoir project_id
- recevoir tracking_key
- vérifier que tracking_key == project.public_tracking_key
- refuser 403 si clé invalide
- enregistrer traffic_event
- mettre project.status = connected si première visite
- mettre project.last_seen_at = now
- ne jamais demander secret_api_key

Le script traffic.js doit être safe pour navigateur.

HELPERS

Créer helpers :
- slugify()
- generate_unique_slug_for_project()
- calculate_word_count()
- mask_secret_key()
- detect_device_from_user_agent() simple
- hash_visitor() simple anonymisé

SECURITÉ

Toutes les routes privées doivent :
- vérifier utilisateur connecté
- vérifier appartenance au projet
- vérifier rôle si modification

Rôles :
- owner/admin/editor : gérer catégories/articles
- writer : créer/modifier brouillons
- viewer : lecture seule

MIGRATIONS

Créer migration Alembic pour :
- categories
- articles
- traffic_events

Si une table existe déjà, garder compatibilité.

TESTS MINIMUM

Ajouter tests pour :
1. créer catégorie
2. lister catégories par projet
3. empêcher accès catégorie d’un autre projet
4. créer article
5. publier article
6. API publique retourne seulement articles published
7. API publique ne retourne pas draft
8. traffic collect avec bonne clé → 200
9. traffic collect avec mauvaise clé → 403
10. project.last_seen_at mis à jour après tracking
11. vérifier que les tests Jour 1 passent encore
12. vérifier que les routes Jour 1 ne sont pas cassées

README

Mettre à jour README avec :
- routes CMS
- exemple API publique
- exemple snippet tracking
- commandes tests

COMMANDES ATTENDUES

Le projet doit toujours démarrer avec :

uvicorn app.main:app --reload

Et tests avec :

pytest

Vérifie aussi :

alembic upgrade head

RAPPORT FINAL

À la fin, donne :
1. fichiers créés/modifiés
2. modèles ajoutés
3. migrations ajoutées
4. routes ajoutées
5. fonctionnement API publique
6. fonctionnement tracking
7. tests effectués
8. bugs connus
9. ce qui reste pour Jour 3
10. confirmation que les tests Jour 1 passent encore
11. confirmation que les routes Jour 1 n’ont pas été cassées
12. commande exacte utilisée pour lancer les tests

Important :
Ne commence pas le Jour 3.
```

### Rapport Day 2


### Prompt Backend Day 3

```txt
Tu travailles sur le projet Ideas Studio.

Avant de coder, lis entièrement :

prod.md

Ce fichier est la source de vérité du projet.

Règles :
- ne résume pas prod.md
- ne l’ignore pas
- ne pars pas dans une autre architecture
- travaille uniquement sur le JOUR 3 de la roadmap backend
- ne touche pas au frontend sauf minimum API nécessaire
- ne code pas le SEO Analyzer complet aujourd’hui
- ne code pas la performance post-publication aujourd’hui
- ne code pas le billing

CONTEXTE

Jour 1 doit avoir créé :
- auth
- users
- projects
- project_members
- permissions

Jour 2 doit avoir créé :
- categories
- articles
- API publique articles
- tracking de base
- traffic_events

OBJECTIF JOUR 3

Créer :
- Idea Engine
- séparation idea_only / full_article
- LLMProvider abstraction
- SearchProvider abstraction
- création de cartes idées
- lancement rédaction depuis une idée
- rejet / priorité / brouillon manuel
- routes API correspondantes
- jobs background simples si possible

PRINCIPE PRODUIT

Ideas Studio ne doit pas rédiger automatiquement tous les jours.

Le système doit d’abord proposer une idée :

recherche → keyword → angle → plan → carte idée → STOP

Puis l’humain choisit :

- lancer rédaction IA
- écrire manuellement
- rejeter
- prioriser
- modifier plus tard

MODÈLES / COLONNES À CONFIRMER

Vérifie que articles contient déjà :
- project_id
- title
- slug
- status
- category_id
- keyword
- secondary_keywords_json
- audience
- angle
- search_intent
- outline_json
- serp_summary_json
- opportunity_score
- priority
- rejection_reason
- rejection_note
- word_count
- content
- seo_score
- quality_score

Si certains champs manquent, ajoute migration backward-compatible.

AJOUTER SI NÉCESSAIRE

Table possible : article_logs

Champs :
- id
- project_id
- article_id
- level
- message
- step
- created_at

But :
suivre les étapes du pipeline.

PROVIDERS À CRÉER

Créer abstraction :

app/services/providers/llm_provider.py

Interface :
- generate_text(prompt, system=None, temperature=...)
- generate_json(prompt, schema_hint=None)
- is_available()

Créer implémentation simple :
- MockLLMProvider pour tests/dev
- OllamaLLMProvider si simple
- prévoir Claude/OpenAI plus tard sans l’implémenter si hors scope

Créer abstraction :

app/services/providers/search_provider.py

Interface :
- search(query, limit=10)
- is_available()

Créer implémentation simple :
- MockSearchProvider
- SearXNGSearchProvider si simple/configuré

Important :
Le système doit fonctionner en mode dev même sans vraie IA grâce aux providers mock.

IDEA ENGINE

Créer :

app/services/idea_engine.py

Fonction principale :

generate_idea(project_id, category_id=None)

Elle doit :
1. charger project
2. charger stratégie projet si disponible
3. choisir catégorie prioritaire si category_id absent
4. générer ou trouver un keyword principal
5. trouver keywords secondaires
6. créer une intention de recherche
7. proposer un angle
8. créer un plan H2/H3
9. créer serp_summary_json si search provider disponible
10. calculer opportunity_score simple
11. créer un article avec status=idea_proposed
12. retourner la carte idée

Pour dev sans IA :
- générer une idée réaliste mockée à partir de la catégorie/projet

Déduplication :
- ne pas recréer une idée avec le même keyword actif dans le même projet
- si doublon, retourner skipped ou proposer variante

WRITING ENGINE

Créer :

app/services/writing_engine.py

Fonction :

start_writing_from_idea(article_id)

Elle doit :
1. vérifier que l’article appartient au projet
2. vérifier status compatible :
   - idea_proposed
   - idea_priority
   - outline_ready
   - failed
3. passer status=writing_in_progress
4. utiliser keyword / angle / outline_json
5. générer contenu complet
6. créer meta_title/meta_description si absent
7. générer excerpt
8. calculer word_count
9. status=draft_ready ou review_needed
10. logguer les étapes

Pour dev sans IA :
- générer un contenu mock structuré avec H2/H3 depuis outline_json

ROUTES IDÉES

Créer :

POST /projects/{project_id}/ideas/generate

Body optionnel :
- category_id
- count
- mode

Action :
- génère 1 ou plusieurs idées
- par défaut count=1
- limite count raisonnable, ex max 5

Retour :
- liste des idées créées
- skipped duplicates si applicable

Créer :

POST /articles/{article_id}/start-writing

Action :
- lance rédaction depuis une idée
- si worker disponible, lancer en background
- sinon exécuter sync en dev
- retourne article mis à jour ou job_id

Créer :

POST /articles/{article_id}/reject

Body :
- reason
- note

Raisons :
- Sujet pas intéressant
- Mauvais angle
- Déjà traité
- Mot-clé trop faible
- Pas adapté au public
- Trop concurrentiel
- Autre

Action :
- status=idea_rejected
- rejection_reason
- rejection_note
- rejected_at si champ disponible

Créer :

POST /articles/{article_id}/priority

Action :
- priority=true
- status=idea_priority

Créer :

POST /articles/{article_id}/manual-draft

Action :
- transforme idée en brouillon manuel
- status=draft_ready
- content vide ou squelette basé sur outline_json

Créer :

POST /articles/{article_id}/rerun

Action :
- si idée → relancer génération plan ou rédaction
- si failed → relancer depuis étape possible
- v1 simple : relancer start_writing_from_idea

LAUNCH MODE

Préparer endpoint :

POST /projects/{project_id}/launch

Body :
- mode = idea_only | full_article
- category_id
- title
- keyword
- audience
- angle
- article_type

Si mode=idea_only :
- créer carte idée

Si mode=full_article :
- créer idée puis lancer writing_engine

SCHEDULER

Créer fonction :

generate_daily_ideas(project_id)

Elle doit :
- lire IDEAS_PER_DAY depuis settings
- générer N idées
- éviter doublons
- logguer résultat

Ne branche pas encore forcément cron complet si trop long.
Mais la fonction doit exister et être testable.

SETTINGS

Ajouter dans config :
- IDEAS_PER_DAY=1
- DEFAULT_LLM_PROVIDER=mock
- DEFAULT_SEARCH_PROVIDER=mock
- OLLAMA_URL
- SEARXNG_URL

SECURITÉ

Toutes les routes doivent vérifier :
- user connecté
- accès projet
- rôle

Permissions minimales :
- owner/admin/editor/writer peuvent générer idée
- owner/admin/editor/writer peuvent lancer rédaction
- owner/admin/editor peuvent rejeter/prioriser
- viewer lecture seule

TESTS MINIMUM

Ajouter tests :
1. generate idea crée un article status idea_proposed
2. generate idea avec même keyword évite doublon
3. reject idea met status idea_rejected
4. priority met idea_priority
5. manual draft met draft_ready
6. start-writing génère content mock et status draft_ready
7. user non membre ne peut pas générer idée
8. viewer ne peut pas modifier
9. generate_daily_ideas respecte IDEAS_PER_DAY

RAPPORT FINAL

À la fin, donne :
1. fichiers créés/modifiés
2. providers ajoutés
3. routes ajoutées
4. fonctionnement idea_only
5. fonctionnement full_article depuis idée
6. fonctionnement mock IA
7. tests effectués
8. ce qui reste pour Jour 4

Important :
Ne commence pas Jour 4.
```
### Rapport Day 3


### Prompt Backend Day 4

```txt
Tu travailles sur le projet Ideas Studio.

Avant de coder, lis entièrement :

prod.md

Ce fichier est la source de vérité du projet.

Règles :
- ne résume pas prod.md
- ne l’ignore pas
- travaille uniquement sur le JOUR 4 de la roadmap backend
- ne fais pas de frontend complet
- ne code pas le design de l’éditeur
- ne code pas la performance post-publication avancée
- ne code pas billing
- concentre-toi sur API + logique backend

CONTEXTE

Jour 1 :
- auth, projects, permissions

Jour 2 :
- CMS articles, categories, public API, tracking

Jour 3 :
- Idea Engine
- Writing Engine
- cartes idées
- start-writing depuis idée

OBJECTIF JOUR 4

Créer :
- SEO Analyzer backend
- Readability Analyzer
- Quality Analyzer
- EEAT checks
- endpoint analyze article
- sauvegarde article depuis éditeur
- gestion meta/slug/cover/FAQ/callouts
- suggestions actionnables
- scores simples affichables

PRINCIPE

Le moteur d’analyse doit être détaillé en interne, mais simple à afficher.

Il vérifie beaucoup de critères, mais retourne des scores simples :
- SEO Score /100
- Readability Score /100
- Quality Score /100
- EEAT Score /100
- Publication Readiness

MODÈLES À AJOUTER

Créer table seo_analyses :

Champs :
- id
- project_id
- article_id
- seo_score
- readability_score
- quality_score
- eeat_score
- readiness_status
- issues_json
- suggestions_json
- created_at

Ajouter à articles si absent :
- seo_score
- readability_score
- quality_score
- eeat_score
- readiness_status
- faq_json
- callouts_json
- internal_links_json
- external_links_json
- cover_image_url
- updated_at

SEO ANALYZER

Créer :

app/services/seo_analyzer.py

Fonction principale :

analyze_article(article_id)

Elle doit :
1. charger article
2. analyser title
3. analyser meta title
4. analyser meta description
5. analyser slug
6. analyser keyword
7. analyser structure H1/H2/H3
8. analyser longueur article
9. analyser densité keyword
10. analyser mots-clés secondaires
11. analyser liens internes
12. analyser liens externes
13. analyser images/alt text
14. analyser FAQ
15. analyser lisibilité
16. analyser qualité
17. analyser EEAT
18. calculer scores
19. sauvegarder seo_analyses
20. mettre à jour scores sur articles

CHECKS SEO DÉTAILLÉS

Vérifier :
- keyword dans title
- keyword dans H1
- keyword dans introduction
- keyword dans H2/H3
- densité raisonnable
- présence keywords secondaires
- longueur article suffisante
- meta title longueur correcte
- meta description longueur correcte
- keyword dans meta description
- slug lisible
- slug contient keyword si possible
- au moins 1 lien interne si article long
- liens externes pertinents
- structure H2/H3 logique
- pas de H1 multiples si contenu HTML
- FAQ présente si article informatif
- images avec alt text
- conclusion présente
- intro répond au sujet

READABILITY ANALYZER

Vérifier :
- phrases trop longues
- paragraphes trop longs
- répétitions
- mots trop complexes si détectable
- sections trop denses
- manque de sous-titres
- listes utiles
- lisibilité générale

QUALITY ANALYZER

Vérifier :
- contenu trop générique
- absence d’exemples
- absence de données concrètes
- sections vides
- répétitions entre sections
- couverture insuffisante du sujet
- introduction faible
- conclusion faible
- valeur ajoutée faible
- réponse à l’intention de recherche

EEAT CHECKS

Vérifier :
- présence sources/citations
- présence exemples concrets
- présence conseils actionnables
- absence d’affirmations non supportées
- clarté de l’auteur ou du point de vue si disponible
- contenu crédible
- liens externes fiables si nécessaires

FORMAT ISSUE

Chaque problème doit avoir :

{
  "type": "...",
  "category": "seo|readability|quality|eeat",
  "severity": "info|warning|critical",
  "message": "...",
  "suggestion": "...",
  "section": "...",
  "auto_fix_available": false
}

READINESS

Calculer readiness_status :

- ready si scores bons et aucun critical
- needs_improvement si warnings
- blocked si critical

ROUTES API

Créer :

POST /articles/{article_id}/analyze

Action :
- vérifie accès projet
- lance analyze_article
- retourne scores + issues + suggestions

GET /articles/{article_id}/analysis/latest

Action :
- retourne dernière analyse

GET /articles/{article_id}/analyses

Action :
- historique analyses

PATCH /articles/{article_id}/editor

Action :
- sauvegarde contenu édité
- champs acceptés :
  - title
  - slug
  - content
  - meta_title
  - meta_description
  - cover_image_url
  - faq_json
  - callouts_json
  - category_id
- recalcul word_count
- ne publie pas automatiquement

POST /articles/{article_id}/ready-check

Action :
- analyse l’article
- retourne si prêt à publier

OPTION AUTO-SUGGESTIONS

Créer fonction :

generate_improvement_suggestions(article_id)

V1 :
- pas besoin d’appeler LLM
- suggestions basées sur issues

Exemple :
Si meta_description trop courte :
→ “Allonge la meta description entre 140 et 160 caractères.”

TESTS

Ajouter tests :
1. analyze article retourne scores
2. article sans meta description crée warning
3. article trop court pénalise quality
4. article sans keyword dans title pénalise SEO
5. article avec phrases longues pénalise readability
6. critical bloque readiness
7. editor patch sauvegarde content
8. word_count recalculé
9. viewer ne peut pas modifier
10. user non membre ne peut pas analyser

README

Mettre à jour README :
- endpoints analyse
- exemple retour SEO
- logique scores

RAPPORT FINAL

À la fin, donne :
1. fichiers créés/modifiés
2. tables/colonnes ajoutées
3. checks SEO implémentés
4. scores implémentés
5. routes ajoutées
6. tests effectués
7. limitations connues
8. ce qui reste pour Jour 5

Important :
Ne commence pas Jour 5.
```
### Rapport Day 4

### Prompt Backend Day 5

```txt
Tu travailles sur le projet Ideas Studio.

Avant de coder, lis entièrement :

prod.md

Ce fichier est la source de vérité du projet.

Règles :
- ne résume pas prod.md
- ne l’ignore pas
- travaille uniquement sur le JOUR 5 de la roadmap backend
- ne fais pas de frontend complet
- ne code pas billing
- ne lance pas de grosse refonte architecture si les jours 1-4 sont stables

CONTEXTE

Jour 1 :
- auth/projects/permissions

Jour 2 :
- CMS/articles/categories/public API/tracking

Jour 3 :
- Idea Engine/Writing Engine

Jour 4 :
- SEO Analyzer/Editor API

OBJECTIF JOUR 5

Créer :
- APIs performance
- résumé traffic par projet
- performance articles
- review post-publication J+7/J+30/J+90
- optimization recommendations
- scheduler simple
- notifications backend
- stabilisation tests
- documentation API

MODÈLES À AJOUTER

1. optimization_recommendations

Champs :
- id
- project_id
- article_id
- type
- priority
- reason
- suggestion
- status
- created_at
- updated_at

Types possibles :
- improve_title
- improve_meta_description
- add_faq
- add_internal_links
- refresh_content
- improve_intro
- improve_eeat
- expand_section
- fix_low_traffic
- update_keywords

Status :
- pending
- accepted
- rejected
- applied

2. notifications

Champs :
- id
- project_id
- user_id nullable
- type
- title
- message
- level
- read_at
- created_at

Levels :
- info
- success
- warning
- error

PERFORMANCE SERVICES

Créer :

app/services/performance_service.py

Fonctions :

get_project_traffic_summary(project_id, period="30d")

Retour :
- total_views
- unique_pages
- top_pages
- referrers
- countries
- devices
- trend_by_day

get_article_performance(article_id, period="30d")

Retour :
- views
- referrers
- countries
- daily_views
- last_seen_at

POST-PUBLICATION REVIEW

Créer :

app/services/optimization_engine.py

Fonction :

review_published_articles(project_id)

Elle doit :
- trouver articles published
- regarder published_at
- classer :
  - J+7 observation
  - J+30 analyse
  - J+90 optimisation profonde
- analyser trafic disponible
- détecter articles faibles
- créer optimization_recommendations

Règles simples V1 :

Si article publié depuis plus de 30 jours et très peu de vues :
→ recommendation fix_low_traffic

Si article sans FAQ :
→ recommendation add_faq

Si SEO score faible :
→ recommendation improve_content

Si pas assez de liens internes :
→ recommendation add_internal_links

Si meta description faible :
→ recommendation improve_meta_description

Ne pas créer doublon si recommandation pending existe déjà.

ROUTES PERFORMANCE

Créer :

GET /projects/{project_id}/performance/summary
- résumé global

GET /projects/{project_id}/performance/articles
- performance par article

GET /articles/{article_id}/performance
- performance d’un article

ROUTES RECOMMENDATIONS

Créer :

GET /projects/{project_id}/recommendations
- liste recommandations

POST /recommendations/{recommendation_id}/accept
- status accepted

POST /recommendations/{recommendation_id}/reject
- status rejected

POST /recommendations/{recommendation_id}/apply
- status applied placeholder
- ne modifie pas automatiquement contenu en V1 si dangereux

ROUTES NOTIFICATIONS

Créer :

GET /projects/{project_id}/notifications
- liste notifications

POST /notifications/{notification_id}/read
- marque lu

POST /projects/{project_id}/notifications/read-all
- marque toutes lues

Créer helper :

create_notification(project_id, title, message, level="info", type="system")

SCHEDULER

Créer :

app/services/scheduler_service.py

Fonctions :
- run_daily_project_tasks(project_id)
- run_all_projects_daily_tasks()

Daily tasks :
- generate_daily_ideas(project_id)
- review_published_articles(project_id)
- create notifications if needed

Ne pas forcément installer cron complet.
Préparer fonction appelée plus tard par CLI ou worker.

CLI OPTIONNEL

Si structure simple, créer :

app/cli.py

Commandes :
- python -m app.cli daily
- python -m app.cli generate-ideas --project-id X
- python -m app.cli review --project-id X

Si trop long, créer seulement fonctions documentées.

SEARCH CONSOLE

Ne pas intégrer Google Search Console maintenant si pas déjà configuré.

Prévoir placeholder propre :

search_console_metrics_json nullable plus tard

PUBLIC API STABILISATION

Vérifier :
- API publique articles published seulement
- articles scheduled non visibles avant date si logique implémentée
- drafts non visibles
- no secret leaked

SECURITÉ

Toutes les routes privées :
- user connecté
- membre du projet
- rôle correct si action

TESTS

Ajouter tests :
1. performance summary retourne data même vide
2. article performance retourne data
3. review_published_articles crée recommendation
4. pas de doublon recommendation
5. accept recommendation
6. reject recommendation
7. notifications list
8. mark notification read
9. daily task appelle generate_daily_ideas et review
10. API publique ne leak pas draft/scheduled non publié

DOCUMENTATION

Mettre à jour README :
- endpoints performance
- endpoints recommendations
- scheduler
- daily tasks
- workflow complet backend V1

AUDIT FINAL BACKEND

Faire un audit rapide :
- routes principales
- modèles
- permissions
- project_id partout
- absence de secrets frontend
- tests OK

RAPPORT FINAL

À la fin, donne :
1. fichiers créés/modifiés
2. modèles ajoutés
3. routes ajoutées
4. performance summary fonctionnement
5. optimization engine fonctionnement
6. scheduler fonctionnement
7. notifications fonctionnement
8. tests effectués
9. points faibles restants
10. backend V1 prêt ou non pour frontend

Important :
Ne code pas le frontend.
Ne commence pas billing.
```
### Rapport Day 5

## PROMPT AUDIT FINAL BACKEND

```txt
Tu travailles sur le projet Ideas Studio.

Avant de répondre, lis entièrement :

prod.md

Tu dois faire un audit complet du backend V1 après les jours 1 à 5.

Ne modifie rien au début.
Commence par inspecter le projet.

OBJECTIF

Vérifier si le backend V1 est réellement prêt pour que le front-end soit développé.

À contrôler :

1. Architecture
- structure app propre
- séparation routers/services/models/schemas
- pas de logique énorme dans les routers
- config propre
- migrations présentes

2. Auth
- register
- login
- me
- password hash
- token/session
- user actif
- sécurité correcte

3. Projects
- création projet
- membres projet
- rôles
- permissions
- accès interdit entre projets
- project_id utilisé partout

4. CMS
- catégories
- articles
- statuts
- publication
- programmation
- API publique articles
- drafts non exposés

5. Tracking
- traffic.js
- collect endpoint
- tracking key vérifiée
- secret non exposé
- traffic lié à project_id

6. Idea Engine
- générer idée
- éviter doublons
- outline
- keyword
- angle
- priority
- rejet
- start-writing

7. Writing Engine
- full article depuis idée
- mock provider fonctionne
- structure article générée
- status correct
- logs si disponibles

8. SEO Analyzer
- scores
- issues
- suggestions
- readiness
- analyze endpoint
- editor patch

9. Performance
- traffic summary
- article performance
- recommendations
- review J+7/J+30/J+90
- notifications

10. Sécurité
- secrets non exposés
- permissions rôles
- user non membre bloqué
- viewer lecture seule
- tracking public key limitée

11. Tests
- tests unitaires
- tests API
- tests permissions
- tests isolation projet
- tests public API

12. Documentation
- README à jour
- .env.example complet
- commandes lancement
- commandes migration
- commandes tests

SORTIE ATTENDUE

Donne un rapport structuré :

1. Ce qui est prêt
2. Ce qui est partiellement prêt
3. Ce qui manque
4. Bugs ou risques
5. Dette technique
6. Recommandations avant frontend
7. Liste des endpoints disponibles
8. Liste des modèles/tables
9. Verdict final :
   - Backend V1 prêt pour frontend : oui/non
   - Si non, liste exacte des corrections bloquantes

Ne corrige rien sans que je te le demande.
```

