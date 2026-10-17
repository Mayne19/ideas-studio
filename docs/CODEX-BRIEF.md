# Dossier Codex

Rédigé par Claude (rédacteur en chef) le 17 octobre 2026, ajouté au dépôt par Claude Code. À lire en entier avant toute tâche.

> Les trois articles de référence validés (questionnaire-90.md, basilic-90.md, budget-50-30-20-90.md), collés par Claude dans sa conversation, sont disponibles sur le Mac dans `/Users/mayne/Perso/Projects/ideas-studio-shared/calibration/` : copie-les tels quels dans `tests/data/judge_calibration/` sur ta branche.

**DOSSIER CODEX : à lire en entier avant toute tâche**

**1. L'objectif**
- Ideas Studio génère des articles de blog en français pour theslash.fr.
- On veut qu'un article généré par le système soit noté au moins 90/100 par Claude (le rédacteur en chef), publiable et sans faute grave.
- Notes actuelles : essai 4 à 84, essai 5 à 82.
- Personne ne s'arrête avant l'objectif.

**2. Les rôles**
- **Claude (rédacteur en chef) :** il note les articles, fixe les règles et valide chaque diff. Rien n'entre sur main sans son « VALIDÉ » écrit, donné sur un hash précis.
- **Claude Code (directeur technique) :** il est le seul à écrire sur main. Il fusionne, déploie sur Railway et lance les essais payants.
- **Codex (toi) :** tu codes sur des branches `gpt/<sujet>` et tu vérifies les faits des articles. Tu ne fusionnes jamais toi-même.

**3. Les fichiers à lire avant de coder** (sur origin/main, après `git pull`)
- `docs/COORDINATION-AGENTS.md` : les règles d'équipe.
- `docs/AGENT-WRITER-PROMPT.md` : le prompt de l'agent rédacteur. C'est la référence des règles d'écriture.
- `app/services/seo/agent_generation.py` : les contrôles appliqués à chaque article. Voici ce qu'ils vérifient, et chacun est une faute dure qui déclenche un tour de correction :

  | Fonction | Ce qu'elle contrôle |
  |---|---|
  | `competitor_errors` | concurrent cité, et moins de 3 domaines de sources |
  | `fact_errors` | chaque fait a une citation et une source déclarée |
  | `quote_errors` | toute citation de 4 mots ou plus figure dans `facts` |
  | `source_balance_errors` | aucune source ne porte plus de la moitié des faits |
  | `source_mention_errors` | une même source n'est pas nommée plus de 5 fois |
  | `self_review_errors` | l'auto-relecture n'avoue aucun fait sans source |
  | `prose_count_errors` | un nombre annoncé dans le texte correspond au nombre d'éléments |
  | `judge_errors` | `heading_mismatch`, `unsourced_figure` et `invented_fact` relevés par le juge |

  On y trouve aussi `correction_rounds` (la boucle de correction) et `consistency_review` (la relecture de cohérence).
- `app/services/seo/agent_writer_openrouter.py` : le pont vers le modèle, les outils de recherche et de lecture, l'arrêt dur sur le coût, le refus des URL inventées.
- `app/services/seo/editorial_judge_v2.py` : le juge v2, avec la grille sur 100, les mesures calculées par le code et les plafonds en cas de faute grave. **Sa signature exacte :**
  `judge_v2(content, call_fn, *, title="", keyword="", facts=list[dict]|None, competitors=list[str]|None, faq=list[dict]|None, meta_title="", meta_description="", slug="")`
  Les faits sont des dictionnaires `{value, quote, source_url}`, les concurrents des domaines (exemple : `lonelyplanet.fr`), et le contenu peut être en Markdown.
- `tests/test_agent_generation.py` et `tests/test_agent_writer.py` : lis les tests existants avant d'en écrire.

**4. La base de données (lecture seule)**
- Article : `select r.title, r.body, r.faq from content.articles a join content.article_revisions r on r.id = a.current_revision_id where a.id = :id`
- Faits et concurrents : `select payload from ai.artifacts where article_id = :id and agent_key = 'agent_writer_output' order by created_at desc limit 1`

**5. Les règles de travail** (non négociables)
1. **Lis le code réel** des fonctions que tu appelles ou modifies, et vérifie leur signature. Ne travaille jamais à partir d'un résumé.
2. **Fais exactement la tâche demandée, rien de plus.** Si tu vois un autre problème, signale-le dans ton compte rendu, sans le corriger.
3. **Une branche `gpt/<sujet>` par tâche,** créée depuis origin/main à jour.
4. **Commits :** en anglais, en minuscules, au format `type: verbe` (`feat`, `fix`, `test`, `docs`, `chore`), un sujet par commit. Jamais de rebase, d'amend ni de force-push.
5. **Avant chaque push,** lance ces quatre vérifications :
   - `DATABASE_URL=postgresql://u:p@localhost:5432/x python -m pytest -q tests` : tout doit passer, avec les mêmes tests ignorés qu'avant ;
   - `py_compile` sur chaque fichier modifié ;
   - `git diff --check` ;
   - une recherche de secrets dans le diff.
6. **Tout nouveau contrôle** a un test positif et un test de faux positif.
7. **Après le push,** vérifie avec `git ls-remote origin | grep <branche>` que le hash est bien sur le dépôt.
8. **Ton compte rendu suit toujours ce format :**
   - la branche et le hash (vérifié) ;
   - la liste exacte des fichiers modifiés ;
   - ce que fait chaque commit, ni plus ni moins que le diff ;
   - le résultat des tests.
9. **Aucun appel payant au modèle** sans validation de Claude. Le budget est quasi épuisé.
10. **Ne touche jamais :** main, les branches `claude-code/*`, le frontend (sauf si on te le demande), l'ancien pipeline.
11. **N'injecte jamais** les articles de référence dans le prompt de l'agent. Ils servent uniquement à l'étalonnage du juge.

**6. Ta tâche maintenant : `gpt/judge-calibration`**, en un seul commit `fix: correct calibration manifest and faq parsing`.
1. Ajoute les trois fichiers Markdown que Claude a collés dans la conversation à 8 h 34, sous ces noms exacts :
   - `tests/data/judge_calibration/budget-50-30-20-90.md`
   - `tests/data/judge_calibration/basilic-90.md`
   - `tests/data/judge_calibration/questionnaire-90.md`

   Ils remplacent les anciens. Fais-en un commit séparé, `chore: replace calibration articles with validated versions`.
2. Dans `manifest.json`, corrige l'identifiant de « reste à vivre » : la bonne fin est `e089f2ef-0c91-4a9a-8e18-a87ee6b2be7a`.
3. Fixe la note de référence du questionnaire à **87**.
4. Dans `_faq_from_markdown`, la FAQ s'arrête au prochain titre `## ` : la conclusion qui suit ne doit pas être absorbée.
5. Ajoute un test du découpage de la FAQ sur un petit Markdown avec un titre `## ` après la FAQ.
6. Envoie le compte rendu au format du point 8.

**Ta tâche suivante :** la vérification des faits de l'essai 5 (article `d34f45fb`), en lecture seule. Compare chaque chiffre à la page source et classe chacun en confirmé ou infirmé, avec la citation.
