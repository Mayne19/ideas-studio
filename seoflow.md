# Ideas Studio — Workflow éditorial et SEO Expert Agent

## 1. Vision générale

Ideas Studio ne doit pas être un simple générateur d’articles. Le système doit fonctionner comme une équipe éditoriale complète, capable de préparer, rechercher, structurer, rédiger, corriger, contrôler et documenter chaque article avant validation humaine.

Le système doit agir comme :

* un SEO Expert ;
* un analyste de recherche ;
* un stratège mots-clés ;
* un planificateur éditorial ;
* un rédacteur ;
* un correcteur de style ;
* un contrôleur originalité ;
* un reviewer EEAT ;
* un assistant publication.

Le système ne publie jamais automatiquement. Il crée des idées, des briefs, des brouillons et des rapports. L’humain reste responsable de la validation, de la publication ou de la programmation.

Objectif final : produire des brouillons SEO sérieux, utiles, structurés, lisibles, originaux, vérifiables, adaptés au site, et accompagnés d’un rapport clair dans l’éditeur.

---

## 2. Modes de fonctionnement

### 2.1 Mode manuel

Dans le mode manuel, un utilisateur déclenche lui-même le travail.

L’utilisateur peut :

* créer une idée ;
* choisir une idée existante dans le Kanban ;
* remplir un sujet précis ;
* donner un titre souhaité ;
* choisir une catégorie ;
* définir un mot-clé principal ;
* ajouter un angle ;
* ajouter un contexte ;
* demander une FAQ ;
* demander des callouts ;
* lancer la rédaction.

Règle fondamentale : si l’utilisateur fournit un titre, une catégorie, un angle ou une intention claire, le système doit respecter ces éléments. Il peut proposer une amélioration, mais il ne doit pas remplacer ce que l’utilisateur a donné sans raison visible.

### 2.2 Mode automatique

Dans le mode automatique, le système travaille seul selon une planification.

Le pipeline doit permettre :

* activation / désactivation ;
* pause jusqu’à une date ;
* pause jusqu’à réactivation manuelle ;
* choix des jours actifs ;
* choix des heures de travail ;
* nombre d’idées ou articles à produire ;
* nombre maximum de brouillons en attente ;
* priorités par catégorie ;
* fréquence mensuelle par catégorie.

Même en mode automatique, le système ne publie jamais seul. Il peut créer des idées, des briefs, des brouillons et des rapports, mais la publication reste humaine.

---

## 3. Catégories, priorité et fréquence

La priorité et la fréquence doivent être liées aux catégories.

### 3.1 Page Catégories

Chaque catégorie doit pouvoir contenir :

* nom ;
* slug ;
* couleur ;
* statut actif / inactif ;
* priorité éditoriale ;
* fréquence d’articles par mois ;
* objectif éditorial ;
* description ;
* public cible spécifique ;
* notes internes.

Exemple :

```txt
Catégorie : Intelligence artificielle
Priorité : 9/10
Fréquence : 8 articles/mois
Objectif : capter les recherches IA pratiques et business
Statut pipeline : actif
```

### 3.2 Paramètres Pipeline

Les paramètres pipeline peuvent afficher et modifier les priorités et fréquences, mais il ne doit pas exister deux vérités différentes.

Règles :

* si une priorité/fréquence est définie sur la catégorie, le pipeline l’utilise ;
* si rien n’est défini sur la catégorie, le pipeline utilise les valeurs globales par défaut ;
* si une valeur est modifiée depuis les paramètres pipeline, elle doit être visible sur la page Catégories ;
* si elle est modifiée depuis la page Catégories, elle doit être visible dans les paramètres pipeline.

### 3.3 Choix automatique d’une catégorie

Le système ne choisit pas une catégorie au hasard. Il doit tenir compte de :

* priorité de la catégorie ;
* fréquence mensuelle attendue ;
* nombre d’articles déjà publiés ce mois-ci ;
* nombre de brouillons en attente ;
* nombre d’idées existantes dans le Kanban ;
* date du dernier article publié ;
* opportunité SEO ;
* saturation éventuelle ;
* risque de cannibalisation.

Le système doit justifier son choix dans le rapport.

---

## 4. Planification automatique

Le pipeline doit permettre :

* génération quotidienne ;
* génération certains jours ;
* génération hebdomadaire ;
* génération mensuelle ;
* horaires précis ;
* plusieurs créneaux dans la journée ;
* pause temporaire ;
* pause indéfinie.

Statuts nécessaires :

* active ;
* paused_until_date ;
* paused_indefinitely ;
* disabled.

L’utilisateur peut dire :

* ne travaille pas cette semaine ;
* ne travaille pas jusqu’au 15 juin ;
* ne travaille pas jusqu’à réactivation ;
* reprends lundi prochain.

---

## 5. Budget et consommation API

Il ne faut pas limiter brutalement le système au point de le rendre faible. Pour ce projet, le mode par défaut doit être orienté qualité.

Le système ne doit pas :

* réduire la recherche au minimum pour économiser ;
* supprimer les étapes SEO ;
* écrire un article court pour réduire le coût ;
* éviter le fact-check par défaut ;
* produire un texte faible pour respecter une limite trop basse.

À la place, il doit afficher une observabilité :

* provider utilisé ;
* modèle utilisé ;
* coût estimé ;
* nombre d’appels IA ;
* nombre de tokens estimé ;
* durée de génération ;
* nombre de sources consultées.

Modes possibles :

* qualité maximale ;
* équilibré ;
* économique.

Pour ce projet, le mode par défaut recommandé est : qualité maximale.

