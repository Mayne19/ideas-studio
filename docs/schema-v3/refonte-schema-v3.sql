-- =====================================================================
-- Ideas Studio — refonte du schéma, v3.1 (révisée)
--
-- Révision du v3 initial après confrontation au code réel et aux
-- données de dev (md-datas/ideas_studio.db) et de prod. Voir
-- docs/schema-v3/CHANGELOG.md pour le détail de chaque changement.
--
-- Points structurants de cette révision :
--   * Tous les libellés (`label`) sont en anglais, comme les `code`.
--     Le français reste géré côté frontend (frontend/src/lib/status.ts),
--     jamais stocké en base — une seule source de vérité, traduite à
--     l'affichage.
--   * Le vocabulaire de statuts colle exactement à ce que le code utilise
--     aujourd'hui (app/models/*.py), pas à un vocabulaire réinventé.
--   * Deux axes distincts pour un article, comme le fait déjà le code
--     actuel (Article.status vs Article.workflow_status) :
--       - content.articles.status_reason_id   → étape éditoriale
--       - ai.workflow_runs.status_reason_id   → issue de l'exécution IA
--       - ai.workflow_runs.phase_id           → phase du pipeline IA
--   * content.board_columns supporte les colonnes kanban réellement
--     libres (custom_key), une fonctionnalité existante du produit
--     (voir app/routers/kanban_columns.py) que le v3 initial ne pouvait
--     pas représenter.
--   * ai.agents porte les métadonnées du registre Python
--     (app/services/agents/agent_registry.py, 62 agents) : category,
--     phase, status, output_json_field. Ce n'est PAS rempli à la main
--     ici — il est synchronisé par l'application au démarrage (source
--     de vérité = le code, la base est un cache interrogeable). Voir
--     plan-migration-v3.md §2.
-- PostgreSQL 15+
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE SCHEMA IF NOT EXISTS ref;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS content;
CREATE SCHEMA IF NOT EXISTS ai;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS ops;

-- =====================================================================
-- REF — statuts et motifs
-- =====================================================================

-- Niveau 1 : le statut. Deux valeurs, valables pour toutes les entités.
CREATE TABLE ref.states (
  id    smallint PRIMARY KEY,
  code  text NOT NULL UNIQUE,
  label text NOT NULL
);
INSERT INTO ref.states (id, code, label) VALUES
  (0,'active','Active'),
  (1,'inactive','Inactive');

