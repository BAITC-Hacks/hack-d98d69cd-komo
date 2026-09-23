"""Frozen initial schema; never import live application metadata here."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    for table, key in [('skills', 'skill_id'), ('events', 'event_id'), ('employees', 'employee_id')]:
        op.create_table(table, sa.Column(key, sa.String(100), primary_key=True), sa.Column('data', JSONB, nullable=False))
    op.create_table('role_profiles', sa.Column('role', sa.String(100), primary_key=True), sa.Column('grade', sa.String(20), primary_key=True), sa.Column('data', JSONB, nullable=False))
    op.create_table('dataset_state', sa.Column('id', sa.Integer, primary_key=True), sa.Column('as_of_date', sa.Date, nullable=False), sa.Column('revision', sa.Integer, nullable=False), sa.Column('session_secret', sa.String(128), nullable=False))
    op.create_table('users', sa.Column('username', sa.String(100), primary_key=True), sa.Column('password_hash', sa.String(255), nullable=False), sa.Column('role', sa.String(20), nullable=False), sa.Column('employee_id', sa.String(100), sa.ForeignKey('employees.employee_id'), nullable=True))
    op.create_table('activity_records', sa.Column('record_id', sa.String(100), primary_key=True), sa.Column('employee_id', sa.String(100), sa.ForeignKey('employees.employee_id'), nullable=False), sa.Column('event_id', sa.String(100), sa.ForeignKey('events.event_id'), nullable=False), sa.Column('date', sa.Date, nullable=False), sa.Column('status', sa.String(20), nullable=False), sa.Column('data', JSONB, nullable=False))
    op.create_index('ix_history_employee_date', 'activity_records', ['employee_id', 'date'])
    op.create_table('completion_receipts', sa.Column('employee_id', sa.String(100), sa.ForeignKey('employees.employee_id'), primary_key=True), sa.Column('idempotency_key', sa.String(100), primary_key=True), sa.Column('event_id', sa.String(100), sa.ForeignKey('events.event_id'), nullable=False), sa.Column('response', JSONB, nullable=False))
    op.create_table('recommendation_runs', sa.Column('run_id', sa.String(40), primary_key=True), sa.Column('employee_id', sa.String(100), sa.ForeignKey('employees.employee_id'), nullable=False), sa.Column('revision', sa.Integer, nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column('data', JSONB, nullable=False))
    op.create_index('ix_recommendation_employee_date', 'recommendation_runs', ['employee_id', 'created_at'])


def downgrade():
    for table in ['recommendation_runs', 'completion_receipts', 'activity_records', 'users', 'dataset_state', 'role_profiles', 'employees', 'events', 'skills']:
        op.drop_table(table)
