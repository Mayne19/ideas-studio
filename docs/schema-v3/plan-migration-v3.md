# Plan de migration v3.2 (révisé) — Ideas Studio

Aligné sur `CLAUDE.md`. Chaque section renvoie aux dossiers, commandes et checklists décrits dans la référence technique du projet.

Cette version corrige le plan initial après vérification directe contre `app/models/*.py`, `app/services/*.py`, `app/routers/*.py` et un export de la base de dev (`md-datas/ideas_studio.db`). Le détail changement-par-changement est dans `CHANGELOG.md` ; ce document se concentre sur le plan à jour.

**Deux horloges différentes, à ne pas confondre.** La bascule technique de la base (créer le schéma v3, copier la poignée de lignes réelles) tient en quelques minutes — c'est confirmé maintenant que le volume réel est connu (peu d'utilisateurs, peu de projets, données de test exclues d'office). Ce qui ne se compresse PAS avec un petit volume, c'est le refactor du code applicatif (§2) : son coût est proportionnel à l'ampleur de la refonte du schéma (48 colonnes `*_json` à répartir, RLS à brancher partout, registre d'agents à synchroniser...), pas au nombre de lignes à migrer. Les deux sections suivantes reflètent cette distinction.

**Dev = SQLite, prod = PostgreSQL réel, confirmé.** `.env` local pointe vers `sqlite:///./md-datas/ideas_studio.db` ; la prod tourne sur PostgreSQL (Render) — `psycopg2-binary` en dépendance, plusieurs correctifs historiques dédiés à Render+PostgreSQL dans `LESSONS_LEARNED.md` (LL-001) et `KNOWN_ISSUES.md` (KI-RES-001). Le schéma v3 (schémas nommés, `jsonb`, RLS, partitionnement) n'a de sens que sur PostgreSQL — le passage à un Postgres local (§3) reste un préalable non négociable, mais lui aussi rapide vu le volume.

## 1. Le modèle de statut

Deux niveaux, comme demandé, mais calé sur les vraies valeurs que le code produit aujourd'hui — pas sur un vocabulaire reconstruit de mémoire.

**Niveau 1 — le statut** (`ref.states`) : Active (0) / Inactive (1). Une seule table, partagée par toutes les entités.

**Niveau 2 — le motif de statut** (`ref.*_status_reasons`) : une table par entité, chaque motif rattaché à un statut. **Le contenu n'est pas le même partout** — un projet n'a que 3 motifs réels, un article en a 21. Forcer un vocabulaire unique aurait été un choix arbitraire ; le code, lui, a déjà tranché.

### Articles — 21 motifs, repris 1:1 de `ARTICLE_STATUSES` (`app/models/article.py:7-30`)

| `status_reason_id` | `code` | `label` | Remarque |
|---|---|---|---|
| 10 | draft | Draft | défaut |
| 20 | idea_proposed | Idea proposed | |
| 30 | idea_priority | Idea prioritized | |
| 40 | outline_ready | Outline ready | |
| 50 | writing_requested | Writing requested | |
| 60 | writing_in_progress | Writing in progress | |
| 70 | draft_ready | Draft ready | éditable par un designer |
| 80 | review_needed | Review needed | éditable par un designer |
| 90 | correction_needed | Correction needed | éditable par un designer |
| 100 | ready_to_publish | Ready to publish | éditable par un designer |
| 110 | scheduled | Scheduled | **ne requiert pas** de révision publiée |
| 120 | published | Published | requiert une révision publiée |
| 130 | unpublished | Unpublished | requiert une révision publiée (déjà publiée avant) |
| 140 | update_recommended | Update recommended | masqué du kanban — page Recommandations |
| 150 | improvement_proposed | Improvement proposed | masqué du kanban |
| 160 | improvement_in_progress | Improvement in progress | masqué du kanban |
| 170 | improvement_ready | Improvement ready | masqué du kanban |
| 180 | failed | Failed | |
| 190 | blocked_cost_limit | Blocked (cost limit) | |
| 200 | idea_rejected | Idea rejected | état Inactive |
| 210 | archived | Archived | état Inactive |

