from app.services.seo.section_proofreader import proofread_article

ARTICLE = (
    "<p>Un basilic acheté en pot meurt souvent en quelques jours, car les plants sont trop serrés dans un "
    "petit pot de supermarché.</p>"
    "<h2>Trop d'eau ou pas assez</h2><p>Les feuilles jaunes et molles signalent un excès d'eau dans le pot. "
    "Ajouter de l'eau à ce moment-là, en croyant bien faire, achève souvent la plante en 3 jours.</p>"
)


def test_inverted_sentence_is_rewritten():
    def fake(prompt, step, temperature):
        if "Ajouter de l'eau" in prompt.split("Extrait :\n", 1)[1]:
            return ("<h2>Trop d'eau ou pas assez</h2><p>Les feuilles jaunes et molles signalent un excès d'eau "
                    "dans le pot. Si vous ajoutez de l'eau à ce moment-là, vous tuez la plante en 3 jours.</p>")
        return prompt.split("Extrait :\n", 1)[1]

    out, report = proofread_article(ARTICLE, fake, mode="clarity")
    assert "Si vous ajoutez de l'eau" in out and report["corrected"] == 1


def test_changed_figures_are_rejected_and_original_kept():
    def fake(prompt, step, temperature):
        if "Ajouter de l'eau" in prompt.split("Extrait :\n", 1)[1]:
            return ("<h2>Trop d'eau ou pas assez</h2><p>Les feuilles jaunes et molles signalent un excès d'eau "
                    "dans le pot. Si vous ajoutez de l'eau à ce moment-là, vous tuez la plante en 5 jours.</p>")
        return prompt.split("Extrait :\n", 1)[1]

    out, report = proofread_article(ARTICLE, fake, mode="clarity")
    assert "achève souvent la plante en 3 jours" in out and report["rejected"] == 1
