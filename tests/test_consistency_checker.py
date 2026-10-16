"""Contrôle de cohérence : tests hors ligne avec un faux provider."""
import json

from app.services.seo.consistency_checker import apply_consistency_fixes, check_and_fix_consistency
from app.services.seo.section_writer import extract_h2_texts

DUPLICATE = "Le bon choix dépend surtout du temps que vous voulez consacrer à la maintenance."
ARTICLE = (
    "<p>Un site vitrine coûte entre 1 500 et 2 000 € chez un freelance. " + DUPLICATE + "</p>\n"
    "<h2>Les prix réels</h2>\n"
    "<p>" + DUPLICATE + " Un freelance facture un site vitrine entre 1 500 et 3 000 € selon le nombre "
    "de pages et les intégrations.</p>\n"
    "<p>Une agence demande <strong>souvent plus de 5 000 €</strong> pour le même périmètre.</p>\n"
    "<h2>Le SEO</h2>\n"
    "<p>Les deux outils gèrent les balises essentielles, "
    "<a href=\"https://fr.wikipedia.org/wiki/WordPress\">WordPress passe par une extension</a> pour cela.</p>\n"
)

ISSUES = [
    {
        "type": "contradiction",
        "sentence": "Un site vitrine coûte entre 1 500 et 2 000 € chez un freelance.",
        "action": "replace",
        "replacement": "Un site vitrine coûte entre 1 500 et 3 000 € chez un freelance.",
        "related_sentence": "Un freelance facture un site vitrine entre 1 500 et 3 000 €",
        "reason": "fourchette différente entre l'introduction et la section prix",
    },
    {
        "type": "duplicate",
        "sentence": DUPLICATE,  # présente deux fois : ambiguë, doit être ignorée
        "action": "remove",
        "replacement": "",
    },
]


def fake_call(issues):
    def _call(prompt: str, step: str, temperature: float) -> str:
        assert step == "ConsistencyCheck"
        assert "INTRODUCTION" in prompt and "SECTION « Les prix réels »" in prompt
        return "```json\n" + json.dumps({"issues": issues}, ensure_ascii=False) + "\n```"
    return _call


def test_contradiction_is_fixed_by_targeted_replacement():
    content, report = check_and_fix_consistency(ARTICLE, fake_call(ISSUES[:1]))
    assert "entre 1 500 et 2 000 €" not in content
    assert "Un site vitrine coûte entre 1 500 et 3 000 € chez un freelance." in content
    assert report["issues_found"] == 1
    assert report["applied"][0]["before"] == ISSUES[0]["sentence"]
    # Rien d'autre n'a bougé.
    assert content.replace("1 500 et 3 000 € chez", "1 500 et 2 000 € chez") == ARTICLE


def test_ambiguous_duplicate_sentence_is_skipped_not_guessed():
    content, report = check_and_fix_consistency(ARTICLE, fake_call(ISSUES))
    assert content.count(DUPLICATE) == 2
    assert len(report["applied"]) == 1
    assert report["skipped"][0]["skipped_because"].startswith("phrase introuvable")


def test_duplicate_removed_when_located_exactly_once():
    # La section reprend la phrase de l'introduction avec une amorce : le
    # modèle cite l'occurrence de la section, unique dans l'article.
    sentence = "En pratique, le bon choix dépend surtout du temps que vous voulez consacrer à la maintenance."
    article = ARTICLE.replace("<p>" + DUPLICATE + " Un freelance", "<p>" + sentence + " Un freelance", 1)
    padding = "<p>" + " ".join(["Chaque outil a ses forces selon le projet."] * 20) + "</p>\n"
    article = article.replace("<h2>Le SEO</h2>", padding + "<h2>Le SEO</h2>")
    assert article.count(sentence) == 1
    content, applied, skipped = apply_consistency_fixes(article, [
        {"type": "duplicate", "sentence": sentence, "action": "remove", "replacement": ""},
    ])
    assert sentence not in content
    assert "<p>Un freelance facture un site vitrine" in content
    assert len(applied) == 1 and not skipped


def test_never_touches_headings_links_or_html_replacements():
    issues = [
        {"type": "contradiction", "sentence": "Les prix réels", "action": "replace", "replacement": "Les tarifs"},
        {"type": "contradiction", "sentence": "Les deux outils gèrent les balises essentielles, WordPress passe par une extension pour cela.",
         "action": "remove", "replacement": ""},
        {"type": "contradiction", "sentence": "Une agence demande souvent plus de 5 000 € pour le même périmètre.",
         "action": "replace", "replacement": "Une agence demande <b>4 000 €</b> pour le même périmètre."},
    ]
    content, applied, skipped = apply_consistency_fixes(ARTICLE, issues)
    assert content == ARTICLE
    assert applied == []
    assert len(skipped) == 3


def test_sentence_with_inline_bold_can_be_replaced():
    issues = [{
        "type": "contradiction",
        "sentence": "Une agence demande souvent plus de 5 000 € pour le même périmètre.",
        "action": "replace",
        "replacement": "Une agence demande souvent plus de 4 000 € pour le même périmètre.",
    }]
    content, applied, _ = apply_consistency_fixes(ARTICLE, issues)
    assert "plus de 4 000 €" in content and "5 000" not in content
    assert extract_h2_texts(content) == extract_h2_texts(ARTICLE)
    assert len(applied) == 1


def test_removing_too_much_text_reverts_all_fixes():
    issues = [{
        "type": "duplicate",
        "sentence": "Une agence demande souvent plus de 5 000 € pour le même périmètre.",
        "action": "remove",
        "replacement": "",
    }]
    content, applied, skipped = apply_consistency_fixes(ARTICLE, issues)
    assert content == ARTICLE
    assert applied == []
    assert skipped[0]["skipped_because"] == "trop de texte supprimé au total"


def test_invalid_json_leaves_article_unchanged():
    content, report = check_and_fix_consistency(ARTICLE, lambda p, s, t: "pas de JSON ici")
    assert content == ARTICLE
    assert report["error"] == "réponse JSON invalide"


def test_prompt_covers_unsupported_claims_and_uses_many_facts():
    from app.services.seo.consistency_checker import build_consistency_prompt

    facts = [f"fait {i}" for i in range(40)]
    prompt = build_consistency_prompt("<p>Un texte assez long pour être lu.</p>", facts)
    assert "non étayées" in prompt and '"unsupported"' in prompt and "fragment" in prompt
    assert "fait 29" in prompt and "fait 30" not in prompt


def test_unsupported_claim_removal_is_applied():
    from app.services.seo.consistency_checker import apply_consistency_fixes

    html = ("<h2>Réserver</h2><p>Réservez pour deux ans. Cela signale aux moteurs de recherche que votre site "
            "est stable et durable. Activez le renouvellement automatique chez votre registraire.</p>"
            + "<p>" + "Vérifiez les coordonnées de contact et verrouillez le transfert du domaine. " * 25 + "</p>")
    issue = {"type": "unsupported", "action": "remove",
             "sentence": "Cela signale aux moteurs de recherche que votre site est stable et durable."}
    out, applied, skipped = apply_consistency_fixes(html, [issue])
    assert applied and "moteurs" not in out and "renouvellement" in out
