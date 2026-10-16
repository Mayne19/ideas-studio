# Audit de la chaîne éditoriale d'Ideas Studio, agent par agent, et proposition de chaîne v2

## Synthèse

Les articles sont propres mais génériques parce que la chaîne est construite ainsi. L'hypothèse « si chaque agent fait son travail à 100 % et qu'ils sont bien connectés, le résultat sera excellent » ne tient pas ici, pour trois raisons.

1. **Les agents qui produiraient du gain d'information n'existent pas.** Aucun agent ne lit réellement les pages concurrentes, et aucun ne construit de tableau de couverture.
2. **La plupart des sorties d'analyse ne parviennent jamais au rédacteur.** C'est le cas des content gaps, des angles concurrents, des mots-clés secondaires, des sous-questions et des URL des faits.
3. **Les juges ne mesurent pas votre grille et ne déclenchent rien.** Le fact-check n'a pas accès aux sources. Le juge LLM tourne après le calcul du score et ses verdicts ne sont pas utilisés.

Le rédacteur reçoit au plus 6 « faits », tirés de snippets SERP de 500 caractères au maximum. Il a aussi pour consigne de n'écrire aucun chiffre absent de ces faits. Avec si peu de matière, il produit des conseils génériques.

Le coût LLM actuel est d'environ 0,01 à 0,015 $ par article. Le budget ne limite donc pas la qualité.

---

## 1. Inventaire des agents

### 1.A Étapes réellement exécutées, dans l'ordre de `generate_full_article`

Abréviations utilisées dans le tableau :
- **orch** : `app/services/seo/seo_generation_orchestrator.py`
- **SW** : `section_writer.py`
- **PB** : `production_brief_service.py`
- **AS** : `agents/agent_services.py`

