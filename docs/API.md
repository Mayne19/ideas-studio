# Documentation API — Ideas Studio

L'API REST d'Ideas Studio est construite avec FastAPI. Elle expose des endpoints pour la gestion des projets, articles, catégories, utilisateurs, génération IA, analyse SEO et bien plus.

**Base URL** : `http://localhost:8000` (dev) ou `https://api.ideas-studio.com` (prod)

**Documentation interactive** : `http://localhost:8000/docs` (Swagger UI)

---

## Authentification

### Inscription

Crée un nouveau compte utilisateur.

```
POST /auth/register
```

**Body :**
```json
{
  "email": "user@example.com",
  "password": "mon-mot-de-passe",
  "name": "Jean Dupont"
}
```

**Réponse (201) :**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "Jean Dupont",
  "created_at": "2026-01-15T10:00:00Z"
}
```

### Connexion

```json
POST /auth/login
```

**Body :**
```json
{
  "email": "user@example.com",
  "password": "mon-mot-de-passe"
}
```

**Réponse :**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### Utilisateur courant

```
GET /auth/me
```

**Headers :** `Authorization: Bearer <token>`

**Réponse :**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "Jean Dupont",
  "is_platform_admin": false,
  "created_at": "2026-01-15T10:00:00Z"
}
```

### Déconnexion

```
POST /auth/logout
```

**Headers :** `Authorization: Bearer <token>`

---

## Profil

### Modifier le mot de passe

```
POST /profile/password
```

**Headers :** `Authorization: Bearer <token>`

**Body :**
```json
{
  "current_password": "ancien-mot-de-passe",
  "new_password": "nouveau-mot-de-passe"
}
```

### Uploader un avatar

```
POST /profile/avatar
```

**Headers :** `Authorization: Bearer <token>`  
**Body :** `multipart/form-data` avec champ `file`

Formats acceptés : JPEG, PNG, GIF, WebP

---

## Santé

### Health check général

```
GET /health
```

**Réponse :**
```json
{
  "status": "ok"
}
```

### Health check LLM provider

```
GET /health/llm
```

Retourne l'état du provider IA configuré (disponibilité, modèle, erreurs éventuelles).

**Réponse (exemple) :**
```json
{
  "provider": "ollama",
  "model": "qwen3:14b",
  "configured": true,
  "available": true,
  "mock_allowed": "no",
  "environment": "production"
}
```

---

## Projets

### Lister les projets

```
GET /projects
```

**Headers :** `Authorization: Bearer <token>`

### Créer un projet

```
POST /projects
```

**Headers :** `Authorization: Bearer <token>`

**Body :**
```json
{
  "name": "Mon Blog",
  "domain": "monblog.com",
  "language": "fr",
  "audience": "Développeurs web",
  "tone": "Professionnel et technique"
}
```

### Obtenir un projet

```
GET /projects/{project_id}
```

**Headers :** `Authorization: Bearer <token>`

### Modifier un projet

```
PATCH /projects/{project_id}
```

**Headers :** `Authorization: Bearer <token>` (rôle : owner, admin)

### Supprimer un projet

```
DELETE /projects/{project_id}
```

**Headers :** `Authorization: Bearer <token>` (rôle : owner, admin)

### Connecter un blog

Récupère les informations de connexion et le snippet de tracking.

```
GET /projects/{project_id}/connect
```

**Headers :** `Authorization: Bearer <token>`

**Réponse :**
```json
{
  "project_id": "uuid",
  "domain": "monblog.com",
  "status": "not_connected",
  "public_tracking_key": "key",
  "secret_api_key_masked": "abc...xyz",
  "snippet": "<script src=...",
  "public_api_endpoints": {
    "articles": "https://api...",
    "article_by_slug": "https://api..."
  }
}
```

### Déconnecter un blog

```
POST /projects/{project_id}/disconnect
```

**Headers :** `Authorization: Bearer <token>` (rôle : owner, admin)

---

## Catégories

### Lister les catégories

```
GET /projects/{project_id}/categories
```

**Headers :** `Authorization: Bearer <token>`

### Créer une catégorie

```
POST /projects/{project_id}/categories
```

**Body :**
```json
{
  "name": "JavaScript",
  "slug": "javascript",
  "description": "Tout sur JavaScript",
  "color": "#F7DF1E",
  "priority": 1,
  "target_frequency": 4,
  "editorial_goal": "Devenir référence JS en France",
  "target_audience": "Développeurs JS"
}
```

