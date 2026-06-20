# Flux complet de fonctionnement — Ideas Studio SEO/GEO Expert

## 1. Vision générale du système

Ideas Studio est un studio éditorial SEO/GEO assisté par IA.

Son rôle n’est pas seulement de générer un article. Son rôle est de piloter tout le cycle éditorial, depuis la stratégie du projet jusqu’au suivi après publication.

Le système couvre :

1. configuration du projet ;
2. définition des catégories éditoriales ;
3. configuration des providers IA ;
4. configuration des agents ;
5. planification éditoriale ;
6. découverte des vraies demandes des internautes ;
7. proposition d’idées ;
8. préparation de pré-briefs ;
9. validation humaine ;
10. transformation en brief de production ;
11. estimation du coût de génération ;
12. rédaction assistée par agents ;
13. enrichissement du contenu ;
14. génération des données structurées ;
15. optimisation SEO/GEO ;
16. contrôle qualité ;
17. suivi du coût réel ;
18. génération d’un rapport complet ;
19. relecture humaine ;
20. planification ou publication manuelle ;
21. affichage sur le site public ;
22. tracking conforme ;
23. monitoring post-publication ;
24. proposition d’amélioration ;
25. rollback possible si une mise à jour pose problème.

La règle centrale est simple :

Les agents préparent, analysent, rédigent, vérifient et recommandent.
L’humain valide, corrige, planifie et publie.

Aucun article ne doit être publié automatiquement sans validation humaine.

---

## 2. Principe métier global

Le flux complet doit fonctionner comme une vraie chaîne éditoriale.

Le système ne doit jamais fonctionner comme ceci :

```txt
Utilisateur donne un mot-clé
→ Gemini écrit un article
→ article publié
```

La bonne logique est :

```txt
Catégorie
→ demande réelle
→ sujet prouvé
→ mots-clés
→ recherche
→ intention
→ concurrence
→ angle
→ plan
→ brief final
→ coût estimé
→ rédaction
→ métas
→ FAQ
→ données structurées
→ médias
→ liens
→ SEO/GEO
→ qualité
→ originalité
→ fact-checking
→ rapport
→ relecture humaine
→ planification/publication
→ monitoring
```

Chaque étape doit produire une donnée exploitable.

Exemples :

* `category_context_json`
* `demand_discovery_json`
* `topic_selection_json`
* `keyword_brief_json`
* `serp_analysis_json`
* `extracted_sources_json`
* `content_gap_json`
* `research_brief_json`
* `source_quality_report_json`
* `evidence_pack_json`
* `intent_analysis_json`
* `cannibalization_initial_json`
* `editorial_angle_json`
* `outline_json`
* `production_brief_json`
* `estimated_cost_json`
* `style_guide_json`
* `content_html`
* `faq_json`
* `structured_data_json`
* `media_plan_json`
* `internal_links_json`
* `external_links_json`
* `seo_review_json`
* `geo_optimization_json`
* `language_quality_report_json`
* `originality_report_json`
* `claims_json`
* `fact_check_report_json`
* `eeat_checklist_json`
* `generation_report_json`

Le principe central est :

```txt
Agent
→ sortie JSON
→ sauvegarde DB
→ affichage UI
→ décision humaine
```

---

## 3. Les grands intervenants

## 3.1 Utilisateur humain

L’utilisateur peut avoir plusieurs rôles :

* owner ;
* admin ;
* editor ;
* writer ;
* viewer.

Le owner/admin peut configurer :

* projet ;
* catégories ;
* fréquence éditoriale ;
* providers IA ;
* agents ;
* pipeline ;
* intégrations ;
* membres ;
* permissions ;
* budget IA ;
* tracking ;
* publication.

L’editor peut généralement :

* relire ;
* corriger ;
* valider ;
* demander amélioration ;
* planifier ;
* publier selon permission.

Le writer peut généralement :

* créer ;
* éditer ;
* travailler sur des brouillons ;
* proposer des corrections ;
* envoyer en review.

Le viewer consulte seulement.

## 3.2 Frontend CMS

Le frontend est l’interface visible par l’utilisateur.

Il contient :

* Dashboard ;
* Articles ;
* Catégories ;
* Idées ;
* Production ;
* Médias ;
* Calendrier ;
* Performance ;
* Trafic ;
* Optimisations ;
* Génération IA ;
* Notifications ;
* Paramètres ;
* Providers IA ;
* Agents IA ;
* Pipeline ;
* Éditeur d’article ;
* Compte ;
* Documentation publique hors CMS.

Le frontend ne décide pas du workflow.
Il affiche l’état, déclenche les actions, montre les résultats et permet à l’humain de valider.

## 3.3 Backend

Le backend est le cerveau applicatif.

Il gère :

* projets ;
* rôles ;
* permissions ;
* articles ;
* idées ;
* catégories ;
* agents ;
* providers ;
* assignations ;
* pipeline ;
* workflow runs ;
* logs ;
* coûts ;
* rapports ;
* publication ;
* API publique ;
* tracking ;
* erreurs ;
* snapshots ;
* rollback.

## 3.4 Agent Registry

L’Agent Registry est la liste officielle des agents disponibles.

Il contient pour chaque agent :

* `agent_key` ;
* nom ;
* description ;
* phase du workflow ;
* obligatoire ou optionnel ;
* désactivable ou non ;
* besoin LLM ou non ;
* besoin search ou non ;
* besoin scraper ou non ;
* besoin API externe ou non ;
* support fallback ou non ;
* provider par défaut ;
* modèle par défaut ;
* statut.

Le frontend ne doit jamais inventer la liste des agents.

Il doit récupérer les agents depuis le backend.

## 3.5 AgentRouter

L’AgentRouter est l’aiguilleur technique des agents.

Il reçoit :

* `project_id` ;
* `agent_key` ;
* contexte ;
* messages ;
* format attendu ;
* contraintes ;
* budget restant.

Il lit :

* provider assigné ;
* modèle assigné ;
* fallback éventuel ;
* clé API chiffrée côté backend ;
* paramètres de l’agent ;
* limite de coût ;
* nombre de retries.

Il exécute l’agent, puis retourne :

* agent_key ;
* provider utilisé ;
* modèle utilisé ;
* statut ;
* durée ;
* tokens input ;
* tokens output ;
* coût estimé/réel ;
* fallback utilisé ou non ;
* erreur éventuelle ;
* output.

Aucun agent ne doit appeler directement un provider sans passer par AgentRouter.

## 3.6 Scheduler / Worker

Le scheduler permet de lancer automatiquement certaines actions :

* génération des idées du mois ;
* remplacement d’idées rejetées ;
* production assistée ;
* vérification d’articles planifiés ;
* publication d’articles déjà planifiés par un humain ;
* monitoring après publication ;
* notifications.

Le scheduler ne doit jamais décider seul de publier un article non validé.

Il peut publier un article planifié uniquement si l’humain l’a déjà validé et programmé.

## 3.7 Base de données

La base de données garde :

* projets ;
* catégories ;
* idées ;
* articles ;
* statuts ;
* contenus ;
* briefs ;
* sorties JSON ;
* rapports ;
* sources ;
* providers ;
* assignations ;
* coûts ;
* logs ;
* erreurs ;
* versions ;
* snapshots ;
* événements de tracking ;
* notifications.

## 3.8 Site public

Le site public n’est pas l’éditeur.

Il consomme uniquement les contenus publiés via l’API publique.

Il affiche :

* articles publiés ;
* catégories ;
* contenu HTML ;
* FAQ ;
* callouts ;
* médias ;
* métas SEO ;
* données structurées ;
* liens ;
* auteur ;
* date ;
* temps de lecture.

Le site public renvoie aussi des événements de tracking à Ideas Studio, selon les règles de consentement.

