# migrations/versions/002_add_track_embeddings.py
"""add track_embeddings

Revision ID: 002
Revises: 001
Create Date: 2024-11-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

def upgrade():
    # Create track_embeddings table
    op.create_table('track_embeddings',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('track_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('embedding', sa.dialects.postgresql.VECTOR(384), nullable=True),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('track_id', 'model_version', name='unique_track_model')
    )
    
    # Create index for vector similarity search
    op.create_index('idx_embeddings_vector', 'track_embeddings', ['embedding'], unique=False, postgresql_using='hnsw')

def downgrade():
    op.drop_table('track_embeddings')