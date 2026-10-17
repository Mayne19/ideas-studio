# Refonte Ideas Studio : plateforme simplifiée autour du skill de rédaction

Validé par Mayne le 17 octobre 2026. Ce document est la référence de la refonte. Toute décision qui s'en écarte doit être validée par Mayne.

## Principe

La qualité des articles vient désormais du skill `.claude/skills/redaction-article/SKILL.md`. La plateforme ne fait plus de rédaction, d'analyse ni de notation. Elle fait cinq choses simples :

1. gérer les idées de sujets ;
2. lancer la rédaction avec le skill ;
3. faire relire et valider les articles par un humain ;
4. publier automatiquement selon un calendrier ;
5. rappeler les mises à jour.

L'utilisateur ne règle aucun paramètre technique. Tout ce qui peut être décidé par le système l'est par défaut.

## Le skill est gelé

- La version actuelle du skill est la version de référence (tag git `skill-v1`).
- Personne ne modifie le skill sans validation de Claude (chat) et de Mayne.
- Après toute modification, on régénère les deux articles de référence (« Comment enlever une tache de gras sur un vêtement » et « Comment contester un forfait post-stationnement ») et on compare. Si la qualité baisse, la modification est annulée.

## Le parcours dans l'application (un écran Production)

La sidebar conserve les espaces principaux : Tableau de bord, Articles avec le
Kanban, Catégories, Calendrier éditorial, Analytics, Médias, Optimisations,
Notifications et Production. Les réglages gardent Providers pour les clés API
et Services externes pour les connexions de recherche et d'images.

### Production — Idées

- Le bouton « Générer les idées du mois » produit le nombre d'idées prévu par
  les catégories et le pipeline.
- Les idées sont groupées par catégorie et affichent seulement le titre, le
  mot-clé et une alerte de cannibalisation éventuelle.
- Chaque idée peut être acceptée, rejetée et supprimée, ou renommée. Les
  actions « Tout accepter » et « Accepter la sélection » envoient les sujets
  acceptés dans la file de rédaction.

### Production — Rédaction

- Un résumé indique le nombre d'articles rédigés par jour, les jours de
  rédaction et la date prévisionnelle de fin de file.
- La file affiche les états « en attente », « en cours », « terminé » et
  « erreur », avec la date prévue et un bouton « Relancer » pour une erreur.
- Le coût par article et le total du mois sont affichés de façon discrète.
  Les agents, fournisseurs, jetons et journaux ne sont pas affichés.
- La route du rédacteur local ne renvoie aucun sujet lorsque le plafond du jour
  est atteint ou lorsque le jour courant n'est pas un jour de rédaction.

### Production — Validation

- La liste affiche le titre, la catégorie, le score global sur 100, les trois
  contrôles techniques, ainsi que les alertes de plagiat et de doublon.
- Un clic ouvre l'article dans l'éditeur existant et sa fiche dans le panneau
  latéral : métadonnées SEO, slug, sources, images et légendes, intégrations,
  expériences à ajouter et informations à mettre à jour.
- Le bouton « Valider tous les articles au-dessus du seuil » utilise
  `min_publish_score`, et la validation de la sélection reste disponible.
  La validation programme automatiquement l'article dans le calendrier selon
  les dates et heures configurées.
- Le score repose sur six contrôles déterministes : encadré « En résumé » (15),
  absence de tiret cadratin (10), fiche valide (15), trois sources liées dont
  une primaire ou officielle (20), absence d'alerte de plagiat (20) et
  structure respectée (20). L'encadré, le tiret et la fiche sont bloquants,
  quel que soit le score.
- Les sous-scores SEO, GEO, originalité et humanisation ne sont pas affichés.

### Production — Mises à jour

- La liste vient du champ `a_mettre_a_jour` des fiches et affiche l'article,
  l'information, la source et la date prévue.
- Un bouton renvoie l'article en rédaction.

### Paramètres du pipeline

- La génération mensuelle des idées et les dates et heures de publication sont
  conservées.
- Le pipeline règle le nombre d'articles rédigés par jour, fixé à 2 par défaut,
  et les jours de rédaction, fixés du lundi au vendredi par défaut.

## Ce qu'on garde (en le simplifiant si besoin)

- Authentification et comptes.
- Projets, catégories, articles, versions et retour arrière.
- Jobs asynchrones (suivi de l'état d'une rédaction).
- Contrôle de cannibalisation (alerte seulement).
- Contrôle de plagiat (alerte seulement).
- Liste des articles publiés transmise au skill pour le maillage interne.
- Constructeur de données structurées : Article, FAQPage, Person (auteur), BreadcrumbList.
- Suivi du coût réel par article.
- Règles RGPD.
- Rédacteur du laboratoire (Claude Code + skill), qui devient le seul rédacteur.

## Ce qu'on supprime totalement

Tout ce qui rédigeait, analysait ou notait à la place du skill :

