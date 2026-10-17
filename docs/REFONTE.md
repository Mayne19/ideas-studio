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

## Le parcours dans l'application (5 écrans)

### 1. Idées
- Liste des sujets par catégorie, avec leur statut.
- Ajout manuel d'un sujet, ou génération d'une liste d'idées pour une catégorie.
- Contrôle automatique de doublon avec les articles existants (cannibalisation), affiché comme simple alerte.
- Un bouton : « Envoyer en rédaction ».

### 2. Rédaction
- File des sujets en cours de rédaction, avec l'état (en attente, en cours, terminé, erreur).
- Le coût réel de chaque article est affiché, rien d'autre.
- Aucun réglage : modèle, raisonnement et outils sont fixés dans le code.

### 3. Relecture et validation
- L'article est affiché mis en forme, comme sur le site, jamais en Markdown brut.
- Édition directe du texte.
- À côté de l'article, la fiche lisible :
  - titre SEO, meta description, slug (modifiables) ;
  - sources ;
  - images à ajouter, avec emplacement, texte alternatif et légende ;
  - intégrations proposées (vidéo, publication) ;
  - expériences de l'équipe à ajouter ;
  - informations à mettre à jour plus tard.
- Trois contrôles techniques affichés en vert ou rouge : encadré « En résumé », aucun tiret cadratin, fiche valide. Le plagiat est une simple alerte.
- Deux boutons : « Valider » ou « Renvoyer en rédaction » avec un commentaire.

### 4. Publication
- Calendrier des articles validés.
- La date de publication est fixée automatiquement selon la cadence choisie dans les paramètres. Mayne peut la déplacer.
- Publication automatique à la date prévue. Aucun article n'est publié sans validation humaine.

### 5. Mises à jour
- Liste générée depuis le champ `a_mettre_a_jour` des fiches : quelle information revérifier, dans quel article, et quand.
- Un bouton pour renvoyer l'article en rédaction pour mise à jour.

### Paramètres (une seule page, réduite au minimum)
- Nom du site, domaine, langue du site (fixée à la création, une langue par site ou département).
- Catégories.
- Cadence de publication (articles par semaine).
- Mode de rédaction : local (abonnement Claude, par défaut) ou API (plus tard).
- Auteurs : nom, photo, biographie (pour les pages auteur et l'E-E-A-T).

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

1. **Codex : nettoyage du backend.** Suppression de tout ce qui est listé dans « Ce qu'on supprime », mise à jour des tests.
2. **Codex : nouveau parcours côté backend.** Statuts des sujets et articles (idée, en rédaction, à relire, validé, programmé, publié, à mettre à jour), routes de l'API, calendrier de publication automatique, liste des mises à jour.
3. **Claude Code : branchement du rédacteur.** Le rédacteur du laboratoire devient le service de rédaction, en mode local (rédacteur sur le Mac de Mayne qui récupère les sujets et dépose les résultats).
4. **Codex : front-end simplifié.** Les 5 écrans et la page de paramètres décrits plus haut, suppression des anciens écrans.
5. **Codex : base de données et documentation.** Migration de suppression des colonnes inutiles, README réécrit (rôle de l'application, installation, parcours, rédaction locale).
6. **Claude Code : vérification finale.** Test de bout en bout : un sujet ajouté, rédigé, relu, validé, programmé et publié.