### Obtenir une catégorie

```
GET /categories/{category_id}
```

### Modifier une catégorie

```
PATCH /categories/{category_id}
```

### Supprimer une catégorie

```
DELETE /categories/{category_id}
```

---

## Articles

### Lister les articles

```
GET /projects/{project_id}/articles?status=&category_id=&search=&published_only=&limit=&offset=
```

**Headers :** `Authorization: Bearer <token>`

**Paramètres :**
| Paramètre | Type | Description |
|---|---|---|
| `status` | string | Filtrer par statut |
| `category_id` | string | Filtrer par catégorie |
| `search` | string | Recherche texte |
| `published_only` | bool | Articles publiés uniquement |
| `limit` | int | Nombre max (défaut: 20) |
| `offset` | int | Pagination |

### Créer un article manuel

```
POST /projects/{project_id}/articles
```

**Body :**
```json
{
  "title": "Mon article",
  "category_id": "uuid",
  "content": "<h1>Contenu HTML</h1>",
  "keyword": "mot-clé principal",
  "meta_title": "Titre SEO",
  "meta_description": "Description SEO"
}
```

### Obtenir un article

```
GET /articles/{article_id}
```

### Modifier un article

```
PATCH /articles/{article_id}
```

### Publier

```
POST /articles/{article_id}/publish
```

Marque l'article comme publié, enregistre les métadonnées de publication et déclenche la revalidation du blog.

### Planifier

```
POST /articles/{article_id}/schedule
```

**Body :**
```json
{
  "scheduled_at": "2026-02-01T08:00:00Z"
}
```

L'article sera automatiquement publié par le worker.

### Dépublier

```
POST /articles/{article_id}/unpublish
```

### Marquer prêt

```
POST /articles/{article_id}/mark-ready
```

Passe le statut à `ready_to_publish`.

### Archiver

```
POST /articles/{article_id}/archive
```

### Promouvoir (mettre à jour la version publiée)

```
POST /articles/{article_id}/promote
```

Remplace le contenu publié par le contenu actuel du brouillon.

### Planifier une mise à jour

```
POST /articles/{article_id}/schedule-update
```

### Supprimer

```
DELETE /articles/{article_id}
```

### Statuts d'article

```
draft → idea_proposed → idea_priority / idea_rejected → outline_ready
→ writing_requested → writing_in_progress → draft_ready → review_needed
→ correction_needed → scheduled → published → update_recommended
→ ready_to_publish → unpublished → archived → failed
```

---

## Moteur d'idées

### Générer une idée

```
POST /projects/{project_id}/ideas/generate
```

**Headers :** `Authorization: Bearer <token>` (rôle : owner, admin, editor, writer)

**Body :**
```json
{
  "preferred_title": "Titre suggéré",
  "keyword": "mot-clé",
  "category_id": "uuid",
  "audience": "Développeurs",
  "angle": "Guide pratique",
  "search_intent": "informational",
  "context_hint": "Contexte additionnel"
}
```

L'idée utilise le LLM configuré, le provider de recherche, et vérifie les doublons de mot-clé.

### Génération multiple

```
POST /projects/{project_id}/ideas/auto-generate
```

**Body :**
```json
{
  "count": 3,
  "context_hint": "Contexte"
}
```

### Découverte d'idées (avec stratégie)

```
POST /projects/{project_id}/ideas/discover
```

**Body :**
```json
{
  "count": 5,
  "context_hint": "Contexte"
}
```

### Lancer un projet (idée + rédaction)

```
POST /projects/{project_id}/launch
```

**Body :**
```json
{
  "mode": "full_article",
  "preferred_title": "...",
  "keyword": "...",
  "category_id": "...",
  "audience": "...",
  "angle": "...",
  "search_intent": "informational",
  "context_hint": "...",
  "include_faq": true,
  "include_callouts": true,
  "dry_run": false
}
```

---

## Rédaction

### Démarrer la rédaction

Transforme une idée en article complet.

```
POST /articles/{article_id}/start-writing
```

**Headers :** `Authorization: Bearer <token>`

Génère le plan, rédige le contenu, crée les métadonnées SEO (meta_title, meta_description), extrait l'excerpt, génère la FAQ, exécute l'audit SEO Expert intégré.

