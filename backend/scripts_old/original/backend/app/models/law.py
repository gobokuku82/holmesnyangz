from sqlalchemy import(
    Column,
    Integer,
    String, 
    TIMESTAMP,
    ForeignKey, 
    Index,
    Text,
    JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func 
from app.db.postgre_db import Base 

class Law(Base):
    """법률 모델 """
    __tablename__ = "laws"
    law_id = Column(Integer, primary_key=True, index=True, comment="법률/시행령/시행규칙/대법원규칙/용어집/기타")
    doc_type = Column(String(20), unique=True, nullable=False, comment="법령명")
    title = Column(String(30), unique=True, nullable=False, comment="법령명")
    number = Column(String(20), unique=True,comment="법령번호")
    enforcement_data = Column(String(20), comment="시행일")
    category = Column(String(20), nullable=False, comment="카테고리")
    total_articles = Column(Integer, default=0, comment="총 조항 수")
    last_article = Column(String(20), comment="마지막 조항 번호")
    source_file = Column(Text, comment="원본 파일명") # 필요할지는 의문임 
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), comment="생성된 시간")

    articles = relationship("Article", back_populates="law")
class Article(Base):
    """조항 상세 정보 """
    __tablename__ = "articles"
    article_id = Column(Integer, primary_key=True, index=True)
    law_id = Column(Integer, ForeignKey("laws.law_id", ondelete="CASCADE"), nullable=False)
    article_number = Column(String(20), nullable=False, comment="조항 번호(예: 제 1조)")
    article_title = Column(String(100), comment="조항 제목")
    chapter  = Column(String(20), comment="장")
    section = Column(String(20), comment="절")
    is_deleted = Column(Integer, default=0, comment="삭제 여부 (0: 유효, 1= 삭제)")
    is_tenant_protection = Column(Integer, default=0, comment="임차인 보호 조항")
    is_tax_realted = Column(Integer, default=0, comment="세금 관련")
    is_delegation = Column(Integer, default=0, comment="위임")
    is_penalty_related = Column(Integer, default=0, comment="별칙")
    chunk_ids = Column(Text, comment="ChromaDB chunk ID 배열(json)")
    metadata_json = Column(JSON, comment="전체 메타데이터 (JSON)")

    references = relationship("LegalReference", back_populates="article")


class LegalReference(Base):
    __tablename__ = "legal_references"
    reference_id = Column(Integer, primary_key=True, index= True)
    source_article_id = Column(Integer, ForeignKey("articles.article_id", ondelete="CASCADE"), nullable=False)
    reference_type = Column(String(50), comment="law references, decree_references, form_references")
    target_law_title = Column(String(100), comment = "참조 대상 법령명")
    target_article_number = Column(String(20), comment="참조 대상 조항")
    reference_text = Column(Text, comment="참조 내용")
    
    article = relationship("LegalReference", back_populates="references")