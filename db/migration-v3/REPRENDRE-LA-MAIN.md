# Reprendre la main

## 1. L'erreur de déploiement — à lire en premier

```
duplicate key value violates unique constraint "pg_type_typname_nsp_index"
DETAIL: Key (typname, typnamespace)=(alembic_version, 20863) already exists.
```

Alembic essaie de créer `alembic_version`, ne la trouve pas là où il regarde, mais la création échoue parce qu'elle existe déjà dans le schéma d'OID 20863.

**Détail important** : `ALTER SCHEMA public RENAME TO legacy` ne change que le nom, l'OID reste le même. L'ancien `public` — celui qui contient toutes vos anciennes tables, dont `alembic_version` — est donc probablement ce 20863. Vérifiez :

```sql
SELECT oid, nspname FROM pg_namespace WHERE oid = 20863;

SELECT n.nspname AS schema, c.relname AS objet, c.relkind
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relname = 'alembic_version';

SHOW search_path;
```

Si le premier résultat renvoie `legacy`, cela veut dire que la connexion de votre application résout `legacy` dans son `search_path`. C'est le point à corriger : sinon vos requêtes vont taper au hasard entre l'ancien et le nouveau schéma.

## 2. Le danger immédiat : Alembic

`app/main.py` exécute `upgrade head` au démarrage. Vos 30 migrations décrivent l'**ancien** schéma. Si elles s'exécutent maintenant, elles vont recréer `users`, `projects`, `articles` — les anciennes versions — dans le `public` vide. Vous vous retrouveriez avec deux schémas concurrents à moitié peuplés, et là ça devient vraiment pénible à démêler.

**À faire avant tout redéploiement** : neutraliser l'exécution automatique.

```python
# app/main.py
if settings.APP_ENV not in ("test", "maintenance"):
    run_migrations()
```

Et sur Render, `APP_ENV=maintenance`. Vous réactiverez après avoir posé la nouvelle baseline (`alembic stamp head`).

## 3. Décision : revenir en arrière, ou continuer ?

**Option A — revenir en arrière maintenant.** Cinq secondes, l'application refonctionne, vous ajoutez votre clé IA, et vous refaites la bascule quand le code Python sera prêt.

```sql
DROP SCHEMA ref, core, content, ai, analytics, ops, migration CASCADE;
DROP SCHEMA public CASCADE;
ALTER SCHEMA legacy RENAME TO public;
```

C'est ce que je recommande. Rien n'est perdu : les fichiers SQL sont écrits, la bascule est répétable à volonté, et vous ne travaillez plus sous la pression d'une production à l'arrêt.

**Option B — continuer.** L'application reste hors service jusqu'à ce que les modèles SQLAlchemy soient réécrits. Tenable seulement si personne n'en dépend et si vous vous y mettez tout de suite.

## 4. Extraire le schéma réel

Ne réadaptez pas le Python d'après mes fichiers : ils ont déjà eu deux erreurs de cast. La source de vérité, c'est ce qui est réellement en base. Cette requête sort tout ce dont vous avez besoin pour écrire les modèles :

```sql
SELECT table_schema, table_name, ordinal_position,
       column_name, data_type, udt_name, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema IN ('ref','core','content','ai','analytics','ops')
ORDER BY table_schema, table_name, ordinal_position;
```

Les clés étrangères et contraintes :

```sql
SELECT tc.table_schema, tc.table_name, tc.constraint_type, tc.constraint_name,
       string_agg(kcu.column_name, ', ' ORDER BY kcu.ordinal_position) AS colonnes,
       ccu.table_schema AS ref_schema, ccu.table_name AS ref_table
FROM information_schema.table_constraints tc
LEFT JOIN information_schema.key_column_usage kcu
       ON kcu.constraint_name = tc.constraint_name AND kcu.table_schema = tc.table_schema
LEFT JOIN information_schema.constraint_column_usage ccu
       ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
WHERE tc.table_schema IN ('core','content','ai','analytics','ops')
  AND tc.constraint_type IN ('PRIMARY KEY','FOREIGN KEY','UNIQUE')
GROUP BY 1,2,3,4,6,7
ORDER BY 1,2,3;
```

Les valeurs de statut à recopier dans vos `IntEnum` :

```sql
SELECT 'article' AS entite, id, code, label, state_id FROM ref.article_status_reasons
UNION ALL SELECT 'project', id, code, label, state_id FROM ref.project_status_reasons
UNION ALL SELECT 'membership', id, code, label, state_id FROM ref.membership_status_reasons
UNION ALL SELECT 'run', id, code, label, state_id FROM ref.run_status_reasons
UNION ALL SELECT 'step', id, code, label, state_id FROM ref.step_status_reasons
UNION ALL SELECT 'role', id, code, label, NULL FROM ref.member_roles
ORDER BY 1, 2;
```

Les types énumérés natifs :

```sql
SELECT n.nspname AS schema, t.typname AS type,
       string_agg(e.enumlabel, ', ' ORDER BY e.enumsortorder) AS valeurs
FROM pg_type t
JOIN pg_namespace n ON n.oid = t.typnamespace
JOIN pg_enum e      ON e.enumtypid = t.oid
WHERE n.nspname IN ('core','content','ai')
GROUP BY 1,2 ORDER BY 1,2;
```

