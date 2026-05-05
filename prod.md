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

## Règle actuelle avec `prod.md` et `label.md`

À partir de maintenant, le projet utilise deux documents :

```txt
prod.md  = source de vérité principale pour la V1 à coder maintenant
label.md = annexe stratégique IA/SEO long terme
```

Règles :

1. `prod.md` reste prioritaire pour le développement backend V1.
2. `label.md` doit être lu pour comprendre la direction stratégique future.
3. `label.md` ne doit jamais élargir automatiquement le scope du jour en cours.
4. Les modules avancés de `label.md` ne doivent pas être codés tant qu’ils ne sont pas explicitement demandés.
5. Chaque jour de roadmap doit rester limité à son objectif.
6. Les choix techniques doivent rester extensibles pour ne pas bloquer les futurs modules IA/SEO.
7. Ne pas transformer la V1 en système trop complexe avant d’avoir fini le backend stable.

Modules avancés de `label.md` à NE PAS coder automatiquement dans les jours 1 à 5 :

```txt
Source Ledger
Source Verification Engine
Claim-to-Source Mapping
Deep Rewrite Engine complet
Natural Writing Engine complet
Google Fit Score
Originality Engine complet
Safe Publish Gate
ContentBrief complet
Model Router avancé
Model Performance Registry
Prompt Versioning complet
AI Jobs avancés
Article Versioning
Audit Trail avancé
Webhooks avancés
Billing
Quotas IA
Google Update Watcher
Topical Authority Engine avancé
Competitive Comparison View
```

Ces éléments servent pour la roadmap future : V1 renforcée, V1.5, V2.

---

## PROMPTS BACKEND

---

# Prompt Backend Day 1 — ARCHIVÉ / DÉJÀ FAIT

```txt
Tu travailles sur un nouveau projet nommé Ideas Studio.

Avant de coder, lis entièrement :

prod.md

Ce fichier est la source de vérité principale du projet.

Si label.md existe déjà, lis-le uniquement comme annexe stratégique long terme.
Ne code aucun module avancé de label.md pendant le Jour 1.

Règles :
- ne résume pas prod.md
- ne l’ignore pas
- ne pars pas dans une autre architecture
- ne fais pas autre chose que ce qui est demandé ici
- si une consigne de ce prompt contredit prod.md, demande confirmation avant d’agir
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
- modules avancés de label.md

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

---

# Rapport Day 1

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

users :
id, name, email unique, password_hash, is_active, is_platform_admin, created_at, updated_at

projects :
id, owner_id, name, domain, language, country_target, audience, tone, status, public_tracking_key, secret_api_key, connected_at, last_seen_at, created_at, updated_at

project_members :
id, project_id, user_id, role, status, created_at
UniqueConstraint(project_id, user_id)

Rôles projet disponibles :
owner, admin, editor, writer, viewer

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

register user
duplicate email rejeté
login user
login mauvais password
GET /auth/me
GET /auth/me sans token
create project
list projects
list ne retourne que ses projets
access own project OK
access other user project → 403
project member créé comme owner
patch project as owner
connect info snippet + clé masquée

Note technique :
bcrypt doit rester < 4.0.0.
passlib 1.7.4 est incompatible avec bcrypt 4+/5+.
Déjà pris en compte dans requirements.txt.

6. Ce qui reste pour Jour 2

Modèle articles
Modèle categories
Routes CRUD articles liées à project_id
Public API articles published
Route POST /api/traffic/collect
Servir GET /traffic.js
Migration Alembic pour articles/categories/traffic_events
```

---

# Prompt Backend Day 2 — ARCHIVÉ / DÉJÀ FAIT

```txt
Tu travailles sur le projet Ideas Studio.

Avant de coder, lis entièrement :

prod.md
label.md

RÈGLE DE PRIORITÉ ENTRE LES DOCUMENTS

prod.md est la source de vérité principale pour ce qui doit être codé maintenant en V1.

label.md est une annexe stratégique IA/SEO long terme.
Il sert à comprendre la direction future du produit, mais il ne doit pas élargir le scope du jour en cours.

Si label.md propose un module avancé qui n’est pas explicitement demandé dans le Jour 2, ne l’implémente pas maintenant.

Utilise label.md seulement pour :
- garder une architecture extensible ;
- éviter des choix qui bloqueraient les futurs modules IA/SEO ;
- préparer proprement les futurs modules sans les coder aujourd’hui.

Ne crée pas aujourd’hui les modules avancés de label.md :
- Source Ledger
- Source Verification Engine
- Claim-to-Source Mapping
- Deep Rewrite Engine
- Natural Writing Engine
- Google Fit Score
- Originality Engine
- Safe Publish Gate
- ContentBrief
- Model Router
- Prompt Versioning
- AI Jobs avancés
- Article Versioning
- Audit Trail avancé
- Webhooks
- Billing
- Quotas IA

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
- ne résume pas label.md
- ne les ignore pas
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
- modules avancés de label.md

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
Ne code pas les modules avancés de label.md.
```

---

# Rapport Day 2

```txt
À coller ici après réception du rapport final de Claude pour le Jour 2.
```

---

# Prompt Backend Day 3

