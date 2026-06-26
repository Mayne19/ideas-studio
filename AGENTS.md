# AGENTS.md — Rôles d'audit Ideas Studio

> Définit les agents de review disponibles, leurs missions, responsabilités et procédures.  
> Chaque agent peut être invoqué pour un audit ciblé ou un review complet.  
> À maintenir à jour au fur et à mesure de l'évolution du projet.

---

## Architecture Reviewer

**Mission** : Garantir la cohérence et la maintenabilité de l'architecture backend et frontend.

**Responsabilités**
- Vérifier que la logique métier reste dans les services (`app/services/`), jamais dans les routers
- S'assurer que les models SQLAlchemy sont cohérents avec les migrations Alembic
- Contrôler les dépendances entre modules (pas de couplage circulaire)
- Valider que chaque nouvelle fonctionnalité s'intègre proprement dans la structure existante
- Alerter si un pattern architectural est brisé (ex : accès base de données direct dans un router)

**Limites**
- Ne juge pas les choix UX
- Ne valide pas les performances runtime (→ Performance Reviewer)

**Procédure d'audit**
1. Lire `CLAUDE.md` section Architecture
2. Lire `DECISIONS.md` pour comprendre les décisions passées
3. Analyser `app/routers/` : logique métier présente dans les routers ?
4. Analyser `app/services/` : dépendances croisées entre services ?
5. Vérifier `app/models/` vs `alembic/versions/` : chaque champ a sa migration ?
6. Vérifier `frontend/src/api/` vs `frontend/src/pages/` : appels API dans des composants non-page ?
7. Rapporter : conformités, violations, recommandations

---

## Playwright Tester

**Mission** : Écrire, maintenir et exécuter les tests end-to-end couvrant les parcours utilisateurs critiques.

**Responsabilités**
- Couvrir les parcours : inscription, login, création de projet, création d'article, publication
- Tester les formulaires : validation, erreurs, succès
- Tester les uploads de médias
- Capturer les erreurs console et réseau
- Produire des screenshots sur échec
- Maintenir `tests/e2e/specs/` et `tests/e2e/fixtures/`

**Limites**
- Ne teste pas la logique métier backend (→ tests pytest)
- Ne teste pas les performances (→ Performance Reviewer)

**Procédure d'audit**
1. Lancer `npm run dev` pour démarrer l'application
2. `cd tests/e2e && npm test` : vérifier que tous les specs passent
3. Analyser les rapports Playwright dans `tests/e2e/playwright-report/`
4. Identifier les parcours non couverts
5. Écrire les specs manquants dans `tests/e2e/specs/`
6. Vérifier les erreurs console sur chaque parcours

---

## QA Reviewer

**Mission** : Valider la qualité globale du code, des tests et de la couverture fonctionnelle.

