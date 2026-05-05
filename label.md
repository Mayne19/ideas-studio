# Ideas Studio — Document stratégique IA, SEO, outils et angles morts

Version : 1.0  
Statut : Annexe stratégique à `prod.md`  
Projet : Ideas Studio  
Objectif : documenter toutes les décisions, corrections, idées et modules ajoutés après réflexion sur le moteur IA/SEO du produit.

---

## 1. Rappel de la vision produit

Ideas Studio est un **CMS headless SEO assisté par IA** pour blogs et sites codés.

Le but n’est pas seulement de générer des articles. Le but est de créer une plateforme complète qui permet de :

- connecter un site ou un blog codé ;
- gérer plusieurs projets/blogs ;
- proposer automatiquement des idées de contenus SEO ;
- rédiger ou assister la rédaction ;
- analyser SEO, lisibilité, qualité, EEAT et structure ;
- vérifier les sources ;
- éviter le contenu générique ou trop proche des sources ;
- publier ou programmer ;
- suivre les performances ;
- recommander des optimisations après publication.

Principe central :

```txt
L’IA propose.
L’humain valide.
L’IA rédige.
L’humain corrige.
Le CMS publie.
Le système surveille.
L’IA recommande.
L’humain garde le contrôle.
```

---

## 2. Correction majeure : ne pas chercher “une IA magique”

Décision importante :

```txt
Ne pas créer notre propre LLM.
Ne pas dépendre d’un seul LLM.
Créer un système intelligent autour de plusieurs modèles, données, règles et workflows.
```

Un LLM seul ne suffit pas pour faire un bon outil SEO.

Un vrai moteur SEO sérieux repose sur :

```txt
données fraîches
+ SERP analysée
+ sources vérifiables
+ extraction propre
+ règles SEO
+ analyse concurrentielle
+ LLM puissant aux bons endroits
+ validation humaine
+ suivi après publication
```

Donc la stratégie de Ideas Studio est :

```txt
Construire un Strategic SEO Engine
et non un simple générateur d’articles IA.
```

---

## 3. Positionnement renforcé

Ideas Studio ne doit pas essayer de copier Semrush, Ahrefs ou SE Ranking.

Ces outils sont très larges :

- base de mots-clés massive ;
- backlinks ;
- rank tracking ;
- audit technique ;
- trafic estimé ;
- analyse concurrentielle globale ;
- publicités ;
- keyword research massive.

Ideas Studio doit être plus concentré :

```txt
Créer, vérifier, publier et optimiser du contenu SEO utile, fiable et vérifiable.
```

Positionnement recommandé :

```txt
Ideas Studio aide les créateurs de blogs codés, freelances et petites agences à produire,
publier et optimiser des contenus SEO vérifiables sans dépendre d’un CMS lourd comme WordPress.
```

Avantage recherché :

```txt
Semrush analyse beaucoup de choses.
Ideas Studio analyse moins de choses, mais transforme directement l’analyse en contenu publiable, vérifié, suivi et optimisable.
```

---

## 4. Ce que les grands outils SEO font vraiment

Les outils comme Semrush, Ahrefs, Ubersuggest ou SE Ranking ne sont pas devenus puissants grâce à une IA magique.

Ils reposent surtout sur :

```txt
1. Crawlers web
2. Bases de données de mots-clés
3. Snapshots de SERP
4. Backlink index
5. Estimations de trafic
6. Audits techniques
7. Règles SEO
8. Scoring statistique
9. Historique de données
```

L’IA moderne est venue comme couche supplémentaire :

```txt
Avant l’IA :
SEO tools = data + crawlers + règles + statistiques

Après l’IA :
SEO tools = data + crawlers + règles + statistiques + LLM
```

Ideas Studio doit suivre la même logique, mais sur un périmètre plus petit.

---

## 5. Objectif SEO stratégique : donner à Google “le bon bonbon”

L’idée retenue :

Google ne veut pas seulement un “bonbon”.  
Il veut le bon bonbon, avec le bon goût, la bonne qualité et la bonne intention.

Traduction produit :

```txt
Google Candy Engine
```

Ce moteur doit répondre à ces questions :

```txt
1. Qu’est-ce que Google semble favoriser dans la SERP actuelle ?
2. Quelle est l’intention réelle de l’utilisateur ?
3. Quels formats dominent les meilleurs résultats ?
4. Que couvrent les concurrents ?
5. Que manque-t-il dans les contenus existants ?
6. Quel angle peut apporter plus de valeur ?
7. Quelles sources sont nécessaires ?
8. L’article est-il utile, fiable, complet et humain ?
9. Est-il publiable maintenant ?
10. Que faut-il améliorer après publication ?
```

---

## 6. Nouveau score recommandé : Google Fit Score

En plus des scores déjà prévus dans `prod.md`, ajouter :

