import sqlite3
import threading
import time
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

DB_PATH = "user_sessions.db"
SESSION_TTL_HOURS = 24
MAX_HISTORY_LENGTH = 10
MAX_AI_REQUESTS_PER_WINDOW = 5
RATE_WINDOW_SECONDS = 60


class ActionState(Enum):
    NONE = "none"
    WAITING_FOR_IMAGE_COMPRESS = "compress_image"
    WAITING_FOR_PDF_COMPRESS = "compress_pdf"
    WAITING_FOR_IMAGE_TO_PDF = "to_pdf"
    WAITING_FOR_PDF_TO_IMAGES = "to_images"


@dataclass
class UserSession:
    user_id: int
    action_state: ActionState = ActionState.NONE
    history: list[dict] = field(default_factory=list)
    ai_request_timestamps: list[float] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def add_message(self, role: str, text: str):
        self.history.append({'role': role, 'parts': [text]})
        if len(self.history) > MAX_HISTORY_LENGTH:
            self.history = self.history[-MAX_HISTORY_LENGTH:]

    def can_make_ai_request(self) -> bool:
        now = time.time()
        cutoff = now - RATE_WINDOW_SECONDS
        self.ai_request_timestamps = [ts for ts in self.ai_request_timestamps if ts > cutoff]
        return len(self.ai_request_timestamps) < MAX_AI_REQUESTS_PER_WINDOW

    def record_ai_request(self):
        self.ai_request_timestamps.append(time.time())


class SessionManager:
    _instance: Optional['SessionManager'] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self):
        self._db_lock = threading.Lock()
        self._sessions: dict[int, UserSession] = {}
        self._init_db()
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()

    def _init_db(self):
        with self._db_lock:
            self._conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    user_id INTEGER PRIMARY KEY,
                    action_state TEXT NOT NULL DEFAULT 'none',
                    history TEXT NOT NULL DEFAULT '[]',
                    ai_timestamps TEXT NOT NULL DEFAULT '[]',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            self._conn.commit()

    def _cleanup_loop(self):
        while True:
            time.sleep(300)
            self._cleanup_expired()

    def _cleanup_expired(self):
        try:
            with self._db_lock:
                now = time.time()
                cutoff = now - (SESSION_TTL_HOURS * 3600)
                cur = self._conn.execute(
                    "SELECT user_id FROM sessions WHERE updated_at < ?", (cutoff,)
                )
                expired = [row[0] for row in cur.fetchall()]
                if expired:
                    self._conn.execute("DELETE FROM sessions WHERE updated_at < ?", (cutoff,))
                    self._conn.commit()
                    for uid in expired:
                        self._sessions.pop(uid, None)
                    logger.info("Cleaned up %d expired sessions", len(expired))
        except Exception as e:
            logger.error("Cleanup error: %s", e)

    def get_session(self, user_id: int) -> UserSession:
        now = time.time()
        if user_id in self._sessions:
            session = self._sessions[user_id]
            session.updated_at = now
            return session

        with self._db_lock:
            cur = self._conn.execute(
                "SELECT action_state, history, ai_timestamps, created_at FROM sessions WHERE user_id = ?",
                (user_id,)
            )
            row = cur.fetchone()

        if row:
            session = UserSession(
                user_id=user_id,
                action_state=ActionState(row[0]),
                history=eval(row[1]),
                ai_request_timestamps=eval(row[2]),
                created_at=row[3],
                updated_at=now
            )
        else:
            session = UserSession(user_id=user_id)

        self._sessions[user_id] = session
        return session

    def _save_session(self, session: UserSession):
        try:
            with self._db_lock:
                self._conn.execute("""
                    INSERT OR REPLACE INTO sessions 
                    (user_id, action_state, history, ai_timestamps, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    session.user_id,
                    session.action_state.value,
                    str(session.history),
                    str(session.ai_request_timestamps),
                    session.created_at,
                    session.updated_at
                ))
                self._conn.commit()
        except Exception as e:
            logger.error("Failed to save session: %s", e)

    def set_action(self, user_id: int, state: ActionState) -> UserSession:
        session = self.get_session(user_id)
        session.action_state = state
        session.updated_at = time.time()
        self._save_session(session)
        return session

    def clear_action(self, user_id: int):
        session = self.get_session(user_id)
        session.action_state = ActionState.NONE
        session.updated_at = time.time()
        self._save_session(session)

    def add_history(self, user_id: int, role: str, text: str):
        session = self.get_session(user_id)
        session.add_message(role, text)
        session.updated_at = time.time()
        self._save_session(session)

    def check_rate_limit(self, user_id: int) -> bool:
        session = self.get_session(user_id)
        return session.can_make_ai_request()

    def record_request(self, user_id: int):
        session = self.get_session(user_id)
        session.record_ai_request()
        self._save_session(session)

    def close(self):
        with self._db_lock:
            if self._conn:
                self._conn.close()