```txt
Tu travailles sur le projet Ideas Studio.

Avant de coder, lis entièrement :

prod.md
label.md

RÈGLE DE PRIORITÉ ENTRE LES DOCUMENTS

prod.md est la source de vérité principale pour ce qui doit être codé maintenant en V1.

label.md est une annexe stratégique IA/SEO long terme.
Il sert à comprendre la direction future du produit, mais il ne doit pas élargir le scope du jour en cours.

Si label.md propose un module avancé qui n’est pas explicitement demandé dans le Jour 3, ne l’implémente pas maintenant.

Utilise label.md seulement pour :
- garder une architecture extensible ;
- éviter des choix qui bloqueraient les futurs modules IA/SEO ;
- nommer proprement les dossiers/services si cela aide ;
- préparer des abstractions simples, sans coder les modules avancés.

Ne crée pas aujourd’hui les modules avancés de label.md :
- Source Ledger
- Source Verification Engine
- Claim-to-Source Mapping
- Deep Rewrite Engine complet
- Natural Writing Engine complet
- Google Fit Score
- Originality Engine
- Safe Publish Gate
- ContentBrief complet
- Model Router avancé
- Prompt Versioning
- AI Jobs avancés
- Article Versioning
- Audit Trail avancé
- Webhooks
- Billing
- Quotas IA

AVANT DE MODIFIER

Commence par inspecter rapidement l’état actuel du projet :
- structure app/
- modèles existants
- routers existants
- services existants
- providers existants s’il y en a
- dependencies auth/permissions existantes
- migrations Alembic existantes
- tests existants

Ne réécris pas les Jours 1 et 2.
Ne casse pas les routes déjà fonctionnelles.
Réutilise les helpers/services existants quand ils existent.
Si une fonction existe déjà, améliore-la au lieu de créer un doublon.

Avant de commencer le Jour 3, vérifie que les tests Jour 1 et Jour 2 passent encore.

RÈGLES GÉNÉRALES

- ne résume pas prod.md
- ne résume pas label.md
- ne pars pas dans une autre architecture
- ne fais pas autre chose que ce qui est demandé ici
- travaille uniquement sur le JOUR 3 de la roadmap backend
- ne touche pas au frontend sauf minimum API nécessaire
- ne code pas le SEO Analyzer complet aujourd’hui
- ne code pas la performance post-publication aujourd’hui
- ne code pas le billing
- ne code pas les modules avancés de label.md aujourd’hui

CONTEXTE

Jour 1 doit avoir créé :
- auth
- users
- projects
- project_members
- permissions
- routes de base
- migrations initiales
- tests auth/projects

Jour 2 doit avoir créé :
- categories
- articles
- statuts articles
- API publique articles
- tracking de base
- traffic_events
- traffic.js
- routes CMS
- tests CMS/public API/tracking

OBJECTIF JOUR 3

Créer :
- Idea Engine
- séparation idea_only / full_article
- LLMProvider abstraction simple
- SearchProvider abstraction simple
- création de cartes idées
- lancement rédaction depuis une idée
- rejet / priorité / brouillon manuel
- routes API correspondantes
- scheduler simple pour generate_daily_ideas
- logs simples du pipeline si raisonnable

PRINCIPE PRODUIT

Ideas Studio ne doit pas rédiger automatiquement tous les jours sans validation.

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

Si certains champs manquent, ajoute une migration backward-compatible.

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
suivre les étapes simples du pipeline Jour 3.

Important :
article_logs doit rester simple.
Ne crée pas encore le système complet ai_jobs décrit dans label.md.

PROVIDERS À CRÉER

Créer abstraction :

app/services/providers/llm_provider.py

Interface :
- generate_text(prompt, system=None, temperature=...)
- generate_json(prompt, schema_hint=None)
- is_available()

Créer implémentation simple :
- MockLLMProvider pour tests/dev
- OllamaLLMProvider seulement si simple et non bloquant
- prévoir Claude/OpenAI plus tard sans les implémenter aujourd’hui

Créer abstraction :

app/services/providers/search_provider.py

Interface :
- search(query, limit=10)
- is_available()

Créer implémentation simple :
- MockSearchProvider
- SearXNGSearchProvider seulement si simple/configuré

Important :
Le système doit fonctionner en mode dev même sans vraie IA grâce aux providers mock.

Ne crée pas aujourd’hui :
- LiteLLM complet
- Model Router avancé
- Model Performance Registry
- Cost Tracker avancé
- Prompt Versioning complet

IDEA ENGINE

Créer :

app/services/idea_engine.py

Fonction principale :

generate_idea(project_id, category_id=None)

Elle doit :
1. charger project
2. charger catégorie si category_id fourni
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
1. vérifier que l’article existe
2. vérifier que l’article appartient bien à un projet
3. vérifier status compatible :
   - idea_proposed
   - idea_priority
   - outline_ready
   - failed
4. passer status=writing_in_progress
5. utiliser keyword / angle / outline_json
6. générer contenu complet
7. créer meta_title/meta_description si absent
8. générer excerpt
9. calculer word_count
10. status=draft_ready ou review_needed
11. logguer les étapes si article_logs existe

Pour dev sans IA :
- générer un contenu mock structuré avec H2/H3 depuis outline_json

Important :
Le Writing Engine Jour 3 reste simple.

Ne code pas encore :
- Deep Rewrite Engine complet
- Natural Writing Engine complet
- Originality Engine
- Source Verification Engine
- Safe Publish Gate

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
- retourne article mis à jour ou job_id simple

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
- V1 simple : relancer start_writing_from_idea

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

SCHEDULER SIMPLE

Créer fonction :

generate_daily_ideas(project_id)

Elle doit :
- lire IDEAS_PER_DAY depuis settings
- générer N idées
- éviter doublons
- logguer résultat

Ne branche pas encore cron complet.
Ne crée pas encore ai_jobs complet.
La fonction doit seulement exister et être testable.

SETTINGS

Ajouter dans config :
- IDEAS_PER_DAY=1
- DEFAULT_LLM_PROVIDER=mock
- DEFAULT_SEARCH_PROVIDER=mock
- OLLAMA_URL
- SEARXNG_URL

SÉCURITÉ

Toutes les routes doivent vérifier :
- user connecté
- accès projet
- rôle

Permissions minimales :
- owner/admin/editor/writer peuvent générer idée
- owner/admin/editor/writer peuvent lancer rédaction
- owner/admin/editor peuvent rejeter/prioriser
- viewer lecture seule

Règle critique :
Un utilisateur ne doit jamais accéder, modifier, générer ou rédiger pour un projet dont il n’est pas membre.

TESTS MINIMUM

Ajouter tests :
1. les tests Jour 1 passent encore
2. les tests Jour 2 passent encore
3. generate idea crée un article status idea_proposed
4. generate idea avec même keyword évite doublon
5. reject idea met status idea_rejected
6. priority met idea_priority
7. manual draft met draft_ready
8. start-writing génère content mock et status draft_ready
9. user non membre ne peut pas générer idée
10. viewer ne peut pas générer/modifier
11. generate_daily_ideas respecte IDEAS_PER_DAY
12. launch mode idea_only fonctionne
13. launch mode full_article crée idée puis draft

README

Mettre à jour README avec :
- endpoints Idea Engine
- endpoints Writing Engine
- mode mock IA
- variables .env ajoutées
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
2. modèles/tables ajoutés ou modifiés
3. migrations ajoutées
4. providers ajoutés
5. routes ajoutées
6. fonctionnement idea_only
7. fonctionnement full_article depuis idée
8. fonctionnement mock IA
9. tests effectués
10. confirmation que les tests Jour 1 passent encore
11. confirmation que les tests Jour 2 passent encore
12. bugs connus
13. ce qui reste pour Jour 4
14. commande exacte utilisée pour lancer les tests

Important :
Ne commence pas Jour 4.
Ne code pas les modules avancés de label.md.
Ne transforme pas Ideas Studio en usine nucléaire avant d’avoir fini la V1.
```
#### Support Day 3
```txt
Tu viens de terminer le Jour 3 du backend Ideas Studio.

Avant de passer au Jour 4, fais une vérification ciblée du Jour 3.

Lis d’abord :

prod.md
label.md

Puis inspecte le code actuel.

Objectif :
vérifier que toutes les abstractions demandées au Jour 3 ont bien été créées et intégrées correctement.

À vérifier précisément :

1. LLMProvider

Confirme si ces éléments existent :
- app/services/providers/llm_provider.py
- une interface ou classe de base LLMProvider
- MockLLMProvider
- get_llm_provider() ou équivalent
- méthodes prévues :
  - generate_text()
  - generate_json()
  - is_available()

Vérifie aussi si writing_engine utilise bien cette abstraction ou une abstraction équivalente.

Si ce n’est pas fait :
- ajoute uniquement l’abstraction minimale LLMProvider
- ajoute MockLLMProvider
- connecte writing_engine au provider si nécessaire
- ne crée pas Claude/OpenAI/Gemini aujourd’hui
- ne demande aucune clé API
- ne commence pas le Jour 4

2. SearchProvider

Confirme si ces éléments existent :
- app/services/providers/search_provider.py
- SearchProvider ou interface équivalente
- MockSearchProvider
- SearXNGSearchProvider si prévu
- get_search_provider() ou équivalent
- méthodes prévues :
  - search()
  - is_available()

Vérifie aussi si idea_engine utilise bien cette abstraction.

3. Idea Engine

Vérifie :
- generate_idea()
- création article status=idea_proposed
- déduplication par keyword actif dans le même projet
- outline_json
- serp_summary_json
- opportunity_score
- category_id optionnel
- count max raisonnable dans la route generate

4. Writing Engine

Vérifie :
- start_writing_from_idea()
- statuts compatibles :
  - idea_proposed
  - idea_priority
  - outline_ready
  - failed
- passage temporaire en writing_in_progress
- génération de content mock
- meta_title/meta_description si absents
- excerpt
- word_count
- status final draft_ready ou review_needed
- logs si article_logs existe

5. Routes Jour 3

Vérifie que les routes existent et fonctionnent :
- POST /projects/{project_id}/ideas/generate
- POST /articles/{article_id}/start-writing
- POST /articles/{article_id}/reject
- POST /articles/{article_id}/priority
- POST /articles/{article_id}/manual-draft
- POST /articles/{article_id}/rerun
- POST /projects/{project_id}/launch

6. Sécurité

Vérifie :
- user connecté obligatoire
- accès projet obligatoire
- user non membre bloqué
- viewer ne peut pas générer/modifier
- owner/admin/editor/writer autorisés selon les règles du Jour 3

7. Tests

Relance :

pytest tests/ -v

Vérifie que :
- les tests Jour 1 passent encore
- les tests Jour 2 passent encore
- les tests Jour 3 passent encore

RÈGLES IMPORTANTES

- Ne commence pas le Jour 4.
- Ne code pas le SEO Analyzer.
- Ne code pas les modules avancés de label.md.
- Ne fais pas de refonte générale.
- Si quelque chose manque, corrige seulement ce qui manque pour compléter le Jour 3.
- Si tout est déjà bon, ne modifie rien.

Rapport attendu :

1. LLMProvider : présent / manquant / corrigé
2. SearchProvider : présent / manquant / corrigé
3. Idea Engine : OK / problèmes trouvés
4. Writing Engine : OK / problèmes trouvés
5. Routes Jour 3 : OK / problèmes trouvés
6. Sécurité : OK / problèmes trouvés
7. Tests : résultat exact
8. Fichiers modifiés si correction
9. Verdict final :
   - Jour 3 complet : oui/non
   - Prêt pour Jour 4 : oui/non
```

---

# Rapport Day 3

