# KNOWN_ISSUES.md — Ideas Studio

> Liste des problèmes connus, de leur priorité, et de leur état.  
> Mettre à jour automatiquement : ajouter à la découverte, mettre à jour à la résolution.  
> Ne jamais supprimer un problème résolu — marquer `[RÉSOLU]` avec la date.

---

## Légende priorités

| Priorité | Description |
|---|---|
| 🔴 CRITIQUE | Bloque la production ou cause une perte de données |
| 🟠 HAUTE | Impacte fortement l'expérience utilisateur |
| 🟡 MOYENNE | Fonctionnalité dégradée mais contournable |
| 🟢 BASSE | Cosmétique, optimisation ou confort |

---

## Problèmes ouverts

### [KI-001] — Tests E2E non couverts (zéro spec au démarrage du projet)

- **Priorité** : 🟠 HAUTE
- **Description** : Aucun test end-to-end n'existe à date. L'infrastructure Playwright est installée mais les specs sont minimaux (auth uniquement).
- **Impact** : Impossible de détecter automatiquement les régressions UI/UX lors des modifications frontend
- **Fichiers concernés** : `tests/e2e/specs/`
- **Solution envisagée** : Écrire progressivement les specs couvrant les parcours critiques : login, création projet, création article, éditeur, publication
- **État** : Ouvert — infrastructure prête, specs à écrire
- **Date découverte** : 2026-06-26

---

### [KI-002] — Firefox et WebKit non disponibles pour les tests Playwright

- **Priorité** : 🟡 MOYENNE
- **Description** : L'installation des navigateurs Firefox et WebKit échoue faute de dépendances système (`sudo` requis). Seul Chromium est disponible.
- **Impact** : Tests cross-browser impossibles localement
- **Fichiers concernés** : `tests/e2e/playwright.config.ts`
- **Solution envisagée** : En CI (GitHub Actions), utiliser `playwright install --with-deps` avec des droits root. En local, utiliser `sudo playwright install-deps`.
- **État** : Ouvert — Chromium suffit pour le développement local
- **Date découverte** : 2026-06-26

---

### [KI-003] — Serena MCP non installé (outil de navigation codebase)

- **Priorité** : 🟡 MOYENNE
- **Description** : Serena (outil de navigation intelligente de codebase via MCP) n'est pas disponible sous forme de package npm ou pip. Nécessite une installation depuis GitHub via uvx ou pip depuis le repo source.
- **Impact** : Navigation codebase moins rapide pour les refactorings complexes
- **Fichiers concernés** : `.claude/settings.json`
- **Solution envisagée** : Installer via `pip install git+https://github.com/oraios/serena` ou via uvx quand le package sera publié
- **État** : Ouvert — alternatives disponibles (filesystem MCP + Bash grep)
- **Date découverte** : 2026-06-26

---

### [KI-004] — Pas de validation côté frontend pour certains formulaires

- **Priorité** : 🟡 MOYENNE
- **Description** : Certains formulaires (ex : settings projet, config providers IA) délèguent entièrement la validation au backend sans feedback immédiat côté client.
- **Impact** : UX dégradée — l'utilisateur attend un round-trip réseau avant de voir l'erreur
- **Fichiers concernés** : `frontend/src/pages/projects/settings/`
- **Solution envisagée** : Ajouter validation Zod ou validation native HTML5 sur les formulaires critiques
- **État** : Ouvert — à adresser lors de l'audit UX
- **Date découverte** : 2026-06-26

---

### [KI-005] — Gestion du mode offline absente

- **Priorité** : 🟢 BASSE
- **Description** : L'autosave de l'éditeur dépend entièrement de la connectivité réseau. En cas de perte de connexion, les modifications non sauvegardées sont perdues.
- **Impact** : Risque de perte de contenu sur connexion instable
- **Fichiers concernés** : `frontend/src/pages/projects/editor/ArticleEditorPage.tsx`
- **Solution envisagée** : Couche localStorage en fallback si le POST autosave échoue — voir DEC-006
- **État** : Ouvert — non prioritaire pour la V1
- **Date découverte** : 2026-06-26

---

### [KI-006] — Migrations SQLite vs PostgreSQL : différences de comportement non testées

- **Priorité** : 🟠 HAUTE
- **Description** : Les tests s'exécutent sur SQLite mais la production tourne sur PostgreSQL. Certains comportements diffèrent (JSONB, ILIKE, types booléens, auto-increment).
- **Impact** : Risque de bug en production non détectable par les tests locaux
- **Fichiers concernés** : `tests/conftest.py`, `alembic/versions/`
- **Solution envisagée** : Configurer un job CI qui exécute les tests sur PostgreSQL ; ou utiliser un PostgreSQL local pour les tests de staging
- **État** : Ouvert — risque accepté en V1, à traiter avant montée en charge
- **Date découverte** : 2026-06-26

---

### [KI-007] — Refresh token absent — sessions de 24h max

- **Priorité** : 🟡 MOYENNE
- **Description** : L'authentification n'utilise que des access tokens de 24h sans refresh. Les utilisateurs doivent se reconnecter quotidiennement.
- **Impact** : Légère friction pour les utilisateurs actifs quotidiens
- **Fichiers concernés** : `app/routers/auth.py`, `app/core/security.py`
- **Solution envisagée** : Implémenter un refresh token endpoint — voir DEC-007
- **État** : Ouvert — acceptable en V1
- **Date découverte** : 2026-06-26

---

### [KI-008] — uvx non dans le PATH par défaut (nécessite export PATH)

- **Priorité** : 🟡 MOYENNE
- **Description** : `uvx` est installé dans `/home/mluca/.local/bin/` mais ce chemin n'est pas dans le PATH par défaut du shell. Les MCP servers Git et SQLite utilisent le chemin absolu dans `.claude/settings.json`, ce qui fonctionne, mais `uvx` en ligne de commande directe nécessite `export PATH="$HOME/.local/bin:$PATH"`.
- **Impact** : `uvx` inaccessible directement en terminal sans configuration du PATH
- **Fichiers concernés** : `.claude/settings.json` (utilise le chemin absolu — OK), shell profile
- **Solution envisagée** : Ajouter `export PATH="$HOME/.local/bin:$PATH"` dans `~/.bashrc` ou `~/.zshrc`
- **État** : Partiellement résolu — MCP settings utilisent le chemin absolu
- **Date découverte** : 2026-06-26

---

## Problèmes résolus

### [KI-RES-001] — URL postgres:// incompatible avec SQLAlchemy → [RÉSOLU 2026-06]

- **Solution** : Normalisation automatique dans `Settings.database_url` → voir LL-001

### [KI-RES-002] — Revalidation blog sans secret en header → [RÉSOLU 2026-06]

- **Solution** : Secret envoyé en header `x-revalidate-secret` → voir LL-004

### [KI-RES-003] — Erreurs revalidation remontées dans canal SEO éditeur → [RÉSOLU 2026-06]

- **Solution** : Séparation des canaux d'erreur réseau vs SEO → voir LL-005
