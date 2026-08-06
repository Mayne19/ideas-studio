from __future__ import annotations

from app.schemas.seo_workflow import IntentAnalysis, asdict


def analyze_intent(
    title: str,
    keyword: str,
    context_hint: str | None = None,
    category_name: str | None = None,
    idea_discovery: dict | None = None,
    project_context: dict | None = None,
) -> IntentAnalysis:
    title_lower = (title or "").lower()
    keyword_lower = (keyword or "").lower()
    hint_lower = (context_hint or "").lower()
    category_lower = (category_name or "").lower()

    analysis = IntentAnalysis(
        explicit_intent="informational",
        reader_real_question=title,
        expected_answer="",
        first_block_goal="",
    )

    # ── Scoring multi-dimension : chaque intention est notée 0-1 à partir de
    # marqueurs lexicaux (titre, mot-clé, contexte, catégorie). La dimension
    # dominante pilote le type d'article ; commercial_intent_score indique
    # séparément le poids d'intention transactionnelle pour le SEO.
    text_combined = " ".join([title_lower, keyword_lower, hint_lower, category_lower])

    dims = {
        "informational": [
            "quoi", "qu'est-ce", "comment", "pourquoi", "guide", "tutoriel",
            "conseil", "astuce", "definition", "apprendre", "information",
            "how", "what", "why", "guide", "tutorial", "tips",
        ],
        "commercial": [
            "meilleur", "comparer", "comparaison", "vs", "vs.", "différence",
            "choisir", "avis", "recommandation", "alternative", "test",
            "best", "compare", "review", "vs", "alternatives", "top",
        ],
        "transactional": [
            "acheter", "prix", "tarif", "commander", "abonnement", "offre",
            "télécharger", "essai", "gratuit", "réserver", "inscription",
            "buy", "price", "pricing", "download", "trial", "order", "free",
        ],
        "navigational": [
            "login", "connexion", "compte", "site officiel", "dashboard",
            "console", "sign in", "sign up", "official", "login",
        ],
    }

    intent_scores: dict[str, float] = {}
    for dim, markers in dims.items():
        hits = sum(1 for m in markers if m in text_combined)
        score = min(1.0, hits / 4.0)
        intent_scores[dim] = round(score, 2)

    analysis.intent_scores = intent_scores
    analysis.commercial_intent_score = intent_scores["commercial"]

    dominant = max(intent_scores, key=lambda k: intent_scores[k])
    if intent_scores[dominant] >= 0.25 and dominant != "informational":
        analysis.explicit_intent = dominant

    comparison_markers = ["vs", "ou", "comparer", "différence", "meilleur", "choisir"]
    guide_markers = ["comment", "guide", "tutoriel", "étapes", "créer", "configurer"]
    question_markers = ["quoi", "qu'est-ce", "pourquoi", "quand", "quel", "comment"]

    if intent_scores["commercial"] >= 0.25 or analysis.explicit_intent == "commercial":
        analysis.article_type = "comparison"
        analysis.first_block_goal = "Cadrer les critères de comparaison pour aider le lecteur à comprendre les différences essentielles."
        analysis.recommended_angle = "Comparer objectivement les options disponibles."
    elif intent_scores["transactional"] >= 0.25:
        analysis.article_type = "transactional"
        analysis.first_block_goal = "Présenter directement les options, prix et conditions pour aider à décider."
        analysis.recommended_angle = "Présentation claire des options et de leurs différences."
    elif analysis.explicit_intent == "navigational" or intent_scores["navigational"] >= 0.25:
        analysis.article_type = "navigational"
        analysis.first_block_goal = "Aider le lecteur à trouver rapidement la ressource ou la page recherchée."
        analysis.recommended_angle = "Orientation directe vers la ressource recherchée."
    elif any(m in title_lower or m in keyword_lower for m in guide_markers):
        analysis.article_type = "guide"
        analysis.first_block_goal = "Donner une première action utile que le lecteur peut appliquer immédiatement."
        analysis.recommended_angle = "Guide pratique avec étapes concrètes."
    elif any(m in title_lower or m in keyword_lower for m in question_markers):
        analysis.article_type = "simple_question"
        analysis.first_block_goal = "Répondre directement à la question principale du lecteur."
        analysis.recommended_angle = "Réponse claire et directe avec explications."
    else:
        analysis.first_block_goal = "Présenter le sujet et donner une première information utile au lecteur."
        analysis.recommended_angle = "Contenu informatif complet et utile."

    analysis.implicit_intent = f"Le lecteur cherche des informations pratiques et fiables sur {keyword or title}"
    analysis.expected_answer = f"Un guide complet expliquant {keyword or title} avec des conseils pratiques"
    analysis.sub_questions = [
        f"Qu'est-ce que {keyword or title} ?",
        f"Pourquoi {keyword or title} est-il important ?",
        f"Comment appliquer {keyword or title} concrètement ?",
    ]
    analysis.what_to_avoid = [
        "Réponse trop générique sans conseil pratique",
        "Contenu trop technique sans explication",
        "Absence d'exemples concrets",
    ]

    return analysis


