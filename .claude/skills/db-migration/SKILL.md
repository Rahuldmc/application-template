---
name: db-migration
description: Create, review and apply Alembic database migrations safely, including data migrations and upgrades for offline client installs. Use whenever a SQLAlchemy model changes, a table/column/index is added, renamed or removed, or data must be transformed.
---

# Database migrations (Alembic)

Every schema change is a migration. Migrations run on developer machines, CI, cloud servers and offline client installs. Many of these you can't touch after shipping, so they must be correct first time.

## Workflow

```bash
cd backend
# 1. Change the model(s) in app/models/ (and register new models in app/models/__init__.py)
# 2. Generate
uv run alembic revision --autogenerate -m "add orders table"
# 3. REVIEW the generated file (checklist below) and edit it
# 4. Apply and prove it reverses
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
# 5. Confirm models and DB agree
uv run alembic check
# 6. See the SQL that will run on client databases
uv run alembic upgrade head --sql
# 7. Run the tests (they also run every migration up, down and up)
uv run pytest
```

## Review checklist: autogenerate is a draft, not an answer

- [ ] **Renames.** Autogenerate sees a rename as drop + add, which **loses data**. Replace with `op.alter_column(..., new_column_name=...)` or `op.rename_table`.
- [ ] **New NOT NULL column on an existing table** needs a `server_default`, or three steps: add nullable → backfill → set NOT NULL.
- [ ] **Enum/type changes** and `String` length reductions can fail on existing data. Check.
- [ ] **Indexes** for every foreign key and every column you filter or sort by.
- [ ] **Unique constraints** on existing data: check for duplicates first, or the upgrade fails at the client.
- [ ] **Downgrade** actually reverses the upgrade (or raises a clear error if it's truly irreversible, with a comment explaining why).
- [ ] **No imports from `app.models`** in the migration. Models change over time and old migrations must keep working. Use `sa.table()` / `sa.column()` for data updates.
- [ ] Remove the "please adjust" comments once reviewed.

## Data migrations

```python
from alembic import op
import sqlalchemy as sa

orders = sa.table("orders", sa.column("status", sa.String))

def upgrade() -> None:
    op.add_column("orders", sa.Column("status", sa.String(20), nullable=True))
    op.execute(orders.update().values(status="open"))
    op.alter_column("orders", "status", nullable=False)
```

Keep data changes set-based (one `UPDATE`), not row-by-row Python loops.

## Hard rules

- **Never edit a migration that has been committed.** Other databases may have applied it. Write a new migration. The repo's PreToolUse hook blocks such edits.
- One logical change per migration, with a descriptive message.
- Never use `Base.metadata.create_all()` outside tests.
- Two people created migrations from the same head? Run `uv run alembic merge heads -m "merge"`.

## Zero-downtime and offline clients (expand → contract)

When the old and new app versions might run against the same DB (rolling deploys), or a client may roll back:

1. **Expand** (release N): add new columns/tables, nullable or defaulted; write to both old and new.
2. **Migrate data** (release N or N+1).
3. **Contract** (release N+1 or later): remove old columns once nothing reads them.

For offline clients, `install.sh` backs up the database before migrating. Still: test the upgrade from the **oldest version any client runs**, not just the previous one.