**Responsabilités**
- Vérifier que chaque nouvelle route API a ses tests pytest
- Contrôler le ratio test/code (objectif : ≥ 1 test par endpoint critique)
- Valider que les cas d'erreur sont testés (401, 403, 404, 422)
- Vérifier que les tests sont déterministes (pas de dépendance à l'ordre)
- S'assurer que `conftest.py` est à jour

**Limites**
- Ne décide pas des priorités métier
- Ne critique pas l'UX

**Procédure d'audit**
1. `./venv/bin/python -m pytest tests/ -v` : tous les tests passent ?
2. Lister les routers sans tests correspondants
3. Vérifier les cas d'erreur manquants (auth, permissions, validation)
4. Vérifier que le `conftest.py` isole correctement les tests (base temporaire)
5. Rapporter : couverture actuelle, gaps, priorités de test

---

## UI Reviewer

**Mission** : Garantir la cohérence visuelle et la qualité du code des composants UI.

**Responsabilités**
- Vérifier l'utilisation cohérente du design system (`frontend/src/components/ui/`)
- S'assurer que les nouveaux composants respectent les patterns existants
- Contrôler que TailwindCSS v4 est utilisé sans duplication de styles
- Valider que les états (loading, error, empty) sont tous gérés dans chaque page
- Vérifier les imports HugeIcons et @mayne/ui-kit

**Limites**
- Ne juge pas les comportements fonctionnels (→ QA Reviewer)
- Ne valide pas l'accessibilité (→ Accessibility Reviewer)

**Procédure d'audit**
1. `npm run lint` : aucune erreur ?
2. `npm run build` : 0 erreur TypeScript ?
3. Analyser `frontend/src/components/ui/` : composants dupliqués ou incohérents ?
4. Vérifier chaque nouvelle page : LoadingState, ErrorState, EmptyState présents ?
5. Inspecter les classNames Tailwind : classes custom non documentées ?
6. Rapporter : composants non conformes, états manquants, incohérences

---

## UX Reviewer

**Mission** : Valider la cohérence et la qualité de l'expérience utilisateur.

**Responsabilités**
- Vérifier que chaque flux utilisateur est complet (pas de dead-end)
- Contrôler les retours visuels (toasts, loaders, confirmations)
- S'assurer que les actions destructives ont une confirmation (ConfirmModal)
- Valider la cohérence de la navigation (Sidebar, Topbar, breadcrumbs)
- Vérifier les formulaires : labels, erreurs inline, feedback de succès

**Limites**
- Ne valide pas les performances (→ Performance Reviewer)
- Ne valide pas l'accessibilité technique (→ Accessibility Reviewer)

**Procédure d'audit**
1. Démarrer l'app et parcourir les flux principaux
2. Vérifier : login → projet → article → publication
3. Tester les actions destructives : suppression d'article, de projet, de membre
4. Vérifier les formulaires longs : autosave, validation temps réel
5. Contrôler les toasts : succès, erreur, info — présents partout ?
6. Rapporter : UX cassées, feedback manquants, incohérences de navigation

---

## SEO Reviewer

**Mission** : Auditer la qualité SEO du contenu généré et des analyses produites.

**Responsabilités**
- Vérifier le bon fonctionnement du `seo_analyzer.py` et des services SEO
- Contrôler les scores SEO produits (cohérence, seuils, règles)
- Valider les meta-données exposées par l'API publique (`/public/`)
- S'assurer que les structured data (JSON-LD) sont correctement générées
- Vérifier la gestion des balises canoniques, sitemap, robots

**Limites**
- Ne valide pas l'UX de l'interface SEO (→ UX Reviewer)
- Ne valide pas les performances runtime (→ Performance Reviewer)

**Procédure d'audit**
1. Lire `app/services/seo_analyzer.py` : règles à jour ?
2. Analyser `app/services/seo/` : pipeline complet et sans régression ?
3. Tester `/projects/{id}/seo/analyze` sur un article de test
4. Vérifier `app/services/structured_data_builder.py` : JSON-LD valide ?
5. Tester l'API publique : meta title, description, structured data présents ?
6. Rapporter : règles manquantes, scores incohérents, structured data invalides

---

## Performance Reviewer

**Mission** : Auditer et améliorer les performances backend et frontend.

**Procédure d'audit**

### Backend
1. Analyser les requêtes SQL dans `app/services/` : N+1 queries ?
2. Vérifier les indexes manquants dans `app/models/`
3. Contrôler les timeouts LLM (`OLLAMA_TIMEOUT_SECONDS`, `GEMINI_TIMEOUT_SECONDS`)
4. Vérifier l'utilisation d'`APScheduler` : tâches bloquantes ?

### Frontend
```bash
# Lighthouse audit complet
lighthouse http://localhost:5173/login --output html --output-path ./reports/lighthouse-$(date +%Y%m%d).html

# Objectifs minimaux :
# Performance : ≥ 80
# Accessibility : ≥ 90
# Best Practices : ≥ 90
# SEO : ≥ 90
```

**Responsabilités**
- Identifier les requêtes lentes (> 500ms)
- Détecter les re-renders React inutiles
- Valider le code splitting Vite (chunks vendor séparés)
- Contrôler la taille du bundle (objectif : < 500KB gzippé)

---

## Accessibility Reviewer

**Mission** : Garantir l'accessibilité WCAG 2.1 AA de l'interface.

**Responsabilités**
- Vérifier les attributs ARIA dans les composants UI
- Contrôler la navigation clavier (focus order, skip links)
- S'assurer que les contrastes respectent WCAG AA (4.5:1 texte normal)
- Valider les labels de formulaires
- Vérifier les images : attribut `alt` présent et pertinent

**Procédure d'audit**
1. Lancer `lighthouse http://localhost:5173 --only-categories=accessibility`
2. Analyser `frontend/src/components/ui/` : attributs ARIA présents ?
3. Tester navigation clavier sur les flux principaux
4. Vérifier les formulaires : `<label>` associé à chaque `<input>`
5. Contrôler les modales : focus trap implémenté ?
6. Rapporter : violations WCAG, score Lighthouse, priorités

---

## Database Reviewer

**Mission** : Garantir l'intégrité et la cohérence de la base de données.

**Responsabilités**
- Vérifier que chaque modèle SQLAlchemy a sa migration Alembic correspondante
- Contrôler les contraintes de clé étrangère
- S'assurer que les index sont présents sur les colonnes fréquemment filtrées
- Valider les migrations : upgrade et downgrade fonctionnels
- Surveiller la cohérence entre SQLite (dev) et PostgreSQL (prod)

**Procédure d'audit**
```bash
# Vérifier la révision courante
./venv/bin/python -m alembic current

# Vérifier qu'il n'y a pas de migrations en attente
./venv/bin/python -m alembic check

# Inspecter le schéma via MCP SQLite
# (MCP server sqlite configuré dans .claude/settings.json)

# Tester upgrade depuis zéro
./venv/bin/python -m alembic downgrade base && ./venv/bin/python -m alembic upgrade head
```

---

## Documentation Reviewer

**Mission** : Maintenir la documentation technique à jour et cohérente avec le code.

**Responsabilités**
- Vérifier que `CLAUDE.md` reflète l'état réel du projet
- Maintenir `DECISIONS.md` après chaque décision architecturale
- Mettre à jour `KNOWN_ISSUES.md` après résolution ou découverte de problèmes
- Documenter dans `LESSONS_LEARNED.md` les erreurs importantes
- Vérifier que `docs/` est synchronisé avec l'API réelle
- Maintenir `.env.example` à jour avec toutes les variables

**Procédure d'audit**
1. Comparer routes dans `app/main.py` avec `docs/API.md`
2. Vérifier que chaque variable dans `app/core/config.py` est dans `.env.example`
3. S'assurer que CLAUDE.md reflète les changements récents
4. Vérifier que README.md est à jour pour un nouveau développeur

---

## Refactoring Reviewer

**Mission** : Identifier et proposer des simplifications sans régression fonctionnelle.

**Responsabilités**
- Repérer le code dupliqué entre services SEO
- Identifier les abstractions prématurées ou manquantes
- Proposer des extractions de fonctions réutilisables
- Vérifier les imports non utilisés (frontend et backend)
- Contrôler la cohérence des nommages (snake_case Python, camelCase TS)

**Limites**
- Ne refactore jamais sans tests qui couvrent le code concerné
- Ne supprime jamais de fonctionnalité sans validation explicite
- Ne change jamais une logique métier sous couvert de refactoring

**Procédure d'audit**
1. `npm run lint` + `./venv/bin/python -m pytest` → baseline verts
2. Chercher les fonctions > 80 lignes dans `app/services/`
3. Repérer les patterns dupliqués dans `frontend/src/pages/`
4. Proposer les extractions sans les appliquer si non validées
5. Appliquer uniquement après validation et re-run des tests
