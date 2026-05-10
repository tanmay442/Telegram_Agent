import sqlite3
import threading
import time
import logging
import json
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = "user_sessions.db"
SESSION_TTL_HOURS = 24
MAX_HISTORY_LENGTH = 10

AI_WINDOW_SECONDS = 60
AI_MAX_REQUESTS = 5
AI_WARNING_THRESHOLD = 3
AI_COOLDOWN_HOURS = 2

FILE_OP_WINDOW_SECONDS = 3600
FILE_OP_MAX_REQUESTS = 100


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
    ai_warning_sent: bool = False
    ai_cooldown_until: float = 0.0
    file_op_timestamps: list[float] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def add_message(self, role: str, text: str):
        self.history.append({'role': role, 'parts': [text]})
        if len(self.history) > MAX_HISTORY_LENGTH:
            self.history = self.history[-MAX_HISTORY_LENGTH:]

    def _clean_old_timestamps(self, timestamps: list[float], window_seconds: int) -> list[float]:
        now = time.time()
        cutoff = now - window_seconds
        return [ts for ts in timestamps if ts > cutoff]

    def get_ai_status(self) -> tuple[int, int, bool, float]:
        now = time.time()
        if self.ai_cooldown_until > now:
            return 0, AI_MAX_REQUESTS, False, self.ai_cooldown_until - now

        self.ai_request_timestamps = self._clean_old_timestamps(self.ai_request_timestamps, AI_WINDOW_SECONDS)
        remaining = AI_MAX_REQUESTS - len(self.ai_request_timestamps)
        return max(0, remaining), AI_MAX_REQUESTS, self.ai_warning_sent, 0

    def can_make_ai_request(self) -> tuple[bool, str]:
        now = time.time()

        if self.ai_cooldown_until > now:
            cooldown_remaining = self.ai_cooldown_until - now
            hours = int(cooldown_remaining // 3600)
            minutes = int((cooldown_remaining % 3600) // 60)
            return False, f"Rate limit exceeded. Cooldown active. Try again in {hours}h {minutes}m."

        self.ai_request_timestamps = self._clean_old_timestamps(self.ai_request_timestamps, AI_WINDOW_SECONDS)

        if len(self.ai_request_timestamps) >= AI_MAX_REQUESTS:
            self.ai_cooldown_until = now + (AI_COOLDOWN_HOURS * 3600)
            self.ai_warning_sent = False
            return False, f"Rate limit exceeded. You can make {AI_MAX_REQUESTS} AI requests per minute. Cooldown: {AI_COOLDOWN_HOURS} hours."

        if len(self.ai_request_timestamps) >= AI_WARNING_THRESHOLD and not self.ai_warning_sent:
            remaining = AI_MAX_REQUESTS - len(self.ai_request_timestamps)
            self.ai_warning_sent = True
            return True, f"⚠️ Warning: Approaching AI request limit. {remaining} requests remaining."

        return True, ""

    def record_ai_request(self):
        now = time.time()
        self.ai_request_timestamps.append(now)
        self.ai_warning_sent = False

    def can_make_file_op(self) -> tuple[bool, str]:
        self.file_op_timestamps = self._clean_old_timestamps(self.file_op_timestamps, FILE_OP_WINDOW_SECONDS)

        if len(self.file_op_timestamps) >= FILE_OP_MAX_REQUESTS:
            remaining_time = AI_WINDOW_SECONDS - (time.time() - self.file_op_timestamps[0]) if self.file_op_timestamps else AI_WINDOW_SECONDS
            minutes = int(remaining_time // 60)
            return False, f"File operation rate limit exceeded. Try again in {minutes} minutes."

        return True, ""

    def record_file_op(self):
        self.file_op_timestamps.append(time.time())


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
                    ai_warning_sent INTEGER NOT NULL DEFAULT 0,
                    ai_cooldown_until REAL NOT NULL DEFAULT 0,
                    file_op_timestamps TEXT NOT NULL DEFAULT '[]',
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

    def _json_load(self, data: str, default) -> any:
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return default

    def get_session(self, user_id: int) -> UserSession:
        now = time.time()
        if user_id in self._sessions:
            session = self._sessions[user_id]
            session.updated_at = now
            return session

        with self._db_lock:
            cur = self._conn.execute(
                """SELECT action_state, history, ai_timestamps, ai_warning_sent,
                   ai_cooldown_until, file_op_timestamps, created_at
                   FROM sessions WHERE user_id = ?""",
                (user_id,)
            )
            row = cur.fetchone()

        if row:
            session = UserSession(
                user_id=user_id,
                action_state=ActionState(row[0]),
                history=self._json_load(row[1], []),
                ai_request_timestamps=self._json_load(row[2], []),
                ai_warning_sent=bool(row[3]),
                ai_cooldown_until=float(row[4]),
                file_op_timestamps=self._json_load(row[5], []),
                created_at=row[6],
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
                    (user_id, action_state, history, ai_timestamps, ai_warning_sent,
                     ai_cooldown_until, file_op_timestamps, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session.user_id,
                    session.action_state.value,
                    json.dumps(session.history),
                    json.dumps(session.ai_request_timestamps),
                    int(session.ai_warning_sent),
                    session.ai_cooldown_until,
                    json.dumps(session.file_op_timestamps),
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

    def check_ai_rate_limit(self, user_id: int) -> tuple[bool, str]:
        session = self.get_session(user_id)
        return session.can_make_ai_request()

    def record_ai_request(self, user_id: int):
        session = self.get_session(user_id)
        session.record_ai_request()
        self._save_session(session)

    def check_file_op_rate_limit(self, user_id: int) -> tuple[bool, str]:
        session = self.get_session(user_id)
        return session.can_make_file_op()

    def record_file_op(self, user_id: int):
        session = self.get_session(user_id)
        session.record_file_op()
        self._save_session(session)

    def get_ai_quota(self, user_id: int) -> str:
        session = self.get_session(user_id)
        remaining, total, _, cooldown = session.get_ai_status()
        if cooldown > 0:
            hours = int(cooldown // 3600)
            minutes = int((cooldown % 3600) // 60)
            return f"AI quota: On cooldown ({hours}h {minutes}m)"
        return f"AI quota: {remaining}/{total} remaining"

    def close(self):
        with self._db_lock:
            if self._conn:
                self._conn.close()