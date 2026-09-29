# DESIGN.md — AgencyDesk

## How the schema enforces tenant isolation

Every tenant-owned table (`clients`, `projects`, `tasks`, `comments`,
`files`, `time_entries`, `invites`) carries a non-nullable `agency_id`
foreign key — including tables like `tasks`, `comments`, `files`, and
`time_entries` that are one hop further from `agencies` in the object
graph. That's a deliberate denormalization: it means every one of those
tables can be filtered by tenant with a single indexed column comparison,
instead of a multi-table join through `project -> client -> agency` on
every request. It also means a single Postgres Row-Level-Security policy
(`agency_id = current_setting('app.agency_id')::uuid`) could be layered on
top of all of them uniformly as defense-in-depth, if we wanted a second
enforcement layer below the app.

But the real enforcement happens in `app/deps.py`, in one class:
`TenantScope`. Every router calls `scope.tasks()`, `scope.projects()`, etc.
instead of writing its own `.filter(...)`. `agency_id` is never read from
the URL, body, or query string — it comes only from the JWT, which the
server itself issued. A request can *ask* for another tenant's ID, but the
query underneath it is already scoped to the caller's own `agency_id`, so a
mismatched ID just 404s (never 403 — we don't want to confirm the ID exists
elsewhere).

## How a client is blocked from internal content

`is_client_visible` lives on `tasks`, `comments`, and `files`
independently — a client-visible task can still have an internal-only
comment thread underneath it. `TenantScope` adds
`.filter(is_client_visible == True)` for every one of those three
resources whenever `ctx.role == "client_user"`, and it does this in the
*same* method used by list, detail, search/filter, and the dashboard
aggregate — there's no second code path that could forget the check. Time
entries are blocked outright for clients (403), since raw hours were never
meant to be client-facing per the spec ("no invoicing needed").

## How the identity model supports one person across two agencies

`User` is a single, agency-agnostic identity keyed by email. Role and
tenant live on separate join rows: `AgencyMembership` (user × agency ×
role) and `ClientUser` (user × client, which implies an agency via
`client.agency_id`). One email can have a row in both tables, pointing at
different agencies, with no conflict — there's nothing on `User` itself to
collide. Login reflects this: if an email resolves to more than one
membership, `/auth/login` returns the list of contexts instead of a token,
and the client picks one via `/auth/select-context`. The resulting JWT
encodes that one active context (`agency_id` + `role`, or `client_id` for
a client), so a session is always scoped to exactly one tenant — even
though the same person could log in again five minutes later as someone
completely different.

## Edge case I'm proud of: invite races

Resending an invite calls a check-then-insert (`create_or_resend_invite`),
which is enough for the common case but not for two concurrent "resend"
clicks. The real guarantee is a **partial unique index** in the migration:
`UNIQUE (agency_id, email, COALESCE(client_id, nil_uuid)) WHERE status =
'pending'`. If two requests race past the app-level check, Postgres itself
rejects the second `INSERT`, and the handler catches that `IntegrityError`
and returns the winning row's token instead of erroring — so "resend"
stays idempotent under real concurrency, not just in the happy path. The
same email accepting the same invite twice is handled the mirror way: the
invite flips to `accepted` transactionally, so a second `/invites/accept`
gets a clean 400 rather than a second `User` row.
