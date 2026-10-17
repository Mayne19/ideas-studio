from app.services import production_queue


def test_production_queue_keeps_legacy_writer_helpers_available():
    assert callable(production_queue.write_queued_article)
    assert callable(production_queue.claim_for_writing)