---

# 4. Structure produit des pages

## 4.1 Menu final du CMS

Ordre final attendu :

```txt
Dashboard

ÉDITORIAL
1. Articles
2. Catégories
3. Idées
4. Production
5. Médias
6. Calendrier

INTELLIGENCE
1. Performance
2. Trafic
3. Optimisations
4. Génération IA
5. Notifications

PROJET
1. Paramètres
```

Règles :

* ne pas supprimer de pages utiles ;
* ne pas créer de doublons ;
* `Production` remplace visuellement `Kanban` ;
* `Articles` reste la bibliothèque complète ;
* `Idées` est le backlog IA avant rédaction ;
* `Production` est le workflow visuel après validation ;
* `Calendrier` affiche les dates.

## 4.2 Séparation Idées / Production / Articles / Calendrier

La séparation correcte est :

```txt
Catégories = stratégie éditoriale
Idées = avant rédaction
Production = pendant rédaction / relecture
Articles = bibliothèque complète du CMS
Calendrier = dates
```

Plus précisément :

* Catégories définissent les thèmes, fréquences, priorités et règles.
* Idées contient les sujets proposés avant rédaction.
* Production contient uniquement les idées validées entrées dans le workflow.
* Articles contient tous les contenus réels du CMS.
* Calendrier affiche les dates de rédaction, relecture, planification et publication.

Il ne doit pas y avoir deux pages qui ressemblent à deux Kanban.

---

# 5. Configuration du projet

## 5.1 Page Dashboard

Le Dashboard affiche :

* nombre d’articles ;
* articles publiés ;
* brouillons ;
* idées à valider ;
* contenus en production ;
* trafic récent ;
* alertes ;
* état des providers IA ;
* état du pipeline ;
* coûts récents ;
* actions importantes.

Le Dashboard donne l’état global du projet.

Il ne doit pas remplacer les pages spécialisées.

## 5.2 Page Paramètres

La page Paramètres permet de configurer :

* informations générales ;
* langue ;
* public ciblé ;
* ton éditorial ;
* stratégie ;
* intégration site ;
* équipe ;
* providers IA ;
* agents ;
* pipeline ;
* budget IA ;
* tracking ;
* callouts ;
* sécurité.

Exemples de champs projet :

* langue principale ;
* public ciblé ;
* niveau du lecteur ;
* ton souhaité ;
* sujets autorisés ;
* sujets interdits ;
* style d’écriture ;
* longueur moyenne des articles ;
* fréquence de publication ;
* jours préférés de publication ;
* coût maximum par article ;
* coût maximum mensuel ;
* consentement tracking requis ou non.

Ces données deviennent le contexte du workflow.

## 5.3 Page Catégories

La page Catégories est la base de la planification.

Chaque catégorie doit pouvoir contenir :

* nom ;
* slug ;
* description ;
* priorité ;
* fréquence mensuelle ;
* public cible ;
* niveau de profondeur ;
* format préféré ;
* longueur cible ;
* mots-clés principaux associés ;
* jours préférés de publication ;
* statut actif/inactif ;
* consignes éditoriales propres ;
* sujets interdits dans cette catégorie.

Exemple :

```txt
Catégorie : SEO
Fréquence : 6 articles/mois
Public : créateurs de contenu francophones
Format : guide pratique
Niveau : débutant à intermédiaire
Objectif : contenus utiles, actionnables, structurés
```

Le système commence toujours par une catégorie avant de chercher des idées.

---

# 6. Providers IA et agents

## 6.1 Page Providers IA

L’utilisateur doit pouvoir connecter ses providers depuis le CMS.

Providers possibles :

* Gemini ;
* OpenAI ;
* Anthropic / Claude ;
* OpenRouter ;
* Mistral ;
* Ollama ;
* Custom OpenAI-compatible.

Chaque provider contient :

* type ;
* nom affiché ;
* base URL optionnelle ;
* clé API ;
* modèle par défaut ;
* statut actif/inactif ;
* dernier test ;
* dernière erreur ;
* bouton tester ;
* bouton modifier ;
* bouton désactiver.

Règles :

* aucune clé API dans le frontend ;
* aucune clé hardcodée ;
* clés chiffrées côté backend ;
* clé complète jamais renvoyée après sauvegarde ;
* affichage masqué du type `********AB12`.

## 6.2 Page Agents IA

La page Agents affiche tous les agents du backend.

Chaque ligne agent affiche :

* nom ;
* description ;
* phase ;
* requis ou optionnel ;
* activé/désactivé ;
* provider principal ;
* modèle principal ;
* fallback activé ou non ;
* provider fallback ;
* modèle fallback ;
* statut.

Règles :

* tous les agents du backend doivent apparaître ;
* un agent actif doit avoir un provider principal ;
* fallback optionnel ;
* pas deux providers en parallèle pour le même agent ;
* fallback utilisé seulement si le provider principal échoue ;
* les agents critiques peuvent être non désactivables.

## 6.3 Assignation agent ↔ provider

Chaque agent est assigné à :

```txt
1 provider principal
+ 1 modèle principal
+ 1 fallback optionnel
```

Exemple :

```txt
writer → Gemini / gemini-2.5-flash
seo_optimizer → OpenAI / gpt-4.1-mini
fact_checker → Claude / claude-sonnet
meta_writer → Gemini / gemini-2.5-flash
```

La configuration est par projet.

---

# 7. Contrôle des coûts IA

## 7.1 Problème à éviter

Le workflow peut contenir beaucoup d’agents.

Si chaque agent appelle un LLM sans limite, le système peut coûter trop cher par article.

Il faut donc contrôler :

* coût estimé avant lancement ;
* coût réel pendant exécution ;
* coût total par article ;
* coût mensuel par projet ;
* coût par provider ;
* coût par agent ;
* arrêt automatique si limite dépassée.

## 7.2 Service `cost_estimator`

`cost_estimator` intervient avant le lancement du workflow de production.

Il reçoit :

* article ou idée ;
* agents à exécuter ;
* provider de chaque agent ;
* modèle de chaque agent ;
* prix par modèle ;
* estimation tokens input ;
* estimation tokens output ;
* nombre maximum de retries ;
* fallback éventuel.

Il produit :

* `estimated_cost_json`.

Exemple :

```json
{
  "estimated_cost_eur": 0.42,
  "currency": "EUR",
  "cost_limit_eur": 1.50,
  "breakdown": [
    {
      "agent_key": "writer",
      "provider": "gemini",
      "model": "gemini-2.5-flash",
      "estimated_input_tokens": 12000,
      "estimated_output_tokens": 2500,
      "estimated_cost_eur": 0.18
    }
  ],
  "fallback_risk_cost_eur": 0.10,
  "status": "within_limit"
}
```

Le frontend peut afficher :

```txt
Coût estimé : environ 0,42 €
Limite article : 1,50 €
```

Si le coût n’est pas estimable :

```txt
Coût estimé indisponible pour un ou plusieurs modèles.
```

Le système ne doit pas inventer un faux coût.

## 7.3 Service `cost_tracker`

`cost_tracker` fonctionne à chaque appel AgentRouter.

Il logge :

* project_id ;
* article_id ;
* workflow_run_id ;
* agent_key ;
* provider ;
* model ;
* status ;
* fallback_used ;
* duration_ms ;
* input_tokens ;
* output_tokens ;
* total_tokens ;
* estimated_cost ;
* actual_cost ;
* error_message ;
* created_at.

Ces données alimentent :

* `ai_usage_logs` ;
* `generation_report_json` ;
* dashboard coûts ;
* notifications si dépassement.

## 7.4 Seuil maximum par article

Chaque projet doit pouvoir définir :

