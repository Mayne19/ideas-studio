---
name: redaction-article
description: Rédiger un article de blog en français pour Ideas Studio, de la recherche à la fiche de publication, avec la méthode éditoriale validée (articles notés 90). À utiliser pour tout article à partir d'un sujet ou d'un mot-clé.
---

# Rédiger un article Ideas Studio

Tu écris pour une personne réelle qui a tapé une question dans Google et qui veut repartir en sachant quoi faire. Tout ce qui suit sert ce seul but. Ces consignes décrivent une manière de travailler et des principes, pas des formules : n'en recopie jamais les mots dans l'article.

## Ce que tu reçois et ce que tu rends

Tu reçois un sujet ou un mot-clé, et parfois une liste d'articles déjà publiés sur le site (titre, URL, résumé) pour le maillage interne.

Tu rends deux choses :
1. L'article complet en Markdown.
2. Juste après, un bloc de code `json` appelé fiche de publication (format en fin de document).

Tu ne rends ni ton raisonnement, ni tes notes de recherche, ni ta relecture.

## Étape 1 : comprendre le lecteur avant de chercher à écrire

Commence par chercher le sujet comme le ferait le lecteur. Ouvre et lis en entier au moins trois résultats éditoriaux sérieux (pas de forums, vidéos, réseaux sociaux ni pages du site lui-même). Lis-les pour comprendre ce que le lecteur trouve aujourd'hui et ce qui lui manque, jamais pour les imiter ou chercher à les battre sur un détail technique.

Formule ensuite pour toi seul :
- le but réel du lecteur, en une phrase ;
- la réponse ou la cause la plus probable à sa question ;
- son niveau (débutant, intermédiaire) et le piège dans lequel il tombe le plus souvent ;
- les questions qu'il se pose, dans l'ordre où elles lui viennent ;
- ce qu'il doit pouvoir faire concrètement après la lecture.

Si une information n'aide pas ce lecteur à comprendre ou à décider, elle n'entre pas dans l'article, même si elle est exacte et impressionnante. Un détail technique n'entre que s'il change la décision d'un non-spécialiste, et il est alors traduit en vérification simple qu'il peut faire lui-même.

## Étape 2 : vérifier les faits

Pour chaque chiffre, prix, limite, règle ou date qui oriente une décision, ouvre la source et vérifie-la toi-même. Un extrait de résultat de recherche n'est pas une source.

- Priorité aux sources primaires : sites officiels des éditeurs ou fabricants, administrations, institutions, organismes de référence, études publiées.
- Toute affirmation juridique ou réglementaire repose sur une source officielle. Sinon, retire-la.
- Un chiffre décisif vient d'une source que tu peux nommer et lier. Une source anonyme ou introuvable fait sortir le chiffre de l'article.
- Aucune citation, anecdote, étude ou statistique inventée. Aucun calcul fabriqué pour faire sérieux.
- Ne cite jamais un autre article de blog, un comparatif ou un guide comme source, et ne parle jamais des « autres articles » ou des « conseils trouvés en ligne ».
- Avant de chercher, décide si le sujet dépend d'un pays (loi, aide, salaire, prix, produit vendu localement, organisme). Si oui, les sources principales sont les autorités et organismes officiels de ce pays. Si l'information est universelle, une source étrangère fiable convient. Ne cite pas une marque ou un produit qui n'est pas vendu dans le pays du lecteur.
- Pour un sujet de santé, d'argent ou de droit, n'utilise que des sources officielles, médicales ou institutionnelles. Ne remplace jamais l'avis d'un professionnel, et indique clairement quand un cas demande d'en consulter un.

## Étape 3 : construire le plan

Le plan suit les questions du lecteur dans leur ordre naturel. La réponse ou la cause la plus probable arrive tôt.

- Si le sujet est un outil, un produit, une méthode ou une notion que le lecteur peut découvrir, une courte section au début du corps explique simplement comment cela fonctionne, sauf si la question suppose déjà qu'il le maîtrise.
- Chaque titre annonce exactement ce que contient la section. Pas de titre slogan, pas de titre vague.
- Chaque H2 commence par un paragraphe avant son premier H3. Une section n'est découpée en H3 que si elle contient au moins deux sous-parties réellement distinctes.
- Un critère qui pèse sur la décision du lecteur, comme le budget, est traité dans le corps, jamais seulement dans la FAQ.
- Un même repère n'est expliqué qu'une fois ; les sections suivantes s'appuient dessus sans le répéter.

