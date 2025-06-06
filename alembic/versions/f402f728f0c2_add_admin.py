"""Add admin

Revision ID: f402f728f0c2
Revises: 796c61a169ad
Create Date: 2025-05-04 15:55:48.730014

"""
from app.config import settings
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String, Integer, UUID, Enum

from app.models.enums.UserRole import UserRole

# revision identifiers, used by Alembic.
revision: str = 'f402f728f0c2'
down_revision: Union[str, None] = '796c61a169ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    users = table('users',
                  column('id', UUID),
                  column('name', String),
                  column('role', Enum(UserRole, name="user_role")),
                  column('api_key', String)
                  )

    instruments = table('instruments',
                        column('ticker', String),
                        column('name', String)
    )

    for i, uuid in enumerate(settings.admins_id):
        op.bulk_insert(users, [
            {
                'id': uuid,
                'name': f"Admin{i}",
                'role': UserRole.ADMIN,
                'api_key': f"key-{uuid}"
            }
        ])

    op.bulk_insert(instruments, [
        {
            'ticker': "RUB",
            'name': "Ruble"
        }
    ])


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM users WHERE username = 'admin'")
    op.execute("DELETE FROM instruments")
