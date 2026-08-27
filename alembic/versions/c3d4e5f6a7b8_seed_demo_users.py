"""seed_demo_users

Seeds 5 demo users, one per persona role, for local/demo environments.
Password for all seeded accounts is "demo1234" - this is an intentionally
public, non-secret demo credential documented on the login page; it must
never be reused for a real production account.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-04 00:00:00.000001

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# bcrypt hash of the plaintext demo password "demo1234"
DEMO_PASSWORD_HASH = "$2b$12$pBq4iIIc3HWApmwhflwiZe9nkmZJYNsgVIeFF0qR1kryuI556HQdy"

DEMO_USERS = [
    ("owner@hotelmind.demo", "Demo Owner", "OWNER"),
    ("revenue.manager@hotelmind.demo", "Demo Revenue Manager", "REVENUE_MANAGER"),
    ("ops.manager@hotelmind.demo", "Demo Ops Manager", "OPS_MANAGER"),
    ("restaurant.manager@hotelmind.demo", "Demo Restaurant Manager", "RESTAURANT_MANAGER"),
    ("guest.experience@hotelmind.demo", "Demo Guest Experience Manager", "GUEST_EXPERIENCE_MANAGER"),
]


def upgrade() -> None:
    conn = op.get_bind()

    # Non-OWNER demo users are scoped to the first branch found, if any exists.
    # OWNER always gets branch_id = NULL (all-branch access).
    branch_row = conn.execute(sa.text("SELECT id FROM branches ORDER BY created_at LIMIT 1")).fetchone()
    default_branch_id = branch_row[0] if branch_row else None

    users_table = sa.table(
        "users",
        sa.column("id", sa.UUID()),
        sa.column("email", sa.String()),
        sa.column("hashed_password", sa.String()),
        sa.column("full_name", sa.String()),
        sa.column("role", sa.String()),
        sa.column("branch_id", sa.UUID()),
        sa.column("is_active", sa.Boolean()),
    )

    for email, full_name, role in DEMO_USERS:
        conn.execute(
            users_table.insert().values(
                id=sa.text("gen_random_uuid()"),
                email=email,
                hashed_password=DEMO_PASSWORD_HASH,
                full_name=full_name,
                role=role,
                branch_id=None if role == "OWNER" else default_branch_id,
                is_active=True,
            )
        )


def downgrade() -> None:
    conn = op.get_bind()
    emails = [email for email, _, _ in DEMO_USERS]
    conn.execute(
        sa.text("DELETE FROM users WHERE email = ANY(:emails)"),
        {"emails": emails},
    )