```txt
Jour 3 terminé — 53/53 tests passent.

Fichiers créés :

search_provider.py — SearchResult, MockSearchProvider, SearXNGSearchProvider, get_search_provider()
log_service.py — log_step()
idea_engine.py — generate_idea() avec déduplication par keyword actif
writing_engine.py — start_writing_from_idea() avec outline + rédaction
scheduler.py — generate_daily_ideas() pour tous les projets actifs
schemas/ideas.py — tous les schémas Pydantic
routers/ideas.py — 7 routes (generate, start-writing, reject, priority, manual-draft, rerun, launch)
003_article_logs.py — migration article_logs

Rapport d'audit Jour 3

1. LLMProvider — présent, corrigé

Interface, MockLLMProvider, OllamaLLMProvider, get_llm_provider(), generate_text(), generate_json(), is_available() : tous présents
writing_engine utilise bien l'abstraction via llm.is_mock
2. SearchProvider — présent, correct

Interface, SearchResult, MockSearchProvider, SearXNGSearchProvider, get_search_provider(), search(), is_available() : tous présents
idea_engine utilise bien l'abstraction
3. Idea Engine — corrigé

status="idea" (inexistant dans ARTICLE_STATUSES) → "idea_proposed" ✓
Déduplication : ensemble des statuts actifs incomplet → corrigé (ajout idea_proposed, idea_priority, outline_ready, writing_requested) ✓
4. Writing Engine — corrigé

Statut intermédiaire writing_in_progress manquant → ajouté ✓
meta_title / meta_description non générés si absents → ajoutés ✓
excerpt non généré → ajouté ✓
Statut final "draft" → "draft_ready" ✓
5. Routes Jour 3 — corrigées

generate : "writer" manquant dans les rôles → ajouté ✓
start-writing : statuts vérifiés erronnés ("idea" au lieu de "idea_proposed"…) → corrigés ✓
reject : statut et rôle corrigés ✓
priority : PATCH → POST, status "idea_priority" maintenant effectivement appliqué ✓
manual-draft : route déplacée vers /articles/{id}/manual-draft, transforme une idée existante, status="draft_ready" ✓
rerun : statuts corrigés ✓
launch : mode idea_only / full_article ajouté ✓
6. Sécurité — corrigée

get_member_for_project retournait None silencieusement → remplacé par _check_role() qui lève systématiquement 403 ✓
Viewer bloqué sur toutes les routes de modification ✓
Non-membre bloqué sur /articles/{id}/* ✓
7. Tests — 61/61 passent

Jour 1 (16) : ✓
Jour 2 (20) : ✓
Jour 3 (25) : ✓ (8 tests ajoutés : deduplication, viewer bloqué, non-membre bloqué, idea_priority, draft_ready, launch modes, scheduler)
8. Fichiers modifiés

idea_engine.py
writing_engine.py
routers/ideas.py
schemas/ideas.py
tests/test_ideas.py
9. Verdict

Jour 3 complet : oui
Prêt pour Jour 4 : oui
```

---

# Prompt Backend Day 4

```txt
Tu travailles sur le projet Ideas Studio.

Avant de coder, lis entièrement :

prod.md
label.md

RÈGLE DE PRIORITÉ ENTRE LES DOCUMENTS

prod.md est la source de vérité principale pour ce qui doit être codé maintenant en V1.

label.md est une annexe stratégique IA/SEO long terme.
Il sert à comprendre la direction future du produit, mais il ne doit pas élargir le scope du jour en cours.

Si label.md propose un module avancé qui n’est pas explicitement demandé dans le Jour 4, ne l’implémente pas maintenant.

Utilise label.md seulement pour :
- garder une architecture extensible ;
- éviter des choix qui bloqueraient les futurs modules IA/SEO ;
- préparer des scores ou champs futurs seulement si cela ne complique pas la V1.

Ne crée pas aujourd’hui les modules avancés de label.md :
- Source Ledger complet
- Source Verification Engine complet
- Claim-to-Source Mapping
- Deep Rewrite Engine complet
- Natural Writing Engine complet
- Google Fit Score complet
- Originality Engine complet
- Safe Publish Gate complet
- ContentBrief complet
- Model Router avancé
- Prompt Versioning
- AI Jobs avancés
- Article Versioning
- Audit Trail avancé
- Webhooks
- Billing
- Quotas IA

AVANT DE MODIFIER

Commence par inspecter rapidement l’état actuel du projet :
- modèles articles/categories existants
- routes articles existantes
- routes ideas/writing existantes
- services existants
- migrations Alembic existantes
- tests existants

Ne réécris pas les Jours 1, 2 et 3.
Ne casse pas les routes déjà fonctionnelles.
Réutilise les helpers/services existants quand ils existent.
Si une fonction existe déjà, améliore-la au lieu de créer un doublon.

Avant de commencer le Jour 4, vérifie que les tests Jour 1, Jour 2 et Jour 3 passent encore.

RÈGLES GÉNÉRALES

- ne résume pas prod.md
- ne résume pas label.md
- ne pars pas dans une autre architecture
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
- providers mock simples

OBJECTIF JOUR 4

Créer :
- SEO Analyzer backend
- Readability Analyzer simple
- Quality Analyzer simple
- EEAT checks simples
- endpoint analyze article
- sauvegarde article depuis éditeur
- gestion meta/slug/cover/FAQ/callouts
- suggestions actionnables
- scores simples affichables

PRINCIPE

Le moteur d’analyse doit être détaillé en interne, mais simple dans l’affichage.

Il vérifie plusieurs critères, mais retourne des scores simples :
- SEO Score /100
- Readability Score /100
- Quality Score /100
- EEAT Score /100
- Publication Readiness

Attention :
label.md parle de Google Fit Score, Helpful Content Score, Trust Score, Safe Publish Gate, Source Verification, etc.
Ces modules sont importants pour la suite, mais ne doivent pas être codés complètement aujourd’hui.

Aujourd’hui, le Jour 4 doit rester sur le SEO Analyzer V1 prévu dans prod.md.

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
17. analyser EEAT simple
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

EEAT CHECKS SIMPLES

Vérifier :
- présence sources/citations si possible
- présence exemples concrets
- présence conseils actionnables
- absence d’affirmations trop vagues
- contenu crédible
- liens externes utiles si nécessaires

Important :
Ne crée pas encore Source Verification Engine complet.
Ne crée pas encore Claim-to-Source Mapping.
Ne bloque pas la publication avec Safe Publish Gate complet aujourd’hui.

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
1. les tests Jour 1 passent encore
2. les tests Jour 2 passent encore
3. les tests Jour 3 passent encore
4. analyze article retourne scores
5. article sans meta description crée warning
6. article trop court pénalise quality
7. article sans keyword dans title pénalise SEO
8. article avec phrases longues pénalise readability
9. critical bloque readiness
10. editor patch sauvegarde content
11. word_count recalculé
12. viewer ne peut pas modifier
13. user non membre ne peut pas analyser

README

Mettre à jour README :
- endpoints analyse
- exemple retour SEO
- logique scores
- limites de la V1
- mention que les modules avancés de label.md arriveront plus tard

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
2. tables/colonnes ajoutées
3. migrations ajoutées
4. checks SEO implémentés
5. scores implémentés
6. routes ajoutées
7. tests effectués
8. confirmation que les tests Jour 1, 2 et 3 passent encore
9. limitations connues
10. ce qui reste pour Jour 5
11. commande exacte utilisée pour lancer les tests

Important :
Ne commence pas Jour 5.
Ne code pas les modules avancés de label.md.
```

---

# Rapport Day 4

```txt
Jour 4 terminé — 77/77 tests passent. Voici ce qui a été livré :

Fichiers créés :

app/services/seo_analyzer.py — analyseur rule-based complet (SEO + Readability + Quality + EEAT), formule 100 - 20×critical - 10×warning - 3×info
app/routers/seo.py — 5 routes : /analyze, /analysis/latest, /analyses, /editor (PATCH), /ready-check
alembic/versions/004_seo_analyzer.py — migration table seo_analyses + 4 colonnes articles
tests/test_seo.py — 16 tests
Mise à jour : app/main.py et alembic/env.py pour inclure le nouveau routeur et le modèle.
```

---

# Prompt Backend Day 5

