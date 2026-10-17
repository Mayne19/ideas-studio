# Laboratoire de rédaction

Le rédacteur est un seul agent Claude Code, lancé en mode non interactif avec la session déjà authentifiée
(abonnement, sans OpenRouter). Il charge le skill `redaction-article`
(`.claude/skills/redaction-article/SKILL.md`), seule source des consignes de rédaction, et n'a accès qu'aux
outils WebSearch et WebFetch, avec un raisonnement élevé. Il ne peut lire aucun fichier du dépôt : les
articles d'étalonnage du juge (`tests/data/judge_calibration`) ne lui sont jamais transmis.

## Fichiers

- `run_live.py` : génère un article en ligne de commande.
- `test_ui.py` : interface locale qui lance le même rédacteur depuis un formulaire.
- `editorial_agent/claude_cli_client.py` : lance Claude Code (outils autorisés, effort, coût et jetons réels).
- `editorial_agent/writer.py` : transmet le sujet et la liste des articles du site, puis sépare l'article
  Markdown de la fiche de publication JSON.
- `editorial_agent/checks.py` : les trois contrôles bloquants (encadré « En résumé », aucun tiret cadratin,
  fiche JSON valide).
- `editorial_agent/similarity.py` : alerte de plagiat (phrases identiques à une source), sans blocage.
- `editorial_agent/runner.py` : enchaîne rédaction, contrôles et fichiers de sortie.
- `tests/test_lab.py` : tests du laboratoire.

## Générer un article

Depuis la racine du dépôt :

```bash
python -m experiments.editorial_agent_lab.run_live "Quelle application gratuite choisir pour apprendre une langue"
```

Option : `--site-articles articles.json` (liste `{titre, url, resume}`) pour le maillage interne.

Sortie dans `experiments/editorial_agent_lab/outputs/<slug>/` : `article.md`, `fiche.json` et `report.json`
(coût réel, jetons, contrôles, alerte de plagiat).

Interface locale : `python -m experiments.editorial_agent_lab.test_ui --port 8765`, puis
`http://127.0.0.1:8765`.

Tests : `python -m pytest experiments/editorial_agent_lab/tests -q`.