**Pourquoi ne pas consolider à 10 motifs comme dans la v3 initiale ?** Le code teste des valeurs exactes à plusieurs endroits (`app/routers/ideas.py:279,474,635`, `app/routers/articles.py:151,257,278,363,385`, `app/services/production_queue.py:103,165,195,210,261,382,394,405`). Fusionner `writing_requested`/`writing_in_progress` ou `draft_ready`/`review_needed` aurait cassé ces vérifications sans toucher une ligne du code applicatif — un aller simple vers un bug de production. La consolidation est possible, mais c'est un chantier de refactor applicatif à part entière (Phase 2 ci-dessous), pas quelque chose qu'une migration de schéma peut décider seule.

**`requires_revision` corrigé.** Uniquement `published` et `unpublished`. La v3 initiale l'exigeait aussi pour `scheduled`, ce qui aurait cassé `schedule_article_with_validation` (`app/services/article_service.py:188-210`), qui ne peuple jamais `published_content` avant la publication réelle — seul `publish_article` (lignes 167-172) le fait.

**Deux axes, pas un seul.** Le code actuel a déjà deux dimensions de statut sur un article : `Article.status` (étape éditoriale, ci-dessus) et `Article.workflow_status` (phase du pipeline IA : `idea_prebrief` → `planning` → `production` → `quality` → `completed`, vu dans `app/services/idea_engine.py:461`, `app/routers/ideas.py:461,506`, `app/services/production_queue.py:93,102,266`). La v3 initiale ne capturait que le premier axe. Le second vit maintenant dans `ai.workflow_runs.phase_id` (`ref.workflow_phases`), séparé de `ai.workflow_runs.status_reason_id` (l'*issue* de l'exécution : queued/running/succeeded/failed/cancelled — `ref.run_status_reasons`).

### Projets — 3 motifs réels, pas 5 inventés

Le vrai `Project.status` ne connaît que **deux** valeurs observées en code et en base : `not_connected` (défaut) et `connected` (bascule automatique au premier événement `/tracking/*`, `tracking_service.py:40-41`). Confirmé sur la base de dev : 8 `not_connected`, 1 `connected`, rien d'autre. Il n'existe ni `running`, ni `paused`, ni `suspended` dans le code.

| `status_reason_id` | `code` | `label` |
|---|---|---|
| 10 | not_connected | Not connected |
| 20 | connected | Connected |
| 30 | archived | Archived *(état cible, pas encore atteignable — voir §6 de la note de conception d'origine sur l'archivage explicite)* |

### Rôles — les 5 vrais rôles

`PROJECT_ROLES = ("owner", "admin", "editor", "designer", "viewer")` (`app/models/project_member.py:23`). La v3 initiale avait un rôle `writer` qui n'existe nulle part et **oubliait `designer`**, qui conditionne pourtant une vraie permission (`DESIGNER_EDITABLE_STATUSES`, `article.py:33-35` ; `_MANAGE_ROLES = ("owner","admin","editor")`, `kanban_columns.py:12`).

| `role_id` | `code` | `rank` |
|---|---|---|
| 10 | viewer | 10 |
| 20 | designer | 20 |
| 30 | editor | 30 |
| 40 | admin | 40 |
| 50 | owner | 50 |

`role_id >= 30` reproduit exactement `_MANAGE_ROLES`. `role_id >= 20` couvre "peut éditer un article en attente de design".

### Français vs anglais