| # | Étape (agent du registre) | Type | Entrées | Sortie (artefact) | Qui consomme en aval | Verdict |
|---|---|---|---|---|---|---|
| 1 | ProjectContext (`category_context_builder`) | heuristique | projet en base | `project_context` (orch:280, 681) | audience (orch:668, PB:62) ; `used_angles`, injectés dans le brief du rédacteur (orch:1272-1274) | utile et bien branché, apport faible |
| 2 | CategoryStrategy (`topic_selector`) | heuristique | catégories | `category_strategy` (orch:285) | `chosen_category` (orch:289) | utile si aucune catégorie n'est fournie |
| 3 | IdeaDiscovery (`demand_discovery`) | dict statique, ou LLM si ni titre ni mot-clé | titre/mot-clé | `idea_discovery` (orch:293-331) | `angle`, utilisé par la reformulation de l'intention (intent_analysis_service.py:177) | partiel : en production, c'est presque toujours le dict statique |
| 3b | `extract_main_keyword` (`keyword_research`) | LLM, conditionnel | titre | mot-clé (orch:342) | tout le pipeline | utile |
| 4 | CannibalizationCheck (`cannibalization_check_initial`) | heuristique | titre, mot-clé | `cannibalization_check` (orch:348) | un simple log (orch:354), sans arrêt | exécuté mais résultat ignoré |
| 5 | IntentAnalysis (`intent_analysis`) | heuristique lexicale | titre, mot-clé | `intent_analysis` (orch:358) | écrasé à l'étape 6e (orch:453) | sert seulement de repli |
| 6 | ResearchBrief (`research_brief` / `search_serp`) | Serper + scraper | mot-clé | `research_brief` (orch:367) : URL, titre, snippet, H2/H3 | intention 6e, mots-clés 7a, evidence pack, plan, liens externes | branché mais appauvri : le texte des pages est jeté (voir §3) |
| 6b | SourceQuality (`source_quality_checker`) | scraper | URL | `quality_check` par source (orch:377) | prompt de l'evidence pack (AS:116-121), tier des liens | utile, mais refait les téléchargements de l'étape 6 (source_quality_service.py:139) |
| 6c | HumanInsights (pas d'id au registre) | scrapers Reddit, Stack Overflow, Nitter, Quora, YouTube et Google PAA | mot-clé | `human_insights` (orch:388-424, 697) | content gaps ; 4 questions, 4 difficultés et 3 exemples injectés « si utile » (orch:1275-1283) ; FAQ (orch:1774-1788) | partiel et bruité : classement par mots-clés (human_insights_service.py:172-188), scraping de Google PAA (l.481) |
| 6d | ContentGap (`gap_identifier`) | heuristique | insights, angles concurrents, articles **du projet** | `content_gaps` (orch:429, 698) | PB:99-102, puis `production_brief_to_text` (PB:117), **qui n'a aucun appelant** ; bonus de +10 dans `value_added` (scoring_service.py:70) | exécuté mais résultat ignoré par le rédacteur, et nuisible dans le score |
| 6e | IntentAnalysisRefine (`intent_analysis`) | LLM | titre, mot-clé, 8 snippets de 180 caractères | `intent_analysis` affiné | plan, production brief, brief de section (`reader_real_question`, `expected_answer`, `must_include` / `must_avoid`) | **utile et bien branché** : c'est le seul vrai pilote du contenu |
| 6f | TitleGeneration (`meta_writer`) | LLM, conditionnel | mot-clé, intention, titres concurrents | titre (orch:472) | brouillon | utile |
| 7 | KeywordBrief | heuristique (« X guide », « X conseils ») | mot-clé | `keyword_brief` (orch:493) | écrasé en 7a | doublon |
| 7a | KeywordResearch (`keyword_research`) | LLM sur snippets | snippets | `keyword_brief` (orch:509) | plan (mots-clés secondaires tronqués à 200 caractères, article_outline_planner.py:128) ; PB:80-82 sans transmission au rédacteur ; `entities` lues par personne | exécuté, presque ignoré |
| 7b | EvidencePack (`evidence_pack_builder`) | LLM | snippet + meta description, ≤ 500 caractères par source (AS:124-128) | `evidence_pack` | 6 faits maximum, **sans URL**, dans chaque section (SW:191-198) ; cohérence (orch:1392) ; GEO (orch:925) | branché mais nourri de presque rien |
| 8 | EditorialAngle (`editorial_angle`) | déterministe | intention | `editorial_angle` (orch:532) | `main_angle` ; `differentiation` vaut seulement « Éviter : … » (editorial_angle_service.py:24) | doublon : reformule l'intention |
| 9 | Outline (`outline_planner`) | LLM | intention, angles concurrents en chaîne de 400 caractères (article_outline_planner.py:115, 127) | `outline` (orch:540) | SectionWriter | utile, sans benchmark ni gabarit de composants |
| 9b | CannibalizationCheckOutline (`cannibalization_check_outline`) | heuristique | **mêmes arguments qu'à l'étape 4** (orch:552 contre 348) | `cannibalization_outline` | indices de liens internes (orch:564-568, 612) | doublon : n'utilise pas le plan |
| 9c | Section cannibalization | heuristique | plan | `section_cannibalization` (orch:573) | un log | exécuté mais résultat ignoré |
| 10 | ImagePlan (`media_planner`) | LLM + Unsplash | H2 | `image_plan`, `image_sources` (orch:585) | `insert_images_in_content` (orch:1547-1549) | utile et bien branché |
| 11 | CalloutPlan (`callout_planner`) | heuristique (« Le mot-clé principal est… », callout_plan_service.py:35) | gabarits | `callout_plan` | compteur dans le rapport (orch:1979) uniquement ; `draft.callouts` n'est jamais rempli | mort fonctionnellement |
| 12 | FAQPlan | heuristique (réponses « (à développer) », faq_plan_service.py:16) | sous-questions | `faq_plan` (orch:602) | passé à `_finalize_report`, qui ne l'utilise pas | mort |
| 13 | InternalLinkPlan (`internal_link_planner`) | heuristique | base de données | `internal_links` | bloc de liens du rédacteur (orch:1306-1307), CitationPass (orch:1432) | utile |
| 14 | ExternalLinkPlan (`external_link_planner`) | heuristique + téléchargements | `research_brief` | `external_links` | rédacteur (SW:225-229), CitationPass | utile |
| 14a | StyleAdaptation (`style_guide_builder`) | LLM + 3 gabarits fixes | profil éditorial | `style_adaptation` (orch:716) | prompt système du rédacteur (orch:1240-1250) | faible valeur |
| 14c | ProductionBrief (`production_brief_builder`) | assemblage | tous les artefacts amont | `production_brief` (orch:741) | **seul un sous-ensemble passe au rédacteur** via `build_section_brief` (SW:175-199) | goulot d'étranglement (§2) |
| 15 | Writing (`writer`) | LLM : introduction, une section par H2, fin (orch:1485-1489) | brief compact, plan, liens, exemple de style | HTML | tout l'aval | utile, mais privé de contexte |
| 15a | WritingPass_QualityGate (`writer`) | LLM, **réécriture complète** « phrases creuses » (orch:1498-1528) | article | HTML | article | faible valeur, risque de lisser le texte (un garde-fou limite la casse) |
| 15b | Proofreading, Consistency, Citation (`writer`) | LLM ciblé + code (orch:1531-1533) | article, faits | HTML + rapports | article | **utiles et bien conçus** |
| 15c | Garde-fous (structure, mots, style, présence humaine, volumétrie) | heuristiques (orch:1544-1611) | HTML | 5 artefacts | logs ; `human_presence` pèse 14 % du score | journalisation seulement |
| 15d | ArticleReviewer + juge « moment de surprise » (`originality_angle_judge`) | heuristique + LLM sans la SERP (AS:872-884) | HTML | `article_review_report` (orch:1586) | avertissement non bloquant (validation_service.py:241-251) ; aucune réécriture (orch:1599-1602) | exécuté mais résultat ignoré |
| 15e | Méta title et description (`meta_writer`) | 2 appels LLM, **titre + mot-clé seulement** (orch:1618-1621, 1641-1644) | titre | `ArticleSeo` | publication | branché, résultat générique |
| 15f | FAQ (`faq_generator`) | LLM sur `content[:1500]` (orch:1799) | 1 500 premiers caractères + insights | `draft.faq` | données structurées | partiel : ignore les PAA de la SERP et la fin de l'article |
| 15g | HumanInsightsUsageGuard | heuristique (orch:829, 1174-1216) | HTML | limitation | log | exécuté mais résultat ignoré |
| 16 | LanguageQuality (`language_quality`) | LanguageTool ou heuristique | HTML | `language_quality_report` | revue SEO agrégée | journalisation seulement |
| 17 | Originality (`originality_checker`) | n-grammes **contre les snippets** (orch:833-836, 851) | HTML | `originality_report` | 16 % du score ; peut bloquer la validation (scoring_service.py:177-186) | nuisible : mesure vide de sens, et bloquante |
| 18 | Humanization (`humanizer`) | heuristique | HTML | `humanization_report` | revue agrégée | journalisation seulement |
| 18b | Readability | heuristique | brouillon | `readability_report` | 15 % du score | signal de surface |
| 19 | EEAT (`eeat_reviewer`) | heuristique (liens, titres) ; la couche LLM n'est **jamais appelée** car aucun budget n'est passé (orch:880, eeat_service.py:232, 254-258) | HTML | `eeat_checklist` | 18 % du score | signal de surface |
| 20 | EditorialQualityGate (`editor`, `quality_gate`) | heuristique (H5/H6, tirets…) | HTML | `editorial_quality_report` | `quality_score` (orch:1734) | contrôle de forme (lint) |
| 21a | StructuredData (`structured_data_builder`) | déterministe | brouillon | `structured_data` (orch:918) | artefact | utile |
| 21b | GEO (`geo_answer_optimizer`) | heuristique | brouillon, evidence | `geo_optimization` (orch:926) | affichage et avertissement < 80 ; aucun poids dans le score | exécuté, presque ignoré |
| 21c | SEOFinalChecklist (`seo_final_checklist`) | heuristique | brouillon | `seo_final_checklist` | 27 % du score, liste des problèmes | utile (pour le critère SEO à 5 points) |
| 21d | AutoScoring | agrégation | artefacts | `ArticleScore` (orch:957, 1710-1740) | validation, notification | nuisible (§3.7) |
| 22 | SEOReview (`seo_optimizer`) | heuristique | rapports | `seo_review` (orch:969) | **écrase** le `seo_review` écrit par `run_and_store_seo_review` (orch:1720) | doublon |
| 23 | ClaimExtraction (`claim_extractor`) | LLM (orch:979) | HTML | `extracted_claims` | **aucun consommateur** (le fact-checker ne le reçoit pas) | mort fonctionnellement |
| 24 | FactCheck (`fact_checker`) | LLM **sans aucune source** (AS:51-61) | HTML | `fact_check_report` (orch:991) | la validation vérifie seulement sa présence et son statut (validation_service.py:168-178), jamais les verdicts « inaccurate » | exécuté mais résultat ignoré |
| 25 | QualityGate LLM (`quality_gate`) | LLM sans brief ni sources (AS:543-560) | HTML | `editorial_quality_report.llm_review` (orch:1007-1011) | rien : il tourne **après** AutoScoring | exécuté mais résultat ignoré |
| 26 | ErrorManager, GenerationReport | déterministe | erreurs, étapes | `error_analysis`, `generation_report` | interface | utiles (observabilité) |

### 1.B Agents du registre jamais appelés pendant la génération

Le registre compte 65 entrées : 46 canoniques et 19 alias hérités.

| Agent | Constat | Verdict |
|---|---|---|
| `seo_optimizer`, fonction LLM `seo_optimize_content` (AS:394) | aucun appelant | mort (le registre pointe vers `seo_review_service`, heuristique) |
| `editor`, fonction LLM `editorial_review` (AS:437) | aucun appelant | mort |
| `quality_rate_article` (AS:477) | aucun appelant | mort |
| `reader_retention_checker` (AS:571) | aucun appelant, seulement cité dans une note (article_reviewer_service.py:220) | mort |
| `engagement_editor`, `improve_engagement` (AS:609) | aucun appelant | mort |
| `coherence_editor` | statut `disabled` (agent_registry.py:322) | mort, assumé |
| `scraper_extractor` / `researcher` (`content_extraction_adapter`) | seulement `get_status` (orch:1948) ; `extract()` avec trafilatura n'est jamais utilisé | mort, alors qu'il serait la pièce clé |
| `trend_detector` | utilisé seulement dans idea_discovery quand un `context_hint` est fourni (idea_discovery_service.py:87) | quasi mort |
| `cost_estimator` | `estimate_workflow_cost` n'est pas appelé ; seul `estimate_call_cost` l'est, par le routeur (agent_router.py:284) | partiel |
| `cost_tracker` | aucune implémentation | coquille vide |
| `google_watch` | seulement `get_status` | mort |
| `content_gap_analyzer` | le registre renvoie à `research_brief_service` (agent_registry.py:140) alors que le vrai agent est `gap_identifier` | doublon, étiquette fausse |
| `quality_gate` | déclaré `requires_llm=False` (agent_registry.py:567) alors que `run_quality_gate` est un LLM | métadonnée fausse |
| `idea_generator` (`idea_engine`) | actif dans le pipeline, mais `idea_prebrief` (idea_engine.py:478) **n'est jamais relu** | sortie ignorée |
| 15 alias avec `alias_of`, plus 4 alias hérités sans cible (`trend_detector`, `editorial_strategist`, `content_planner`, `brief_writer`) | servent uniquement à la compatibilité des assignations (agent_registry.py:858-870) | alias, à masquer |

---

## 2. Flux de données actuel (✗ = lien cassé)

```
Idée (idea_engine) ──> idea_prebrief {angle, format, main_answer_summary, search_questions, secondary_kw}
        ✗ jamais relu (pipeline_service.py:479-489 et ideas.py:174-185 passent seulement titre, mot-clé, catégorie, intention)
        │
        ▼
ProjectContext ─ CategoryStrategy ─ Cannibalisation (log seul)
        │
Serper (organic seulement ; ✗ peopleAlsoAsk / relatedSearches / answerBox ignorés, serp_adapter.py:82)
        │
Scrapling.scrape_competitor ─> titres H1-H4, méta, text_preview[:500] (scrapling_adapter.py:203)
        ✗ texte complet jeté ; text_preview non stocké (research_brief_service.py:111-117)
        │
        ├─> SourceQuality (re-télécharge les 12 URL) ─> qualité ──> EvidencePack (snippet + méta ≤ 500 caractères)
        ├─> HumanInsights (scrapers bruités) ─┬─> ContentGap (comparé au projet, pas à la SERP)
        │                                     │      └─> production_brief.content_gaps ✗ production_brief_to_text jamais appelé
        │                                     └─> 4 questions, 4 difficultés, 3 exemples « si utile » ─> rédacteur (faible)
        ├─> competitor_angles ─> Outline (chaîne de 400 caractères, « titres différents ») ; ✗ vers le rédacteur
        ├─> IntentRefine (LLM) ════════> must_include / must_avoid / expected_answer ═══> Outline + rédacteur  ✔ seul lien fort
        └─> KeywordResearch (LLM) ─> secondary_kw ─> Outline (200 caractères) ; ✗ vers le rédacteur ; ✗ entities
        │
EditorialAngle (reformulation) ─> main_angle ─> rédacteur ; differentiation = « Éviter… »
        │
ProductionBrief (tout est assemblé) ──✗ build_section_brief garde ~9 champs ; faits sans URL ni usage_hint ; les mêmes 6 faits dans CHAQUE section
        │
SectionWriter (intro + H2 + fin) ─> réécriture QualityGate (lissage) ─> Relecture ─> Cohérence ─> Citations ─> images
        │
Méta (titre + mot-clé seulement) ─> FAQ (content[:1500]) ─> persist_revision (orch:1669)
        │
Lints : langue, originalité (contre snippets), humanisation, lisibilité, EEAT, qualité éditoriale, GEO, checklist SEO
        │
AutoScoring (score global = signaux de surface + « value_added » = présence d'artefacts) ─> notification « prêt à valider »
        │
APRÈS le score : ClaimExtraction ✗ (aucun consommateur) ; FactCheck ✗ (sans sources, non bloquant) ; QualityGate LLM ✗ (informatif)
        │
Validation : bloque seulement si le score est incomplet ou si fact_check / originalité / date manquent ; jamais sur la qualité réelle
```

Cinq sorties calculées n'atteignent jamais le rédacteur : `content_gaps`, `competitor_angles`, `sub_questions` / `related_questions`, `secondary_keywords` / `entities`, `idea_prebrief`. Le contenu du fact-check, le `quality_grade`, l'EEAT, le GEO, l'`article_review` et les `extracted_claims` ne déclenchent aucune action. Enfin, l'artefact `sources` lu par la validation (validation_service.py:63) n'est jamais écrit. L'avertissement « Aucune source » s'affiche donc toujours.

---

## 3. Pourquoi les articles sont génériques

1. **La recherche se limite à des snippets.** Le scraper télécharge bien les pages, mais il ne garde que les titres et 500 caractères (scrapling_adapter.py:203). Le research brief ne stocke même pas ces 500 caractères (research_brief_service.py:111-117). L'evidence pack ne voit que snippet + méta description, coupés à 500 caractères (AS:124-128). Pour un « guide prix » ou un « comparatif », le rédacteur n'a donc aucun prix, aucune grille tarifaire, aucune fonctionnalité réelle. La consigne anti-hallucination « N'écris aucun chiffre… absent des faits » (SW:311) est justifiée. Mais combinée à un dossier de preuves vide, elle produit de la généralité par construction.
2. **Il n'y a aucun benchmark concurrentiel.** Les H2 concurrents arrivent au plan sous forme d'une chaîne tronquée à 400 caractères, avec la consigne d'avoir des titres « différents » (article_outline_planner.py:115, 127, 139). Personne ne mesure ce que couvrent les 3 à 5 premiers résultats, ce qui fait consensus ni ce qui manque. Les « gaps » sont calculés contre les articles du projet (content_gap_service.py:150-171), donc tout H2 concurrent devient un « manque ».
3. **Rien ne planifie le gain d'information.** L'angle reformule l'intention (editorial_angle_service.py:20-27). Aucun agent ne répond à la question « que va apporter cet article que le top 5 n'a pas ? » (tableau original, exemple chiffré, arbre de décision, pièges vécus). Aucun agent ne demande non plus à l'expert ses données propres. C'est pourtant l'avantage de codeur.com : les données de sa plateforme.
4. **Un seul gabarit sert tous les formats.** Il existe 5 formats (intent_analysis_service.py:10). Ils ne changent que le nombre de H2 (article_outline_planner.py:12-18) et l'objectif de la conclusion (SW:404-408). Aucun composant n'est obligatoire : un comparatif n'a pas de tableau imposé, un guide prix pas de fourchettes datées, un how-to pas de prérequis ni de checklist. Le prompt système est générique (orch:1223-1239) et l'exemple de style unique porte sur les maquettes (writing_reference_examples.py:14-36). Résultat : la même voix et la même forme partout.
5. **Le rédacteur manque de contexte.** `build_section_brief` (SW:175-199) écarte les sous-questions, les mots-clés secondaires, les entités, les angles concurrents, les gaps, la `differentiation`, les URL et l'`usage_hint` des faits. Chaque section reçoit les 6 mêmes faits : ils se répètent ou disparaissent. Aucun fait n'est attribué à une section précise.
6. **Une passe de réécriture complète lisse le texte.** L'appel « Passe de contrôle qualité finale » (orch:1498-1515), à température 0,3 sur un modèle bon marché, réécrit l'article entier sans critères mesurables. Il tend à aplatir les éléments spécifiques.
7. **Les juges ne notent pas votre grille et ne bouclent pas.**
   - Le score global (scoring_service.py:152-170) additionne une checklist SEO, un EEAT de surface (liens et titres), la lisibilité, une originalité calculée contre des snippets, la « présence humaine » et `value_added`.
   - `value_added` donne des points parce que des artefacts existent, pas parce que le texte les utilise : +15 si des `evidence_items` existent, +10 si des gaps sont trouvés (scoring_service.py:36-75). C'est nuisible : cela donne une fausse assurance.
   - Aucun critère ne mesure l'adéquation à l'intention, l'exactitude, la traçabilité ou le gain d'information.
   - Le juge LLM n'a ni brief, ni sources, ni benchmark (AS:543-560) et tourne après le score.
   - Le fact-check juge de mémoire, sans sources (AS:51-61), et n'est pas bloquant.
   - Supprimer les boucles de réécriture était juste, car elles optimisaient la surface. Mais rien ne les a remplacées par une révision ciblée sur des critères qui échouent.
8. **Les informations de l'idée se perdent avant la rédaction.** `idea_prebrief` (angle, format, réponse attendue, questions) est écrit puis jamais relu (idea_engine.py:478-496).
9. **La matière humaine est bruitée.** Elle vient de Stack Overflow, Nitter ou d'un scraping de Google PAA sujet aux captchas (human_insights_service.py:481), et elle est classée par mots-clés (l.172-188). Elle arrive au rédacteur avec la mention « si utile » (orch:1283), et le garde-fou se contente d'un log (orch:1206-1213).
10. **Le modèle a un plafond.**
    - Tout tourne sur `deepseek-v4-flash:free` (config.py:31), y compris le juge. Un modèle qui note un texte du même modèle est indulgent.
    - Le repli `openrouter/free` (config.py:35) peut basculer en silence sur un modèle aléatoire.
    - Le levier existe déjà : `AGENT_<ID>_MODEL` (agent_router.py:186). Avec environ 0,01 $ par article, passer 3 ou 4 appels clés sur un modèle intermédiaire est indolore.
11. **Les métas et la FAQ sont aveugles.** Les métas sont écrites à partir du titre et du mot-clé seulement (orch:1618-1644). La FAQ ne voit que les 1 500 premiers caractères (orch:1799) et ignore les PAA renvoyés par Serper.
12. **Rien ne gère la fraîcheur.** Aucun fait n'est daté, aucune mention « mis à jour le » n'est produite, aucune volatilité n'est estimée à la génération. `monitoring_agent` calcule une volatilité après publication (monitoring_agent.py:154-236), sans lien avec les sources.

---

## 4. Chaîne éditoriale v2

Principes :
- chaque agent a un contrat d'entrée et de sortie typé (JSON) ;
- chaque fait porte un identifiant de fait (`fact_id`) et une URL source ;
- le juge note **votre grille** contre le brief, le benchmark et un registre central des faits (`fact_ledger`) ;
- la révision ne touche que les sections et les critères qui échouent.

### 4.1 Agents

Hypothèse de taille : un article de 6 sections. Prix flash : 0,09 $/M tokens en entrée, 0,18 $/M en sortie.

| Agent v2 | Rôle et contrat | Garder / fusionner / supprimer | Modèle | Appels | Tokens entrée / sortie | Coût flash |
|---|---|---|---|---|---|---|
| A0 IdeaHandoff | relit `idea_prebrief` et les paramètres utilisateur, puis produit `brief_input` | nouveau, déterministe | — | 0 | — | 0 |
| A1 SERP Scout | Serper (organic, **peopleAlsoAsk, relatedSearches, answerBox**), 1 à 3 requêtes ; produit `serp` | étend `serp_adapter` | — | 0 LLM | — | environ 0,001 $ de Serper |
| A2 Research Reader | lit en entier le top 5 concurrent et 3 à 5 sources primaires (page tarifs officielle, .gouv, documentation) avec trafilatura (`content_extraction_adapter.extract`, déjà là), téléchargement unique mis en cache. Une extraction LLM par page : `{outline, components_present, facts[{claim, quote_verbatim, figure, date, url}], angles, weaknesses, user_pains}` ; produit `source_pages[]`, `fact_ledger[]` (tier, date, confiance) | remplace ResearchBrief, SourceQuality, EvidencePack, HumanInsights (réduit à PAA + forums de la SERP), KeywordResearch (les entités viennent des pages) | bon marché | 8 | 56k / 8k | 0,0065 $ |
| A3 Competitive Benchmark | matrice sous-thème × concurrent, consensus (≥ 3/5 = à couvrir), gaps (≤ 1/5), composants concurrents (tableaux, simulateurs), faiblesses ; produit `benchmark` | remplace ContentGap et `competitor_angles` | bon marché ou intermédiaire | 1 | 12k / 2,5k | 0,0015 $ |
| A4 Strategist | type de contenu (7 gabarits), angle, **plan de gain d'information** (≥ 3 apports absents du top 5, chacun relié à des `fact_id` ou à une note d'expert), `must_cover` = consensus, `must_avoid`, budget de mots ; produit `strategy`. Champ optionnel « notes de l'expert » (5 minutes de votre part : prix réels, anecdotes) | fusionne IntentRefine, EditorialAngle, StyleAdaptation et ProductionBrief | **intermédiaire** | 1 | 10k / 2k | 0,0013 $ |
| A5 Outline Architect | plan dicté par le gabarit : par section, `purpose`, **composant obligatoire**, `fact_ids` assignés, apport de gain assigné, nombre de mots ; produit `outline_v2` | garde `article_outline_planner` en le refondant | **intermédiaire** | 1 | 8k / 2k | 0,0011 $ |
| A6 Section Writer | une section par appel, avec **seulement ses faits** (texte + id + URL) et la spécification du composant (schéma du tableau…). Marque chaque affirmation `[F12]` ; produit le HTML | garde SectionWriter ; supprime la réécriture QualityGate complète | bon marché (ou intermédiaire en test A/B) | 8 | 40k / 6,4k | 0,0048 $ |
| A7 Fact Verifier | déterministe : tout nombre ou date du texte doit apparaître dans la citation du fait qu'il référence, et toute phrase factuelle doit porter un `fact_id`. Puis un LLM vérifie que chaque affirmation découle bien de sa citation. Une affirmation sans `fact_id` ou non soutenue est un **blocage** ; produit `verification` | remplace ClaimExtraction et FactCheck | bon marché + code | 1-2 | 15k / 2k | 0,0017 $ |
| A8 QA Judge | **grille de 100 points** (§4.3), avec en entrée brief, benchmark, registre de faits, vérification et article. Sortie par critère : score, preuves, sections fautives, consigne de correction, blocages | remplace `run_quality_gate`, `article_reviewer`, `value_added` et le score global de validation ; les heuristiques (EEAT, GEO, lisibilité, humanisation, présence humaine) passent dans un panneau « lint » | **intermédiaire, d'une autre famille que le rédacteur** | 1 | 16k / 2k | 0,0018 $ |
| A9 Targeted Revision | seulement les sections fautives et les critères < seuil, **2 itérations au maximum**, puis A7 et A8 relancés sur les critères concernés | nouveau | identique à A6 | ≤ 2 × (3 + 1) | 62k / 8,8k | 0,0072 $ |
| A10 Polish | relecture, cohérence, citations ; les citations sont posées à partir des marqueurs `[F12]` vers l'URL du registre | **garder** (bien conçus) | bon marché | 10 | 28k / 6,6k | 0,0037 $ |
| A11 SEO Packager | métas à partir du brief et de l'introduction ; FAQ à partir des PAA non couverts ; schéma Article + FAQ + HowTo ou ItemList selon le gabarit ; liens internes ; checklist SEO | fusionne `meta_writer`, `faq_generator`, StructuredData et SEOFinalChecklist | bon marché | 1 | 6k / 1k | 0,0007 $ |
| A12 Freshness | `facts_as_of`, « Mis à jour le », volatilité par gabarit (prix = élevée), date de revérification des faits volatils, branchée sur `monitoring_agent` | nouveau + réutilisation | — | 0 | — | 0 |

