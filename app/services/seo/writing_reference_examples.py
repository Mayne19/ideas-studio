from __future__ import annotations

"""Extraits d'articles de référence cités dans le prompt du writer comme
modèle stylistique à imiter — pas les sujets, pas la structure exacte, mais
le rythme, la voix et la façon de prendre position. Complète les règles
abstraites (checklist qualité 90+) : un LLM imite un pattern qu'on lui
montre bien plus fidèlement qu'il ne respecte une liste de contraintes
négatives au-delà des premiers paragraphes.

Un seul extrait court, en HTML (le format de sortie attendu), qui répond à
la question dès la première phrase. Il ne contient ni tiret cadratin ni
tics de voix (« honnêtement ») : le modèle reproduit ce qu'on lui montre."""

REFERENCE_EXAMPLES = [
    {
        # Article validé par le fondateur (note 90/100 en lecteur), 2026-10-16 :
        # « Créer un questionnaire en ligne : 8 outils comparés ». Introduction
        # en trois temps (réponse directe, problématique concrète, annonce de
        # ce que le lecteur obtient), puis des phrases reliées entre elles.
        "subject": "Créer un questionnaire en ligne (comparatif d'outils)",
        "excerpt": (
            "<p>Pour créer un questionnaire en ligne sans payer ni limiter le nombre de réponses, deux outils "
            "suffisent dans la plupart des cas : Google Forms si vous voulez aller vite, Tally si vous voulez un "
            "rendu plus soigné et des données stockées en Europe. Les six autres outils de ce comparatif ne "
            "deviennent intéressants que dans des situations précises.</p>\n"
            "<p>Le piège se cache dans les versions gratuites. Celle de Typeform, l'un des noms les plus connus du "
            "secteur, s'arrête désormais à 10 réponses par mois. Passé ce seuil, le formulaire se ferme tout seul, "
            "souvent au milieu d'une campagne d'envoi.</p>\n"
            "<p>Ce comparatif vous donne, pour chacun des 8 outils, la vraie limite de sa version gratuite et le "
            "premier prix à payer, puis un modèle de questionnaire prêt à copier.</p>\n"
            "<h2>Comment fonctionne un outil de questionnaire en ligne ?</h2>\n"
            "<p>Un outil de questionnaire en ligne est un site sur lequel vous créez une liste de questions, que "
            "vous envoyez ensuite à d'autres personnes pour recevoir leurs réponses. Pour chaque question, il vous "
            "suffit de choisir son type : choix multiple, note de 1 à 5, case à cocher ou réponse libre.</p>\n"
            "<p>Une fois votre questionnaire créé, l'outil vous donne un lien. Vous partagez ensuite ce lien avec "
            "les personnes que vous voulez interroger : par e-mail, sur WhatsApp ou dans une publication sur les "
            "réseaux sociaux. Vous pouvez aussi le transformer en QR code, puis l'imprimer sur une affiche ou un "
            "flyer à placer dans votre boutique.</p>\n"
            "<p>Chaque fois qu'une personne remplit le questionnaire, sa réponse est enregistrée automatiquement. "
            "Vous n'avez donc rien à recopier : les réponses s'affichent dans un tableau, et la plupart des outils "
            "créent aussi des graphiques pour vous aider à lire les résultats en un coup d'œil.</p>\n"
            "<h3>Google Forms, le plus simple pour débuter</h3>\n"
            "<p>Google Forms est l'outil le plus simple pour commencer. Il suffit d'avoir un compte Google, le même "
            "que pour Gmail, et vous pouvez publier votre premier questionnaire en une dizaine de minutes. Le nombre "
            "de questionnaires et de réponses est illimité, et aucune fonction importante n'est réservée à une "
            "version payante.</p>\n"
            "<p>Son principal défaut concerne l'apparence. Les formulaires Google se ressemblent tous et offrent "
            "peu de choix de mise en page. Pour une enquête interne, cela ne pose aucun problème. Pour un "
            "questionnaire envoyé à des clients, le rendu peut en revanche paraître un peu amateur.</p>"
        ),
        "formats": ("comparison", "list"),
    },
    {
        # Deuxième article validé (90/100) : guide pratique / explication.
        "subject": "Sauver un basilic acheté en pot (guide pratique)",
        "formats": ("how_to", "explainer"),
        "excerpt": "<p>Si votre basilic acheté en pot meurt en quelques jours, ce n'est presque jamais de votre faute. Le pot vendu en supermarché contient des dizaines de jeunes plants serrés les uns contre les autres, qui se disputent le peu de terre et d'eau disponibles. Il suffit ensuite d'une nuit trop fraîche ou d'un arrosage de trop pour que tout s'effondre.</p>\n<p>La bonne nouvelle, c'est qu'un basilic qui commence à faner peut presque toujours être sauvé, à condition d'agir vite. Le problème, c'est que les conseils trouvés en ligne se contredisent : certains disent d'arroser tous les jours, d'autres une fois par semaine, certains parlent de plein soleil, d'autres de mi-ombre.</p>\n<p>Ce guide vous aide à repérer ce qui tue votre basilic grâce à l'aspect de ses feuilles, à le sauver en quatre étapes, puis à le garder vert et touffu tout l'été.</p>\n<h2>Pourquoi le basilic du supermarché meurt si vite</h2>\n<p>Le basilic vendu en pot n'a pas été cultivé pour durer chez vous. Les producteurs sèment des dizaines de graines dans un petit pot, puis font pousser les plants sous serre, avec une lumière, un arrosage et un engrais parfaitement contrôlés, d'après le site de jardinage GrowVeg. Le résultat paraît beau en rayon, mais il est pensé pour être vendu, pas pour vivre des mois.</p>\n<p>Une fois chez vous, ces plants perdent d'un coup leurs conditions idéales. Comme ils sont trop nombreux dans trop peu de terre, ils épuisent vite l'eau et les nutriments, et leurs racines forment une motte serrée où elles ne peuvent plus se développer. La Royal Horticultural Society, la grande société britannique d'horticulture, note d'ailleurs que ces pots trop denses tombent souvent malades ou fleurissent très vite.</p>\n<p>Votre basilic ne meurt donc pas parce que vous avez la main moins verte que les autres. Il meurt parce qu'il était déjà à l'étroit au moment de l'achat.</p>",
    },
    {
        # Troisième article validé : chiffres expliqués, exemple calculé.
        "subject": "La règle 50/30/20 pour gérer son budget (explication chiffrée)",
        "formats": ("price_guide", "simple_question"),
        "excerpt": "<p>La règle 50/30/20 consiste à partager l'argent qui arrive sur votre compte chaque mois en trois parts : 50 % pour les dépenses obligatoires, 30 % pour vos envies et 20 % pour l'épargne. Avec 2 000 € par mois, cela donne 1 000 € pour le loyer, les courses et les factures, 600 € pour les sorties et les achats plaisir, et 400 € mis de côté.</p>\n<p>Sur le papier, c'est simple. Dans la vraie vie, beaucoup de gens abandonnent dès le premier mois, parce que leur loyer avale déjà presque la moitié de leur salaire. La plupart des articles s'arrêtent pourtant là, sans dire quoi faire quand les chiffres ne tombent pas juste.</p>\n<p>Ce guide vous montre comment calculer vos trois parts à partir de votre vrai revenu, où classer les dépenses qui posent question et comment adapter la règle quand votre budget ne rentre pas dans les cases, exemple au SMIC à l'appui.</p>\n<h2>D'où vient la règle 50/30/20 et ce qu'elle dit vraiment</h2>\n<p>La règle a été popularisée en 2005 par Elizabeth Warren, aujourd'hui sénatrice américaine, et sa fille Amelia Warren Tyagi dans leur livre <em>All Your Worth</em>. Leur objectif était simple : donner aux familles un repère facile à retenir, sans tableau compliqué ni suivi au centime près.</p>\n<p>Deux détails de la version d'origine changent beaucoup de choses, et la plupart des articles les oublient. D'abord, les pourcentages se calculent sur le revenu après impôts, et non sur le salaire brut. Ensuite, seul le remboursement minimum d'un crédit compte dans les 50 % de besoins : tout ce que vous remboursez en plus entre dans les 20 %, comme le rappelle le site Acorns.</p>\n<p>En France, le premier point est plutôt une bonne nouvelle. Depuis le prélèvement à la source, l'impôt est déjà retiré de votre salaire : le montant qui arrive sur votre compte est donc la bonne base de calcul.</p>",
    },
]


