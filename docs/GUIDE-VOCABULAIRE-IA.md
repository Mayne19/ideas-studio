# DOCUMENT 3 — VOCABULAIRE IA À BANNIR
## Liste complète basée sur des sources vérifiées (2024-2026)

---

## AVERTISSEMENT PRÉLIMINAIRE

Ce document est basé sur des recherches récentes incluant une étude scientifique publiée en 2024 sur les biais linguistiques de GPT-4 (550 textes analysés en français et néerlandais), les signalements d'éditeurs francophones professionnels, et les analyses de GPTZero, Compilatio et Originality.ai.

Point capital : les détecteurs IA n'utilisent pas de liste noire de mots. Ils analysent la prédictibilité statistique de l'ensemble du texte — vocabulaire et structure des phrases ensemble. Supprimer les mots de cette liste réduit le score IA indirectement, mais ne suffit pas seul. C'est pour ça que ce document doit être utilisé avec les deux autres guides (règles stylistiques + paires avant/après).

---

## PARTIE 1 — LES 5 FAMILLES DE VOCABULAIRE IA EN FRANÇAIS

### FAMILLE 1 — Transitions creuses

Ce sont les connecteurs que l'IA empile pour signaler qu'une idée en suit une autre. Les rédacteurs humains les varient ou les abandonnent quand le lien est évident. Les modèles les utilisent mécaniquement.

**Liste complète à bannir :**
- En outre
- De plus
- Par ailleurs
- Néanmoins
- Toutefois
- Ainsi
- Dès lors
- En somme
- En définitive
- D'autre part
- À cet égard
- En effet (en début de paragraphe systématique)
- Effectivement (en début de paragraphe)
- Notamment (en début de phrase)
- De surcroît
- Qui plus est
- À cela s'ajoute

**Remède :** supprimez la transition et relisez la phrase. Si le sens tient, le connecteur n'était pas nécessaire. Si une articulation est vraiment utile, choisissez un lien spécifique et concret plutôt qu'un connecteur générique.

**AVANT :**
"Les maquettes permettent d'économiser du temps. De plus, elles facilitent la communication avec le client. Par ailleurs, elles réduisent les erreurs de développement."

**APRÈS :**
"Les maquettes économisent du temps, clarifient les attentes du client avant le premier commit, et réduisent les erreurs qu'on ne découvre plus en production mais en réunion."

---

### FAMILLE 2 — Quantificateurs vagues et intensificateurs creux

Les modèles modèrent leurs affirmations en permanence parce que les propos prudents sont statistiquement plus souvent justes. Résultat : des phrases bourrées de qualificatifs qui n'apportent aucune information.

**Liste complète à bannir :**
- Divers
- Nombreux
- Plusieurs (quand le nombre est connu)
- Multiples
- Extrêmement
- Particulièrement
- Fortement
- Considérablement
- Hautement
- Grandement
- Véritablement
- Réellement (comme intensificateur vide)
- Véritablement
- Absolument
- Tout à fait (en début de réponse)
- Certainement (en début de réponse)
- Bien sûr (en début de réponse)

**Remède :** remplacez par un chiffre précis ou supprimez le mot. "Extrêmement important" et "important" pèsent exactement la même chose — le premier gaspille un adverbe.

**AVANT :**
"Cette approche est particulièrement efficace et permet de considérablement réduire les nombreuses erreurs fréquentes."

**APRÈS :**
"Cette approche réduit les erreurs de 40% selon une étude Nielsen de 2024 sur 200 projets web."

---

### FAMILLE 3 — Verbes corporatifs et managériaux

Ces termes pullulent dans la presse business et la communication d'entreprise qui constituent une part importante des données d'entraînement. Ils sonnent autorisés et ne veulent presque rien dire hors contexte.

**Liste complète à bannir :**
- Utiliser → se servir de, employer, exploiter
- Mettre en œuvre → appliquer, lancer, faire
- Faciliter → aider, rendre possible, simplifier
- Permettre → donner accès à, rendre possible
- Démontrer → montrer, prouver
- Élaborer → construire, développer, rédiger
- Optimiser → améliorer, accélérer, alléger
- Valoriser → mettre en valeur, exploiter
- Mobiliser → rassembler, utiliser, impliquer
- Déployer → lancer, étendre, installer
- Adresser (un problème) → résoudre, traiter, répondre à
- Impacter → affecter, changer, modifier
- Générer (du trafic, des leads) → attirer, produire, créer
- Booster → augmenter, accélérer, renforcer

**Remède :** choisissez le verbe le plus court et le plus concret. "Faire" bat "mettre en œuvre" à tous les coups. "Montrer" est plus clair que "démontrer". "Aider" est plus honnête que "faciliter".

---

### FAMILLE 4 — Ouvertures de paragraphe et formules pompeuses

