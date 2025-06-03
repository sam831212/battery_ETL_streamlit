"""remove_data_meta_from_experiment

Revision ID: 51256a17ff3f
Revises: abdca5d975e3
Create Date: 2025-06-03 22:19:05.576835

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '51256a17ff3f'
down_revision: Union[str, None] = 'abdca5d975e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove data_meta column from experiment table."""
    with op.batch_alter_table('experiment') as batch_op:
        batch_op.drop_column('data_meta')


def downgrade() -> None:
    """Add data_meta column back to experiment table."""
    with op.batch_alter_table('experiment') as batch_op:
        batch_op.add_column(sa.Column('data_meta', sa.JSON(), nullable=True))
