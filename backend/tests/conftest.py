"""
Tests run against SQLite in-memory rather than Postgres so they need zero
external services to execute (`pytest` just works). The schema and every
query in app/deps.py are plain SQLAlchemy Core/ORM with no Postgres-only
features, so behavior is identical; the one Postgres-only piece (the
partial unique index for invites, migrations/versions/0001_initial.py) is
exercised separately — see test_edge_cases.py::test_invite_race_at_app_layer
docstring for how that's covered here instead.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app import models
from app.security import hash_password, create_session_token

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False))


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db):
    def _get_db_override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def world(db):
    """Two agencies, each with a client, a project, an internal task and a
    client-visible task. Returns a dict of everything tests need, plus
    ready-to-use bearer tokens for each role.
    """
    agency_a = models.Agency(name="Agency A")
    agency_b = models.Agency(name="Agency B")
    db.add_all([agency_a, agency_b])
    db.flush()

    admin_a = models.User(email="admin@a.test", full_name="Admin A", hashed_password=hash_password("pw"))
    member_a = models.User(email="member@a.test", full_name="Member A", hashed_password=hash_password("pw"))
    client_user_a = models.User(email="client@a.test", full_name="Client A", hashed_password=hash_password("pw"))
    admin_b = models.User(email="admin@b.test", full_name="Admin B", hashed_password=hash_password("pw"))
    db.add_all([admin_a, member_a, client_user_a, admin_b])
    db.flush()

    db.add(models.AgencyMembership(user_id=admin_a.id, agency_id=agency_a.id, role=models.AgencyRole.agency_admin))
    db.add(models.AgencyMembership(user_id=member_a.id, agency_id=agency_a.id, role=models.AgencyRole.agency_member))
    db.add(models.AgencyMembership(user_id=admin_b.id, agency_id=agency_b.id, role=models.AgencyRole.agency_admin))

    client_a = models.Client(agency_id=agency_a.id, name="Client of A")
    client_b = models.Client(agency_id=agency_b.id, name="Client of B")
    db.add_all([client_a, client_b])
    db.flush()

    db.add(models.ClientUser(user_id=client_user_a.id, client_id=client_a.id, agency_id=agency_a.id))

    project_a = models.Project(agency_id=agency_a.id, client_id=client_a.id, name="Project A")
    project_b = models.Project(agency_id=agency_b.id, client_id=client_b.id, name="Project B")
    db.add_all([project_a, project_b])
    db.flush()

    db.add(models.ProjectMember(project_id=project_a.id, user_id=member_a.id))

    internal_task = models.Task(
        project_id=project_a.id, agency_id=agency_a.id, title="Internal task", is_client_visible=False
    )
    visible_task = models.Task(
        project_id=project_a.id, agency_id=agency_a.id, title="Client-visible task", is_client_visible=True
    )
    task_b = models.Task(project_id=project_b.id, agency_id=agency_b.id, title="Task in B")
    db.add_all([internal_task, visible_task, task_b])
    db.commit()

    def token(user, role, agency_id=None, client_id=None):
        return create_session_token(user_id=user.id, agency_id=agency_id, role=role, client_id=client_id)

    return {
        "agency_a": agency_a, "agency_b": agency_b,
        "client_a": client_a, "client_b": client_b,
        "project_a": project_a, "project_b": project_b,
        "internal_task": internal_task, "visible_task": visible_task, "task_b": task_b,
        "admin_a_token": token(admin_a, "agency_admin", agency_a.id),
        "member_a_token": token(member_a, "agency_member", agency_a.id),
        "client_a_token": token(client_user_a, "client_user", agency_a.id, client_a.id),
        "admin_b_token": token(admin_b, "agency_admin", agency_b.id),
        "member_a_user": member_a,
    }


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}
