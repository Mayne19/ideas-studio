# DECISIONS.md — Décisions architecturales Ideas Studio

> Toute décision importante concernant l'architecture, l'UX, les workflows, la sécurité ou les performances doit être enregistrée ici.  
> Format : problème → options étudiées → décision → justification → conséquences.

---

## Format d'entrée

```
### [DEC-XXX] — Titre de la décision
- **Date** : YYYY-MM-DD
- **Domaine** : architecture | UX | sécurité | performance | SEO | workflow | logique métier
- **Problème** : Description du problème ou du besoin
- **Options étudiées** :
  - Option A : ...
  - Option B : ...
- **Décision retenue** : Option X
- **Justification** : Pourquoi cette option
- **Conséquences** : Impacts positifs et négatifs
- **Révisable** : Oui/Non — conditions
```

---

## Décisions enregistrées

### [DEC-001] — SQLite en développement, PostgreSQL en production

- **Date** : 2026-06 (Jour 1)
- **Domaine** : architecture
- **Problème** : Quel moteur de base de données utiliser pour un démarrage rapide sans infrastructure ?
- **Options étudiées** :
  - Option A : PostgreSQL partout (dev + prod)
  - Option B : SQLite dev, PostgreSQL prod
  - Option C : SQLite partout
- **Décision retenue** : Option B — SQLite dev, PostgreSQL prod
- **Justification** : SQLite ne nécessite aucune installation, parfait pour le développement local rapide. PostgreSQL en prod garantit la fiabilité, les types avancés et la compatibilité Render. SQLAlchemy abstrait la différence.
- **Conséquences** :
  - (+) Démarrage dev immédiat, zéro infrastructure locale
  - (+) Render PostgreSQL gratuit disponible
  - (-) Comportements légèrement différents entre SQLite et PG (ex : types JSON, case-sensitivity)
  - (-) Nécessite de tester les migrations sur PostgreSQL en staging avant prod
- **Révisable** : Non — architecture de base établie

---

### [DEC-002] — Migrations Alembic exécutées automatiquement au démarrage

- **Date** : 2026-06 (Jour 1)
- **Domaine** : architecture
- **Problème** : Comment gérer les migrations en production sans étape manuelle ?
- **Options étudiées** :
  - Option A : Migrations manuelles via CLI avant chaque déploiement
  - Option B : Migrations automatiques dans `@app.on_event("startup")`
- **Décision retenue** : Option B — auto-migrations au démarrage
- **Justification** : Simplifie drastiquement le déploiement Render (pas de pre-deploy script à gérer). Chaque démarrage est auto-suffisant.
- **Conséquences** :
  - (+) Déploiement zero-touch — Render démarre et migre automatiquement
  - (+) Impossible d'oublier une migration
  - (-) Un bug de migration bloque le démarrage complet de l'app
  - (-) Migration non testée = downtime en production
- **Révisable** : Oui — si le nombre de migrations devient trop grand et ralentit le démarrage

---

### [DEC-003] — Multi-provider LLM avec routage automatique

- **Date** : 2026-06 (Jour 3)
- **Domaine** : architecture
- **Problème** : Comment supporter plusieurs providers IA sans coupler le code à un seul ?
- **Options étudiées** :
  - Option A : Un seul provider (OpenAI uniquement)
  - Option B : Abstraction LangChain
  - Option C : Interface maison `LLMProvider` + registry des providers
