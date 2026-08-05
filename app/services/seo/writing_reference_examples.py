from __future__ import annotations

"""Extraits d'articles de référence cités dans le prompt du writer comme
modèle stylistique à imiter — pas les sujets, pas la structure exacte, mais
le rythme, la voix et la façon de prendre position. Complète les règles
abstraites (checklist qualité 90+) : un LLM imite un pattern qu'on lui
montre bien plus fidèlement qu'il ne respecte une liste de contraintes
négatives au-delà des premiers paragraphes.

Issu du guide de rédaction éditorial fourni par l'utilisateur
(guide_redaction_complet.md) — 3 articles jugés 85-88/100 sur la checklist
qualité. Volontairement tronqués (intro + 1-2 sections + conclusion) : un
exemple complet de 900+ mots gonflerait le prompt sans ajouter de valeur
d'imitation par rapport à un extrait représentatif des mêmes patterns."""

REFERENCE_EXAMPLES = [
    {
        "subject": "Maquette de site web",
        "excerpt": (
            "# Comment créer une maquette de site web avant de se lancer\n\n"
            "Beaucoup de projets web échouent non pas à cause du développement, mais à cause de ce qui "
            "n'a pas été pensé avant. La maquette est cette étape qu'on saute trop vite parce qu'on a "
            "hâte de voir le résultat.\n\n"
            "Un site bien maquetté se développe plus vite, génère moins d'allers-retours avec le client, "
            "et répond mieux aux besoins réels de ses utilisateurs. Ce guide montre comment faire ça "
            "correctement.\n\n"
            "## Pourquoi créer une maquette avant de coder\n\n"
            "La raison évidente est le gain de temps. Déplacer un bouton dans Figma prend dix secondes. "
            "Déplacer ce même bouton dans un site déjà développé peut prendre plusieurs heures selon "
            "l'architecture choisie.\n\n"
            "Mais pour être honnête, la raison la plus importante est rarement mentionnée clairement. "
            "La maquette force à prendre des décisions difficiles en amont. Quand on dessine une page de "
            "service, on réalise soudainement qu'on ne sait pas quoi mettre dans la section \"nos "
            "engagements\" parce que personne ne les a jamais vraiment définis.\n\n"
            "## Canva — à éviter pour les projets sérieux\n\n"
            "Canva peut dépanner pour une présentation client très basique. Mais si vous en êtes à "
            "utiliser Canva pour maquetter un site professionnel, c'est probablement le signal que vous "
            "avez besoin d'un prestataire spécialisé plutôt que d'un outil de substitution qui atteindra "
            "ses limites au premier projet un peu complexe.\n\n"
            "## Ce qu'il faut retenir\n\n"
            "Trente minutes de dessin au stylo avant de coder valent mieux que trois semaines de "
            "modifications après la livraison. Ce qui manque rarement, c'est l'outil. Ce qui manque "
            "souvent, c'est la discipline de s'arrêter avant de coder."
        ),
    },
    {
        "subject": "Web design stratégique",
        "excerpt": (
            "# Web design stratégique : comment concevoir un site qui travaille pour vous\n\n"
            "Un site web qui existe sans convertir, c'est une vitrine allumée dans une rue déserte. "
            "Beaucoup d'entrepreneurs l'ont construit, peu savent pourquoi il ne rapporte rien. La "
            "réponse est presque toujours la même : le design a été pensé pour plaire, pas pour "
            "performer.\n\n"
            "C'est précisément ce que le web design stratégique cherche à corriger.\n\n"
            "## Pourquoi la majorité des sites ne convertissent pas\n\n"
            "Honnêtement, la réponse tient en une phrase : ils ont été conçus dans le mauvais ordre.\n\n"
            "La plupart des projets web démarrent par le design. Le client choisit des couleurs, une "
            "police, un style général. Ensuite vient le contenu, souvent rédigé à la hâte pour "
            "\"remplir les espaces\". Et la stratégie, si elle arrive, arrive en dernier, quand tout est "
            "déjà figé.\n\n"
            "Le résultat est prévisible. Un site visuellement cohérent, techniquement fonctionnel, et "
            "commercialement inefficace. Pas parce que le design est mauvais. Parce que personne n'a "
            "réfléchi à son parcours avant de dessiner quoi que ce soit.\n\n"
            "## Les erreurs qui coûtent le plus cher\n\n"
            "**Confondre beau et efficace.** Un site peut être visuellement remarquable et "
            "commercialement nul. L'esthétique sert la performance, pas l'inverse. Quand les deux "
            "entrent en conflit, la performance gagne.\n\n"
            "## Ce qu'il faut retenir\n\n"
            "Un site construit dans cet ordre coûte parfois un peu plus cher au départ. Il coûte presque "
            "toujours beaucoup moins cher sur la durée, parce qu'il n'a pas besoin d'être refait six "
            "mois après le lancement pour corriger ce qui aurait pu être anticipé dès le début."
        ),
    },
    {
        "subject": "Choisir le bon CMS",
        "excerpt": (
            "# Choisir le bon CMS pour votre entreprise\n\n"
            "Changer de CMS une fois le site lancé, c'est en moyenne six semaines de migration, des "
            "données à déplacer, un référencement à reconstruire et un budget qui explose. La plupart "
            "des entrepreneurs qui vivent ça ont tous la même réaction : \"j'aurais dû y réfléchir "
            "avant.\"\n\n"
            "Ce guide est fait pour que vous n'ayez pas à le vivre.\n\n"
            "## Les trois familles de CMS, et ce qu'elles signifient vraiment\n\n"
            "Il existe trois grandes catégories de CMS. Les confondre mène systématiquement au mauvais "
            "choix.\n\n"
            "**Les CMS open source** comme WordPress ou Drupal sont gratuits à l'installation. Mais "
            "gratuit ne veut pas dire sans coût. L'hébergement, les plugins payants, la maintenance, "
            "tout ça s'accumule.\n\n"
            "**Les CMS Headless** comme Strapi ou Contentful séparent complètement la gestion du contenu "
            "de sa présentation visuelle. Honnêtement, si vous n'avez pas d'équipe de développement "
            "dédiée, ce n'est probablement pas votre meilleure option pour démarrer.\n\n"
            "## Ce qu'il faut retenir avant de décider\n\n"
            "Il n'existe pas de meilleur CMS. Il existe le CMS le mieux adapté à votre situation, vos "
            "ressources et vos ambitions.\n\n"
            "La décision la plus coûteuse n'est pas de choisir le mauvais CMS. C'est de ne pas y "
            "réfléchir sérieusement avant de se lancer, et de découvrir ses limites six mois après le "
            "lancement, quand changer de cap coûte dix fois plus cher qu'au départ."
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
        "Voici un extrait d'article jugé conforme au style attendu (85+/100 sur la checklist qualité). "
        "Imite le RYTHME, la VOIX et la façon de PRENDRE POSITION de cet exemple, jamais son sujet, "
        "sa structure exacte de plan, ni ses exemples/situations précis (Canva, Figma, CMS...) s'ils "
        "ne concernent pas le sujet demandé ci-dessous.",
    ]
    for ex in examples:
        parts.append(f"\n--- Exemple (sujet original : {ex['subject']}) ---\n{ex['excerpt']}\n--- Fin de l'exemple ---")
    return "\n".join(parts)
