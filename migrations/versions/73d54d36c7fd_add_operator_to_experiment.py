"""add_operator_to_experiment

Revision ID: 73d54d36c7fd
Revises: 3da0c53ff99f
Create Date: 2025-06-11 16:05:08.684538

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision: str = '73d54d36c7fd'
down_revision: Union[str, None] = '3da0c53ff99f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add operator column to experiment table
    with op.batch_alter_table('experiment', schema=None) as batch_op:
        batch_op.add_column(sa.Column('operator', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove operator column from experiment table
    with op.batch_alter_table('experiment', schema=None) as batch_op:
        batch_op.drop_column('operator')