Le système peut alerter si une génération coûte plus cher, mais il ne bloque pas sauf si l’utilisateur impose volontairement une limite.

---

## 5B. Outillage externe prévu

Cette section précise les outils externes ou open-source qui peuvent accélérer la construction du système. Ils ne remplacent pas Ideas Studio. Ils servent de sources, d’adapters, de knowledge packs ou de briques contrôlées.

Règle centrale : aucun outil externe ne doit être installé, exécuté ou intégré dans le runtime sans audit sécurité, licence et compatibilité. Les outils externes doivent être utilisés à travers des adapters maîtrisés par Ideas Studio.

### 5B.1 Recherche SEO, SERP, People Also Ask et Autocomplete

Objectif : récupérer les questions réelles des internautes, les recherches associées, les suggestions, les SERP et les angles concurrents.

Outils et sources possibles :

* SerpApi ;
* google-search-results-python ;
* seo-keyword-research-tool ;
* HasData SERP API ;
* Bing Search API si disponible ;
* Brave Search API si disponible.

Étapes concernées :

* génération d’idées ;
* People Also Ask ;
* Google Autocomplete ;
* recherches associées ;
* analyse SERP ;
* analyse concurrentielle ;
* ResearchBrief ;
* KeywordBrief.

Usage attendu :

* extraire les questions fréquentes ;
* récupérer les titres et snippets SERP ;
* détecter les formulations réelles utilisées par les internautes ;
* identifier les pages concurrentes ;
* créer une base de sujets et d’intentions ;
* alimenter les idées Kanban.

Données à stocker :

* query ;
* engine ;
* title ;
* url ;
* snippet ;
* source_type ;
* detected_questions ;
* related_searches ;
* paa_items ;
* fetched_at ;
* confidence_score.

Intégration court terme :

* créer un adapter SERP unique ;
* commencer avec une API propre plutôt qu’un scraping direct ;
* indiquer clairement si la recherche est réelle ou indisponible.

Intégration long terme :

* multi-provider SERP ;
* fallback Bing/Brave si Google indisponible ;
* cache des résultats ;
* déduplication des idées ;
* analyse des tendances par catégorie.

Limites :

* les API SERP peuvent être payantes ;
* le scraping direct Google est fragile ;
* les résultats changent selon pays/langue/appareil ;
* il faut éviter de faire croire à une recherche réelle si l’API n’est pas configurée.

Statut : à intégrer dans le backend complet, via adapter contrôlé.

### 5B.2 Tendances de recherche

Objectif : comprendre si un sujet monte, baisse ou reste stable.

Outils possibles :

* pytrends ;
* Google Trends via méthodes disponibles ;
* données Search Console plus tard.

Étapes concernées :

* opportunité SEO ;
* choix des sujets automatiques ;
* priorisation des idées ;
* calendrier éditorial.

Usage attendu :

* comparer deux sujets ;
* repérer un sujet saisonnier ;
* éviter de traiter trop tard un sujet déjà mort ;
* prioriser les catégories.

Données à stocker :

* keyword ;
* timeframe ;
* region ;
* trend_score ;
* rising_queries ;
* related_topics ;
* fetched_at.

Limites :

* pytrends est non officiel ;
* Google peut changer son fonctionnement ;
* la donnée doit être considérée comme signal, pas comme vérité absolue.

Statut : à auditer puis intégrer plus tard.

### 5B.3 Extraction de contenu concurrent

Objectif : lire les contenus concurrents pour comprendre les angles, titres, sources et manques.

Outils possibles :

* trafilatura ;
* readability-lxml ;
* BeautifulSoup ;
* Playwright seulement si nécessaire.

Étapes concernées :

* ResearchBrief ;
* analyse concurrentielle ;
* source reliability ;
* originality comparison ;
* extraction des titres et sections.

Usage attendu :

* extraire le texte principal ;
* extraire les métadonnées ;
* extraire les H1/H2/H3 ;
* détecter les sources citées ;
* comparer les angles concurrents ;
* identifier les lacunes.

Données à stocker :

* url ;
* title ;
* author si disponible ;
* published_at si disponible ;
* extracted_text ;
* headings ;
* meta_description ;
* source_links ;
* extraction_status ;
* fetched_at.

Règles :

* respecter les conditions des sites ;
* éviter le scraping agressif ;
* timeout obligatoire ;
* user-agent propre ;
* ne pas copier le contenu extrait ;
* utiliser les sources pour comprendre et reconstruire, pas paraphraser.

Statut : outil prioritaire pour ResearchBrief réel.

### 5B.4 Correction langue

Objectif : corriger orthographe, grammaire, style et phrases faibles.

Outils possibles :

* LanguageTool ;
* language_tool_python ;
* Harper à auditer.

Étapes concernées :

* Language Quality Pass ;
* Editorial Quality Gate ;
* rapport qualité ;
* correction avant brouillon final.

Usage attendu :

* détecter fautes ;
* détecter erreurs grammaticales ;
* détecter répétitions simples ;
* proposer corrections ;
* noter les problèmes dans le rapport.

Données à stocker :

* tool_name ;
* language ;
* issues_count ;
* issue_type ;
* suggestion ;
* applied_auto_fix ;
* manual_review_needed.

Intégration court terme :

* passe IA/heuristique si aucun outil n’est configuré ;
* rapport honnête : outil externe non utilisé.

Intégration complète :

* LanguageTool auto-hébergé ou remote ;
* adapter contrôlé ;
* timeout ;
* correction non destructive ;
* rapport avant/après.

Statut : LanguageTool prioritaire pour backend complet.

### 5B.5 Lisibilité

Objectif : évaluer la complexité du texte et repérer les phrases trop longues.