```txt
Tu travailles sur le projet Ideas Studio.

Avant de coder, lis entièrement :

prod.md
label.md

RÈGLE DE PRIORITÉ ENTRE LES DOCUMENTS

prod.md est la source de vérité principale pour ce qui doit être codé maintenant en V1.

label.md est une annexe stratégique IA/SEO long terme.
Il sert à comprendre la direction future du produit, mais il ne doit pas élargir le scope du jour en cours.

Si label.md propose un module avancé qui n’est pas explicitement demandé dans le Jour 5, ne l’implémente pas maintenant.

Utilise label.md seulement pour :
- garder une architecture extensible ;
- éviter des choix qui bloqueraient les futurs modules IA/SEO ;
- préparer proprement la suite sans complexifier la V1.

Ne crée pas aujourd’hui les modules avancés de label.md :
- Source Ledger complet
- Source Verification Engine complet
- Claim-to-Source Mapping
- Deep Rewrite Engine complet
- Natural Writing Engine complet
- Google Fit Score complet
- Originality Engine complet
- Safe Publish Gate complet
- ContentBrief complet
- Model Router avancé
- Prompt Versioning
- AI Jobs avancés
- Article Versioning
- Audit Trail avancé
- Webhooks avancés
- Billing
- Quotas IA
- Google Update Watcher
- Topical Authority Engine avancé

AVANT DE MODIFIER

Commence par inspecter rapidement l’état actuel du projet :
- modèles existants
- routers existants
- services existants
- providers existants
- migrations Alembic existantes
- tests existants
- README existant

Ne réécris pas les Jours 1, 2, 3 et 4.
Ne casse pas les routes déjà fonctionnelles.
Réutilise les helpers/services existants quand ils existent.
Si une fonction existe déjà, améliore-la au lieu de créer un doublon.

Avant de commencer le Jour 5, vérifie que les tests Jour 1, Jour 2, Jour 3 et Jour 4 passent encore.

RÈGLES GÉNÉRALES

- ne résume pas prod.md
- ne résume pas label.md
- ne pars pas dans une autre architecture
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
- Idea Engine/Writing Engine/providers mock

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

Important :
Ne pas créer aujourd’hui le système avancé complet décrit dans label.md.
Le Jour 5 crée seulement une première version simple des recommandations.

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

SCHEDULER SIMPLE

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
- aucune clé secrète exposée

SÉCURITÉ

Toutes les routes privées :
- user connecté
- membre du projet
- rôle correct si action

TESTS

Ajouter tests :
1. les tests Jour 1 passent encore
2. les tests Jour 2 passent encore
3. les tests Jour 3 passent encore
4. les tests Jour 4 passent encore
5. performance summary retourne data même vide
6. article performance retourne data
7. review_published_articles crée recommendation
8. pas de doublon recommendation
9. accept recommendation
10. reject recommendation
11. notifications list
12. mark notification read
13. daily task appelle generate_daily_ideas et review
14. API publique ne leak pas draft/scheduled non publié

DOCUMENTATION

Mettre à jour README :
- endpoints performance
- endpoints recommendations
- scheduler
- daily tasks
- workflow complet backend V1
- limites V1
- modules label.md prévus pour plus tard

AUDIT FINAL BACKEND RAPIDE

Faire un audit rapide :
- routes principales
- modèles
- permissions
- project_id partout
- absence de secrets frontend
- tests OK

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
5. performance summary fonctionnement
6. optimization engine fonctionnement
7. scheduler fonctionnement
8. notifications fonctionnement
9. tests effectués
10. confirmation que les tests Jour 1, 2, 3 et 4 passent encore
11. points faibles restants
12. backend V1 prêt ou non pour frontend
13. commande exacte utilisée pour lancer les tests

Important :
Ne code pas le frontend.
Ne commence pas billing.
Ne code pas les modules avancés de label.md.
```

---

# Rapport Day 5

```txt
Rapport final — Jour 5
1. Fichiers créés/modifiés
Créés :

app/models/optimization_recommendation.py
app/models/notification.py
app/services/notification_service.py
app/services/performance_service.py
app/services/optimization_engine.py
app/services/scheduler_service.py
app/schemas/performance.py, recommendation.py, notification.py
app/routers/performance.py, recommendations.py, notifications.py
alembic/versions/005_performance_optimization.py
app/cli.py
tests/test_day5.py
Modifiés : app/main.py, alembic/env.py, app/models/article.py (+ search_console_metrics_json), README.md

2. Modèles ajoutés
optimization_recommendations, notifications

3. Migrations ajoutées
005_performance_optimization.py — 2 tables + 1 colonne placeholder

4. Routes ajoutées (11)
Performance (3) · Recommendations (5) · Notifications (3)

5. Performance summary
Agrège les traffic_events par période configurable (30d, 7d, 90d). Retourne total_views, unique_pages, top_pages, referrers, countries, devices, trend_by_day. Résultat vide si aucun trafic — jamais d'erreur.

6. Optimization Engine
review_published_articles(project_id) parcourt les articles published avec published_at ≥ J+7, classe en J+7/J+30/J+90, crée des OptimizationRecommendation selon 5 règles V1. Anti-doublon : une recommandation pending du même type bloque la création. Crée une Notification par article avec nouvelles recommandations.

7. Scheduler
run_daily_project_tasks(project_id) enchaîne generate_daily_ideas + review_published_articles + notification de synthèse. run_all_projects_daily_tasks() boucle sur tous les projets actifs.

8. Notifications
Helper create_notification() utilisable depuis n'importe quel service. Routes : liste, mark-read, read-all. Non exposées sans auth.

9. Tests effectués
pytest tests/ -v — 97/97 passent

10. Confirmation tests Jours 1–4
Tous passent : Jour 1 (16), Jour 2 (20), Jour 3 (25), Jour 4 (16), Jour 5 (20) = 97 total

11. Points faibles restants
Pas de workers Redis/RQ — le scheduler doit être appelé via CLI ou cron externe
Performance basée sur les traffic_events locaux seulement (pas Search Console)
search_console_metrics_json préparé en DB mais non rempli (placeholder V2)
SQLite en dev : datetimes naive — corrigé via _as_utc() helper
12. Backend V1 prêt pour frontend ?
Oui. Toutes les APIs décrites dans prod.md sont opérationnelles. Architecture extensible pour les modules de label.md (LLM Gateway, Source Verification, Google Fit Score, etc.) sans refonte nécessaire.

13. Commande exacte des tests

source venv/bin/activate && python -m pytest tests/ -v
```

---

# PROMPT AUDIT FINAL BACKEND

```txt
Tu travailles sur le projet Ideas Studio.

Avant de répondre, lis entièrement :

prod.md
label.md

RÈGLE DE PRIORITÉ ENTRE LES DOCUMENTS

prod.md est la source de vérité principale pour vérifier la V1 backend.

label.md est une annexe stratégique IA/SEO long terme.
Il sert à vérifier que l’architecture ne bloque pas les évolutions futures, mais il ne doit pas être utilisé pour déclarer la V1 incomplète simplement parce que les modules avancés ne sont pas encore codés.

Important :
Ne critique pas l’absence des modules avancés de label.md comme un bug bloquant de la V1.
Tu peux les lister comme améliorations futures, dette stratégique ou roadmap V1.5/V2.

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
- architecture suffisamment extensible pour les futurs modules de label.md

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

13. Compatibilité future avec label.md
Vérifie seulement si l’architecture permet plus tard :
- LLMProvider plus avancé
- Source Verification Engine
- ContentBrief
- Google Fit Score
- Safe Publish Gate
- Model Router
- Prompt Versioning
- Article Versioning
- Webhooks

Mais ne demande pas de les coder maintenant.

SORTIE ATTENDUE

Donne un rapport structuré :

1. Ce qui est prêt
2. Ce qui est partiellement prêt
3. Ce qui manque réellement pour la V1
4. Bugs ou risques
5. Dette technique
6. Recommandations avant frontend
7. Liste des endpoints disponibles
8. Liste des modèles/tables
9. Compatibilité future avec label.md
10. Améliorations futures issues de label.md, non bloquantes pour la V1
11. Verdict final :
   - Backend V1 prêt pour frontend : oui/non
   - Si non, liste exacte des corrections bloquantes

Ne corrige rien sans que je te le demande.
Ne transforme pas les modules avancés de label.md en exigences bloquantes pour la V1.
```

### Rapport Audit Final Backend