```txt
cost_limit_per_article_eur
```

Exemple :

```txt
Coût maximum par article : 1,50 €
```

Si le coût cumulé dépasse ce seuil :

1. le pipeline s’arrête ;
2. le statut devient `blocked_cost_limit` ;
3. une notification est envoyée ;
4. le rapport indique l’agent où le dépassement a eu lieu.

Exemple :

```json
{
  "status": "blocked",
  "reason": "cost_limit_exceeded",
  "current_cost_eur": 1.62,
  "cost_limit_eur": 1.50,
  "blocked_at_agent": "fact_checker",
  "next_action": "human_review_required"
}
```

Le système ne doit jamais continuer en boucle si le coût dépasse le seuil.

---

# 8. Planification éditoriale

## 8.1 Déclenchement

La planification peut être déclenchée :

1. manuellement depuis la page Idées ;
2. automatiquement par le scheduler.

Exemple :

```txt
Le 27 de chaque mois, le système prépare les idées du mois suivant.
```

Il lit :

* catégories actives ;
* fréquence mensuelle ;
* priorité ;
* jours préférés ;
* stratégie du projet ;
* articles existants ;
* idées déjà proposées ;
* contenus déjà planifiés ;
* pipeline actif ou non.

## 8.2 Calcul du volume d’idées

Exemple :

```txt
SEO : 6 articles/mois
Analytics : 4 articles/mois
IA : 4 articles/mois
Web Design : 2 articles/mois
```

Total :

```txt
16 idées à proposer pour le mois suivant.
```

Le système répartit les dates pour :

* éviter de tout publier le même jour ;
* respecter les fréquences ;
* espacer les catégories ;
* garder une régularité ;
* éviter les trous trop longs.

Chaque idée reçoit :

* date cible de rédaction ;
* date cible de relecture ;
* date cible de publication.

Ces dates restent modifiables par l’humain.

---

# 9. Phase 1 — Découverte de la demande et choix du sujet

## 9.1 Agent `category_context_builder`

Rôle :

Préparer le cadre de recherche à partir de la catégorie.

Il reçoit :

* project_id ;
* category_id ;
* langue ;
* public cible ;
* fréquence ;
* stratégie ;
* règles éditoriales ;
* sujets interdits ;
* historique articles.

Il produit :

* `category_context_json`.

Ce JSON contient :

* catégorie ciblée ;
* audience ;
* langue ;
* objectif éditorial ;
* fréquence ;
* niveau de profondeur ;
* contraintes ;
* angle général attendu.

## 9.2 Agent `demand_discovery`

Rôle :

Trouver les vraies demandes des internautes.

Il collecte :

* questions fréquentes ;
* formulations réelles ;
* tendances ;
* problèmes exprimés ;
* recherches associées ;
* suggestions ;
* discussions publiques ;
* signaux Search Console si disponibles ;
* signaux de performance interne si disponibles.

Sources possibles :

* SERP ;
* People Also Ask ;
* autocomplete ;
* Google Trends ;
* Search Console ;
* forums publics ;
* Reddit public ;
* Quora public ;
* commentaires publics ;
* documentation ;
* contenus concurrents ;
* sources configurées.

Il produit :

* `demand_discovery_json`.

Chaque demande doit contenir :

* texte ;
* source ;
* preuve ;
* catégorie ;
* fréquence apparente ;
* niveau de confiance ;
* opportunité possible.

## 9.3 Agent `topic_selector`

Rôle :

Transformer les demandes trouvées en sujets éditoriaux.

Il reçoit :

* `category_context_json` ;
* `demand_discovery_json` ;
* articles existants ;
* idées déjà proposées ;
* fréquence restante ;
* stratégie éditoriale.

Il ne choisit jamais au hasard.

Chaque sujet doit être justifié par :

* demande réelle ;
* cohérence catégorie ;
* opportunité ;
* absence de doublon évident ;
* intention probable ;
* raison éditoriale.

Il produit :

* `topic_selection_json`.

Chaque idée contient :

* titre proposé ;
* catégorie ;
* thème ;
* mot-clé initial ;
* audience ;
* preuves ;
* raison ;
* score de confiance ;
* score d’opportunité initial.

---

# 10. Page Idées

La page Idées est le backlog éditorial intelligent.

Elle ne doit pas être un mini-kanban.

Elle affiche les idées proposées avant rédaction.

## 10.1 Colonnes principales

Colonnes visibles recommandées :

* checkbox ;
* score ;
* priorité ;
* titre / résumé court ;
* catégorie ;
* mot-clé principal ;
* statut ;
* date cible publication ;
* dernier agent terminé ;
* prochain agent ;
* coût estimé si disponible ;
* actions.

Il ne faut pas afficher trop de colonnes si cela rend le tableau illisible.

## 10.2 Drawer de détail

Les détails longs doivent être dans un drawer ou modal.

Le drawer affiche :

* pré-brief complet ;
* preuves ;
* intention ;
* audience ;
* mots-clés ;
* angle éditorial ;
* résumé attendu ;
* réponse principale attendue ;
* format recommandé ;
* longueur cible ;
* difficulté estimée ;
* score d’opportunité ;
* justification du score ;
* dates cible rédaction/relecture/publication ;
* FAQ prévue oui/non ;
* médias nécessaires ;
* liens internes suggérés ;
* liens externes suggérés ;
* sorties JSON ;
* agents exécutés ;
* dernier agent terminé ;
* prochain agent ;
* coût estimé.

## 10.3 Actions individuelles

Actions possibles :

* voir détail ;
* modifier ;
* prioriser ;
* rejeter ;
* demander remplacement ;
* valider ;
* envoyer en production ;
* lancer rédaction si autorisé.

Si une action n’a pas de backend réel, elle doit être cachée ou désactivée avec explication.

Aucun bouton mort.

## 10.4 Validation par lot

La page Idées doit permettre la validation en masse.

Chaque ligne peut être cochée.

Actions groupées :

* valider la sélection ;
* rejeter la sélection ;
* prioriser la sélection ;
* envoyer la sélection en production ;
* demander remplacement pour la sélection.

Exemple :

```txt
5 idées sélectionnées → Valider la sélection
```

Le système doit alors :

1. vérifier les statuts ;
2. vérifier que chaque pré-brief est complet ;
3. verrouiller le brief final ;
4. envoyer les idées valides en Production ;
5. afficher les idées ignorées et pourquoi.

## 10.5 Validation rapide selon score

Le système utilise un score de confiance.

Exemple :

```txt
score_confiance >= 85/100
```

Règles :

* score élevé : validation rapide possible ;
* score moyen : drawer recommandé ;
* score faible : drawer obligatoire.

Exemple :

```txt
92/100 → Valider rapidement
68/100 → Voir détail avant validation
41/100 → Validation directe désactivée
```

Cela garde le contrôle humain, mais évite que l’utilisateur soit noyé sous les validations.

## 10.6 Score d’opportunité

Le score d’opportunité répond à :

```txt
Est-ce que ce sujet mérite d’être rédigé maintenant ?
```

Il peut tenir compte de :

* potentiel trafic ;
* intérêt du sujet ;
* pertinence catégorie ;
* difficulté SEO ;
* concurrence estimée ;
* fraîcheur ;
* cohérence stratégie ;
* manque de contenu existant ;
* demande réelle détectée ;
* opportunité GEO.

Si score absent :

```txt
—
```

Ne jamais afficher :

```txt
NaN/100
```

---

# 11. Phase 2 — Recherche SEO et analyse du sujet

## 11.1 Agent `keyword_research`

Rôle :

Trouver la stratégie de mots-clés.

Il reçoit :

* sujet ;
* catégorie ;
* audience ;
* langue ;
* public ciblé ;
* demandes collectées ;
* questions ;
* SERP ;
* articles existants.

