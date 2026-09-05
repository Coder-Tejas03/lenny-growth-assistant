"""Initial schema: 7 core tables and HNSW vector index

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-04 20:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Required PostgreSQL Extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    op.execute('CREATE EXTENSION IF NOT EXISTS vector;')

    # 2. Table: users
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('anonymous_identifier', sa.String(length=255), nullable=False),
        sa.Column('metadata', JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    )
    op.create_index('idx_users_anonymous_identifier', 'users', ['anonymous_identifier'], unique=True)

    # 3. Table: sessions
    op.create_table(
        'sessions',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=255), server_default=sa.text("'New Conversation'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    )
    op.create_index('idx_sessions_user_id', 'sessions', ['user_id'])
    op.create_index('idx_sessions_updated_at', 'sessions', [sa.text('updated_at DESC')])

    # 4. Table: messages
    op.create_table(
        'messages',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('session_id', UUID(as_uuid=True), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('tokens_prompt', sa.Integer(), nullable=True),
        sa.Column('tokens_completion', sa.Integer(), nullable=True),
        sa.Column('cost_usd', sa.Numeric(precision=10, scale=6), server_default=sa.text('0.0'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.CheckConstraint("role IN ('user', 'assistant', 'system')", name='ck_messages_role'),
    )
    op.create_index('idx_messages_session_id', 'messages', ['session_id'])
    op.create_index('idx_messages_created_at', 'messages', ['created_at'])

    # 5. Table: episodes
    op.create_table(
        'episodes',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('episode_number', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('guest_name', sa.String(length=255), nullable=False),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('publication_date', sa.Date(), nullable=True),
        sa.Column('metadata', JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    )
    op.create_index('idx_episodes_guest_name', 'episodes', ['guest_name'])
    op.create_index('idx_episodes_title', 'episodes', ['title'])

    # 6. Table: transcript_chunks
    op.create_table(
        'transcript_chunks',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('episode_id', UUID(as_uuid=True), sa.ForeignKey('episodes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('start_timestamp', sa.String(length=50), nullable=True),
        sa.Column('end_timestamp', sa.String(length=50), nullable=True),
        sa.Column('token_count', sa.Integer(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('metadata', JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.UniqueConstraint('episode_id', 'chunk_index', name='uq_episode_chunk'),
    )
    op.create_index('idx_transcript_chunks_episode_id', 'transcript_chunks', ['episode_id'])
    op.create_index('idx_transcript_chunks_content_hash', 'transcript_chunks', ['content_hash'])

    # HNSW Vector Index on transcript_chunks.embedding using cosine distance
    op.execute(
        """
        CREATE INDEX idx_transcript_chunks_embedding_hnsw 
        ON transcript_chunks 
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
        """
    )

    # 7. Table: message_citations
    op.create_table(
        'message_citations',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('message_id', UUID(as_uuid=True), sa.ForeignKey('messages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_id', UUID(as_uuid=True), sa.ForeignKey('transcript_chunks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('similarity', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.UniqueConstraint('message_id', 'chunk_id', name='uq_message_chunk'),
    )
    op.create_index('idx_message_citations_message_id', 'message_citations', ['message_id'])

    # 8. Table: artifacts
    op.create_table(
        'artifacts',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('session_id', UUID(as_uuid=True), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('message_id', UUID(as_uuid=True), sa.ForeignKey('messages.id', ondelete='SET NULL'), nullable=True),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.CheckConstraint("type IN ('markdown', 'html')", name='ck_artifacts_type'),
    )
    op.create_index('idx_artifacts_session_id', 'artifacts', ['session_id'])


def downgrade() -> None:
    op.drop_table('artifacts')
    op.drop_table('message_citations')
    op.execute('DROP INDEX IF EXISTS idx_transcript_chunks_embedding_hnsw;')
    op.drop_table('transcript_chunks')
    op.drop_table('episodes')
    op.drop_table('messages')
    op.drop_table('sessions')
    op.drop_table('users')
    op.execute('DROP EXTENSION IF EXISTS vector;')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp";')