Les modèles ont des préférences très marquées sur la façon d'entamer un paragraphe explicatif. Ces formules font partie des signaux les plus reconnaissables d'un texte généré.

**Liste complète à bannir :**

*Ouvertures de paragraphe :*
- "Il convient de noter que..."
- "Il est important de souligner que..."
- "Il est essentiel de comprendre que..."
- "Il y a lieu de mentionner que..."
- "Force est de constater que..."
- "Il s'agit de comprendre que..."
- "À cet égard..."
- "En guise d'introduction..."
- "Avant toute chose, rappelons que..."
- "Il faut garder à l'esprit que..."
- "Il va sans dire que..."
- "Rappelons que..."
- "Notons également que..."
- "Soulignons que..."

*Conclusions stéréotypées :*
- "Pour conclure, on peut affirmer que..."
- "En conclusion..."
- "Pour résumer..."
- "En définitive..."
- "Au final..."
- "En somme..."
- "Tout bien considéré..."
- "Il convient donc de retenir que..."
- "Nous avons vu que..."
- "Trouver le juste équilibre entre..."
- "Concilier les deux approches..."

**Remède :** commencez par l'affirmation elle-même. Si quelque chose mérite d'être noté, notez-le. Coupez le préambule et entrez directement dans le sujet.

---

### FAMILLE 5 — Buzzwords managériaux et adjectifs vides

Le vocabulaire managérial à la française a sa propre liste noire. Ces mots ne sont pas interdits isolément, mais leur accumulation sur quelques paragraphes est un drapeau rouge immédiat.

**Liste complète à bannir :**
- Incontournable
- Primordial
- Essentiel (comme adjectif intensificateur)
- Indispensable
- Holistique
- Transversal
- Structurant
- Ambitieux (hors contexte précis)
- Robuste
- Paradigme
- Synergie
- Révolutionnaire
- Innovant (sans précision)
- Performant (comme adjectif générique)
- Clé (dans "joue un rôle clé")
- Catalyseur
- Levier (au sens figuré systématique)
- Écosystème (numérique, digital)
- Paysage (numérique, technologique)
- Royaume (des données, du digital)
- Naviguer (dans la complexité)
- Plonger (dans un sujet)

**Remède :** supprimez le mot et demandez-vous ce qu'il prétendait apporter. Neuf fois sur dix, la phrase est plus forte sans lui. Si le terme dit vraiment quelque chose, remplacez-le par une description concrète.

---

## PARTIE 2 — STRUCTURES DE PHRASES IA À DÉTECTER ET CORRIGER

Au-delà des mots, l'IA a des structures de phrases reconnaissables. Ces patterns sont souvent plus révélateurs que le vocabulaire.

### Structure 1 — "Non seulement X, mais aussi Y"

C'est l'une des constructions les plus fréquentes de ChatGPT. Elle cherche à paraître nuancée en ajoutant une deuxième idée, mais elle sonne mécanique à force de répétition.

**AVANT :**
"Non seulement cette solution est efficace, mais elle est en plus économique."

**APRÈS :**
"Cette solution coûte 30% moins cher qu'une refonte classique et donne des résultats mesurables dès le premier mois."

---

### Structure 2 — "Cela..." ou "Cette approche..." en début de plusieurs phrases consécutives

L'IA enchaîne fréquemment des phrases qui commencent de la même manière. Trois phrases consécutives commençant par "Cela" ou "Cette approche" est un signal fort.

**AVANT :**
"Cette approche permet d'économiser du temps. Cette approche améliore la relation client. Cette approche réduit les coûts de développement."

**APRÈS :**
"Le temps économisé est réel — en moyenne trois semaines sur un projet de six. La relation client s'améliore parce que les malentendus sont réglés avant le premier commit, pas après. Et les coûts de développement baissent mécaniquement quand on ne refait pas deux fois le même travail."

---

### Structure 3 — "Premièrement... Deuxièmement... Enfin..."

Les rédacteurs humains abandonnent souvent leur énumération à mi-chemin ou changent de registre. Les modèles, presque jamais. Une liste "Premièrement / Deuxièmement / Enfin" répétée sur plusieurs sections est un marqueur fort.

**AVANT :**
"Premièrement, définissez vos objectifs. Deuxièmement, choisissez vos outils. Enfin, mesurez vos résultats."

**APRÈS :**
"Définir les objectifs en premier, avant de toucher aux outils. C'est l'ordre que presque tout le monde inverse. Les outils viennent après, quand on sait ce qu'on mesure."

---

### Structure 4 — "[X] joue un rôle clé dans [Y]"

Cette construction est l'une des plus signalées par les détecteurs francophones. Elle n'est pas fausse, mais sa présence systématique signe l'origine.

**AVANT :**
"Le SEO joue un rôle clé dans la visibilité de votre site."

