# RAPPORT D'AMÉLIORATIONS IDEAS STUDIO

> Pipeline de génération SEO — révision du 2026-08-05.
> 24 corrections implémentées sur les 25 prévues (FIX 25 « topic selector perf » exclu volontairement).

---

## Résumé exécutif

Le pipeline de génération SEO d'Ideas Studio souffrait de **quatre fragilités structurelles** :

1. **Recherche trop superficielle** — le brief de recherche se limitait à 5 sources, les insights humains tombaient en échec sans repli, et aucune analyse des manques de contenu n'existait.
2. **Rédaction à passe unique** — le writer recevait un brief éclaté en dizaines de blocs de contexte et rédigeait en une seule passe, sans vérification que la matière humaine était réellement utilisée.
3. **Notation dispersée et contradictoire** — cinq juges LLM séparés (revue éditoriale, rétention, engagement, SEO, qualité) évaluaient le même texte sans consensus, avec des seuils incohérents.
4. **Métriques et liens fragiles** — images insérées sans correspondance de section, liens externes non nettoyés, rapport de génération avec des métriques invalides, pas de suivi de volatilité.

### Changements clés

- **Brief consolidé** : nouveau service `production_brief_service` qui verrouille un brief de production unique et ordonné pour le writer (priorités, faits validés, insights humains, plan).
- **Rédaction en 3 passes** : Foundation (temp 0.7) → Style (temp 0.5) → QualityGate (temp 0.3), avec règle absolue anti-tiret cadratin.
- **Juge qualité unique** : `run_quality_gate` remplace 5 appels LLM séparés par une seule décision avec grade A-D.
- **Analyse des manques** : nouvel agent `gap_identifier` (heuristique) détecte questions, douleurs et angles non couverts par les articles existants du projet.
- **Repli systématique** : insights humains « lite » en secours, guide de style à 3 templates en secours, planneur d'outline `llm|heuristic` configurable.
- **Volatilité** : le monitoring calcule un score de volatilité (30/60/90 jours) pour planifier la re-revue.

---

## Détail par fix

### FIX 1 — Brief de recherche : 12 sources au lieu de 5
`app/services/seo/research_brief_service.py`
- `limit=5` → `limit=12` (l.29) ; message de limitation mis à jour en « 12 URLs max ».
- `serp_adapter.search` gère déjà `limit=12` sans cap interne (SerpAPI `num=12`, Brave `min(12,20)`, Google `min(12,10)`).

### FIX 2 — Evidence pack : qualité de chaque source
`app/services/agents/agent_services.py`
- Helpers `_format_source_for_evidence` + `_quality_for_url`.
- Le prompt `evidence_pack_builder` embarque désormais la qualité par source (`validate_sources` → `quality_check.quality`, skippé → `unknown`).
- Schéma de sortie étendu avec `source_quality` ; backfill post-traitement si l'LLM ne le fournit pas ; sources limitées à 12.

### FIX 3 — Content Gap : manques de contenu par rapport au projet
**Nouveau fichier** `app/services/seo/content_gap_service.py`
- `identify_content_gaps()` / `identify_content_gaps_dict()` — 7 types de gaps : question, pain_point, objection, debate, vocabulary, competitor_angle, field_signal.
- Filtrage par chevauchement lexical (seuil 0.6) et couverture existante (outlines + titres via `get_latest_artifacts_bulk`).
- Statuts `gaps_found | no_gaps | saturated`, priorités high/medium/low, suggestions actionnables.
- Agent `gap_identifier` déclaré dans `agent_registry.py` (heuristique, `implementation_ref="content_gap_service"`).
- Câblé en **phase 6d** de l'orchestrateur avec `exclude_article_id=existing_article_id` ; artifact `content_gaps` persisté.