Le titre de l'article dit simplement ce que le lecteur va obtenir ou comprendre, sans promesse exagérée ni date.

## Étape 4 : écrire

### L'introduction

Elle compte deux à quatre paragraphes courts et suit trois mouvements reliés entre eux :
1. Un fait de départ : soit le constat essentiel que ta recherche a établi, dit brièvement et sans détail, soit une situation que beaucoup de lecteurs ont vécue, décrite de façon générale avec sa cause. Jamais une scène racontée avec des personnages, une chronologie ou des dialogues.
2. Le problème qui en découle, posé clairement, pour que le lecteur reconnaisse sa propre difficulté. Il peut prendre la forme d'une question.
3. Ce que l'article apporte au lecteur, dit comme ce qui a été fait pour lui. Jamais comme une tâche qu'on lui confie, jamais « cet article ».

L'introduction ne paraphrase pas le titre, n'aligne pas de généralités et ne livre pas tout le détail de la solution.

### L'encadré « En résumé »

Juste après l'introduction et avant le premier H2, un seul encadré, écrit exactement ainsi en HTML :

```html
<aside class="summary"><p class="summary-title">En résumé</p><p>…</p></aside>
```

Deux à trois phrases qui donnent la réponse directe, sans détail ni exception. L'introduction ouvre la réflexion ; le résumé formule l'essentiel. Si l'encadré annonce un nombre, le corps le respecte.

### Le corps

Écris comme quelqu'un qui explique calmement à une personne assise en face de lui.

- Chaque phrase porte un seul message clair, ni découpé en fragments, ni surchargé de plusieurs idées.
- Chaque phrase s'appuie sur la précédente et prépare la suivante. Les idées liées sont réunies par des liaisons naturelles plutôt que posées côte à côte en phrases sèches.
- Choisis la liaison selon le vrai rapport entre les idées : cause, conséquence, exemple, précision, suite ou opposition. N'enchaîne pas les liaisons d'opposition et n'en utilise une que s'il y a une vraie opposition.
- Chaque paragraphe développe une seule idée, et sa première phrase le relie au précédent.
- Un paragraphe chargé en chiffres ou en définitions est allégé : un chiffre à la fois, expliqué avant le suivant.
- Tu t'adresses au lecteur avec « vous », par des phrases directes qui le responsabilisent : montre-lui la conséquence de ce qu'il fait ou ne fait pas.
- Le ton est posé, simple, légèrement vif, jamais agressif, jamais moralisateur. Ne critique pas les autres sources.
- Une seule touche humaine naturelle dans l'article : une situation que beaucoup reconnaîtront. Aucun marqueur forcé, aucune anecdote inventée.
- Aucune formule toute faite, aucun remplissage, aucun appel à l'action publicitaire.
- Le contenu reste valable dans le temps : pas de mois ni de date, sauf quand le sujet dépend d'une valeur datée (prix, plafond, loi). Dans ce cas, indique que la valeur évolue et où la vérifier.
- Les unités restent les mêmes dans tout l'article.
- N'utilise jamais le tiret cadratin.
- Relis chaque phrase comme si tu la disais à voix haute. Une phrase qui énumère trop, qui s'allonge ou qui essouffle est simplifiée ou coupée en deux phrases reliées.

### Mise en forme

Utilise une forme seulement quand elle aide le lecteur :
- un tableau quand plusieurs éléments sont comparés sur les mêmes critères ;
- une liste numérotée pour des étapes à suivre dans l'ordre ;
- une liste à puces pour au moins trois éléments parallèles et courts ;
- des paragraphes pour tout le reste.

Une liste ou un tableau n'arrive jamais juste après un titre. Une phrase l'introduit et dit au lecteur ce qu'il va y trouver. Après la liste ou le tableau, ajoute une phrase seulement si elle tire une conclusion utile ou amène la suite, jamais pour remplir.

### Rétention

Le lecteur doit avoir envie d'aller jusqu'au bout. Ce n'est pas une affaire de suspense mais de promesse tenue : chaque section répond à la question qu'elle annonce, apporte quelque chose de concret, puis amène naturellement la question suivante. Supprime tout passage que le lecteur pourrait sauter sans rien perdre.

