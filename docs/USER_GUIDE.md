# Guide utilisateur — Ideas Studio

Ideas Studio est une plateforme SaaS de création de contenu SEO assistée par IA. Ce guide vous accompagne dans l'utilisation de toutes les fonctionnalités.

---

## Table des matières

1. [Créer un compte](#créer-un-compte)
2. [Gérer son profil](#gérer-son-profil)
3. [Créer et configurer un projet](#créer-et-configurer-un-projet)
4. [Connecter un blog](#connecter-un-blog)
5. [Gérer les catégories](#gérer-les-catégories)
6. [Configurer les callouts](#configurer-les-callouts)
7. [Générer des idées](#générer-des-idées)
8. [Rédiger des articles](#rédiger-des-articles)
9. [L'orchestrateur SEO](#lorchestrateur-seo)
10. [Analyser le SEO](#analyser-le-seo)
11. [Éditer et réviser](#éditer-et-réviser)
12. [Publier et programmer](#publier-et-programmer)
13. [Pipeline automatisé](#pipeline-automatisé)
14. [API Publique](#api-publique)
15. [Tracking de trafic](#tracking-de-trafic)
16. [Performance et analytics](#performance-et-analytics)
17. [Recommendations d'optimisation](#recommendations-doptimisation)
18. [Notifications](#notifications)
19. [Gestion d'équipe](#gestion-déquipe)
20. [Invitations](#invitations)
21. [Search Console](#search-console)
22. [Webhooks](#webhooks)
23. [Paramètres du compte](#paramètres-du-compte)

---

## Créer un compte

1. Rendez-vous sur la page d'inscription
2. Renseignez votre email, nom et mot de passe
3. Validez votre inscription

### Connexion

Utilisez votre email et mot de passe pour vous connecter. Un token JWT est généré et conservé pour toute la session (durée configurable, 24h par défaut).

### Profil utilisateur

Accédez à votre profil depuis le menu utilisateur. Vous pouvez y voir :
- Votre nom et email
- Votre avatar
- La date de création de votre compte

---

## Gérer son profil

### Modifier son mot de passe

1. Allez dans **Profil → Changer le mot de passe**
2. Saisissez votre mot de passe actuel
3. Saisissez le nouveau mot de passe (minimum 6 caractères)
4. Confirmez

### Avatar

1. Allez dans **Profil → Avatar**
2. Téléchargez une image (JPEG, PNG, GIF ou WebP)
3. L'avatar est automatiquement recadré et sauvegardé

---

## Créer et configurer un projet

Un projet représente un blog ou site web pour lequel vous produisez du contenu.

### Création

1. Cliquez sur **Nouveau projet**
2. Renseignez les champs :

| Champ | Obligatoire | Description |
|---|---|---|
| Nom | Oui | Nom du projet (ex: "Blog Tech") |
| Domaine | Non | URL du blog connecté (ex: `blog.example.com`) |
| Langue | Non | Langue du contenu (ex: `fr`, `en`, `es`) |
| Audience | Non | Description de l'audience cible |
| Ton | Non | Ton éditorial souhaité |

### Configuration

Une fois le projet créé, vous pouvez modifier ses paramètres à tout moment :
- Le nom et le domaine
- La langue et le pays cible
- L'audience et le ton éditorial
- La configuration IA

### Supprimer un projet

La suppression est définitive. Tous les articles, catégories et données associées sont supprimés.

### Déconnecter un blog

Si vous souhaitez déconnecter le blog sans supprimer le projet, utilisez l'option **Déconnecter**.

---

## Connecter un blog

### Snippet de tracking

1. Allez dans **Projet → Connecter**
2. Copiez le snippet JavaScript fourni
3. Ajoutez-le dans le `<head>` de votre blog

```html
<script
  src="https://api.ideas-studio.com/traffic.js"
  data-project-id="VOTRE_PROJECT_ID"
  data-tracking-key="VOTRE_PUBLIC_TRACKING_KEY"
  async>
</script>
```

### Statuts de connexion

| Statut | Description |
|---|---|
| `not_connected` | Blog pas encore connecté |
| `connected` | Blog connecté et tracking actif |
| `disconnected` | Blog déconnecté |

### Informations de connexion

La page de connexion affiche :
- L'ID du projet
- La clé de tracking publique
- La clé API secrète (masquée)
- Les endpoints de l'API publique
- Le statut de connexion

---

## Gérer les catégories

Les catégories organisent vos articles et permettent à l'orchestrateur SEO de prioriser la production.

### Créer une catégorie

1. Allez dans **Projet → Catégories**
2. Cliquez sur **Nouvelle catégorie**
3. Renseignez :

| Champ | Description |
|---|---|
| Nom | Le nom visible de la catégorie |
| Slug | Version URL-friendly (générée automatiquement) |
| Description | Description de la catégorie |
| Couleur | Code hexadécimal pour identifier la catégorie |
| Priorité | Ordre d'affichage (0 = le plus haut) |
| Objectif éditorial | But stratégique de la catégorie |
| Audience cible | Sous-groupe d'audience pour cette catégorie |
| Fréquence mensuelle | Nombre d'articles visé par mois |
| Pipeline activé | Inclure dans le pipeline automatisé |

### Pipeline et catégories

Les catégories avec `pipeline_enabled=true` sont automatiquement incluses dans les cycles de génération du pipeline.

---

## Configurer les callouts

Les callouts sont des encadrés visuels (info, warning, tip, etc.) qui enrichissent les articles.

### Créer un callout

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

### Styles disponibles

- `info` — Information générale
- `warning` — Attention
- `tip` — Conseil
- `danger` — Important / danger
- `success` — Succès

### Synchronisation depuis le blog

Si votre blog expose une configuration callouts via `/api/ideas-studio/config`, vous pouvez synchroniser automatiquement les callouts :

```
POST /projects/{project_id}/callouts/sync
```

Cette opération importe ou met à jour les callouts depuis le site connecté.

---

## Générer des idées

Le moteur d'idées utilise l'IA pour proposer des sujets d'articles SEO optimisés.

### Génération simple

1. Allez dans **Intelligence → Générer une idée**
2. Vous pouvez préciser (optionnel) :
   - **Titre préféré** — Suggérer un titre
   - **Mot-clé** — Forcer un mot-clé spécifique
   - **Catégorie** — Associer à une catégorie
   - **Angle** — Angle éditorial souhaité
   - **Intention de recherche** — `informational`, `commercial`, `transactional`, `navigational`
   - **Audience** — Audience cible spécifique
   - **Contexte** — Contexte additionnel
3. L'idée générée contient :
   - Un titre
   - Un mot-clé principal
   - Un angle éditorial
   - Une intention de recherche détectée
   - Une audience cible
   - Un score d'opportunité (0.0 - 1.0)
   - Un résumé SERP (si provider de recherche configuré)

### Génération multiple

Générez plusieurs idées d'un coup :

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

### Découverte d'idées

La découverte utilise la stratégie de catégorie pour choisir intelligemment les sujets :

```
POST /projects/{project_id}/ideas/discover
```

### Gérer les idées

Après génération, les idées apparaissent avec le statut `idea_proposed`. Vous pouvez :

- **Définir la priorité** — Marquer une idée comme prioritaire (`idea_priority`)
- **Rejeter** — Avec une raison et une note optionnelle
- **Convertir en brouillon manuel** — Créer un squelette d'article
- **Démarrer la rédaction** — Lancer la génération IA complète

### Prévention des doublons

Le système vérifie automatiquement si le mot-clé est déjà utilisé dans un article actif (de `idea_proposed` à `published`). Si c'est le cas, l'idée n'est pas générée.

---

## Rédiger des articles

### Rédaction automatique

1. Depuis une idée, cliquez sur **Démarrer la rédaction**
2. Le système :
   1. Génère un plan détaillé (H2/H3 avec notes)
   2. Rédige l'article complet en HTML
   3. Calcule le temps de lecture
   4. Génère le meta title et la meta description
   5. Extrait l'excerpt
   6. Génère la FAQ (3-5 questions)
   7. Extrait les callouts du contenu
   8. Exécute l'audit SEO Expert intégré

### Options de rédaction

- **Mode simple** — Idée → rédaction (legacy)
- **Mode orchestrateur** — 23 étapes complètes (recommandé)
- **Relancer** — Régénérer le contenu d'un article existant
- **Brouillon manuel** — Créer un squelette à partir du plan

### Contenu généré

L'article contient :
- Contenu HTML (compatible TipTap)
- Plan structuré (outline_json)
- FAQ (faq_json)
- Callouts extraits (callouts_json)
- Métadonnées SEO (meta_title, meta_description)
- Excerpt
- Temps de lecture
- Rapport de génération complet

---

## L'orchestrateur SEO

L'orchestrateur est le moteur de génération avancé qui exécute 23 étapes pour produire un article professionnel.

### Étapes de l'orchestrateur

| Phase | Étape | Description |
|---|---|---|
| **1** | ProjectContext | Analyse du projet (nom, domaine, audience, ton) |
| **2** | CategoryStrategy | Stratégie de catégorie (priorités, objectifs) |
| **3** | IdeaDiscovery | Découverte d'idée (titre, mot-clé, intention) |
| **4** | CannibalizationCheck | Vérification de cannibalisation SEO |
| **5** | IntentAnalysis | Analyse d'intention de recherche |
| **6** | ResearchBrief | Brief de recherche (sources, questions) |
| **7** | KeywordBrief | Brief mot-clé (principal + secondaires) |
| **8** | EditorialAngle | Angle éditorial (promesse, ton, EEAT) |
| **9** | ArticleOutline | Plan structuré (sections, rôles) |
| **10** | ImagePlan | Plan d'images (sourcing, alt texts) |
| **11** | CalloutPlan | Plan de callouts (placement, style) |
| **12** | FAQPlan | Plan de FAQ (questions pertinentes) |
| **13** | InternalLinkPlan | Plan de liens internes |
| **14** | ExternalLinkPlan | Plan de liens externes |
| **15** | Writing | Rédaction complète de l'article |
| **16** | LanguageQuality | Contrôle qualité linguistique |
| **17** | Originality | Vérification d'originalité |
| **18** | Humanization | Passage d'humanisation |
| **19** | EEAT | Checklist EEAT (Expertise, Authorité, Confiance) |
| **20** | EditorialQuality | Gateau qualité éditoriale |
| **21** | SEOFinalChecklist | Checklist SEO finale |
| **22** | SEOReview | Review SEO agrégée |
| **23** | GenerationReport | Rapport de génération complet |

### Utilisation

```
POST /projects/{project_id}/articles/generate
```

Avec `use_orchestrator: true` pour utiliser le mode complet.

### Rapport de génération

Consultez le rapport complet après génération pour voir :
- Le provider et modèle utilisés
- Les outils disponibles et configurés
- Les étapes complétées
- Les éventuelles erreurs ou limitations
- Les scores et métriques

---

## Analyser le SEO

### Analyse manuelle

1. Ouvrez un article
2. Cliquez sur **Analyser SEO**
3. Les résultats sont immédiats

### Scores

| Score | Plage | Description |
|---|---|---|
| **SEO** | 0-100 | Positionnement mot-clé, meta, slug, structure |
| **Lisibilité** | 0-100 | Longueur phrases/paragraphes, intro, sous-titres |
| **Qualité** | 0-100 | Longueur article, conclusion, image couverture |
| **EEAT** | 0-100 | Liens externes, exemples/statistiques, actionnabilité |

### Statut Readiness

| Statut | Signification |
|---|---|
| `ready` | Prêt à publier |
| `needs_improvement` | Améliorations suggérées |
| `blocked` | Problèmes bloquants à corriger |

### Vérification avant publication (Ready Check)

Lancez un **Ready Check** pour obtenir une synthèse :
- Scores SEO, lisibilité, qualité, EEAT
- Liste des issues bloquantes (critical)
- Indication publiable ou non

### Issues détectées

| Catégorie | Exemples |
|---|---|
| **SEO** | Mot-clé absent du titre, pas de H1, meta title trop long, slug sans mot-clé |
| **Lisibilité** | Phrases > 25 mots, paragraphes > 150 mots, intro trop courte |
| **Qualité** | Contenu mock, article trop court (< 300 mots), pas de conclusion |
| **EEAT** | Pas de liens externes, pas d'exemples, pas de données chiffrées |

---

## Éditer et réviser

### Éditeur riche

L'éditeur TipTap offre :
- Formatage riche (gras, italique, listes, tableaux, blockquotes)
- Gestion des titres (H1, H2, H3)
- Insertion d'images
- Sauvegarde automatique
- Compteur de mots

### Autosave

L'éditeur sauvegarde automatiquement toutes les 30 secondes. Chaque autosave crée une version.

### Versions

L'historique des versions conserve :
- Les versions manuelles (sauvegardes explicites)
- Les versions autosave (sauvegardes automatiques)
- Les versions de restauration

**Restaurer une version :**
1. Ouvrez l'historique des versions
2. Sélectionnez la version à restaurer
3. Confirmez la restauration
4. L'état courant est sauvegardé puis la version est appliquée

### Commentaires inline

Les commentaires permettent la révision collaborative :
1. Sélectionnez du texte dans l'article
2. Cliquez sur l'icône commentaire
3. Rédigez votre commentaire
4. Les commentaires peuvent être marqués comme résolus

### Preview

Utilisez l'aperçu pour voir l'article tel qu'il apparaîtra sur le blog (accessible même pour les brouillons).

---

## Publier et programmer

### Publication immédiate

1. Assurez-vous que l'article est en statut `draft_ready` ou `ready_to_publish`
2. Lancez le **Ready Check** pour vérifier l'absence d'issues bloquantes
3. Cliquez sur **Publier**
4. L'article passe en statut `published`
5. Les métadonnées de publication sont sauvegardées
6. Si configuré, le cache du blog est revalidé

### Que se passe-t-il à la publication ?

- Le statut passe à `published`
- Le contenu, titre, excerpt, meta_description, cover_image, FAQ et callouts sont figés dans les champs `published_*`
- La date de publication est enregistrée
- Un webhook `article.published` est déclenché
- Le blog est revalidé si configuré

### Programmation

1. Cliquez sur **Programmer**
2. Choisissez la date et l'heure de publication
3. L'article reçoit le statut `scheduled`
4. Le worker publie automatiquement à l'heure prévue

### Mettre à jour un article publié

1. Modifiez l'article (le brouillon est séparé de la version publiée)
2. Utilisez **Promouvoir** pour remplacer la version publiée par le brouillon
3. Les modifications sont visibles immédiatement après promotion

### Dépublier

1. Cliquez sur **Dépublier**
2. L'article repasse en brouillon
3. La version publiée est conservée dans `published_*`

### Archiver

Les articles archivés ne sont plus visibles dans les listes actives.

### Planifier une mise à jour

Pour les articles publiés, vous pouvez planifier une future mise à jour :
- Le statut reste `published`
- À la date planifiée, le système notifie qu'une mise à jour est recommandée

---

## Pipeline automatisé

Le pipeline permet d'automatiser la production quotidienne de contenu.

### Configuration

1. Allez dans **Projet → Pipeline**
2. Activez le pipeline
3. Configurez les paramètres :

| Paramètre | Défaut | Description |
|---|---|---|
| Activé | false | Activer/désactiver le pipeline |
| Jours actifs | [] | Jours de la semaine (ex: `["monday", "wednesday", "friday"]`) |
| Heure de lancement | 8 | Heure de début (0-23) |
| Articles par semaine | 5 | Objectif hebdomadaire |
| Idées par semaine | 5 | Nombre d'idées à générer |
| Priorités catégories | {} | Répartition par catégorie (en pourcentage) |
| Max brouillons en attente | 10 | Limite de brouillons non publiés |
| Mode qualité | `quality` | Mode de génération |
| Pause | - | Mettre en pause temporairement |

### Fonctionnement

Le worker exécute le pipeline chaque heure :
1. Vérifie que le pipeline est activé et non en pause
2. Vérifie que le nombre de brouillons en attente est sous la limite
3. Calcule le nombre d'idées à générer pour la journée
4. Pour chaque idée :
   - Utilise le LLM configuré
   - Utilise le provider de recherche
   - Génère une idée avec vérification anti-doublon
5. Sauvegarde le rapport d'exécution

### Logs du pipeline

Consultez les logs pour voir :
- Le statut de chaque exécution (`completed`, `completed_with_errors`, `skipped`, `failed`)
- Le nombre d'idées générées
- Les erreurs éventuelles

### Mise en pause

- **Pause temporaire** — Jusqu'à une date spécifiée
- **Pause indéfinie** — Jusqu'à réactivation manuelle

---

## API Publique

L'API publique expose vos articles et catégories sans authentification pour le blog connecté.

### Endpoints

```
GET /api/public/projects/{project_id}/articles
GET /api/public/projects/{project_id}/articles/{slug}
GET /api/public/projects/{project_id}/categories
```

### Utilisation

1. Connectez votre blog (voir [Connecter un blog](#connecter-un-blog))
2. Utilisez les endpoints avec l'ID public du projet
3. Seuls les articles publiés sont retournés

### Exemple d'intégration blog

```javascript
// Récupérer les articles depuis le blog
const response = await fetch(
  'https://api.ideas-studio.com/api/public/projects/{project_id}/articles'
);
const articles = await response.json();
```

---

## Tracking de trafic

### Installation

Ajoutez le snippet de tracking dans le `<head>` de votre blog (voir [Connecter un blog](#connecter-un-blog)).

### Fonctionnement

Le script collecte automatiquement :
- L'URL de la page visitée
- Le chemin
- Le referrer (provenance)
- Le user-agent
- L'IP (côté serveur)

### Données collectées

Les événements de trafic sont stockés et utilisés pour :
- Les statistiques de performance
- Le calcul des vues par article
- Les métriques de période (7j, 30j, 90j)
- Les recommandations d'optimisation

### Vie privée

Le tracking ne collecte pas de données personnelles identifiables. Aucun cookie n'est déposé.

---

## Performance et analytics

### Résumé de trafic

```
GET /projects/{project_id}/performance/summary?period=30d
```

Retourne :
- Nombre total de vues
- Vues par jour (moyenne)
- Nombre d'articles suivis
- Statistiques agrégées

### Performance des articles

```
GET /projects/{project_id}/performance/articles?period=30d
```

Liste chaque article avec ses métriques de performance.

### Performance d'un article

```
GET /articles/{article_id}/performance?period=30d
```

Détail des métriques pour un article spécifique.

### Périodes disponibles

- `7d` — 7 derniers jours
- `30d` — 30 derniers jours (défaut)
- `90d` — 90 derniers jours

---

## Recommendations d'optimisation

Le moteur d'optimisation analyse automatiquement les articles publiés et propose des améliorations.

### Types de recommandations

| Type | Déclencheur |
|---|---|
| `fix_low_traffic` | Article avec < 5 vues à J+30 ou J+90 |
| `add_faq` | Article sans FAQ |
| `improve_meta_description` | Meta description < 120 caractères |
| `improve_title` | Score SEO < 50 |
| `add_internal_links` | Aucun lien interne détecté |

### Lancer une revue

1. Allez dans **Projet → Optimisation**
2. Cliquez sur **Lancer une revue**
3. Les recommandations sont générées automatiquement

### Gérer les recommandations

| Action | Effet |
|---|---|
| **Accepter** | Marque la recommandation comme acceptée |
| **Appliquer** | Marque comme appliquée (réservé admin/editor) |
| **Rejeter** | Marque comme rejetée |

### Prévention des doublons

Une recommandation `pending` du même type et pour le même article bloque la création d'une nouvelle recommandation identique.

---

## Notifications

Les notifications informent l'équipe des événements importants.

### Types de notifications

| Type | Description |
|---|---|
| `member` | Ajout/modification/suppression de membre |
| `invitation` | Invitation envoyée ou acceptée |
| `article` | Publication, rejet, génération |
| `pipeline` | Résultat d'exécution du pipeline |
| `system` | Informations système |

### Actions disponibles

- **Marquer comme lue** — Une notification individuelle
- **Tout marquer comme lu** — Toutes les notifications du projet
- **Supprimer** — Effacer une notification

### Niveaux

| Niveau | Couleur | Usage |
|---|---|---|
| `info` | Bleu | Information générale |
| `success` | Vert | Opération réussie |
| `warning` | Orange | Attention |
| `error` | Rouge | Erreur |

---

## Gestion d'équipe

### Rôles

| Rôle | Créer/éditer contenu | Gérer membres | Publier | Supprimer | Paramètres projet |
|---|---|---|---|---|---|
| **Owner** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Admin** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Editor** | ✅ | ❌ | ✅ | ✅ | ❌ |
| **Writer** | ✅ (brouillons) | ❌ | ❌ | ❌ | ❌ |
| **Viewer** | ❌ (lecture seule) | ❌ | ❌ | ❌ | ❌ |

### Ajouter un membre

1. Allez dans **Projet → Membres**
2. Cliquez sur **Ajouter un membre**
3. Recherchez par ID utilisateur ou par nom d'utilisateur (@username)
4. Choisissez le rôle
5. Validez

### Modifier un rôle

1. Sélectionnez le membre concerné
2. Choisissez le nouveau rôle
3. Validez

### Retirer un membre

1. Sélectionnez le membre concerné
2. Confirmez la suppression

**Note :** Le propriétaire (`owner`) ne peut pas être retiré.

---

## Invitations

### Envoyer une invitation

1. Allez dans **Projet → Membres → Inviter**
2. Saisissez l'adresse email
3. Choisissez le rôle
4. Une notification est créée dans le projet

### Recevoir une invitation

1. Vous recevez un lien d'invitation
2. Ouvrez le lien
3. Connectez-vous ou créez un compte
4. Acceptez l'invitation

### Statuts d'invitation

| Statut | Description |
|---|---|
| En attente | L'invitation n'a pas encore été acceptée |
| Acceptée | L'utilisateur a rejoint le projet |
| Expirée | Le délai d'acceptation est dépassé |

---

## Search Console

L'intégration Google Search Console permet de visualiser les données de recherche Google directement dans Ideas Studio.

### Statut actuel

**Note :** L'intégration complète nécessite une configuration OAuth Google qui sera disponible dans une version ultérieure. Les endpoints retournent actuellement un statut de non-connexion.

### Endpoints disponibles

| Endpoint | Données |
|---|---|
| `GET .../search-console/status` | Statut de connexion |
| `GET .../search-console/keywords` | Mots-clés et positions |
| `GET .../search-console/pages` | Pages indexées et clics |
| `GET .../search-console/performance` | Impressions, clics, CTR, position |

---

## Webhooks

Les webhooks permettent d'intégrer Ideas Studio avec vos services externes (Slack, Discord, Zapier, etc.).

### Créer un webhook

1. Allez dans **Projet → Webhooks**
2. Cliquez sur **Ajouter un webhook**
3. Renseignez :
   - **Nom** — Identifiant (ex: "Slack #notifications")
   - **URL** — URL de destination
   - **Événements** — Types d'événements à écouter

### Événements disponibles

| Événement | Déclencheur |
|---|---|
| `article.created` | Nouvel article créé |
| `article.published` | Article publié |
| `article.updated` | Article modifié |
| `idea.generated` | Nouvelle idée générée |
| `pipeline.completed` | Pipeline exécuté |

### Signature de sécurité

Chaque webhook reçoit un header `X-IdeasStudio-Signature` contenant une signature HMAC du payload. Vous pouvez vérifier l'intégrité du message côté récepteur.

### Payload type

```json
{
  "event": "article.published",
  "project_id": "uuid",
  "data": {
    "article_id": "uuid",
    "title": "Titre de l'article",
    "slug": "titre-article"
  },
  "timestamp": "2026-01-15T10:00:00Z"
}
```

### Tester un webhook

1. Ouvrez le webhook
2. Cliquez sur **Tester**
3. Un payload de test est envoyé
4. Le statut de la réponse est affiché

---

## Paramètres du compte

### Modifier le mot de passe

Voir [Modifier son mot de passe](#modifier-son-mot-de-passe) dans la section Profil.

### Avatar

Voir [Avatar](#avatar) dans la section Profil.

### Langue de l'interface

L'interface est disponible en français.

### Déconnexion

Cliquez sur **Déconnexion** dans le menu utilisateur pour terminer votre session.

### Sécurité

- Les tokens JWT expirent après 24h (configurable)
- Les mots de passe sont hashés avec bcrypt
- Les clés API des providers sont chiffrées en base de données
- Les sessions sont individuelles

---

## Glossaire

| Terme | Définition |
|---|---|
| **Article** | Contenu publié ou en cours de rédaction |
| **Brouillon** | Article non publié |
| **Callout** | Encadré visuel dans un article (info, warning, tip) |
| **Catégorie** | Groupe thématique d'articles |
| **EEAT** | Experience, Expertise, Authoritativeness, Trustworthiness |
| **Excerpt** | Extrait court de l'article (aperçu) |
| **LLM** | Large Language Model (modèle de langage) |
| **Meta description** | Description SEO affichée dans les résultats de recherche |
| **Meta title** | Titre SEO affiché dans les résultats de recherche |
| **Orchestrateur** | Moteur de génération en 23 étapes |
| **Pipeline** | Automatisation de la production de contenu |
| **Projet** | Représentation d'un blog/site web |
| **Provider** | Service IA (Ollama, Gemini, OpenAI...) |
| **Readiness** | Statut de préparation à la publication |
| **Slug** | Version URL-friendly du titre |
| **Webhook** | Notification HTTP vers un service externe |
