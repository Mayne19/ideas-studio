# Plan de construction et de validation

Ce plan décrit la construction de l'algorithme isolé. Il ne donne aucune
autorisation de modifier le pipeline existant. Chaque étape doit produire une
preuve locale avant de passer à la suivante.

## Légende

- `validated` : construit et vérifié par un test local.
- `planned` : spécifié, mais pas encore construit.
- `blocked` : impossible à valider sans une dépendance ou une décision externe.

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
| A2 | Brancher la vraie recherche | Adaptateur vers `SerpAdapter` avec limite, déduplication et exclusion du domaine propre | Contrat faux SERP validé ; configuration réseau réelle encore séparée | `validated` |
| A3 | Brancher la vraie lecture | Adaptateur vers `PageCache` et extraction de contenu | Contrat de lecture et gestion d'échec validés ; factory CMS bloquée par l'environnement incomplet | `validated` |
| A4 | Construire le dossier concurrentiel | Forces, faiblesses, oublis et contradictions par page | Contrats et conditions bloquantes validés ; analyse sémantique réelle encore à brancher | `validated` |
| A5 | Comprendre le lecteur | Question réelle, niveau, piège et gain concret | Construction déterministe minimale validée ; analyse sémantique du modèle encore à brancher | `validated` |
| A6 | Construire le registre des faits | Faits, définitions, unités, sources, citations et statut | Fait confirmé, fait contradictoire et fait non vérifié | `planned` |
| A7 | Diversifier les sources | Au moins trois domaines admissibles, hors concurrents | Test de source dominante et test de sources suffisantes | `validated` |
| A8 | Choisir l'angle | Angle original fondé sur le lecteur et les lacunes | L'angle doit différer des concurrents et rester traçable | `planned` |
| A9 | Construire le plan complet | Introduction, call out, H2, H3, conclusion et FAQ | Contrats de sections et FAQ validés ; planification par le modèle encore à brancher | `validated` |
| A10 | Vérifier les zones de répétition | Matrice article/FAQ et matrice section/fait | Recouvrement FAQ/corps et recouvrement de faits détectés | `validated` |
| A11 | Brancher le rédacteur unique | Un appel de rédaction avec recherche, faits et plan complets | Faux client : un seul appel, JSON valide, contexte conservé | `planned` |
| A12 | Valider le brouillon | Structure, chiffres, définitions, répétitions, call out et conclusion | Erreurs bloquantes détectées ; aucune réécriture automatique stylistique | `planned` |
| A13 | Analyser le plagiat | Phrase, source, passage commun, score et suggestion séparée | Le brouillon initial reste inchangé après détection | `validated` |
| A14 | Conserver la meilleure version | Comparaison des versions sans dégrader un passage réussi | Égalité : conserver la version la plus ancienne | `validated` |
| A15 | Produire le rapport | Recherches, pages, coûts, sources, faits, contrôles, alertes et versions | Rapport JSON complet et lisible | `planned` |
| A16 | Ajouter la validation humaine | Validation, refus, commentaire et décision | Un refus ne publie rien | `planned` |
| A17 | Transformer les remarques en règles | Registre versionné des règles avec origine et test | Chaque nouvelle règle possède un test positif et un faux positif | `planned` |
| A18 | Comparer avec l'ancien système | Cinq sujets puis dix articles comparables | Score, coût, erreurs et temps comparés avant toute intégration | `planned` |

## Règles de progression

1. Une étape `planned` ne doit pas être présentée comme terminée.
2. Une étape ne passe à `validated` qu'avec une preuve locale enregistrée.
3. Les appels payants restent interdits pendant les tests unitaires.
4. Aucun résultat de laboratoire ne modifie un article existant.
5. Aucune correction stylistique automatique ne remplace une version réussie.
6. L'intégration dans Ideas Studio ne sera envisagée qu'après l'étape A18.