```txt
Google Fit Score /100
```

Décomposition possible :

```txt
Search Intent Fit      25 points
Content Completeness   20 points
Helpful Value          20 points
EEAT / Trust           15 points
On-page SEO            10 points
Readability            5 points
Freshness              5 points
```

But :

```txt
Mesurer si l’article correspond vraiment à ce que Google et l’utilisateur attendent.
```

Ce score ne garantit pas la position 1.  
Il maximise les chances de produire un contenu utile, pertinent et compétitif.

---

## 7. Architecture IA recommandée

Architecture globale :

```txt
Ideas Studio AI Engine

Search Layer
  - SearXNG
  - Tavily fallback optionnel

Extraction Layer
  - Trafilatura
  - BeautifulSoup4
  - readability-lxml

LLM Gateway
  - LiteLLM
  - Ollama
  - OpenAI
  - Anthropic / Claude
  - Gemini
  - Mistral
  - OpenRouter si nécessaire

Local / Open-weight Models
  - Qwen
  - DeepSeek
  - Mistral
  - gpt-oss
  - Llama / Gemma selon tests

SEO Intelligence
  - SERP Intent Analyzer
  - Competitor Content Analyzer
  - Content Gap Analyzer
  - Helpful Content Scorer
  - EEAT Analyzer
  - Google Fit Score

Quality Layer
  - LanguageTool pour correction uniquement
  - readability rules
  - originality checks
  - source verification

Workflow Layer
  - FastAPI services d’abord
  - RQ/Redis pour jobs
  - LangGraph plus tard si workflows complexes
  - DSPy plus tard pour optimiser les prompts
```

---

## 8. Décision sur LanguageTool

Correction importante :

```txt
LanguageTool ne doit pas être utilisé comme moteur de reformulation profonde.
```

Rôle accepté :

```txt
LanguageTool = correction grammaticale, orthographe, ponctuation, style léger.
```

Rôle refusé :

```txt
LanguageTool ≠ moteur de deep rewrite
LanguageTool ≠ moteur anti-plagiat
LanguageTool ≠ moteur de rédaction SEO premium
LanguageTool ≠ moteur de reformulation profonde
```

Pourquoi ?

Parce que les reformulations testées restent trop proches du texte source.  
Elles changent quelques mots, mais gardent la même structure.

Ideas Studio doit éviter ce type de résultat.

---

## 9. Nouveau module : Deep Rewrite Engine

Ajouter un module :

```txt
Deep Rewrite Engine
```

Objectif :

```txt
Réécrire à partir du sens, pas paraphraser phrase par phrase.
```

Pipeline :

```txt
1. Extraire les faits importants.
2. Comprendre l’intention.
3. Identifier le public cible.
4. Créer un nouveau plan.
5. Changer l’ordre logique si nécessaire.
6. Rédiger avec un angle propre.
7. Ajouter de la clarté et de la valeur.
8. Éviter les formulations proches des sources.
9. Vérifier l’originalité.
10. Corriger seulement à la fin.
```

Règles interdites :

```txt
- garder la même structure phrase par phrase ;
- remplacer seulement des synonymes ;
- suivre exactement l’ordre de la source ;
- reprendre les mêmes formulations ;
- produire un texte trop proche d’une source ;
- publier un article sans contrôle de similarité.
```

Règles obligatoires :

```txt
- extraire les faits ;
- réorganiser les idées ;
- clarifier ;
- adapter au public ;
- écrire naturellement ;
- citer les sources importantes ;
- vérifier l’originalité.
```

---

## 10. Nouveau module : Natural Writing Engine

Objectif :

```txt
Obtenir un style plus naturel, fluide, humain et clair.
```

Le but est de se rapprocher de la qualité d’écriture naturelle d’un bon modèle comme Claude, même lorsque Claude n’est pas disponible.

Ce module doit contenir :

```txt
1. Style Guide
2. Exemples de style
3. Rewrite pass
4. Human tone checker
5. Anti-generic checker
```

Style attendu :

```txt
- phrases naturelles ;
- ton clair ;
- explication progressive ;
- peu de jargon ;
- exemples concrets ;
- transitions fluides ;
- pas de remplissage ;
- pas de phrases marketing creuses ;
- pas de répétition mécanique ;
- pas de style robotique ;
- pas de paraphrase phrase par phrase.
```

Pipeline recommandé :

```txt
Passe 1 : rédaction
Passe 2 : naturalisation du style
Passe 3 : vérification sources/originalité
Passe 4 : correction grammaticale finale
```

---

## 11. Nouveau module : Source Verification Engine

Décision majeure :

```txt
Ideas Studio doit produire du contenu vérifiable.
```

Le système ne doit pas seulement générer un article.  
Il doit pouvoir montrer d’où vient chaque information importante.

