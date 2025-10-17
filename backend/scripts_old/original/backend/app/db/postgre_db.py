from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# PostgreSQL 엔진 생성 
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)
Session = SessionLocal  # 하위 호환성을 위해 유지
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
