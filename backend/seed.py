"""
Seeds two agencies with clients, projects, tasks (a mix of internal and
client-visible), and demonstrates the "one person, two agencies" edge case
by giving demo.person@example.com an agency_member seat at Northwind and a
client_user seat at Beacon — same email, two different roles.

Run: python seed.py   (after `alembic upgrade head`)
"""
from app.database import SessionLocal, engine, Base
from app import models
from app.security import hash_password

Base.metadata.create_all(bind=engine)  # convenience for sqlite/dev; alembic is the source of truth for postgres

db = SessionLocal()


def get_or_create_user(email, name, password="password123"):
    u = db.query(models.User).filter(models.User.email == email).first()
    if u:
        return u
    u = models.User(email=email, full_name=name, hashed_password=hash_password(password))
    db.add(u)
    db.flush()
    return u


# --- Agency 1: Northwind Creative -----------------------------------------
northwind = models.Agency(name="Northwind Creative")
db.add(northwind)
db.flush()

admin1 = get_or_create_user("admin@northwind.test", "Nora Admin")
member1 = get_or_create_user("demo.person@example.com", "Demo Person")  # <- also a client_user at Beacon below
db.add(models.AgencyMembership(user_id=admin1.id, agency_id=northwind.id, role=models.AgencyRole.agency_admin))
db.add(models.AgencyMembership(user_id=member1.id, agency_id=northwind.id, role=models.AgencyRole.agency_member))

acme = models.Client(agency_id=northwind.id, name="Acme Corp")
globex = models.Client(agency_id=northwind.id, name="Globex Inc")
db.add_all([acme, globex])
db.flush()

acme_client_contact = get_or_create_user("contact@acme.test", "Alex Acme")
db.add(models.ClientUser(user_id=acme_client_contact.id, client_id=acme.id, agency_id=northwind.id))

proj1 = models.Project(agency_id=northwind.id, client_id=acme.id, name="Acme Website Redesign")
db.add(proj1)
db.flush()
db.add(models.ProjectMember(project_id=proj1.id, user_id=member1.id))

t1 = models.Task(
    project_id=proj1.id, agency_id=northwind.id, title="Draft homepage wireframes",
    is_client_visible=True, assignee_id=member1.id,
)
t2 = models.Task(
    project_id=proj1.id, agency_id=northwind.id, title="Internal: renegotiate hosting cost",
    is_client_visible=False, assignee_id=admin1.id,
)
db.add_all([t1, t2])
db.flush()

db.add(models.Comment(task_id=t1.id, agency_id=northwind.id, author_id=member1.id,
                       body="First draft attached, let us know what you think!", is_client_visible=True))
db.add(models.Comment(task_id=t1.id, agency_id=northwind.id, author_id=admin1.id,
                       body="Internal note: client tends to want more whitespace.", is_client_visible=False))
db.add(models.TimeEntry(task_id=t1.id, agency_id=northwind.id, user_id=member1.id,
                         duration_minutes=180, note="Wireframing"))

# --- Agency 2: Beacon Studio ------------------------------------------------
beacon = models.Agency(name="Beacon Studio")
db.add(beacon)
db.flush()

admin2 = get_or_create_user("admin@beacon.test", "Bea Admin")
db.add(models.AgencyMembership(user_id=admin2.id, agency_id=beacon.id, role=models.AgencyRole.agency_admin))

beacon_client = models.Client(agency_id=beacon.id, name="Initech")
db.add(beacon_client)
db.flush()

# demo.person@example.com, same human as above, is a CLIENT at Beacon — not
# agency staff. Same email, different role, different tenant.
db.add(models.ClientUser(user_id=member1.id, client_id=beacon_client.id, agency_id=beacon.id))

proj2 = models.Project(agency_id=beacon.id, client_id=beacon_client.id, name="Initech Brand Refresh")
db.add(proj2)
db.flush()

t3 = models.Task(project_id=proj2.id, agency_id=beacon.id, title="Share logo concepts",
                  is_client_visible=True, assignee_id=admin2.id)
db.add(t3)

db.commit()

print("Seeded.")
print("Login as agency staff:      admin@northwind.test / password123  (agency_admin @ Northwind)")
print("Login as agency member:     demo.person@example.com / password123")
print("   -> has TWO memberships: agency_member @ Northwind, client_user @ Beacon/Initech")
print("   -> /auth/login will return both contexts; pick one via /auth/select-context")
print("Login as a client contact:  contact@acme.test / password123  (client_user @ Northwind/Acme)")
