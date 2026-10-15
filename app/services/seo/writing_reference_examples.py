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
        "subject": "Maquette avant de créer un site",
        "excerpt": (
            "<p>Oui, dès que votre site dépasse une page, faites une maquette avant de le développer. "
            "Elle vous oblige à décider du contenu et du parcours du visiteur pendant que les changements "
            "ne coûtent encore rien. Un simple croquis papier suffit souvent pour un site vitrine.</p>\n"
            "<h2>Ce que la maquette vous fait gagner</h2>\n"
            "<p>Déplacer un bouton dans Figma prend quelques secondes. Le déplacer sur un site déjà "
            "développé peut demander des heures, selon la façon dont il a été construit.</p>\n"
            "<p>Le vrai bénéfice est ailleurs : en dessinant une page de services, on découvre vite "
            "qu'on ne sait pas quoi écrire dans certaines sections. Mieux vaut le découvrir sur papier "
            "que la veille de la mise en ligne.</p>\n"
            "<h2>Quel outil choisir</h2>\n"
            "<ul>\n"
            "<li><strong>Papier et stylo</strong> : idéal pour valider la structure en une heure.</li>\n"
            "<li><strong>Figma</strong> : utile dès que vous devez montrer la maquette à quelqu'un.</li>\n"
            "<li><strong>Canva</strong> : à éviter pour un site professionnel, il atteint vite ses limites.</li>\n"
            "</ul>\n"
            "<p>Si vous hésitez, commencez sur papier. Vous passerez à Figma le jour où un client "
            "ou un développeur devra la valider.</p>"
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
        "Exemple de ton et de format attendus (réponse directe dès la première phrase, HTML "
        "simple, phrases concrètes). Imite le ton et la clarté, jamais le sujet ni les exemples.",
    ]
    for ex in examples:
        parts.append(f"\n--- Exemple (sujet original : {ex['subject']}) ---\n{ex['excerpt']}\n--- Fin de l'exemple ---")
    return "\n".join(parts)
