"""Separate QA fixtures from the normal HR population without deleting data."""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('employees', sa.Column('is_test', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute("UPDATE employees SET is_test = true WHERE left(employee_id, 3) = 'QA_'")


def downgrade():
    op.drop_column('employees', 'is_test')