Exportez ces quatre résultats en CSV : c'est votre cahier des charges pour la réécriture.

## 5. Correspondance ancien → nouveau

Pour chaque modèle SQLAlchemy à réécrire.

### `User` → `core.users`

| Avant | Après |
|---|---|
| `id` varchar | `id` uuid |
| `name` | supprimé — `first_name` + `last_name` |
| `is_platform_admin` | `is_staff` |
| — | `deleted_at` (nouveau) |

### `Project` → éclaté en 5

| Avant | Après |
|---|---|
| `owner_id` | via `core.organizations` + `core.project_members` (role_id = 50) |
| `status` texte | `state_id` + `status_reason_id` |
| `language` + `country_target` | `locale` (BCP 47) |
| `tone`, `audience`, `reader_level`, `writing_style`, `vertical`, `word_count_*` | `core.editorial_profiles` (colonnes) |
| `seo_rules`, `geo_rules`, `style_examples`, `source_guidelines`, `*_linking_guidelines`, `preferred_formats`, `technical_level`, `editorial_goal`, `value_proposition`, `description`, `industry` | `core.editorial_profiles.rules` (jsonb) |
| `allowed_topics`, `forbidden_topics`, `words_to_avoid` | `core.editorial_profiles.constraints` (jsonb) |
| `public_site_url`, `revalidate_url`, `last_revalidate*` | `core.publishing_targets` |
| `public_tracking_key`, `secret_api_key` | `core.project_credentials` (SHA-256) |

### `Article` → éclaté en 7

| Avant | Après |
|---|---|
| `status` texte | `state_id` + `status_reason_id` |
| `workflow_status` | `ai.workflow_runs.phase_id` |
| `title`, `content`, `excerpt`, `faq_json`, `callouts_json`, `content_blocks_json`, `word_count`, `reading_time_minutes` | `content.article_revisions` |
| `published_*` (10 colonnes) | révision pointée par `published_revision_id` |
| `meta_title`, `meta_description`, `structured_data_json` | `content.article_seo` |
| `keyword`, `secondary_keywords_json` | `content.keywords` + `content.article_keywords` |
| `internal_links_json`, `external_links_json`, `suggested_*_links` | `content.article_links` |
| `seo_score`, `quality_score`, `eeat_score`, `readability_score`, `global_score`, `readiness_status` | `content.article_scores` (historisé) |
| `search_console_metrics_json` | `analytics.search_metrics_daily` |
| les ~40 autres `*_json` | `ai.artifacts` (`agent_key` = nom de la colonne sans `_json`) |
| `workflow_run_id`, `completed_agent_keys`, `next_agent_key` | `ai.workflow_runs` + `ai.workflow_steps` |
| `cover_image_url` | `content.article_media` (role = 'cover') |
| `original_article_id`, `revision_of_article_id` | `derived_from_id` |
| `rejection_reason` | supprimé, `rejection_note` conservé |

### Autres

| Avant | Après |
|---|---|
| `Idea` | n'existe plus — article aux motifs 20 / 30 |
| `ArticleVersion` | `content.article_revisions` |
| `SeoAnalysis` | `content.article_scores` |
| `KanbanColumn` | `content.board_columns` (+ vue `v_board_columns`) |
| `AiProviderConfig` | `ai.providers` + `ai.provider_credentials` |
| `AgentAssignment` | `ai.agents` + `ai.agent_bindings` |
| `Pipeline` | `ai.pipelines` (planning en jsonb) |
| `PipelineLog` | `ai.pipeline_runs` |
| `ArticleLog` + `ActivityLog` | `ops.event_logs` |
| `AiUsageLog` | `ai.usage_events` (partitionné) |
| `TrafficEvent` | `analytics.traffic_events` (partitionné) |
| `ProjectCalloutTemplate` | `content.callout_templates` |

## 6. Ordre de réécriture

1. `app/core/config.py` — `DATABASE_URL` refuse SQLite
2. `app/models/reference.py` — modèles `ref.*` en lecture seule + `IntEnum` (valeurs issues de la requête §4)
3. `app/models/` — `core`, puis `content`, puis `ai`
4. `app/services/tracking_service.py` — recherche par `digest(clé,'sha256')` au lieu de la comparaison en clair
5. `app/services/article_service.py` — `publish` pose `published_revision_id`, `schedule` ne le fait pas
6. `app/services/seo/` — helper `save_artifact()` puis remplacement mécanique
7. `app/routers/` + schémas Pydantic — exposer `state_id`, `state_label`, `status_reason_id`, `status_label`
8. `frontend/src/lib/status.ts` puis les pages
9. `alembic/versions/` — archiver, générer une baseline unique, `alembic stamp head`
10. Réactiver les migrations au démarrage, repasser `APP_ENV=production`

Les vues `content.v_articles_current` et `content.v_articles_published` existent précisément pour cette transition : elles renvoient un article « à plat », comme avant. Une route qui ne fait que lire peut s'y brancher immédiatement, sans attendre que tous les modèles soient réécrits.
