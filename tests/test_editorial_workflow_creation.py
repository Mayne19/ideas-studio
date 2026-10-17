from app.services.editorial_workflow_service import create_workflow_idea, request_writing


def test_workflow_creation_rejects_an_empty_title():
    try:
        create_workflow_idea(None, "project", "  ")
    except ValueError as exc:
        assert str(exc) == "Le sujet ou le titre est obligatoire."
    else:
        raise AssertionError("An empty title must be rejected before database access")


def test_request_writing_supports_a_caller_owned_transaction():
    assert "commit" in request_writing.__kwdefaults__
    assert request_writing.__kwdefaults__["commit"] is True
