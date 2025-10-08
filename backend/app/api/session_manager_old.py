"""
Session Manager
Server-side session management

현재: 메모리 기반 (개발/테스트용)
추후: Redis/DynamoDB (AWS/Google 배포 시)
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)


class SessionManager:
    """
    서버 측 세션 관리

    세션 생성, 검증, 조회, 삭제 기능 제공
    """

    def __init__(self, session_ttl_hours: int = 24):
        """
        초기화

        Args:
            session_ttl_hours: 세션 유효 시간 (시간)
        """
        self._sessions: Dict[str, Dict] = {}  # session_id -> session_data
        self.session_ttl = timedelta(hours=session_ttl_hours)

        logger.info(f"SessionManager initialized (TTL: {session_ttl_hours}h)")

    def create_session(
        self,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Tuple[str, datetime]:
        """
        새 세션 생성

        서버가 고유한 UUID 기반 session_id 생성

        Args:
            user_id: 사용자 ID (선택)
            metadata: 추가 메타데이터 (선택)

        Returns:
            (session_id, expires_at): 생성된 세션 ID와 만료 시각
        """
        session_id = f"session-{uuid.uuid4()}"
        created_at = datetime.now()
        expires_at = created_at + self.session_ttl

        self._sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "metadata": metadata or {},
            "created_at": created_at,
            "expires_at": expires_at,
            "last_activity": created_at,
            "request_count": 0
        }

        logger.info(
            f"Session created: {session_id} "
            f"(user: {user_id or 'anonymous'}, expires: {expires_at.isoformat()})"
        )

        return session_id, expires_at

    def validate_session(self, session_id: str) -> bool:
        """
        세션 유효성 검증

        Args:
            session_id: 검증할 세션 ID

        Returns:
            유효 여부
        """
        if session_id not in self._sessions:
            logger.warning(f"Session not found: {session_id}")
            return False

        session = self._sessions[session_id]

        # 만료 체크
        if datetime.now() > session["expires_at"]:
            logger.info(f"Session expired: {session_id}")
            del self._sessions[session_id]
            return False

        # 마지막 활동 시간 업데이트
        session["last_activity"] = datetime.now()
        session["request_count"] += 1

        logger.debug(
            f"Session validated: {session_id} "
            f"(requests: {session['request_count']})"
        )

        return True

    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        세션 정보 조회

        Args:
            session_id: 세션 ID

        Returns:
            세션 정보 dict (없으면 None)
        """
        session = self._sessions.get(session_id)

        if session and datetime.now() <= session["expires_at"]:
            return session

        return None

    def delete_session(self, session_id: str) -> bool:
        """
        세션 삭제 (로그아웃)

        Args:
            session_id: 삭제할 세션 ID

        Returns:
            삭제 성공 여부
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
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
        now = datetime.now()
        expired = [
            sid for sid, data in self._sessions.items()
            if now > data["expires_at"]
        ]

        for sid in expired:
            del self._sessions[sid]

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")

        return len(expired)

    def get_active_session_count(self) -> int:
        """
        활성 세션 수 조회

        Returns:
            현재 활성 세션 수
        """
        # 만료되지 않은 세션만 카운트
        now = datetime.now()
        active = sum(
            1 for data in self._sessions.values()
            if now <= data["expires_at"]
        )
        return active

    def extend_session(self, session_id: str, hours: int = 24) -> bool:
        """
        세션 만료 시간 연장

        Args:
            session_id: 연장할 세션 ID
            hours: 연장할 시간 (시간)

        Returns:
            연장 성공 여부
        """
        session = self.get_session(session_id)

        if not session:
            return False

        session["expires_at"] = datetime.now() + timedelta(hours=hours)
        logger.info(f"Session extended: {session_id} (+{hours}h)")

        return True


# === 전역 싱글톤 ===

_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """
    SessionManager 싱글톤 인스턴스 반환

    FastAPI Depends()에서 사용

    Returns:
        SessionManager 인스턴스
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
