from app.services import production_queue


def test_production_queue_exposes_queue_helpers():
    assert callable(production_queue.claim_for_writing)
