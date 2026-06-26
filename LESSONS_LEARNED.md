# LESSONS_LEARNED.md — Ideas Studio

> Journal des erreurs importantes rencontrées et des bonnes pratiques qui en découlent.  
> **Ne jamais supprimer une entrée.**  
> Consulter ce fichier avant toute modification importante.

---

## Format d'entrée

```
### [LL-XXX] — Titre court
- **Date** : YYYY-MM-DD
- **Contexte** : Où et pourquoi cette erreur a eu lieu
- **Cause** : La cause racine
- **Symptômes** : Ce qui était observable
- **Solution** : Comment c'a été résolu
- **Fichiers concernés** : liste
- **Impacts** : Ce qui a été affecté
- **Bonne pratique** : La règle à appliquer maintenant
- **Comment éviter** : Étapes concrètes pour ne pas reproduire
```

---

## Erreurs rencontrées

### [LL-001] — Migrations Alembic échouant au démarrage en production

- **Date** : 2026-06 (Jour 1 du projet)
- **Contexte** : Déploiement Render — le backend démarrait mais les migrations Alembic bloquaient l'app
- **Cause** : `postgres://` URL Render incompatible avec SQLAlchemy qui nécessite `postgresql://`
- **Symptômes** : `OperationalError: could not connect to server` au démarrage, app inaccessible
- **Solution** : Ajout d'un correctif automatique dans `app/core/config.py` : `database_url` normalise `postgres://` → `postgresql://`
- **Fichiers concernés** : `app/core/config.py` (property `database_url`)
- **Impacts** : App inaccessible jusqu'à correction, migrations non appliquées
- **Bonne pratique** : Toujours normaliser les URLs PostgreSQL au niveau de la config
- **Comment éviter** : Vérifier la property `database_url` dans `Settings` avant tout déploiement ; tester les migrations sur une vraie base PostgreSQL en staging

---

### [LL-002] — Tests non isolés partageant la même base de données

- **Date** : 2026-06 (Jour 2)
- **Contexte** : Tests pytest se polluant mutuellement, ordre d'exécution influençant les résultats
- **Cause** : Base SQLite partagée entre tests sans isolation par test
- **Symptômes** : Tests passant seuls mais échouant ensemble, flakiness selon l'ordre de lancement
- **Solution** : `conftest.py` avec fixture `reset_db(tmp_path)` — chaque test utilise une base temporaire fresh dans `tmp_path`
- **Fichiers concernés** : `tests/conftest.py`
- **Impacts** : Tests instables, faux positifs/négatifs
- **Bonne pratique** : Toujours utiliser `tmp_path` de pytest pour isoler les bases de test
- **Comment éviter** : Ne jamais utiliser une base partagée entre tests ; chaque `reset_db` fixture doit créer une DB unique

---

### [LL-003] — Clé secrète JWT générée dynamiquement → sessions invalidées au redémarrage

- **Date** : 2026-06 (Jour 1)
- **Contexte** : `SECRET_KEY` avec `secrets.token_urlsafe(48)` comme valeur par défaut dans `Settings`
- **Cause** : Valeur par défaut regénérée à chaque démarrage si `SECRET_KEY` non définie dans `.env`
- **Symptômes** : Tous les tokens JWT invalidés à chaque redémarrage du backend
- **Solution** : Définir une `SECRET_KEY` fixe dans `.env` pour le développement ; en production, variable d'environnement Render obligatoire
- **Fichiers concernés** : `app/core/config.py`, `.env`
- **Impacts** : Déconnexion forcée de tous les utilisateurs au redémarrage
- **Bonne pratique** : `SECRET_KEY` doit être une valeur fixe persistante — jamais générée dynamiquement en runtime
- **Comment éviter** : Vérifier `.env` avant démarrage ; `.env.example` doit indiquer que `SECRET_KEY=change-me` est une valeur temporaire à remplacer

---

### [LL-004] — Revalidation CMS échouant silencieusement sans secret en header

- **Date** : 2026-06 (Jour 6)
- **Contexte** : Route de revalidation du blog Next.js externe appelée sans le secret requis
- **Cause** : Secret de revalidation envoyé en query param au lieu du header `x-revalidate-secret`
- **Symptômes** : Revalidation retournant 401 sans log d'erreur visible côté Studio
- **Solution** : Migration vers envoi du secret en header HTTP (`x-revalidate-secret`)
- **Fichiers concernés** : `app/services/publication_revalidation_service.py`
- **Impacts** : Pages publiées non revalidées, cache CDN non invalidé
- **Bonne pratique** : Toujours envoyer les secrets d'API dans les headers HTTP, jamais en query params
- **Comment éviter** : Tester la revalidation après chaque modification du service en vérifiant la réponse du blog

---

### [LL-005] — Audit SEO de revalidation remontant des faux positifs en éditeur

- **Date** : 2026-06 (Jour 6)
- **Contexte** : Les erreurs de revalidation apparaissaient comme des erreurs SEO dans le panel éditeur
- **Cause** : Mauvaise séparation entre les erreurs réseau de revalidation et les erreurs métier SEO
- **Symptômes** : Messages d'erreur SEO trompeurs dans l'interface éditeur lors de la publication
- **Solution** : Filtrage des erreurs de revalidation hors du canal d'erreur SEO ; gestion séparée dans les editor actions
- **Fichiers concernés** : `app/routers/editor.py`, frontend editor panels
- **Impacts** : Confusion utilisateur, alertes SEO inexactes
- **Bonne pratique** : Séparer clairement les canaux d'erreur — erreur réseau ≠ erreur métier ≠ warning SEO
- **Comment éviter** : Chaque type d'erreur doit avoir son propre handler et sa propre UI de reporting

---

### [LL-006] — Migrations Alembic non numérotées causant des conflits d'ordre

- **Date** : 2026-06 (Jour 4-5)
- **Contexte** : Deux migrations créées en parallèle sans numéro de séquence explicite
- **Cause** : Alembic génère des révisions par hash UUID — sans convention de nommage, l'ordre devient illisible
- **Symptômes** : `alembic history` difficile à lire, risque de mauvais ordre d'application
- **Solution** : Convention de nommage `NNN_description.py` pour les nouvelles migrations
- **Fichiers concernés** : `alembic/versions/`
- **Impacts** : Lisibilité dégradée de l'historique des migrations
- **Bonne pratique** : Nommer les migrations `NNN_verb_description.py` (ex : `029_add_user_settings.py`)
- **Comment éviter** : Utiliser `--rev-id NNN` lors de la création : `alembic revision --autogenerate -m "description" --rev-id 029`

---

## Bonnes pratiques générales consolidées

1. **Tests** : Toujours utiliser `tmp_path` de pytest pour les bases de test (voir LL-002)
2. **Auth** : `SECRET_KEY` fixe dans `.env`, jamais dynamique (voir LL-003)
3. **Migrations** : Nommer avec préfixe numérique séquentiel (voir LL-006)
4. **Secrets** : Toujours dans les headers HTTP, jamais en query params (voir LL-004)
5. **DB** : Normaliser les URLs PostgreSQL dès la config (voir LL-001)
6. **Erreurs** : Un canal d'erreur par type — réseau, métier, UX (voir LL-005)
7. **Logique** : Services uniquement dans `app/services/`, jamais dans les routers
8. **Clés API** : Ne jamais exposer une clé API dans les réponses JSON — toujours masquer côté backend
