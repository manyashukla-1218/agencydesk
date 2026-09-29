from tests.conftest import auth_headers
from app import models


def test_one_person_two_agencies_same_email_different_roles(client, world, db):
    """Same human, same email, agency_member at A and client_user at B.
    Login must not collapse these into one role, and each token must only
    ever unlock its own tenant.
    """
    shared_user = models.User(
        email="shared@person.test", full_name="Shared Person",
        hashed_password=world["member_a_user"].hashed_password,
    )
    db.add(shared_user)
    db.flush()
    db.add(models.AgencyMembership(user_id=shared_user.id, agency_id=world["agency_b"].id, role=models.AgencyRole.agency_member))
    db.add(models.ClientUser(user_id=shared_user.id, client_id=world["client_a"].id, agency_id=world["agency_a"].id))
    db.commit()

    r = client.post("/auth/login", json={"email": "shared@person.test", "password": "pw"})
    assert r.status_code == 200
    body = r.json()
    assert body["token"] is None  # ambiguous -> must pick a context
    roles = {c["role"] for c in body["contexts"]}
    assert roles == {"agency_member", "client_user"}

    # Selecting the client_user context only grants client-scoped access...
    r2 = client.post(
        "/auth/select-context",
        json={"email": "shared@person.test", "password": "pw", "client_id": str(world["client_a"].id)},
    )
    client_token = r2.json()["token"]
    r3 = client.get(f"/tasks/{world['internal_task'].id}", headers=auth_headers(client_token))
    assert r3.status_code == 404  # internal task at Agency A, invisible to the client role

    # ...while selecting the agency_member context at Agency B cannot reach
    # anything at Agency A.
    r4 = client.post(
        "/auth/select-context",
        json={"email": "shared@person.test", "password": "pw", "agency_id": str(world["agency_b"].id)},
    )
    staff_token = r4.json()["token"]
    r5 = client.get(f"/tasks/{world['internal_task'].id}", headers=auth_headers(staff_token))
    assert r5.status_code == 404


def test_resending_invite_does_not_duplicate_it(client, world):
    payload = {"email": "newclient@x.test", "role": "client_user", "client_id": str(world["client_a"].id)}
    r1 = client.post("/invites", json=payload, headers=auth_headers(world["admin_a_token"]))
    r2 = client.post("/invites", json=payload, headers=auth_headers(world["admin_a_token"]))
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["token"] == r2.json()["token"]
    assert r1.json()["resent"] is False
    assert r2.json()["resent"] is True


def test_accepting_same_invite_twice_does_not_create_two_accounts(client, world, db):
    payload = {"email": "onceonly@x.test", "role": "client_user", "client_id": str(world["client_a"].id)}
    invite_resp = client.post("/invites", json=payload, headers=auth_headers(world["admin_a_token"]))
    token = invite_resp.json()["token"]

    accept_payload = {"token": token, "full_name": "Once Only", "password": "pw123456"}
    r1 = client.post("/invites/accept", json=accept_payload)
    assert r1.status_code == 200

    r2 = client.post("/invites/accept", json=accept_payload)
    # Invite is now marked accepted -> second accept is rejected outright.
    assert r2.status_code == 400

    users = db.query(models.User).filter(models.User.email == "onceonly@x.test").all()
    assert len(users) == 1


def test_removing_member_mid_task_unassigns_but_keeps_history(client, world, db):
    task = world["internal_task"]
    task.assignee_id = world["member_a_user"].id
    db.add(models.TimeEntry(task_id=task.id, agency_id=world["agency_a"].id,
                             user_id=world["member_a_user"].id, duration_minutes=60, note="did some work"))
    db.commit()

    r = client.delete(
        f"/projects/{world['project_a'].id}/members/{world['member_a_user'].id}",
        headers=auth_headers(world["admin_a_token"]),
    )
    assert r.status_code == 200

    db.refresh(task)
    assert task.assignee_id is None  # unassigned, not deleted

    remaining_entries = db.query(models.TimeEntry).filter(models.TimeEntry.task_id == task.id).count()
    assert remaining_entries == 1  # past time entry preserved for the audit trail

    r2 = client.get(f"/projects/{world['project_a'].id}/tasks", headers=auth_headers(world["member_a_token"]))
    # member_a lost project access -> their old project now 404s for them
    assert r2.status_code == 404
