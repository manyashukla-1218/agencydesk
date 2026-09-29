from tests.conftest import auth_headers


def test_client_cannot_see_internal_task_in_list(client, world):
    r = client.get(f"/projects/{world['project_a'].id}/tasks", headers=auth_headers(world["client_a_token"]))
    assert r.status_code == 200
    titles = [t["title"] for t in r.json()]
    assert "Internal task" not in titles
    assert "Client-visible task" in titles


def test_client_cannot_fetch_internal_task_by_id_directly(client, world):
    r = client.get(f"/tasks/{world['internal_task'].id}", headers=auth_headers(world["client_a_token"]))
    assert r.status_code == 404


def test_client_cannot_bypass_visibility_via_search_filter(client, world):
    # The exact "search, filters ... easy to miss" case from the brief.
    r = client.get(
        f"/projects/{world['project_a'].id}/tasks",
        params={"q": "Internal"},
        headers=auth_headers(world["client_a_token"]),
    )
    assert r.status_code == 200
    assert r.json() == []


def test_client_cannot_bypass_visibility_via_status_filter(client, world, db):
    from app import models

    r = client.get(
        f"/projects/{world['project_a'].id}/tasks",
        params={"status_filter": models.TaskStatus.todo.value},
        headers=auth_headers(world["client_a_token"]),
    )
    assert r.status_code == 200
    ids = [t["id"] for t in r.json()]
    assert str(world["internal_task"].id) not in ids


def test_client_cannot_see_internal_comment_on_a_visible_task(client, world, db):
    from app import models

    db.add(models.Comment(task_id=world["visible_task"].id, agency_id=world["agency_a"].id,
                           author_id=world["member_a_user"].id, body="internal-only note", is_client_visible=False))
    db.add(models.Comment(task_id=world["visible_task"].id, agency_id=world["agency_a"].id,
                           author_id=world["member_a_user"].id, body="hello client", is_client_visible=True))
    db.commit()

    r = client.get(f"/tasks/{world['visible_task'].id}/comments", headers=auth_headers(world["client_a_token"]))
    assert r.status_code == 200
    bodies = [c["body"] for c in r.json()]
    assert "internal-only note" not in bodies
    assert "hello client" in bodies


def test_client_cannot_see_time_entries(client, world):
    r = client.get(f"/tasks/{world['visible_task'].id}/time-entries", headers=auth_headers(world["client_a_token"]))
    assert r.status_code == 403


def test_dashboard_counts_exclude_internal_tasks_for_client(client, world):
    r = client.get(f"/projects/{world['project_a'].id}/dashboard", headers=auth_headers(world["client_a_token"]))
    assert r.status_code == 200
    body = r.json()
    # Only the one client-visible task should be counted.
    assert sum(body["task_counts_by_status"].values()) == 1
    assert body["total_hours_logged"] is None  # clients never see raw hours


def test_client_cannot_create_task(client, world):
    r = client.post(
        f"/projects/{world['project_a'].id}/tasks",
        json={"title": "client trying to sneak in a task"},
        headers=auth_headers(world["client_a_token"]),
    )
    assert r.status_code == 403
