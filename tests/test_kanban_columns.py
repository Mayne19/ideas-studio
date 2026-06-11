from tests.conftest import register_and_login


def _create_project(client, headers, name="Test Blog"):
    resp = client.post("/projects", json={"name": name}, headers=headers)
    return resp.json()


def test_list_kanban_columns_empty(client):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    resp = client.get(f"/projects/{project['id']}/kanban-columns", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_kanban_column(client):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    resp = client.post(
        f"/projects/{project['id']}/kanban-columns",
        json={"label": "À valider client", "color": "#ff9500"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["label"] == "À valider client"
    assert data["color"] == "#ff9500"
    assert data["status"] == "custom_à_valider_client"
    assert data["sort_order"] == 0
    assert data["project_id"] == project["id"]


def test_create_kanban_column_duplicate_label(client):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    client.post(
        f"/projects/{project['id']}/kanban-columns",
        json={"label": "Doublon"},
        headers=headers,
    )
    resp = client.post(
        f"/projects/{project['id']}/kanban-columns",
        json={"label": "Doublon"},
        headers=headers,
    )
    assert resp.status_code == 409


def test_list_kanban_columns(client):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    client.post(
        f"/projects/{project['id']}/kanban-columns",
        json={"label": "Colonne A", "sort_order": 2},
        headers=headers,
    )
    client.post(
        f"/projects/{project['id']}/kanban-columns",
        json={"label": "Colonne B", "sort_order": 1},
        headers=headers,
    )
    resp = client.get(f"/projects/{project['id']}/kanban-columns", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    # Ordered by sort_order then created_at
    assert data[0]["label"] == "Colonne B"
    assert data[1]["label"] == "Colonne A"


def test_update_kanban_column(client):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    col = client.post(
        f"/projects/{project['id']}/kanban-columns",
        json={"label": "Ma colonne", "color": "#007aff"},
        headers=headers,
    ).json()
    resp = client.patch(
        f"/kanban-columns/{col['id']}",
        json={"label": "Colonne modifiée", "color": "#34c759"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["label"] == "Colonne modifiée"
    assert data["color"] == "#34c759"


def test_delete_kanban_column(client):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    col = client.post(
        f"/projects/{project['id']}/kanban-columns",
        json={"label": "À supprimer"},
        headers=headers,
    ).json()
    resp = client.delete(f"/kanban-columns/{col['id']}", headers=headers)
    assert resp.status_code == 204
    # Verify deleted
    resp = client.get(f"/projects/{project['id']}/kanban-columns", headers=headers)
    assert len(resp.json()) == 0


def test_kanban_column_other_project_not_visible(client):
    headers1 = register_and_login(client, "a@test.com", "pass1234", "A")
    headers2 = register_and_login(client, "b@test.com", "pass1234", "B")
    project1 = _create_project(client, headers1)
    client.post(
        f"/projects/{project1['id']}/kanban-columns",
        json={"label": "Secret"},
        headers=headers1,
    )
    project2 = _create_project(client, headers2)
    resp = client.get(f"/projects/{project2['id']}/kanban-columns", headers=headers2)
    assert resp.status_code == 200
    assert resp.json() == []
