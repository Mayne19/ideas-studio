# Journal de validation

Ce journal accompagne `IMPLEMENTATION_PLAN.md`. Une validation locale ne vaut
pas encore une validation de production avec de vraies clés et de vraies pages.

## 17 octobre 2026

### Validé

- A0 : le laboratoire est dans un dossier séparé et aucun fichier du pipeline
  existant n'a été modifié.
- A1 : les contrats Pydantic couvrent le contexte, le lecteur, les concurrents,
  les faits, le plan, le call out, la FAQ, le brouillon et le rapport.
- A2 : l'adaptateur de recherche limite les résultats, retire le domaine propre,
  déduplique les URLs et conserve les erreurs dans ses statistiques.
- A3 : l'adaptateur de lecture transmet les pages au fournisseur existant,
  compte les lectures et distingue les contenus vides des lectures réussies.
- A13 : le scanner local signale une phrase identique et produit une suggestion
  séparée sans modifier le texte original.
- A14 : une égalité de sécurité conserve la version la plus ancienne.

### Preuve exécutée

Le runtime Python fourni par l'environnement a exécuté les tests du laboratoire
par appel direct des fonctions de test : tous les tests ont renvoyé `PASS`.
La compilation Python du dossier a également réussi et `git diff --check` ne
signale aucune erreur.

### Limitation connue

La commande pytest n'est pas disponible dans le runtime courant. La factory
`from_ideas_studio()` n'a pas été déclarée validée en conditions CMS, car ce
runtime ne contient pas `pydantic_settings`, une dépendance du projet. Aucun
appel réseau réel ni appel payant au modèle n'a été lancé.
