"""
Add pre_test_rest_time column to Step table

Revision ID: add_pre_test_rest_time_20250606
Revises: 
Create Date: 2025-06-06
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_pre_test_rest_time_20250606'
down_revision = None  # Set this to the latest revision in your project
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('step', sa.Column('pre_test_rest_time', sa.Float(), nullable=True))

def downgrade():
    op.drop_column('step', 'pre_test_rest_time')
