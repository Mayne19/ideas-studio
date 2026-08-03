-- =====================================================================
-- Ideas Studio — cutover rapide v3.2 (peu de données réelles)
-- Ancien schéma (public, PostgreSQL réel — voir CHANGELOG.md) →
-- schéma v3 (ref, core, content, ai, analytics, ops)
--
-- Contexte confirmé : la prod tourne sur PostgreSQL (Render), le volume
-- réel est faible (quelques utilisateurs, une poignée de projets), et
-- les articles/idées sont des données de test qu'on peut sortir sans
-- regret. Sont repris : users, projects, project_members, categories,
-- project_pipelines, ai_provider_configs, agent_assignments,
-- kanban_columns.
--
-- Différence avec la v3.1 : la table id_map générique + la fonction
-- map_id(entité, ancien_id) — pensées pour un volume qu'on n'a pas et
-- pour être rejouées sur des dizaines de milliers de lignes — sont
-- remplacées par une petite table temporaire PAR ENTITÉ (users,
-- organisations, projects, categories). Même principe (correspondance
-- ancien id → nouveau uuid, cohérente d'une table à l'autre), mais
-- chaque table se relit d'un coup d'œil vu le nombre de lignes réel :
-- `SELECT * FROM user_id_map` doit littéralement pouvoir être comparé
-- à la main à `SELECT id, email FROM legacy.users`. Toujours un script
-- rejouable (utile pour répéter l'essai avant le vrai passage), toujours
-- transactionnel — juste sans la mécanique dimensionnée pour un tout
-- autre volume. Voir CHANGELOG.md pour le détail complet.
--
-- Prérequis impératif : APP_ENV=maintenance ou service arrêté, car
-- app/main.py exécute les migrations Alembic au démarrage.
--
-- Sauvegarde (30 secondes, vu le volume) :
--   pg_dump "$DATABASE_URL" -Fc -f backup_avant_refonte.dump
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- 0. Contrôles préalables — AVANT toute écriture. ai_provider_configs,
--    agent_assignments et ai_usage_logs n'ont jamais eu de contrainte de
--    clé étrangère sur project_id (constat de la note de conception
--    d'origine). Ce bloc est trois SELECT — gratuit en temps, toujours
--    utile même sur un petit volume : mieux vaut échouer ici avec un
--    message clair que sur une contrainte FK au milieu de l'étape 6.
-- ---------------------------------------------------------------------
DO $$
DECLARE orphan_count int;
BEGIN
  SELECT count(*) INTO orphan_count
  FROM legacy.ai_provider_configs c
  WHERE c.project_id IS NOT NULL AND c.project_id NOT IN (SELECT id FROM legacy.projects);
  IF orphan_count > 0 THEN
    RAISE EXCEPTION 'ai_provider_configs : % ligne(s) avec un project_id orphelin. Nettoyer avant de relancer.', orphan_count;
  END IF;

  SELECT count(*) INTO orphan_count
  FROM legacy.agent_assignments a
  WHERE a.project_id IS NOT NULL AND a.project_id NOT IN (SELECT id FROM legacy.projects);
  IF orphan_count > 0 THEN
    RAISE EXCEPTION 'agent_assignments : % ligne(s) avec un project_id orphelin. Nettoyer avant de relancer.', orphan_count;
  END IF;

  SELECT count(*) INTO orphan_count
  FROM legacy.agent_assignments a
  WHERE a.provider_id NOT IN (SELECT id FROM legacy.ai_provider_configs);
  IF orphan_count > 0 THEN
    RAISE EXCEPTION 'agent_assignments : % ligne(s) référencent un provider_id inexistant. Nettoyer avant de relancer.', orphan_count;
  END IF;

  SELECT count(*) INTO orphan_count
  FROM legacy.ai_usage_logs u
  WHERE u.project_id IS NOT NULL AND u.project_id NOT IN (SELECT id FROM legacy.projects);
  IF orphan_count > 0 THEN
    RAISE WARNING 'ai_usage_logs : % ligne(s) avec un project_id orphelin — non bloquant (table non reprise par cette migration), à nettoyer séparément si besoin.', orphan_count;
  END IF;
END $$;

ALTER SCHEMA public RENAME TO legacy;
CREATE SCHEMA public;

-- >>> Exécuter ici refonte-schema-v3.sql  (\i refonte-schema-v3.sql)

-- ---------------------------------------------------------------------
-- Correspondances d'id — une table temporaire par entité. Vu le volume
-- réel (quelques dizaines de lignes en tout), chacune peut être relue
-- entièrement avant de continuer, par exemple :
--   SELECT m.old_id, u.email, m.new_id FROM user_id_map m JOIN legacy.users u ON u.id = m.old_id;
-- ---------------------------------------------------------------------
CREATE TEMP TABLE user_id_map AS
  SELECT id AS old_id, gen_random_uuid() AS new_id FROM legacy.users;

CREATE TEMP TABLE org_id_map AS
  SELECT DISTINCT owner_id AS old_owner_id, gen_random_uuid() AS new_id FROM legacy.projects;

CREATE TEMP TABLE project_id_map AS
  SELECT id AS old_id, gen_random_uuid() AS new_id FROM legacy.projects;

CREATE TEMP TABLE category_id_map AS
  SELECT id AS old_id, gen_random_uuid() AS new_id FROM legacy.categories;

-- Remarque : pas de table de correspondance de statuts d'articles ici.
-- ref.article_status_reasons.code porte déjà les vraies valeurs de
-- l'ancien Article.status (draft, writing_in_progress, review_needed,
-- ...) — la correspondance des colonnes kanban se fait par un LEFT JOIN
-- direct sur ce code, à l'étape 8.

-- ---------------------------------------------------------------------
-- 1. Utilisateurs
-- ---------------------------------------------------------------------
INSERT INTO core.users (id, email, username, password_hash, first_name, last_name,
                        avatar_url, is_active, is_staff, created_at, updated_at)
SELECT m.new_id, u.email, u.username, u.password_hash,
       COALESCE(nullif(u.first_name,''), split_part(u.name,' ',1)),
       COALESCE(nullif(u.last_name,''), nullif(substring(u.name from position(' ' in u.name)+1),'')),
       u.avatar_url, u.is_active, u.is_platform_admin, u.created_at, u.updated_at
FROM legacy.users u
JOIN user_id_map m ON m.old_id = u.id;

-- ---------------------------------------------------------------------
-- 2. Organisations — une par propriétaire de projet.
--    Le suffixe -<6 premiers caractères de l'id> garantit un slug
--    unique même si deux comptes partagent le même préfixe d'email ou
--    le même username.
-- ---------------------------------------------------------------------
INSERT INTO core.organizations (id, name, slug)
SELECT om.new_id,
       COALESCE(nullif(u.name,''), split_part(u.email,'@',1)),
       lower(regexp_replace(COALESCE(nullif(u.username,''), split_part(u.email,'@',1)),
                            '[^a-zA-Z0-9]+','-','g')) || '-' || left(u.id, 6)
FROM legacy.users u
JOIN org_id_map om ON om.old_owner_id = u.id;

INSERT INTO core.organization_members (organization_id, user_id, role_id, state_id, status_reason_id)
SELECT om.new_id, um.new_id, 50, 0, 20
FROM org_id_map om
JOIN user_id_map um ON um.old_id = om.old_owner_id;

-- ---------------------------------------------------------------------
-- 3. Projets
--
-- status_reason_id : le vrai Project.status ne connaît que deux valeurs
-- ("not_connected" par défaut, "connected" dès le premier événement
-- /tracking/* — tracking_service.py:40-41, confirmé par la base de dev :
-- 8 not_connected / 1 connected, aucune autre valeur). "archived" (30)
-- existe dans le schéma cible mais n'est jamais atteint par cette
-- migration : aucune donnée legacy n'y correspond, c'est attendu.
-- ---------------------------------------------------------------------
INSERT INTO core.projects (id, organization_id, name, slug, domain, locale, timezone,
                           state_id, status_reason_id, created_at, updated_at)
SELECT pm.new_id,
       om.new_id,
       p.name,
       lower(regexp_replace(p.name,'[^a-zA-Z0-9]+','-','g')) || '-' || left(p.id, 6),
       p.domain,
       COALESCE(nullif(p.language,'') || '-' || upper(COALESCE(nullif(p.country_target,''),'FR')),'fr-FR'),
       COALESCE(nullif(p.timezone,''),'Europe/Paris'),
       0,
       CASE lower(COALESCE(p.status,'not_connected'))
         WHEN 'connected' THEN 20
         ELSE 10
       END,
       p.created_at, p.updated_at
FROM legacy.projects p
JOIN project_id_map pm ON pm.old_id = p.id
JOIN org_id_map om     ON om.old_owner_id = p.owner_id;

INSERT INTO core.editorial_profiles (project_id, version, is_active, audience, tone,
                                     reader_level, writing_style, vertical,
                                     word_count_min, word_count_max, rules, constraints, created_at)
SELECT pm.new_id, 1, true,
       p.audience, p.tone, p.reader_level, p.writing_style, p.vertical,
       p.word_count_min, p.word_count_max,
       jsonb_strip_nulls(jsonb_build_object(
         'seo_rules',p.seo_rules,'geo_rules',p.geo_rules,
         'source_guidelines',p.source_guidelines,
         'internal_linking_guidelines',p.internal_linking_guidelines,
         'external_linking_guidelines',p.external_linking_guidelines,
         'style_examples',p.style_examples,'preferred_formats',p.preferred_formats,
         'technical_level',p.technical_level,'average_target_length',p.average_target_length,
         'editorial_goal',p.editorial_goal,'value_proposition',p.value_proposition,
         'description',p.description,'industry',p.industry)),
       jsonb_strip_nulls(jsonb_build_object(
         'allowed_topics',p.allowed_topics,'forbidden_topics',p.forbidden_topics,
         'words_to_avoid',p.words_to_avoid)),
       p.created_at
FROM legacy.projects p
JOIN project_id_map pm ON pm.old_id = p.id;

INSERT INTO core.publishing_targets (project_id, site_url, revalidate_url, is_primary,
                                     last_synced_at, last_sync_status, last_sync_error)
SELECT pm.new_id, p.public_site_url, p.revalidate_url, true,
       p.last_revalidated_at, p.last_revalidate_status, p.last_revalidate_error
FROM legacy.projects p
JOIN project_id_map pm ON pm.old_id = p.id
WHERE p.public_site_url IS NOT NULL;

-- Clés inchangées côté client : seule leur représentation en base change.
-- tracking_service.py devra chercher par digest(clé,'sha256') au lieu de comparer en clair.
INSERT INTO core.project_credentials (project_id, kind, label, token_prefix, token_sha256, created_at)
SELECT pm.new_id, 'tracking', 'Tracking key',
       left(p.public_tracking_key,8), digest(p.public_tracking_key,'sha256'), p.created_at
FROM legacy.projects p
JOIN project_id_map pm ON pm.old_id = p.id
WHERE p.public_tracking_key IS NOT NULL
UNION ALL
SELECT pm.new_id, 'api', 'API key',
       left(p.secret_api_key,8), digest(p.secret_api_key,'sha256'), p.created_at
FROM legacy.projects p
JOIN project_id_map pm ON pm.old_id = p.id
WHERE p.secret_api_key IS NOT NULL;

-- ---------------------------------------------------------------------
-- 4. Membres
--
-- role_id : les 5 vrais rôles (project_member.py:23). Un rôle legacy
-- inconnu tombe sur "viewer" (10) — le moins privilégié — plutôt que
-- sur un rôle à mi-échelle : un rôle mal reconnu doit échouer fermé.
-- ---------------------------------------------------------------------
INSERT INTO core.project_members (project_id, user_id, role_id, state_id, status_reason_id, created_at)
SELECT pm.new_id, um.new_id,
       CASE lower(m.role)
         WHEN 'owner'    THEN 50
         WHEN 'admin'    THEN 40
         WHEN 'editor'   THEN 30
         WHEN 'designer' THEN 20
         WHEN 'viewer'   THEN 10
         ELSE 10
       END,
       CASE lower(m.status) WHEN 'suspended' THEN 1 WHEN 'removed' THEN 1 ELSE 0 END,
       CASE lower(m.status) WHEN 'invited' THEN 10 WHEN 'suspended' THEN 30
                            WHEN 'removed' THEN 40 ELSE 20 END,
       m.created_at
FROM legacy.project_members m
JOIN project_id_map pm ON pm.old_id = m.project_id
JOIN user_id_map um    ON um.old_id = m.user_id
ON CONFLICT (project_id, user_id) DO NOTHING;

INSERT INTO core.project_members (project_id, user_id, role_id, state_id, status_reason_id, created_at)
SELECT pm.new_id, um.new_id, 50, 0, 20, p.created_at
FROM legacy.projects p
JOIN project_id_map pm ON pm.old_id = p.id
JOIN user_id_map um    ON um.old_id = p.owner_id
ON CONFLICT (project_id, user_id) DO UPDATE SET role_id = 50;

-- ---------------------------------------------------------------------
-- 5. Catégories
-- ---------------------------------------------------------------------
INSERT INTO content.categories (id, project_id, name, slug, description, color,
                                priority_score, monthly_target, is_pipeline_enabled,
                                overrides, created_at, updated_at)
SELECT cm.new_id, pm.new_id,
       c.name, c.slug, c.description, c.color,
       COALESCE(c.priority_score, c.priority),
       COALESCE(c.monthly_frequency, c.target_frequency),
       COALESCE(c.pipeline_enabled, true),
       jsonb_strip_nulls(jsonb_build_object(
         'editorial_goal',c.editorial_goal,'target_audience',c.target_audience,
         'internal_notes',c.internal_notes,'vertical',c.vertical,'niche',c.niche,
         'word_count_min',c.word_count_min,'word_count_max',c.word_count_max)),
       c.created_at, c.updated_at
FROM legacy.categories c
JOIN category_id_map cm ON cm.old_id = c.id
JOIN project_id_map pm  ON pm.old_id = c.project_id;

-- ---------------------------------------------------------------------
-- 6. Fournisseurs, agents, affectations
--
-- ai.providers est déjà pré-rempli par refonte-schema-v3.sql (catalogue
-- statique aligné sur core/config.py). On complète seulement si un
-- projet a configuré un provider hors catalogue (typo, provider
-- déprécié) — ON CONFLICT DO NOTHING au lieu d'écraser.
-- Pas de table de correspondance dédiée pour ai_provider_configs : le
-- provider_id cible se retrouve directement par jointure sur le code
-- (lower(provider)), pas besoin de générer un nouvel id ici — c'est déjà
-- ai.providers.id, stable, seedé par le schéma.
-- ---------------------------------------------------------------------
INSERT INTO ai.providers (code, label, base_url, is_enabled)
SELECT DISTINCT ON (lower(c.provider))
       lower(c.provider), COALESCE(c.display_name, c.label, initcap(c.provider)),
       c.base_url, c.enabled
FROM legacy.ai_provider_configs c
ORDER BY lower(c.provider), c.created_at
ON CONFLICT (code) DO NOTHING;

INSERT INTO ai.provider_credentials (provider_id, project_id, secret_ref, last_test_at, last_test_ok, created_at)
SELECT pr.id, pm.new_id,
       'TODO://vault/' || lower(c.provider) || '/' || c.id,
       c.last_tested_at, (c.last_test_status = 'success'), c.created_at
FROM legacy.ai_provider_configs c
JOIN ai.providers pr    ON pr.code = lower(c.provider)
LEFT JOIN project_id_map pm ON pm.old_id = c.project_id;

-- Filet de sécurité uniquement : le catalogue réel (62 agents, avec
-- category/phase/output_json_field) vit dans
-- app/services/agents/agent_registry.py et est synchronisé par
-- l'application juste après cette migration (voir plan §2). Cette
-- insertion garantit seulement qu'aucune ligne agent_assignments ne
-- fera échouer la FK ci-dessous si elle référence une clé pas encore
-- synchronisée.
INSERT INTO ai.agents (key, label, category, phase, status)
SELECT DISTINCT a.agent_id, initcap(replace(a.agent_id,'_',' ')), 'creation', 'unknown', 'planned'
FROM legacy.agent_assignments a
ON CONFLICT (key) DO NOTHING;

INSERT INTO ai.agent_bindings (agent_id, provider_id, project_id, model, priority, is_enabled)
SELECT ag.id, pr.id, pm.new_id,
       COALESCE(c.model,'default'), a.priority, a.enabled
FROM legacy.agent_assignments a
JOIN ai.agents ag                 ON ag.key = a.agent_id
JOIN legacy.ai_provider_configs c ON c.id = a.provider_id
JOIN ai.providers pr              ON pr.code = lower(c.provider)
LEFT JOIN project_id_map pm       ON pm.old_id = a.project_id;

-- ---------------------------------------------------------------------
-- 7. Pipelines
-- ---------------------------------------------------------------------
INSERT INTO ai.pipelines (project_id, is_enabled, articles_per_week, ideas_per_week,
                          max_pending_drafts, max_parallel_jobs, schedule, quality_mode,
                          cost_limit_per_article, paused_until, updated_at)
SELECT pm.new_id, p.enabled, p.articles_per_week,
       COALESCE(p.ideas_per_week,5), COALESCE(p.max_pending_drafts,10),
       COALESCE(p.max_parallel_writing_jobs,2),
       jsonb_strip_nulls(jsonb_build_object(
         'active_days',        nullif(p.active_days,'')::jsonb,
         'launch_hour',        p.launch_hour,
         'launch_hours',       nullif(p.launch_hours,'')::jsonb,
         'publish_hour_start', p.publish_hour_start,
         'publish_hour_end',   p.publish_hour_end,
         'ideas_day_of_month', p.ideas_day_of_month,
         'category_priorities',nullif(p.category_priorities,'')::jsonb)),
       COALESCE(p.default_quality_mode,'quality'), p.cost_limit_per_article_eur,
       CASE WHEN p.paused_indefinitely THEN 'infinity'::timestamptz ELSE p.paused_until END,
       p.updated_at
FROM legacy.project_pipelines p
JOIN project_id_map pm ON pm.old_id = p.project_id;

-- ---------------------------------------------------------------------
-- 8. Colonnes kanban personnalisées
--
-- LEFT JOIN (pas INNER JOIN) sur ref.article_status_reasons.code, qui
-- porte déjà les vraies valeurs d'Article.status. Toute ligne dont le
-- statut ne correspond à aucun motif connu (colonnes "custom_xxx" —
-- une fonctionnalité réelle, kanban_columns.py:50 — ou un statut
-- historique renommé depuis) devient une colonne libre (custom_key) au
-- lieu de disparaître.
-- ---------------------------------------------------------------------
INSERT INTO content.board_columns (project_id, status_reason_id, custom_key, label, color, sort_order, is_visible)
SELECT
  pm.new_id,
  sr.id,
  CASE WHEN sr.id IS NULL THEN lower(k.status) END,
  k.label, k.color, k.sort_order, true
FROM legacy.kanban_columns k
JOIN project_id_map pm ON pm.old_id = k.project_id
LEFT JOIN ref.article_status_reasons sr ON sr.code = lower(k.status)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------
-- 9. Contrôles — la transaction est annulée au moindre écart. Vu le
--    volume réel, ces comptages peuvent aussi être vérifiés à l'œil
--    juste avant le COMMIT (SELECT * FROM ... au lieu de count(*)).
-- ---------------------------------------------------------------------
DO $$
DECLARE o int; n int;
BEGIN
  SELECT count(*) INTO o FROM legacy.users;             SELECT count(*) INTO n FROM core.users;
  IF o <> n THEN RAISE EXCEPTION 'users : % / %', o, n; END IF;

  SELECT count(*) INTO o FROM legacy.projects;          SELECT count(*) INTO n FROM core.projects;
  IF o <> n THEN RAISE EXCEPTION 'projects : % / %', o, n; END IF;

  SELECT count(*) INTO o FROM legacy.projects;          SELECT count(*) INTO n FROM core.editorial_profiles WHERE is_active;
  IF o <> n THEN RAISE EXCEPTION 'editorial_profiles : % / %', o, n; END IF;

  SELECT count(*) INTO o FROM legacy.categories;        SELECT count(*) INTO n FROM content.categories;
  IF o <> n THEN RAISE EXCEPTION 'categories : % / %', o, n; END IF;

  SELECT count(*) INTO o FROM legacy.agent_assignments; SELECT count(*) INTO n FROM ai.agent_bindings;
  IF o <> n THEN RAISE EXCEPTION 'agent_bindings : % / %', o, n; END IF;

  SELECT count(*) INTO o FROM legacy.project_pipelines; SELECT count(*) INTO n FROM ai.pipelines;
  IF o <> n THEN RAISE EXCEPTION 'pipelines : % / %', o, n; END IF;

  SELECT count(*) INTO o FROM legacy.kanban_columns;    SELECT count(*) INTO n FROM content.board_columns;
  IF o <> n THEN RAISE EXCEPTION 'board_columns : % / %', o, n; END IF;

  -- Aucun projet sans membre propriétaire
  SELECT count(*) INTO o FROM core.projects p
   WHERE NOT EXISTS (SELECT 1 FROM core.project_members m
                     WHERE m.project_id = p.id AND m.role_id = 50);
  IF o > 0 THEN RAISE EXCEPTION '% projet(s) sans propriétaire', o; END IF;
END $$;

-- Optionnel — vu le faible volume, un dernier coup d'œil manuel avant
-- de valider ne coûte rien :
--   SELECT slug, status_reason_id FROM core.projects;
--   SELECT email, role_id FROM core.users u JOIN core.project_members m ON m.user_id = u.id;

COMMIT;

-- =====================================================================
-- APRÈS VALIDATION
-- =====================================================================
-- 1. Synchroniser le vrai catalogue d'agents depuis le code :
--      ./venv/bin/python -m app.scripts.sync_agent_catalog   (à créer, voir plan §2)
--    Ceci met à jour category/phase/status/output_json_field pour les
--    clés déjà présentes (étape 6) et ajoute les agents jamais assignés
--    à un provider (la majorité des 62 — la plupart tournent sur le
--    provider par défaut du projet, sans ligne agent_assignments dédiée).
-- 2. Clés des fournisseurs IA vers le coffre :
--      UPDATE ai.provider_credentials SET secret_ref = '<ref>' WHERE secret_ref LIKE 'TODO://%';
--      SELECT count(*) FROM ai.provider_credentials WHERE secret_ref LIKE 'TODO://%';  -- doit valoir 0
-- 3. alembic stamp head   (nouvelle baseline)
-- 4. Redémarrer le service avec APP_ENV=production
-- 5. Après une à deux semaines : DROP SCHEMA legacy CASCADE;
--
-- Retour arrière tant que legacy existe :
--   DROP SCHEMA ref, core, content, ai, analytics, ops CASCADE;
--   DROP SCHEMA public CASCADE;
--   ALTER SCHEMA legacy RENAME TO public;