def analyze_intent_dict(
    title: str,
    keyword: str,
    context_hint: str | None = None,
    category_name: str | None = None,
    idea_discovery: dict | None = None,
    project_context: dict | None = None,
) -> dict:
    return asdict(analyze_intent(title, keyword, context_hint, category_name, idea_discovery, project_context))


def refine_intent_with_research(
    base: dict,
    title: str,
    keyword: str,
    research_brief: dict | None = None,
    db=None,
    project_id: str | None = None,
) -> dict:
    """Affine l'analyse d'intention heuristique avec un jugement LLM appuyé sur
    les VRAIS résultats SERP du research brief (titres + snippets concurrents).
    Point 9 du pipeline : l'heuristique seule inférait l'intention depuis des
    marqueurs lexicaux du titre ; elle ignore ce que la SERP montre réellement
    (type de pages classées, questions posées par les concurrents). Repli
    systématique sur l'analyse de base si aucun provider n'est disponible —
    jamais bloquant, toujours un enrichissement."""
    result = dict(base)
    if db is None:
        return result
    try:
        from app.services.agents.agent_router import get_router
    except Exception:
        return result
    router = get_router(db)
    if router is None:
        return result
    try:
        provider = router.get_provider("intent_analysis", project_id=project_id)
        if provider is None or provider.is_mock:
            return result
    except Exception:
        return result

    sources = (research_brief or {}).get("sources_consulted") or []
    serp_context = ""
    if sources:
        lines = []
        for source in sources[:10]:
            if isinstance(source, dict):
                snippet = (source.get("snippet") or "")[:200]
                lines.append(f"- {source.get('title', '')} — {snippet}")
        serp_context = "\n".join(lines)

    prompt = (
        "Analyse l'intention de recherche réelle derrière ce sujet d'article en t'appuyant sur "
        "les résultats Google réels (SERP) ci-dessous. Détermine : explicit_intent (informational|"
        "commercial|transactional|navigational), article_type (evergreen_information|guide|"
        "comparison|transactional|navigational|simple_question), la vraie question du lecteur, "
        "la réponse attendue, les sous-questions à traiter, l'angle recommandé et ce qu'il faut "
        "éviter (ce que les concurrents ratent).\n\n"
        f"Titre : {title}\nMot-clé : {keyword}\n\n"
        + (f"Résultats SERP réels :\n{serp_context}\n\n" if serp_context else "Aucun résultat SERP disponible.\n\n")
        + "Réponds UNIQUEMENT avec un JSON valide :\n"
        '{"explicit_intent": "...", "article_type": "...", "reader_real_question": "...", '
        '"expected_answer": "...", "sub_questions": ["...", "..."], "first_block_goal": "...", '
        '"recommended_angle": "...", "what_to_avoid": ["...", "..."]}'
    )
    try:
        refined = provider.generate_json(prompt, schema_hint="json intent analysis object")
    except Exception:
        return result
    if not isinstance(refined, dict):
        return result

    for field in ("explicit_intent", "article_type", "reader_real_question", "expected_answer",
                  "first_block_goal", "recommended_angle"):
        value = refined.get(field)
        if isinstance(value, str) and value.strip():
            result[field] = value.strip()
    for list_field in ("sub_questions", "what_to_avoid"):
        value = refined.get(list_field)
        if isinstance(value, list) and value:
            result[list_field] = [str(x) for x in value if str(x).strip()][:8]
    result["refined_by_llm"] = True
    if isinstance(result.get("intent_scores"), dict):
        result["intent_scores"] = dict(result["intent_scores"])
    return result