Outils possibles :

* textstat ;
* règles internes ;
* analyse de phrases maison.

Étapes concernées :

* ReadabilityScore ;
* SEOReview ;
* Editorial Quality Gate ;
* QualityPassReport.

Usage attendu :

* longueur moyenne des phrases ;
* paragraphes trop longs ;
* phrases trop complexes ;
* score lisibilité ;
* recommandations de simplification.

Limites :

* les formules de lisibilité ne sont pas parfaites en français ;
* ne pas traiter le score comme vérité absolue ;
* utiliser comme signal complémentaire.

Statut : intégrable rapidement avec règles internes, textstat à auditer.

### 5B.6 Originalité, anti-plagiat et anti-paraphrase faible

Objectif : éviter la copie et éviter la paraphrase faible.

Outils possibles :

* n-grams ;
* cosine similarity ;
* sentence-transformers ;
* embeddings ;
* Plagiarism-checker-Python à auditer ;
* autres outils open-source à auditer.

Étapes concernées :

* OriginalityReport ;
* Deep Reformulation Pass ;
* ResearchBrief comparison ;
* Editorial Quality Gate.

Usage attendu :

* comparer le brouillon avec les sources collectées ;
* détecter phrases trop proches ;
* détecter structures trop similaires ;
* détecter débuts de phrases identiques ;
* détecter expressions rares reprises ;
* exiger une reconstruction complète des passages suspects.

Règle absolue : le système ne doit pas faire de paraphrase faible. Il doit comprendre l’idée, fermer la source, reconstruire l’explication et produire une version originale.

Données à stocker :

* compared_sources ;
* similarity_method ;
* suspicious_passages ;
* risk_level ;
* heuristic_score ;
* real_plagiarism_tool_used ;
* manual_review_needed.

Limite : sans API spécialisée, le système ne peut pas prétendre mesurer le plagiat sur tout le web. Il peut seulement comparer contre les sources collectées.

Statut : heuristique obligatoire dans le backend complet, API réelle plus tard si nécessaire.

### 5B.7 Humanisation et suppression des traces IA

Objectif : rendre le texte naturel, direct, non robotique.

Outils possibles :

* humanizer comme inspiration ;
* règles internes ;
* passe IA dédiée ;
* listes d’anti-patterns éditoriaux.

Étapes concernées :

* AI Traces Removal Pass ;
* Editorial Quality Gate ;
* QualityPassReport.

À détecter :

* “il est recommandé de” répété ;
* “il est conseillé de” répété ;
* “il est important de noter que” ;
* “dans le monde numérique d’aujourd’hui” ;
* “de nos jours” ;
* transitions IA ;
* conclusions génériques ;
* répétitions de structure ;
* paragraphes sans valeur concrète.

Statut : à intégrer directement dans Editorial Quality Gate.

### 5B.8 SEO technique et audit site

Objectif : auditer le site et les articles publiés.

Outils possibles :

* python-seo-analyzer ;
* crawlers internes ;
* sitemap parser ;
* Search Console plus tard ;
* PageSpeed Insights plus tard.

Étapes concernées :

* SEO Watcher ;
* audit site mensuel ;
* recommandations post-publication ;
* ContentRefreshRecommendation.

Usage attendu :

* détecter pages faibles ;
* vérifier titles/meta ;
* vérifier liens cassés ;
* vérifier headings ;
* vérifier indexabilité ;
* vérifier maillage interne ;
* proposer mises à jour.

Statut : plus tard, après backend génération complet.

### 5B.9 Images, sources et attribution

Objectif : proposer des images utiles avec sources et droits clairs.

Outils possibles :

* médiathèque interne ;
* Unsplash API ;
* Wikimedia Commons API ;
* Pexels API si conditions compatibles ;
* sources officielles.

Étapes concernées :

* ImagePlan ;
* image_sources_json ;
* SEO images ;
* alt text ;
* captions.

Données à stocker :

* image_url ;
* source_url ;
* source_name ;
* author ;
* license ;
* alt_text ;
* caption ;
* usage_rights_status.

Règles :

* ne pas utiliser une image sans source claire ;
* ne pas prendre une image Google au hasard ;
* si licence incertaine, proposer à validation humaine ;
* sous l’image, afficher la source si image externe.

Statut : adapter à intégrer après génération texte, mais structure JSON à prévoir maintenant.

### 5B.10 Google officiel et veille SEO

Objectif : garder le système aligné avec les consignes Google.

Sources prioritaires :

* Google Search Central ;
* Google SEO Starter Guide ;
* Google Search Status Dashboard ;
* documentation updates ;
* core updates ;
* helpful content documentation.

Étapes concernées :

* Google Watcher ;
* SEO Expert Agent ;
* mise à jour des règles internes ;
* ContentRefreshRecommendation.

Usage attendu :

* surveiller les changements ;
* résumer les updates ;
* classer l’impact ;
* proposer des actions ;
* relier une update aux articles concernés.

Fréquence :

* sources Google officielles : quotidien ;
* blogs SEO secondaires : hebdomadaire ;
* audit articles : hebdomadaire ;
* audit site complet : mensuel.

Statut : service déjà préparé, veille active à implémenter plus tard.

### 5B.11 Knowledge packs SEO externes déjà audités

Repos utiles comme knowledge packs :

* AgriciDaniel/claude-seo ;
* ivankuznetsov/claude-seo ;
* aaron-he-zhu/seo-geo-claude-skills ;
* blader/humanizer.

Usage :

* workflows ;
* checklists ;
* prompts ;
* EEAT ;
* GEO/AEO ;
* humanization ;
* fact-check ;
* optimize.

Règles :