### FIX 4 — Vérification que les insights humains sont utilisés
`app/services/seo/seo_generation_orchestrator.py`
- Nouvelle méthode `_verify_human_insights_usage(content)` appelée en **étape 15b** (après l'écriture).
- Non bloquant : vérifie la présence d'une URL de source ou d'un fragment de questions/douleurs ; sinon warning + `limitations.append("human_insights_ignored: ...")` ; sinon tool `human_insights_usage`.

### FIX 5 — Insights humains « lite » en repli
**Nouveau fichier** `app/services/human_insights_lite_service.py`
- `extract_human_insights_lite()` — Autocomplete Google + People Also Ask + forums SERP, même format de sortie avec `"lite": True`.
- Réutilise les helpers privés de `human_insights_service` (`_extract_google_autocomplete`, `_extract_people_also_ask`, `_extract_forums_from_serp`, `_classify`).
- Câblé en **6c** : repli si l'extracteur complet renvoie 0 insight ou lève une exception.

### FIX 6 — Mode de plan d'outline `llm|heuristic`
`app/core/config.py` + `app/services/seo/article_outline_planner.py`
- Nouvelle variable `OUTLINE_PLANNER_MODE: str = "llm"` avec `field_validator` restreignant à `llm|heuristic` ; documentée dans `.env.example`.
- `build_outline()` délègue selon le mode : `_build_outline_with_llm()` (provider `outline_planner`, normalisation des sections, repli `None`) ou `_build_outline_heuristic()` (ancienne logique conservée).
- Orchestrateur (étape 9) : `outline_planner_mode=app_settings.OUTLINE_PLANNER_MODE`, step « ArticleOutline (llm|heuristic) ».

### FIX 7 — Analyse d'intention multidimensionnelle
`app/schemas/seo_workflow.py` + `app/services/seo/intent_analysis_service.py`
- `IntentAnalysis` : + `intent_scores: dict` et `commercial_intent_score: float`.
- Scoring 4 dimensions (informational / commercial / transactional / navigational), dominant ≥ 0.25 pilote `explicit_intent`.
- Mapping `article_type` : comparison, transactional, navigational, guide, simple_question, evergreen.
- Testé : « meilleure assurance auto » → commercial/comparison ; « comment configurer vpn » → informational/guide.

### FIX 8 — Rédaction en 3 passes
`app/services/seo/seo_generation_orchestrator.py`
- Helper `_write_pass(prompt, agent_id, article, temperature, step)` (via `call_agent` si router, sinon provider ; lève `GenerationFailedError` si mock/vide).
- `_generate_content` : **Pass 1 Foundation temp 0.7** (brief complet) → **Pass 2 Style temp 0.5** (style, transitions, règle absolue : pas de tiret cadratin —) → **Pass 3 QualityGate temp 0.3** (redondances, densité mot-clé ≤ 2%, pas de —).
- `apply_structure_guards` après les passes ; `_raise_if_cancelled(article)` entre chaque passe.

### FIX 9 — Juge qualité unique
`app/schemas/seo_workflow.py` + `app/services/seo/editorial_quality_gate.py` + `app/services/agents/agent_services.py`
- `EditorialQualityReport.quality_grade: str` ajouté ; `editorial_quality_gate` calcule un grade déterministe (A ≥ 90, B ≥ 75, C ≥ 55, D sinon) + `manual_review_needed`.
- `run_quality_gate()` : **un seul appel LLM** → `quality_grade` A/B/C/D, `decision` pass|minor_fixes|rewrite, score, blocking_issues ; mock → skipped/unknown.
- Orchestrateur : les 5 passes séparées (EditorialReview, ReaderRetention, Engagement, SEOOptimizer, QualityRating) remplacées par un appel unique fusionné dans `editorial_quality_report` (`llm_review` + `quality_grade`).
- Les fonctions `seo_optimize_content`, `editorial_review`, `check_reader_retention`, `improve_engagement`, `quality_rate_article` existent toujours mais ne sont plus appelées par l'orchestrateur.

### FIX 10 — Brief de production consolidé
**Nouveau fichier** `app/services/production_brief_service.py`
- `build_production_brief()` : consolide project_context + intent_analysis + keyword_brief + research_brief + evidence_pack + editorial_angle + outline + human_insights + content_gaps + volume cible + style en un brief ordonné avec **priorités absolues** (question du lecteur, promesse éditoriale, gaps à couvrir, faits validés).
- `production_brief_to_text()` : sérialisation lisible injectable dans le prompt du writer.
- Agent `production_brief_builder` re-pointé vers `production_brief_service` (`requires_llm=False`).
- Câblé en **14c** de l'orchestrateur (avant la rédaction) ; brief injecté en tête du prompt du writer ; artifact `production_brief` persisté.

### FIX 11 — Humanization : 10 tests universels
`app/services/seo/humanization_service.py`
- Réécrit pour réutiliser les listes de signaux de `human_presence_service` (GENERIC_OPENERS, WORTHLESS_FILLER_PHRASES, EMPTY_SUPERLATIVES, WORN_EXPRESSIONS, HUMAN_MARKERS, CONCLUSION_STARTERS) — cohérence entre les deux services.
- 10 tests : ouverture générique (intro + début de section), remplissage, superlatifs vides, expressions usées, transitions en excès, absence de phrase courte de rythme, absence de marqueur humain, conclusion générique, tiret cadratin, répétition des premiers mots de paragraphe.

### FIX 12 — Scoring : valeur ajoutée 10%
`app/services/scoring_service.py`
- `compute_value_added_score(artifacts)` : mesure si l'article dépasse la paraphrase (sources validées citées, matière humaine intégrée, angle différenciant, liens externes contextuels, gaps couverts).
- Poids v2.3 : SEO ×27% · EEAT ×18% · Lisibilité ×15% · Originalité ×16% · Présence humaine ×14% · Valeur ajoutée ×10%.
- `value_added_contrib` + `value_added_flags` dans la sortie ; artifacts lus : `production_brief`, `human_insights`, `editorial_angle`, `external_links`, `content_gaps`.

### FIX 13 — Originalité : seuil de 500 mots
`app/services/seo/originality_service.py`
- Un contenu de moins de 500 mots retourne `status=unverified` avec flag `insufficient_content` (au lieu du seul check de 50 caractères) — pas de fausse assurance sur un texte trop court.

### FIX 14 — Cannibalisation par sections : Jaccard + cosinus
`app/services/seo/cannibalization_service.py`
- `_similarity` réécrite : **Jaccard réel** (intersection/union, pondéré par fréquence) + **cosinus** des fréquences de mots.
- Une paire H2 est retenue si Jaccard ≥ 0.4 **ET** cosinus ≥ 0.5 — réduit les faux positifs des titres courts partageant un mot banal.
- Sortie enrichie : `{proposed, existing, jaccard, cosine}`.

### FIX 15 — Qualité de langue : seuil 35 mots + répétitions + voix passive
`app/services/seo/language_quality_service.py`
- Seuil de longueur de phrase abaissé de 40 → **35 mots**.
- Nouveaux détecteurs : répétition d'une séquence de phrases (≥ 2 occurrences de 3 phrases consécutives normalisées ≥ 20 chars), voix passive fréquente (≥ 3 occurrences sur ≥ 10 phrases).

### FIX 16 — Guide de style : 3 templates + auto-détection
`app/services/agents/agent_services.py`
- `STYLE_GUIDE_TEMPLATES` : 3 templates complets (accessible & conversationnel, professionnel & informationnel, technique & expert), chacun avec 6 règles actionnables.
- `_detect_style_template()` : auto-détection du template le plus proche du style de base du projet (mots-clés par template).
- `build_style_guide_fallback()` : repli 100% déterministe injecté dans le prompt du writer.
- `adapt_editorial_style()` enrichie : le guide de style (template + règles) accompagne la réponse LLM ou sert de repli en cas de provider indisponible.

### FIX 17 — Éditeur d'engagement : réécriture par section
`app/services/agents/agent_services.py`
- `improve_engagement()` : réécrit chaque section (H2 + contenu) individuellement avec meilleure accroche, transitions et fin de section — plus une simple liste de suggestions.
- Chaque réécriture doit conserver le sens, les faits et les balises HTML ; validée (présence de `<h2`, longueur ≥ 30% de l'original) sinon la section d'origine est conservée.
- Reconstruit le contenu en ne remplaçant que les sections validées ; `rewritten_sections` + `rewritten_count` en sortie.

### FIX 18 — Seuils de révision 75/70
`app/services/seo/article_reviewer_service.py`
- Décisions : APPROUVE ≥ **75**, REVISION_AUTOMATIQUE ≥ **70**, sinon REECRITURE (au lieu de 80/65).

### FIX 19 — Volatilité 30/60/90 jours
`app/services/monitoring_agent.py`
- `_compute_volatility(db, article)` : score 0-100 sans colonne DB (difficulté du mot-clé principal, volume de recherche, variance de trafic Search Console, ancienneté).
- Niveaux : high ≥ 60 → re-revue à **30 jours** ; medium ≥ 30 → **60 jours** ; low → **90 jours**.
- `next_review_at` calculé dynamiquement au lieu du fixe 90 jours ; artifact `volatility_assessment` persisté.

### FIX 20 — Liens externes nettoyés
`app/services/seo/external_link_service.py`
- `_clean_url()` : normalise schéma/domaine (minuscules), supprime fragments et params de tracking (utm_, fbclid, gclid), rejette les URLs invalides et les domaines placeholders.
- `_clean_anchor()` : supprime les balises HTML, les espaces multiples, tronque à 80 caractères, remplace les ancres-URL par « Source ».
- Déduplication par URL propre avant insertion.

### FIX 21 — Plan d'images par section
`app/services/seo/image_plan_service.py`
- Chaque image sourcée porte désormais `section_heading` (section H2 planifiée).
- `insert_images_in_content()` : appariement image → section par titre de section (normalisé, tolérant aux `?`/casse) ; images sans correspondance réparties après les sections sans image.

### FIX 22 — Volumétrie : article_tier + section_tier
**Nouveau fichier** `app/services/seo/article_tier_service.py`
- `compute_volume_tiers(content)` : `article_tier` (micro/short/medium/long/pillar selon le volume réel) + `section_tier` par H2 (brief < 150 mots, standard ≥ 150, deep ≥ 400).
- Flags : `section_creuse:<titre>` (section < 100 mots), `pas_de_h2_detecte`.
- Câblé dans l'orchestrateur après la révision ; artifact `volume_tiers` persisté.

### FIX 23 — Contexte des liens internes
`app/services/seo/internal_link_service.py`
- Chaque lien interne embarque `context` : `target_keyword`, `target_excerpt` (extrait réel de l'article cible) et `context_note` expliquant la pertinence.
- Utilisable par le writer pour choisir une ancre et un emplacement cohérents.

### FIX 24 — Angles et exemples déjà utilisés
`app/services/seo/project_context_service.py` + `app/schemas/seo_workflow.py`
- `ProjectContext` : + `used_angles` et `used_examples`.
- `build_project_context()` : collecte les angles/différenciations (artifact `editorial_angle`) et exemples réels (artifact `human_insights`) des articles publiés + brouillons.
- Prompt du writer : blocs « Angles éditoriaux déjà utilisés (À ÉVITER) » et « Exemples déjà exploités (À NE PAS RÉPÉTER) ».

### FIX 26 — Métriques invalides dans le rapport
`app/services/seo/generation_report_service.py` + `app/schemas/seo_workflow.py`
- `reading_time_minutes` toujours **dérivé du word_count réel** (jamais pris tel quel de l'appelant) ; `None` quand l'article est vide (0 mot).
- `GenerationReport.reading_time_minutes` : `int | None`.
- L'orchestrateur ne force plus `or 1`.

---

## Nouveaux fichiers

| Fichier | Fix | Rôle |
|---|---|---|
| `app/services/seo/content_gap_service.py` | FIX 3 | Détection des manques de contenu vs articles existants |
| `app/services/human_insights_lite_service.py` | FIX 5 | Insights humains en repli (Autocomplete + PAA + forums) |
| `app/services/production_brief_service.py` | FIX 10 | Brief de production consolidé pour le writer |
| `app/services/seo/article_tier_service.py` | FIX 22 | Volumétrie article + par section |

## Fichiers modifiés

- `app/services/seo/research_brief_service.py` (FIX 1)
- `app/services/agents/agent_services.py` (FIX 2, 9, 16, 17)
- `app/services/seo/seo_generation_orchestrator.py` (FIX 3, 4, 5, 8, 9, 10, 12, 22, 24, 26)
- `app/services/agents/agent_registry.py` (FIX 3, 10)
- `app/core/config.py` + `.env.example` (FIX 6)
- `app/services/seo/article_outline_planner.py` (FIX 6)
- `app/services/seo/intent_analysis_service.py` (FIX 7)
- `app/schemas/seo_workflow.py` (FIX 7, 9, 24, 26)
- `app/services/seo/editorial_quality_gate.py` (FIX 9)
- `app/services/seo/humanization_service.py` (FIX 11)
- `app/services/scoring_service.py` (FIX 12)
- `app/services/seo/originality_service.py` (FIX 13)
- `app/services/seo/cannibalization_service.py` (FIX 14)
- `app/services/seo/language_quality_service.py` (FIX 15)
- `app/services/seo/article_reviewer_service.py` (FIX 18)
- `app/services/monitoring_agent.py` (FIX 19)
- `app/services/seo/external_link_service.py` (FIX 20)
- `app/services/seo/image_plan_service.py` (FIX 21)
- `app/services/seo/internal_link_service.py` (FIX 23)
- `app/services/seo/project_context_service.py` (FIX 24)
- `app/services/seo/generation_report_service.py` (FIX 26)

---

## Dépendances

- **Aucune nouvelle dépendance externe.** Toutes les heuristiques sont calculées avec la stdlib (re, math, collections, urllib) + SQLAlchemy existant.
- La réécriture de `humanization_service` réutilise `human_presence_service` (mêmes listes de signaux — aucun décalage entre les deux rapports).
- Le brief de production, le guide de style et les insights lite sont des **replis déterministes** : ils fonctionnent sans aucun provider LLM.

## Configuration requise

| Variable | Valeur | Effet |
|---|---|---|
| `OUTLINE_PLANNER_MODE` | `llm` (défaut) ou `heuristic` | Mode du planneur d'outline — `llm` avec repli heuristique automatique |

Aucune autre variable n'est requise : les nouveaux services (content gap, tiers, volatilité, valeur ajoutée) sont 100% heuristiques.

## Tests recommandés

Aucun test unitaire service n'existe pour ces chemins (uniquement `tests/e2e` et `test_reference_sync.py`) — vérifications manuelles à prévoir :

1. **Production brief** : générer un article et contrôler l'artifact `production_brief` (sections, priorités, faits validés).
2. **Content gap** : générer un 2e article sur un même sujet → `content_gaps` doit lister les questions non couvertes.
3. **Outline modes** : `OUTLINE_PLANNER_MODE=heuristic` vs `llm` → les deux produisent un plan.
4. **Insights lite** : désactiver l'extracteur complet → le repli `human_insights_lite` prend le relais.
5. **QualityGate** : vérifier `editorial_quality_report.quality_grade` (A-D) et un seul appel LLM dans les logs.
6. **Volatilité** : `_compute_volatility` → `review_delay_days` ∈ {30, 60, 90}.
7. **Images par section** : vérifier que chaque image insérée correspond à sa section H2 planifiée.
8. **Liens externes** : vérifier l'absence de params `utm_` et de domaines placeholders.
9. **Rapport** : `reading_time_minutes` dérivé du word_count ; `None` pour un article vide.
10. **E2E** : `cd tests/e2e && npm test` pour valider les parcours critiques.

## Risques

- **Coût LLM du juge unique** : `run_quality_gate` réduit le nombre d'appels par rapport aux 5 juges précédents (amélioration) mais reste un appel LLM bloquant sur le contenu complet — coût proportionnel à la longueur de l'article.
- **FIX 14 (Jaccard + cosinus)** : seuil plus strict (0.4) que l'ancien « 0.6 sur intersection/court » — le risque est de **sous-détecter** des chevauchements de sections ; à surveiller en production (faux négatifs préférés aux faux positifs).
- **FIX 13 (500 mots)** : un article volontairement court (< 500 mots) sera toujours marqué `unverified` en originalité — comportement voulu, mais `scoring_service` bloque le score global dans ce cas (règle déjà existante).
- **FIX 19 (volatilité)** : le score dépend de la difficulté/volume du mot-clé principal ; sans mot-clé associé, il repose sur la variance de trafic et l'ancienneté (repli « low » à 90 jours).
- **FIX 22 (tiers)** : sans colonne DB, les tiers sont recalculés à chaque génération à partir du contenu — aucune persistance historique, c'est un instantané.
- **Régressions de prompts** : les réécritures de prompts (writer 3 passes, style guide, quality gate) changent la sortie observée — valider par des articles de référence avant mise en prod.

## Périmètre exclu

- **FIX 25 (topic selector performance)** : exclu volontairement.
- **Callout résumé d'introduction** : instruction retirée du prompt du writer (le callout bloquait le rendu TipTap) — non implémenté.
- **Migration DB** : les FIX 19 et 22 fonctionnent **sans colonne dédiée** (`volatility_score`, `article_tier`). Une migration Alembic serait nécessaire uniquement pour une persistance historique ou un filtrage en base.