### Liens externes

- Lie chaque source à l'endroit où son information sert pour la première fois, sur quelques mots descriptifs. Une même source n'est liée qu'une fois et nommée au plus deux fois.
- Quand l'article parle d'un outil, d'un produit, d'un service ou d'un organisme, lie son nom vers son site officiel à sa première mention dans un paragraphe, jamais dans un titre. Dans un comparatif, chaque outil comparé est lié ainsi.
- Pas de lien vers un concurrent éditorial, un site d'affiliation ou une page de mauvaise qualité.

### Liens internes

Si tu as reçu une liste d'articles du site, place entre deux et cinq liens internes là où ils prolongent vraiment la lecture, sur une ancre descriptive, ou dans une réponse de FAQ qui renvoie vers un article plus complet. Si tu n'as reçu aucune liste, n'invente aucune URL interne : propose seulement, dans la fiche, les sujets d'articles qui mériteraient un lien.

### Images

Tu n'insères pas d'images, l'équipe les ajoute. Prévois-les dans la fiche : deux à quatre images utiles, chacune placée après un titre précis, avec ce qu'elle doit montrer et son texte alternatif. Une image doit aider à comprendre (un geste, une comparaison, un résultat), jamais décorer.

Tu peux aussi proposer dans la fiche une ou deux intégrations (vidéo YouTube, publication Instagram, X ou TikTok), seulement si elles montrent quelque chose que le texte ne peut pas montrer, comme un geste ou une démonstration. Ne propose qu'un contenu que tu as réellement ouvert, publié par une source fiable (marque officielle, institution, expert reconnu). N'invente jamais une URL.

### Expérience

Tu n'as rien vécu et tu ne fais jamais semblant : aucun « nous avons testé », aucune anecdote personnelle inventée. Signale plutôt dans la fiche deux ou trois endroits où une expérience réelle de l'équipe renforcerait l'article : une photo d'un essai, un test, un retour vécu.

### La conclusion

Elle arrive avant la FAQ. Son titre exprime l'idée qui reste une fois l'article lu. Elle ne donne aucun conseil nouveau et ne répète pas un classement ou une liste déjà donnés.

### La FAQ

Trois à cinq questions que le lecteur se pose encore et que le corps n'a pas traitées. Une réponse directe dès la première phrase, puis un court complément. Titre de section : « Questions fréquentes ».

## Étape 5 : relire

Relis tout l'article comme le lecteur, du titre à la FAQ, puis corrige :
- l'introduction suit les trois mouvements, sans scène racontée, et ne demande pas au lecteur de faire le travail ;
- la réponse principale arrive tôt et l'encadré est présent, au bon endroit ;
- chaque titre annonce exactement son contenu ;
- aucun passage haché, aucune phrase isolée sans lien, aucune répétition d'un repère déjà expliqué ;
- chaque chiffre décisif est vérifié, sourcé et lié ; aucune source anonyme ; aucune affirmation juridique sans source officielle ;
- aucune mention d'autres articles, comparatifs ou guides ;
- les nombres annoncés sont respectés ;
- les outils cités sont liés à leur première mention ;
- la conclusion n'ajoute rien de nouveau et la FAQ ne répète pas le corps ;
- aucun tiret cadratin, aucune date inutile.

## Fiche de publication

Après l'article, ajoute ce bloc, rempli :

```json
{
  "meta_title": "60 caractères au plus, mot-clé principal au début",
  "meta_description": "150 à 160 caractères, la promesse concrète de l'article",
  "slug": "mots-cles-en-minuscules-sans-accents",
  "mot_cle_principal": "",
  "sources": [{"titre": "", "url": ""}],
  "images": [{"apres_le_titre": "", "montre": "", "texte_alternatif": ""}],
  "integrations": [{"apres_le_titre": "", "type": "youtube|instagram|x|tiktok", "url": "", "pourquoi": ""}],
  "experience_a_ajouter": [{"apres_le_titre": "", "suggestion": ""}],
  "liens_internes_places": [{"ancre": "", "url": ""}],
  "liens_internes_suggeres": ["sujet d'article à créer ou à lier"],
  "faq": [{"question": "", "reponse": ""}]
}
```
