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
- A16/A17 : ces décisions éditoriales sont maintenant explicitement hors du
  run automatique. Le modèle ne reçoit aucune demande de validation et aucune
  boucle de conversation ne reprend l'article après sa production.
- A18 : le harnais de comparaison est prêt, mais attend encore cinq sujets et
  dix articles réels avant de conclure.

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

Le jugement de l'éditeur et la transformation de ses remarques en règles sont
des opérations postérieures au laboratoire. Elles ne sont pas exécutées par
l'algorithme et ne déclenchent aucune reprise automatique.
