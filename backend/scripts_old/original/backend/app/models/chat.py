from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    TIMESTAMP,
    ForeignKey,
    Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.postgre_db import Base
import uuid

class ChatSession(Base):
    """채팅 세션 모델"""
    __tablename__ = "chat_sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="사용자 ID")
    title = Column(String(20), nullable=False, comment="채팅 세션 제목")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="생성일")
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now(), comment="수정일")

    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    
class ChatMessage(Base):
    """채팅 메시지 모델"""
    __tablename__ = "chat_messages"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True, comment="세션 ID")
    sender_type = Column(String(20), nullable=False, comment="발신자 타입 (user/assistant)")
    content = Column(Text, nullable=False, comment="메시지 내용")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="생성일")

    # Relationships
    session = relationship("ChatSession", back_populates="messages")