**APRÈS :**
"Sans SEO, votre site existe uniquement pour ceux qui connaissent déjà votre URL."

---

### Structure 5 — "Les études montrent que..." / "Les experts s'accordent à dire que..."

L'IA utilise ces formules pour paraître crédible sans citer aucune source réelle. C'est de la fausse précision.

**AVANT :**
"Les études montrent que les sites rapides convertissent mieux. Les experts s'accordent à dire que la vitesse est un facteur SEO majeur."

**APRÈS :**
"Selon une étude Google de 2023, chaque seconde de chargement supplémentaire réduit les conversions de 7%. Ce n'est pas une tendance — c'est une équation."

---

### Structure 6 — La liste à puces systématique

L'IA aborde les problèmes complexes avec des listes. Les listes sont efficaces, mais leur abus aplatit le récit. Un article qui transforme chaque argument en bullet point manque les connexions logiques entre les idées.

**AVANT :**
"Les avantages d'une maquette :
- Gain de temps
- Réduction des erreurs
- Meilleure communication client
- Validation des objectifs"

**APRÈS :**
"Une maquette économise du temps parce qu'elle réduit les erreurs avant qu'elles coûtent cher. Et ces erreurs ne sont pas techniques — elles sont stratégiques. Une page sans objectif clair, une navigation qui ne mène nulle part, un message principal qu'on comprend en trente secondes mais qu'on devrait comprendre en trois."

---

### Structure 7 — La fausse nuance finale

L'IA conclut presque toujours sur une métaphore d'équilibre pour paraître nuancée sans prendre position. Cette formule apparaît sur n'importe quel sujet controversé.

**À détecter et bannir :**
- "Il convient de trouver le juste équilibre entre..."
- "Il faut concilier les deux approches..."
- "La vérité se situe probablement entre les deux..."
- "Chaque situation est différente et il n'existe pas de solution universelle..."
- "En fin de compte, tout dépend de votre contexte spécifique..."

**Remède :** prendre une position réelle. Si le sujet est nuancé, expliquer pourquoi avec des faits précis — pas avec une formule d'équilibre vague.

---

### Structure 8 — L'anglicisme structurel

16% des erreurs linguistiques dans les textes IA ont une origine anglaise (étude sur GPT-4, 2024). Ce sont des expressions traduites mot à mot qui sonnent faux en français naturel.

