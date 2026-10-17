# Plan de construction et de validation

Ce plan décrit la construction de l'algorithme isolé. Il ne donne aucune
autorisation de modifier le pipeline existant. Chaque étape doit produire une
preuve locale avant de passer à la suivante.

## Légende

- `validated` : construit et vérifié par un test local.
- `planned` : spécifié, mais pas encore construit.
- `blocked` : impossible à valider sans une dépendance ou une décision externe.
- `ready_for_live_run` : construit, mais l'essai réel n'a pas encore été exécuté.
- `out_of_algorithm` : volontairement hors du traitement automatique.
- `post_run_only` : intervient seulement après le résultat, sans boucle avec le modèle.
- `pending_real_sample` : harnais prêt, échantillon réel encore absent.

## Ce qui existe déjà et sera réutilisé

| Besoin de l'algorithme | Composant existant | Décision |
|---|---|---|
| Résultats web réels | `app/services/seo/adapters/serp_adapter.py` | Réutiliser via un adaptateur isolé. Il gère Serper, SerpAPI, Brave et Google CSE. |
| Lecture des pages | `PageCache`, `content_extraction_adapter`, `page_fetcher` | Réutiliser le cache, les règles robots et le lecteur de secours. |
| Sources primaires | `source_pages_service.py` | Réutiliser la sélection des pages officielles et la classification des sources. |
| Contexte et articles publiés | `published_articles()` et contexte de l'orchestrateur | Lire uniquement ; ne pas appeler directement le CMS depuis le cœur éditorial. |
| Agent avec outils | `AgentWriter` et `OpenRouterAgentClient` | Réutiliser le contrat d'appel, les budgets et la conversation persistante. |
| Prompt | `docs/AGENT-WRITER-PROMPT.md` | Reprendre les règles utiles, mais créer une version laboratoire avec le call out et la FAQ planifiée. |
| Structure HTML | `structure_validator`, `html_render_errors`, `announced_count_errors` | Réutiliser les contrôles déterministes après adaptation au nouveau plan. |
| Faits et sources | `fact_errors`, `quote_errors`, `source_balance_errors` | Réutiliser les règles, puis ajouter le lien entre fait et section du plan. |
| Plagiat | `plagiarism_check.py` | Réutiliser l'analyse SERP. Ne pas déclencher une réécriture automatique. |
| SEO final | `StructuredDataBuilder`, `SEOFinalChecklist` | Appeler seulement après validation du brouillon. |

## Étapes de construction

| ID | Étape | Sortie attendue | Validation | État |
|---|---|---|---|---|
| A0 | Isoler le laboratoire | Package indépendant, aucun import du pipeline dans le cœur | Compilation + tests faux fournisseurs | `validated` |
| A1 | Définir les contrats | Modèles pour contexte, lecteur, concurrents, faits, plan, FAQ, brouillon et rapport | Pydantic refuse les champs inattendus | `validated` |
| A2 | Brancher la vraie recherche | Adaptateur vers `SerpAdapter` avec limite, déduplication et exclusion du domaine propre | Lanceur réel prêt ; exécution réseau encore bloquée par les credentials absentes du runtime | `ready_for_live_run` |
| A3 | Brancher la vraie lecture | Adaptateur vers `PageCache` et extraction de contenu | Lanceur réel prêt ; exécution réseau encore bloquée par les credentials absentes du runtime | `ready_for_live_run` |
| A4 | Construire le dossier concurrentiel | Forces, faiblesses, oublis et contradictions par page | Prompt réel et sortie JSON préparés ; essai modèle encore nécessaire | `ready_for_live_run` |
| A5 | Comprendre le lecteur | Question réelle, niveau, piège et gain concret | Prompt réel préparé ; essai modèle encore nécessaire | `ready_for_live_run` |
| A6 | Construire le registre des faits | Faits, définitions, unités, sources, citations et statut | Citation absente, source non lue, fait non vérifié et concurrent utilisé comme source détectés | `validated` |
| A7 | Diversifier les sources | Au moins trois domaines admissibles, hors concurrents | Test de source dominante et test de sources suffisantes | `validated` |
| A8 | Choisir l'angle | Angle original fondé sur le lecteur et les lacunes | Prompt réel préparé ; essai modèle encore nécessaire | `ready_for_live_run` |
| A9 | Construire le plan complet | Introduction, call out, H2, H3, conclusion et FAQ | Prompt réel préparé ; essai modèle encore nécessaire | `ready_for_live_run` |
| A10 | Vérifier les zones de répétition | Matrice article/FAQ et matrice section/fait | Recouvrement FAQ/corps et recouvrement de faits détectés | `validated` |
| A11 | Brancher le rédacteur unique | Une seule production de contenu avec recherche, faits et plan complets | Client réel relié ; JSON invalide bloquant, sans tour de correction éditoriale | `ready_for_live_run` |
| A12 | Valider le brouillon | Structure, chiffres, définitions, répétitions, call out et conclusion | Rapport centralisé ; erreurs bloquantes séparées des alertes de similarité | `validated` |
| A13 | Analyser le plagiat | Phrase, source, passage commun et score | La détection déclenche au plus une réécriture ciblée, jamais une réécriture générale | `ready_for_live_run` |
| A14 | Conserver la meilleure version | Comparaison de la version initiale et de la version ciblée | Une version n'est gardée que si elle réduit le problème sans ajouter de faute structurelle ; égalité : garder l'initiale | `ready_for_live_run` |
| A15 | Produire le rapport | Recherches, pages, coûts, sources, faits, contrôles, alertes et version produite | Rapport JSON et rendu HTML prêts ; essai réel encore nécessaire | `ready_for_live_run` |
| A16 | Validation de l'éditeur | L'éditeur lit le résultat après l'exécution | Ne fait jamais partie de l'algorithme et ne déclenche aucune conversation automatique | `out_of_algorithm` |
| A17 | Transformer les remarques en règles | Évolution future du prompt par décision éditoriale | Opération manuelle ultérieure, sans modifier l'article en cours | `post_run_only` |
| A18 | Comparer avec l'ancien système | Cinq sujets puis dix articles comparables | Harnais prêt, échantillon réel encore absent | `pending_real_sample` |

## Règles de progression

1. Une étape `planned` ou `ready_for_live_run` ne doit pas être présentée comme validée en production.
2. Une étape ne passe à `validated` qu'avec une preuve locale enregistrée.
3. Les appels payants restent interdits pendant les tests unitaires.
4. Aucun résultat de laboratoire ne modifie un article existant.
5. Aucune correction stylistique automatique ne remplace une version réussie ; seule une similarité détectée peut déclencher une réécriture ciblée.
6. L'éditeur ne dialogue pas avec l'algorithme pendant un run ; il juge le résultat après coup.
7. L'intégration dans Ideas Studio ne sera envisagée qu'après l'étape A18.