### Rejeter une idée

```
POST /articles/{article_id}/reject
```

**Body :**
```json
{
  "rejection_reason": "keyword_too_broad",
  "rejection_note": "Mot-clé trop large"
}
```

### Définir la priorité

```
POST /articles/{article_id}/priority
```

**Body :**
```json
{
  "priority": 5
}
```

### Brouillon manuel

Crée un brouillon à partir du plan existant.

```
POST /articles/{article_id}/manual-draft
```

### Relancer la rédaction

Régénère le contenu d'un article existant.

```
POST /articles/{article_id}/rerun
```

---

## Génération complète (orchestrateur SEO)

### Générer un article complet

```
POST /projects/{project_id}/articles/generate
```

Utilise l'orchestrateur SEO complet (23 étapes) ou le mode legacy (idée + rédaction).

**Body :**
```json
{
  "preferred_title": "...",
  "keyword": "...",
  "category_id": "...",
  "audience": "...",
  "angle": "...",
  "search_intent": "informational",
  "context_hint": "...",
  "include_faq": true,
  "include_callouts": true,
  "use_orchestrator": true
}
```

### Rapport de génération

```
GET /projects/{project_id}/articles/{article_id}/generation-report
```

Retourne les métadonnées complètes de la génération (provider, modèle, sources, outils, étapes, erreurs).

### Workflow SEO complet

```
GET /projects/{project_id}/articles/{article_id}/seo-workflow
```

Retourne l'intégralité des données de l'orchestrateur : contexte projet, stratégie catégorie, analyse intention, brief recherche, brief keyword, angle éditorial, plan, images, callouts, FAQ, liens, rapports qualité, originalité, humanisation, EEAT, checklist SEO finale.

---

## Analyse SEO

### Analyser un article

```
POST /articles/{article_id}/analyze
```

Exécute l'analyse SEO complète : SEO, lisibilité, qualité, EEAT.

### Dernière analyse

```
GET /articles/{article_id}/analysis/latest
```

### Historique des analyses

```
GET /articles/{article_id}/analyses
```

### Vérification avant publication (Ready Check)

```
POST /articles/{article_id}/ready-check
```

Retourne le statut `blocked`, `needs_improvement` ou `ready` avec la liste des issues bloquantes.

### Mise à jour éditeur

```
PATCH /articles/{article_id}/editor
```

Sauvegarde les champs éditoriaux (titre, contenu, slug, meta, etc.), crée une version manuelle si nécessaire.

### SEO Expert Review

Déclenche l'audit SEO Expert avancé.

```
POST /projects/{project_id}/articles/{article_id}/seo-expert-review
```

---

## Éditeur

### Données éditeur

```
GET /articles/{article_id}/editor
```

Retourne toutes les données nécessaires à l'éditeur : article, métadonnées, rapports SEO, versions publiées, indicateur de modifications.

### Autosave

```
POST /articles/{article_id}/autosave
```

Sauvegarde sans publier, crée une version autosave si le contenu a changé.

**Body :** champs partiels (titre, contenu, meta, slug, etc.)

### Preview

```
GET /articles/{article_id}/preview
```

Aperçu privé de l'article (inclus les brouillons).

---

## Versions

### Lister les versions

```
GET /articles/{article_id}/versions
```

### Restaurer une version

```
POST /articles/{article_id}/versions/{version_id}/restore
```

Sauvegarde l'état courant puis applique la version demandée.

---

## Commentaires

### Lister

```
GET /articles/{article_id}/comments
```

### Créer

```
POST /articles/{article_id}/comments
```

**Body :**
```json
{
  "text": "Revoir ce paragraphe",
  "selected_text": "texte sélectionné dans l'article"
}
```

### Modifier

```
PATCH /articles/{article_id}/comments/{comment_id}
```

**Body :**
```json
{
  "resolved": true
}
```

### Supprimer

```
DELETE /articles/{article_id}/comments/{comment_id}
```

---

## Médias

### Lister les médias

```
GET /projects/{project_id}/media?article_id=uuid
```

### Uploader un fichier

```
POST /projects/{project_id}/media/upload
```

**Body :** `multipart/form-data` avec `file` et optionnellement `article_id`

### Uploader depuis une URL