**À supprimer :**
- CalloutPlan et FAQPlan (morts) ;
- le doublon de cannibalisation (orch:552) ;
- KeywordBrief et IntentAnalysis heuristiques (gardés seulement comme repli) ;
- `value_added` ;
- WritingPass_QualityGate ;
- les fonctions mortes de AS (`seo_optimize_content`, `editorial_review`, `quality_rate_article`, `check_reader_retention`, `improve_engagement`) ;
- le second `seo_review`.

Les 19 alias hérités restent seulement dans une table de correspondance.

**Coût estimé :** environ 33 appels, 260k tokens en entrée et 41k en sortie, soit **0,025 à 0,031 $ par article** tout en flash, révisions comprises. Si A4, A5, A6 et A8 passent sur un modèle intermédiaire, avec une hypothèse illustrative de 1 $/M en entrée et 4 $/M en sortie (à vérifier sur OpenRouter), le total monte à environ 0,15 à 0,20 $ par article.

### 4.2 Gabarits par type de contenu

Le gabarit est imposé au plan (A5), vérifié par du code (structure/UX) et noté par le juge.

| Type | Composants obligatoires | Contrôles spécifiques du juge |
|---|---|---|
| Comparatif | tableau critères × options (≥ 5 critères, sources datées), verdict par profil, « quand ne PAS choisir X », méthodologie | chaque cellule du tableau est sourcée ; le verdict est cohérent avec le tableau |
| Guide prix / budget | fourchettes datées avec leur source, facteurs de coût, **exemple chiffré complet** (calcul), coûts cachés, tableau par scénario | toutes les fourchettes ont une date et une source ; le calcul est juste |
| Guide pratique / how-to | prérequis, étapes numérotées avec résultat attendu, erreurs fréquentes, checklist finale | les étapes sont exécutables ; aucune étape vague |
| Définition / explainer | définition en 2 phrases, mécanisme, exemple concret, confusions courantes, « à retenir » | justesse de la définition, présence d'un exemple |
| Tutoriel | environnement et versions, code ou captures, vérification à chaque étape, dépannage | versions datées ; les étapes peuvent être testées |
| Liste / sélection | critères de sélection explicites, fiche par élément (pour qui, limite, prix daté), tableau récapitulatif | les critères sont appliqués de façon homogène |
| Question simple | réponse dans les 50 premiers mots, nuances, un ou deux cas particuliers, 400 à 900 mots | pas de remplissage |

