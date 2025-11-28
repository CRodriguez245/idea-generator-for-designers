"""
Session persistence utilities backed by SQLite.

Provides:
    - SQLAlchemy models for sessions and generated assets
    - CRUD helpers to create/update session records
    - Retention policy enforcement for data older than six months
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class Session(Base):
    """SQLAlchemy model for user sessions."""

    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    user_name = Column(String(255), nullable=True)
    user_email = Column(String(255), nullable=True)
    challenge_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # JSON fields for generated content
    hmw_results = Column(Text, nullable=True)  # JSON array of strings
    sketch_prompts = Column(Text, nullable=True)  # JSON array of strings
    image_urls = Column(Text, nullable=True)  # JSON array of URLs
    layout_results = Column(Text, nullable=True)  # JSON array of dicts


class SessionStore:
    """Manages session persistence with SQLite."""

    def __init__(self, database_path: str = "data/sessions.db") -> None:
        """Initialize store with database path."""
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{self.database_path}", echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def create_session(
        self, session_id: str, challenge_text: str, user_name: str = "", user_email: str = ""
    ) -> str:
        """Create a new session record and return its identifier."""
        db_session = self.Session()
        try:
            session = Session(
                session_id=session_id,
                challenge_text=challenge_text,
                user_name=user_name or None,
                user_email=user_email or None,
            )
            db_session.add(session)
            db_session.commit()
            return session_id
        except Exception as e:
            db_session.rollback()
            raise RuntimeError(f"Failed to create session: {e}") from e
        finally:
            db_session.close()

    def update_session(self, session_id: str, payload: Dict[str, Any]) -> None:
        """Update an existing session record with generated results."""
        db_session = self.Session()
        try:
            session = db_session.query(Session).filter_by(session_id=session_id).first()
            if not session:
                raise ValueError(f"Session not found: {session_id}")

            if "hmw_results" in payload:
                session.hmw_results = json.dumps(payload["hmw_results"])
            if "sketch_prompts" in payload:
                session.sketch_prompts = json.dumps(payload["sketch_prompts"])
            if "image_urls" in payload:
                session.image_urls = json.dumps(payload["image_urls"])
            if "layout_results" in payload:
                session.layout_results = json.dumps(payload["layout_results"])

            session.updated_at = datetime.utcnow()
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            raise RuntimeError(f"Failed to update session: {e}") from e
        finally:
            db_session.close()

    def get_session(self, session_id: str) -> Dict[str, Any] | None:
        """Retrieve a session by ID."""
        db_session = self.Session()
        try:
            session = db_session.query(Session).filter_by(session_id=session_id).first()
            if not session:
                return None
            return {
                "session_id": session.session_id,
                "user_name": session.user_name,
                "user_email": session.user_email,
                "challenge_text": session.challenge_text,
                "hmw_results": json.loads(session.hmw_results) if session.hmw_results else [],
                "sketch_prompts": json.loads(session.sketch_prompts) if session.sketch_prompts else [],
                "image_urls": json.loads(session.image_urls) if session.image_urls else [],
                "layout_results": json.loads(session.layout_results) if session.layout_results else [],
                "created_at": session.created_at.isoformat() if session.created_at else None,
            }
        finally:
            db_session.close()

    def purge_expired_sessions(self, retention_days: int = 180) -> int:
        """Remove sessions older than the retention threshold. Returns count deleted."""
        db_session = self.Session()
        try:
            cutoff = datetime.utcnow() - timedelta(days=retention_days)
            deleted = db_session.query(Session).filter(Session.created_at < cutoff).delete()
            db_session.commit()
            return deleted
        except Exception as e:
            db_session.rollback()
            raise RuntimeError(f"Failed to purge expired sessions: {e}") from e
        finally:
            db_session.close()
