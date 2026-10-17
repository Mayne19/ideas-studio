# Editorial Agent Lab

Prototype isolé de l'algorithme éditorial décrit dans la conversation Claude.

Ce dossier ne modifie pas le pipeline existant d'Ideas Studio. Il formalise
uniquement le noyau de la nouvelle méthode :

1. contexte du site et articles existants ;
2. concurrents, forces, faiblesses et contradictions ;
3. intention réelle du lecteur ;
4. faits et sources ;
5. plan détaillé avec call out, sections, H3 et FAQ ;
6. rédaction complète en une passe via un port de modèle ;
7. validations bloquantes ;
8. analyse de similarité sans réécriture automatique ;
9. conservation de la meilleure version.

Le cœur de l'algorithme reste testable avec des faux fournisseurs. Le mode réel
réutilise toutefois les adaptateurs de recherche et de lecture existants, puis
le client Anthropic/OpenRouter déjà présent dans Ideas Studio. Il fait un seul
essai complet dans une conversation modèle : recherche, lecture, analyse
sémantique, plan, rédaction et relecture. Rien n'est publié dans le CMS.

Le plan de construction et les preuves sont dans
[`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) et
[`VALIDATION_LOG.md`](VALIDATION_LOG.md).

## Exécution des tests

Depuis la racine du dépôt :

```bash
python -m pytest experiments/editorial_agent_lab/tests -q
```

## Un essai réel

Quand le runtime du CMS et ses credentials sont disponibles :

```bash
.venv/bin/python -m experiments.editorial_agent_lab.run_live "mot-clé de test" \
  --site-name "Nom du site" --domain "example.com"
```

Le résultat est écrit dans `run/article.html` et le rapport complet dans
`run/report.json`. La clé est résolue depuis le runtime existant ou depuis les
variables d'environnement, sans jamais être copiée dans le laboratoire.

L'analyse sémantique réelle est faite par le modèle dans sa conversation : il
compare les concurrents, repère leurs lacunes et contradictions, formule la
question réelle du lecteur, choisit l'angle, organise le plan et relie les
faits aux sources. Le code ne prétend pas remplacer ce jugement par un score
de mots-clés. Il contrôle ensuite la structure et la similarité sans réécrire
le texte.

## Règle de correction

Une alerte stylistique ou de similarité ne remplace jamais automatiquement le
texte. La validation humaine et la publication viennent après ce laboratoire ;
elles ne font pas partie de l'algorithme testé ici.