-- ---------------------------------------------------------------------
-- Projets — vocabulaire réel (app/services/project_service.py,
-- app/services/tracking_service.py:40-41). Aujourd'hui, un projet n'a
-- QUE deux états observables : "not_connected" (par défaut) et
-- "connected" (bascule automatique dès le premier événement /tracking/*
-- reçu). Il n'existe ni "running", ni "paused", ni "suspended" dans le
-- code — le v3 initial inventait ces motifs sans support applicatif.
-- "archived" est ajouté en anticipation du point ouvert de la note de
-- conception (§6, "Suppression des projets" — ON DELETE RESTRICT impose
-- un archivage explicite) : la colonne existe, aucune donnée réelle n'y
-- correspondra tant que l'app ne l'implémente pas.
-- ---------------------------------------------------------------------
CREATE TABLE ref.project_status_reasons (
  id         smallint PRIMARY KEY,
  state_id   smallint NOT NULL REFERENCES ref.states(id),
  code       text NOT NULL UNIQUE,
  label      text NOT NULL,
  sort_order smallint NOT NULL DEFAULT 0,
  is_default boolean NOT NULL DEFAULT false,
  UNIQUE (id, state_id)
);
INSERT INTO ref.project_status_reasons (id, state_id, code, label, sort_order, is_default) VALUES
  (10,0,'not_connected','Not connected',10,true),
  (20,0,'connected','Connected',20,false),
  (30,1,'archived','Archived',30,false);

-- ---------------------------------------------------------------------
-- Articles — repris 1:1 depuis ARTICLE_STATUSES (app/models/article.py:7-30),
-- confirmé en base de dev réelle (draft, draft_ready, idea_priority,
-- idea_proposed, published, review_needed, writing_in_progress y sont
-- effectivement présents). Rien n'est inventé, rien n'est fusionné :
-- fusionner aurait cassé les routers qui testent une valeur exacte
-- (app/routers/ideas.py:279,474,635 ; app/routers/articles.py:151,257,278,363,385 ;
-- app/services/production_queue.py:103,165,195,210,261,382,394,405).
--
-- requires_revision : uniquement published et unpublished. "scheduled"
-- N'EST PAS de la publication (voir schedule_article_with_validation,
-- article_service.py:188-210 : aucun _snapshot_published_fields() n'y
-- est appelé, published_revision_id reste tel quel). Le v3 initial
-- exigeait déjà published_revision_id pour "scheduled" — cela aurait
-- rendu la programmation d'un article impossible.
--
-- designer_editable : reflet direct de DESIGNER_EDITABLE_STATUSES
-- (article.py:33-35), pour appliquer la permission en base plutôt que
-- de dupliquer un frozenset Python dans une contrainte applicative.
--
-- is_board_visible=false pour update_recommended/improvement_* : ces
-- motifs vivent sur la page /projects/:id/recommendations
-- (OptimizationRecommendation), pas sur le kanban de production.
-- ---------------------------------------------------------------------
CREATE TABLE ref.article_status_reasons (
  id                smallint PRIMARY KEY,
  state_id          smallint NOT NULL REFERENCES ref.states(id),
  code              text NOT NULL UNIQUE,
  label             text NOT NULL,
  color             text,
  sort_order        smallint NOT NULL,
  is_board_visible  boolean NOT NULL DEFAULT true,
  is_default        boolean NOT NULL DEFAULT false,
  requires_revision boolean NOT NULL DEFAULT false,
  designer_editable boolean NOT NULL DEFAULT false,
  UNIQUE (id, state_id)
);
INSERT INTO ref.article_status_reasons
  (id, state_id, code, label, color, sort_order, is_board_visible, is_default, requires_revision, designer_editable) VALUES
  (10, 0,'draft',                'Draft',                 '#8892a0',10, true,  true,  false, true),
  (20, 0,'idea_proposed',        'Idea proposed',         '#8892a0',20, true,  false, false, false),
  (30, 0,'idea_priority',        'Idea prioritized',      '#7c9dfd',30, true,  false, false, false),
  (40, 0,'outline_ready',        'Outline ready',         '#7c9dfd',40, true,  false, false, false),
  (50, 0,'writing_requested',    'Writing requested',     '#e0a03a',50, true,  false, false, false),
  (60, 0,'writing_in_progress',  'Writing in progress',   '#e0a03a',60, true,  false, false, false),
  (70, 0,'draft_ready',          'Draft ready',            '#e0a03a',70, true,  false, false, true),
  (80, 0,'review_needed',        'Review needed',          '#e0a03a',80, true,  false, false, true),
  (90, 0,'correction_needed',    'Correction needed',      '#c0392b',90, true,  false, false, true),
  (100,0,'ready_to_publish',     'Ready to publish',       '#1d9e75',100,true,  false, false, true),
  (110,0,'scheduled',            'Scheduled',              '#1d9e75',110,true,  false, false, false),
  (120,0,'published',            'Published',              '#0f6e56',120,true,  false, true,  false),
  (130,0,'unpublished',          'Unpublished',            '#6b6b6b',130,true,  false, true,  false),
  (140,0,'update_recommended',   'Update recommended',     '#e0a03a',140,false, false, false, false),
  (150,0,'improvement_proposed', 'Improvement proposed',   '#7c9dfd',150,false, false, false, false),
  (160,0,'improvement_in_progress','Improvement in progress','#e0a03a',160,false, false, false, false),
  (170,0,'improvement_ready',    'Improvement ready',      '#1d9e75',170,false, false, false, false),
  (180,0,'failed',               'Failed',                 '#c0392b',180,true,  false, false, false),
  (190,0,'blocked_cost_limit',   'Blocked (cost limit)',   '#c0392b',190,true,  false, false, false),
  (200,1,'idea_rejected',        'Idea rejected',          '#c0392b',200,false, false, false, false),
  (210,1,'archived',             'Archived',               '#6b6b6b',210,false, false, false, false);

CREATE TABLE ref.membership_status_reasons (
  id       smallint PRIMARY KEY,
  state_id smallint NOT NULL REFERENCES ref.states(id),
  code     text NOT NULL UNIQUE,
  label    text NOT NULL,
  is_default boolean NOT NULL DEFAULT false,
  UNIQUE (id, state_id)
);
INSERT INTO ref.membership_status_reasons (id, state_id, code, label, is_default) VALUES
  (10,0,'invited','Invited',false),
  (20,0,'active','Active',true),
  (30,1,'suspended','Suspended',true),
  (40,1,'removed','Removed',false);

CREATE TABLE ref.run_status_reasons (
  id       smallint PRIMARY KEY,
  state_id smallint NOT NULL REFERENCES ref.states(id),
  code     text NOT NULL UNIQUE,
  label    text NOT NULL,
  is_default boolean NOT NULL DEFAULT false,
  UNIQUE (id, state_id)
);
INSERT INTO ref.run_status_reasons (id, state_id, code, label, is_default) VALUES
  (10,0,'queued','Queued',true),
  (20,0,'running','Running',false),
  (30,1,'succeeded','Succeeded',true),
  (40,1,'failed','Failed',false),
  (50,1,'cancelled','Cancelled',false);

CREATE TABLE ref.step_status_reasons (
  id       smallint PRIMARY KEY,
  state_id smallint NOT NULL REFERENCES ref.states(id),
  code     text NOT NULL UNIQUE,
  label    text NOT NULL,
  is_default boolean NOT NULL DEFAULT false,
  UNIQUE (id, state_id)
);
INSERT INTO ref.step_status_reasons (id, state_id, code, label, is_default) VALUES
  (10,0,'pending','Pending',true),
  (20,0,'running','Running',false),
  (30,1,'succeeded','Succeeded',true),
  (40,1,'failed','Failed',false),
  (50,1,'skipped','Skipped',false);

-- ---------------------------------------------------------------------
-- Phases du pipeline IA — reprend les valeurs RÉELLES observées dans
-- Article.workflow_status (distinct de Article.status !) :
-- app/services/idea_engine.py:461, app/routers/ideas.py:461,506,
-- app/services/production_queue.py:93,102,266, app/services/pipeline_service.py:462.
-- Le code utilise déjà deux axes ("status" éditorial + "workflow_status"
-- pipeline) — le v3 initial n'en capturait qu'un. "error" n'est pas
-- repris comme phase : c'est une ISSUE (ref.run_status_reasons.failed),
-- pas une étape du pipeline.
-- ---------------------------------------------------------------------
CREATE TABLE ref.workflow_phases (
  id         smallint PRIMARY KEY,
  code       text NOT NULL UNIQUE,
  label      text NOT NULL,
  sort_order smallint NOT NULL
);
INSERT INTO ref.workflow_phases (id, code, label, sort_order) VALUES
  (10,'idea_prebrief','Idea prebrief',10),
  (20,'planning','Planning',20),
  (30,'production','Production',30),
  (40,'quality','Quality review',40),
  (50,'completed','Completed',50);

-- Rôles : pas un statut, mais même logique d'identifiant + libellé.
-- Repris exactement de PROJECT_ROLES (app/models/project_member.py:23) :
-- ("owner","admin","editor","designer","viewer"). Le v3 initial avait
-- inventé un rôle "writer" qui n'existe nulle part dans le code, et
-- oubliait "designer" qui, lui, conditionne réellement des permissions
-- (DESIGNER_EDITABLE_STATUSES, article.py:33-35).
CREATE TABLE ref.member_roles (
  id    smallint PRIMARY KEY,
  code  text NOT NULL UNIQUE,
  label text NOT NULL,
  rank  smallint NOT NULL        -- permissions : rank >= 30 pour "éditeur ou plus"
);
INSERT INTO ref.member_roles (id, code, label, rank) VALUES
  (10,'viewer','Viewer',10),
  (20,'designer','Designer',20),
  (30,'editor','Editor',30),
  (40,'admin','Admin',40),
  (50,'owner','Owner',50);

CREATE TABLE ref.log_levels (
  id       smallint PRIMARY KEY,
  code     text NOT NULL UNIQUE,
  label    text NOT NULL,
  severity smallint NOT NULL
);
INSERT INTO ref.log_levels (id, code, label, severity) VALUES
  (10,'debug','Debug',10),(20,'info','Info',20),
  (30,'warning','Warning',30),(40,'error','Error',40);

-- Discriminateurs techniques : jamais filtrés depuis l'interface,
-- aucun attribut associé — un enum suffit.
CREATE TYPE core.credential_kind    AS ENUM ('tracking','api','revalidate','webhook');
CREATE TYPE content.revision_source AS ENUM ('ai','human','import','rollback');
CREATE TYPE content.keyword_role    AS ENUM ('primary','secondary','entity');
CREATE TYPE content.link_kind       AS ENUM ('internal','external');
CREATE TYPE content.media_role      AS ENUM ('cover','inline','thumbnail','og');
CREATE TYPE ai.agent_category       AS ENUM ('research','strategy','creation','review');
CREATE TYPE ai.agent_status         AS ENUM ('active','heuristic','partial','planned','disabled','not_implemented');

-- =====================================================================
-- CORE
-- =====================================================================

CREATE TABLE core.users (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email         citext NOT NULL UNIQUE,
  username      citext UNIQUE,
  password_hash text NOT NULL,                  -- bcrypt (passlib), inchangé
  first_name    text,
  last_name     text,
  avatar_url    text,
  is_active     boolean NOT NULL DEFAULT true,
  is_staff      boolean NOT NULL DEFAULT false,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now(),
  deleted_at    timestamptz
);

CREATE TABLE core.organizations (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name       text NOT NULL,
  slug       citext NOT NULL UNIQUE,
  plan       text NOT NULL DEFAULT 'free',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE core.organization_members (
  organization_id  uuid NOT NULL REFERENCES core.organizations(id) ON DELETE CASCADE,
  user_id          uuid NOT NULL REFERENCES core.users(id) ON DELETE CASCADE,
  role_id          smallint NOT NULL REFERENCES ref.member_roles(id),
  state_id         smallint NOT NULL DEFAULT 0,
  status_reason_id smallint NOT NULL DEFAULT 20,
  created_at       timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, user_id),
  FOREIGN KEY (status_reason_id, state_id)
    REFERENCES ref.membership_status_reasons(id, state_id)
);

CREATE TABLE core.projects (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id  uuid NOT NULL REFERENCES core.organizations(id) ON DELETE RESTRICT,
  name             text NOT NULL,
  slug             citext NOT NULL,
  domain           text,
  locale           text NOT NULL DEFAULT 'fr-FR',
  timezone         text NOT NULL DEFAULT 'Europe/Paris',
  state_id         smallint NOT NULL DEFAULT 0,
  status_reason_id smallint NOT NULL DEFAULT 10,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now(),
  archived_at      timestamptz,
  UNIQUE (organization_id, slug),
  FOREIGN KEY (status_reason_id, state_id)
    REFERENCES ref.project_status_reasons(id, state_id)
);

CREATE TABLE core.project_members (
  project_id       uuid NOT NULL REFERENCES core.projects(id) ON DELETE CASCADE,
  user_id          uuid NOT NULL REFERENCES core.users(id) ON DELETE CASCADE,
  role_id          smallint NOT NULL REFERENCES ref.member_roles(id) DEFAULT 20,
  state_id         smallint NOT NULL DEFAULT 0,
  status_reason_id smallint NOT NULL DEFAULT 20,
  created_at       timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (project_id, user_id),
  FOREIGN KEY (status_reason_id, state_id)
    REFERENCES ref.membership_status_reasons(id, state_id)
);

CREATE TABLE core.editorial_profiles (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id     uuid NOT NULL REFERENCES core.projects(id) ON DELETE CASCADE,
  version        integer NOT NULL,
  is_active      boolean NOT NULL DEFAULT false,
  audience       text,
  tone           text,
  reader_level   text,
  writing_style  text,
  vertical       text,
  word_count_min integer,
  word_count_max integer,
  rules          jsonb NOT NULL DEFAULT '{}'::jsonb,
  constraints    jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_by     uuid REFERENCES core.users(id) ON DELETE SET NULL,
  created_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, version)
);
CREATE UNIQUE INDEX editorial_profiles_one_active
  ON core.editorial_profiles (project_id) WHERE is_active;

CREATE TABLE core.publishing_targets (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id       uuid NOT NULL REFERENCES core.projects(id) ON DELETE CASCADE,
  site_url         text NOT NULL,
  revalidate_url   text,
  is_primary       boolean NOT NULL DEFAULT true,
  last_synced_at   timestamptz,
  last_sync_status text,
  last_sync_error  text,
  created_at       timestamptz NOT NULL DEFAULT now()
);

-- Clés de projet : SHA-256, pas bcrypt.
-- Une clé aléatoire de 32+ octets n'a pas besoin d'un hash lent, et
-- /tracking/* doit rester en O(1) sur chaque événement reçu.
CREATE TABLE core.project_credentials (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id   uuid NOT NULL REFERENCES core.projects(id) ON DELETE CASCADE,
  kind         core.credential_kind NOT NULL,
  label        text NOT NULL,
  token_prefix text NOT NULL,
  token_sha256 bytea NOT NULL,
  last_used_at timestamptz,
  revoked_at   timestamptz,
  created_at   timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, kind, label)
);
CREATE UNIQUE INDEX project_credentials_sha_idx
  ON core.project_credentials (token_sha256) WHERE revoked_at IS NULL;

CREATE TABLE core.invitations (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id  uuid NOT NULL REFERENCES core.projects(id) ON DELETE CASCADE,
  email       citext NOT NULL,
  role_id     smallint NOT NULL REFERENCES ref.member_roles(id) DEFAULT 20,
  token_sha256 bytea NOT NULL,
  invited_by  uuid REFERENCES core.users(id) ON DELETE SET NULL,
  accepted_by uuid REFERENCES core.users(id) ON DELETE SET NULL,
  accepted_at timestamptz,
  expires_at  timestamptz NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX invitations_token_idx ON core.invitations (token_sha256);

CREATE TABLE core.password_reset_tokens (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      uuid NOT NULL REFERENCES core.users(id) ON DELETE CASCADE,
  token_sha256 bytea NOT NULL,
  expires_at   timestamptz NOT NULL,
  used_at      timestamptz,
  created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX password_reset_token_idx ON core.password_reset_tokens (token_sha256);

-- =====================================================================
-- CONTENT
-- =====================================================================

CREATE TABLE content.categories (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id          uuid NOT NULL REFERENCES core.projects(id) ON DELETE CASCADE,
  parent_id           uuid REFERENCES content.categories(id) ON DELETE SET NULL,
  name                text NOT NULL,
  slug                citext NOT NULL,
  description         text,
  color               text,
  priority_score      numeric(5,2),
  monthly_target      integer,
  is_pipeline_enabled boolean NOT NULL DEFAULT true,
  overrides           jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, slug)
);

-- Une idée est un article dont le motif de statut est dans
-- (10 draft, 20 idea_proposed, 30 idea_priority, 200 idea_rejected).
-- sub_niche et rejection_reason sont repris tels quels du modèle actuel
-- (Article.sub_niche, Article.rejection_reason) — absents du brouillon v3
-- initial alors qu'ils sont réellement utilisés.
CREATE TABLE content.articles (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id            uuid NOT NULL REFERENCES core.projects(id) ON DELETE CASCADE,
  category_id           uuid REFERENCES content.categories(id) ON DELETE SET NULL,
  derived_from_id       uuid REFERENCES content.articles(id) ON DELETE SET NULL,
  slug                  citext NOT NULL,
  state_id              smallint NOT NULL DEFAULT 0,
  status_reason_id      smallint NOT NULL DEFAULT 10,
  sub_niche             text,
  rejection_reason      text,
  rejection_note        text,
  search_intent         text,
  content_format        text,
  target_word_count     integer,
  opportunity_score     numeric(5,2),
  priority              smallint NOT NULL DEFAULT 0,
  is_featured           boolean NOT NULL DEFAULT false,
  author_name           text,
  current_revision_id   uuid,
  published_revision_id uuid,
  scheduled_for         timestamptz,
  published_at          timestamptz,
  next_review_at        timestamptz,
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now(),
  archived_at           timestamptz,
  UNIQUE (project_id, slug),
  FOREIGN KEY (status_reason_id, state_id)
    REFERENCES ref.article_status_reasons(id, state_id)
);

CREATE TABLE content.article_revisions (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  article_id           uuid NOT NULL REFERENCES content.articles(id) ON DELETE CASCADE,
  revision_no          integer NOT NULL,
  source               content.revision_source NOT NULL DEFAULT 'ai',
  title                text NOT NULL,
  excerpt              text,
  body                 text,
  blocks               jsonb,
  faq                  jsonb NOT NULL DEFAULT '[]'::jsonb,
  callouts             jsonb NOT NULL DEFAULT '[]'::jsonb,
  word_count           integer NOT NULL DEFAULT 0,
  reading_time_minutes integer,
  created_by           uuid REFERENCES core.users(id) ON DELETE SET NULL,
  created_at           timestamptz NOT NULL DEFAULT now(),
  UNIQUE (article_id, revision_no)
);

ALTER TABLE content.articles
  ADD CONSTRAINT articles_current_revision_fk
    FOREIGN KEY (current_revision_id) REFERENCES content.article_revisions(id) ON DELETE SET NULL,
  ADD CONSTRAINT articles_published_revision_fk
    FOREIGN KEY (published_revision_id) REFERENCES content.article_revisions(id) ON DELETE SET NULL;

-- requires_revision ne s'applique qu'à published (120) et unpublished (130).
-- "scheduled" (110) en a été délibérément exclu — voir le commentaire sur
-- ref.article_status_reasons plus haut.
CREATE OR REPLACE FUNCTION content.enforce_publication_rules() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE needs_revision boolean;
BEGIN
  SELECT requires_revision INTO needs_revision
  FROM ref.article_status_reasons WHERE id = NEW.status_reason_id;

  IF needs_revision AND NEW.published_revision_id IS NULL THEN
    RAISE EXCEPTION 'Status reason % requires a published revision', NEW.status_reason_id;
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER articles_publication_rules
  BEFORE INSERT OR UPDATE OF status_reason_id, published_revision_id ON content.articles
  FOR EACH ROW EXECUTE FUNCTION content.enforce_publication_rules();

CREATE TABLE content.article_seo (
  article_id       uuid PRIMARY KEY REFERENCES content.articles(id) ON DELETE CASCADE,
  meta_title       text,
  meta_description text,
  canonical_url    text,
  structured_data  jsonb,
  updated_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE content.keywords (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES core.projects(id) ON DELETE CASCADE,
  term       citext NOT NULL,
  volume     integer,
  difficulty numeric(5,2),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, term)
);

CREATE TABLE content.article_keywords (
  article_id uuid NOT NULL REFERENCES content.articles(id) ON DELETE CASCADE,
  keyword_id uuid NOT NULL REFERENCES content.keywords(id) ON DELETE CASCADE,
  role       content.keyword_role NOT NULL DEFAULT 'secondary',
  PRIMARY KEY (article_id, keyword_id)
);
CREATE UNIQUE INDEX article_keywords_one_primary
  ON content.article_keywords (article_id) WHERE role = 'primary';

CREATE TABLE content.article_links (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  article_id        uuid NOT NULL REFERENCES content.articles(id) ON DELETE CASCADE,
  kind              content.link_kind NOT NULL,
  target_article_id uuid REFERENCES content.articles(id) ON DELETE SET NULL,
  target_url        text,
  anchor_text       text,
  is_suggested      boolean NOT NULL DEFAULT false,
  CHECK (kind = 'internal' AND target_article_id IS NOT NULL
      OR kind = 'external' AND target_url IS NOT NULL)
);

CREATE TABLE content.media_assets (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES core.projects(id) ON DELETE CASCADE,
  url        text NOT NULL,
  filename   text NOT NULL,
  mime_type  text,
  byte_size  bigint,
  width      integer,
  height     integer,
  alt_text   text,
  caption    text,
  source     text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE content.article_media (
  article_id uuid NOT NULL REFERENCES content.articles(id) ON DELETE CASCADE,
  media_id   uuid NOT NULL REFERENCES content.media_assets(id) ON DELETE CASCADE,
  role       content.media_role NOT NULL DEFAULT 'inline',
  position   smallint NOT NULL DEFAULT 0,
  PRIMARY KEY (article_id, media_id, role)
);

CREATE TABLE content.article_scores (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  article_id        uuid NOT NULL REFERENCES content.articles(id) ON DELETE CASCADE,
  revision_id       uuid REFERENCES content.article_revisions(id) ON DELETE SET NULL,
  seo_score         numeric(5,2),
  readability_score numeric(5,2),
  quality_score     numeric(5,2),
  eeat_score        numeric(5,2),
  geo_score         numeric(5,2),
  global_score      numeric(5,2),
  readiness_status  text,
  issues            jsonb NOT NULL DEFAULT '[]'::jsonb,
  suggestions       jsonb NOT NULL DEFAULT '[]'::jsonb,
  evaluated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE content.article_comments (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  article_id  uuid NOT NULL REFERENCES content.articles(id) ON DELETE CASCADE,
  author_id   uuid REFERENCES core.users(id) ON DELETE SET NULL,
  parent_id   uuid REFERENCES content.article_comments(id) ON DELETE CASCADE,
  body        text NOT NULL,
  quoted_text text,
  resolved_at timestamptz,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);

-- Colonnes kanban personnalisées. Une colonne est SOIT liée à un motif de
-- statut réel (status_reason_id), SOIT une voie totalement libre
-- (custom_key) — cette deuxième forme existe réellement aujourd'hui
-- (app/routers/kanban_columns.py:50 : `status = data.status or
-- f"custom_{label}"`), le v3 initial ne pouvait pas la représenter du
-- tout puisque status_reason_id y était NOT NULL avec FK stricte.
CREATE TABLE content.board_columns (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id       uuid NOT NULL REFERENCES core.projects(id) ON DELETE CASCADE,
  status_reason_id smallint REFERENCES ref.article_status_reasons(id),
  custom_key       citext,
  label            text,
  color            text,
  sort_order       smallint NOT NULL DEFAULT 0,
  is_visible       boolean NOT NULL DEFAULT true,
  CHECK (
    (status_reason_id IS NOT NULL AND custom_key IS NULL) OR
    (status_reason_id IS NULL AND custom_key IS NOT NULL)
  ),
  UNIQUE (project_id, status_reason_id),
  UNIQUE (project_id, custom_key)
);

CREATE TABLE content.callout_templates (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id  uuid NOT NULL REFERENCES core.projects(id) ON DELETE CASCADE,
  slug        citext NOT NULL,
  label       text NOT NULL,
  style       jsonb NOT NULL DEFAULT '{}'::jsonb,
  external_id text,
  created_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, slug)
);

-- =====================================================================
-- AI
-- =====================================================================

CREATE TABLE ai.providers (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code       text NOT NULL UNIQUE,      -- ollama, openrouter, openai, gemini, mistral, mock
  label      text NOT NULL,
  base_url   text,
  is_enabled boolean NOT NULL DEFAULT true
);
-- Catalogue statique, aligné sur core/config.py (DEFAULT_LLM_PROVIDER et
-- les providers réellement supportés par app/services/providers/).
-- Contrairement à v3 initial, ce n'est PAS dérivé des lignes
-- ai_provider_configs existantes : un provider supporté par le code mais
-- jamais configuré par un projet doit quand même exister dans le
-- catalogue (pour être proposé à la config, pas seulement après coup).
INSERT INTO ai.providers (code, label, is_enabled) VALUES
  ('ollama','Ollama',true),
  ('openrouter','OpenRouter',true),
  ('openai','OpenAI',true),
  ('gemini','Gemini',true),
  ('mistral','Mistral',true),
  ('mock','Mock (tests)',true)
ON CONFLICT (code) DO NOTHING;

CREATE TABLE ai.provider_credentials (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  provider_id  uuid NOT NULL REFERENCES ai.providers(id) ON DELETE CASCADE,
  project_id   uuid REFERENCES core.projects(id) ON DELETE CASCADE,
  secret_ref   text NOT NULL,
  last_test_at timestamptz,
  last_test_ok boolean,
  created_at   timestamptz NOT NULL DEFAULT now()
);

-- Catalogue des agents. Rempli et tenu à jour par l'application au
-- démarrage depuis app/services/agents/agent_registry.py (62 AgentDef
-- aujourd'hui) — PAS par ce script SQL. Copier les 62 lignes ici aurait
-- recréé exactement le problème que la refonte cherche à éliminer pour
-- les colonnes *_json : deux endroits qui peuvent diverger. Voir
-- plan-migration-v3.md §2 pour la fonction de synchronisation.
CREATE TABLE ai.agents (
  id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  key                    text NOT NULL UNIQUE,
  label                  text NOT NULL,
  category               ai.agent_category NOT NULL,
  phase                  text NOT NULL,        -- discovery|strategy|writing|seo|quality|final|cost|research
  status                 ai.agent_status NOT NULL DEFAULT 'planned',
  output_json_field      text,                  -- ex-colonne articles.<x>_json que cet agent alimentait
  requires_llm           boolean NOT NULL DEFAULT true,
  requires_search        boolean NOT NULL DEFAULT false,
  sort_order             smallint NOT NULL DEFAULT 0,
  is_visible_in_frontend boolean NOT NULL DEFAULT true
);

CREATE TABLE ai.agent_bindings (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id    uuid NOT NULL REFERENCES ai.agents(id) ON DELETE CASCADE,
  provider_id uuid NOT NULL REFERENCES ai.providers(id) ON DELETE RESTRICT,
  project_id  uuid REFERENCES core.projects(id) ON DELETE CASCADE,
  model       text NOT NULL,
  priority    smallint NOT NULL DEFAULT 0,
  is_enabled  boolean NOT NULL DEFAULT true
);
CREATE UNIQUE INDEX agent_bindings_unique_global
  ON ai.agent_bindings (agent_id, priority) WHERE project_id IS NULL;
CREATE UNIQUE INDEX agent_bindings_unique_project
  ON ai.agent_bindings (agent_id, project_id, priority) WHERE project_id IS NOT NULL;

CREATE TABLE ai.pipelines (
  project_id             uuid PRIMARY KEY REFERENCES core.projects(id) ON DELETE CASCADE,
  is_enabled             boolean NOT NULL DEFAULT false,
  articles_per_week      smallint NOT NULL DEFAULT 5,
  ideas_per_week         smallint NOT NULL DEFAULT 5,
  max_pending_drafts     smallint NOT NULL DEFAULT 10,
  max_parallel_jobs      smallint NOT NULL DEFAULT 2,
  schedule               jsonb NOT NULL DEFAULT '{}'::jsonb,
  quality_mode           text NOT NULL DEFAULT 'quality',
  cost_limit_per_article numeric(10,4),
  paused_until           timestamptz,
  updated_at             timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ai.pipeline_runs (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id       uuid NOT NULL REFERENCES core.projects(id) ON DELETE CASCADE,
  state_id         smallint NOT NULL DEFAULT 0,
  status_reason_id smallint NOT NULL DEFAULT 10,
  ideas_generated  integer NOT NULL DEFAULT 0,
  articles_created integer NOT NULL DEFAULT 0,
  error            text,
  started_at       timestamptz NOT NULL DEFAULT now(),
  finished_at      timestamptz,
  FOREIGN KEY (status_reason_id, state_id) REFERENCES ref.run_status_reasons(id, state_id)
);

-- phase_id : la phase macro du pipeline (idea_prebrief → planning →
-- production → quality → completed), reprise de la vraie colonne
-- Article.workflow_status. status_reason_id reste l'ISSUE de
-- l'exécution (queued/running/succeeded/failed/cancelled) — les deux
-- axes coexistent déjà dans le code actuel, ils coexistent donc ici.
CREATE TABLE ai.workflow_runs (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  article_id       uuid NOT NULL REFERENCES content.articles(id) ON DELETE CASCADE,
  pipeline_run_id  uuid REFERENCES ai.pipeline_runs(id) ON DELETE SET NULL,
  phase_id         smallint REFERENCES ref.workflow_phases(id),
  state_id         smallint NOT NULL DEFAULT 0,
  status_reason_id smallint NOT NULL DEFAULT 10,
  cancel_requested boolean NOT NULL DEFAULT false,
  error            text,
  started_at       timestamptz NOT NULL DEFAULT now(),
  finished_at      timestamptz,
  FOREIGN KEY (status_reason_id, state_id) REFERENCES ref.run_status_reasons(id, state_id)
);

CREATE TABLE ai.workflow_steps (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id           uuid NOT NULL REFERENCES ai.workflow_runs(id) ON DELETE CASCADE,
  agent_id         uuid NOT NULL REFERENCES ai.agents(id) ON DELETE RESTRICT,
  attempt          smallint NOT NULL DEFAULT 1,
  state_id         smallint NOT NULL DEFAULT 0,
  status_reason_id smallint NOT NULL DEFAULT 10,
  error            text,
  started_at       timestamptz,
  finished_at      timestamptz,
  UNIQUE (run_id, agent_id, attempt),
  FOREIGN KEY (status_reason_id, state_id) REFERENCES ref.step_status_reasons(id, state_id)
);

CREATE TABLE ai.artifacts (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  article_id uuid NOT NULL REFERENCES content.articles(id) ON DELETE CASCADE,
  step_id    uuid REFERENCES ai.workflow_steps(id) ON DELETE SET NULL,
  agent_key  text NOT NULL,
  payload    jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX artifacts_article_agent_idx ON ai.artifacts (article_id, agent_key, created_at DESC);
CREATE INDEX artifacts_payload_gin       ON ai.artifacts USING gin (payload jsonb_path_ops);

CREATE TABLE ai.usage_events (
  id                uuid NOT NULL DEFAULT gen_random_uuid(),
  occurred_at       timestamptz NOT NULL DEFAULT now(),
  project_id        uuid,
  article_id        uuid,
  step_id           uuid,
  agent_key         text NOT NULL,
  provider_code     text,
  model             text,
  prompt_tokens     integer,
  completion_tokens integer,
  duration_ms       integer,
  status_reason_id  smallint NOT NULL DEFAULT 30 REFERENCES ref.step_status_reasons(id),
  error_message     text,
  estimated_cost    numeric(12,6),
  actual_cost       numeric(12,6),
  PRIMARY KEY (occurred_at, id)
) PARTITION BY RANGE (occurred_at);

-- =====================================================================
-- ANALYTICS
-- =====================================================================

CREATE TABLE analytics.traffic_events (
  id            uuid NOT NULL DEFAULT gen_random_uuid(),
  occurred_at   timestamptz NOT NULL DEFAULT now(),
  project_id    uuid NOT NULL,
  article_id    uuid,
  path          text NOT NULL,
  referrer_host text,
  country       char(2),
  device        text,
  browser       text,
  visitor_hash  text,
  PRIMARY KEY (occurred_at, id)
) PARTITION BY RANGE (occurred_at);

CREATE TABLE analytics.search_metrics_daily (
  article_id   uuid NOT NULL REFERENCES content.articles(id) ON DELETE CASCADE,
  metric_date  date NOT NULL,
  impressions  integer NOT NULL DEFAULT 0,
  clicks       integer NOT NULL DEFAULT 0,
  ctr          numeric(6,4),
  avg_position numeric(6,2),
  PRIMARY KEY (article_id, metric_date)
);

CREATE TABLE analytics.optimization_recommendations (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id       uuid NOT NULL REFERENCES core.projects(id) ON DELETE CASCADE,
  article_id       uuid REFERENCES content.articles(id) ON DELETE CASCADE,
  type             text NOT NULL,
  priority         smallint NOT NULL DEFAULT 0,
  reason           text NOT NULL,
  suggestion       text NOT NULL,
  state_id         smallint NOT NULL DEFAULT 0,
  status_reason_id smallint NOT NULL DEFAULT 10,
  created_at       timestamptz NOT NULL DEFAULT now(),
  resolved_at      timestamptz,
  FOREIGN KEY (status_reason_id, state_id) REFERENCES ref.run_status_reasons(id, state_id)
);

-- =====================================================================
-- OPS
-- =====================================================================

CREATE TABLE ops.event_logs (
  id          uuid NOT NULL DEFAULT gen_random_uuid(),
  occurred_at timestamptz NOT NULL DEFAULT now(),
  project_id  uuid,
  article_id  uuid,
  actor_id    uuid,
  level_id    smallint NOT NULL REFERENCES ref.log_levels(id) DEFAULT 20,
  scope       text NOT NULL,
  action      text NOT NULL,
  message     text,
  context     jsonb NOT NULL DEFAULT '{}'::jsonb,
  PRIMARY KEY (occurred_at, id)
) PARTITION BY RANGE (occurred_at);

CREATE TABLE ops.notifications (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES core.projects(id) ON DELETE CASCADE,
  user_id    uuid REFERENCES core.users(id) ON DELETE CASCADE,
  type       text NOT NULL DEFAULT 'system',
  level_id   smallint NOT NULL REFERENCES ref.log_levels(id) DEFAULT 20,
  title      text NOT NULL,
  body       text NOT NULL,
  link       text,
  read_at    timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ops.webhooks (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES core.projects(id) ON DELETE CASCADE,
  name       text NOT NULL,
  url        text NOT NULL,
  events     text[] NOT NULL DEFAULT '{}',
  secret_ref text NOT NULL,
  is_enabled boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ops.webhook_deliveries (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  webhook_id   uuid NOT NULL REFERENCES ops.webhooks(id) ON DELETE CASCADE,
  event        text NOT NULL,
  status_code  integer,
  error        text,
  attempt      smallint NOT NULL DEFAULT 1,
  delivered_at timestamptz NOT NULL DEFAULT now()
);

-- =====================================================================
-- PARTITIONS INITIALES
-- =====================================================================
CREATE TABLE ai.usage_events_2026_08 PARTITION OF ai.usage_events
  FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
CREATE TABLE analytics.traffic_events_2026_08 PARTITION OF analytics.traffic_events
  FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
CREATE TABLE ops.event_logs_2026_08 PARTITION OF ops.event_logs
  FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');

-- =====================================================================
-- INDEX
-- =====================================================================
CREATE INDEX projects_org_status_idx     ON core.projects (organization_id, state_id, status_reason_id);
CREATE INDEX categories_project_idx      ON content.categories (project_id);
CREATE INDEX articles_project_status_idx ON content.articles (project_id, state_id, status_reason_id, updated_at DESC);
CREATE INDEX articles_project_cat_idx    ON content.articles (project_id, category_id);
CREATE INDEX articles_scheduled_idx      ON content.articles (scheduled_for) WHERE status_reason_id = 110;
CREATE INDEX revisions_article_idx       ON content.article_revisions (article_id, revision_no DESC);
CREATE INDEX revisions_title_trgm_idx    ON content.article_revisions USING gin (title gin_trgm_ops);
CREATE INDEX scores_article_idx          ON content.article_scores (article_id, evaluated_at DESC);
CREATE INDEX comments_article_open_idx   ON content.article_comments (article_id) WHERE resolved_at IS NULL;
CREATE INDEX workflow_runs_article_idx   ON ai.workflow_runs (article_id, started_at DESC);
CREATE INDEX workflow_steps_run_idx      ON ai.workflow_steps (run_id, status_reason_id);
CREATE INDEX usage_project_time_idx      ON ai.usage_events (project_id, occurred_at DESC);
CREATE INDEX traffic_project_time_idx    ON analytics.traffic_events (project_id, occurred_at DESC);
CREATE INDEX notifications_unread_idx    ON ops.notifications (user_id) WHERE read_at IS NULL;

-- =====================================================================
-- VUES — identifiants ET libellés
-- =====================================================================
CREATE VIEW content.v_articles_current AS
SELECT a.id, a.project_id, a.category_id, a.slug,
       a.state_id,          s.code  AS state_code,  s.label  AS state_label,
       a.status_reason_id,  sr.code AS status_code, sr.label AS status_label,
       sr.color AS status_color,
       r.title, r.excerpt, r.body, r.word_count, r.reading_time_minutes,
       seo.meta_title, seo.meta_description,
       a.published_at, a.updated_at
FROM content.articles a
JOIN ref.states s                     ON s.id  = a.state_id
JOIN ref.article_status_reasons sr    ON sr.id = a.status_reason_id
LEFT JOIN content.article_revisions r ON r.id  = a.current_revision_id
LEFT JOIN content.article_seo seo     ON seo.article_id = a.id;

CREATE VIEW content.v_articles_published AS
SELECT a.id, a.project_id, a.slug,
       r.title, r.excerpt, r.body, r.faq, r.callouts,
       seo.meta_title, seo.meta_description, seo.canonical_url, seo.structured_data,
       a.published_at
FROM content.articles a
JOIN content.article_revisions r  ON r.id = a.published_revision_id
LEFT JOIN content.article_seo seo ON seo.article_id = a.id
WHERE a.status_reason_id = 120;

CREATE VIEW content.v_article_latest_score AS
SELECT DISTINCT ON (article_id) * FROM content.article_scores
ORDER BY article_id, evaluated_at DESC;

-- Colonnes liées à un motif de statut réel, PLUS les voies libres
-- (custom_key), qui n'existaient dans aucune vue du v3 initial.
CREATE VIEW content.v_board_columns AS
SELECT p.id AS project_id,
       sr.id AS status_reason_id, sr.code AS status_code, NULL::citext AS custom_key,
       COALESCE(bc.label, sr.label)           AS label,
       COALESCE(bc.color, sr.color)           AS color,
       COALESCE(bc.sort_order, sr.sort_order) AS sort_order,
       COALESCE(bc.is_visible, sr.is_board_visible) AS is_visible
FROM core.projects p
CROSS JOIN ref.article_status_reasons sr
LEFT JOIN content.board_columns bc ON bc.project_id = p.id AND bc.status_reason_id = sr.id
UNION ALL
SELECT bc.project_id, NULL::smallint, NULL::text, bc.custom_key,
       bc.label, bc.color, bc.sort_order, bc.is_visible
FROM content.board_columns bc
WHERE bc.custom_key IS NOT NULL;

CREATE VIEW core.v_projects AS
SELECT p.*, s.code AS state_code, s.label AS state_label,
       sr.code AS status_code, sr.label AS status_label
FROM core.projects p
JOIN ref.states s                  ON s.id  = p.state_id
JOIN ref.project_status_reasons sr ON sr.id = p.status_reason_id;

-- =====================================================================
-- RLS
-- =====================================================================
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
    CREATE ROLE app_user LOGIN;
  END IF;
END $$;

GRANT USAGE ON SCHEMA ref, core, content, ai, analytics, ops TO app_user;
GRANT SELECT ON ALL TABLES IN SCHEMA ref TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA core, content, ai, analytics, ops TO app_user;

CREATE OR REPLACE FUNCTION core.current_project_id() RETURNS uuid
LANGUAGE sql STABLE AS $$
  SELECT nullif(current_setting('app.project_id', true), '')::uuid;
$$;

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'content.articles','content.categories','content.media_assets','content.keywords',
    'content.callout_templates','content.board_columns','core.editorial_profiles',
    'core.publishing_targets','core.project_credentials','ai.pipeline_runs',
    'ops.notifications','analytics.optimization_recommendations'
  ] LOOP
    EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %s FORCE ROW LEVEL SECURITY', t);
    EXECUTE format($f$CREATE POLICY tenant_isolation ON %s
      USING (project_id = core.current_project_id())
      WITH CHECK (project_id = core.current_project_id())$f$, t);
  END LOOP;
END $$;

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'content.article_revisions','content.article_seo','content.article_scores',
    'content.article_comments','content.article_links','content.article_keywords',
    'content.article_media','ai.workflow_runs','ai.artifacts','analytics.search_metrics_daily'
  ] LOOP
    EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %s FORCE ROW LEVEL SECURITY', t);
    EXECUTE format($f$CREATE POLICY tenant_isolation ON %s
      USING (EXISTS (SELECT 1 FROM content.articles a
                     WHERE a.id = article_id
                       AND a.project_id = core.current_project_id()))$f$, t);
  END LOOP;
END $$;
