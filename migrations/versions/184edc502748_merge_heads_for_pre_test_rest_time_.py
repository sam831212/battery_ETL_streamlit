"""merge heads for pre_test_rest_time column

Revision ID: 184edc502748
Revises: add_pre_test_rest_time_20250605, 51256a17ff3f
Create Date: 2025-06-05 23:42:37.080766

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '184edc502748'
down_revision: Union[str, None] = ('add_pre_test_rest_time_20250605', '51256a17ff3f')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
