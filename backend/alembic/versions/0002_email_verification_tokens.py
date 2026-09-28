"""Add email verification tokens.

Revision ID: 0002_email_verification_tokens
Revises: 0001_verifact_initial
"""
from alembic import op
import sqlalchemy as sa

revision = '0002_email_verification_tokens'
down_revision = '0001_verifact_initial'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'email_verification_tokens',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('token_hash', sa.String(length=128), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash'),
    )
    op.create_index('ix_email_verification_tokens_user_id', 'email_verification_tokens', ['user_id'])


def downgrade():
    op.drop_index('ix_email_verification_tokens_user_id', table_name='email_verification_tokens')
    op.drop_table('email_verification_tokens')
