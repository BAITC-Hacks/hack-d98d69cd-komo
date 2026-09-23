"""Employee goal overrides and participation action receipts."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('employees', sa.Column('goal_mode', sa.String(20), nullable=False, server_default='profile'))
    op.add_column('employees', sa.Column('goal_override', JSONB, nullable=True))
    op.add_column('completion_receipts', sa.Column('action', sa.String(20), nullable=False, server_default='complete'))
    op.add_column('completion_receipts', sa.Column('request_data', JSONB, nullable=True))


def downgrade():
    op.drop_column('completion_receipts', 'request_data')
    op.drop_column('completion_receipts', 'action')
    op.drop_column('employees', 'goal_override')
    op.drop_column('employees', 'goal_mode')
