# Guide utilisateur — Ideas Studio

> Ideas Studio est une plateforme SaaS de création de contenu SEO assistée par IA. Ce guide couvre toutes les fonctionnalités réellement disponibles dans l'interface, vérifiées contre le code au 2026-08-04 (branche `main`, commit `febbae1e`).
>
> Les fonctionnalités qui existent côté API mais ne sont pas encore branchées à une page de l'interface sont signalées par ⚠️ et regroupées en annexe (§24) plutôt que présentées comme utilisables aujourd'hui.

---

## Table des matières

1. [Vue d'ensemble & navigation](#vue-densemble--navigation)
2. [Compte & profil](#compte--profil)
3. [Projets](#projets)
4. [Équipe, rôles & invitations](#équipe-rôles--invitations)
5. [Catégories](#catégories)
6. [Callouts](#callouts)
7. [Assistant de configuration éditoriale](#assistant-de-configuration-éditoriale)
8. [Générer des idées](#générer-des-idées)
9. [Générer des articles — l'orchestrateur SEO](#générer-des-articles--lorchestrateur-seo)
10. [Analyser le SEO](#analyser-le-seo)
11. [Éditeur, versions & commentaires](#éditeur-versions--commentaires)
12. [Médiathèque](#médiathèque)
13. [Publier, programmer & calendrier éditorial](#publier-programmer--calendrier-éditorial)
14. [Configuration IA — Providers & Agents](#configuration-ia--providers--agents)
15. [Pipeline automatisé](#pipeline-automatisé)
16. [API publique du blog](#api-publique-du-blog)
17. [Analytics](#analytics)
18. [Recommandations d'optimisation](#recommandations-doptimisation)
19. [Notifications](#notifications)
20. [Search Console](#search-console)
21. [Webhooks](#webhooks)
22. [Sécurité du compte](#sécurité-du-compte)
23. [Glossaire](#glossaire)
24. [Annexe — fonctionnalités backend pas encore exposées](#annexe--fonctionnalités-backend-pas-encore-exposées)

---

## Vue d'ensemble & navigation

Un **projet** représente un blog ou site web pour lequel vous produisez du contenu. Toutes les fonctionnalités décrites ci-dessous (catégories, idées, articles, pipeline, analytics…) sont rattachées à un projet précis — vous naviguez d'un projet à l'autre depuis la liste des projets.

À l'intérieur d'un projet, la barre de recherche globale (icône loupe) interroge en une fois :
- les pages de réglages du projet (paramètres, stratégie, providers, agents, pipeline, intégration, médias…),
- les articles et idées (titre, mot-clé, extrait, contenu),
- les catégories,
- les médias (nom de fichier, texte alternatif, légende),
- les autres projets auxquels vous avez accès.

C'est un raccourci pratique pour retrouver un article ou sauter directement à un écran de configuration sans naviguer dans les menus.

---

## Compte & profil

### Créer un compte

1. Rendez-vous sur la page d'inscription.
2. Renseignez votre email, votre nom et un mot de passe.
3. Validez.

Aucune règle de complexité n'est imposée sur le mot de passe à l'inscription (au-delà du hash bcrypt appliqué en base).

### Connexion

Un token JWT est généré à la connexion et conservé pour la session. Il expire après **24h** (configurable côté serveur).

### Modifier son mot de passe

Il existe deux flux distincts, avec deux règles de longueur minimale différentes — à connaître pour éviter la confusion :

| Flux | Où | Longueur minimale |
|---|---|---|
| Changer son mot de passe depuis le compte connecté | **Compte → Changer le mot de passe** | 6 caractères |
| Réinitialiser après un « mot de passe oublié » (lien reçu par email) | Page de réinitialisation | 8 caractères |

### Avatar

1. Allez dans **Compte → Avatar**.
2. Téléchargez une image (JPEG, PNG, GIF ou WebP).
3. L'image est affichée en cercle dans l'interface, **mais elle n'est pas recadrée automatiquement** avant l'enregistrement — préférez une image déjà carrée pour un rendu propre.

---

## Projets

### Création

1. Cliquez sur **Nouveau projet**.
2. Renseignez les champs :

| Champ | Obligatoire | Description |
|---|---|---|
| Nom | Oui | Nom du projet (ex. « Blog Tech ») |
| Domaine | Non | URL du blog connecté |
| Langue (`locale`) | Non | Langue du contenu (ex. `fr`, `en`) |
| Fuseau horaire | Non | Utilisé pour la programmation des publications |
| Audience | Non | Description de l'audience cible |
| Ton | Non | Ton éditorial souhaité |
| Niveau de lecteur | Non | Niveau de lecture visé |
| Style rédactionnel | Non | Style d'écriture souhaité |
| Vertical | Non | Secteur/thématique du blog |
| Longueur d'article min/max | Non | Bornes de mots visées par défaut |
| Règles / contraintes | Non | Consignes éditoriales libres à respecter |

### Configuration

Ces mêmes champs sont modifiables à tout moment depuis les paramètres du projet, ainsi que la configuration IA (voir [§14](#configuration-ia--providers--agents)).

### Connecter un blog

1. Allez dans **Projet → Intégration**.
2. Copiez le snippet JavaScript fourni.
3. Ajoutez-le dans le `<head>` de votre blog :

```html
<script
  src="https://api.ideas-studio.com/traffic.js"
  data-project-id="VOTRE_PROJECT_ID"
  data-tracking-key="VOTRE_PUBLIC_TRACKING_KEY"
  async>
</script>
```

Le script collecte automatiquement l'URL visitée, le chemin, le referrer et le user-agent ; l'IP est utilisée côté serveur uniquement pour hasher le visiteur (jamais stockée en clair) et **aucun cookie n'est déposé**.

La page d'intégration affiche également l'ID du projet, la clé de tracking publique, la clé API secrète (masquée) et les endpoints de l'[API publique](#api-publique-du-blog).

**Statuts** : un projet est soit **non connecté** soit **connecté** (deux états seulement — il n'existe pas de troisième statut « déconnecté » distinct : l'action **Déconnecter** ramène simplement le projet à l'état non connecté, sans rien supprimer).

### Supprimer un projet

Réservé aux rôles Owner et Admin. La suppression est **définitive** : articles, catégories, médias et toutes les données associées sont supprimés en cascade.

---

## Équipe, rôles & invitations

### Les 5 rôles

| Rôle | Écrire/éditer des articles | Gérer la médiathèque | Gérer catégories, callouts, pipeline | Gérer les membres | Paramètres & suppression du projet |
|---|:---:|:---:|:---:|:---:|:---:|
| **Owner** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Admin** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Editor** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Designer** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Viewer** | ❌ (lecture seule) | ❌ (lecture seule) | ❌ | ❌ | ❌ |

Le rôle **Designer** est pensé spécifiquement pour la gestion des images et de la médiathèque, en plus de la rédaction. Le rôle **Owner ne peut jamais être réassigné ni retiré** — ni depuis l'interface, ni via l'API.

### Ajouter un membre

1. Allez dans **Projet → Membres → Ajouter un membre**.
2. Recherchez la personne par ID utilisateur ou par **@nom d'utilisateur** (elle doit déjà avoir un compte Ideas Studio).
3. Choisissez le rôle (Admin, Editor, Designer ou Viewer — le rôle Owner n'est pas proposé).
4. Validez.

Modifier un rôle ou retirer un membre suit le même principe, réservé aux rôles Owner et Admin. Chaque changement génère une notification dans le projet.

### Invitations par email

1. Allez dans **Projet → Membres → Inviter**.
2. Saisissez l'email et choisissez le rôle.
3. Un lien d'invitation est généré, valable **14 jours**. S'il n'y a pas d'envoi d'email transactionnel configuré, copiez le lien manuellement pour le transmettre.
4. La personne invitée ouvre le lien, se connecte ou crée un compte, puis accepte l'invitation.

Statuts affichés : **En attente**, **Acceptée**, **Expirée**. Une invitation en attente peut être **révoquée** à tout moment.

---

## Catégories

Les catégories organisent vos articles et pilotent la priorisation automatique de l'orchestrateur SEO et du pipeline.

### Créer une catégorie

| Champ | Description |
|---|---|
| Nom | Nom visible de la catégorie |
| Slug | Version URL-friendly, générée automatiquement |
| Description | Description de la catégorie |
| Couleur | Code hexadécimal pour l'identifier visuellement |
| Score de priorité | Un poids : **plus la valeur est élevée, plus la catégorie est favorisée** dans le choix automatique de sujet (ce n'est pas un simple ordre d'affichage) |
| Objectif éditorial | But stratégique de la catégorie |
| Audience cible | Sous-groupe d'audience visé |
| Fréquence mensuelle | Nombre d'articles visé par mois |
| Longueur min/max | Bornes de mots imposées pour les articles de cette catégorie |
| Notes internes | Notes libres, non visibles publiquement |
| Pipeline activé | Inclure cette catégorie dans les cycles du pipeline automatisé |

Les catégories avec le pipeline activé sont automatiquement prises en compte dans les cycles de génération automatique (voir [§15](#pipeline-automatisé)).

---

## Callouts

Les callouts sont des encadrés visuels (info, astuce, avertissement…) qui enrichissent le contenu d'un article.

### Créer un callout

```json
{
  "slug": "conseil",
  "label": "Conseil",
  "default_title": "À savoir",
  "color_background": "#e8f4f8",
  "color_border": "#2196F3",
  "color_text": "#0d47a1"
}
```

Il n'existe **pas de liste fermée de styles imposés** : `label` est un texte libre, et le slug se génère automatiquement à partir de celui-ci. Un jeu de couleurs par défaut est appliqué si vous ne précisez pas vos propres couleurs, pour quelques mots-clés reconnus par l'éditeur (`conseil`, `attention`, `erreur`, `succes`) — pour tout autre libellé, définissez vos couleurs manuellement afin d'obtenir un rendu cohérent.

### Synchronisation depuis le blog

Si votre blog expose sa configuration de callouts via `/api/ideas-studio/config`, vous pouvez les importer ou les mettre à jour automatiquement :

```
POST /projects/{project_id}/callouts/sync
```

---

## Assistant de configuration éditoriale

Pour démarrer rapidement un nouveau projet, un assistant peut pré-remplir la stratégie éditoriale à partir du domaine déjà connecté :

1. Depuis la page **Stratégie** du projet, lancez la suggestion.
2. L'assistant récupère les catégories existantes de votre blog et analyse la page d'accueil (titre, meta-description).
3. Si un provider IA est configuré (non-mock), il propose : une description, une audience, un ton, un positionnement, 5 à 8 mots-clés principaux, 5 à 10 catégories recommandées et des consignes de rédaction SEO.
4. Sans provider IA configuré, une suggestion générique par défaut est proposée à la place.

Vous restez libre d'ajuster chaque champ suggéré avant de l'enregistrer.

---

## Générer des idées

Le moteur d'idées utilise l'IA — enrichie par une recherche web réelle — pour proposer des sujets d'articles SEO optimisés.

### Génération simple

1. Allez dans **Intelligence → Générer une idée**.
2. Précisez, en option : titre préféré, mot-clé, catégorie, angle éditorial, intention de recherche (`informational`, `commercial`, `transactional`, `navigational`), audience, contexte additionnel, et si la FAQ/les callouts doivent être préparés dès cette étape.
3. L'idée générée contient un titre, un mot-clé principal, un angle, une intention détectée, une audience et un score d'opportunité (0.0–1.0).

Le pré-brief détaillé de l'idée (sources trouvées lors de la recherche web, justification de l'opportunité, format recommandé, difficulté estimée) est consultable séparément dans l'espace de travail de l'article — il n'apparaît pas directement dans la réponse de génération, et n'est produit que lorsqu'un vrai provider IA est configuré (pas en mode démo).

### Génération multiple & découverte

```
POST /projects/{project_id}/ideas/auto-generate     # génère N idées d'un coup
POST /projects/{project_id}/ideas/discover           # laisse la stratégie de catégorie choisir les sujets
```

### Gérer les idées

Une idée générée apparaît avec le statut « proposée ». Vous pouvez la marquer prioritaire, la rejeter (avec raison et note), la convertir en brouillon manuel, ou démarrer directement sa rédaction complète.

### Prévention des doublons

Avant de générer une idée, le système vérifie que le mot-clé n'est pas déjà utilisé par un article actif (de l'idée à la publication). Si c'est le cas, l'idée n'est pas générée.

### Le provider de recherche web

Pour enrichir les idées avec de vrais résultats de recherche (plutôt que des données inventées), Ideas Studio interroge un moteur de recherche configuré **au niveau serveur** (pas par projet) :

| Provider | Description |
|---|---|
| **Google Custom Search** | API Google officielle, nécessite une clé API + un moteur de recherche personnalisé (« cx »). Limite gratuite : 100 requêtes/jour. |
| **SearXNG** | Instance de métamoteur auto-hébergée. |
| **Mode démo (mock)** | Résultats fictifs, utilisé par défaut si rien n'est configuré. |

⚠️ Sans configuration explicite, la génération d'idées tourne silencieusement en mode démo (résultats inventés). Si une clé Google est renseignée, elle est utilisée en priorité automatiquement.

**À ne pas confondre** : ce provider sert à *trouver des sujets*. Un second système de recherche, indépendant, sert à l'**analyse concurrentielle** pendant la génération d'article complet (voir [§9](#générer-des-articles--lorchestrateur-seo)) — les deux se configurent séparément.

---

## Générer des articles — l'orchestrateur SEO

Depuis une idée, cliquez sur **Démarrer la rédaction**. Un seul mode de génération existe aujourd'hui : l'**orchestrateur**, un pipeline complet qui exécute une quarantaine d'étapes automatiques, organisées en phases.

### Les phases de l'orchestrateur

| Phase | Ce qui s'y passe |
|---|---|
| **1. Analyse & stratégie** | Contexte du projet, stratégie de catégorie, découverte de l'idée, vérification de cannibalisation SEO, analyse d'intention, brief de recherche (avec évaluation de la qualité des sources et extraction d'enseignements si des sources ont été trouvées) |
| **2. Brief éditorial** | Sélection des faits/preuves les plus fiables, brief de mots-clés, angle éditorial, plan de l'article, nouvelle vérification de cannibalisation sur le plan, plan d'images, plan de callouts, plan de FAQ, plan de liens internes et externes |
| **3. Rédaction** | Génération du contenu HTML complet de l'article |
| **4. Contrôle qualité linguistique & SEO** | Qualité de la langue, originalité, humanisation, lisibilité, EEAT, qualité éditoriale, données structurées, optimisation GEO (moteurs de réponse IA), checklist SEO finale, revue SEO agrégée |
| **5. Révision par agents IA** *(si des agents sont configurés — [§14](#configuration-ia--providers--agents))* | Extraction des affirmations vérifiables, fact-checking, revue éditoriale, vérification de la rétention lecteur, revue d'engagement, optimisation SEO, notation qualité |
| **6. Score & amélioration automatique** | Notation globale de l'article, puis jusqu'à 2 cycles d'amélioration ciblés automatiquement sur les points faibles détectés (EEAT, SEO, lisibilité, originalité, GEO) |
| **7. Clôture** | Analyse des éventuelles erreurs rencontrées, rapport de génération final |

Certaines étapes sont conditionnelles (dépendent de la disponibilité de sources de recherche ou d'agents IA configurés) — le nombre exact d'étapes exécutées varie donc légèrement d'un article à l'autre. C'est normal.

### Contenu généré

- Contenu HTML de l'article (compatible avec l'éditeur riche)
- Plan structuré, FAQ, callouts extraits
- Métadonnées SEO (meta title, meta description)
- Extrait, temps de lecture
- Rapport de génération complet : provider et modèle utilisés, outils disponibles/configurés, étapes complétées, erreurs éventuelles, coûts estimés et réels

### Autres options

- **Relancer** — régénère le contenu d'un article existant.
- **Brouillon manuel** — crée un squelette d'article à partir du plan, sans passer par la génération complète.

---

## Analyser le SEO

### Analyse manuelle

Ouvrez un article puis cliquez sur **Analyser SEO** — les résultats s'affichent immédiatement.

### Scores

| Score | Plage | Description |
|---|---|---|
| **SEO** | 0-100 | Positionnement mot-clé, meta, slug, structure |
| **Lisibilité** | 0-100 | Longueur phrases/paragraphes, intro, sous-titres |
| **Qualité** | 0-100 | Longueur article, conclusion, image de couverture |
| **EEAT** | 0-100 | Liens externes, exemples/statistiques, actionnabilité |

### Statut de préparation (Readiness)

| Statut | Signification |
|---|---|
| `ready` | Prêt à publier |
| `needs_improvement` | Améliorations suggérées |
| `blocked` | Problèmes bloquants à corriger |

### Ready Check

Avant de publier, lancez un **Ready Check** pour obtenir une synthèse : les 4 scores, la liste des problèmes bloquants, et une indication claire « publiable ou non ».

Catégories d'issues détectées : SEO (mot-clé absent du titre, pas de H1, meta title trop long…), Lisibilité (phrases trop longues, paragraphes trop denses…), Qualité (contenu de démonstration, article trop court, pas de conclusion…), EEAT (pas de liens externes, pas d'exemples ni de données chiffrées…).

---

## Éditeur, versions & commentaires

### Éditeur riche

L'éditeur (TipTap) offre le formatage riche (gras, italique, listes, tableaux, citations), la gestion des titres H1/H2/H3, l'insertion d'images depuis la médiathèque, la sauvegarde automatique et un compteur de mots.

### Autosave & versions

L'éditeur sauvegarde automatiquement **2 secondes après votre dernière modification** (pas sur un intervalle fixe). Chaque sauvegarde distincte crée une nouvelle version dans l'historique — aux côtés des sauvegardes manuelles explicites et des versions issues d'une restauration.

**Restaurer une version :**
1. Ouvrez l'historique des versions.
2. Sélectionnez la version voulue.
3. Confirmez — l'état courant est d'abord sauvegardé, puis la version choisie est appliquée comme nouvelle version courante (rien n'est écrasé, l'historique reste complet).

### Commentaires inline

1. Sélectionnez du texte dans l'article.
2. Cliquez sur l'icône commentaire et rédigez votre remarque.
3. Un commentaire peut être marqué comme résolu une fois traité.

### Preview

L'aperçu montre l'article tel qu'il apparaîtra sur le blog, même pour un brouillon non publié.

---

## Médiathèque

Chaque projet dispose d'une bibliothèque d'images dédiée.

- **Formats acceptés** : JPEG, PNG, WebP, GIF, SVG (uniquement des images).
- **Taille maximale** : 10 Mo par fichier.
- **Import** : sélection multi-fichiers, glisser-déposer possible depuis la page Médiathèque.
- **Stockage** : sur disque par défaut, ou vers un service de stockage externe si celui-ci est configuré pour le projet.
- **Utilisation** : copiez l'URL d'un média pour l'insérer manuellement dans le corps d'un article via l'éditeur. Il n'existe pas encore de champ dédié « image de couverture » séparé du contenu.
- **Permissions** : upload et suppression réservés aux rôles Owner, Admin, Editor et Designer. Le rôle Viewer est en lecture seule.

---

## Publier, programmer & calendrier éditorial

### Publication immédiate

1. Vérifiez que l'article est prêt à publier (statut brouillon prêt ou similaire).
2. Lancez un **Ready Check** pour écarter les problèmes bloquants.
3. Cliquez sur **Publier**.
4. Le contenu, le titre, l'extrait, la meta description, l'image de couverture, la FAQ et les callouts sont figés dans la version publiée, et la date de publication est enregistrée.
5. Si une URL de revalidation est configurée pour le blog, le cache est invalidé automatiquement.

### Programmation

1. Cliquez sur **Programmer**, choisissez la date et l'heure.
2. L'article passe au statut « programmé ».
3. Le worker publie automatiquement l'article à l'échéance (vérification toutes les 5 minutes).

### Mettre à jour un article publié

Modifiez librement le brouillon (il est distinct de la version publiée), puis utilisez **Promouvoir** pour remplacer la version publiée par le brouillon. Les changements sont visibles immédiatement après promotion.

### Dépublier / archiver

**Dépublier** repasse l'article en brouillon tout en conservant la dernière version publiée en mémoire. **Archiver** retire l'article des listes actives sans le supprimer.

### Calendrier éditorial

La page **Calendrier** propose deux vues :
- **Vue Liste**, groupée par mois.
- **Vue Mois**, en grille, avec un code couleur par statut (idée, en rédaction, programmé, publié) — cliquer sur un article ouvre directement son éditeur.

Une **heatmap annuelle** façon « contributions GitHub » visualise votre rythme de publication sur l'année, sélectionnable année par année.

---

## Configuration IA — Providers & Agents

La configuration IA d'un projet se fait en deux étapes, réservées aux rôles Owner et Admin.

### 1. Providers — connecter une clé API

Un **provider** est une clé API pour une plateforme IA (Ollama, OpenRouter, OpenAI, Gemini, Mistral et autres selon le catalogue disponible) rattachée à votre projet. Pour Ollama, l'absence de clé pointe vers une instance locale (`127.0.0.1:11434`), tandis qu'une clé renseignée bascule sur Ollama Cloud.

Pour chaque provider configuré : un libellé, la clé API (masquée, révélable via l'icône œil), le modèle par défaut, un statut de connexion, et un bouton **Tester** qui vérifie réellement l'accès au provider. Les clés API sont chiffrées en base — jamais renvoyées en clair par l'API.

### 2. Agents — assigner un provider à chaque étape

Un **agent** correspond à une étape précise du pipeline de génération (rédacteur, recherche de mots-clés, optimisation SEO, fact-checking…). Il en existe 62 dans le registre, regroupés par catégorie (Recherche, Stratégie, Création, Révision).

Pour chaque agent, vous choisissez un provider dans une liste déroulante (ou utilisez **Tout assigner** pour tout affecter au même provider en une fois). Un agent sans assignation utilise le provider par défaut du projet. Le modèle utilisé n'est pas choisi ici — il provient de la configuration du provider.

Chaque agent affiche un statut :

| Statut | Signification |
|---|---|
| **Actif** | Fonctionne pleinement, utilise un provider IA assigné (47 agents actuellement) |
| **Heuristique** (« Sans LLM ») | Fonctionne par règles internes, sans appel à un modèle IA — aucun provider ne peut lui être assigné (7 agents) |
| **Partiel** | Dépend d'un service externe complémentaire (recherche web, tendances…) (8 agents) |

---

## Pipeline automatisé

Le pipeline automatise la production régulière de contenu.

### Configuration

| Paramètre | Défaut | Description |
|---|---|---|
| Activé | `false` | Active/désactive le pipeline |
| Jours actifs | `[]` | Jours de la semaine concernés |
| Heure de lancement | `8` | Heure de déclenchement visée (0-23) |
| Articles par semaine | `5` | Objectif hebdomadaire |
| Idées par semaine | `5` | Nombre d'idées à générer |
| Priorités par catégorie | `{}` | Répartition en pourcentage |
| Max brouillons en attente | `10` | Limite de brouillons non publiés avant pause automatique |
| Plafond de coût par article | — | Au-delà, l'article passe au statut « Bloqué (coût) » |
| Pause | — | Temporaire (jusqu'à une date) ou indéfinie |

### Fonctionnement réel

Trois tâches automatiques tournent en arrière-plan, indépendamment :

- **Publications programmées** — vérifiées toutes les 5 minutes.
- **Génération d'idées** — une vérification a lieu chaque heure, mais le pipeline ne se déclenche réellement qu'une fois par échéance configurée (le rythme dépend de l'objectif mensuel par catégorie), pas à chaque vérification horaire.
- **File de rédaction** — traitée toutes les 2 minutes.

### Logs du pipeline

Chaque exécution est journalisée avec un statut : `running`, `success`, `partial_success` ou `failed`, ainsi que le nombre d'idées générées et les erreurs éventuelles.

---

## API publique du blog

Une fois votre blog connecté ([§3](#projets)), il peut récupérer vos contenus publiés sans authentification :

```
GET /api/public/projects/{project_id}/articles
GET /api/public/projects/{project_id}/articles/{slug}
GET /api/public/projects/{project_id}/categories
```

Seuls les articles publiés sont retournés, sans cache CDN par défaut (`Cache-Control: no-store`).

```javascript
const response = await fetch(
  'https://api.ideas-studio.com/api/public/projects/{project_id}/articles'
);
const articles = await response.json();
```

---

## Analytics

Une seule page **Analytics** regroupe désormais les statistiques de trafic interne et les données Google Analytics 4 (les anciens menus « Performance » et « Trafic » redirigent automatiquement ici).

### Statistiques internes

Basées sur le script de tracking installé sur votre blog ([§3](#projets)) : vues totales, vues moyennes par jour, tendance par canal (direct/organique/referral/social), sources, pays, appareils, score SEO moyen, top articles, et une section « à auditer maintenant ». Périodes disponibles : nombre de jours au choix, périodes prédéfinies (jour/semaine/mois/trimestre/semestre/année) ou plage de dates personnalisée.

Un indicateur `tracking_status` explique pourquoi le résumé peut être vide : blog non connecté, connecté mais sans données encore, ou connecté avec des données.

### Google Analytics 4 (optionnel)

Si un compte GA4 est connecté au projet, un second bloc affiche visiteurs uniques, sessions, pages vues, durée moyenne, taux de rebond, articles les plus vus et sources de trafic côté GA4.

Export des données disponible en JSON ou PDF.

---

## Recommandations d'optimisation

Le moteur d'optimisation analyse automatiquement les articles publiés et propose des améliorations.

### Types de recommandations

| Type | Déclencheur |
|---|---|
| `fix_low_traffic` | Moins de 5 vues à J+30 ou J+90 |
| `add_faq` | Article sans FAQ |
| `improve_meta_description` | Meta description absente ou < 120 caractères |
| `improve_title` | Score SEO < 50 |
| `add_internal_links` | Aucun lien interne détecté |

### Gérer les recommandations

**Accepter** et **Rejeter** sont ouverts à tout membre du projet. **Appliquer** est réservé aux rôles Owner, Admin et Editor. Une recommandation identique en attente pour le même article bloque toute nouvelle création en doublon.

---

## Notifications

Les notifications informent l'équipe des événements importants du projet : ajout/modification/retrait de membre, invitation, idées mensuelles prêtes, recommandation d'optimisation, échec de génération, article prêt après génération, ou message système.

Actions disponibles : marquer une notification comme lue, tout marquer comme lu, supprimer. Chaque notification affiche un niveau — `info`, `warning` ou `error`.

---

## Search Console

L'intégration Google Search Console permettra de visualiser vos données de recherche Google directement dans Ideas Studio.

**Statut actuel : non disponible.** L'intégration nécessite une configuration OAuth Google prévue pour une version ultérieure — les endpoints (`status`, `keywords`, `pages`, `performance`) renvoient aujourd'hui systématiquement un statut « non connecté ».

---

## Webhooks

Les webhooks permettent, en théorie, de notifier un service externe (Slack, Discord, Zapier…) lors d'événements du projet.

**Ce qui fonctionne aujourd'hui** : créer, lister, modifier et supprimer un webhook via l'API, avec une signature HMAC-SHA256 (header `X-IdeasStudio-Signature`) et un bouton de **test manuel** qui envoie effectivement une requête au webhook.

⚠️ **Ce qui ne fonctionne pas encore** : le déclenchement automatique lors d'un événement réel (publication d'article, génération d'idée…) n'est pas implémenté — seul le test manuel envoie une requête. Il n'existe pas non plus de page dédiée dans l'interface actuellement ; la configuration se fait via l'API.

---

## Sécurité du compte

- Les tokens JWT expirent après 24h.
- Les mots de passe sont hashés avec **bcrypt**.
- Les clés API des providers IA et les secrets de webhooks sont chiffrés en base (chiffrement symétrique réversible).
- Les clés de tracking et d'API publique sont stockées sous forme de hash non réversible (comparaison rapide, jamais déchiffrables).
- Une couche de sécurité supplémentaire au niveau base de données (Row-Level Security PostgreSQL, en complément des vérifications de rôle applicatives) est en préparation mais **n'est pas encore activée en production** — elle n'a aucun impact visible pour vous à ce stade.

---

## Glossaire

| Terme | Définition |
|---|---|
| **Agent** | Étape du pipeline de génération associée à un provider IA (62 au total) |
| **Article** | Contenu publié ou en cours de rédaction |
| **Brouillon** | Article non publié |
| **Callout** | Encadré visuel dans un article |
| **Catégorie** | Groupe thématique d'articles |
| **EEAT** | Experience, Expertise, Authoritativeness, Trustworthiness |
| **Excerpt** | Extrait court de l'article |
| **GEO** | Optimisation pour les moteurs de réponse IA (Generative Engine Optimization) |
| **LLM** | Large Language Model (modèle de langage) |
| **Meta description / Meta title** | Champs SEO affichés dans les résultats de recherche |
| **Orchestrateur** | Pipeline de génération d'article en une quarantaine d'étapes |
| **Pipeline** | Automatisation de la production de contenu |
| **Provider** | Service IA connecté au projet (Ollama, OpenAI, Gemini…) |
| **Ready Check** | Vérification synthétique avant publication |
| **Readiness** | Statut de préparation à la publication |
| **SERP** | Résultats de recherche web utilisés pour enrichir la génération |
| **Slug** | Version URL-friendly d'un titre |
| **Version (révision)** | Snapshot du contenu d'un article, conservé dans l'historique |

---

## Annexe — fonctionnalités backend pas encore exposées

Ces éléments existent dans l'API mais ne sont pas (ou pas encore) utilisables depuis l'interface. Ils sont listés ici par souci de transparence plutôt que présentés comme des fonctionnalités actives :

| Fonctionnalité | État |
|---|---|
| **Déclenchement automatique des webhooks** | CRUD et test manuel fonctionnent ; aucun événement réel (publication, génération…) ne déclenche encore un webhook automatiquement. Pas de page dédiée dans l'interface. |
| **Colonnes Kanban personnalisées** | L'API existe (créer/modifier des colonnes), mais la route `/kanban` de l'interface redirige vers la page Production — il n'y a pas de tableau kanban actif à ce jour. |
| **Journal d'activité projet** | L'endpoint de lecture existe mais rien n'écrit encore d'entrées dans ce journal — il renvoie systématiquement une liste vide. |
| **Monitoring éditorial (amélioration continue des articles publiés)** | Le scan automatique et la génération de propositions d'amélioration existent côté API, mais aucun bouton ni écran ne les déclenche depuis l'interface actuellement. |
| **Détail des coûts IA par génération** | Un coût estimé/réel est calculé et stocké pour chaque génération, mais n'est affiché nulle part dans l'interface — seul le plafond de coût par article (§15) a un effet visible (statut « Bloqué (coût) »). |