Ajouter :

```txt
Source Verification Engine
```

Responsabilités :

```txt
1. stocker toutes les sources consultées ;
2. extraire les faits importants ;
3. relier chaque fait à une ou plusieurs sources ;
4. classer les sources par autorité ;
5. signaler les affirmations non sourcées ;
6. signaler les contradictions ;
7. empêcher la publication si trop d’affirmations importantes sont invérifiables.
```

Structure possible :

```txt
app/services/sources/
  source_collector.py
  source_ranker.py
  claim_extractor.py
  claim_source_mapper.py
  citation_generator.py
  hallucination_checker.py
  source_freshness_scorer.py
  contradiction_detector.py
```

---

## 12. Source Ledger

Ajouter un objet ou une table :

```txt
source_ledger
```

Rôle :

```txt
Garder la trace de toutes les sources utilisées, citées, rejetées ou simplement consultées.
```

Différencier :

```txt
sources consultées
sources citées publiquement
sources internes
sources rejetées
sources contradictoires
sources trop faibles
```

Champs possibles :

```txt
id
project_id
article_id
url
title
domain
author
published_at
accessed_at
source_type
authority_score
freshness_score
extraction_quality_score
used_in_article
publicly_cited
rejected_reason
created_at
```

---

## 13. Claim-to-Source Mapping

Ajouter un système qui relie les affirmations importantes à leurs sources.

Chaque claim doit avoir :

```txt
claim_id
article_id
text
importance
source_ids
verification_status
confidence_score
created_at
```

Statuts :

```txt
verified
partially_verified
unverified
contradicted
needs_review
```

---

## 14. Claim Importance Classifier

Toutes les phrases n’ont pas besoin d’une source.

Mais les affirmations importantes doivent être vérifiées.

Ajouter :

```txt
Claim Importance Classifier
```

Niveaux :

```txt
low       = phrase générale
medium    = conseil ou explication standard
high      = définition, comparaison, tendance, fait technique
critical  = chiffre, prix, date, santé, droit, finance, sécurité
```

Règle :

```txt
high ou critical = source obligatoire
```

---

## 15. Number Verification Engine

Les chiffres sont dangereux.

Ajouter :

```txt
Number Verification Engine
```

Il vérifie :

```txt
statistiques
prix
pourcentages
dates
classements
volumes
nombres d’utilisateurs
années
tendances temporelles
```

Chaque chiffre doit avoir :

```txt
source
date
contexte
niveau de confiance
```

Règle :

```txt
Aucun chiffre important ne doit être publié sans source.
```

---

## 16. Source Authority Score

Ajouter :

```txt
Authority Score /100
```

Critères positifs :

```txt
source officielle
documentation produit
gouvernement
université
organisme reconnu
média spécialisé fiable
auteur identifiable
date récente
sources internes de la page
cohérence avec d’autres sources
```

Critères négatifs :

```txt
blog anonyme
contenu affilié agressif
pas d’auteur
pas de date
contenu trop ancien
pas de sources
promesses exagérées
contenu généré automatiquement
site faible ou douteux
```

---

## 17. Source Freshness Score

Toutes les sources ne vieillissent pas pareil.

Ajouter :

```txt
Source Freshness Score
```

Règles :

```txt
SEO trends             source très récente obligatoire
prix logiciel          source très récente obligatoire
actualité IA           source très récente obligatoire
définition générale    source ancienne acceptable
tutoriel technique     source récente recommandée
comparatif outils      source récente obligatoire
```

Le système doit adapter l’exigence de fraîcheur au type d’article.

---

## 18. Source Contradiction Detection

Ajouter :

```txt
Source Contradiction Detector
```

Exemple :

```txt
Source A : outil gratuit
Source B : essai gratuit puis payant
```

Le système doit signaler :

```txt
information contradictoire
confirmation nécessaire
ne pas affirmer catégoriquement
```

Sorties possibles :

```txt
verified
conflicting
uncertain
needs_manual_review
```

---

## 19. Originality Engine

Objectif :

```txt
Éviter les articles copiés, paraphrasés trop près ou structurellement trop proches des sources.
```

Vérifications :

```txt
similarité phrase par phrase
similarité paragraphe par paragraphe
n-gram overlap
fuzzy matching
longest common subsequence
similarité par embeddings
similarité de structure
répétition des formulations sources
sections trop génériques
```

Scores :

```txt
similarity_score
source_overlap_score
sentence_reuse_score
structure_similarity_score
originality_score
```

Règle :

```txt
Si similarité trop haute → rewrite obligatoire.
```

---

## 20. Generic AI Content Detector

Un texte peut être unique mais sentir l’IA fade.

Ajouter :

```txt
Generic AI Content Detector
```

Il détecte :