def pick_reference_example(fmt: str = "") -> dict:
    """Exemple validé du même format (comparatif, guide pratique, chiffres),
    sinon le premier."""
    for example in REFERENCE_EXAMPLES:
        if fmt and fmt in example.get("formats", ()):
            return example
    return REFERENCE_EXAMPLES[0]


def build_reference_examples_block(count: int = 1, fmt: str = "") -> str:
    """Sélectionne `count` exemple(s) (le premier par défaut) à insérer dans
    le prompt — un seul exemple complet est plus efficace qu'un résumé des
    trois : le LLM a besoin de voir un pattern complet respecté de bout en
    bout, pas une liste de fragments désunis."""
    examples = [pick_reference_example(fmt)] if fmt else REFERENCE_EXAMPLES[:count]
    parts = [
        "Exemple validé par le rédacteur en chef : introduction en trois temps (réponse directe adaptée au but "
        "du lecteur, problème concret, annonce en une phrase de ce qu'il va obtenir), phrases reliées les unes aux "
        "autres, chaque fait suivi de ce qu'il change pour le lecteur. Imite le ton, le fil et la clarté, jamais "
        "le sujet ni les exemples.",
    ]
    for ex in examples:
        parts.append(f"\n--- Exemple (sujet original : {ex['subject']}) ---\n{ex['excerpt']}\n--- Fin de l'exemple ---")
    return "\n".join(parts)
