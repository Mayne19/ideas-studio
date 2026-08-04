# Plan d'activation RLS — Ideas Studio

> Statut : **NON ACTIVÉ**. Ce document décrit l'état de préparation au 2026-08-04
> et ce qu'il reste à faire avant d'exécuter `db/migration-v3/rls-a-activer-plus-tard.sql`
> en production. Ne pas exécuter ce script tant que les sections « Bloquant »
> ci-dessous ne sont pas cochées.

## 1. Pourquoi RLS, et pourquoi ce n'est pas urgent

L'isolation entre projets existe déjà aujourd'hui, à un seul niveau :
`get_project_member` (et `get_member_for_project`) vérifient l'appartenance,
puis chaque service filtre explicitement par `project_id`. Ça protège
réellement, mais ça repose entièrement sur la discipline du code applicatif —
un `WHERE project_id = ...` oublié dans un nouveau endpoint ne serait détecté
par rien.

RLS ajoute une deuxième couche, au niveau base : même une requête qui oublie
le filtre ne peut pas voir les données d'un autre projet. C'est un vrai gain
de sécurité, mais un gain en **défense en profondeur**, pas la correction
d'une faille active. Vu l'échelle actuelle (peu d'utilisateurs, peu de
projets), rien n'oblige à l'activer dans l'urgence — mieux vaut le faire une
fois, proprement, que par étapes pendant qu'on découvre encore le périmètre.

## 2. Ce qui est déjà en place

- **Rôle applicatif dédié** `app_user` (droits `SELECT/INSERT/UPDATE/DELETE`
  sur `core/content/ai/analytics/ops`, `SELECT` sur `ref`), créé par
  `docs/schema-v3/refonte-schema-v3.sql` (lignes ~963-972). Pas encore
  utilisé : la prod se connecte avec `postgres`.
- **Script RLS prêt** : `db/migration-v3/rls-a-activer-plus-tard.sql`. Utilise
  `FORCE ROW LEVEL SECURITY` (neutralise l'exemption "propriétaire de table"),
  inclut un bloc de désactivation d'urgence en fin de fichier.
- **Mécanisme de contexte côté code** : `app/core/database.py` expose
  `set_current_project_id()` / `current_project_id` (ContextVar), lu par un
  hook SQLAlchemy `after_begin` qui pose `SET LOCAL app.project_id` sur
  chaque transaction Postgres. Ce hook existait déjà avant cette session ;
  il envoyait systématiquement une chaîne vide faute d'appelant.
- **Câblage initial fait** (branche `security/enable-rls-project-isolation`,
  2026-08-04) — voir §3.

## 3. Câblage déjà fait (safe, inerte tant que RLS est éteint)

Vérifié : rien dans le schéma actuel ne lit `app.project_id` avant que
`rls-a-activer-plus-tard.sql` crée `core.current_project_id()` et les
policies. Poser cette variable de session ne change donc aucun comportement
aujourd'hui — c'est un pur prérequis pour plus tard.

| Fichier | Changement |
|---|---|
| `app/dependencies/auth.py` | `get_project_member` et `get_member_for_project` posent `set_current_project_id()` |
| `app/services/worker.py` | `check_scheduled_publications` et `process_writing_queues` restructurés en boucle par projet (ils faisaient une requête cross-projet en un seul `SELECT`, incompatible avec RLS) ; `check_scheduled_idea_generation` pose le contexte à chaque itération |
| `app/services/production_queue.py` | `write_queued_article` (tourne dans un `ThreadPoolExecutor`, session dédiée) pose son propre contexte depuis le `project_id` reçu en paramètre |
| `app/cli.py` | `cmd_daily`, `cmd_generate_ideas`, `cmd_review` posent le contexte (ces commandes ne passent pas par `get_project_member`) |

## 4. Audit complet des 31 routers — ce qui reste à câbler

### Déjà couvert par le §3 (aucun travail supplémentaire)

Tout router qui dépend de `get_project_member` / `require_project_role`
(`activity`, `analytics`, `articles`, `callouts`, `categories`,
`editorial_setup`, `kanban_columns`, `media`, `members`, `notifications`,
`performance`, `pipeline`, `projects`, `recommendations`, `search_console`,
`webhooks`) ou qui appelle `get_member_for_project()` en ligne (`ai_agents`,
`ai_providers`, `articles`, `comments`, `editor`, `seo`, `versions`).

### Bloquant — gaps confirmés, à traiter avant activation

1. **`app/routers/public_api.py` — PRIORITÉ MAXIMALE.** Sert les articles
   publiés au public (`/api/public/projects/{project_id}/articles*`), sans
   authentification. `get_public_articles()` / `get_public_article_by_slug()`
   (`app/services/article_service.py:467,498`) et `get_categories_for_project()`
   (`app/services/category_service.py:45`) requêtent `content.articles` /
   `content.categories` directement par `project_id`, sans jamais poser de
   contexte. **Sans correctif, activer RLS rend tous les sites publics vides
   instantanément.** Correctif : poser `set_current_project_id(project_id)`
   en tout début de chaque route (le `project_id` est déjà dans le path, pas
   besoin d'authentification pour ça — c'est une donnée publique par
   construction).

2. **`app/routers/generation.py` et `app/routers/ideas.py`.** Utilisent un
   helper local `_get_project_or_404(project_id, db)` (`db.get(Project, ...)`
   uniquement) au lieu de `get_project_member`/`get_member_for_project` — ne
   pose pas le contexte. À vérifier en même temps : ce helper ne semble pas
   non plus vérifier l'appartenance au projet (`current_user` récupéré à côté
   mais pas croisé) — à confirmer avant de juste ajouter l'appel de contexte,
   ça peut être un trou d'autorisation indépendant de RLS.