```txt
Audit Backend V1 — Ideas Studio (Jours 1-5)
Généré le 2026-05-05 — 97/97 tests passent

1. Ce qui est prêt
Module	Statut	Détail
Auth JWT	✅ Prêt	Register, login, logout (token blacklist), GET /auth/me, bcrypt + python-jose, middleware token blacklist en mémoire
Projects	✅ Prêt	CRUD complet, public_tracking_key auto-généré, GET /connect avec masquage de la clé secrète, ProjectMember role-based
Categories	✅ Prêt	CRUD complet, rattaché à un projet, protection par membership
Articles (CMS)	✅ Prêt	CRUD + filtres (status, category, search, published_only, pagination), PATCH /editor, publish/unpublish/schedule, statuses complets
Tracking	✅ Prêt	traffic.js servi dynamiquement, POST /api/traffic/collect sans auth, collecte path/url/referrer/user_agent
Idea Engine	✅ Prêt	generate + launch (idea_only / full_article / dry_run), reject/priority/rerun, abstraction LLM/Search provider
Writing Engine	✅ Prêt	start-writing, manual-draft, pipeline outline→draft via LLM provider
SEO Analyzer	✅ Prêt	4 familles de règles (SEO / Readability / Quality / EEAT), formule scoring documentée, ready-check, SeoAnalysis historisé
Performance	✅ Prêt	Summary + articles list + article detail, filtre period=Nd, agrégation sur traffic_events
Recommendations	✅ Prêt	5 règles V1 (low_traffic, faq, meta_desc, seo_score, internal_links), anti-doublon pending, accept/reject/apply
Notifications	✅ Prêt	Création automatique via optimization engine, list, mark-read, read-all
Public API	✅ Prêt	Filtre strict status="published", aucun champ sensible exposé
CLI	✅ Prêt	daily, generate-ideas --project-id, review --project-id
Migrations	✅ Prêt	Chaîne 001→002→003→004→005 cohérente
2. Ce qui est partiellement prêt
Gestion des membres du projet

ProjectMember existe en base, le modèle/service est fonctionnel, le role-check est utilisé partout.
POST /projects/{id}/members est référencé dans le README mais n'existe pas en tant que route HTTP. Les tests qui en ont besoin contournent via insertion directe en DB (TestingSessionLocal).
Impact : bloquant pour le frontend — impossible d'inviter un collaborateur sans accès direct à la base.
Provider configuration

L'abstraction LLMProvider / SearchProvider est propre et fonctionne en mock.
Ollama est branché mais non testé de bout en bout (pas de test d'intégration avec un vrai serveur Ollama).
.env.example ne documente pas les variables ajoutées aux Jours 3-5 (IDEAS_PER_DAY, DEFAULT_LLM_PROVIDER, DEFAULT_SEARCH_PROVIDER, OLLAMA_URL, OLLAMA_MODEL, SEARXNG_URL). Le README les documente correctement — mais .env.example est la référence pour un nouveau développeur.
Token blacklist

Implémenté en mémoire (set()). Fonctionnel en dev/test, mais non persistant — redémarrer le serveur invalide tous les tokens blacklistés. Acceptable V1, problème V2+ prod.
3. Ce qui manque réellement pour la V1
Manque	Priorité	Impact
POST /projects/{id}/members	Critique	Le frontend ne peut pas gérer les équipes
.env.example incomplet	Élevée	Onboarding cassé pour un nouveau dev
DELETE /projects/{id}	Moyenne	Impossible de supprimer un projet via API
DELETE /projects/{id}/members/{user_id}	Moyenne	Impossible de retirer un membre
Pagination sur /notifications et /recommendations	Basse	OK pour V1, nécessaire dès >50 entrées
4. Bugs et risques
Bug 1 — POST /projects/{id}/members absent (critique)
Le README documente cette route, elle est attendue par le frontend, mais aucune route n'existe dans app/routers/projects.py. Les tests qui l'appellent ne vérifient pas le status code (ex. test_seo.py ligne ~160), ce qui masque le 404.

Bug 2 — Token blacklist non persistante
BLACKLISTED_TOKENS: set[str] dans app/core/security.py est une variable globale. En multi-worker (uvicorn --workers 4), chaque processus a sa propre copie — un token blacklisté sur le worker 1 reste valide sur le worker 2.

Risque 1 — CORS wildcard
allow_origins=["*"] dans main.py est correct en dev mais ne doit pas aller en production sans restriction.

Risque 2 — allow_credentials=True avec allow_origins=["*"]
La combinaison allow_credentials=True + allow_origins=["*"] viole la spec CORS (les navigateurs la rejettent). FastAPI/starlette lève une exception au démarrage si cette combinaison est détectée — vérifier que allow_credentials n'est pas activé simultanément.

Risque 3 — SQLite en production
DATABASE_URL defaulte à SQLite. Acceptable en dev, problème de concurrence en production (writes sérialisés, verrous). Documenter explicitement que PostgreSQL est requis pour la prod.

Risque 4 — Naive datetime SQLite
Le bug a été corrigé via _as_utc() dans optimization_engine.py, mais d'autres comparaisons de dates dans le projet (ex. tracking_service.py, performance_service.py) pourraient subir le même problème si elles comparent des datetimes issus de SQLite avec datetime.now(timezone.utc). À surveiller lors du passage PostgreSQL.

5. Dette technique
Item	Sévérité	Détail
Token blacklist en mémoire	Moyenne	Doit migrer vers Redis pour la prod multi-worker
_get_article_view_count charge tous les events en mémoire	Moyenne	db.query(...).all() puis filtre Python — OK avec <10k events, lent ensuite
Pas d'index sur traffic_events.path	Basse	Requêtes performance lentes à large volume
ideas.py router : _run_ideas dupliqué dans scheduler_service.py	Basse	La logique de génération d'idées est répliquée
Aucune limite sur content article	Basse	Un article très long peut saturer le LLM
SeoAnalysis non purgé	Basse	Accumulation infinie d'analyses — prévoir TTL ou limite max
6. Recommandations avant de démarrer le frontend
Bloquant (à faire avant J1 frontend) :

Implémenter POST /projects/{id}/members — sans ça, la gestion d'équipe est impossible via l'interface. Corps attendu : {"user_id": "...", "role": "editor|admin|viewer"}. Prévoir aussi DELETE /projects/{id}/members/{user_id} et GET /projects/{id}/members.

Compléter .env.example avec toutes les variables requises (copier depuis README).

Fortement conseillé :

Documenter la combinaison CORS — choisir entre allow_origins=["*"] (sans credentials) ou allow_origins=["http://localhost:3000"] (avec credentials si cookies JWT).

Ajouter GET /projects/{id}/members — le frontend en aura besoin pour afficher l'équipe.

Ajouter DELETE /projects/{id} — nécessaire pour les settings du projet.

Non bloquant mais utile :

Migrer vers PostgreSQL dès le premier test de charge.
Ajouter un index sur traffic_events(project_id, created_at) — les queries performance en bénéficieront immédiatement.
7. Liste des endpoints disponibles (37 routes)

Auth
  POST /auth/register
  POST /auth/login
  GET  /auth/me
  POST /auth/logout

Projects
  GET  /projects
  POST /projects
  GET  /projects/{id}
  PATCH /projects/{id}
  GET  /projects/{id}/connect
  POST /projects/{id}/members          ← NON IMPLÉMENTÉ (404)

Categories
  GET  /projects/{id}/categories
  POST /projects/{id}/categories
  GET  /categories/{id}
  PATCH /categories/{id}
  DELETE /categories/{id}

Articles
  GET  /projects/{id}/articles
  POST /projects/{id}/articles
  GET  /articles/{id}
  PATCH /articles/{id}
  POST /articles/{id}/publish
  POST /articles/{id}/schedule
  POST /articles/{id}/unpublish

Idea Engine
  POST /projects/{id}/ideas/generate
  POST /projects/{id}/launch
  POST /articles/{id}/start-writing
  POST /articles/{id}/reject
  POST /articles/{id}/priority
  POST /articles/{id}/manual-draft
  POST /articles/{id}/rerun

SEO Analyzer
  POST /articles/{id}/analyze
  GET  /articles/{id}/analysis/latest
  GET  /articles/{id}/analyses
  PATCH /articles/{id}/editor
  POST /articles/{id}/ready-check

Performance
  GET  /projects/{id}/performance/summary
  GET  /projects/{id}/performance/articles
  GET  /articles/{id}/performance

Recommendations
  GET  /projects/{id}/recommendations
  POST /projects/{id}/recommendations/review
  POST /recommendations/{id}/accept
  POST /recommendations/{id}/reject
  POST /recommendations/{id}/apply

Notifications
  GET  /projects/{id}/notifications
  POST /notifications/{id}/read
  POST /projects/{id}/notifications/read-all

Public API (sans auth)
  GET  /api/public/projects/{id}/articles
  GET  /api/public/projects/{id}/articles/{slug}

Tracking
  GET  /traffic.js
  POST /api/traffic/collect

Health
  GET  /health
8. Modèles / Tables
Table	Champs clés
users	id, email, hashed_password, name, role, created_at
projects	id, owner_id, name, domain, language, public_tracking_key, secret_api_key, status, created_at
project_members	id, project_id, user_id, role
categories	id, project_id, name, slug, description
articles	id, project_id, category_id, title, slug, content, status, keyword, seo_score, readability_score, quality_score, eeat_score, faq_json, internal_links_json, external_links_json, search_console_metrics_json, published_at, scheduled_at, …
seo_analyses	id, article_id, seo_score, readability_score, quality_score, eeat_score, readiness_status, issues_json, suggestions_json, created_at
traffic_events	id, project_id, url, path, referrer, user_agent, created_at
optimization_recommendations	id, project_id, article_id, type, priority, reason, suggestion, status, created_at, updated_at
notifications	id, project_id, user_id, type, title, message, level, read_at, created_at
9. Compatibilité future avec label.md
Le backend V1 est structuré de façon à absorber les modules label.md sans refactoring majeur :

Module label.md	Compatibilité	Note
LLM Gateway (LiteLLM)	✅ Directe	Remplace MockLLMProvider / OllamaProvider — l'interface LLMProvider est déjà abstraite
Deep Rewrite Engine	✅ Directe	Nouveau service, nouveaux champs sur articles
Source Ledger	✅ Directe	Nouvelle table sources, champ JSON sur articles
SearXNG	✅ Déjà partiellement branché	SearchProvider existe, SearXNGProvider implémenté
Originality Engine	✅ Directe	Nouveau service + nouveau score sur seo_analyses
Anti-Cannibalization	✅ Directe	Query sur articles par keyword — pas de changement de modèle
Internal Linking Engine	✅ Directe	Extension de optimization_engine.py
Article Versioning	⚠️ Requiert migration	Nouvelle table article_versions — modèle actuel sans historique
Search Console	⚠️ Requiert migration	search_console_metrics_json placeholder existe — à typer
Webhooks	⚠️ Requiert worker	Necessaire un système de queue (Redis/RQ)
Billing	❌ Hors scope V1	Architecture séparée requise
Google Update Watcher	❌ Hors scope V1	Service externe à intégrer
10. Améliorations futures (non bloquantes V1)
Issues de label.md, à planifier post-frontend :

Model Router : sélection automatique du LLM selon le contexte (idée vs rédaction vs SEO) — infrastructure déjà en place via LLMProvider
Google Fit Score : score de pertinence par rapport aux SERPs — requiert Search Console ou SearXNG
Safe Publish Gate : vérification automatique avant publication (min word count, min SEO score, meta présente) — peut s'appuyer sur ready-check existant
ContentBrief : génération de brief structuré avant la rédaction — extension de outline_json
Topical Authority Engine : analyse du cluster thématique du blog — requiert indexation complète des articles publiés
Author Profiles : table authors + champ author_id sur articles
11. Verdict final
Le backend V1 est fonctionnel et couvrant pour le frontend, avec une réserve critique.

✅ 97/97 tests passent. Toutes les routes prévues dans la roadmap Jours 1-5 sont implémentées, testées, et documentées. L'architecture est propre (SQLAlchemy 2.0, Pydantic v2, abstraction providers, role-based access control cohérent, Public API isolée).

⚠️ Un point bloquant avant de démarrer le frontend : POST /projects/{id}/members n'existe pas. C'est la seule fonctionnalité documentée dans le README qui retourne un 404. À implémenter en moins d'une heure — c'est une route CRUD standard qui suit exactement le pattern des autres routes du projet.

⚠️ Un point de fragilité opérationnel : .env.example est incomplet — un nouveau développeur ne peut pas configurer le projet correctement sans consulter le README en parallèle.

Une fois POST /projects/{id}/members implémenté et .env.example complété, le backend est prêt pour le frontend.
```

