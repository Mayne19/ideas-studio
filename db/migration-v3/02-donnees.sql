-- =====================================================================
-- ONGLET 2 — Reprise des données depuis le schéma legacy
--
-- PRÉREQUIS : 01-schema.sql exécuté avec succès.
--
-- Corrections appliquées par rapport à la version d'origine :
--   * cast explicite ::core.credential_kind (bloc project_credentials)
--   * casts explicites ::ai.agent_category et ::ai.agent_status
--     (bloc ai.agents) — un UNION ou un DISTINCT fige le type des
--     littéraux avant l'affectation à la colonne
--   * COMMIT final retiré : le SQL Editor gère sa propre transaction
--
-- Si "function digest(...) does not exist" : remplacer les deux
-- occurrences de digest( par extensions.digest(
--
-- POUR RELANCER APRÈS UN ÉCHEC, exécuter d'abord :
--   DROP SCHEMA IF EXISTS migration CASCADE;
--   DO $reset$ DECLARE t text; BEGIN
--     FOR t IN SELECT schemaname||'.'||tablename FROM pg_tables
--              WHERE schemaname IN ('core','content','ai','analytics','ops')
--     LOOP EXECUTE format('TRUNCATE %s CASCADE', t); END LOOP;
--   END $reset$;
-- =====================================================================

CREATE SCHEMA migration;

CREATE TABLE migration.id_map (
  entity text NOT NULL,
  old_id text NOT NULL,
  new_id uuid NOT NULL,
  PRIMARY KEY (entity, old_id)
);

CREATE OR REPLACE FUNCTION migration.map_id(p_entity text, p_old text)
RETURNS uuid LANGUAGE plpgsql AS $$
DECLARE v_new uuid;
BEGIN
  IF p_old IS NULL THEN RETURN NULL; END IF;
  SELECT new_id INTO v_new FROM migration.id_map WHERE entity = p_entity AND old_id = p_old;
  IF FOUND THEN RETURN v_new; END IF;
  BEGIN v_new := p_old::uuid;
  EXCEPTION WHEN others THEN v_new := gen_random_uuid();
  END;
  INSERT INTO migration.id_map VALUES (p_entity, p_old, v_new);
  RETURN v_new;
END $$;

-- Remarque : il n'y a plus de table de correspondance de statuts
-- d'articles ici. ref.article_status_reasons.code porte déjà les
-- vraies valeurs de l'ancien Article.status (draft, writing_in_progress,
-- review_needed, ...) — la correspondance se fait par un LEFT JOIN
-- direct sur ce code, à l'étape 8.

-- ---------------------------------------------------------------------
-- 1. Utilisateurs
-- ---------------------------------------------------------------------
INSERT INTO core.users (id, email, username, password_hash, first_name, last_name,
                        avatar_url, is_active, is_staff, created_at, updated_at)
SELECT migration.map_id('user', u.id), u.email, u.username, u.password_hash,
       COALESCE(nullif(u.first_name,''), split_part(u.name,' ',1)),
       COALESCE(nullif(u.last_name,''), nullif(substring(u.name from position(' ' in u.name)+1),'')),
       u.avatar_url, u.is_active, u.is_platform_admin, u.created_at, u.updated_at
FROM legacy.users u;

-- ---------------------------------------------------------------------
-- 2. Organisations — une par propriétaire de projet.
--    Le suffixe -<6 premiers caractères de l'id> garantit un slug
--    unique même si deux comptes partagent le même préfixe d'email ou
--    le même username (le v3 initial pouvait produire une violation
--    UNIQUE ici, non gérée).
-- ---------------------------------------------------------------------
INSERT INTO core.organizations (id, name, slug)
SELECT migration.map_id('org', u.id),
       COALESCE(nullif(u.name,''), split_part(u.email,'@',1)),
       lower(regexp_replace(COALESCE(nullif(u.username,''), split_part(u.email,'@',1)),
                            '[^a-zA-Z0-9]+','-','g')) || '-' || left(u.id, 6)
FROM legacy.users u
WHERE EXISTS (SELECT 1 FROM legacy.projects p WHERE p.owner_id = u.id);

INSERT INTO core.organization_members (organization_id, user_id, role_id, state_id, status_reason_id)
SELECT migration.map_id('org', u.id), migration.map_id('user', u.id), 50, 0, 20
FROM legacy.users u
WHERE EXISTS (SELECT 1 FROM legacy.projects p WHERE p.owner_id = u.id);

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
SELECT migration.map_id('project', p.id),
       migration.map_id('org', p.owner_id),
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
FROM legacy.projects p;

INSERT INTO core.editorial_profiles (project_id, version, is_active, audience, tone,
                                     reader_level, writing_style, vertical,
                                     word_count_min, word_count_max, rules, constraints, created_at)
SELECT migration.map_id('project', p.id), 1, true,
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
FROM legacy.projects p;

INSERT INTO core.publishing_targets (project_id, site_url, revalidate_url, is_primary,
                                     last_synced_at, last_sync_status, last_sync_error)
SELECT migration.map_id('project', p.id), p.public_site_url, p.revalidate_url, true,
       p.last_revalidated_at, p.last_revalidate_status, p.last_revalidate_error
FROM legacy.projects p WHERE p.public_site_url IS NOT NULL;

-- Clés inchangées côté client : seule leur représentation en base change.
-- tracking_service.py devra chercher par digest(clé,'sha256') au lieu de comparer en clair.
INSERT INTO core.project_credentials (project_id, kind, label, token_prefix, token_sha256, created_at)
SELECT migration.map_id('project', p.id), 'tracking'::core.credential_kind, 'Tracking key',
       left(p.public_tracking_key,8), digest(p.public_tracking_key,'sha256'), p.created_at
FROM legacy.projects p WHERE p.public_tracking_key IS NOT NULL
UNION ALL
SELECT migration.map_id('project', p.id), 'api'::core.credential_kind, 'API key',
       left(p.secret_api_key,8), digest(p.secret_api_key,'sha256'), p.created_at
FROM legacy.projects p WHERE p.secret_api_key IS NOT NULL;

-- ---------------------------------------------------------------------
-- 4. Membres
--
-- role_id : les 5 vrais rôles (project_member.py:23). Un rôle legacy
-- inconnu tombe désormais sur "viewer" (10) — le moins privilégié —
-- plutôt que sur un rôle à mi-échelle comme le faisait le v3 initial :
-- un rôle mal reconnu doit échouer fermé (moins de droits), pas ouvert.
-- ---------------------------------------------------------------------
INSERT INTO core.project_members (project_id, user_id, role_id, state_id, status_reason_id, created_at)
SELECT migration.map_id('project', m.project_id), migration.map_id('user', m.user_id),
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
ON CONFLICT (project_id, user_id) DO NOTHING;

INSERT INTO core.project_members (project_id, user_id, role_id, state_id, status_reason_id, created_at)
SELECT migration.map_id('project', p.id), migration.map_id('user', p.owner_id), 50, 0, 20, p.created_at
FROM legacy.projects p
ON CONFLICT (project_id, user_id) DO UPDATE SET role_id = 50;

-- ---------------------------------------------------------------------
-- 5. Catégories
-- ---------------------------------------------------------------------
INSERT INTO content.categories (id, project_id, name, slug, description, color,
                                priority_score, monthly_target, is_pipeline_enabled,
                                overrides, created_at, updated_at)
SELECT migration.map_id('category', c.id), migration.map_id('project', c.project_id),
       c.name, c.slug, c.description, c.color,
       COALESCE(c.priority_score, c.priority),
       COALESCE(c.monthly_frequency, c.target_frequency),
       COALESCE(c.pipeline_enabled, true),
       jsonb_strip_nulls(jsonb_build_object(
         'editorial_goal',c.editorial_goal,'target_audience',c.target_audience,
         'internal_notes',c.internal_notes,'vertical',c.vertical,'niche',c.niche,
         'word_count_min',c.word_count_min,'word_count_max',c.word_count_max)),
       c.created_at, c.updated_at
FROM legacy.categories c;

-- ---------------------------------------------------------------------
-- 6. Fournisseurs, agents, affectations
--
-- ai.providers est déjà pré-rempli par refonte-schema-v3.sql (catalogue
-- statique aligné sur core/config.py). On complète seulement si un
-- projet a configuré un provider hors catalogue (typo, provider
-- déprécié) — ON CONFLICT DO NOTHING au lieu d'écraser.
-- ---------------------------------------------------------------------
INSERT INTO ai.providers (code, label, base_url, is_enabled)
SELECT DISTINCT ON (lower(c.provider))
       lower(c.provider), COALESCE(c.display_name, c.label, initcap(c.provider)),
       c.base_url, c.enabled
FROM legacy.ai_provider_configs c
ORDER BY lower(c.provider), c.created_at
ON CONFLICT (code) DO NOTHING;

INSERT INTO ai.provider_credentials (provider_id, project_id, secret_ref, last_test_at, last_test_ok, created_at)
SELECT pr.id, migration.map_id('project', c.project_id),
       'TODO://vault/' || lower(c.provider) || '/' || c.id,
       c.last_tested_at, (c.last_test_status = 'success'), c.created_at
FROM legacy.ai_provider_configs c
JOIN ai.providers pr ON pr.code = lower(c.provider);

-- Filet de sécurité uniquement : le catalogue réel (62 agents, avec
-- category/phase/output_json_field) vit dans
-- app/services/agents/agent_registry.py et est synchronisé par
-- l'application juste après cette migration (voir plan §2). Cette
-- insertion garantit seulement qu'aucune ligne agent_assignments ne
-- fera échouer la FK ci-dessous si elle référence une clé pas encore
-- synchronisée.
INSERT INTO ai.agents (key, label, category, phase, status)
SELECT DISTINCT a.agent_id, initcap(replace(a.agent_id,'_',' ')),
       'creation'::ai.agent_category, 'unknown'::text, 'planned'::ai.agent_status
FROM legacy.agent_assignments a
ON CONFLICT (key) DO NOTHING;

INSERT INTO ai.agent_bindings (agent_id, provider_id, project_id, model, priority, is_enabled)
SELECT ag.id, pr.id, migration.map_id('project', a.project_id),
       COALESCE(c.model,'default'), a.priority, a.enabled
FROM legacy.agent_assignments a
JOIN ai.agents ag                 ON ag.key = a.agent_id
JOIN legacy.ai_provider_configs c ON c.id = a.provider_id
JOIN ai.providers pr              ON pr.code = lower(c.provider);

-- ---------------------------------------------------------------------
-- 7. Pipelines
-- ---------------------------------------------------------------------
INSERT INTO ai.pipelines (project_id, is_enabled, articles_per_week, ideas_per_week,
                          max_pending_drafts, max_parallel_jobs, schedule, quality_mode,
                          cost_limit_per_article, paused_until, updated_at)
SELECT migration.map_id('project', p.project_id), p.enabled, p.articles_per_week,
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
FROM legacy.project_pipelines p;

-- ---------------------------------------------------------------------
-- 8. Colonnes kanban personnalisées
--
-- LEFT JOIN (pas INNER JOIN) sur ref.article_status_reasons.code, qui
-- porte déjà les vraies valeurs d'Article.status. Toute ligne dont le
-- statut ne correspond à aucun motif connu (colonnes "custom_xxx" —
-- une fonctionnalité réelle, kanban_columns.py:50 — ou un statut
-- historique renommé depuis) devient une colonne libre (custom_key) au
-- lieu de disparaître. C'est le changement le plus important de cette
-- révision : la version précédente perdait silencieusement ces lignes
-- via un INNER JOIN sur une table de correspondance qui ne couvrait
-- qu'un vocabulaire de statuts inventé.
-- ---------------------------------------------------------------------
INSERT INTO content.board_columns (project_id, status_reason_id, custom_key, label, color, sort_order, is_visible)
SELECT
  migration.map_id('project', k.project_id),
  sr.id,
  CASE WHEN sr.id IS NULL THEN lower(k.status) END,
  k.label, k.color, k.sort_order, true
FROM legacy.kanban_columns k
LEFT JOIN ref.article_status_reasons sr ON sr.code = lower(k.status)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------
-- 9. Contrôles — la transaction est annulée au moindre écart
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

  -- Nouveau : absent du script initial. C'est ce comptage qui aurait
  -- révélé la perte silencieuse des colonnes kanban.
  SELECT count(*) INTO o FROM legacy.kanban_columns;    SELECT count(*) INTO n FROM content.board_columns;
  IF o <> n THEN RAISE EXCEPTION 'board_columns : % / %', o, n; END IF;

  -- Aucun projet sans membre propriétaire
  SELECT count(*) INTO o FROM core.projects p
   WHERE NOT EXISTS (SELECT 1 FROM core.project_members m
                     WHERE m.project_id = p.id AND m.role_id = 50);
  IF o > 0 THEN RAISE EXCEPTION '% projet(s) sans propriétaire', o; END IF;
END $$;