**À détecter :**
- "Faire du sens" → avoir du sens
- "Adresser un problème" → résoudre, traiter un problème
- "Plonger dans un sujet" → explorer, examiner (et surtout l'éviter)
- "Naviguer dans la complexité" → gérer la complexité
- "Prendre action" → agir, passer à l'action
- "Livrer de la valeur" → apporter de la valeur
- "Impacter positivement" → améliorer, renforcer
- "Challenger une idée" → remettre en question
- "Onboarder un client" → intégrer un client

---

## PARTIE 3 — VOCABULAIRE SPÉCIFIQUE PAR MODÈLE IA

### ChatGPT en français

Préférences marquées :
- "Tout à fait", "absolument", "certainement", "bien sûr" en début de réponse
- Listes numérotées systématiques
- Transitions lourdes sur les paragraphes longs
- Structure "Premièrement / Deuxièmement / Enfin"
- Paragraphes d'une longueur étonnamment constante

### Claude en français

Préférences marquées :
- "En effet", "effectivement", "tout à fait" en ouverture de réponse
- "Notamment" et "par ailleurs" comme connecteurs de paragraphe
- "Approfondi" et "nuancé" dans les longues réponses
- Tendance aux phrases bien construites et symétriques

### Gemini en français

Préférences marquées :
- "Complet", "approfondi", "exhaustif", "global" comme modificateurs
- Transitions qui miroitent celles de ChatGPT
- Structure académique très marquée

**Note importante :** en pratique, la même liste de mots s'applique aux trois modèles. Les différences sont stylistiques, pas catégorielles.

---

## PARTIE 4 — TABLEAU DE RÉFÉRENCE COMPLET

Ce tableau condense les expressions les plus courantes avec leur catégorie et l'alternative recommandée.

| Mot ou expression IA | Catégorie | Alternative |
|---|---|---|
| En outre / De plus | Transition creuse | Supprimez, ou connecteur précis |
| Par ailleurs | Transition creuse | Supprimez ou nouvelle phrase |
| En conclusion | Ouverture creuse | Entamez directement par la conclusion |
| Il convient de noter que | Ouverture creuse | Supprimez, gardez l'information |
| Force est de constater | Registre académique | Constatez directement |
| Il est important de souligner | Ouverture creuse | Supprimez |
| Divers / Nombreux / Plusieurs | Quantificateur vague | Donnez le chiffre exact ou supprimez |
| Extrêmement / Particulièrement | Intensificateur creux | Supprimez |
| Tout à fait / Absolument | Marqueur ChatGPT | Supprimez en début de phrase |
| Utiliser | Verbe corporatif | Se servir de, employer |
| Faciliter | Verbe corporatif | Aider, rendre possible |
| Mettre en œuvre | Verbe corporatif | Appliquer, faire, lancer |
| Optimiser | Verbe corporatif | Améliorer, accélérer, alléger |
| Booster | Verbe anglicisme | Augmenter, accélérer, renforcer |
| Une multitude de | Formule de remplissage | Donnez un chiffre ou supprimez |
| Les études montrent que | Fausse précision | Citez l'étude réelle ou reformulez |
| Notamment / Par ailleurs | Ouverture creuse | Coupez et entrez dans le vif |
| Holistique / Transversal | Modificateur vide | Précisez ce que cela couvre vraiment |
| Joue un rôle clé | Affirmation vague | Décrivez l'effet précis |
| En définitive | Connecteur de fin creux | Supprimez, énoncez la conclusion |
| À cet égard | Transition vide | Supprimez |
| Approfondi / Complet | Marqueur Gemini/Claude | Précisez la profondeur réelle |
| Incontournable | Buzzword vide | Expliquez pourquoi concrètement |
| Primordial / Essentiel | Superlatif vide | Supprimez ou justifiez avec un fait |
| Synergie | Buzzword vide | Décrivez l'effet précis |
| Révolutionnaire | Buzzword vide | Décrivez ce qui change concrètement |
| Paradigme | Registre académique | Remplacez par ce dont vous parlez vraiment |
| Naviguer dans | Anglicisme | Gérer, traverser, affronter |
| Plonger dans | Anglicisme (delve) | Explorer, examiner, analyser |
| Faire du sens | Anglicisme | Avoir du sens |
| Adresser un problème | Anglicisme | Résoudre, traiter, répondre à |
| Non seulement X mais aussi Y | Structure IA | Reformulez en deux phrases distinctes |
| Cela... Cela... Cela... | Structure répétitive | Variez les sujets grammaticaux |
| Premièrement... Deuxièmement... | Structure mécanique | Intégrez dans la prose ou variez |
| Trouver le juste équilibre | Fausse nuance finale | Prenez une vraie position |

---

## PARTIE 5 — INSTRUCTIONS D'INTÉGRATION POUR L'AGENT

### Ordre de priorité lors de la révision automatique

**Niveau 1 — Bloquant (publication impossible) :**
Présence de plus de 3 expressions de la Famille 4 (ouvertures pompeuses) dans un même article.
Conclusion qui commence par "En conclusion", "Pour résumer", "Nous avons vu que".
Deux structures "Non seulement X mais aussi Y" dans le même article.

**Niveau 2 — Révision obligatoire (score impacté) :**
Présence de plus de 5 expressions des Familles 1, 2 ou 3 dans 500 mots.
Trois paragraphes consécutifs commençant par "Cela" ou "Cette approche".
"Les études montrent que" ou "Les experts s'accordent à dire que" sans source citée.
Deux occurrences de "joue un rôle clé" dans le même article.

**Niveau 3 — Amélioration recommandée :**
Présence de buzzwords de la Famille 5 (holistique, transversal, paradigme).
Anglicismes structurels (naviguer dans, plonger dans, faire du sens).
"Tout à fait" ou "absolument" en début de paragraphe.

### Seuil de densité maximale

Ne pas dépasser 2 mots ou expressions de cette liste par tranche de 100 mots. Au-dessus de ce seuil, l'article est renvoyé en révision avant soumission à l'éditeur humain.

### Ce que cette liste ne résout pas seule

Remplacer les mots de cette liste sans changer la structure des phrases, la longueur des paragraphes et la présence de positions tranchées ne fait pas passer un article de 38/100 à 90/100. Cette liste traite la surface. Les deux autres documents (guide de règles + paires avant/après) traitent la structure et la présence humaine. Les trois documents fonctionnent ensemble.

---

## SOURCES

- Étude scientifique 2024 sur les biais linguistiques de GPT-4 et Zephyr en français (550 textes analysés)
- GPT Watermark Remover — liste des mots typiques IA en français (mai 2026)
- Daria décrypte l'IA — tics de langage ChatGPT (juillet 2025)
- Cours NDRC — 15 signes pour détecter l'écriture IA (février 2026)
- Redacteur.com — éviter les tics de langage ChatGPT (avril 2024)
- Intellectual Lead — mots et expressions surutilisés par ChatGPT (octobre 2025)
- Assistouest — patterns IA à nettoyer pour écrire pour le web (mai 2026)
- Signalements d'éditeurs francophones professionnels (r/france, r/Quebec, Twitter/X, Slack rédaction web)