Il cherche :

* mot-clé principal ;
* mots-clés secondaires ;
* variantes ;
* longue traîne ;
* questions associées ;
* champ lexical ;
* entités ;
* expressions proches ;
* formulations naturelles.

Sources possibles :

* autocomplete ;
* People Also Ask ;
* SERP ;
* Search Console ;
* outil sémantique configuré ;
* contenus concurrents ;
* communautés publiques ;
* base d’articles existants.

Il produit :

* `keyword_brief_json`.

## 11.2 Agent `search_serp`

Rôle :

Observer les résultats de recherche.

Il reçoit :

* mot-clé principal ;
* mots-clés secondaires ;
* langue ;
* marché ou public ciblé ;
* catégorie.

Il récupère :

* titres ;
* URLs ;
* snippets ;
* meta descriptions ;
* People Also Ask si disponible ;
* formats qui rankent ;
* types de pages ;
* intention dominante probable ;
* fraîcheur des contenus ;
* concurrents principaux.

Il produit :

* `serp_analysis_json`.

## 11.3 Agent `scraper_extractor`

Rôle :

Lire les pages sélectionnées.

Il reçoit :

* URLs SERP ;
* sources sélectionnées ;
* règles d’extraction ;
* limite de pages.

Il extrait :

* H1 ;
* H2 ;
* H3 ;
* H4 ;
* paragraphes importants ;
* données importantes ;
* chiffres ;
* exemples ;
* FAQ ;
* tableaux ;
* médias ;
* sources citées ;
* longueur approximative ;
* sujets couverts.

Il produit :

* `extracted_sources_json`.

Chaque source contient :

* URL ;
* titre ;
* structure ;
* résumé ;
* passages utiles ;
* points forts ;
* points faibles ;
* données à vérifier ;
* limites éventuelles.

## 11.4 Agent `content_gap_analyzer`

Rôle :

Comparer les concurrents.

Il répond à :

* quels sujets reviennent partout ?
* quels sujets manquent ?
* quel concurrent couvre quoi ?
* quelles sections sont faibles ?
* quelles informations sont inutiles ?
* quelles opportunités existent ?
* que peut-on faire mieux ?
* quel angle différencie l’article ?

Il produit :

* `content_gap_json`.

## 11.5 Agent `research_brief`

Rôle :

Transformer les données brutes en synthèse utile.

Il reçoit :

* `serp_analysis_json` ;
* `extracted_sources_json` ;
* `content_gap_json` ;
* questions ;
* sources.

Il produit :

* `research_brief_json`.

Ce brief répond à :

* que disent les concurrents ?
* que veulent les lecteurs ?
* quels points couvrir ?
* quelles sources semblent fiables ?
* quelles informations sont faibles ?
* quelles opportunités éditoriales existent ?

## 11.6 Agent `source_quality_checker`

Rôle :

Évaluer la qualité des sources.

Il vérifie :

* source officielle ou non ;
* auteur identifié ;
* date ;
* fiabilité ;
* source primaire ou secondaire ;
* risque de contenu faible ;
* pertinence.

Il produit :

* `source_quality_report_json`.

Classement possible :

* source forte ;
* source acceptable ;
* source faible ;
* source à éviter ;
* source à vérifier.

## 11.7 Agent `evidence_pack_builder`

Rôle :

Créer le dossier de preuves pour la rédaction.

Il reçoit :

* `research_brief_json` ;
* `source_quality_report_json` ;
* `extracted_sources_json` ;
* `content_gap_json` ;
* `keyword_brief_json`.

Il produit :

* `evidence_pack_json`.

Ce pack contient :

* faits utilisables ;
* sources validées ;
* extraits utiles ;
* points à couvrir ;
* passages à ne pas copier ;
* données à vérifier ;
* statistiques utilisables ;
* sources rejetées ;
* recommandations pour le writer.

Le writer écrit à partir de ce pack.

Il ne doit pas inventer librement.

---

# 12. Phase 3 — Compréhension stratégique

## 12.1 Agent `intent_analysis`

Rôle :

Comprendre l’intention réelle du lecteur.

Il ne doit pas se limiter à :

* informationnelle ;
* commerciale ;
* transactionnelle ;
* navigationnelle.

Il doit comprendre :

* ce que le lecteur veut vraiment ;
* ce qu’il n’a pas clairement formulé ;
* son niveau ;
* ses blocages ;
* ses peurs ;
* la profondeur attendue ;
* le format idéal ;
* les sous-intentions ;
* la réponse attendue.

Il produit :

* `intent_analysis_json`.

## 12.2 Agent `cannibalization_check_initial`

Rôle :

Vérifier si le sujet existe déjà.

Il reçoit :

* sujet ;
* mot-clé principal ;
* mots-clés secondaires ;
* articles existants ;
* idées existantes ;
* slugs ;
* titres ;
* H2/H3 si disponibles.

Il produit :

* `cannibalization_initial_json`.

Décisions possibles :

* continuer ;
* changer l’angle ;
* fusionner ;
* améliorer un ancien article ;
* rejeter.

Si le site est vide, il indique :

```txt
Aucun contenu existant.
Pas de risque de cannibalisation.
```

## 12.3 Agent `editorial_angle`

Rôle :

Choisir comment traiter le sujet.

Il reçoit :

* `intent_analysis_json` ;
* `research_brief_json` ;
* `content_gap_json` ;
* `cannibalization_initial_json` ;
* `category_context_json` ;
* style projet.

Il produit :

* `editorial_angle_json`.

Ce JSON contient :

* angle principal ;
* positionnement ;
* différenciation ;
* promesse éditoriale ;
* ton recommandé ;
* points à éviter ;
* niveau de profondeur ;
* format recommandé.

## 12.4 Agent `outline_planner`

Rôle :

Construire le plan.

Il reçoit :

* sujet ;
* mot-clé principal ;
* intention ;
* angle ;
* research brief ;
* content gap ;
* questions ;
* style souhaité.

Il produit :

* `outline_json`.

Le plan contient :

* H1 ;
* introduction attendue ;
* H2 ;
* H3 ;
* H4 si nécessaire ;
* ordre des sections ;
* réponse rapide ;
* exemples prévus ;
* tableaux prévus ;
* callouts prévus ;
* conclusion attendue.

La structure doit aller rapidement vers le besoin du lecteur.

Elle ne doit pas commencer par des généralités inutiles.

## 12.5 Agent `cannibalization_check_outline`

Rôle :

Deuxième contrôle de cannibalisation après le plan.

Il compare :

* outline nouvel article ;
* anciens articles ;
* anciens H2/H3 ;
* angle ;
* mot-clé ;
* intention.

Il produit :

* `cannibalization_outline_json`.

Décisions possibles :

* plan accepté ;
* plan à modifier ;
* transformer en mise à jour d’un article existant ;
* production bloquée.

## 12.6 Agent `production_brief_builder`

Rôle :

Verrouiller le brief final.

Il reçoit toutes les données précédentes.

Il produit :

* `production_brief_json`.

Ce brief dit au writer :

* quoi écrire ;
* pour qui ;
* pourquoi ;
* avec quel angle ;
* avec quel plan ;
* quelle réponse donner ;
* quels mots-clés utiliser ;
* quelles sources utiliser ;
* quels points couvrir ;
* quels points éviter ;
* quel style adopter ;
* quelle longueur viser ;
* quels médias prévoir ;
* quelles règles SEO/GEO respecter.

---

# 13. Validation humaine de l’idée

## 13.1 Décision humaine

Sur la page Idées, l’humain peut :

* valider ;
* modifier ;
* rejeter ;
* demander remplacement ;
* envoyer en production.