```txt
phrases creuses
intros génériques
conclusions inutiles
phrases type “dans un monde numérique...”
absence d’exemples concrets
conseils évidents
répétitions
absence d’expérience
ton trop neutre
paragraphes interchangeables
```

Action :

```txt
Si contenu trop générique → retour au Deep Rewrite Engine.
```

---

## 21. Helpful Content Scorer

Ajouter un score spécifique :

```txt
Helpful Content Score /100
```

Critères :

```txt
répond vraiment à la question
aide le lecteur à agir
explique clairement
apporte de la valeur originale
évite le remplissage
reste aligné avec l’intention
n’exagère pas dans le titre
donne exemples concrets
ne se limite pas à reformuler les concurrents
```

---

## 22. EEAT Analyzer renforcé

Le module EEAT doit vérifier :

```txt
Experience
- exemples concrets
- cas pratiques
- vécu ou démonstration
- captures/preuves si applicable

Expertise
- précision technique
- sources solides
- concepts bien expliqués
- absence d’erreurs évidentes

Authoritativeness
- auteur identifiable
- site cohérent sur le sujet
- maillage interne thématique
- références fiables

Trustworthiness
- sources vérifiables
- dates
- absence d’affirmations risquées non sourcées
- transparence
```

Ajouter :

```txt
Trust Score /100
```

Basé sur :

```txt
sources fiables
citations vérifiées
fraîcheur
auteur
similarité faible
pas d’affirmations critiques non sourcées
pas de liens cassés
```

---

## 23. Live SEO Editor

L’éditeur doit faire une partie des analyses en direct.

### Checks instantanés sans LLM

```txt
word count
longueur title
longueur meta description
présence keyword dans title
présence keyword dans intro
structure H2/H3
paragraphes trop longs
phrases trop longues
liens internes
liens externes
images alt
FAQ présente
densité approximative
readability basique
```

Fréquence :

```txt
toutes les 1 à 2 secondes
```

### Checks IA en arrière-plan

```txt
content gap
EEAT
natural writing score
source verification
originality check
SERP fit
helpful content score
generic AI detection
```

Fréquence :

```txt
bouton manuel “Analyser”
ou toutes les 30 à 60 secondes
ou job background
```

But :

```txt
Ne pas exploser les coûts.
Ne pas ralentir l’éditeur.
Garder l’expérience fluide.
```

---

## 24. Panneau sources dans l’éditeur

Ajouter une sidebar :

```txt
Sources utilisées
```

Fonctions :

```txt
voir les sources liées à une phrase
voir les sources citées publiquement
voir les sources consultées
voir les extraits sources
voir le niveau d’autorité
voir le niveau de fraîcheur
voir les claims non vérifiés
voir les contradictions
```

Quand l’utilisateur clique sur une phrase :

```txt
Statut :
- vérifié
- partiellement vérifié
- non vérifié
- contradictoire
```

---

## 25. Safe Publish Gate

Un article ne doit pas être publiable si :

```txt
trop d’affirmations importantes sont non vérifiées
des chiffres importants ne sont pas sourcés
le texte est trop proche des sources
les sources sont faibles
l’intention de recherche n’est pas couverte
le contenu est trop générique
le score EEAT est trop bas
le score Google Fit est trop bas
des liens importants sont cassés
des erreurs critiques existent
```

Règle :

```txt
Si le système n’est pas sûr, il ne publie pas.
Il explique ce qui manque.
```

---

## 26. Search Intent Analyzer

Le système doit détecter :

```txt
intention informationnelle
intention transactionnelle
intention navigationnelle
intention commerciale
intention locale
intention mixte
```

Il doit aussi analyser :

```txt
format dominant SERP
niveau de profondeur attendu
types de résultats dominants
présence vidéos
présence forums
présence marketplaces
présence sites officiels
présence comparatifs
présence guides longs
```

Sortie :

```txt
intent_primary
intent_secondary
recommended_format
risk_of_wrong_angle
```

---

## 27. Content Gap Analyzer

Comparer l’article avec les meilleurs résultats.

Vérifier :

```txt
sujets couverts par concurrents
sections manquantes
FAQ manquante
exemples manquants
sources manquantes
angle moins clair
profondeur insuffisante
données obsolètes
maillage interne faible
```

Sortie :

```txt
missing_sections
weak_sections
unique_opportunities
recommended_additions
```

---

## 28. Ranking Difficulty Reality Check

Parfois, il ne faut pas écrire.

Ajouter :

```txt
Ranking Difficulty Reality Check
```

Détecter :

```txt
SERP dominée par sites officiels
SERP dominée par marketplaces
SERP dominée par YouTube
SERP dominée par gros médias
SERP dominée par forums
SERP dominée par très gros domaines
mot-clé trop compétitif
intent incompatible avec le site
```

Verdicts possibles :