* ne pas exécuter leurs scripts ;
* ne pas installer directement ;
* ne pas brancher dans runtime FastAPI sans adapter ;
* transformer en règles internes ;
* garder commit hash audité ;
* vérifier licence.

Statut : utiliser comme base d’inspiration et de règles internes.

### 5B.12 Règle d’intégration des outils

Aucun outil externe ne doit être intégré sans :

* audit sécurité ;
* vérification licence ;
* vérification dépendances ;
* test isolé ;
* adapter contrôlé ;
* timeout ;
* logs ;
* désactivation possible ;
* statut clair dans le rapport.

Le système doit toujours dire la vérité :

* source utilisée réellement ;
* outil utilisé réellement ;
* outil indisponible ;
* résultat heuristique ;
* limite de confiance.

---

## 6. Génération d’idées

Avant de rédiger, le système doit déterminer quoi écrire.

Sources possibles :

* Google Autocomplete ;
* People Also Ask ;
* recherches associées Google ;
* Google Trends ;
* Search Console plus tard ;
* Bing ;
* Brave Search ;
* forums publics ;
* Reddit / Quora si accessible proprement ;
* commentaires publics ;
* articles concurrents ;
* articles déjà publiés sur le site ;
* catégories du site ;
* lacunes de contenu ;
* Ahrefs / Semrush / Ubersuggest / AnswerThePublic si API disponible.

Règle : si une source n’est pas réellement disponible, le système ne doit pas faire semblant.

Le rapport doit indiquer :

* recherche réelle : oui/non ;
* sources réellement utilisées ;
* sources non disponibles ;
* limites.

Une idée dans le Kanban doit contenir :

* titre proposé ;
* catégorie ;
* priorité ;
* fréquence liée à la catégorie ;
* mot-clé principal ;
* mots-clés secondaires ;
* intention détectée ;
* réponse attendue ;
* angle éditorial ;
* opportunité SEO ;
* source de l’idée ;
* niveau de confiance ;
* statut du brief ;
* date prévue.

Statuts possibles :

* idea_proposed ;
* idea_validated ;
* brief_ready ;
* writing_in_progress ;
* draft_ready ;
* rejected ;
* archived.

---

## 7. Analyse de l’intention réelle

Cette étape est obligatoire. Le système doit comprendre la vraie question derrière la question.

Il doit identifier :

* intention explicite ;
* intention implicite ;
* besoin pratique ;
* peur ou doute du lecteur ;
* niveau de connaissance du lecteur ;
* réponse attendue rapidement ;
* sous-questions réelles ;
* erreurs d’interprétation possibles ;
* informations à éviter.

Exemple : pour un sujet comme “Comment les jeunes hommes vivent leur première expérience sexuelle ?”, le système ne doit pas répondre uniquement avec l’âge moyen ou des statistiques générales. Il doit chercher le vécu concret : stress, satisfaction, plaisir, peur de ne pas être à la hauteur, envie de recommencer, gêne, erreurs fréquentes, etc.

Objet attendu : `IntentAnalysis`.

Champs :

* explicit_intent ;
* implicit_intent ;
* reader_real_question ;
* expected_answer ;
* sub_questions ;
* what_to_avoid ;
* risk_of_wrong_angle ;
* recommended_angle ;
* first_block_goal.

---

## 8. Règle du début d’article

Ancienne règle trop rigide : le premier H2 doit toujours donner la réponse directe.

Nouvelle règle : le début de l’article doit satisfaire rapidement l’intention principale du lecteur.

Selon le type d’article :

* question simple : le premier H2 peut donner la réponse principale ;
* comparaison : le premier H2 doit cadrer les critères de comparaison et aider à comprendre comment choisir ;
* guide pratique : le premier H2 doit donner la première action utile ;
* liste / classement : le premier H2 peut expliquer comment choisir ou lire la liste ;
* sujet sensible ou complexe : le premier H2 doit cadrer avec nuance, sans réponse simpliste.

Le lecteur doit sentir rapidement que l’article comprend ce qu’il cherche.

---

## 9. Recherche approfondie

Le système doit chercher avant de rédiger.

Recherche concurrentielle :

* résultats Google ;
* résultats Bing / Brave si disponibles ;
* articles concurrents ;
* titres ;
* H2/H3 ;
* angles ;
* sources ;
* réponses données ;
* manques ;
* contradictions ;
* points peu pratiques.

Recherche terrain :

* forums publics ;
* discussions publiques ;
* commentaires ;
* questions internautes ;
* Reddit / Quora si accessible légalement ;
* retours d’expérience publics.

But : trouver des questions concrètes, formulations réelles, frustrations, exemples pratiques, expériences et signaux humains.

Objet attendu : `ResearchBrief`.

Champs :

* sources_consulted ;
* competitor_angles ;
* common_answers ;
* missing_points ;
* contradictions ;
* field_signals ;
* practical_examples ;
* facts_to_include ;
* risks_or_uncertainties ;
* source_reliability_notes.

---

## 10. Recherche mots-clés

Le système prépare une stratégie de mots-clés.

Éléments :

* mot-clé principal ;
* mots-clés secondaires ;
* variantes longue traîne ;
* synonymes ;
* entités importantes ;
* questions associées ;
* termes à inclure naturellement.

Le système ne doit pas chercher uniquement la phrase exacte. Il doit comprendre les groupes importants.

Objet attendu : `KeywordBrief`.

Champs :

* main_keyword ;
* secondary_keywords ;
* long_tail_variants ;
* related_questions ;
* entities ;
* synonyms ;
* usage_strategy ;
* keyword_risk_notes.

---

## 11. Cannibalisation SEO