- l'orchestrateur `seo_generation_orchestrator.py` et l'ancien pipeline modulaire ;
- le mode agent historique `agent_generation.py` et `docs/AGENT-WRITER-PROMPT.md` ;
- contexte projet, stratégie de catégorie, découverte d'idée, analyse d'intention, brief de recherche, insights humains, écarts de contenu, mots-clés secondaires, registre des faits, angle éditorial, gain d'information, planificateur de plan, plans d'images, d'encadrés et de FAQ, adaptation du style, brief de production ;
- rédacteur par sections, réécriture de qualité, relecture ciblée, vérification de cohérence, insertion de citations, correction de structure, révision ciblée, générateur de FAQ, générateur de méta ;
- tous les contrôles et scores : contrôle de langue, originalité, humanisation, lisibilité, EEAT et sa couche LLM, garde éditorial, juges éditoriaux v1 et v2, calibration du juge, GEO, checklist SEO, score automatique, revue SEO agrégée, extraction des affirmations, fact-check ;
- les agents du registre jamais exécutés et les alias historiques ;
- le routage agent par agent vers des fournisseurs, et les liaisons agent-fournisseur ;
- les paramètres CMS devenus inutiles : `min_publish_score`, `agent_reasoning_effort`, `agent_consistency_review`, `agent_reader_fallback`, `OUTLINE_PLANNER_MODE`, modèle par agent, réglages d'illustration détaillés ;
- les écrans du front-end liés à tout ce qui précède.

Les scores ne sont plus calculés ni affichés : la qualité est garantie par le skill et par la validation humaine.

## Règles de travail

- Répartition : Codex environ 70 % (suppressions, base de données, API, front-end, README, tests), Claude Code environ 30 % (branchement du rédacteur, revue finale, tests de bout en bout).
- Tout le travail est commité et poussé sur `main` (règles 8 et 9 de `docs/COORDINATION-AGENTS.md`).
- Avant chaque suppression, vérifier qu'aucun code conservé ne dépend du fichier supprimé. Tous les tests passent après chaque phase.
- Les colonnes de base de données devenues inutiles sont supprimées par une migration propre, après sauvegarde, dans une phase dédiée.
- Commits en anglais, minuscules, format « type: verbe ».

## Commits et coordination entre Codex et Claude Code

- **Petits commits séparés, beaucoup de commits.** Un commit = un seul changement cohérent : une suppression de fichier, une route, un écran, une migration, un test. Jamais un gros commit qui mélange plusieurs choses. Des centaines de commits ne posent aucun problème : chaque étape doit pouvoir être retrouvée ou annulée seule.
- **Chaque commit laisse le projet fonctionnel.** Les tests concernés passent avant chaque push.
- **Commit et push immédiats.** Dès qu'un changement est terminé et testé, il est commité et poussé sur `main`. Aucun fichier modifié n'est laissé en attente.
- **Avant chaque push :** `git pull` (fusion, jamais de rebase ni de force-push), relancer les tests, puis pousser.
- **Chacun ses fichiers.** Codex travaille sur les phases 1, 2, 4 et 5 ; Claude Code sur les phases 3 et 6. Un agent ne modifie pas un fichier que l'autre est en train de changer. En cas de besoin, il l'écrit dans `docs/COORDINATION-AGENTS.md` et attend.
- **Journal de progression.** À la fin de chaque phase, l'agent ajoute dans `docs/COORDINATION-AGENTS.md` : la phase terminée, la liste des commits, le résultat des tests et ce que l'autre agent peut commencer.
- **Ordre.** Codex fait d'abord la phase 1. Claude Code ne commence la phase 3 qu'après la phase 2. Codex peut faire la phase 4 en parallèle de la phase 3, car les fichiers sont différents.
- **Validation de Mayne.** Avant toute suppression de fichiers ou de colonnes, l'agent présente la liste exacte et attend la validation.

## Phases

1. **Codex : nouveau parcours côté backend.** Statuts (idée, en rédaction, à relire, validé, programmé, publié, à mettre à jour), routes de l'API, routes de dépôt pour le rédacteur local, validation basée sur les 3 contrôles techniques au lieu de scoring_service, calendrier de publication automatique, liste des mises à jour. L'ancien pipeline reste en place.
2. **Codex : bascule des points d'entrée.** Routers, generation_job_service, production_queue, pipeline_service, validation et publication passent au nouveau parcours.
3. **Claude Code : branchement du rédacteur local.** Le rédacteur local est branché sur les nouvelles routes.
4. **Codex : suppression de l'ancien pipeline.** Suppression par petits lots, un lot par commit, avec tests verts après chaque lot.
5. **Codex : front-end simplifié.** Les 5 écrans et la page de paramètres décrits plus haut, avec un parcours simplifié.
6. **Codex : base de données et documentation.** Migration de suppression des colonnes inutiles et README réécrit.
7. **Claude Code : test de bout en bout.** Test d'un sujet ajouté, rédigé, relu, validé, programmé et publié.