```txt
écrire maintenant
viser une longue traîne
changer l’angle
améliorer un article existant
abandonner
attendre plus de data
```

---

## 29. Anti-Cannibalization Engine

Éviter que plusieurs articles du même projet se concurrencent.

Vérifier :

```txt
keyword déjà ciblé
article similaire existant
même intention
même angle
même audience
risque de doublon
```

Décisions :

```txt
créer nouvel article
fusionner avec article existant
mettre à jour ancien article
changer angle
changer keyword
```

---

## 30. Internal Linking Engine

Ajouter un vrai moteur de maillage interne.

Il propose :

```txt
liens internes à ajouter
anchor text recommandé
articles liés
pages piliers
clusters thématiques
liens manquants
liens trop nombreux
```

Il utilise :

```txt
articles existants
embeddings
catégories
keywords
intentions
performance
```

---

## 31. Topical Authority / Content Cluster Engine

Ne pas penser article par article seulement.

Ajouter :

```txt
Content Cluster Engine
```

Il organise :

```txt
page pilier
articles secondaires
guides pratiques
définitions
comparatifs
tutoriels
FAQ
études de cas
```

But :

```txt
Construire une autorité thématique au lieu de publier des articles isolés.
```

---

## 32. Article Templates

Prévoir des templates selon le type de contenu :

```txt
guide complet
comparatif
liste d’outils
avis produit
tutoriel
définition
FAQ
article local
étude de cas
actualité
mise à jour
page pilier
```

Chaque template doit définir :

```txt
structure H2/H3
niveau de sources requis
longueur cible
type d’intention
éléments obligatoires
risques SEO
```

---

## 33. ContentBrief comme objet séparé

Ne pas mélanger idée et article.

Ajouter :

```txt
ContentBrief
```

Champs :

```txt
project_id
article_id
keyword
intent
audience
angle
sources
competitors
required_sections
forbidden_sections
internal_links
citation_requirements
eeat_requirements
tone
recommended_length
publication_risks
created_at
```

Workflow :

```txt
Idea → ContentBrief → Draft → Analysis → Review → Publish
```

---

## 34. Model Router et coûts

Ajouter un routeur de modèles.

Règle :

```txt
tâche simple → modèle local
tâche moyenne → modèle open-weight puissant
tâche critique → modèle premium
```

Exemples :

```txt
Correction simple          LanguageTool / local
Résumé source              Qwen / Mistral / DeepSeek
Analyse SERP               modèle fort
Content gap                modèle fort
Rédaction finale           meilleur modèle disponible
Vérification hallucination modèle fort + sources
```

Chaque tâche doit enregistrer :

```txt
model_used
provider
tokens_input
tokens_output
cost_estimate
latency
success_status
```

---

## 35. Model Performance Registry

Tous les modèles ne seront pas bons partout.

Ajouter :

```txt
Model Performance Registry
```

Il enregistre :

```txt
modèle
task_type
qualité moyenne
coût moyen
latence
taux erreur JSON
taux hallucination
score utilisateur
dernière évaluation
```

Le système choisit progressivement le meilleur modèle par tâche.

---

## 36. AI Output Evaluator

Chaque sortie IA doit être évaluée.

Vérifier :

```txt
réponse complète
format JSON valide
sources présentes
pas d’invention visible
ton respecté
structure respectée
article utilisable
score minimum atteint
```

Si la sortie échoue :

```txt
retry
changer modèle
demander validation humaine
marquer job failed
```

---

## 37. Prompt Versioning

Les prompts sont un actif important.

Ajouter :

```txt
prompts/
  idea_generation.md
  serp_analysis.md
  content_gap.md
  deep_rewrite.md
  eeat_check.md
  natural_style.md
  seo_brief.md
  optimization.md
  source_verification.md
  originality_check.md
```

Chaque prompt doit avoir :

```txt
prompt_id
version
task_type
model_target
input_variables
expected_output_schema
last_updated
success_score
```

Chaque génération doit enregistrer :

```txt
prompt_version_used
```

---

## 38. Human Feedback Learning

Le système doit apprendre des corrections humaines.

Stocker :

```txt
corrections fréquentes
phrases supprimées
style préféré
sections rejetées
sources préférées
sources interdites
types d’idées rejetées
longueur préférée
niveau de détail préféré
```

Objectif :

```txt
Adapter progressivement le style au projet.
```

---

## 39. Article Versioning

Chaque modification doit être traçable.

Stocker :

```txt
ancienne version
nouvelle version
qui a modifié
pourquoi
date
score avant
score après
sources ajoutées
sources supprimées
modèle utilisé
```

Indispensable pour :

```txt
audit
comparaison
rollback
confiance utilisateur
collaboration
```

---

## 40. Audit Trail

Au-delà des articles, tracer :