### Revue Audit Final Backend

```txt
Tu travailles sur Ideas Studio.

Avant de coder, lis :

prod.md
label.md

Objectif :
corriger uniquement les blocages identifiés dans l’audit final backend V1.

Ne commence pas le frontend.
Ne code pas de module avancé de label.md.
Ne fais pas de refonte générale.
Ne touche pas aux modules qui fonctionnent déjà sauf nécessité directe.

BLOCAGE 1 — Routes project members manquantes

L’audit a trouvé que ProjectMember existe déjà en base et que les permissions utilisent déjà les rôles, mais les routes HTTP de gestion d’équipe sont manquantes.

À implémenter :

GET /projects/{project_id}/members
- retourne la liste des membres du projet
- accessible seulement aux membres du projet
- doit inclure au minimum :
  - id
  - user_id
  - user name/email si relation disponible
  - role
  - status
  - created_at

POST /projects/{project_id}/members
- ajoute un membre au projet
- uniquement owner/admin
- body attendu :
  {
    "user_id": "...",
    "role": "admin|editor|writer|viewer"
  }
- interdit d’ajouter deux fois le même user au même projet
- interdit d’ajouter un membre avec role owner via cette route
- status par défaut = active
- retourne le membre créé

PATCH /projects/{project_id}/members/{user_id}
- modifie le rôle d’un membre
- uniquement owner/admin
- interdit de modifier le owner principal si cela casse le projet
- interdit de donner role owner via cette route
- retourne le membre modifié

DELETE /projects/{project_id}/members/{user_id}
- retire un membre du projet
- uniquement owner/admin
- interdit de supprimer le owner principal du projet
- retourne un message clair

Règles sécurité :
- user non membre du projet → 403
- viewer/writer/editor ne peuvent pas gérer les membres
- admin peut gérer les membres sauf owner principal
- owner peut gérer les membres
- ne jamais permettre à un projet de se retrouver sans owner

BLOCAGE 2 — .env.example incomplet

Complète .env.example avec toutes les variables utilisées par les jours 1 à 5.

Doit contenir au minimum :

APP_NAME=Ideas Studio
APP_ENV=development
APP_URL=http://localhost:8000
DATABASE_URL=sqlite:///./ideas_studio.db
SECRET_KEY=change-me
ACCESS_TOKEN_EXPIRE_MINUTES=1440

IDEAS_PER_DAY=1
DEFAULT_LLM_PROVIDER=mock
DEFAULT_SEARCH_PROVIDER=mock
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=
SEARXNG_URL=

Ajoute aussi toute autre variable réellement utilisée dans app/core/config.py.

TESTS À AJOUTER

Ajoute des tests pour :

1. GET /projects/{id}/members fonctionne pour owner
2. POST /projects/{id}/members ajoute un membre
3. POST empêche doublon project_id/user_id
4. POST interdit role owner
5. PATCH modifie le rôle d’un membre
6. DELETE retire un membre
7. DELETE interdit de retirer le owner principal
8. viewer ne peut pas gérer les membres
9. user non membre ne peut pas voir/gérer les membres
10. tous les anciens tests passent encore

DOCUMENTATION

Mets à jour README si nécessaire :
- routes members
- exemple body POST/PATCH
- permissions

COMMANDES

Relance :

python -m pytest tests/ -v
alembic upgrade head

RAPPORT FINAL ATTENDU

Donne :
1. fichiers modifiés
2. routes ajoutées
3. règles de sécurité appliquées
4. .env.example complété : oui/non
5. tests ajoutés
6. résultat exact des tests
7. backend V1 prêt frontend : oui/non

Important :
Corrige uniquement ces blocages.
Ne commence pas autre chose.
```

#### Rapport revue audit final 
```txt
Rapport final
1. Fichiers modifiés / créés
Fichier	Action
app/schemas/member.py	Créé — MemberAdd, MemberPatch, MemberPublic
app/routers/members.py	Créé — 4 routes members
app/main.py	Modifié — import + include_router(members.router)
.env.example	Modifié — toutes les variables ajoutées
tests/test_members.py	Créé — 10 tests
README.md	Modifié — section Members ajoutée
2. Routes ajoutées

GET    /projects/{id}/members
POST   /projects/{id}/members
PATCH  /projects/{id}/members/{user_id}
DELETE /projects/{id}/members/{user_id}
3. Règles de sécurité appliquées
Non-membre → 403 sur toutes les routes members
viewer/writer/editor → 403 sur POST/PATCH/DELETE
Rôle owner non assignable via API → 422 (validation Pydantic)
Doublon project_id/user_id → 409
Owner principal (= project.owner_id) non modifiable et non supprimable → 403
Admin peut gérer tous les membres sauf le owner principal
4. .env.example complété : oui
Toutes les variables de app/core/config.py sont présentes : APP_NAME, APP_ENV, APP_URL, DATABASE_URL, SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, IDEAS_PER_DAY, DEFAULT_LLM_PROVIDER, DEFAULT_SEARCH_PROVIDER, OLLAMA_URL, OLLAMA_MODEL, SEARXNG_URL.

5. Tests ajoutés : 10/10
list_members_owner · add_member_success · add_member_duplicate_blocked · add_member_role_owner_blocked · patch_member_role · delete_member_success · delete_owner_blocked · viewer_cannot_add_member · nonmember_cannot_list_members · nonmember_cannot_add_member

6. Résultat des tests

107 passed, 1 warning in 126.36s
7. Backend V1 prêt frontend : oui
Les deux blocages identifiés dans l'audit sont corrigés. Les 97 tests originaux passent toujours. 10 nouveaux tests couvrent entièrement la gestion d'équipe.
```