```
POST /projects/{project_id}/media/upload-json
```

**Body :**
```json
{
  "url": "https://example.com/image.jpg",
  "filename": "image.jpg",
  "mime_type": "image/jpeg",
  "size": 12345,
  "alt_text": "Description",
  "article_id": "uuid"
}
```

### Modifier un média

```
PATCH /media/{media_id}
```

### Supprimer un média

```
DELETE /media/{media_id}
```

---

## Pipeline automatisé

### Configuration

```
GET /projects/{project_id}/pipeline
```

```
PATCH /projects/{project_id}/pipeline
```

**Body :**
```json
{
  "enabled": true,
  "active_days": ["monday", "wednesday", "friday"],
  "launch_hour": 8,
  "articles_per_week": 5,
  "ideas_per_week": 5,
  "category_priorities": {"cat-id": 80},
  "max_pending_drafts": 10,
  "default_quality_mode": "quality",
  "paused_until": null,
  "paused_indefinitely": false
}
```

### Exécution manuelle

```
POST /projects/{project_id}/pipeline/run
```

### Logs

```
GET /projects/{project_id}/pipeline/logs?limit=20
```

---

## Callouts

### Lister

```
GET /projects/{project_id}/callouts
```

### Créer

```
POST /projects/{project_id}/callouts
```

**Body :**
```json
{
  "slug": "info",
  "label": "Information",
  "style": "info",
  "default_title": "À savoir",
  "color_background": "#e8f4f8",
  "color_border": "#2196F3",
  "color_text": "#0d47a1"
}
```

### Modifier

```
PATCH /projects/{project_id}/callouts/{callout_id}
```

### Supprimer

```
DELETE /projects/{project_id}/callouts/{callout_id}
```

### Synchroniser depuis le blog

Importe la configuration callouts depuis le site connecté.

```
POST /projects/{project_id}/callouts/sync
```

---

## Configuration éditoriale

### Suggérer une configuration

Analyse le domaine du projet et propose des suggestions de configuration éditoriale.

```
POST /projects/{project_id}/editorial-setup/suggest
```

---

## Performance et tracking

### Résumé de trafic

```
GET /projects/{project_id}/performance/summary?period=30d
```

### Performance des articles

```
GET /projects/{project_id}/performance/articles?period=30d
```

### Performance d'un article

```
GET /articles/{article_id}/performance?period=30d
```

### Script de tracking

```
GET /traffic.js
```

### Collecte de trafic

```
POST /api/traffic/collect
```

---

## Recommendations

### Lister

```
GET /projects/{project_id}/recommendations
```

### Lancer une revue

Analyse les articles publiés et génère des recommandations d'optimisation.

```
POST /projects/{project_id}/recommendations/review
```

### Accepter

```
POST /recommendations/{recommendation_id}/accept
```

### Rejeter

```
POST /recommendations/{recommendation_id}/reject
```

### Appliquer

```
POST /recommendations/{recommendation_id}/apply
```

---

## Notifications

### Lister

```
GET /projects/{project_id}/notifications
```

### Marquer comme lue

```
POST /notifications/{notification_id}/read
```

### Tout marquer comme lu

```
POST /projects/{project_id}/notifications/read-all
```

### Supprimer

```
DELETE /notifications/{notification_id}
```

---

## Membre et invitations

### Lister les membres

```
GET /projects/{project_id}/members
```

### Ajouter un membre (par ID)

```
POST /projects/{project_id}/members
```

**Body :**
```json
{
  "user_id": "uuid",
  "role": "editor"
}
```

### Ajouter un membre (par username)

```
POST /projects/{project_id}/members/by-username
```

**Body :**
```json
{
  "user_id": "@username",
  "role": "editor"
}
```

### Modifier le rôle

```
PATCH /projects/{project_id}/members/{user_id}
```

**Body :**
```json
{
  "role": "admin"
}
```

### Retirer un membre

```
DELETE /projects/{project_id}/members/{user_id}
```

### Lister les invitations

```
GET /projects/{project_id}/invitations
```

### Inviter par email

```
POST /projects/{project_id}/invitations
```

**Body :**
```json
{
  "email": "user@example.com",
  "role": "editor"
}
```

### Voir une invitation

```
GET /invitations/{token}
```

### Accepter une invitation

```
POST /invitations/{token}/accept
```

### Rôles disponibles