Avant de valider un sujet, le système doit vérifier si un article trop proche existe déjà.

Comparer avec :

* articles publiés ;
* brouillons ;
* idées existantes ;
* mots-clés ciblés ;
* slugs similaires ;
* titres similaires.

Objet attendu : `CannibalizationCheck`.

Champs :

* similar_articles ;
* similar_keywords ;
* risk_level ;
* recommendation.

Recommandations possibles :

* créer un nouvel article ;
* fusionner avec un article existant ;
* changer l’angle ;
* transformer en section d’un article existant.

---

## 12. Angle éditorial

Le système doit définir pourquoi l’article mérite d’exister.

Objet attendu : `EditorialAngle`.

Champs :

* editorial_promise ;
* main_angle ;
* reader_benefit ;
* differentiation ;
* tone ;
* eeat_opportunities.

Question centrale : pourquoi cet article sera-t-il meilleur ou plus utile que les autres ?

---

## 13. Plan de l’article

Règles structurelles :

* H1 = titre article ;
* introduction courte ;
* premier bloc principal = satisfaction rapide de l’intention ;
* H2 suivants = approfondissement ;
* H3 seulement si nécessaire ;
* si H3 sous un H2, minimum 2 H3 ;
* pas de H3 isolé ;
* H4 maximum ;
* pas de H5/H6 ;
* conclusion avec titre SEO naturel, pas forcément “Conclusion”.

Objet attendu : `ArticleOutline`.

Champs :

* h1 ;
* intro_goal ;
* sections ;
* first_block_goal ;
* conclusion_title ;
* faq_planned ;
* callouts_planned.

Chaque section contient :

* heading ;
* level ;
* purpose ;
* key_points ;
* sources_to_use ;
* reader_value.

---

## 14. Rédaction

Entrées :

* IntentAnalysis ;
* ResearchBrief ;
* KeywordBrief ;
* CannibalizationCheck ;
* EditorialAngle ;
* ArticleOutline ;
* règles SEO ;
* règles EEAT ;
* règles humanisation.

Sortie : HTML compatible TipTap.

Interdits :

* Markdown brut ;
* ## visibles ;
* [Mock] ;
* Lorem ipsum ;
* texte générique ;
* sections vides.

Style attendu : clair, humain, conversationnel, concret, utile, pas robotique, pas académique inutile, pas Wikipédia.

---

## 15. Listes

Chaque article doit contenir au moins une liste si le sujet s’y prête, mais aucune liste ne doit être forcée.

Utilisations utiles :

* étapes ;
* critères ;
* avantages ;
* erreurs ;
* éléments courts ;
* résumé rapide ;
* comparaison simple.

Règles :

* idéalement 3 à 7 éléments ;
* maximum 10 éléments sauf cas spécial ;
* si plus de 10 éléments, découper en sections ;
* si chaque élément est trop long, transformer en paragraphes ;
* idéalement une ligne par élément, deux lignes maximum si nécessaire.

Ponctuation souhaitée pour les listes à puces simples :

* chaque élément finit par un point-virgule ;
* le dernier peut finir par un point.

Exemple :

```txt
- vérifier l’intention du lecteur ;
- choisir un angle précis ;
- rédiger une réponse claire.
```

---

## 16. Tableaux

Le tableau est optionnel. Il est utilisé seulement s’il rend l’information plus claire.

Cas utiles :

* comparaison ;
* outils ;
* prix ;
* critères ;
* avantages / inconvénients ;
* résumé de différences ;
* étapes avec indicateurs.

Règles :

* maximum 3 à 5 colonnes ;
* cellules courtes ;
* pas de gros blocs de texte dans les cellules ;
* tableau utile, pas décoratif.

---

## 17. Images

Le système peut proposer des images, mais il ne doit pas utiliser n’importe quelle image Google sans source ni droit.

Sources préférables :

* médiathèque interne ;
* images uploadées ;
* sources officielles ;
* Wikimedia Commons si licence compatible ;
* banques d’images libres si licence compatible ;
* images générées plus tard si le système le permet.

Métadonnées obligatoires :

* image_url ;
* source_url ;
* source_name ;
* author ;
* license ;
* alt_text ;
* caption ;
* usage_rights_status.

Sous l’image, si elle vient d’une source externe, afficher une source avec lien.

Si la licence est incertaine : ne pas insérer automatiquement, proposer à validation, indiquer le risque de droit.

---

## 18. Callouts

Le système utilise les callouts existants du projet. S’il n’existe pas de template adapté, il peut proposer un callout nouveau.

Champs nécessaires :

* title ;
* text ;
* type ;
* main_color ;
* background_color ;
* border_color ;
* text_color ;
* placement ;
* reason.

Types possibles :

* information importante ;
* erreur à éviter ;
* chiffre clé ;
* conseil pratique ;
* publicité/service interne ;
* avertissement ;
* résumé express.

Règles :

* pas de callout forcé ;
* pas trop de callouts ;
* chaque callout doit avoir une raison ;
* un callout pub interne doit être pertinent.

---

## 19. FAQ

Règles :

* minimum 2 questions ;
* maximum 6 questions ;
* pas de FAQ si moins de 2 vraies questions utiles.

Stockage : `faq_json`, pas seulement HTML.

Format :

```json
[
  {
    "question": "...",
    "answer": "..."
  }
]
```

---

## 20. Maillage interne

Le système doit proposer des liens internes pertinents.

Il regarde :

* articles publiés ;
* catégories proches ;
* mots-clés proches ;
* sujets complémentaires ;
* pages importantes à pousser.

Chaque lien interne doit avoir :

