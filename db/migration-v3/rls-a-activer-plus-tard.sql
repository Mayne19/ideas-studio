-- =====================================================================
-- RLS — À N'EXÉCUTER QU'APRÈS avoir modifié app/core/db.py
--
-- Tant que le backend ne pose pas app.project_id au début de chaque
-- transaction, ce script rend l'application AVEUGLE : toutes les
-- requêtes renvoient 0 ligne. Ce n'est pas un bug, c'est la RLS qui
-- fonctionne — mais l'app ne peut pas travailler dans cet état.
--
-- Prérequis :
--   1. app/core/db.py exécute SET LOCAL app.project_id à chaque
--      transaction (voir RUNBOOK §A2)
--   2. Les jobs APScheduler le posent aussi, explicitement
--   3. Testé en local avec le rôle app_user
--
-- Note Supabase : le rôle "postgres" est propriétaire des tables et
-- contourne la RLS. FORCE ROW LEVEL SECURITY corrige ce point, mais
-- vérifiez d'abord avec quel rôle votre backend se connecte réellement.
-- =====================================================================

CREATE OR REPLACE FUNCTION core.current_project_id() RETURNS uuid
LANGUAGE sql STABLE AS $$
  SELECT nullif(current_setting('app.project_id', true), '')::uuid;
$$;

-- Tables portant directement project_id
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

-- Tables filles : la politique remonte à l'article parent
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

-- ---------------------------------------------------------------------
-- Vérification : à exécuter juste après
-- ---------------------------------------------------------------------
-- SET app.project_id = '<uuid d un projet>';
-- SELECT count(*) FROM content.articles;   -- ne doit voir que ce projet
-- SET app.project_id = '';
-- SELECT count(*) FROM content.articles;   -- doit renvoyer 0

-- ---------------------------------------------------------------------
-- DÉSACTIVATION D'URGENCE — si l'application ne voit plus rien
-- ---------------------------------------------------------------------
-- DO $$
-- DECLARE t text;
-- BEGIN
--   FOR t IN SELECT schemaname||'.'||tablename FROM pg_tables
--            WHERE schemaname IN ('core','content','ai','analytics','ops')
--   LOOP
--     EXECUTE format('ALTER TABLE %s DISABLE ROW LEVEL SECURITY', t);
--   END LOOP;
-- END $$;
