from types import SimpleNamespace

from app.services.seo.plagiarism_check import (
    MAX_SENTENCES,
    SerpPlagiarismBackend,
    check_plagiarism,
    extract_sentences,
    plagiarism_fixes,
)

LONG = "Le compost domestique réduit nettement le volume des déchets ménagers jetés chaque semaine à la poubelle."
COPIED = ("Les épluchures de légumes se décomposent en quelques semaines lorsque le tas reste humide "
          "et bien aéré.")


def _search_returning(results):
    calls = []

    def search(query, limit):
        calls.append(query)
        return results
    return search, calls


def test_extract_skips_headings_tables_and_quotes():
    content = (
        f"<h2>{LONG}</h2>"
        f"<table><tr><td>{LONG}</td></tr></table>"
        f"<blockquote><p>{LONG}</p></blockquote>"
        f"<ul><li>{COPIED}</li></ul>"
    )
    assert extract_sentences(content) == [COPIED]


def test_extract_requires_twelve_words():
    content = "<p>Phrase courte de six mots ici.</p><p>" + LONG + "</p>"
    assert extract_sentences(content) == [LONG]


def test_extract_samples_every_150_words_and_caps():
    paragraphs = "".join(f"<p>{LONG}</p>" for _ in range(200))
    picked = extract_sentences(paragraphs)
    assert len(picked) == MAX_SENTENCES
    # ~16 mots par phrase : une phrase retenue sur 10 environ, pas toutes.
    assert len(extract_sentences(paragraphs, max_sentences=100)) < 30


def test_match_on_ten_consecutive_words():
    snippet = "Selon le guide, les epluchures de légumes se décomposent en quelques semaines lorsque le tas reste."
    search, calls = _search_returning([{"title": "Guide", "link": "https://autre-site.fr/compost", "snippet": snippet}])
    report = check_plagiarism(f"<p>{COPIED}</p>", SerpPlagiarismBackend(search))
    assert calls == [f'"{COPIED}"']
    assert report["status"] == "plagiarism"
    match = report["matches"][0]
    assert match["url"] == "https://autre-site.fr/compost"
    assert match["matched_count"] >= 10


def test_nine_words_is_not_a_match():
    snippet = "les épluchures de légumes se décomposent en quelques semaines, puis autre chose"
    search, _ = _search_returning([{"title": "", "url": "https://autre-site.fr", "snippet": snippet}])
    report = check_plagiarism(f"<p>{COPIED}</p>", SerpPlagiarismBackend(search))
    assert report["status"] == "clean"
    assert report["matches"] == []


def test_no_match_no_blocker_material():
    search, _ = _search_returning([{"title": "Autre", "url": "https://x.fr", "snippet": "Rien à voir avec le texte."}])
    report = check_plagiarism(f"<p>{COPIED}</p>", SerpPlagiarismBackend(search))
    assert report["status"] == "clean"
    assert report["sentences"] == [COPIED]


def test_own_domain_results_ignored():
    search, _ = _search_returning([{"title": "", "link": "https://www.mon-site.fr/blog/compost", "snippet": COPIED}])
    backend = SerpPlagiarismBackend(search, own_domain="https://mon-site.fr")
    assert check_plagiarism(f"<p>{COPIED}</p>", backend)["matches"] == []


def test_skipped_without_backend():
    assert check_plagiarism(f"<p>{COPIED}</p>", None)["status"] == "skipped"


def test_search_error_is_not_plagiarism():
    def search(query, limit):
        raise RuntimeError("quota")
    report = check_plagiarism(f"<p>{COPIED}</p>", SerpPlagiarismBackend(search))
    assert report["status"] == "clean"
    assert report["errors"]


def test_fixes_target_containing_section():
    content = f"<p>Intro.</p><h2>Compost</h2><p>{COPIED}</p>"
    fixes = plagiarism_fixes(content, [COPIED])
    assert fixes == [{"section": "Compost",
                      "instructions": f"Reformule entièrement cette phrase, même sens, autres mots : « {COPIED} »"}]