* URL cible ;
* ancre proposée ;
* emplacement conseillé ;
* raison du lien ;
* degré de pertinence.

Pas de lien forcé si rien n’est pertinent.

---

## 21. Liens externes

Le système peut proposer des liens externes vers des sources fiables.

Liens externes utiles :

* études ;
* documents officiels ;
* outils cités ;
* pages de référence ;
* sources utilisées pour une information importante.

Règle : un lien externe doit apporter une preuve, une ressource ou une clarification. Pas de lien décoratif.

---

## 22. Correction langue

Après rédaction, vérifier :

* orthographe ;
* grammaire ;
* répétitions ;
* phrases trop longues ;
* paragraphes trop longs ;
* ton ;
* clarté ;
* cohérence.

Si aucun outil réel n’est branché, le rapport doit dire : correction linguistique heuristique / IA, outil externe non utilisé.

Plus tard, auditer LanguageTool, Harper ou autres correcteurs open-source.

---

## 23. Originalité et anti-plagiat

Le système doit éviter le paraphrasage faible.

Interdits :

* changer quelques mots seulement ;
* garder la même structure ;
* inverser deux propositions ;
* reprendre les mêmes phrases.

Méthode souhaitée :

1. lire la source ;
2. extraire les idées et faits ;
3. fermer la source ;
4. reformuler depuis le brief ;
5. changer l’angle d’explication ;
6. ajouter exemple, nuance ou application pratique ;
7. comparer avec la source ;
8. réécrire les passages trop similaires.

Objectif : plagiat maximum souhaité 15 %.

Si aucun vrai outil anti-plagiat n’est branché, ne pas prétendre mesurer le web entier. Faire un contrôle heuristique avec les sources collectées.

Objet : `OriginalityReport`.

---

## 24. EEAT

Le système doit renforcer :

* Experience ;
* Expertise ;
* Authoritativeness ;
* Trustworthiness.

Il peut ajouter :

* sources fiables ;
* données vérifiables ;
* exemples concrets ;
* nuances ;
* limites ;
* conseils pratiques ;
* retours terrain publics ;
* transparence sur incertitudes.

Interdits :

* fausses expériences personnelles ;
* fausses sources ;
* fausses données.

Objet : `EEATChecklist`.

---

## 25. Editorial Style & Formatting Gate

Cette étape est obligatoire avant le SEO final ou avant la sauvegarde finale.

Elle vérifie que le texte ne ressemble pas à un texte IA brut et qu’il respecte le style voulu.

### 25.1 Traces IA à réduire

Formulations à éviter ou limiter :

* il est recommandé de ;
* il est conseillé de ;
* il est important de noter que ;
* dans le monde numérique d’aujourd’hui ;
* de nos jours ;
* en conclusion, il convient de ;
* cet article explore ;
* plongeons dans ;
* il ne faut pas oublier que ;
* il est essentiel de comprendre que ;
* dans cet article, nous allons voir.

Préférer des formulations directes.

### 25.2 Répétitions

Repérer :

* idées répétées ;
* mêmes mots trop fréquents ;
* mêmes débuts de phrase ;
* transitions identiques ;
* paragraphes redondants.

Corriger par suppression, fusion, déplacement ou reformulation profonde.

### 25.3 Gras et italique

Interdits :

* paragraphe entier en gras ;
* liste entière en gras ;
* section entière en italique.

Le gras sert uniquement à mettre en valeur :

* mot-clé important ;
* expression clé ;
* idée centrale ;
* alerte importante ;
* contraste.

### 25.4 Majuscules

Pas de Title Case artificiel en français.

Mauvais :

```txt
Comment Créer Une Landing Page Pour Une Application Mobile
```

Bon :

```txt
Comment créer une landing page pour une application mobile
```

Exceptions : noms propres, marques, entreprises, sigles, début de phrase, titres officiels.

### 25.5 H2 suivi directement d’un H3

Un H2 ne doit jamais être suivi directement par un H3. Il doit y avoir au minimum une phrase ou un court paragraphe entre les deux.

Mauvais :

```html
<h2>Les critères à comparer</h2>
<h3>Le prix</h3>
```

Bon :

```html
<h2>Les critères à comparer</h2>
<p>Avant de choisir, il faut regarder les critères qui changent vraiment l’expérience et le coût final.</p>
<h3>Le prix</h3>
```

### 25.6 Tirets longs et symboles IA

Éviter les tirets longs dans le corps du texte :

* — ;
* –.

Remplacer par :

* phrase séparée ;
* parenthèse ;
* reformulation naturelle.

À éviter :

* tirets longs ;
* séparateurs artificiels ;
* symboles décoratifs ;
* emojis dans l’article sauf demande explicite ;
* caractères typiques de texte IA.

### 25.7 Listes

Vérifier :

* listes pas trop longues ;
* éléments pas trop longs ;
* ponctuation propre ;
* pas de liste entière en gras ;
* pas de listes qui remplacent un vrai développement.

Objet : `EditorialQualityReport`.

Champs :

* score ;
* passed_checks ;
* failed_checks ;
* issues ;
* recommendations ;
* auto_fixes_applied ;
* manual_review_needed.

---

## 26. SEO final

Le système vérifie :

* title ;
* slug ;
* meta title ;
* meta description ;
* keyword dans intro si naturel ;
* keyword dans headings si naturel ;
* premier bloc satisfait l’intention ;
* structure H2/H3/H4 ;
* FAQ ;
* liens internes ;
* liens externes ;
* images alt ;
* longueur ;
* lisibilité ;
* densité intelligente ;
* pas de keyword stuffing ;
* pas de contenu trop générique.

Objet : `SEOFinalChecklist`.