## 13.2 Si l’idée est rejetée

Statut :

```txt
rejected
```

Le système garde la raison du rejet.

Si remplacement automatique est actif, le scheduler peut proposer une nouvelle idée dans la même catégorie.

## 13.3 Si l’idée est validée

Statut :

```txt
validated
```

Le système crée ou verrouille :

* `production_brief_json` ;
* workflow_run ;
* entrée Production ;
* dates ;
* coût estimé ;
* next_agent_key.

L’idée validée quitte le backlog et entre en Production.

---

# 14. Page Production

Production est l’ancien Kanban renommé et clarifié.

Elle contient uniquement les idées validées et les articles en cours de workflow.

Elle ne contient pas toutes les idées.

## 14.1 Colonnes possibles

* brief prêt ;
* en attente de production ;
* génération programmée ;
* génération en cours ;
* brouillon généré ;
* contrôle SEO ;
* prêt pour relecture ;
* corrections demandées ;
* prêt à planifier ;
* planifié ;
* publié.

## 14.2 Carte Production

Chaque carte affiche :

* titre ;
* catégorie ;
* statut ;
* score ;
* coût estimé ;
* coût actuel ;
* dernier agent terminé ;
* prochain agent ;
* date cible ;
* warnings ;
* responsable humain ;
* progression.

## 14.3 Queue de production

La queue évite de générer trop d’articles en même temps.

V1 :

```txt
Séquentiel dans un même projet.
```

Donc :

```txt
Article 1 → génération
Article 1 terminé
Article 2 → génération
Article 2 terminé
```

La production doit utiliser les données déjà créées.

Elle ne doit pas refaire inutilement :

* recherche déjà faite ;
* intention déjà analysée ;
* brief déjà préparé ;
* angle déjà validé ;
* plan déjà construit.

Elle reprend au prochain agent.

---

# 15. Phase 4 — Coût avant production

## 15.1 `cost_estimator`

Avant de lancer la production, le système estime le coût.

Il regarde :

* agents restants ;
* providers ;
* modèles ;
* tokens estimés ;
* prix ;
* fallback ;
* retries.

Il produit :

* `estimated_cost_json`.

Si le coût dépasse la limite avant même lancement :

* pipeline bloqué ;
* notification humaine ;
* décision humaine requise.

---

# 16. Phase 5 — Rédaction et enrichissement

## 16.1 Agent `style_guide_builder`

Rôle :

Préparer la plume.

Il reçoit :

* stratégie projet ;
* audience ;
* catégorie ;
* intention ;
* angle ;
* niveau lecteur.

Il produit :

* `style_guide_json`.

Il définit :

* ton ;
* style ;
* niveau de langage ;
* longueur des phrases ;
* mots à éviter ;
* expressions à éviter ;
* humour autorisé ou non ;
* niveau technique ;
* chaleur humaine ;
* rythme.

## 16.2 Agent `writer`

Rôle :

Rédiger le contenu principal.

Il reçoit :

* `production_brief_json` ;
* `evidence_pack_json` ;
* `style_guide_json` ;
* `outline_json` ;
* `keyword_brief_json` ;
* `research_brief_json` ;
* `source_quality_report_json`.

Il respecte :

* intention ;
* angle ;
* plan ;
* preuves ;
* sources ;
* style ;
* SEO ;
* GEO ;
* longueur ;
* clarté.

Il produit :

* `content_html` ;
* `content_markdown` si nécessaire ;
* `word_count` ;
* `sections_written` ;
* `writing_notes_json`.

S’il manque une donnée importante, il ne doit pas inventer.

Il retourne :

* `needs_more_research` ;
* missing_information ;
* retry_from.

## 16.3 Agent `meta_writer`

Rôle :

Préparer les métas.

Il reçoit :

* titre ;
* contenu ;
* mot-clé principal ;
* intention ;
* angle ;
* public.

Il produit :

* meta_title ;
* meta_description ;
* slug ;
* excerpt ;
* social_title ;
* social_description.

## 16.4 Agent `faq_generator`

Rôle :

Créer une FAQ courte.

Règles :

* minimum 3 questions ;
* maximum 6 questions ;
* réponses de 30 à 35 mots maximum ;
* questions simples ;
* réponses rapides ;
* pas de question qui mérite un article entier.

Il produit :

* `faq_json`.

## 16.5 Agent `structured_data_builder`

Rôle :

Générer les données structurées schema.org.

Il intervient après :

* meta_writer ;
* faq_generator ;
* media_planner si les images doivent être incluses.

Il reçoit :

* title ;
* slug ;
* meta_title ;
* meta_description ;
* excerpt ;
* author ;
* published_at ;
* updated_at ;
* category ;
* content ;
* FAQ ;
* images ;
* canonical_url ;
* organization ;
* article type.

Il produit :

* `structured_data_json`.

Schémas possibles :

* Article ;
* BlogPosting ;
* FAQPage ;
* HowTo si le contenu est réellement un tutoriel ;
* BreadcrumbList ;
* Organization si nécessaire.

Il ne doit pas inventer de faits.

Le `seo_final_checklist` doit vérifier que les données structurées existent et sont valides.

## 16.6 Agent `callout_planner`

Rôle :

Proposer les callouts utiles.

Types autorisés :

* À retenir ;
* Réponse rapide ;
* Conseil pratique ;
* Erreur fréquente ;
* Attention ;
* Exemple court ;
* Point important.

Règle :

Pas de checklist longue en callout.

Une checklist complète doit être dans le contenu normal avec H2/H3.

Il produit :

* `callout_plan_json`.

## 16.7 Agent `media_planner`

Rôle :

Proposer les médias utiles.

Types :

* image ;
* vidéo ;
* podcast ;
* audio ;
* post intégré ;
* graphique ;
* tableau ;
* infographie.

Il produit :

* `media_plan_json` ;
* `image_sources_json`.

Chaque média contient :

* type ;
* placement ;
* source ;
* URL ;
* raison ;
* alt text ;
* légende ;
* statut/licence si nécessaire.

Aucun média décoratif inutile.

## 16.8 Agent `internal_link_planner`

Rôle :

Proposer les liens internes.

Il analyse :

* nouvel article ;
* mots-clés ;
* H2/H3 ;
* articles existants ;
* sections existantes ;
* ancres disponibles ;
* proximité sémantique.

Il peut proposer :

* lien vers article entier ;
* lien vers section précise.

Il produit :

* `internal_links_json`.

Si aucun lien pertinent n’existe, il ne force rien.

## 16.9 Agent `external_link_planner`

Rôle :

Proposer les liens externes.

Il privilégie :

* sources officielles ;
* documentation ;
* études ;
* rapports ;
* statistiques fiables ;
* pages primaires.

Il produit :

* `external_links_json`.

Chaque lien doit avoir une raison.

---

# 17. Phase 6 — Optimisation SEO/GEO

## 17.1 Agent `seo_optimizer`

Rôle :

Contrôler le SEO avancé.

Il vérifie :

* intention respectée ;
* réponse principale donnée tôt ;
* H1 ;
* title ;
* meta description ;
* slug ;
* structure H2/H3/H4 ;
* mots-clés ;
* densité ;
* champ lexical ;
* keyword stuffing ;
* paragraphes ;
* listes ;
* tableaux ;
* FAQ ;
* callouts ;
* liens internes ;
* liens externes ;
* alt text ;
* données sourcées ;
* conclusion.

Il produit :

* `seo_review_json`.

La densité ne doit pas suivre un pourcentage magique.

Elle sert à détecter :

* mot-clé absent ;
* mot-clé trop rare ;
* mot-clé trop répété ;
* texte artificiel ;
* surcharge SEO.

## 17.2 Agent `geo_answer_optimizer`

Rôle :

