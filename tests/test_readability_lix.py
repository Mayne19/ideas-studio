from app.services.seo.readability_service import lix_to_score


def test_french_reference_blogs_score_fairly():
    # codeur.com / nocodefactory.fr mesurés entre LIX 45 et 53
    assert lix_to_score(45) == 80
    assert lix_to_score(48) == 70
    assert lix_to_score(53) == 55


def test_clearer_text_scores_higher():
    assert lix_to_score(38) > lix_to_score(44) > lix_to_score(49) > lix_to_score(58)
