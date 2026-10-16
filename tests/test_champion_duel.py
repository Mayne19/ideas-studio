import json
import random

from app.services.seo.champion_duel import DUEL_CRITERIA, pick_champion, run_duel


def test_pick_champion_skips_videos_forums_and_own_site():
    organic = [
        {"link": "https://www.youtube.com/watch?v=1"},
        {"link": "https://theslash.fr/a"},
        {"link": "https://www.reddit.com/r/x"},
        {"link": "https://www.codeur.com/blog/prix-site-vitrine/", "title": "Prix", "position": 4},
    ]
    assert pick_champion(organic, exclude_hosts=("theslash.fr",))["url"].startswith("https://www.codeur.com")


def test_duel_cancels_position_and_detects_win():
    def judge(prompt, step, temperature):
        # Le juge préfère toujours l'article qui contient « OURS », où qu'il soit.
        a_is_ours = prompt.index("OURS") < prompt.index("CHAMP")
        good, bad = {k: 9 for k in DUEL_CRITERIA}, {k: 6 for k in DUEL_CRITERIA}
        ours_side = "A" if a_is_ours else "B"
        return json.dumps({"scores": {"A": good if a_is_ours else bad, "B": bad if a_is_ours else good},
                           "publish": ours_side, "reader_prefers": ours_side, "ai_cites": ours_side})

    result = run_duel("OURS texte", "CHAMP texte", "kw", "q", [("j", judge)], rng=random.Random(1))
    assert result["valid_rounds"] == 2 and result["won"] and result["publish_rate"] == 1.0
    assert result["losing_criteria"] == []