Optimiser pour les moteurs IA et réponses génératives.

Il vérifie :

* réponse claire dès le début ;
* définitions précises ;
* sections autonomes ;
* phrases citables ;
* entités nommées ;
* tableaux si utiles ;
* listes si utiles ;
* sources fiables ;
* absence d’ambiguïté ;
* contenu facilement résumable.

Il produit :

* `geo_optimization_json`.

## 17.3 Agent `engagement_editor`

Rôle :

Vérifier que l’article capte le lecteur.

Il regarde :

* titre ;
* première phrase ;
* introduction ;
* promesse ;
* rythme ;
* transitions ;
* exemples ;
* curiosité ;
* progression ;
* conclusion.

Il produit :

* `engagement_report_json`.

## 17.4 Agent `reader_retention_checker`

Rôle :

Détecter les endroits où le lecteur peut décrocher.

Il cherche :

* sections trop longues ;
* paragraphes denses ;
* réponse trop tardive ;
* répétitions ;
* manque d’exemple ;
* baisse de rythme ;
* transitions faibles.

Il produit :

* `reader_retention_report_json`.

---

# 18. Phase 7 — Qualité éditoriale

## 18.1 Agent `editor`

Rôle :

Relire comme un rédacteur en chef.

Il vérifie :

* clarté ;
* cohérence ;
* structure ;
* logique ;
* répétitions ;
* ton ;
* respect du brief ;
* fluidité.

Il produit :

* `editorial_quality_report_json`.

## 18.2 Agent `language_quality`

Rôle :

Vérifier langue et lisibilité.

Il regarde :

* fautes ;
* phrases trop longues ;
* phrases sans verbe ;
* répétitions ;
* lisibilité ;
* grammaire ;
* vocabulaire ;
* transitions.

Règles :

* phrase moyenne : 20 à 25 mots ;
* maximum conseillé : 28 mots ;
* couper les phrases trop longues ;
* éviter les phrases sans verbe.

Il produit :

* `language_quality_report_json`.

## 18.3 Agent `originality_checker`

Rôle :

Vérifier l’originalité avec comparaison réelle aux sources collectées.

Il utilise :

* `evidence_pack_json` ;
* `extracted_sources_json` ;
* URLs sources ;
* passages concurrents ;
* n-grams ;
* shingles ;
* embeddings si disponibles ;
* outil anti-plagiat externe si configuré.

Il détecte :

* phrase trop proche ;
* structure trop proche ;
* paragraphe trop proche ;
* ordre d’idées trop similaire ;
* paraphrase faible ;
* manque d’angle propre.

Règle absolue :

```txt
Interdiction de paraphrase faible.
```

S’il y a similarité, il demande une reformulation complète.

Une reformulation complète doit :

* garder le sens ;
* garder la précision ;
* garder les mots-clés importants ;
* changer la structure ;
* changer l’expression ;
* éviter l’ambiguïté ;
* éviter d’allonger inutilement.

Il produit :

* `originality_report_json`.

Le rapport contient :

* URL source ;
* passage source ;
* passage problématique ;
* score de similarité ;
* type de similarité ;
* niveau de risque ;
* section concernée ;
* action requise.

## 18.4 Agent `claim_extractor`

Rôle :

Extraire les affirmations vérifiables.

Il repère :

* chiffres ;
* dates ;
* statistiques ;
* comparaisons ;
* promesses ;
* données techniques ;
* citations ;
* références à des sources officielles.

Il produit :

* `claims_json`.

## 18.5 Agent `fact_checker`

Rôle :

Vérifier les claims.

Il utilise :

* sources collectées ;
* documentation officielle ;
* études ;
* rapports ;
* pages primaires ;
* recherche web ;
* source map ;
* evidence pack.

Il produit :

* `fact_check_report_json`.

Décisions possibles :

* claim vérifié ;
* claim incertain ;
* claim faux ;
* source manquante ;
* reformulation nécessaire ;
* suppression recommandée.

## 18.6 Agent `humanizer`

Rôle :

Rendre le texte naturel.

Il évite :

* formules typiques IA ;
* tirets longs trop fréquents ;
* introductions vagues ;
* conclusions automatiques ;
* ton froid ;
* phrases symétriques ;
* répétitions ;
* paragraphes lourds.

Il produit :

* `humanization_report_json`.

## 18.7 Agent `eeat_reviewer`

Rôle :

Vérifier la crédibilité.

Il regarde :

* auteur ;
* sources ;
* preuves ;
* expérience ;
* exemples ;
* cas réels ;
* prudence ;
* fiabilité ;
* expertise ;
* confiance.

Il produit :

* `eeat_checklist_json`.

---

# 19. Phase 8 — Gate final

## 19.1 Agent `seo_final_checklist`

Rôle :

Contrôle technique final SEO/GEO.

Il vérifie :

* title ;
* meta description ;
* slug ;
* H1 unique ;
* H2/H3 corrects ;
* FAQ ;
* callouts ;
* images ;
* alt text ;
* liens internes ;
* liens externes ;
* sources ;
* sections vides ;
* données structurées ;
* données structurées valides ;
* conclusion ;
* cohérence globale.

Il produit :

* `seo_final_checklist_json`.

## 19.2 Agent `quality_gate`

Rôle :

Décider si l’article passe.

Statuts possibles :

* pass ;
* needs_revision ;
* blocked.

Il lit :

* `seo_review_json` ;
* `geo_optimization_json` ;
* `engagement_report_json` ;
* `reader_retention_report_json` ;
* `language_quality_report_json` ;
* `originality_report_json` ;
* `fact_check_report_json` ;
* `humanization_report_json` ;
* `eeat_checklist_json` ;
* `seo_final_checklist_json`.

S’il bloque, il indique :

* raison ;
* agent concerné ;
* section concernée ;
* donnée manquante ;
* étape de reprise ;
* nombre de tentatives ;
* coût déjà consommé ;
* action recommandée.

Après 3 échecs sur le même problème, le système arrête et notifie l’humain.

## 19.3 Service `error_manager`

Rôle :

Centraliser les erreurs.

Il enregistre :

* phase ;
* agent ;
* outil ;
* erreur ;
* cause exacte si connue ;
* cause probable sinon ;
* retry possible ;
* tentative ;
* notification ;
* reprise.

Il produit :

* `workflow_error_json`.

## 19.4 Service `cost_tracker`

Rôle :

Consolider les coûts déjà loggés par AgentRouter.

Il ajoute au rapport :

* coût estimé ;
* coût réel ;
* coût par agent ;
* coût par provider ;
* coût des retries ;
* coût fallback ;
* statut du budget.

## 19.5 Agent `generation_report_builder`

Rôle :

Créer le rapport final.

Il produit :

* `generation_report_json`.

Le rapport contient :

* sujet ;
* catégorie ;
* mots-clés ;
* intention ;
* angle ;
* sources ;
* agents exécutés ;
* providers ;
* modèles ;
* tokens ;
* coûts ;
* erreurs ;
* retries ;
* fallback ;
* score SEO ;
* score GEO ;
* score originalité ;
* score E-E-A-T ;
* score lisibilité ;
* structured data status ;
* warnings ;
* corrections ;
* recommandations ;
* statut final.

---

# 20. Champs obligatoires dans `generation_report_json`

Le rapport final doit contenir au minimum :

