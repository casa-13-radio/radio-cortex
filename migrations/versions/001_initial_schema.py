"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-11-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Create licenses table
    op.create_table(
        'licenses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('short_code', sa.String(20), nullable=False, unique=True, index=True),
        sa.Column('full_name', sa.String(200), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('allows_commercial', sa.Boolean(), nullable=False),
        sa.Column('allows_derivatives', sa.Boolean(), nullable=False),
        sa.Column('requires_attribution', sa.Boolean(), nullable=False),
        sa.Column('requires_share_alike', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('usage_count', sa.Integer(), default=0),
        sa.Column('icon_url', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    
    # Create artists table
    op.create_table(
        'artists',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(300), nullable=False, index=True),
        sa.Column('name_normalized', sa.String(300), nullable=False, unique=True, index=True),
        sa.Column('aliases', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('style', sa.String(200), nullable=True),
        sa.Column('country', sa.String(2), nullable=True),
        sa.Column('website_url', sa.Text(), nullable=True),
        sa.Column('social_links', postgresql.JSONB(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('track_count', sa.Integer(), default=0),
        sa.Column('total_plays', sa.BigInteger(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    
    # Create tracks table
    op.create_table(
        'tracks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(500), nullable=False, index=True),
        sa.Column('artist_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('artists.id'), nullable=False, index=True),
        sa.Column('album', sa.String(500), nullable=True),
        sa.Column('license_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('licenses.id'), nullable=False, index=True),
        sa.Column('audio_url', sa.Text(), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=False),
        sa.Column('bitrate_kbps', sa.Integer(), nullable=True),
        sa.Column('format', sa.String(10), default='mp3'),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('primary_genre', sa.String(100), nullable=True),
        sa.Column('secondary_genres', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('mood_tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('cultural_context', sa.String(200), nullable=True),
        sa.Column('id3_tags', postgresql.JSONB(), nullable=True),
        sa.Column('audio_fingerprint', sa.Text(), nullable=True),
        sa.Column('embedding', Vector(384), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=False),
        sa.Column('collected_by', sa.String(50), default='hunter_agent', nullable=False),
        sa.Column('collected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(50), default='pending_enrichment', nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('pending_enrichment', 'pending_compliance', 'approved', 'rejected', 'on_hold')", name='valid_status'),
        sa.CheckConstraint('duration_seconds > 0', name='positive_duration'),
    )
    
    # Create index on embedding for similarity search
    op.execute('CREATE INDEX idx_tracks_embedding ON tracks USING ivfflat (embedding vector_cosine_ops)')


def downgrade() -> None:
    op.drop_table('tracks')
    op.drop_table('artists')
    op.drop_table('licenses')
    op.execute('DROP EXTENSION IF EXISTS vector')