| Rôle | Permissions |
|---|---|
| `owner` | Accès total, non supprimable |
| `admin` | Accès total sauf transfert propriété |
| `editor` | Gère contenu, catégories, médias |
| `writer` | Crée et modifie les brouillons |
| `viewer` | Lecture seule |

---

## Search Console

### Statut de connexion

```
GET /projects/{project_id}/search-console/status
```

**Note :** L'intégration Google Search Console nécessite une configuration OAuth (à venir).

### Mots-clés

```
GET /projects/{project_id}/search-console/keywords
```

### Pages

```
GET /projects/{project_id}/search-console/pages
```

### Performance

```
GET /projects/{project_id}/search-console/performance
```

---

## Recherche globale

```
GET /search?q=terme&limit=20
```

Recherche dans les articles, catégories et projets accessibles à l'utilisateur.

---

## Activité

```
GET /projects/{project_id}/activity?limit=50&action=generate_idea
```

Journal d'activité du projet avec filtrage par action.

---

## Webhooks

### Lister

```
GET /projects/{project_id}/webhooks
```

### Créer

```
POST /projects/{project_id}/webhooks
```

**Body :**
```json
{
  "name": "Notification Slack",
  "url": "https://hooks.slack.com/...",
  "events": ["article.published", "article.created"]
}
```

### Modifier

```
PATCH /projects/{project_id}/webhooks/{webhook_id}
```

### Supprimer

```
DELETE /projects/{project_id}/webhooks/{webhook_id}
```

### Tester

```
POST /projects/{project_id}/webhooks/{webhook_id}/test
```

### Événements disponibles

| Événement | Déclencheur |
|---|---|
| `article.created` | Nouvel article créé |
| `article.published` | Article publié |
| `article.updated` | Article mis à jour |
| `idea.generated` | Nouvelle idée générée |
| `pipeline.completed` | Pipeline exécuté |

---

## API Publique (sans auth)

Accessible sans authentification pour exposer le contenu sur le blog connecté.

### Articles publiés

```
GET /api/public/projects/{project_id}/articles?limit=20&offset=0
```

### Article par slug

```
GET /api/public/projects/{project_id}/articles/{slug}
```

### Catégories

```
GET /api/public/projects/{project_id}/categories
```

---

## Providers IA

### Lister les providers

```
GET /settings/ai-providers
```

**Headers :** `Authorization: Bearer <token>` (admin)

### Créer un provider

```
POST /settings/ai-providers
```

**Body :**
```json
{
  "provider": "anthropic",
  "label": "Anthropic Claude",
  "api_key": "sk-...",
  "model": "claude-3-haiku-20240307",
  "base_url": "https://api.anthropic.com/v1",
  "is_default": false,
  "enabled": true
}
```

### Obtenir un provider

```
GET /settings/ai-providers/{provider_id}
```

### Modifier

```
PATCH /settings/ai-providers/{provider_id}
```

### Supprimer

```
DELETE /settings/ai-providers/{provider_id}
```

### Tester

```
POST /settings/ai-providers/{provider_id}/test
```

### Provider par défaut

```
GET /settings/ai-providers/default
```

### Providers supportés

| Key | Label | URL par défaut |
|---|---|---|
| `gemini` | Google Gemini | `https://generativelanguage.googleapis.com/v1beta/openai/` |
| `openai` | OpenAI | `https://api.openai.com/v1` |
| `openrouter` | OpenRouter | `https://openrouter.ai/api/v1` |
| `anthropic` | Anthropic | `https://api.anthropic.com/v1` |
| `mistral` | Mistral AI | `https://api.mistral.ai/v1` |
| `ollama` | Ollama (local) | `http://127.0.0.1:11434/v1` |
| `custom` | Custom OpenAI-compatible | Libre |

---

## Gestion des erreurs

L'API retourne les codes HTTP standard :

| Code | Signification |
|---|---|
| `200` | Succès |
| `201` | Créé |
| `204` | Supprimé (pas de contenu) |
| `400` | Requête invalide |
| `401` | Non authentifié |
| `403` | Permissions insuffisantes |
| `404` | Ressource introuvable |
| `409` | Conflit (doublon) |
| `502` | Erreur provider IA |
| `503` | Provider IA indisponible |

Toutes les erreurs retournent un corps JSON avec un champ `detail`.