```json
{
  "workflow_id": "...",
  "article_id": "...",
  "category": "...",
  "main_keyword": "...",
  "secondary_keywords": [],
  "intent_summary": "...",
  "editorial_angle": "...",
  "agents_completed": [],
  "providers_used": [],
  "models_used": [],
  "fallback_used": false,
  "estimated_cost_eur": 0.42,
  "actual_cost_eur": 0.47,
  "cost_limit_eur": 1.50,
  "cost_status": "within_limit",
  "cost_breakdown_json": [],
  "seo_score": 84,
  "geo_score": 78,
  "originality_score": 91,
  "eeat_score": 82,
  "readability_score": 80,
  "structured_data_status": "valid",
  "structured_data_json": {},
  "batch_validation_used": false,
  "previous_version_available": true,
  "rollback_available": true,
  "tracking_privacy": {
    "ip_anonymization_required": true,
    "cookie_consent_required": true
  },
  "warnings": [],
  "errors": [],
  "recommended_next_action": "human_review"
}
```

---

# 21. Éditeur CMS

## 21.1 Page Éditeur Article

L’article généré apparaît dans l’éditeur.

L’éditeur affiche :

* contenu ;
* titre ;
* slug ;
* meta title ;
* meta description ;
* excerpt ;
* catégorie ;
* statut ;
* auteur ;
* FAQ ;
* callouts ;
* médias ;
* liens ;
* sources ;
* données structurées ;
* score SEO ;
* score GEO ;
* score originalité ;
* score E-E-A-T ;
* coût estimé ;
* coût réel ;
* rapport de génération ;
* contrôles qualité ;
* warnings ;
* historique ;
* versions.

L’humain peut :

* corriger ;
* reformuler ;
* demander amélioration IA ;
* accepter une recommandation ;
* refuser une recommandation ;
* marquer prêt ;
* planifier ;
* publier si autorisé ;
* revenir à une version précédente si disponible.

## 21.2 Panneau “Brief SEO”

Afficher :

* `intent_analysis_json` ;
* `research_brief_json` ;
* `keyword_brief_json` ;
* `editorial_angle_json` ;
* `outline_json` ;
* `production_brief_json`.

## 21.3 Panneau “Rapport de génération”

Afficher :

* agents exécutés ;
* provider/model par étape ;
* durée ;
* tokens ;
* coût ;
* fallback ;
* erreurs ;
* retries ;
* sources ;
* décisions ;
* warnings.

## 21.4 Panneau “Contrôles qualité”

Afficher :

* `seo_review_json` ;
* `geo_optimization_json` ;
* `language_quality_report_json` ;
* `originality_report_json` ;
* `claims_json` ;
* `fact_check_report_json` ;
* `humanization_report_json` ;
* `eeat_checklist_json` ;
* `seo_final_checklist_json`.

## 21.5 Panneau “Assets et liens”

Afficher :

* `faq_json` ;
* `callout_plan_json` ;
* `media_plan_json` ;
* `image_sources_json` ;
* `internal_links_json` ;
* `external_links_json` ;
* `structured_data_json`.

---

# 22. Page Articles

La page Articles est la bibliothèque complète du CMS.

Elle affiche tous les contenus selon droits :

* brouillons ;
* en rédaction ;
* en relecture ;
* prêts ;
* planifiés ;
* publiés ;
* archivés ;
* amélioration proposée.

Filtres :

* tous ;
* brouillons ;
* à relire ;
* prêts ;
* planifiés ;
* publiés ;
* archivés.

Actions :

* ouvrir ;
* modifier ;
* dupliquer ;
* archiver ;
* planifier ;
* publier ;
* dépublier ;
* voir rapport ;
* voir historique ;
* rollback si disponible.

Important :

```txt
CMS interne = tous les articles.
Site public/API publique = seulement articles publiés.
```

---

# 23. Calendrier

La page Calendrier affiche :

* idées prévues ;
* dates de rédaction ;
* dates de relecture ;
* dates de publication ;
* articles planifiés ;
* articles publiés ;
* trous dans le planning ;
* surcharge éventuelle.

L’utilisateur peut déplacer une publication.

Le système doit garder :

* régularité ;
* équilibre des catégories ;
* cohérence des fréquences ;
* validation humaine avant publication.

Quand l’article est prêt à planifier, le bouton “Programmer” doit pré-remplir la date cible proposée.

---

# 24. Publication

## 24.1 Publication manuelle

L’humain clique sur publier.

Le backend vérifie :

* rôle ;
* statut ;
* quality gate ;
* erreurs bloquantes ;
* coût non bloqué ;
* article complet ;
* slug ;
* meta ;
* contenu ;
* données structurées.

Si tout est bon :

* status = published ;
* published_at rempli ;
* snapshot créé ;
* API publique expose l’article ;
* revalidation du site public déclenchée si configurée.

## 24.2 Planification

L’humain peut programmer l’article.

Statut :

```txt
scheduled
```

Quand la date arrive, le scheduler publie seulement si l’article a été validé et planifié par l’humain.

Ce n’est pas une publication automatique décidée par l’IA.

---

# 25. Snapshots, versioning simple et rollback

## 25.1 Snapshot à chaque publication

À chaque publication, le backend crée un snapshot contenant :

* titre ;
* slug ;
* contenu ;
* meta title ;
* meta description ;
* FAQ ;
* callouts ;
* médias ;
* liens ;
* structured data ;
* date de publication ;
* auteur ;
* version.

## 25.2 Amélioration post-publication

Quand le monitoring propose une amélioration et que l’humain l’accepte, le système ne doit pas écraser directement la version publiée.

Il crée :

```txt
nouvelle version brouillon
```

L’ancienne version publiée reste active jusqu’à validation humaine.

## 25.3 `previous_version_json`

Avant de remplacer une version publiée par une nouvelle version, le système sauvegarde l’ancienne version dans :

```txt
previous_version_json
```

ou dans une table snapshots si elle existe.

## 25.4 Bouton rollback

Dans l’éditeur, si une version précédente existe :

```txt
Revenir à la version précédente
```

Cette action doit :

1. demander confirmation ;
2. restaurer le contenu précédent ;
3. créer un nouveau snapshot ;
4. noter l’action dans l’historique ;
5. revalider le site public si nécessaire.

Pas besoin d’un versioning complexe type Git pour la V1.

---

# 26. Site public et API publique

Le site public consomme seulement les articles publiés.

Il récupère :

* titre ;
* slug ;
* contenu ;
* catégorie ;
* meta ;
* FAQ ;
* callouts ;
* médias ;
* auteur ;
* temps de lecture ;
* dates ;
* sources ;
* structured data.

Le site public garde son propre design.

Ideas Studio fournit le contenu.

Le site public rend le contenu.

## 26.1 Communication Ideas Studio → Site public

Ideas Studio fournit :

* articles publiés ;
* catégories ;
* contenu HTML ;
* FAQ ;
* callouts ;
* images ;
* meta SEO ;
* auteur ;
* temps de lecture ;
* structured data ;
* signal de revalidation.

## 26.2 Communication Site public → Ideas Studio

Le site public renvoie :

* tracking ;
* état de connexion ;
* configuration site ;
* capacités du site ;
* callouts disponibles ;
* routes ;
* état de revalidation.

## 26.3 Revalidation

Quand Ideas Studio publie ou met à jour un article, il peut appeler le site public pour revalider :

* page blog ;
* page article ;
* sitemap.

---

# 27. Tracking et RGPD minimal viable

## 27.1 Consentement avant tracking

Le site public ne doit pas envoyer de données analytics non essentielles avant consentement si ce consentement est requis.

Règle :

```txt
Aucune donnée de tracking marketing/analytics non essentielle n’est envoyée sans consentement.
```

## 27.2 Anonymisation IP

Le système doit anonymiser les IP avant stockage ou éviter de stocker l’IP brute.

Règle :

```txt
Les IP doivent être anonymisées avant tracking ou avant stockage.
```

Si le pays est calculé, le système ne doit pas conserver l’IP brute inutilement.

## 27.3 Données minimales

Le tracking collecte seulement les données utiles :

