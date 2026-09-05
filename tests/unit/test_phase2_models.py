"""
Lenny Growth Assistant — Unit Tests for SQLAlchemy ORM Models (Phase 2)

Verifies model definitions, table metadata, constraints, and relationships.
"""

import unittest
from app.db.base import Base
from app.db.models import (
    Artifact,
    Episode,
    Message,
    MessageCitation,
    Session,
    TranscriptChunk,
    User,
)


class TestORMModels(unittest.TestCase):
    """Verifies that all 7 core ORM models match the implementation contract."""

    def test_registered_tables(self):
        """Ensure all 7 required tables exist in the declarative metadata."""
        expected_tables = {
            "users",
            "sessions",
            "messages",
            "episodes",
            "transcript_chunks",
            "message_citations",
            "artifacts",
        }
        actual_tables = set(Base.metadata.tables.keys())
        self.assertEqual(expected_tables, actual_tables)

    def test_user_model_columns(self):
        """Verify columns on User model."""
        cols = {c.name: c for c in User.__table__.columns}
        self.assertIn("id", cols)
        self.assertIn("anonymous_identifier", cols)
        self.assertIn("metadata", cols)
        self.assertIn("created_at", cols)
        self.assertTrue(cols["anonymous_identifier"].unique)
        self.assertFalse(cols["anonymous_identifier"].nullable)

    def test_session_model_columns_and_fk(self):
        """Verify columns and foreign keys on Session model."""
        cols = {c.name: c for c in Session.__table__.columns}
        self.assertIn("id", cols)
        self.assertIn("user_id", cols)
        self.assertIn("title", cols)
        self.assertIn("created_at", cols)
        self.assertIn("updated_at", cols)
        fks = list(Session.__table__.foreign_keys)
        self.assertEqual(len(fks), 1)
        self.assertEqual(fks[0].target_fullname, "users.id")
        self.assertEqual(fks[0].ondelete, "CASCADE")

    def test_message_model_constraints(self):
        """Verify role check constraint on Message model."""
        cols = {c.name: c for c in Message.__table__.columns}
        self.assertIn("role", cols)
        self.assertIn("cost_usd", cols)
        self.assertIn("tokens_prompt", cols)
        self.assertIn("tokens_completion", cols)
        constraints = [c.name for c in Message.__table__.constraints]
        self.assertIn("ck_messages_role", constraints)

    def test_transcript_chunk_unique_constraint(self):
        """Verify (episode_id, chunk_index) uniqueness and vector column."""
        cols = {c.name: c for c in TranscriptChunk.__table__.columns}
        self.assertIn("embedding", cols)
        self.assertIn("content_hash", cols)
        self.assertIn("token_count", cols)
        unique_constraints = [
            c.name for c in TranscriptChunk.__table__.constraints if hasattr(c, "columns")
        ]
        self.assertIn("uq_episode_chunk", unique_constraints)

    def test_message_citation_unique_constraint(self):
        """Verify (message_id, chunk_id) uniqueness on citations."""
        unique_constraints = [
            c.name for c in MessageCitation.__table__.constraints if hasattr(c, "columns")
        ]
        self.assertIn("uq_message_chunk", unique_constraints)

    def test_artifact_model_constraints(self):
        """Verify artifact type check constraint and nullable message FK."""
        constraints = [c.name for c in Artifact.__table__.constraints]
        self.assertIn("ck_artifacts_type", constraints)
        cols = {c.name: c for c in Artifact.__table__.columns}
        self.assertTrue(cols["message_id"].nullable)
        fks = {fk.target_fullname: fk for fk in Artifact.__table__.foreign_keys}
        self.assertIn("messages.id", fks)
        self.assertEqual(fks["messages.id"].ondelete, "SET NULL")
        self.assertIn("sessions.id", fks)
        self.assertEqual(fks["sessions.id"].ondelete, "CASCADE")


if __name__ == "__main__":
    unittest.main()