## SUITE BACKEND
## Stack et outils validés — règle générale

Avant d’installer une librairie ou de choisir un outil, vérifier cette section.

Les outils officiels de Ideas Studio V1 sont ceux listés ici.

Ne pas choisir :
- un autre éditeur WYSIWYG
- une autre stack backend
- un autre système de jobs
- un autre outil SEO externe payant
- un autre provider IA par défaut

sans validation explicite.

### Backend

- Python
- FastAPI
- SQLAlchemy ou SQLModel
- Alembic
- PostgreSQL en production
- SQLite seulement en développement local
- Pydantic
- python-dotenv
- passlib/bcrypt
- python-jose/JWT
- Uvicorn

### Jobs background

Outil prévu :

- Redis + RQ

Important :
Redis/RQ est prévu pour les jobs réels, mais ne doit pas être forcé dans les étapes où une version simple/synchrone suffit.

Jobs prévus :
- generate_idea
- write_article
- analyze_article
- publish_article
- review_performance
- generate_recommendations

### IA

Ideas Studio ne crée pas son propre LLM.

Le système utilise une abstraction :

- LLMProvider

Providers prévus :
- MockLLMProvider pour tests/dev
- OllamaLLMProvider pour local
- ClaudeProvider optionnel premium
- OpenAIProvider optionnel plus tard
- GeminiProvider optionnel plus tard

### Recherche web / SERP

Le système utilise une abstraction :

- SearchProvider

Providers prévus :
- MockSearchProvider pour tests/dev
- SearXNGSearchProvider pour recherche locale
- TavilySearchProvider optionnel plus tard

Extraction :
- trafilatura
- BeautifulSoup4
- lxml
- readability-lxml si nécessaire
- Playwright seulement si nécessaire

### Correction grammaticale

- LanguageTool local

Important :
LanguageTool sert à la correction grammaticale, orthographe, ponctuation et style léger.

LanguageTool ne doit pas être utilisé comme moteur de reformulation profonde.

### SEO Analyzer

Le SEO Analyzer est codé dans Ideas Studio.

Il ne doit pas dépendre d’un outil SEO payant externe.

Il analyse :
- keyword
- title
- H1/H2/H3
- meta title
- meta description
- slug
- densité
- liens internes
- liens externes
- images/alt
- lisibilité
- EEAT
- FAQ
- structure
- qualité
- readiness publication

### Tracking

Tracking maison :

- traffic.js
- /api/traffic/collect
- project_id
- public_tracking_key

Le script public ne doit jamais contenir secret_api_key.

### Frontend

Frontend recommandé :

- React + Vite pour le dashboard SaaS
- Next.js possible plus tard si besoin SSR/public blog

### Éditeur WYSIWYG officiel

Éditeur officiel :

- TipTap

TipTap sert uniquement côté frontend.

Le backend doit seulement fournir :
- Editor API
- autosave
- versions
- preview
- media manager
- content blocks
- SEO analysis endpoints
- publishing workflow

Ne pas utiliser :
- éditeur maison
- simple textarea comme éditeur final
- Quill comme éditeur principal
- awesome-wysiwyg-editors comme composant

Quill peut être mentionné comme ancien prototype, mais Ideas Studio V2 utilise TipTap.

### Graphiques frontend

Outil recommandé :

- Recharts

Utilisation :
- dashboard performance
- traffic summary
- articles performance
- recommendations stats