```txt
qui a publié
qui a modifié
qui a validé
qui a rejeté
qui a lancé l’IA
qui a accepté une recommandation
qui a supprimé une source
qui a modifié une clé API
```

---

## 41. Job System relançable

Chaque étape IA doit être un job indépendant.

Types de jobs :

```txt
research_job
brief_job
writing_job
rewrite_job
seo_analysis_job
source_verification_job
originality_job
publish_job
optimization_job
```

Chaque job :

```txt
status
started_at
finished_at
error
retry_count
input_snapshot
output_snapshot
model_used
cost_estimate
priority
```

Actions nécessaires :

```txt
cancel
pause
retry
resume from step
```

---

## 42. Pipeline failures

Gérer les échecs partiels.

Exemple :

```txt
SERP OK
extraction concurrent échoue
rédaction OK
source verification échoue
```

Le système doit décider :

```txt
continuer
bloquer
relancer étape échouée
marquer incomplet
demander validation humaine
```

---

## 43. Over-Optimization Detector

Le système doit éviter de trop optimiser pour Google.

Détecter :

```txt
keyword stuffing
titre trop optimisé
FAQ artificielle
liens internes forcés
répétition excessive du mot-clé
texte écrit pour robot
paragraphes remplis de keywords
```

Objectif :

```txt
Optimiser sans rendre le contenu artificiel.
```

---

## 44. YMYL Safety Mode

Pour les sujets sensibles :

```txt
santé
finance
droit
emploi
sécurité
immigration
assurance
investissement
médical
```

Règles :

```txt
sources fortes obligatoires
pas de conseils catégoriques dangereux
avertissement si nécessaire
review humaine obligatoire
publication bloquée si incertitude
```

---

## 45. Google Update Watcher

Ajouter un module de veille Google.

Surveiller :

```txt
Google Search Central Blog
documentation Search Central
Helpful Content updates
Core Updates
Spam Updates
Search Quality Rater Guidelines
changements liés IA/SEO
```

Actions :

```txt
alerte admin
mise à jour des règles SEO
réanalyse des articles sensibles
recommandations globales
```

---

## 46. Import d’articles existants

Ideas Studio doit pouvoir analyser un blog déjà existant.

Fonctions :

```txt
importer articles
récupérer title/meta/content/slug
calculer scores
détecter contenus faibles
proposer mises à jour
proposer maillage interne
éviter cannibalisation
```

---

## 47. Preview SEO

Ajouter :

```txt
Preview Google snippet
```

Afficher :

```txt
title
meta description
URL
preview desktop
preview mobile
longueur title
longueur meta
risque troncature
```

---

## 48. Connexion réelle avec sites codés

Documenter :

```txt
Next.js integration
Vite/React integration
Astro integration
Nuxt integration
plain HTML integration
MDX export
API public articles
preview drafts
cache invalidation
webhooks
```

Un CMS headless doit fournir des exemples concrets.

---

## 49. Webhooks

Ajouter :

```txt
article.published
article.updated
article.deleted
article.scheduled_published
project.connected
tracking.received
```

Usage :

```txt
rebuild site
invalidate cache
notify frontend
sync external systems
```

---

## 50. API publique : cache et sécurité

Prévoir :

```txt
cache headers
ETag
pagination
CDN
rate limiting
CORS propre
fallback si API down
```

Endpoints sensibles :

```txt
/api/public/projects/{id}/articles
/api/public/projects/{id}/articles/{slug}
/traffic.js
/api/traffic/collect
```

---

## 51. Tracking script quality

`traffic.js` doit être :

```txt
léger
rapide
non bloquant
respectueux privacy
résistant aux erreurs
sans casser le site client
compatible cache
```

Ajouter :

```txt
bot filtering
crawler detection
spam detection
anonymous visitor hash
IP anonymization si applicable
```

---

## 52. Privacy / RGPD

À prévoir :

```txt
cookie consent selon besoin
anonymisation IP
durée conservation données
export données utilisateur
suppression compte
suppression projet
droit à l’oubli
privacy policy
logs sans données sensibles
```

---

## 53. Data retention

Définir combien de temps garder :

```txt
logs IA
sources extraites
anciens prompts
versions articles
traffic events
analyses SEO
recommandations rejetées
jobs échoués
```

---

## 54. Backup / Restore

Prévoir :

```txt
backup quotidien
restore testé
export projet
import projet
plan de récupération
```

---

## 55. Environnements

Séparer :

```txt
local
staging
production
```

Avec :

```txt
clés différentes
bases différentes
providers IA différents
données test séparées
```

---

## 56. Observabilité

Ajouter :

```txt
logs structurés
erreurs workers
temps de génération
échecs LLM
échecs scraping
coûts par tâche
alertes
monitoring API
monitoring jobs
```

---

