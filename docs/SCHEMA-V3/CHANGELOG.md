# Changelog — révision v3 → v3.2

Ce document liste tout ce qui a changé entre les trois artifacts d'origine (`REFONTE-SCHEMA-V3.sql`, `MIGRATION-BIGBANG-V3.sql`, `PLAN-MIGRATION-V3.md`) et cette révision, et pourquoi. Chaque point a été vérifié contre le code réel (`app/models`, `app/routers`, `app/services`) et contre un export de la base de dev (`md-datas/ideas_studio.db` : 15 users, 9 projects, 23 articles, 10 categories, 0 kanban_columns, 0 ai_provider_configs, 0 agent_assignments).

## v3.2 — cutover simplifié pour un petit volume réel

Confirmé : dev tourne sur SQLite (`.env` → `sqlite:///./md-datas/ideas_studio.db`), la prod sur PostgreSQL réel (Render — `psycopg2-binary`, `LESSONS_LEARNED.md` LL-001, `KNOWN_ISSUES.md` KI-RES-001). Le volume réel à migrer est faible et les articles/idées (données de test) sont exclus d'office.

**Ce qui a changé** : la table `migration.id_map` générique + la fonction `migration.map_id(entité, ancien_id)` — dimensionnées pour un volume qu'on n'a pas, avec repli sur `gen_random_uuid()` et cast défensif — sont remplacées par une petite table temporaire par entité (`user_id_map`, `org_id_map`, `project_id_map`, `category_id_map`). Même principe (correspondance ancien id → nouveau uuid cohérente d'une table à l'autre), mais chaque correspondance peut être relue intégralement à l'œil avant de valider, vu qu'il n'y a que quelques dizaines de lignes au total. Le script reste transactionnel, rejouable sur une copie pour répétition, et conserve tous les contrôles de cohérence (`RAISE EXCEPTION`) et le pré-vol sur les 3 tables sans FK — ce sont trois `SELECT`, ils ne coûtent rien en temps même sur un petit volume et restent une assurance utile.

**Ce qui n'a pas changé** : le schéma cible (`REFONTE-SCHEMA-V3.sql`) reste identique — RLS, partitionnement, catalogue d'agents synchronisé depuis le Python, etc. Le volume de données ne change rien à la complexité du schéma cible ni à l'ampleur du refactor applicatif (§2 du plan) : seule la *mécanique de copie des quelques lignes réelles* a été allégée.

