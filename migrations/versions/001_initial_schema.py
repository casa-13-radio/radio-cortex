# migrations/versions/001_initial_schema.py
"""initial schema

Revision ID: 001
Revises: 
Create Date: 2024-11-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Criar extensões
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

    # Tabela artists
    op.create_table('artists',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('name', sa.String(length=300), nullable=False),
        sa.Column('name_normalized', sa.String(length=300), nullable=True),
        sa.Column('aliases', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('style', sa.String(length=200), nullable=True),
        sa.Column('country', sa.String(length=2), nullable=True),
        sa.Column('website_url', sa.Text(), nullable=True),
        sa.Column('social_links', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('track_count', sa.Integer(), server_default=sa.text('0'), nullable=True),
        sa.Column('total_plays', sa.BigInteger(), server_default=sa.text('0'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Tabela licenses
    op.create_table('licenses',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('short_code', sa.String(length=20), nullable=False),
        sa.Column('full_name', sa.String(length=200), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('allows_commercial', sa.Boolean(), nullable=False),
        sa.Column('allows_derivatives', sa.Boolean(), nullable=False),
        sa.Column('requires_attribution', sa.Boolean(), nullable=False),
        sa.Column('requires_share_alike', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=True),
        sa.Column('usage_count', sa.Integer(), server_default=sa.text('0'), nullable=True),
        sa.Column('icon_url', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('short_code')
    )

    # Tabela tracks
    op.create_table('tracks',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('artist_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('album', sa.String(length=500), nullable=True),
        sa.Column('license_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('audio_url', sa.Text(), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=False),
        sa.Column('bitrate_kbps', sa.Integer(), nullable=True),
        sa.Column('format', sa.String(length=10), server_default=sa.text("'mp3'"), nullable=True),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('primary_genre', sa.String(length=100), nullable=True),
        sa.Column('secondary_genres', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('mood_tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('cultural_context', sa.String(length=200), nullable=True),
        sa.Column('id3_tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('audio_fingerprint', sa.Text(), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=False),
        sa.Column('collected_by', sa.String(length=50), server_default=sa.text("'hunter_agent'"), nullable=True),
        sa.Column('collected_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('status', sa.String(length=50), server_default=sa.text("'pending_enrichment'"), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.CheckConstraint("duration_seconds > 0", name="positive_duration"),
        sa.CheckConstraint("status IN ('pending_enrichment', 'pending_compliance', 'approved', 'rejected', 'on_hold')", name="valid_status"),
        sa.ForeignKeyConstraint(['artist_id'], ['artists.id'], ),
        sa.ForeignKeyConstraint(['license_id'], ['licenses.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Tabela track_embeddings
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

    # Índices
    op.create_index('idx_artists_name', 'artists', ['name_normalized'], unique=False)
    op.create_index('idx_artists_country', 'artists', ['country'], unique=False)
    op.create_index('idx_tracks_status', 'tracks', ['status'], unique=False)
    op.create_index('idx_tracks_artist', 'tracks', ['artist_id'], unique=False)
    op.create_index('idx_tracks_genre', 'tracks', ['primary_genre'], unique=False)
    op.create_index('idx_tracks_created', 'tracks', ['created_at'], unique=False)
    op.create_index('idx_embeddings_vector', 'track_embeddings', ['embedding'], unique=False, postgresql_using='hnsw')
    op.create_index('idx_embeddings_track', 'track_embeddings', ['track_id'], unique=False)

def downgrade():
    op.drop_table('track_embeddings')
    op.drop_table('tracks')
    op.drop_table('licenses')
    op.drop_table('artists')