Tous les `code` et tous les `label` de `ref.*` sont en anglais — y compris les `label`, qui étaient en français dans la v3 initiale (incohérent avec des `code` déjà en anglais). Le français que voient les éditeurs reste géré côté frontend : créer `frontend/src/lib/status.ts` avec une table de traduction `code → libellé FR`, alimentée une fois depuis ce tableau. Une seule source de vérité (l'anglais, en base), une seule couche de traduction (le frontend) — pas de texte français dupliqué dans des migrations SQL qui deviendraient vite désynchronisées de l'UI.

Cohérence garantie par la base, pas par le code :

```sql
FOREIGN KEY (status_reason_id, state_id)
  REFERENCES ref.article_status_reasons(id, state_id)
```

Un article Active avec le motif "archived" est rejeté par PostgreSQL. Impossible de produire l'incohérence, même par une écriture directe en SQL.

Requêtes à deux niveaux :

```sql
-- Tout ce qui est encore en circulation
SELECT * FROM content.articles WHERE project_id = $1 AND state_id = 0;

-- Uniquement les publiés
SELECT * FROM content.articles WHERE project_id = $1 AND status_reason_id = 120;

-- Le pipeline d'idées (page /projects/:id/ideas)
SELECT * FROM content.articles WHERE project_id = $1 AND status_reason_id IN (10, 20, 30);
```

Les motifs sont espacés de 10, ce qui laisse la place d'en insérer sans rien réordonner.

Même schéma appliqué à `core.projects`, `core.project_members`, `ai.pipeline_runs`, `ai.workflow_runs`, `ai.workflow_steps` et `analytics.optimization_recommendations`.

## 2. Ce que la refonte implique dans l'arborescence

### `app/models/` — 25+ modèles

Le nombre de modèles augmente (~35), mais chacun devient court. Les gros chantiers :

- `article.py` : ~180 lignes aujourd'hui, une trentaine demain. Le contenu part dans `ArticleRevision`, les ~48 colonnes `*_json` dans `AiArtifact`, les scores dans `ArticleScore`, l'état de workflow dans `WorkflowRun`/`WorkflowStep`. `sub_niche` et `rejection_reason` sont repris dans `content.articles` (absents du brouillon v3 initial alors que réellement utilisés).
- `project.py` : la charte éditoriale part dans `EditorialProfile`, les URL de publication dans `PublishingTarget`, les clés dans `ProjectCredential`.
- Nouveaux : `Organization`, `OrganizationMember`, `EditorialProfile`, `PublishingTarget`, `ProjectCredential`, `ArticleRevision`, `ArticleSeo`, `Keyword`, `ArticleKeyword`, `ArticleLink`, `ArticleMedia`, `ArticleScore`, `Agent`, `AgentBinding`, `WorkflowRun`, `WorkflowStep`, `WorkflowPhase`, `AiArtifact`, plus les modèles de référence en lecture seule.
- `Idea` disparaît en tant que modèle distinct.

Les tables `ref.*` se déclarent en lecture seule côté SQLAlchemy, avec des `IntEnum` Python miroir :

```python
class State(IntEnum):
    ACTIVE = 0
    INACTIVE = 1

class ArticleStatus(IntEnum):
    DRAFT = 10; IDEA_PROPOSED = 20; IDEA_PRIORITY = 30; OUTLINE_READY = 40
    WRITING_REQUESTED = 50; WRITING_IN_PROGRESS = 60; DRAFT_READY = 70
    REVIEW_NEEDED = 80; CORRECTION_NEEDED = 90; READY_TO_PUBLISH = 100
    SCHEDULED = 110; PUBLISHED = 120; UNPUBLISHED = 130
    UPDATE_RECOMMENDED = 140; IMPROVEMENT_PROPOSED = 150
    IMPROVEMENT_IN_PROGRESS = 160; IMPROVEMENT_READY = 170
    FAILED = 180; BLOCKED_COST_LIMIT = 190
    IDEA_REJECTED = 200; ARCHIVED = 210
```

Un test dédié compare ces énumérations au contenu des tables `ref.*` et échoue si les deux divergent. C'est la seule discipline à tenir dans la durée.

### `app/services/agents/` — le registre reste en Python, la base le reflète

`app/services/agents/agent_registry.py` définit aujourd'hui **62 agents** (`AgentDef`, avec `category`, `phase`, `status`, `output_json_field`). C'est la vraie source de vérité du pipeline — `agent_assignments` ne contient que les *dérogations* de provider par projet, pas le catalogue complet (dans la base de dev, `agent_assignments` est vide : 0 ligne).

La migration ne doit donc **pas** essayer de reconstruire `ai.agents` à partir de `agent_assignments` (c'était le bug du script initial : `ai.agents` se serait retrouvé avec seulement les agents ayant une dérogation, pas les 62). À la place :

1. Le script SQL fait une insertion défensive (clé + libellé générique) juste pour ne pas bloquer la FK d'`ai.agent_bindings`.
2. Juste après la migration, un script applicatif (`app/scripts/sync_agent_catalog.py`, à créer) upserte `ai.agents` depuis `AGENTS` (le registre Python) — `category`, `phase`, `status`, `output_json_field` y compris. Idempotent, à relancer à chaque déploiement (le registre Python change plus souvent que le schéma).
3. Le routeur d'agents lit `ai.agent_bindings` avec la règle de surcharge "ligne projet sinon ligne globale".

`output_json_field` est le lien direct avec l'étape suivante : chaque agent qui écrivait dans une colonne `articles.<x>_json` le documente ici, ce qui rend le backfill vers `ai.artifacts` mécanique plutôt qu'à deviner colonne par colonne.

### `app/core/` — configuration et base

- `db.py` : ajouter un événement SQLAlchemy `after_begin` qui exécute `SET LOCAL app.project_id`. Sans lui, la RLS renvoie zéro ligne partout — comportement correct mais déroutant au premier essai.
- `config.py` : `DATABASE_URL` ne peut plus tomber sur SQLite. Ajouter une validation Pydantic qui refuse un DSN non-PostgreSQL.
- `security.py` : bcrypt reste pour les mots de passe utilisateur. Les clés de projet passent en SHA-256 — voir ci-dessous.

### `app/services/`

- `tracking_service.py:18,40-41` est le point le plus sensible. La comparaison en clair `project.public_tracking_key != data.tracking_key` devient une recherche indexée sur `digest(clé,'sha256')`. La transition `not_connected → connected` (ligne 40-41) doit maintenant écrire `status_reason_id = 20` au lieu de la chaîne `"connected"`.
- `services/seo/` (20+ services) : chaque service qui écrivait dans une colonne `*_json` de l'article écrit maintenant une ligne dans `ai.artifacts`, via `agent_key = <output_json_field mappé au agent_id correspondant dans le registre>`. Un helper `save_artifact(article_id, agent_key, payload)` couvre l'essentiel des cas.
- `services/agents/` : voir plus haut — le registre reste en Python, synchronisé, pas dupliqué en SQL.
- `services/article_service.py` : `publish_article` doit désormais poser `status_reason_id = 120` et écrire `published_revision_id` ; `schedule_article_with_validation` pose `status_reason_id = 110` **sans toucher** `published_revision_id` (cohérent avec le trigger `enforce_publication_rules`) ; `unpublish_article` pose `status_reason_id = 130`.

### `app/routers/` — 31 routers

Les routes ne changent pas. Ce qui change : les schémas Pydantic exposent désormais `state_id`, `state_label`, `status_reason_id`, `status_label` au lieu d'un `status` texte. Prévoir une période où l'ancien champ `status` reste présent en lecture seule, alimenté depuis `status_label` (en anglais désormais — le frontend traduit), le temps que le frontend suive.

Les permissions décrites dans `CLAUDE.md` (owner / editor / viewer, à compléter avec admin / designer réellement présents dans le code) passent par `role_id`. Le champ `rank` permet d'écrire `role_id >= 30` pour `_MANAGE_ROLES` au lieu d'une liste en dur.

### `frontend/src/`

- `api/` (22 modules) : les types TypeScript reflètent les deux niveaux. Créer `frontend/src/lib/status.ts` avec les constantes miroir des `IntEnum` Python **et** la table de traduction anglais → français utilisée pour l'affichage (voir §1).
- `pages/` : `/kanban` lit `v_board_columns` (colonnes de statut **et** colonnes libres `custom_key`) au lieu de `kanban_columns`. `/ideas` filtre sur `status_reason_id IN (10, 20, 30)`. `/validation` et `/archives` filtrent sur `state_id`. `/recommendations` filtre sur `status_reason_id IN (140, 150, 160, 170)`.
- `components/editor/` : le panneau Versions se branche sur `article_revisions`, l'autosave crée ou met à jour la révision courante au lieu d'écrire dans `articles.content`.

### `alembic/` — 30 révisions

Toutes les tables étant recréées, l'historique n'a plus d'objet. Archiver `alembic/versions/`, générer une révision unique de baseline, et faire `alembic stamp head` après la bascule.

**Point d'attention** : `app/main.py` exécute `upgrade head` au démarrage. Pendant la bascule, le service doit être arrêté ou en `APP_ENV=maintenance`, sinon un redémarrage Render relancerait des migrations sur un schéma qui n'existe plus.

### `tests/` — 131+ tests

Le poste de travail le plus lourd après les modèles. Le `conftest.py` bascule sur PostgreSQL — soit `testcontainers-python`, soit une base `seo_test` du Docker Compose local, recréée entre les sessions. Ajouts nécessaires :

- une fixture qui pose `app.project_id` pour les tests qui touchent des tables sous RLS ;
- un test qui vérifie que la RLS bloque effectivement un accès inter-projets — ne peut pas exister en SQLite ;
- un test qui compare les `IntEnum` Python aux tables `ref.*` (voir §2, ci-dessus) ;
- un test qui vérifie que `schedule_article_with_validation` fonctionne toujours sans révision publiée (garde-fou direct contre la régression identifiée dans cette révision).

### `.claude/settings.json`

Le serveur MCP `sqlite` n'a plus d'objet. Le remplacer par un serveur MCP PostgreSQL pointant sur la base de développement.

### Documentation

`CLAUDE.md` : mettre à jour la ligne "Base : SQLite (dev) / PostgreSQL (prod)", le tableau des modèles, et la section Configuration environnement. `DECISIONS.md` : consigner les décisions structurantes — RLS plutôt que schéma par tenant, modèle statut/motif à deux niveaux calé sur le vocabulaire réel du code, SHA-256 pour les clés de projet, catalogue d'agents synchronisé depuis le Python plutôt que dupliqué en SQL. `LESSONS_LEARNED.md` : noter le piège de la RLS contournée par le propriétaire des tables, et celui de la table de correspondance de statuts qui perdait des lignes en silence (`INNER JOIN` sur un vocabulaire non vérifié contre les données réelles).

## 3. Développement local sur PostgreSQL

Préalable à tout le reste : sans lui, ni la RLS, ni le partitionnement, ni la migration elle-même ne sont testables avant la production.

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ideas
      POSTGRES_PASSWORD: ideas
      POSTGRES_DB: ideas_studio_dev
    ports: ["5433:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ideas"]
      interval: 5s
volumes:
  pgdata:
```

`.env` :

```
DATABASE_URL=postgresql+psycopg://ideas:ideas@localhost:5433/ideas_studio_dev
```

`scripts/dev.sh` démarre le conteneur et attend le healthcheck avant de lancer uvicorn. `npm run dev` reste la commande unique décrite dans `CLAUDE.md`.

Trois pièges à connaître dès le premier essai :

- **La RLS ne s'applique pas au propriétaire des tables.** Si l'application se connecte avec le rôle qui a créé le schéma, les politiques sont contournées en silence — vous croiriez qu'elles marchent alors qu'elles ne protègent rien. D'où `FORCE ROW LEVEL SECURITY` et le rôle `app_user` dans le DDL. En local comme en production, l'application se connecte avec `app_user`.
- **APScheduler tourne hors requête HTTP.** Les tâches du planificateur doivent poser `app.project_id` explicitement au début de chaque job, sinon la pipeline ne verra aucun article.
- **Le registre d'agents (Python) et `ai.agents` (base) peuvent diverger.** Faire tourner `sync_agent_catalog` à chaque déploiement, pas seulement à la migration — sinon un agent ajouté dans `agent_registry.py` reste invisible côté base tant que le script n'a pas re-tourné.

## 4. Déroulé de la bascule

Deux moments bien séparés : la **préparation** (refactor applicatif, non compressible, à faire calmement en amont) et **la fenêtre de bascule elle-même** (base + redémarrage), qui, elle, tient en une poignée de minutes vu le volume réel.

### Préparation (jours, avant la fenêtre de bascule — pas le jour J)

| Étape | Durée | Commande / action |
|---|---|---|
| P1 | 30 min | `docker compose up -d db`, `.env`, l'app démarre en local sur Postgres |
| P2 | jours | Refactoring applicatif (voir §2) — la seule étape non compressible |
| P3 | 5 min | Répétition à blanc de `migration-bigbang-v3.sql` sur une copie du dump de prod (le volume réel se relit intégralement à l'œil, `SELECT * FROM core.projects`, etc.) |

### Fenêtre de bascule (quelques minutes, une fois P1-P3 validés)

| Étape | Durée | Commande / action |
|---|---|---|
| 1 | 30 s | `pg_dump "$DATABASE_URL" -Fc -f backup_avant_refonte.dump` |
| 2 | 1 min | Passer Render en maintenance (sinon `main.py` relance les migrations) |
| 3 | 1 min | `psql "$DATABASE_URL" -f migration-bigbang-v3.sql` (schéma + copie des données réelles + contrôles intégrés) |
| 4 | 1 min | `./venv/bin/python -m app.scripts.sync_agent_catalog` (catalogue des 62 agents) |
| 5 | 2 min | Vérification manuelle rapide vu le volume : `SELECT slug, status_reason_id FROM core.projects;`, login, un kanban |
| 6 | 1 min | Clés des fournisseurs IA vers le coffre, `secret_ref` renseigné |
| 7 | 1 min | `alembic stamp head`, redémarrage en production (sortie de maintenance) |

Soit environ **7 à 8 minutes** pour la fenêtre de bascule proprement dite, une fois le code applicatif (P2) prêt et déployé. C'est ce dernier point qui fixe le calendrier réel du projet, pas le script SQL.

Les contrôles de cohérence sont intégrés au script sous forme de `RAISE EXCEPTION` : orphelins pré-migration sur les 3 tables historiquement sans FK, nombre d'utilisateurs, de projets, de profils éditoriaux actifs, de catégories, d'affectations d'agents, de pipelines, de colonnes kanban, et absence de projet sans propriétaire. Un seul écart annule toute la transaction. Vu le faible volume, ces contrôles peuvent aussi être doublés d'une relecture à l'œil avant de valider (le script le suggère juste avant le `COMMIT`).

Le retour arrière ne demande pas de restauration : tant que le schéma `legacy` existe, il suffit de le renommer en `public`.

## 5. Checklists

**Avant la bascule** (complète celle de `CLAUDE.md`) :

- [ ] `pytest tests/` vert sur PostgreSQL, pas sur SQLite
- [ ] Test d'isolation RLS présent et vert
- [ ] Test de cohérence `IntEnum` Python ↔ tables `ref.*` vert
- [ ] Test « programmer un article sans révision publiée fonctionne » vert (régression directement visée par cette révision)
- [ ] `npm run build` sans erreur TypeScript
- [ ] E2E Playwright sur les parcours article, kanban (colonnes standard + personnalisées), idées, génération, programmation
- [ ] Migration répétée sur une copie du dump de production, avec des colonnes kanban et des `ai_provider_configs`/`agent_assignments` réels (pas seulement la base de dev, qui n'en a aucun)
- [ ] `alembic upgrade head` testé sur base vierge
- [ ] `.env.example` à jour avec le nouveau `DATABASE_URL`
- [ ] Variables Render mises à jour, service en maintenance

**Après la bascule** :

- [ ] `SELECT count(*) FROM ai.agents` ≈ 62 (catalogue synchronisé, pas seulement les clés vues dans `agent_assignments`)
- [ ] `SELECT count(*) FROM ai.provider_credentials WHERE secret_ref LIKE 'TODO://%'` renvoie 0
- [ ] Un événement `/tracking/*` bascule bien un projet de `not_connected` à `connected`
- [ ] Une génération IA complète va jusqu'au bout et produit des lignes dans `ai.artifacts`
- [ ] Une programmation d'article (`scheduled`) fonctionne sans révision publiée existante
- [ ] Audit Lighthouse ≥ 80
- [ ] `CLAUDE.md`, `DECISIONS.md`, `LESSONS_LEARNED.md` mis à jour
- [ ] `DROP SCHEMA legacy CASCADE` après une à deux semaines de fonctionnement