### 4.3 Grille du juge et blocages

| Critère | Points | Mesure |
|---|---|---|
| Adéquation à l'intention | 15 | le juge compare au `reader_real_question` et à la réponse attendue ; la réponse doit être dans les 100 premiers mots |
| Exactitude factuelle | 20 | résultat de A7 + juge |
| Fiabilité et traçabilité des sources | 15 | part des affirmations portant un `fact_id` de tier fort ou primaire |
| Originalité / gain d'information | 15 | apports du plan de gain réellement présents et absents du benchmark |
| Profondeur / couverture | 10 | part des sous-thèmes de consensus couverts (matrice A3) |
| Clarté | 10 | juge + lint |
| Structure / UX | 5 | présence des composants du gabarit (contrôle déterministe) |
| SEO | 5 | `seo_final_checklist` |
| Fraîcheur | 5 | dates présentes, pas d'année périmée |

**Blocages** (rejet immédiat) :
- fait ou source inventés ;
- chiffre sans `fact_id` ;
- composant obligatoire absent ;
- intention manquée ;
- contradiction interne.

Un article est publiable avec un score **≥ 90 et aucun blocage**. Cette règle remplace le blocage sur score incomplet de `validation_service.py:216-224`.

---

## 5. Plan d'implémentation

Chaque étape se teste sur le même jeu de référence : 3 mots-clés réels (un comparatif, un guide prix, un how-to). On compare les artefacts et le score manuel sur votre grille avant et après.

