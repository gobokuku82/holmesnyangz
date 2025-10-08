"""
SQLite-based Session Manager
Persistent session storage that survives backend restarts

기존 메모리 기반 SessionManager를 SQLite로 교체
Backend 재시작 시에도 세션 유지
"""

import sqlite3
import uuid
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)


class SessionManager:
    """
    SQLite 기반 세션 관리

    Backend 재시작 시에도 세션 유지
    LangGraph checkpointer와 동일한 아키텍처
    """

    def __init__(self, db_path: Optional[str] = None, session_ttl_hours: int = 24):
        """
        초기화

        Args:
            db_path: 데이터베이스 파일 경로 (None이면 기본 경로)
            session_ttl_hours: 세션 유효 시간 (시간)
        """
        if db_path is None:
            # backend/data/system/sessions/sessions.db
            base_dir = Path(__file__).parent.parent.parent
            db_path = base_dir / "data" / "system" / "sessions" / "sessions.db"

        self.db_path = Path(db_path)
        self.session_ttl = timedelta(hours=session_ttl_hours)

        # 디렉토리 생성
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 데이터베이스 초기화
        self._init_db()

        logger.info(
            f"SQLiteSessionManager initialized "
            f"(DB: {self.db_path}, TTL: {session_ttl_hours}h)"
        )

    def _init_db(self):
        """데이터베이스 스키마 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    last_activity TIMESTAMP NOT NULL,
                    request_count INTEGER DEFAULT 0
                )
            """)

            # 인덱스 생성 (만료 시간 기준 정리용)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at
                ON sessions(expires_at)
            """)

            conn.commit()

        logger.debug("Session database schema initialized")

    def create_session(
        self,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Tuple[str, datetime]:
        """
        새 세션 생성 (SQLite에 저장)

        Args:
            user_id: 사용자 ID (선택)
            metadata: 추가 메타데이터 (선택)

        Returns:
            (session_id, expires_at): 생성된 세션 ID와 만료 시각
        """
        session_id = f"session-{uuid.uuid4()}"
        created_at = datetime.now()
        expires_at = created_at + self.session_ttl

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO sessions
                (session_id, user_id, metadata, created_at, expires_at, last_activity, request_count)
                VALUES (?, ?, ?, ?, ?, ?, 0)
            """, (
                session_id,
                user_id,
                json.dumps(metadata or {}),
                created_at.isoformat(),
                expires_at.isoformat(),
                created_at.isoformat()
            ))
            conn.commit()

        logger.info(
            f"Session created (SQLite): {session_id} "
            f"(user: {user_id or 'anonymous'}, expires: {expires_at.isoformat()})"
        )

        return session_id, expires_at

    def validate_session(self, session_id: str) -> bool:
        """
        세션 유효성 검증 (SQLite 조회)

        Args:
            session_id: 검증할 세션 ID

        Returns:
            유효 여부
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT session_id, expires_at FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()

            if not row:
                logger.warning(f"Session not found: {session_id}")
                return False

            # 만료 체크
            expires_at = datetime.fromisoformat(row["expires_at"])
            if datetime.now() > expires_at:
                logger.info(f"Session expired: {session_id}")
                # 만료된 세션 삭제
                conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
                conn.commit()
                return False

            # 마지막 활동 시간 업데이트
            conn.execute("""
                UPDATE sessions
                SET last_activity = ?, request_count = request_count + 1
                WHERE session_id = ?
            """, (datetime.now().isoformat(), session_id))
            conn.commit()

            logger.debug(f"Session validated: {session_id}")
            return True

    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        세션 정보 조회 (SQLite)

        Args:
            session_id: 세션 ID

        Returns:
            세션 정보 dict (없으면 None)
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()

            if not row:
                return None

            # 만료 체크
            expires_at = datetime.fromisoformat(row["expires_at"])
            if datetime.now() > expires_at:
                # 만료된 세션 삭제
                conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
                conn.commit()
                return None

            return {
                "session_id": row["session_id"],
                "user_id": row["user_id"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                "created_at": datetime.fromisoformat(row["created_at"]),
                "expires_at": expires_at,
                "last_activity": datetime.fromisoformat(row["last_activity"]),
                "request_count": row["request_count"]
            }

    def delete_session(self, session_id: str) -> bool:
        """
        세션 삭제 (로그아웃)

        Args:
            session_id: 삭제할 세션 ID

        Returns:
            삭제 성공 여부
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            conn.commit()

            if cursor.rowcount > 0:
                logger.info(f"Session deleted: {session_id}")
                return True

            logger.warning(f"Session not found for deletion: {session_id}")
            return False

    def cleanup_expired_sessions(self) -> int:
        """
        만료된 세션 정리

        Returns:
            정리된 세션 수
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM sessions WHERE expires_at < ?",
                (datetime.now().isoformat(),)
            )
            conn.commit()
            count = cursor.rowcount

        if count > 0:
            logger.info(f"Cleaned up {count} expired sessions")

        return count

    def get_active_session_count(self) -> int:
        """
        활성 세션 수 조회

        Returns:
            현재 활성 세션 수
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE expires_at > ?",
                (datetime.now().isoformat(),)
            )
            count = cursor.fetchone()[0]

        return count

    def extend_session(self, session_id: str, hours: int = 24) -> bool:
        """
        세션 만료 시간 연장

        Args:
            session_id: 연장할 세션 ID
            hours: 연장할 시간 (시간)

        Returns:
            연장 성공 여부
        """
        new_expires_at = datetime.now() + timedelta(hours=hours)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE sessions
                SET expires_at = ?
                WHERE session_id = ? AND expires_at > ?
            """, (
                new_expires_at.isoformat(),
                session_id,
                datetime.now().isoformat()
            ))
            conn.commit()

            if cursor.rowcount > 0:
                logger.info(f"Session extended: {session_id} (+{hours}h)")
                return True

            return False


# === 전역 싱글톤 ===

_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """
    SessionManager 싱글톤 인스턴스 반환

    FastAPI Depends()에서 사용

    Returns:
        SessionManager 인스턴스 (SQLite 기반)
    """
    global _session_manager

    if _session_manager is None:
        _session_manager = SessionManager(session_ttl_hours=24)

    return _session_manager


def reset_session_manager():
    """
    SessionManager 초기화 (테스트용)
    """
    global _session_manager
    _session_manager = None