* page vue ;
* article consulté ;
* source ;
* referrer ;
* device ;
* pays ou zone approximative ;
* progression de lecture ;
* clics éditoriaux utiles.

Il ne collecte pas plus que nécessaire.

---

# 28. Performance et trafic

## 28.1 Page Performance

Elle affiche :

* vues ;
* visiteurs ;
* articles performants ;
* articles faibles ;
* progression ;
* opportunités ;
* contenus à optimiser.

Si aucune donnée :

* cartes visibles ;
* valeurs à 0 ;
* graphiques avec état vide discret ;
* pas de faux contenu.

## 28.2 Page Trafic

Elle affiche :

* sources ;
* canaux ;
* pays ;
* appareils ;
* pages d’entrée ;
* évolution par période.

Si aucune donnée :

* dashboard visible ;
* valeurs à 0 ou `—` ;
* message discret ;
* aucun mock présenté comme réel.

---

# 29. Monitoring après publication

Après publication, le système suit l’article.

Il regarde :

* âge de l’article ;
* trafic ;
* baisse de performance ;
* absence de progression ;
* CTR ;
* position si Search Console disponible ;
* engagement ;
* obsolescence ;
* concurrence.

## 29.1 Agent `performance_monitor`

Rôle :

Détecter les problèmes de performance.

Il produit :

* `performance_diagnosis_json`.

## 29.2 Agent `improvement_proposal_builder`

Rôle :

Proposer une amélioration.

Il peut suggérer :

* mise à jour ;
* nouvelle section ;
* correction SEO ;
* ajout FAQ ;
* ajout source ;
* amélioration intro ;
* enrichissement média ;
* amélioration maillage interne.

Il produit :

* `improvement_proposal_json`.

L’humain décide :

* accepter ;
* modifier ;
* rejeter.

Si accepté, le système crée une nouvelle version brouillon.

L’article publié reste en ligne jusqu’à validation.

Le monitoring ne dépublie rien automatiquement.

---

# 30. Notifications

La page Notifications affiche :

* erreurs d’agents ;
* providers indisponibles ;
* pipeline bloqué ;
* coût dépassé ;
* génération terminée ;
* article prêt à relire ;
* article planifié ;
* article publié ;
* amélioration proposée ;
* tracking absent ;
* clé API invalide ;
* échec après 3 tentatives.

Chaque notification indique :

* quoi ;
* où ;
* pourquoi ;
* action possible.

---

# 31. Gestion des erreurs

Chaque agent ou service doit retourner une erreur structurée.

L’erreur précise :

* phase ;
* agent ;
* outil ;
* cause exacte si connue ;
* cause probable sinon ;
* gravité ;
* retry possible ;
* étape de reprise ;
* tentative ;
* action recommandée ;
* notification nécessaire.

Règle :

* première erreur : retry si possible ;
* deuxième erreur : retry + warning ;
* troisième erreur : arrêt + notification humaine.

Le workflow reprend depuis l’agent bloqué, pas depuis zéro.

---

# 32. Chaîne finale des agents/services V1

Chaîne finale :

1. `category_context_builder`
2. `demand_discovery`
3. `topic_selector`
4. `keyword_research`
5. `search_serp`
6. `scraper_extractor`
7. `content_gap_analyzer`
8. `research_brief`
9. `source_quality_checker`
10. `evidence_pack_builder`
11. `intent_analysis`
12. `cannibalization_check_initial`
13. `editorial_angle`
14. `outline_planner`
15. `cannibalization_check_outline`
16. `production_brief_builder`
17. `cost_estimator`
18. `style_guide_builder`
19. `writer`
20. `meta_writer`
21. `faq_generator`
22. `media_planner`
23. `structured_data_builder`
24. `callout_planner`
25. `internal_link_planner`
26. `external_link_planner`
27. `seo_optimizer`
28. `geo_answer_optimizer`
29. `engagement_editor`
30. `reader_retention_checker`
31. `editor`
32. `language_quality`
33. `originality_checker`
34. `claim_extractor`
35. `fact_checker`
36. `humanizer`
37. `eeat_reviewer`
38. `seo_final_checklist`
39. `quality_gate`
40. `error_manager`
41. `cost_tracker`
42. `generation_report_builder`

Note :

`cost_tracker` n’est pas seulement un agent final.
Il fonctionne surtout à chaque appel AgentRouter, puis ses données sont consolidées dans `generation_report_builder`.

---

# 33. Flux complet résumé

Le flux complet est :

1. L’utilisateur configure le projet.
2. Il configure les catégories et fréquences.
3. Il connecte les providers IA.
4. Il assigne les providers aux agents.
5. Il définit les limites de coût.
6. Il configure le pipeline.
7. Le scheduler ou l’utilisateur lance la planification.
8. Le système part d’une catégorie.
9. Il cherche les demandes réelles.
10. Il propose des sujets prouvés.
11. La page Idées affiche les pré-briefs.
12. L’humain valide, modifie ou rejette.
13. Une idée validée devient un brief final.
14. Le coût est estimé.
15. L’idée entre en Production.
16. La queue lance les agents.
17. Les agents recherchent, analysent, rédigent et enrichissent.
18. Les données structurées sont générées.
19. Les agents SEO/GEO contrôlent.
20. Les agents qualité vérifient.
21. Les coûts réels sont suivis.
22. Le rapport final est généré.
23. L’article apparaît dans l’éditeur.
24. L’humain relit.
25. L’humain corrige ou valide.
26. L’humain planifie ou publie.
27. Un snapshot est créé.
28. Le site public affiche l’article publié.
29. Le tracking mesure les performances selon consentement.
30. Le monitoring propose des améliorations.
31. L’humain valide toute modification importante.
32. Une version précédente reste restaurable.

---

# 34. Éléments V2 non bloquants

Ces éléments sont utiles mais ne bloquent pas la V1.

## 34.1 Monitoring GEO réel

V2 peut ajouter :

* `geo_visibility_monitor`.

Objectif :

* tester des requêtes types ;
* vérifier si le site apparaît dans les réponses IA ;
* suivre la visibilité GEO ;
* proposer des optimisations basées sur les résultats.

## 34.2 Parallélisation avancée

V1 :

```txt
Séquentiel dans un même projet.
```

V2 :

```txt
Parallèle entre projets différents si budgets et quotas le permettent.
```

Règles futures :

* limites globales ;
* limites par provider ;
* contrôle de concurrence ;
* priorité multi-clients.

## 34.3 Sécurité avancée

V2 peut approfondir :

* rotation des clés API ;
* audit logs détaillés ;
* journal d’accès aux clés ;
* politiques de rétention ;
* export/suppression de données ;
* gestion avancée des consentements ;
* DPA / conformité commerciale.

---

# 35. Règles finales du système

Aucun sujet sans preuve.

Aucun agent ne décide au hasard.

Aucun résultat mocké présenté comme réel.

Aucune source inventée.

Aucune statistique non vérifiée.

Aucune paraphrase faible.

Aucun lien inutile.

Aucun média décoratif.

Aucune publication automatique décidée par l’IA.

Aucun tracking non essentiel sans consentement lorsque requis.

Aucune IP brute ne doit être stockée inutilement.

Aucun workflow ne doit dépasser le coût maximum défini sans arrêt et notification.

Chaque agent produit une sortie exploitable.

Chaque sortie importante est sauvegardée.

Chaque rapport important est visible dans l’interface.

Chaque coût estimé et réel est visible dans le rapport.

Chaque erreur indique où reprendre.

Après trois échecs, l’humain est notifié.

Chaque publication crée un snapshot.

Chaque mise à jour post-publication conserve une version précédente restaurable.

Le système doit rester contrôlable humainement, financièrement, éditorialement et techniquement.