### Prompt Day 7 Backend
```txt
Tu travailles sur Ideas Studio.

Avant de coder, lis entièrement :

prod.md
label.md

Contexte :
Le backend V1 Jours 1 à 5 est terminé.
L’audit final a été corrigé.
Les routes members ont été ajoutées.
.env.example a été complété.
107 tests passent.

Objectif :
faire uniquement un Backend Day 6 — Editor Backend Hardening.

But :
compléter le backend nécessaire au vrai éditeur d’articles frontend TipTap, avant de commencer le frontend.

RÈGLE DE PRIORITÉ

prod.md = source principale de la V1.
label.md = annexe stratégique long terme.

Utilise label.md seulement pour ne pas bloquer l’évolution future, mais n’implémente pas ses modules avancés aujourd’hui.

Important :
- Ne commence pas le frontend.
- N’installe pas TipTap dans le backend.
- TipTap sera installé côté frontend plus tard.
- Ne refais pas les Jours 1 à 5.
- Ne casse pas les routes existantes.
- Ne code pas Redis/RQ complet aujourd’hui.
- Ne code pas Google Fit Score complet.
- Ne code pas Source Verification Engine.
- Ne code pas Deep Rewrite Engine.
- Ne code pas Originality Engine complet.
- Ne code pas Safe Publish Gate complet.
- Ne code pas billing.
- Ne fais pas de refonte générale.

TipTap est l’éditeur WYSIWYG officiel de Ideas Studio, mais il est frontend-only.
Le backend Day 6 doit seulement préparer les routes, modèles et données nécessaires pour que TipTap puisse fonctionner plus tard côté frontend.

AVANT DE MODIFIER

Inspecte rapidement :
- modèles articles existants
- routes articles / seo existantes
- routes publish/schedule/unpublish existantes
- services existants
- permissions existantes
- migrations Alembic existantes
- tests existants

Avant de commencer les modifications, vérifie que les tests existants passent encore.

À FAIRE

1. Editor Backend API

Ajouter :

GET /articles/{article_id}/editor

Cette route doit :
- charger toutes les données nécessaires à l’éditeur
- être protégée par auth
- vérifier project membership
- retourner au minimum :
  - id
  - project_id
  - category_id
  - title
  - slug
  - content
  - excerpt
  - status
  - keyword
  - meta_title
  - meta_description
  - cover_image_url
  - faq_json
  - callouts_json
  - internal_links_json
  - external_links_json
  - content_blocks_json si présent
  - word_count
  - seo_score
  - readability_score
  - quality_score
  - eeat_score
  - readiness_status
  - latest_analysis si simple à joindre
  - created_at
  - updated_at

Vérifier et compléter :

PATCH /articles/{article_id}/editor

Cette route existe déjà, mais elle doit maintenant accepter et sauvegarder :
- title
- slug
- content
- excerpt
- meta_title
- meta_description
- cover_image_url
- faq_json
- callouts_json
- internal_links_json
- external_links_json
- content_blocks_json
- category_id

Elle doit :
- recalculer word_count si content change
- mettre updated_at
- ne jamais publier automatiquement
- créer une version si le contenu ou les champs éditoriaux importants changent

Ajouter :

POST /articles/{article_id}/autosave

Cette route doit :
- sauvegarder sans publier
- accepter les mêmes champs principaux que PATCH /editor
- recalculer word_count si content change
- mettre updated_at
- ne pas changer le status vers published
- créer une version autosave si article_versions existe
- éviter les doublons inutiles si le contenu est identique à la dernière version autosave

Ajouter :

GET /articles/{article_id}/preview

Cette route doit :
- retourner une preview privée de l’article, même si l’article n’est pas publié
- nécessiter auth + project membership
- ne pas exposer les brouillons via l’API publique
- retourner au minimum :
  - title
  - slug
  - content
  - excerpt
  - meta_title
  - meta_description
  - cover_image_url
  - faq_json
  - callouts_json
  - internal_links_json
  - external_links_json
  - content_blocks_json
  - status

2. Version History

Créer une table article_versions :

Champs :
- id
- project_id
- article_id
- title
- slug
- content
- excerpt
- meta_title
- meta_description
- cover_image_url
- faq_json
- callouts_json
- internal_links_json
- external_links_json
- content_blocks_json
- version_number
- version_type
- created_by
- created_at

version_type possible :
- manual
- autosave
- restore

Créer routes :

GET /articles/{article_id}/versions

Cette route doit :
- lister les versions d’un article
- nécessiter auth
- vérifier project membership
- retourner les versions triées par version_number ou created_at DESC

POST /articles/{article_id}/versions/{version_id}/restore

Cette route doit :
- restaurer une ancienne version
- créer une nouvelle version de type restore ou sauvegarder l’état précédent avant restauration
- recalculer word_count
- mettre updated_at
- être autorisée pour owner/admin/editor
- être autorisée pour writer seulement si l’article n’est pas published
- être interdite à viewer
- être interdite au non-membre

3. Media Manager simple

Créer une table media_assets :

Champs :
- id
- project_id
- article_id nullable
- url
- filename
- mime_type
- size
- alt_text
- caption
- source
- created_at
- updated_at

Créer routes :

GET /projects/{project_id}/media

Cette route doit :
- lister les médias du projet
- nécessiter auth
- vérifier project membership
- accepter éventuellement un filtre article_id

POST /projects/{project_id}/media/upload

V1 simple :
- ne pas intégrer S3
- ne pas intégrer Cloudinary
- ne pas forcer un vrai stockage fichier
- stocker des médias URL-based

Body attendu :
- url
- filename
- mime_type
- size
- alt_text
- caption
- source
- article_id nullable

Règles :
- owner/admin/editor/writer autorisés
- viewer interdit
- si article_id est fourni, vérifier que l’article appartient au même projet

PATCH /media/{media_id}

Permettre de modifier :
- alt_text
- caption
- source
- article_id

Règles :
- owner/admin/editor/writer autorisés
- viewer interdit
- si article_id est fourni, vérifier même projet

DELETE /media/{media_id}

Règles :
- owner/admin/editor autorisés
- writer autorisé seulement si média lié à un article non published qu’il peut modifier
- viewer interdit
- non-membre interdit

4. Publishing Workflow complémentaire

Ajouter les statuts si absents :

- ready_to_publish
- unpublished
- archived

Ajouter routes :

POST /articles/{article_id}/mark-ready

Cette route doit :
- mettre status = ready_to_publish
- être autorisée pour owner/admin/editor
- être autorisée pour writer seulement si article non published
- ne doit pas publier l’article

POST /articles/{article_id}/archive

Cette route doit :
- mettre status = archived
- être autorisée seulement pour owner/admin/editor
- archived ne doit jamais être visible via l’API publique

Vérifier :
- status published visible dans Public API
- scheduled non visible si pas encore publié
- draft / review_needed / correction_needed / ready_to_publish / unpublished / archived non visibles publiquement

5. Content Blocks

Ajouter à articles si absent :

- content_blocks_json

Vérifier que ces champs sont supportés dans :
- GET /editor
- PATCH /editor
- POST /autosave
- GET /preview
- article_versions
- restore version

Champs structurés :
- faq_json
- callouts_json
- internal_links_json
- external_links_json
- content_blocks_json

6. Sécurité

Toutes les routes ajoutées doivent vérifier :
- user connecté
- membre du projet
- rôle correct

Règles :
- viewer = lecture seule
- writer peut modifier brouillons / draft_ready / review_needed / correction_needed / ready_to_publish
- writer ne doit pas modifier un article published
- owner/admin/editor peuvent gérer le workflow complet
- non-membre = 403

Ne jamais exposer :
- secret_api_key
- brouillons dans l’API publique
- articles archived/unpublished dans l’API publique

7. Migrations

Créer une migration Alembic pour :
- article_versions
- media_assets
- content_blocks_json si absent
- nouveaux statuts si enum utilisé

Si les statuts sont stockés en string, mettre simplement à jour la constante ARTICLE_STATUSES.

8. Tests

Ajouter des tests pour :

Editor :
1. GET /articles/{id}/editor retourne les données complètes
2. PATCH /editor sauvegarde content_blocks_json
3. PATCH /editor crée une version si contenu changé
4. POST /autosave sauvegarde sans publier
5. viewer ne peut pas autosave
6. non-membre bloqué

Versions :
7. GET /versions liste les versions
8. restore version restaure le contenu
9. restore crée une version de type restore ou sauvegarde l’état précédent
10. restore interdit à viewer
11. restore interdit à non-membre

Preview :
12. GET /preview fonctionne pour brouillon avec auth
13. preview brouillon non accessible sans auth
14. preview brouillon non accessible à non-membre

Media :
15. créer media URL-based
16. lister media du projet
17. patch alt_text/caption
18. delete media
19. viewer ne peut pas créer media
20. non-membre bloqué

Publishing :
21. mark-ready met status ready_to_publish
22. archive met status archived
23. archived non visible dans Public API
24. unpublished non visible dans Public API

Regression :
25. tous les anciens tests passent encore

9. Documentation

Mettre à jour README avec :
- Editor Backend API
- Autosave
- Version History
- Preview
- Media Manager URL-based
- Publishing workflow
- limites V1

Mettre à jour .env.example seulement si une nouvelle variable est réellement ajoutée.

COMMANDES À EXÉCUTER

alembic upgrade head
python -m pytest tests/ -v

RAPPORT FINAL ATTENDU

Donne :
1. fichiers créés/modifiés
2. modèles/tables ajoutés
3. routes ajoutées
4. migrations ajoutées
5. fonctionnement Editor API
6. fonctionnement Autosave
7. fonctionnement Version History
8. fonctionnement Preview
9. fonctionnement Media Manager
10. workflow publication complété
11. tests ajoutés
12. résultat exact des tests
13. anciens tests toujours OK : oui/non
14. backend prêt pour frontend : oui/non

VERDICT ATTENDU

À la fin, dis clairement :

Backend V1 + Editor Backend prêt pour frontend : oui/non

Important :
Ne commence pas le frontend.
Ne code pas les modules avancés de label.md.
Ne transforme pas ce Day 6 en refonte générale.
Corrige uniquement ce qui est nécessaire pour que le frontend éditeur puisse être construit proprement.
```

#### Rapport Day 6

```txt
Rapport final Day 6
1. Fichiers créés / modifiés
Fichier	Action
app/models/article.py	Modifié — content_blocks_json, statuts ready_to_publish/unpublished/archived, WRITER_EDITABLE_STATUSES
app/models/article_version.py	Créé
app/models/media_asset.py	Créé
app/schemas/seo.py	Modifié — ArticleEditorUpdate étendu
app/schemas/editor.py	Créé
app/schemas/media.py	Créé
app/services/version_service.py	Créé
app/routers/editor.py	Créé
app/routers/versions.py	Créé
app/routers/media.py	Créé
app/routers/articles.py	Modifié — mark-ready, archive
app/routers/seo.py	Modifié — PATCH /editor crée versions + word_count
app/main.py	Modifié — 3 nouveaux routers
alembic/versions/006_editor_hardening.py	Créé
tests/test_day6.py	Créé — 24 tests
README.md	Modifié
2. Modèles / tables ajoutés
Table	Champs clés
article_versions	id, project_id, article_id, title, slug, content, excerpt, meta, cover, faq/callouts/links/blocks json, version_number, version_type (manual|autosave|restore), created_by, created_at
media_assets	id, project_id, article_id (nullable), url, filename, mime_type, size, alt_text, caption, source, created_at, updated_at
articles.content_blocks_json	Colonne Text nullable ajoutée
3. Routes ajoutées (12 nouvelles)

GET  /articles/{id}/editor
POST /articles/{id}/autosave
GET  /articles/{id}/preview
GET  /articles/{id}/versions
POST /articles/{id}/versions/{version_id}/restore
POST /articles/{id}/mark-ready
POST /articles/{id}/archive
GET  /projects/{id}/media
POST /projects/{id}/media/upload
PATCH /media/{id}
DELETE /media/{id}
PATCH /articles/{id}/editor étendu (4 champs + word_count + version)
4. Migration ajoutée
006_editor_hardening.py → tables article_versions + media_assets + colonne content_blocks_json

5–10. Fonctionnement
Editor API : GET /editor retourne toutes les données + dernière analyse SEO comme latest_analysis
Autosave : POST /autosave sauvegarde sans jamais changer status → published, déduplique si contenu identique au dernier autosave
Version History : PATCH /editor et autosave créent des snapshots ; restore applique la version choisie après avoir sauvegardé l'état courant
Preview : accès privé au contenu brouillon (auth + membre requis, API publique non affectée)
Media Manager : URL-based (pas de stockage fichier), lié optionnellement à un article du même projet
Publishing : mark-ready → ready_to_publish ; archive → archived (invisible API publique) ; les 3 nouveaux statuts valides dans ARTICLE_STATUSES
11–13. Tests
Tests ajoutés : 24 (test_day6.py)
Résultat : 131/131 passed
Anciens tests : 107/107 toujours OK ✓
Verdict final
Backend V1 + Editor Backend prêt pour frontend : OUI
```