3. **`app/routers/search.py` — `/search`.** Cross-projet **par construction** :
   une seule requête SQL avec `Article.project_id.in_(member_project_ids)`
   sur potentiellement plusieurs projets à la fois. Incompatible avec le
   modèle RLS actuel (un seul `project_id` de contexte à la fois — les
   projets hors contexte seraient silencieusement absents des résultats,
   pas d'erreur). **Décision d'architecture à prendre, pas juste du câblage** :
   soit boucler par projet et fusionner côté application (N requêtes au lieu
   d'une, coût acceptable vu le volume actuel), soit accepter que cette route
   utilise un contexte différent. À trancher avant d'écrire le correctif.

4. **`app/routers/tracking.py` — `/api/traffic/collect`.** Public, sans
   authentification, écrit dans `analytics.traffic_events` en recevant
   `project_id` dans le payload JSON. **Cette table n'est même pas dans la
   liste protégée par `rls-a-activer-plus-tard.sql` aujourd'hui** — à
   décider explicitement : l'ajouter à la liste (et alors il faut que ce
   endpoint public pose son propre contexte, validé par le `tracking_key`
   déjà vérifié par `collect_traffic_event`), ou documenter pourquoi elle en
   reste exclue (la validation par clé fait déjà office de garde-fou
   applicatif). Ne pas laisser ce choix implicite.

5. **`app/routers/webhooks.py` — `trigger_webhooks(db, project_id, event, data)`.**
   Priorité basse : semble toujours appelé depuis un contexte de requête déjà
   authentifié (donc déjà couvert par le §3), mais à vérifier explicitement
   pendant l'implémentation — lister tous les call sites de `trigger_webhooks`.

### À vérifier rapidement (probablement sans risque, non confirmé en détail)

`invitations.py`, `profile.py` : ne touchent a priori que des tables non
protégées par RLS (`core.invitations`, `core.project_members`, `core.users`).
À confirmer par un passage rapide avant l'activation, pas par supposition.

## 5. Prérequis d'infrastructure — bloquants

- [ ] **Rôle de connexion.** `DATABASE_URL` de prod utilise `postgres`
  aujourd'hui. Sur Supabase, ce rôle a l'attribut `BYPASSRLS` — `FORCE ROW
  LEVEL SECURITY` ne le neutralise pas (c'est un mécanisme séparé de
  l'exemption "propriétaire"). **Activer RLS sans changer de rôle ne
  protégerait rien, silencieusement.** Basculer vers `app_user` :
  1. `SELECT rolname, rolcanlogin, rolbypassrls FROM pg_roles WHERE rolname = 'app_user';`
  2. Si pas de mot de passe utilisable : `ALTER ROLE app_user WITH PASSWORD '<fort>';`
  3. Tester en local avec cette chaîne de connexion avant tout déploiement.
- [ ] **Migrations Alembic au démarrage.** `app/main.py` exécute
  `alembic upgrade head` à chaque démarrage (sauf `APP_ENV=test|maintenance`).
  `app_user` n'a que des droits DML (`SELECT/INSERT/UPDATE/DELETE`), pas de
  droits DDL (`CREATE`/`ALTER`). Tant qu'il n'y a que la baseline no-op
  `v3_0001`, ça ne pose pas de problème visible — mais la première vraie
  migration future échouera au démarrage si `DATABASE_URL` utilise `app_user`.
  Décision à prendre : soit une deuxième chaîne de connexion dédiée aux
  migrations (rôle avec droits DDL, utilisée uniquement par
  `run_migrations()`), soit accepter de lancer les migrations manuellement
  hors du cycle de démarrage. À trancher avant la bascule de rôle, pas après.
- [ ] **Test contre un vrai Postgres.** Aucun test automatisé ne couvre ce
  chemin aujourd'hui : `tests/conftest.py` tourne sur SQLite,
  `tests/test_reference_sync.py` se saute lui-même sans
  `V3_TEST_DATABASE_URL`. Avant toute activation en prod, il faut : une base
  Postgres de test (locale ou branche Supabase séparée) avec le schéma v3 +
  RLS appliqués, et un passage manuel complet (login, lister/créer un
  article, générer une idée, servir une page publique) avec `app_user`.

## 6. Procédure d'activation (une fois tout ce qui précède réglé)

1. Fenêtre de maintenance (trafic faible).
2. Sauvegarde : `pg_dump "$DATABASE_URL" -Fc -f backup_avant_rls.dump`.
3. Exécuter `db/migration-v3/rls-a-activer-plus-tard.sql`.
4. Vérification immédiate (incluse en bas du script) :
   ```sql
   SET app.project_id = '<uuid d un projet réel>';
   SELECT count(*) FROM content.articles;   -- doit voir uniquement ce projet
   SET app.project_id = '';
   SELECT count(*) FROM content.articles;   -- doit renvoyer 0
   ```
5. Test bout-en-bout sur l'appli déployée : login, lecture/écriture
   d'articles, génération d'idée, page publique d'un article publié.
6. En cas de problème : bloc de désactivation d'urgence en fin de
   `rls-a-activer-plus-tard.sql` (`DISABLE ROW LEVEL SECURITY` sur toutes les
   tables `core/content/ai/analytics/ops`) — pas destructif, réversible
   immédiatement.

## 7. Prochaine étape concrète

Ce document sert de check-list. La suite logique (pas commencée) : traiter
le §4 point par point (en commençant par `public_api.py`, le plus critique),
puis le §5. Une fois les deux entièrement cochés, revenir au §6.
