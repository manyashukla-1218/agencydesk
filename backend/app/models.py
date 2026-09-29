import uuid
import enum
from datetime import datetime

from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, Enum, Integer, Text,
    UniqueConstraint, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


def uuid_col():
    return Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AgencyRole(str, enum.Enum):
    agency_admin = "agency_admin"
    agency_member = "agency_member"


class TaskStatus(str, enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    in_review = "in_review"
    done = "done"


class TaskPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class FileApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    changes_requested = "changes_requested"


class InviteStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    revoked = "revoked"


class InviteRole(str, enum.Enum):
    agency_admin = "agency_admin"
    agency_member = "agency_member"
    client_user = "client_user"


# ---------------------------------------------------------------------------
# Identity — deliberately GLOBAL, not per-tenant.
# A single human (one email) can hold an agency_admin/agency_member membership
# in one agency AND a client_user membership in another. That's why `User`
# has no agency_id: the agency/role pairing lives in the membership tables
# below, never on the identity row itself. See DESIGN.md, "one person, two
# agencies".
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = uuid_col()
    email = Column(String, nullable=False, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    agency_memberships = relationship("AgencyMembership", back_populates="user")
    client_memberships = relationship("ClientUser", back_populates="user")


class Agency(Base):
    __tablename__ = "agencies"

    id = uuid_col()
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    memberships = relationship("AgencyMembership", back_populates="agency")
    clients = relationship("Client", back_populates="agency")


class AgencyMembership(Base):
    """An agency-staff seat: ties one User to one Agency with a role.

    A user can have at most one row per agency (unique constraint below),
    but can have rows in many *different* agencies with different roles —
    that's the whole mechanism for 'same email, different role per agency'.
    """
    __tablename__ = "agency_memberships"
    __table_args__ = (UniqueConstraint("user_id", "agency_id", name="uq_membership_user_agency"),)

    id = uuid_col()
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    agency_id = Column(UUID(as_uuid=True), ForeignKey("agencies.id"), nullable=False)
    role = Column(Enum(AgencyRole), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="agency_memberships")
    agency = relationship("Agency", back_populates="memberships")


class Client(Base):
    """A client company that belongs to exactly one agency (the tenant key)."""
    __tablename__ = "clients"

    id = uuid_col()
    agency_id = Column(UUID(as_uuid=True), ForeignKey("agencies.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    agency = relationship("Agency", back_populates="clients")
    projects = relationship("Project", back_populates="client")


class ClientUser(Base):
    """A client-side login: ties one User to one Client (and therefore one
    agency, via client.agency_id). This is the client_user 'role' — it is a
    membership row, not a flag on User, for the same reason AgencyMembership
    isn't either.
    """
    __tablename__ = "client_users"
    __table_args__ = (UniqueConstraint("user_id", "client_id", name="uq_clientuser_user_client"),)

    id = uuid_col()
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    # Denormalized on purpose: lets every tenant-scoping query filter on
    # agency_id directly on this table without a join to `clients`.
    agency_id = Column(UUID(as_uuid=True), ForeignKey("agencies.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="client_memberships")
    client = relationship("Client")


class Project(Base):
    __tablename__ = "projects"

    id = uuid_col()
    # Tenant key. NOT NULL and always trusted over any client-supplied value.
    agency_id = Column(UUID(as_uuid=True), ForeignKey("agencies.id"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)

    client = relationship("Client", back_populates="projects")
    members = relationship("ProjectMember", back_populates="project")
    tasks = relationship("Task", back_populates="project")


class ProjectMember(Base):
    """Scopes an agency_member to the specific project(s) they're assigned to."""
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_projectmember"),)

    id = uuid_col()
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="members")


class Task(Base):
    __tablename__ = "tasks"

    id = uuid_col()
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    # Denormalized tenant key — see DESIGN.md. Lets every query (including
    # comments/files/time-entries joins) filter on agency_id without walking
    # task -> project -> client -> agency each time, and lets a DB-level
    # Postgres Row-Level-Security policy key off one column consistently
    # across every table.
    agency_id = Column(UUID(as_uuid=True), ForeignKey("agencies.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    status = Column(Enum(TaskStatus), default=TaskStatus.todo, nullable=False)
    priority = Column(Enum(TaskPriority), default=TaskPriority.medium, nullable=False)
    assignee_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    due_date = Column(DateTime, nullable=True)
    is_client_visible = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="tasks")
    comments = relationship("Comment", back_populates="task")
    files = relationship("FileAsset", back_populates="task")
    time_entries = relationship("TimeEntry", back_populates="task")


class Comment(Base):
    __tablename__ = "comments"

    id = uuid_col()
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, index=True)
    agency_id = Column(UUID(as_uuid=True), ForeignKey("agencies.id"), nullable=False, index=True)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=False)
    # Independent of the task's flag on purpose: an internal task can still
    # have one client-visible reply-to-client comment, and vice versa a
    # client-visible task can carry internal-only comments agency staff use
    # to coordinate. Every read path must AND this with the caller's role,
    # never assume it matches the parent task.
    is_client_visible = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="comments")


class FileAsset(Base):
    __tablename__ = "files"

    id = uuid_col()
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, index=True)
    agency_id = Column(UUID(as_uuid=True), ForeignKey("agencies.id"), nullable=False, index=True)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    storage_key = Column(String, nullable=False)
    is_client_visible = Column(Boolean, default=False, nullable=False)
    approval_status = Column(Enum(FileApprovalStatus), default=FileApprovalStatus.pending, nullable=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="files")


class TimeEntry(Base):
    __tablename__ = "time_entries"

    id = uuid_col()
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, index=True)
    agency_id = Column(UUID(as_uuid=True), ForeignKey("agencies.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    note = Column(String, default="")
    entry_date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="time_entries")


class Invite(Base):
    """Pending invitation to join an agency (staff) or a client (portal).

    The partial-unique constraint (enforced in the Alembic migration, since
    plain SQLAlchemy UniqueConstraint can't express a WHERE clause) is what
    makes resending an invite idempotent: only one *pending* invite may
    exist per (agency_id, email, client_id). Accepting or revoking frees the
    slot. See DESIGN.md, "invite races".
    """
    __tablename__ = "invites"

    id = uuid_col()
    agency_id = Column(UUID(as_uuid=True), ForeignKey("agencies.id"), nullable=False, index=True)
    email = Column(String, nullable=False, index=True)
    role = Column(Enum(InviteRole), nullable=False)
    # Only set when role == client_user.
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True)
    token = Column(String, nullable=False, unique=True)
    status = Column(Enum(InviteStatus), default=InviteStatus.pending, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