---

## 27. Données structurées

Plus tard, prévoir :

* Article schema ;
* FAQ schema si FAQ ;
* Breadcrumb schema ;
* Image metadata.

Ne pas tout forcer en V1, mais prévoir la structure.

---

## 28. Freshness et mise à jour

Le système doit détecter les articles à mettre à jour.

Critères :

* article ancien ;
* sujet sensible au temps ;
* changement Google ;
* baisse de performance Search Console plus tard ;
* nouvelles sources ;
* données obsolètes.

Objet : `ContentRefreshRecommendation`.

---

## 29. Google Watcher et veille SEO

Sources à surveiller :

* Google Search Central ;
* Google Search Status Dashboard ;
* Google SEO Starter Guide ;
* Google documentation updates ;
* Core updates ;
* Semrush Blog ;
* Ahrefs Blog ;
* Neil Patel ;
* autres sources SEO secondaires.

Fréquence :

* Google officiel : quotidien ;
* Search Status Dashboard : quotidien ;
* blogs SEO secondaires : hebdomadaire ;
* audit articles : hebdomadaire ;
* audit site complet : mensuel.

Objet : `SEOUpdateEvent`.

Champs :

* source ;
* title ;
* url ;
* summary ;
* impact_level ;
* affected_topics ;
* recommended_actions ;
* date_detected.

---

## 30. Sauvegarde finale dans Ideas Studio

L’article doit être sauvegardé avec :

* status = draft_ready ;
* published = false ;
* content = HTML propre ;
* title ;
* slug ;
* category_id ;
* meta_title ;
* meta_description ;
* excerpt ;
* keyword ;
* secondary_keywords_json ;
* reading_time_minutes ;
* faq_json ;
* callouts_json ;
* sources_json ;
* image_sources_json ;
* internal_links_json ;
* external_links_json ;
* seo_generation_brief_json ;
* intent_analysis_json ;
* research_brief_json ;
* keyword_brief_json ;
* editorial_angle_json ;
* outline_json ;
* eeat_checklist_json ;
* originality_report_json ;
* quality_pass_report_json ;
* editorial_quality_report_json ;
* seo_review_json ;
* generation_report_json.

Le système ne publie jamais automatiquement.

---

## 31. Front-end attendu

### 31.1 Éditeur

Panneau “SEO Expert” :

* score global ;
* score SEO ;
* score EEAT ;
* score lisibilité ;
* issues ;
* recommendations ;
* passed checks ;
* failed checks ;
* bouton relancer audit.

Panneau “Rapport de génération” :

* provider ;
* modèle ;
* titre demandé ;
* titre final ;
* catégorie ;
* mot-clé principal ;
* mots-clés secondaires ;
* intention détectée ;
* réponse attendue ;
* recherche réelle ou non ;
* sources utilisées ;
* images utilisées + sources ;
* plan utilisé ;
* FAQ générée ;
* callouts proposés ;
* limites ;
* étapes réalisées.

### 31.2 Kanban idées

Chaque carte idée affiche :

* titre ;
* catégorie ;
* priorité ;
* fréquence catégorie ;
* mot-clé principal ;
* intention ;
* opportunité SEO ;
* statut brief ;
* date prévue ;
* source de l’idée.

### 31.3 Paramètres pipeline

Afficher :

* pipeline actif/inactif ;
* pause jusqu’à ;
* jours actifs ;
* heures de travail ;
* articles/idées par période ;
* brouillons maximum ;
* catégories prioritaires ;
* fréquences par catégorie.

### 31.4 Page Catégories

Afficher et modifier :

* priorité ;
* fréquence mensuelle ;
* pipeline actif pour cette catégorie ;
* dernier article généré ;
* nombre d’articles ce mois-ci ;
* brouillons en attente.

---

## 32. Validation humaine

Le système donne :

* brouillon ;
* rapport ;
* scores ;
* issues ;
* recommandations.

L’humain décide :

* modifier ;
* relancer audit ;
* ajouter image ;
* publier ;
* programmer ;
* archiver.

---

## 33. Workflow final complet

```txt
MODE MANUEL OU AUTOMATIQUE

→ charger contexte projet
→ lire catégories + priorités + fréquences
→ choisir ou recevoir sujet
→ vérifier cannibalisation
→ trouver questions internautes
→ analyser intention réelle
→ faire recherche concurrentielle
→ faire recherche terrain
→ préparer mots-clés
→ définir angle éditorial
→ construire plan H2/H3/H4 selon le type d’article
→ vérifier checklist structurelle
→ rédiger article
→ ajouter liste utile si pertinent
→ ajouter tableau utile si pertinent
→ proposer images + sources
→ proposer callouts raisonnables
→ générer FAQ si utile
→ proposer liens internes
→ proposer liens externes
→ corriger langue
→ reformuler profondément si nécessaire
→ vérifier originalité
→ supprimer traces IA et répétitions
→ vérifier formatage éditorial
→ renforcer EEAT
→ vérifier SEO final
→ générer rapports
→ sauvegarder brouillon
→ afficher dans l’éditeur
→ validation humaine
→ publication ou programmation
```

---

## 34. Construction backend complète attendue

L’objectif n’est pas de créer seulement une petite V1 superficielle. L’objectif est de construire le backend complet du workflow éditorial, avec toutes les étapes métier prévues, même si certains outils externes restent en mode adapter non configuré au départ.

Le backend doit être pensé comme un orchestrateur complet : il prépare, cherche, analyse, rédige, corrige, vérifie, documente et sauvegarde.

### 34.1 Services backend à créer ou compléter

Services attendus :

