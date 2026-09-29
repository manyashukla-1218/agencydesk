"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String, nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String, nullable=False),
        sa.Column("full_name", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "agencies",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "agency_memberships",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("agency_id", pg.UUID(as_uuid=True), sa.ForeignKey("agencies.id"), nullable=False),
        sa.Column("role", sa.Enum("agency_admin", "agency_member", name="agencyrole"), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "agency_id", name="uq_membership_user_agency"),
    )

    op.create_table(
        "clients",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("agency_id", pg.UUID(as_uuid=True), sa.ForeignKey("agencies.id"), nullable=False, index=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "client_users",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("client_id", pg.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("agency_id", pg.UUID(as_uuid=True), sa.ForeignKey("agencies.id"), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "client_id", name="uq_clientuser_user_client"),
    )

    op.create_table(
        "projects",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("agency_id", pg.UUID(as_uuid=True), sa.ForeignKey("agencies.id"), nullable=False, index=True),
        sa.Column("client_id", pg.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False, index=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("status", sa.String, server_default="active"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "project_members",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", pg.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "user_id", name="uq_projectmember"),
    )

    op.create_table(
        "tasks",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", pg.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False, index=True),
        sa.Column("agency_id", pg.UUID(as_uuid=True), sa.ForeignKey("agencies.id"), nullable=False, index=True),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column(
            "status",
            sa.Enum("todo", "in_progress", "in_review", "done", name="taskstatus"),
            nullable=False,
            server_default="todo",
        ),
        sa.Column(
            "priority",
            sa.Enum("low", "medium", "high", "urgent", name="taskpriority"),
            nullable=False,
            server_default="medium",
        ),
        sa.Column("assignee_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("due_date", sa.DateTime, nullable=True),
        sa.Column("is_client_visible", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "comments",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("task_id", pg.UUID(as_uuid=True), sa.ForeignKey("tasks.id"), nullable=False, index=True),
        sa.Column("agency_id", pg.UUID(as_uuid=True), sa.ForeignKey("agencies.id"), nullable=False, index=True),
        sa.Column("author_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("is_client_visible", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "files",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("task_id", pg.UUID(as_uuid=True), sa.ForeignKey("tasks.id"), nullable=False, index=True),
        sa.Column("agency_id", pg.UUID(as_uuid=True), sa.ForeignKey("agencies.id"), nullable=False, index=True),
        sa.Column("uploaded_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("filename", sa.String, nullable=False),
        sa.Column("storage_key", sa.String, nullable=False),
        sa.Column("is_client_visible", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column(
            "approval_status",
            sa.Enum("pending", "approved", "changes_requested", name="fileapprovalstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("approved_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "time_entries",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("task_id", pg.UUID(as_uuid=True), sa.ForeignKey("tasks.id"), nullable=False, index=True),
        sa.Column("agency_id", pg.UUID(as_uuid=True), sa.ForeignKey("agencies.id"), nullable=False, index=True),
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("duration_minutes", sa.Integer, nullable=False),
        sa.Column("note", sa.String, server_default=""),
        sa.Column("entry_date", sa.DateTime, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "invites",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("agency_id", pg.UUID(as_uuid=True), sa.ForeignKey("agencies.id"), nullable=False, index=True),
        sa.Column("email", sa.String, nullable=False, index=True),
        sa.Column(
            "role",
            sa.Enum("agency_admin", "agency_member", "client_user", name="inviterole"),
            nullable=False,
        ),
        sa.Column("client_id", pg.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=True),
        sa.Column("token", sa.String, nullable=False, unique=True),
        sa.Column(
            "status",
            sa.Enum("pending", "accepted", "revoked", name="invitestatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime, nullable=True),
    )

    # Partial unique index: at most one PENDING invite per (agency, email,
    # client). This is the DB-level backstop for the "invite races" edge
    # case — the app already checks-then-inserts, but only a real
    # constraint prevents two concurrent requests from both racing past
    # that check. Postgres treats NULLs as distinct in a unique index, so we
    # coalesce client_id to a fixed nil UUID for the staff-invite case
    # (client_id IS NULL) to still get "one pending invite per email" there
    # too.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_pending_invite
        ON invites (agency_id, email, COALESCE(client_id, '00000000-0000-0000-0000-000000000000'))
        WHERE status = 'pending'
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_pending_invite")
    op.drop_table("invites")
    op.drop_table("time_entries")
    op.drop_table("files")
    op.drop_table("comments")
    op.drop_table("tasks")
    op.drop_table("project_members")
    op.drop_table("projects")
    op.drop_table("client_users")
    op.drop_table("clients")
    op.drop_table("agency_memberships")
    op.drop_table("agencies")
    op.drop_table("users")
    for enum_name in ("agencyrole", "taskstatus", "taskpriority", "fileapprovalstatus", "inviterole", "invitestatus"):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
