# Coordination des agents IA sur Ideas Studio

Mis à jour le 17 octobre 2026 par Claude Code. Ce fichier est le point de rencontre entre les agents qui travaillent pour Mayne (fondateur) : Claude Code (directeur technique, dans VS Code sur le Mac), Claude (rédacteur en chef, conversation « Article blog questionnaire en ligne » de l'application Claude) et ChatGPT. Lis-le avant d'agir sur le dépôt ou sur le Mac.

## Objectif

Produire des articles publiables (au moins 90/100 selon le rédacteur en chef, aucune faute grave), meilleurs que le top 3 de Google, d'abord sur le site test theslash.fr. Fiindt ne sera branché qu'après des résultats propres sur theslash.

## État au 17 octobre 2026

- Production : backend Railway (déploiement automatique depuis `main`), CMS Vercel, base Supabase.
- Mode de génération par défaut : **agent rédacteur unique** (`app/services/seo/agent_writer.py`, `agent_generation.py`, prompt `docs/AGENT-WRITER-PROMPT.md`). Claude Opus 5.5 via OpenRouter (pont `agent_writer_openrouter.py`, outils web exécutés par notre code), tant que la console Anthropic n'a pas de crédit.
- L'ancienne chaîne reste disponible (Paramètres → Pipeline → Mode de génération) pour comparer.
- Essais : article « tache de gras » 1 (80/100), 2 (78/100 selon le rédacteur en chef). Prochain essai : « comment récupérer du décalage horaire ».
- Budget : clé OpenRouter de test plafonnée (environ 2,30 $ restants), arrêt dur à 3 $ par article. **Aucun achat ni débit de carte sans accord écrit de Mayne.**

## Qui fait quoi

- **Claude (rédacteur en chef)** : évalue chaque article, donne les corrections du prompt et des contrôles. Sa note fait référence.
- **Claude Code (directeur technique)** : implémente, teste, pousse, lance les essais en production, envoie les rapports au rédacteur en chef.
- **ChatGPT** : rôle à convenir avec Mayne. Propositions : relecture critique indépendante des articles générés (lecteur débutant, exactitude), vérification des faits et des sources, ou analyse des concurrents.

## Règles communes

1. **Une seule personne pousse sur `main`** à un instant donné : Claude Code. Tout autre agent travaille sur une branche `gpt/<sujet>` et ne fusionne pas lui-même ; Claude Code relit et fusionne.
2. **Ne jamais pousser pendant une génération en cours** : un déploiement redémarre le serveur et tue la génération.
3. Messages de commit en anglais, en minuscules, petits commits atomiques.
4. Ne jamais toucher aux projets `e-learning` et `manon-prevost` du dossier parent, ni aux onglets personnels de Mayne (cours, mails) sauf demande explicite.
5. Ne jamais injecter les articles de référence du rédacteur en chef dans le prompt ou les données de l'agent : ils servent uniquement à l'évaluation.
6. Tout réglage modifiable doit l'être depuis le CMS, pas dans le code.
7. Pas d'action concurrente à la souris ou au clavier sur le Mac : si un agent pilote l'écran, les autres attendent.

## Comment joindre Claude Code

Écris à Mayne, ou ajoute une section datée à la fin de ce fichier sur une branche `gpt/coordination` : Claude Code la lira avant chaque série de travaux.

## Journal

- 2026-10-17 : création du fichier ; mode agent en production ; règles du rédacteur en chef appliquées (concurrents jamais nommés ni liés, sources admissibles uniquement, faits techniques seulement avec citation, fautes dures en code).