- **Décision retenue** : Option C — interface maison
- **Justification** : LangChain est trop lourd pour nos besoins, introduit trop de dépendances. L'interface maison (`llm_provider.py`) est légère, testable avec mock, et permet d'ajouter des providers sans refactoring.
- **Conséquences** :
  - (+) Indépendance totale vis-à-vis des SDKs IA
  - (+) Mock provider disponible en tests (pas d'appels réels)
  - (+) Routage `auto` : essaie OpenRouter → Ollama → OpenAI en cascade
  - (-) Maintenance de l'interface maison lors des évolutions API providers
- **Révisable** : Non pour le principe ; Oui pour ajouter des providers

---

### [DEC-004] — Scores validés par gate multi-critères avant publication

- **Date** : 2026-06 (Jour 5)
- **Domaine** : logique métier
- **Problème** : Comment garantir la qualité minimale d'un article avant publication ?
- **Options étudiées** :
  - Option A : Publication libre sans validation
  - Option B : Validation manuelle par un éditeur
  - Option C : Gate automatique multi-scores (SEO, qualité, geo, originalité, fact-check)
- **Décision retenue** : Option C — gate automatique, contournable manuellement (bulk publish sans gate)
- **Justification** : Un gate automatique maintient la qualité sans bloquer les éditeurs en urgence. La route `bulk publish` sans gate offre une soupape pour les cas où la validation bloque à tort.
- **Conséquences** :
  - (+) Standard qualité minimum garanti automatiquement
  - (+) Scores tracés (SEO, qualité, geo, originalité) pour chaque article publié
  - (-) Gate peut bloquer la publication d'articles urgents
  - (-) Scores auto ne remplacent pas la relecture humaine
- **Révisable** : Oui — seuils configurables par projet

---

### [DEC-005] — Éditeur TipTap v3 avec extensions personnalisées

- **Date** : 2026-06 (Jour 6)
- **Domaine** : architecture
- **Problème** : Quel éditeur riche pour le contenu éditorial ?
- **Options étudiées** :
  - Option A : Quill
  - Option B : Slate.js
  - Option C : TipTap v3 (basé sur ProseMirror)
- **Décision retenue** : TipTap v3
- **Justification** : TipTap offre une API d'extension propre, un écosystème riche (tables, images, tasks), et une intégration React native. Les extensions `CalloutExtension` et `EditorImageExtension` sont des customisations maison s'intégrant naturellement dans le framework d'extension TipTap.
- **Conséquences** :
  - (+) Extensions maison (callouts, images upload) maintenues facilement
  - (+) Compatibilité React 19
  - (-) TipTap v3 est récent — API peut changer entre mineures
  - (-) Bundle size non négligeable (extensions multiples)
- **Révisable** : Non pour la session courante

---

### [DEC-006] — Autosave côté backend (pas localStorage)

- **Date** : 2026-06 (Jour 6)
- **Domaine** : architecture
- **Problème** : Comment autosauvegarder les brouillons d'articles ?
- **Options étudiées** :
  - Option A : localStorage + sync périodique
  - Option B : Debounce POST vers `/editor/autosave` backend
- **Décision retenue** : Option B — debounce vers API backend
- **Justification** : LocalStorage ne survit pas au changement d'appareil, est limité en taille, et ne se synchronise pas entre membres d'un projet. Le backend persiste en SQLite/PG, accessible depuis n'importe quel appareil.
- **Conséquences** :
  - (+) Synchronisation multi-device automatique
  - (+) Historique de versions côté serveur possible
  - (-) Autosave dépend de la connectivité réseau
  - (-) Latence réseau visible sur connexions lentes
- **Révisable** : Oui — peut combiner localStorage + backend pour mode offline

---

### [DEC-007] — JWT sans refresh token

- **Date** : 2026-06 (Jour 1)
- **Domaine** : sécurité
- **Problème** : Architecture d'authentification — access token seul ou access + refresh ?
- **Options étudiées** :
  - Option A : Access token 24h + refresh token longue durée
  - Option B : Access token seul (1440 min = 24h)
- **Décision retenue** : Option B — access token seul 24h
- **Justification** : Simplicité pour une V1 SaaS interne. Le refresh token complexifie l'implémentation et la rotation des clés. La durée de 24h est un compromis acceptable.
- **Conséquences** :
  - (+) Implémentation simple, maintenable
  - (-) Pas de révocation fine des sessions
  - (-) À revoir si le produit devient public avec des exigences de sécurité plus strictes
- **Révisable** : Oui — prioritaire si le produit ouvre à des utilisateurs externes

---

### [DEC-008] — Secrets revalidation blog envoyés en header HTTP

- **Date** : 2026-06 (Jour 6)
- **Domaine** : sécurité
- **Problème** : Comment transmettre le secret de revalidation Next.js sans l'exposer ?
- **Options étudiées** :
  - Option A : Query param `?secret=xxx` (initial)
  - Option B : Header HTTP `x-revalidate-secret: xxx`
- **Décision retenue** : Option B — header HTTP
- **Justification** : Les query params sont loggés dans les accès logs des serveurs et proxies. Un header HTTP est invisible des logs par défaut et conforme aux bonnes pratiques de sécurité des API.
- **Conséquences** :
  - (+) Secret non visible dans les logs
  - (-) Nécessite que le blog Next.js lise le header côté API route
- **Révisable** : Non

---

### [DEC-009] — TailwindCSS v4 sans fichier de configuration dédié

- **Date** : 2026-06 (Frontend)
- **Domaine** : architecture
- **Problème** : Comment configurer TailwindCSS v4 qui ne nécessite plus de `tailwind.config.js` ?
- **Options étudiées** :
  - Option A : Garder un `tailwind.config.ts` pour compatibilité v3
  - Option B : Utiliser la configuration inline Tailwind v4 (zero-config)
- **Décision retenue** : Option B — Tailwind v4 zero-config via plugin Vite
- **Justification** : Tailwind v4 est conçu pour fonctionner sans fichier de config. Le plugin `@tailwindcss/vite` gère tout. Moins de fichiers à maintenir.
- **Conséquences** :
  - (+) Zero config file, intégration Vite native
  - (-) Documentation Tailwind v4 encore rare — consulter via Context7 MCP
  - (-) Certains tokens v3 peuvent ne plus exister
- **Révisable** : Non pour la session courante

---

### [DEC-010] — Pipeline SEO découplé du pipeline de génération IA

- **Date** : 2026-06 (Jour 3-4)
- **Domaine** : architecture
- **Problème** : L'analyse SEO doit-elle être couplée à la génération IA ou indépendante ?
- **Options étudiées** :
  - Option A : SEO uniquement via IA (scoring LLM)
  - Option B : SEO rule-based indépendant + IA optionnelle
- **Décision retenue** : Option B — SEO rule-based (`seo_analyzer.py`) + pipeline IA séparé (`seo/`)
- **Justification** : Un SEO rule-based est déterministe, testable, gratuit et instantané. L'IA peut enrichir mais ne doit pas être un prérequis pour obtenir un score SEO de base.
- **Conséquences** :
  - (+) Scoring SEO disponible sans provider IA configuré
  - (+) 77 tests sur le SEO rule-based
  - (-) Deux systèmes SEO à maintenir en parallèle
- **Révisable** : Non — principe de séparation confirmé