1. **Mesurer le point de départ.** Écrire un script qui exporte les artefacts d'un article et le coût réel (`_get_article_cost_data`). Noter les 3 articles à la main sur la grille.
2. **Brancher `idea_prebrief`.** L'orchestrateur le lit et l'injecte : angle, format, `main_answer_summary`, `search_questions`. *Test :* le `production_brief` contient l'angle de l'idée.
3. **Correctif rapide côté rédacteur.** `build_section_brief` reçoit les sous-questions, les mots-clés secondaires et les URL des faits. Chaque section reçoit les faits filtrés par `usage_hint`. *Test :* les faits ne se répètent plus d'une section à l'autre.
4. **Exploiter toute la réponse Serper.** Conserver `peopleAlsoAsk`, `relatedSearches` et `answerBox` (serp_adapter.py:82). *Test :* la FAQ s'appuie sur les vraies PAA.
5. **Lecture des pages complètes avec cache unique.** Utiliser trafilatura. Les téléchargements de recherche, de qualité des sources et de liens externes partagent un seul cache. *Test :* 5 textes de plus de 800 mots dans l'artefact, nombre de téléchargements divisé par 3.
6. **Construire `fact_ledger` (A2).** Il remplace EvidencePack. *Test :* au moins 20 faits avec citation exacte et date pour le guide prix.
7. **Benchmark A3 et affichage de la matrice dans l'interface.** *Test :* la matrice du comparatif est lisible et ses gaps sont justes à la relecture humaine.
8. **Strategist A4.** Il fusionne intention, angle et style, ajoute le plan de gain et le champ « notes de l'expert ». *Test :* au moins 3 apports absents du top 5.
9. **Gabarits.** Commencer par guide prix et comparatif : registre des composants, plan A5, spécification de composant pour A6. *Test :* présence vérifiée par code du tableau et de l'exemple chiffré.
10. **Marqueurs `[F12]` et Fact Verifier A7.** Le code contrôle que les nombres du texte sont inclus dans les citations du registre. CitationPass est piloté par les marqueurs. *Test :* un faux chiffre injecté à la main est bloqué.
11. **QA Judge A8 sur 100 points avec blocages.** Il remplace la règle de validation. *Test :* écart de ±5 points au maximum avec votre note manuelle sur les 3 articles.
12. **Révision ciblée A9.** Au maximum 2 itérations, uniquement sur les sections fautives. *Test :* le score monte sur le critère visé sans baisse ailleurs.
13. **Faire le ménage.** Supprimer WritingPass_QualityGate, ClaimExtraction et FactCheck (anciens), `run_quality_gate`, `value_added`, CalloutPlan et FAQPlan, la double cannibalisation, les fonctions mortes de AS. Nettoyer le registre. *Test :* tous les tests verts, coût et durée en baisse.
14. **Hiérarchie de modèles.** Passer A4, A5 et A8 (puis A6) sur un modèle intermédiaire via `AGENT_<ID>_MODEL`. Désactiver le repli `openrouter/free` pour le juge. *Test :* même article, comparaison flash contre intermédiaire.
15. **SEO Packager A11 et Freshness A12.** *Test :* schéma HowTo ou ItemList valide ; mention « Mis à jour le » ; date de revérification posée sur les faits de prix.
16. **Gabarits restants.** Définition, tutoriel, liste, question simple.

Les étapes 2 à 4 se font en moins d'une journée et corrigent déjà les liens cassés. Les étapes 5 à 11 sont celles qui font passer un article de « propre » à « premium ».
