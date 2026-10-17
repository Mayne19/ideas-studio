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

Le modèle, la recherche web, le CMS et la base de données sont des ports.
Le cœur de l'algorithme ne dépend d'aucun fournisseur.

Le plan de construction et les preuves sont dans
[`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) et
[`VALIDATION_LOG.md`](VALIDATION_LOG.md).

## Exécution des tests

Depuis la racine du dépôt :

```bash
python -m pytest experiments/editorial_agent_lab/tests -q
```

## Règle de correction

Une alerte stylistique ou de similarité ne remplace jamais automatiquement le
texte. Seules les erreurs bloquantes de structure, de JSON, de plan ou de
cohérence peuvent être renvoyées au modèle dans une version ultérieure.
