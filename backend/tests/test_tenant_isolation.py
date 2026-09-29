from tests.conftest import auth_headers


def test_agency_b_cannot_read_agency_a_task_by_id(client, world):
    r = client.get(f"/tasks/{world['internal_task'].id}", headers=auth_headers(world["admin_b_token"]))
    # 404, not 403: we never confirm the ID exists in someone else's tenant.
    assert r.status_code == 404


def test_agency_b_cannot_write_agency_a_task(client, world):
    r = client.patch(
        f"/tasks/{world['internal_task'].id}",
        json={"title": "hijacked"},
        headers=auth_headers(world["admin_b_token"]),
    )
    assert r.status_code == 404


def test_agency_b_project_list_never_contains_agency_a_projects(client, world):
    r = client.get("/projects", headers=auth_headers(world["admin_b_token"]))
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()]
    assert str(world["project_a"].id) not in ids
    assert str(world["project_b"].id) in ids


def test_guessing_a_valid_task_id_from_another_tenant_via_query_params_fails(client, world):
    # Even scoping through the "right" project route, a cross-tenant task id
    # must not leak through a filter/search parameter.
    r = client.get(
        f"/projects/{world['project_b'].id}/tasks",
        params={"q": "Internal task"},
        headers=auth_headers(world["admin_a_token"]),
    )
    # project_b isn't even visible to agency A -> 404 at the project check
    assert r.status_code == 404


def test_agency_member_only_sees_their_assigned_projects(client, world, db):
    from app import models

    # member_a is on project_a's team but not on some other project_a2
    other_project = models.Project(agency_id=world["agency_a"].id, client_id=world["client_a"].id, name="Not assigned")
    db.add(other_project)
    db.commit()

    r = client.get("/projects", headers=auth_headers(world["member_a_token"]))
    ids = [p["id"] for p in r.json()]
    assert str(world["project_a"].id) in ids
    assert str(other_project.id) not in ids
