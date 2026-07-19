"""Add support for cash transactions

Revision ID: 3137ebc3838c
Revises: 778bcc15f23b
Create Date: 2026-07-09 09:48:36.251025

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3137ebc3838c'
down_revision: Union[str, Sequence[str], None] = '778bcc15f23b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(**kwargs) -> None:
    """Upgrade schema."""
    op.execute("ALTER TABLE transactions MODIFY COLUMN transaction_type ENUM('BUY', 'SELL', 'DEPOSIT', 'WITHDRAW') NOT NULL;")


def downgrade(**kwargs) -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE transactions MODIFY COLUMN transaction_type ENUM('BUY', 'SELL') NOT NULL;")