## 57. Quotas et budget IA

À prévoir :

```txt
budget IA par projet
budget IA par utilisateur
articles/mois
recherches SERP/mois
rewrites/mois
tokens maximum
mode économique
mode premium
alertes dépassement
```

---

## 58. Monétisation future

Même si billing n’est pas V1, prévoir :

```txt
plan gratuit limité
plan solo
plan agence
crédits IA
limite projets
limite articles
limite recherches
limite modèles premium
```

---

## 59. Onboarding utilisateur

Créer un flow clair :

```txt
Créer projet
Ajouter domaine
Choisir langue/pays
Définir audience
Ajouter catégories
Installer snippet
Connecter API articles
Lancer première idée
Créer premier brief
Publier premier article
```

---

## 60. Permissions fines

Rôles déjà prévus, mais préciser :

```txt
writer peut-il lancer IA ?
writer peut-il voir sources ?
writer peut-il publier ?
editor peut-il gérer clés ?
viewer peut-il voir coûts ?
admin peut-il supprimer définitivement ?
owner peut-il gérer billing ?
```

---

## 61. Autosave et recovery

Dans l’éditeur :

```txt
autosave toutes les X secondes
draft recovery
historique local
conflit si deux utilisateurs modifient
restore version
```

---

## 62. Export

Prévoir :

```txt
export Markdown
export HTML
export JSON
export MDX
export WordPress plus tard
```

---

## 63. Author profiles et Reviewed By

Pour renforcer EEAT :

```txt
auteur
bio auteur
expertise
photo
liens sociaux/pro
articles écrits
reviewed by
date de mise à jour
sources vérifiées le
```

---

## 64. Broken Link Checker

Vérifier :

```txt
liens internes cassés
liens externes morts
redirections
404
sources disparues
```

---

## 65. Internationalisation et SEO local

Prévoir :

```txt
langue
pays cible
vocabulaire local
SERP locale
exemples locaux
devise locale
date locale
contexte culturel
```

Un article SEO France, Canada, Bénin ou Allemagne ne doit pas être traité pareil.

---

## 66. Timezone

Pour publication programmée :

```txt
scheduled_at en UTC
timezone utilisateur
timezone projet
affichage local
```

---

## 67. Evergreen vs News

Le système doit différencier :

```txt
evergreen
actualité
comparatif
tutoriel
définition
tendance
guide annuel
```

Chaque type a :

```txt
fréquence de mise à jour
exigence de fraîcheur
niveau de sources
risque d’obsolescence
```

---

## 68. Benchmark qualité

Tester Ideas Studio contre :

```txt
article humain moyen
article ChatGPT brut
article Claude brut
article concurrent top 3 Google
article généré par Ideas Studio
```

Mesurer :

```txt
utilité
clarté
originalité
sources
SEO
EEAT
readability
generic score
```

---

## 69. Competitive Comparison View

Dans l’éditeur ou l’analyse :

```txt
Ton article
vs concurrent 1
vs concurrent 2
vs concurrent 3
```

Comparer :

```txt
longueur
sections
FAQ
sources
angle
profondeur
fraîcheur
EEAT
liens
structure
```

---

## 70. File d’attente éditoriale

Créer un vrai workflow type Kanban :

```txt
idées proposées
idées validées
briefs prêts
articles en rédaction
articles à relire
articles prêts à publier
articles publiés
articles à optimiser
```

---

## 71. Tableau des outils retenus

### À intégrer dans Ideas Studio

```txt
LiteLLM
Ollama
SearXNG
Trafilatura
LanguageTool uniquement correction
Qwen
DeepSeek
Mistral
gpt-oss
```

### À utiliser pour coder Ideas Studio

```txt
Claude Code
Gemini CLI
OpenClaude
SonarQube
```

### À utiliser comme inspiration ou plus tard

```txt
LangGraph
DSPy
GPT Researcher
pgvector / Qdrant / Chroma
```

### À éviter comme base sérieuse

```txt
Free-Claude-Opus
faux Claude Opus
system prompt leaks
proxies inconnus
comptes/API douteux
dark web
clones non fiables
```

---

## 72. Rôle des outils

### LiteLLM

```txt
LLM Gateway
Model Router
Fallback system
Cost tracking
Provider abstraction
```

### Ollama

```txt
Runtime local pour modèles open-weight
```

### SearXNG

```txt
SearchProvider auto-hébergeable
SERP collector léger
```

### Trafilatura

```txt
Extraction propre du contenu concurrent
```

### LanguageTool

```txt
Correction orthographe/grammaire/style léger
```

### Qwen

```txt
analyse structurée
long contexte
JSON
SEO brief
content gap
reformulation profonde
```

### DeepSeek

```txt
raisonnement
analyse concurrentielle
décisions SEO
audit logique
```

### Mistral

