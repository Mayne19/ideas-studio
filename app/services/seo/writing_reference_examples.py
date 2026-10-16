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
    },
]


def build_reference_examples_block(count: int = 1) -> str:
    """Sélectionne `count` exemple(s) (le premier par défaut) à insérer dans
    le prompt — un seul exemple complet est plus efficace qu'un résumé des
    trois : le LLM a besoin de voir un pattern complet respecté de bout en
    bout, pas une liste de fragments désunis."""
    examples = REFERENCE_EXAMPLES[:count]
    parts = [
        "Exemple validé par le rédacteur en chef : introduction en trois temps (réponse directe adaptée au but "
        "du lecteur, problème concret, annonce en une phrase de ce qu'il va obtenir), phrases reliées les unes aux "
        "autres, chaque fait suivi de ce qu'il change pour le lecteur. Imite le ton, le fil et la clarté, jamais "
        "le sujet ni les exemples.",
    ]
    for ex in examples:
        parts.append(f"\n--- Exemple (sujet original : {ex['subject']}) ---\n{ex['excerpt']}\n--- Fin de l'exemple ---")
    return "\n".join(parts)
