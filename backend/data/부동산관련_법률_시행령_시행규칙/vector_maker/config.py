"""
부동산 법률 문서 벡터DB 구축 설정 파일
"""
import os
from pathlib import Path

# 경로 설정
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
CHUNKS_DIR = DATA_DIR / "chunks"
DB_DIR = BASE_DIR / "vectordb"

# 디렉토리 생성
for dir_path in [RAW_DIR, PROCESSED_DIR, CHUNKS_DIR, DB_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# ChromaDB 설정
CHROMA_PERSIST_DIR = str(DB_DIR / "chroma")
COLLECTION_NAME = "real_estate_law"

# 임베딩 모델 설정 (Kure-v1 / BGE-M3 기반)
EMBEDDING_MODEL = "BAAI/bge-m3"  # HuggingFace 모델명
EMBEDDING_DIMENSION = 1024  # BGE-M3 dimension

# 청킹 설정
CHUNK_SIZE = 500  # 토큰 기준
CHUNK_OVERLAP = 50  # 오버랩 토큰 수
MIN_CHUNK_SIZE = 100  # 최소 청크 크기

# 문서 처리 설정
SUPPORTED_FORMATS = ['.docx', '.doc', '.pdf', '.txt']
TABLE_DETECTION = True  # 표 감지 및 처리 여부

# 로깅 설정
LOG_LEVEL = "INFO"
LOG_FILE = BASE_DIR / "processing.log"
