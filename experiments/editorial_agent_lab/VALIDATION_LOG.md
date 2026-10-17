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
- A4 : un dossier concurrentiel incomplet est bloqué et les forces comme les
  faiblesses sont obligatoires.
- A5 : l'intention minimale du lecteur peut être construite à partir d'une
  lacune concurrentielle.
- A7 : les sources insuffisamment diversifiées et les sources dominantes sont
  détectées.
- A9 : les contrats de sections et de FAQ sont contrôlés avant rédaction.
- A10 : le recouvrement entre une question FAQ et une section du corps est
  détecté avant rédaction.
- A6 : le registre exige une citation exacte, une source lue, un statut vérifié
  et interdit les concurrents comme sources de faits.
- A8 : un angle doit avoir un gain d'information, une différence par rapport
  aux concurrents et des faits de soutien présents dans le registre.
- A11 : le rédacteur unique compose le contexte complet et n'effectue qu'un
  seul appel ; un JSON invalide est bloquant et ne déclenche pas de correction
  cachée.
- A12 : le validateur central regroupe les contrôles du dossier, du plan, des
  faits et du brouillon. Une similarité est une alerte non bloquante ; elle ne
  déclenche aucune réécriture.

### Preuve exécutée

Le runtime Python fourni par l'environnement a exécuté les tests du laboratoire
par appel direct des fonctions de test : tous les tests ont renvoyé `PASS`.
La compilation Python du dossier a également réussi et `git diff --check` ne
signale aucune erreur. Les validations A4, A5, A7, A9 et A10 sont des
validations de contrats déterministes ; elles ne prétendent pas encore
remplacer l'analyse sémantique du modèle.

### Limitation connue

La commande pytest n'est pas disponible dans le runtime courant. La factory
`from_ideas_studio()` n'a pas été déclarée validée en conditions CMS, car ce
runtime ne contient pas `pydantic_settings`, une dépendance du projet. Aucun
appel réseau réel ni appel payant au modèle n'a été lancé.
