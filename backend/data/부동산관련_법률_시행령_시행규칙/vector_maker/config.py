"""
   DB   
"""
import os
from pathlib import Path

#  
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
CHUNKS_DIR = DATA_DIR / "chunks"
DB_DIR = BASE_DIR / "vectordb"

#  
for dir_path in [RAW_DIR, PROCESSED_DIR, CHUNKS_DIR, DB_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# ChromaDB 
CHROMA_PERSIST_DIR = str(DB_DIR / "chroma")
COLLECTION_NAME = "real_estate_law"

#    (Kure-v1  )
# EMBEDDING_MODEL = "BAAI/bge-m3"  # HuggingFace 
EMBEDDING_MODEL = r"C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\___\4. \models\kure_v1"  #  Kure-v1  
EMBEDDING_DIMENSION = 1024  # Kure-v1 dimension

#  
CHUNK_SIZE = 500  #  
CHUNK_OVERLAP = 50  #   
MIN_CHUNK_SIZE = 100  #   

#   
SUPPORTED_FORMATS = ['.docx', '.doc', '.pdf', '.txt']
TABLE_DETECTION = True  #     

#  
LOG_LEVEL = "INFO"
LOG_FILE = BASE_DIR / "processing.log"
