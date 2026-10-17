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
- Le workflow de laboratoire appelle désormais les étapes dans l'ordre :
  recherche, analyse concurrentielle, intention lecteur, faits, angle, plan,
  rédaction, puis validations. Le test utilise uniquement des fournisseurs
  fictifs et ne touche pas au CMS.
- A15 : le rapport contient le plan, l'angle, le brouillon, les contrôles, les
  alertes, le modèle, le coût et les traces de recherche.
- A16 : une validation humaine ne peut pas approuver un résultat bloqué.
- A17 : une remarque peut produire une règle `pending` sans modifier le texte.
- A18 : le harnais de comparaison refuse de conclure avant cinq sujets et dix
  articles, et renvoie `NO-GO` dès qu'une erreur bloquante reste présente.

### Preuve exécutée

Le runtime Python fourni par l'environnement a exécuté les tests du laboratoire
par appel direct des fonctions de test : tous les tests ont renvoyé `PASS`.
La compilation Python du dossier a également réussi et `git diff --check` ne
signale aucune erreur. Les validations A4, A5, A7, A9 et A10 sont des
validations de contrats déterministes ; elles ne prétendent pas encore
remplacer l'analyse sémantique du modèle.

### Limitation connue

Le runtime projet `.venv` contient bien pytest et `pydantic_settings` ; les 23
tests du laboratoire passent, la compilation passe et `git diff --check` passe.
Le nouveau lanceur réel est installé, mais son essai unique a été bloqué avant
tout appel réseau : aucune clé Anthropic/OpenRouter n'est accessible dans le
runtime du terminal, et aucun credential CMS ne peut être résolu sans la
configuration de l'application. Aucun crédit n'a donc été consommé.

La validation humaine et la transformation des remarques en règles sont des
étapes postérieures au laboratoire. Elles ne sont plus comptées comme des
étapes de l'algorithme.
