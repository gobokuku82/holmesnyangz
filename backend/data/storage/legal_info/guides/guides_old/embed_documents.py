import os
import json
import glob
import pandas as pd
import yaml
from tqdm import tqdm

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

# --- 설정 변수 ---

# 데이터가 위치한 기본 경로
# metadata_index.json 파일이 있는 경로를 기준으로 합니다.
BASE_DATA_PATH = '.' 

# 로컬에 다운로드한 KURE-V1 모델 경로
MODEL_PATH = "models/kure_v1"

# ChromaDB를 저장할 디렉토리
PERSIST_DIRECTORY = "chroma_db"

# search_config.yaml 파일에서 컬렉션 이름 가져오기
try:
    with open(os.path.join(BASE_DATA_PATH, "metadata_index", "search_config.yaml"), 'r', encoding='utf-8') as f:
        search_config = yaml.safe_load(f)
    COLLECTION_NAME = search_config.get('vector_db', {}).get('collection_name', 'korean_real_estate_laws')
except FileNotFoundError:
    print("Warning: search_config.yaml 파일을 찾을 수 없어 기본 컬렉션 이름을 사용합니다.")
    COLLECTION_NAME = "korean_real_estate_laws"

def load_all_documents_from_index(base_path: str) -> list[Document]:
    """
    metadata_index.json을 기반으로 모든 chunked.json 파일들을 로드하고,
    LangChain의 Document 객체 리스트로 변환합니다.
    """
    index_path = os.path.join(base_path, "metadata_index.json")
    if not os.path.exists(index_path):
        raise FileNotFoundError(f"'{index_path}' 파일을 찾을 수 없습니다. 경로를 확인해주세요.")

    with open(index_path, 'r', encoding='utf-8') as f:
        metadata_index = json.load(f)

    all_docs = []
    document_files = [doc['file_path'] for doc in metadata_index.get('documents', [])]

    print(f"총 {len(document_files)}개의 문서 파일을 처리합니다.")

    for file_path in tqdm(document_files, desc="문서 로딩 중"):
        full_path = os.path.join(base_path, file_path)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                chunks = json.load(f)
            
            for chunk in chunks:
                # 'text' 필드가 주 콘텐츠라고 가정합니다.
                page_content = chunk.get('text', '') 
                metadata = chunk.get('metadata', {})
                
                # 메타데이터 값들을 ChromaDB가 지원하는 형태로 변환 (string, int, float, bool)
                cleaned_metadata = {}
                for key, value in metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        cleaned_metadata[key] = value
                    elif value is None:
                        continue # None 값은 제외
                    else:
                        # 리스트나 딕셔너리는 JSON 문자열로 변환하여 저장
                        cleaned_metadata[key] = json.dumps(value, ensure_ascii=False)

                doc = Document(page_content=page_content, metadata=cleaned_metadata)
                all_docs.append(doc)

        except FileNotFoundError:
            print(f"Warning: 파일 '{full_path}'를 찾을 수 없습니다. 건너뜁니다.")
        except json.JSONDecodeError:
            print(f"Warning: 파일 '{full_path}'가 유효한 JSON 형식이 아닙니다. 건너뜁니다.")
            
    return all_docs

def main():
    """
    메인 실행 함수: 문서 로드, 임베딩 모델 초기화, ChromaDB에 저장
    """
    print("1. 모든 문서 조각(chunks)을 로드합니다.")
    documents = load_all_documents_from_index(BASE_DATA_PATH)
    if not documents:
        print("처리할 문서가 없습니다. 스크립트를 종료합니다.")
        return
    print(f"성공적으로 {len(documents)}개의 Document 객체를 생성했습니다.")

    print("\n2. HuggingFace 임베딩 모델을 로드합니다.")
    print(f"모델 경로: '{MODEL_PATH}'")
    
    # 모델 로드 시, CPU/GPU 사용 설정
    # GPU 사용 시: model_kwargs = {'device': 'cuda'}
    model_kwargs = {'device': 'cpu'} 
    encode_kwargs = {'normalize_embeddings': False}
    
    try:
        embedding_function = HuggingFaceEmbeddings(
            model_name=MODEL_PATH,
            model_kwargs=model_kwargs,
            encode_kwargs=encode_kwargs
        )
    except Exception as e:
        print(f"임베딩 모델 로딩 중 오류 발생: {e}")
        print("모델 경로가 올바른지, 필요한 라이브러리가 설치되었는지 확인해주세요.")
        return

    print("임베딩 모델 로딩 완료.")

    print("\n3. ChromaDB에 문서를 임베딩하고 저장합니다.")
    print(f"저장 경로: '{PERSIST_DIRECTORY}'")
    print(f"컬렉션 이름: '{COLLECTION_NAME}'")
    
    # ChromaDB 벡터 스토어 생성 또는 로드
    vector_db = Chroma.from_documents(
        documents=documents,
        embedding=embedding_function,
        collection_name=COLLECTION_NAME,
        persist_directory=PERSIST_DIRECTORY
    )
    
    print(f"\n성공적으로 {len(documents)}개의 문서를 ChromaDB에 저장했습니다.")
    print("--- 작업 완료 ---")
    
    # 저장된 데이터 확인 (선택 사항)
    print(f"\n저장된 벡터 수: {vector_db._collection.count()}")


if __name__ == "__main__":
    main()