**Précision apportée au plan** : la fenêtre de bascule (base + redémarrage) est désormais chiffrée séparément du refactor applicatif — environ 7-8 minutes une fois le code prêt, contre plusieurs jours pour le refactor lui-même. Ces deux durées ne dépendent pas des mêmes facteurs (l'une du volume de données, l'autre de l'ampleur de la refonte du schéma) et ne doivent pas être confondues dans la planification.

## Bugs qui auraient cassé une fonctionnalité existante

### 1. La programmation d'un article aurait été bloquée
`content.enforce_publication_rules` exigeait `published_revision_id` pour le motif `scheduled` en plus de `published`. Or `schedule_article_with_validation` ([article_service.py:188-210](../../app/services/article_service.py#L188-L210)) ne pose jamais `published_revision_id` — seul `publish_article` ([article_service.py:167-172](../../app/services/article_service.py#L167-L172)) le fait, au moment réel de la publication.
**Correctif** : `requires_revision` retiré du motif `scheduled` (désormais id 110), conservé uniquement sur `published` (120) et `unpublished` (130, nouveau — voir point 4).

### 2. Les colonnes kanban personnalisées auraient disparu silencieusement
Le script de migration joignait `kanban_columns.status` à une table de correspondance abrégée (`idea`, `writing`, `ready`...) via un `INNER JOIN`. Deux problèmes cumulés :
- une colonne kanban peut avoir un statut totalement libre, `custom_<label>` ([kanban_columns.py:50](../../app/routers/kanban_columns.py#L50)) — une fonctionnalité réelle, pas une valeur théorique ;
- même pour un vrai statut d'article, le vocabulaire de la table de correspondance ne matchait presque aucune des 21 valeurs réelles (`writing_in_progress`, `draft_ready`, `correction_needed`... contre `writing`, `ready`... dans la table).

Un `INNER JOIN` qui ne matche rien insère 0 ligne, sans erreur. Le bloc de contrôle final du script ne comparait d'ailleurs jamais le nombre de `kanban_columns` avant/après — la perte n'aurait été détectée par rien.

**Correctif** :
- `content.board_columns` accepte désormais une colonne réellement libre (`status_reason_id` nullable + `custom_key`, `CHECK` garantissant qu'exactement un des deux est renseigné).
- La migration fait un `LEFT JOIN` direct sur `ref.article_status_reasons.code` (qui porte maintenant les vraies valeurs) : tout ce qui matche devient une colonne standard, tout le reste devient une colonne `custom_key` — plus aucune ligne n'est perdue, quoi qu'il arrive.
- Ajout d'un contrôle `legacy.kanban_columns` vs `content.board_columns` dans le bloc de vérification.

### 3. Le catalogue d'agents se serait retrouvé quasiment vide
`ai.agents` était peuplé uniquement à partir de `legacy.agent_assignments` (`INSERT ... SELECT DISTINCT agent_id FROM legacy.agent_assignments`). Cette table ne contient que les *dérogations* de provider par projet — dans la base de dev elle est vide (0 ligne). Le vrai catalogue vit dans [agent_registry.py](../../app/services/agents/agent_registry.py) : **62 agents** définis en Python (`category`, `phase`, `status`, `output_json_field`).

**Correctif** : la migration ne fait plus qu'une insertion défensive pour ne pas bloquer la FK d'`ai.agent_bindings`. Le vrai peuplement vient d'une synchronisation applicative (`sync_agent_catalog`, décrite au plan §2) exécutée juste après la migration — le registre Python reste la source de vérité, la table est un cache interrogeable, pas une copie qu'on tient à jour à la main.

## Données réelles qui ne correspondaient pas au vocabulaire inventé

### 4. Statuts d'articles : 21 valeurs réelles, pas ~18 abrégées
`ARTICLE_STATUSES` ([article.py:7-30](../../app/models/article.py#L7-L30)) liste 21 valeurs, confirmées en base de dev (`draft`, `draft_ready`, `idea_priority`, `idea_proposed`, `published`, `review_needed`, `writing_in_progress` y sont effectivement présents). La table `ref.article_status_reasons` d'origine en inventait 10 avec des noms proches mais différents (`idea`, `validated`, `planned`, `writing`, `review`, `ready`...), et la table de correspondance de la migration (`migration.article_status_map`) en ajoutait encore d'autres (`new`, `approved`, `generating`, `in_progress`, `pending_review`...) sans qu'aucune ne soit vérifiée contre une vraie donnée.

Découverte annexe : `unpublished` (un article publié puis dépublié, [article_service.py:268](../../app/services/article_service.py#L268)) était absent des deux versions du design d'origine — un état pourtant réel et distinct de `draft`.

**Correctif** : les 21 codes réels repris tels quels comme `ref.article_status_reasons.code` (ils sont déjà en anglais dans le code Python — aucune traduction à faire). La table `migration.article_status_map` est supprimée : elle n'a plus d'objet, la correspondance kanban se fait directement sur ces codes (voir point 2).

### 5. Statuts de projet : 2 valeurs réelles, pas 5 inventées
`Project.status` ne prend que `not_connected` (défaut) et `connected` (bascule automatique dans [tracking_service.py:40-41](../../app/services/tracking_service.py#L40-L41)). Confirmé en base : 8 `not_connected`, 1 `connected`, aucune autre valeur. Il n'existe ni `active`, ni `running`, ni `paused`, ni `suspended` — le CASE de la migration mappait vers ces motifs sans qu'aucune donnée réelle ne puisse jamais les atteindre.

**Correctif** : `ref.project_status_reasons` réduit à `not_connected` (10), `connected` (20), `archived` (30 — état cible pour l'archivage explicite envisagé dans la note de conception d'origine §6, inatteignable tant que l'app ne l'implémente pas). CASE de migration simplifié en conséquence.

### 6. Rôles : 5 rôles réels, pas 4 avec un nom inventé
`PROJECT_ROLES = ("owner", "admin", "editor", "designer", "viewer")` ([project_member.py:23](../../app/models/project_member.py#L23)). Le design d'origine avait `viewer/writer/editor/admin/owner` — `writer` n'existe nulle part dans le code, et `designer` (qui conditionne une vraie permission, `DESIGNER_EDITABLE_STATUSES`, [article.py:33-35](../../app/models/article.py#L33-L35)) manquait entièrement.

**Correctif** : `ref.member_roles` corrigé à `viewer(10)/designer(20)/editor(30)/admin(40)/owner(50)`. Le rôle de repli pour une valeur legacy non reconnue passe de « un rôle à mi-échelle » à `viewer` (le moins privilégié) — un rôle mal reconnu doit échouer fermé, pas ouvert.

## Angle mort structurel comblé

### 7. Deux axes de statut sur un article, pas un seul
Le code actuel distingue déjà `Article.status` (étape éditoriale) de `Article.workflow_status` (phase du pipeline IA — valeurs réelles observées : `idea_prebrief`, `planning`, `production`, `quality`, `completed`, dans [idea_engine.py:461](../../app/services/idea_engine.py#L461), [ideas.py:461,506](../../app/routers/ideas.py#L461), [production_queue.py:93,102,266](../../app/services/production_queue.py#L93)). Le design d'origine ne capturait que le premier axe ; `ai.workflow_runs` n'avait qu'un `status_reason_id` (l'issue : queued/running/succeeded/failed/cancelled), pas de notion de phase.

**Correctif** : ajout de `ref.workflow_phases` (5 valeurs) et `ai.workflow_runs.phase_id`, qui coexiste avec `status_reason_id` — exactement comme le code actuel fait coexister ses deux champs.

## Cosmétique demandée mais réelle

### 8. Labels en anglais
Tous les `label` de `ref.*` étaient en français (`Brouillon`, `Idée`, `En rédaction`...) alors que les `code` correspondants étaient déjà en anglais — incohérent. Traduits en anglais. Le français vu par les éditeurs dans l'interface reste géré côté frontend (`frontend/src/lib/status.ts`, table de traduction anglais → français), pas stocké en base : une seule source de vérité, une seule couche de traduction.

## Durcissements ajoutés (pas des bugs, des filets de sécurité)

### 9. Contrôle pré-vol sur les 3 tables historiquement sans FK
`ai_provider_configs`, `agent_assignments` et `ai_usage_logs` n'ont jamais eu de contrainte de clé étrangère sur `project_id` (constat de la note de conception d'origine). Rien ne garantissait l'absence d'orphelins en production. La migration échouait auparavant *au milieu* d'une insertion (violation de FK), sans diagnostic. Un bloc de contrôle en tout début de transaction compte maintenant ces orphelins et arrête tout avec un message clair avant la moindre écriture.

### 10. Génération de slugs robuste aux collisions
`core.organizations.slug` et `core.projects.slug` sont dérivés du nom/email/username sans garantie d'unicité (deux comptes avec le même préfixe d'email, par exemple). Suffixe des 6 premiers caractères de l'ancien id ajouté systématiquement — élimine un risque de violation `UNIQUE` en plein milieu de la migration.

## Ce qui n'a délibérément pas changé

- **Les 21 statuts d'articles ne sont pas consolidés** en un vocabulaire plus court, même si certains (`writing_requested`/`writing_in_progress`, par exemple) pourraient sembler redondants avec l'axe `workflow_runs.phase_id`. Le code teste des valeurs exactes à plusieurs endroits (voir plan §1) ; les fusionner casserait ces vérifications sans toucher une ligne d'code applicatif. C'est un refactor à part entière, hors du périmètre d'une migration de schéma — documenté comme piste dans le plan, pas fait ici.
- **`ai.agents` n'est pas rempli en dur avec les 62 lignes du registre.** Recopier le registre Python dans une migration SQL aurait recréé exactement le problème que toute la refonte cherche à éliminer pour les colonnes `*_json` : deux endroits qui peuvent diverger. La base reste un cache synchronisé, le code reste la source de vérité.