```txt
rédaction naturelle
français
réécriture
style européen
```

### gpt-oss

```txt
expérimentation open-weight
tâches locales
raisonnement
classification
```

---

## 73. Structure de dossiers recommandée

```txt
app/services/
  strategic_seo/
    serp_collector.py
    competitor_extractor.py
    intent_analyzer.py
    content_gap_analyzer.py
    google_fit_score.py
    ranking_difficulty.py
    helpful_content_scorer.py
    over_optimization_detector.py

  writing/
    fact_extractor.py
    content_brief_generator.py
    deep_rewrite_engine.py
    natural_writing_engine.py
    originality_checker.py
    generic_ai_detector.py

  sources/
    source_collector.py
    source_ranker.py
    source_freshness.py
    claim_extractor.py
    claim_source_mapper.py
    contradiction_detector.py
    number_verifier.py
    citation_generator.py

  models/
    llm_gateway.py
    model_router.py
    model_registry.py
    cost_tracker.py

  prompts/
    prompt_loader.py
    prompt_versioning.py

  jobs/
    job_runner.py
    retry_manager.py
    job_logger.py

  optimization/
    internal_linking_engine.py
    topical_authority_engine.py
    google_update_watcher.py
    update_recommender.py

  quality/
    ai_output_evaluator.py
    language_checker.py
    broken_link_checker.py
    safe_publish_gate.py
```

---

## 74. Tables nouvelles à prévoir

```txt
sources
source_ledger
claims
claim_sources
content_briefs
google_fit_analyses
originality_checks
model_runs
model_performance
prompt_versions
article_versions
audit_logs
ai_jobs
internal_link_suggestions
content_clusters
google_update_alerts
api_keys
webhooks
```

---

## 75. Roadmap recommandée

### MVP strict

```txt
auth
projects
articles
categories
public API
tracking simple
idea generation
writing mock/premium
SEO analyzer simple
editor API
manual publish
basic performance
```

### V1 renforcée

```txt
LLM Gateway
SearXNG
Trafilatura
Deep Rewrite Engine
Source Ledger
Originality Engine
Google Fit Score
Safe Publish Gate
Live SEO Editor
```

### V1.5

```txt
Anti-Cannibalization
Internal Linking
ContentBrief
Model Router
Prompt Versioning
AI Output Evaluator
Source Authority Score
Number Verification
Article Versioning
```

### V2

```txt
Search Console
Google Update Watcher
Topical Authority Engine
Competitive Comparison View
Author Profiles
Reviewed By
Webhooks
SDK examples
billing
advanced quotas
LangGraph/DSPy
```

### Plus tard

```txt
backlink analysis
rank tracking massif
keyword database maison
traffic estimation externe
A/B testing avancé
team collaboration avancée
```

---

## 76. Règle finale de produit

Ideas Studio ne doit pas être :

```txt
un simple générateur d’articles IA
un clone Semrush
un clone WordPress
un paraphraseur
un outil de spam SEO
un système qui publie sans contrôle
```

Ideas Studio doit être :

```txt
un CMS headless SEO assisté par IA
qui produit des contenus utiles, naturels, vérifiables,
alignés avec l’intention de recherche,
optimisés sans sur-optimisation,
reliés à des sources,
contrôlés par un humain,
suivis après publication,
et améliorés dans le temps.
```

---

## 77. Checklist finale avant publication d’un article

```txt
[ ] Intention de recherche identifiée
[ ] Format SERP compris
[ ] Content brief validé
[ ] Sources collectées
[ ] Sources d’autorité vérifiées
[ ] Claims importants sourcés
[ ] Chiffres vérifiés
[ ] Pas de contradiction critique
[ ] Article naturel
[ ] Pas de contenu générique IA
[ ] Similarité faible avec sources
[ ] SEO on-page OK
[ ] Google Fit Score acceptable
[ ] Helpful Content Score acceptable
[ ] EEAT Score acceptable
[ ] Trust Score acceptable
[ ] Liens internes proposés
[ ] Liens externes utiles
[ ] Broken links vérifiés
[ ] Meta title OK
[ ] Meta description OK
[ ] Preview Google vérifiée
[ ] Human review faite
[ ] Safe Publish Gate validé
```

---

## 78. Conclusion

La grande décision finale :

```txt
Le vrai avantage de Ideas Studio ne sera pas un modèle IA secret.
Le vrai avantage sera le système complet :
données fraîches + sources vérifiables + analyse SERP + réécriture profonde + contrôle qualité + validation humaine + suivi post-publication.
```

Autrement dit :

```txt
Le LLM écrit.
Le système vérifie.
L’humain valide.
La performance décide des optimisations futures.
```

C’est cette combinaison qui peut transformer Ideas Studio en outil sérieux, et non en simple générateur d’articles.
