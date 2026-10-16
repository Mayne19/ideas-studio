from app.services.seo.french_typography import NBSP, fix_french_text, fix_french_typography


def test_adds_nbsp_before_double_punctuation():
    assert fix_french_text("coûts cachés: rédaction") == f"coûts cachés{NBSP}: rédaction"
    assert fix_french_text("en 2026? Oui!") == f"en 2026{NBSP}? Oui{NBSP}!"
    assert fix_french_text("a ; b") == f"a{NBSP}; b"


def test_keeps_times_ratios_and_urls():
    assert fix_french_text("à 14:30 en 16:9") == "à 14:30 en 16:9"
    assert fix_french_text("voir https://x.fr/a?b=1 ici") == "voir https://x.fr/a?b=1 ici"


def test_quotes_and_tags_untouched():
    html = '<p>Il dit «bonjour» : <a href="https://x.fr/?q=1">lien</a>?</p>'
    out = fix_french_typography(html)
    assert f"«{NBSP}bonjour{NBSP}»{NBSP}:" in out
    assert '<a href="https://x.fr/?q=1">' in out
    assert out.endswith(f"</a>?</p>") or out.endswith(f"</a>{NBSP}?</p>")


def test_idempotent():
    once = fix_french_text("Pourquoi? Parce que: voilà.")
    assert fix_french_text(once) == once


def test_title_case_is_lowered_except_proper_nouns():
    from app.services.seo.french_typography import fix_title_case

    body = "Avec Webflow ou avec WordPress, le choix dépend de France Num et du budget."
    assert fix_title_case("Le Coût Réel d'un Site Vitrine Professionnel en 2026", body) == \
        "Le coût réel d'un site vitrine professionnel en 2026"
    assert fix_title_case("Webflow Ou WordPress Pour Un Freelance Exigeant", body) == \
        "Webflow ou WordPress pour un freelance exigeant"
    assert fix_title_case("Site vitrine : le vrai budget en 2026", body) == "Site vitrine : le vrai budget en 2026"
