"""Add admin

Revision ID: f402f728f0c2
Revises: 796c61a169ad
Create Date: 2025-05-04 15:55:48.730014

"""
import uuid
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

    uuid_str = "56856e6b-dcfe-48ba-a9b2-fc300fc0028f"
    uuid_obj = uuid.UUID(uuid_str)

    op.bulk_insert(users, [
        {
            'id': uuid_obj,
            'name': "Admin",
            'role': UserRole.ADMIN,
            'api_key': f"key-{uuid_obj}"
        }
    ])

    op.bulk_insert(instruments, [
        {
            'ticker': "BTC",
            'name': "Bitcoin"
        },
        {
            'ticker': "EUR",
            'name': "Euro"
        },
        {
            'ticker': "USD",
            'name': "Dollar"
        },
        {
            'ticker': "SBER",
            'name': "Sberbank"
        },
        {
            'ticker': "GAZP",
            'name': "Gazprom"
        },
        {
            'ticker': "ETH",
            'name': "Ethereum"
        },
        {
            'ticker': "NVDA",
            'name': "NVIDIA Corporation"
        }
    ])


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM users WHERE username = 'admin'")
    op.execute("DELETE FROM instruments")