* ProjectContextBuilder ;
* CategoryPriorityService ;
* PipelineSchedulerService ;
* IdeaDiscoveryService ;
* SerpResearchService ;
* SearchQuestionService ;
* IntentAnalysisService ;
* ResearchBriefService ;
* KeywordBriefService ;
* CannibalizationService ;
* EditorialAngleService ;
* ArticleOutlinePlanner ;
* WritingEngine ;
* ImagePlanService ;
* CalloutPlanService ;
* FAQService ;
* InternalLinkService ;
* ExternalLinkService ;
* LanguageQualityService ;
* OriginalityService ;
* HumanizationService ;
* EEATService ;
* EditorialQualityGate ;
* SEOFinalChecklistService ;
* GenerationReportService ;
* GoogleWatchService ;
* ContentRefreshService.

Chaque service doit avoir une responsabilité claire. Aucun fichier “super agent magique” ne doit tout faire seul.

### 34.2 Objets JSON à produire

Objets attendus :

* project_context_json ;
* category_strategy_json ;
* idea_discovery_json ;
* intent_analysis_json ;
* research_brief_json ;
* keyword_brief_json ;
* cannibalization_check_json ;
* editorial_angle_json ;
* outline_json ;
* image_plan_json ;
* image_sources_json ;
* callout_plan_json ;
* faq_json ;
* internal_links_json ;
* external_links_json ;
* language_quality_report_json ;
* originality_report_json ;
* humanization_report_json ;
* eeat_checklist_json ;
* editorial_quality_report_json ;
* seo_final_checklist_json ;
* seo_review_json ;
* generation_report_json ;
* sources_json.

Ces objets doivent permettre de comprendre ce qui a été fait pour chaque article.

### 34.3 Pipeline backend complet

Le backend doit pouvoir exécuter ce flux :

```txt
Input manuel ou automatique
→ ProjectContext
→ CategoryStrategy
→ IdeaDiscovery
→ CannibalizationCheck
→ IntentAnalysis
→ ResearchBrief
→ KeywordBrief
→ EditorialAngle
→ ArticleOutline
→ DraftWriting
→ ImagePlan
→ CalloutPlan
→ FAQPlan
→ InternalLinkPlan
→ ExternalLinkPlan
→ LanguageQualityPass
→ OriginalityPass
→ HumanizationPass
→ EEATPass
→ EditorialQualityGate
→ SEOFinalChecklist
→ GenerationReport
→ Save draft
```

Le système ne publie jamais automatiquement.

### 34.4 Frontend attendu après backend

Une fois le backend complet, le frontend devra afficher :

* cartes idées enrichies ;
* priorité et fréquence catégories ;
* état du pipeline ;
* rapport de génération ;
* rapport SEO Expert ;
* sources utilisées ;
* liens internes proposés ;
* liens externes proposés ;
* images et sources ;
* recommandations ;
* issues ;
* étapes réalisées ;
* limites.

Mais l’ordre de travail reste : backend propre d’abord, UI détaillée ensuite.

### 34.5 Statut des outils externes dans le backend

Les outils externes peuvent être présents sous forme d’adapters, même s’ils ne sont pas tous activés au départ.

Chaque adapter doit déclarer :

* enabled ;
* provider_name ;
* requires_api_key ;
* configured ;
* last_error ;
* real_data_available ;
* fallback_mode ;
* trust_level.

Si un outil n’est pas configuré, le rapport doit le dire clairement.

Exemple :

```txt
Recherche SERP réelle : non
Raison : SERP_API_KEY absente
Fallback : génération basée sur contexte interne et knowledge pack
```

### 34.6 Tests backend attendus

Tests à prévoir :

* génération manuelle respecte preferred_title ;
* catégorie sauvegardée ;
* priorité/fréquence catégorie utilisée ;
* mode automatique ne publie jamais ;
* pipeline pause fonctionne ;
* IntentAnalysis produit une intention ;
* ResearchBrief indique si recherche réelle ou non ;
* KeywordBrief contient main_keyword ;
* CannibalizationCheck détecte sujet similaire ;
* outline respecte H2/H3/H4 ;
* H2 suivi directement d’un H3 est détecté ;
* H3 isolé est détecté ;
* FAQ avec 1 question est rejetée ;
* liste trop longue est signalée ;
* tirets longs sont détectés ;
* title case artificiel est détecté ;
* gras abusif est détecté ;
* génération sauvegarde generation_report_json ;
* génération sauvegarde seo_review_json ;
* article reste brouillon ;
* sources absentes déclarées honnêtement ;
* outil externe non configuré ne produit pas de faux succès.

### 34.7 Définition de “backend terminé”

Le backend est considéré comme terminé lorsque :

* toutes les étapes du workflow existent sous forme de services ou fonctions ;
* chaque étape produit un objet ou une trace exploitable ;
* les rapports sont sauvegardés sur l’article ;
* les outils externes sont branchés par adapters ou marqués non configurés ;
* aucun faux résultat n’est affiché ;
* aucune publication automatique n’est possible ;
* la génération OpenAI utilise les briefs ;
* les contrôles éditoriaux et SEO s’exécutent ;
* les tests principaux passent.

### 34.8 Ce qui peut rester non activé mais doit être prévu

Certains éléments peuvent rester non activés si les clés/API ne sont pas encore disponibles, mais la structure backend doit exister :

* SERP provider réel ;
* Google Trends ;
* LanguageTool ;
* anti-plagiat avancé ;
* image sourcing externe ;
* Google Watcher actif ;
* Search Console ;
* PageSpeed ;
* Ahrefs/Semrush.

Dans ce cas, le système indique : non configuré, pas utilisé, fallback ou heuristique.
