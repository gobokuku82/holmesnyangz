"""
ChromaDB 재임베딩 스크립트

목적: 청킹된 법령 파일들을 표준화된 메타데이터로 ChromaDB에 재임베딩

주요 기능:
1. 불일치한 메타데이터 필드를 표준 스키마로 정규화
2. title 필드 통합 (law_title/decree_title/rule_title → title)
3. doc_type, category 자동 추출
4. ChromaDB 재생성 (기존 삭제 후 재구축)

실행 방법:
    python backend/data/storage/legal_info/embedding/embed_legal_documents.py --test
    python backend/data/storage/legal_info/embedding/embed_legal_documents.py --full
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any
import chromadb
from sentence_transformers import SentenceTransformer
from datetime import datetime
import re

# 경로 설정
PROJECT_ROOT = Path(__file__).resolve().parents[5]
CHUNKED_DIR = PROJECT_ROOT / "backend" / "data" / "storage" / "legal_info" / "chunked"
CHROMA_PATH = PROJECT_ROOT / "backend" / "data" / "storage" / "legal_info" / "chroma_db"
MODEL_PATH = PROJECT_ROOT / "backend" / "app" / "service" / "models" / "kure_v1"

# 카테고리 매핑
CATEGORIES = [
    "1_공통 매매_임대차",
    "2_임대차_전세_월세",
    "3_공급_및_관리_매매_분양",
    "4_기타"
]


def extract_doc_type(filename: str) -> str:
    """
    파일명에서 문서 타입 추출

    예시:
        - 공인중개사법(법률)(제19841호).json → 법률
        - 부동산거래신고법 시행령(대통령령).json → 시행령
        - 부동산_용어_95가지_chunked.json → 용어집
    """
    filename_lower = filename.lower()

    if "용어" in filename or "glossary" in filename_lower:
        return "용어집"
    elif "대법원규칙" in filename:
        return "대법원규칙"
    elif "시행규칙" in filename:
        return "시행규칙"
    elif "시행령" in filename:
        return "시행령"
    elif "법률" in filename or "(법률)" in filename:
        return "법률"
    else:
        return "기타"


def normalize_metadata(raw_metadata: Dict, category: str, source_file: str, chunk_id: str) -> Dict:
    """
    청킹 파일의 불일치한 메타데이터를 표준 스키마로 변환

    표준 스키마:
        필수: doc_type, title, number, enforcement_date, category, source_file,
              article_number, article_title, chunk_index, is_deleted
        권장: chapter, chapter_title, section, abbreviation
        선택: is_tenant_protection, is_tax_related, is_delegation, is_penalty_related,
              other_law_references, term_name, term_category, term_number
    """
    normalized = {}

    # 1. doc_type 추출
    normalized["doc_type"] = extract_doc_type(source_file)

    # 2. title 통합 (law_title / decree_title / rule_title / glossary_title)
    title = (
        raw_metadata.get("law_title") or
        raw_metadata.get("decree_title") or
        raw_metadata.get("rule_title") or
        raw_metadata.get("glossary_title") or
        "Unknown"
    )
    # 약칭 제거 (예: "부동산 거래신고 등에 관한 법률 시행령 ( 약칭: 부동산거래신고법 시행령" → "부동산 거래신고 등에 관한 법률 시행령")
    if " ( 약칭:" in title:
        title = title.split(" ( 약칭:")[0].strip()
    normalized["title"] = title

    # 3. number 통합
    normalized["number"] = (
        raw_metadata.get("law_number") or
        raw_metadata.get("decree_number") or
        raw_metadata.get("rule_number") or
        ""
    )

    # 4. 필수 필드
    normalized["enforcement_date"] = raw_metadata.get("enforcement_date", "")
    normalized["category"] = category
    normalized["source_file"] = source_file
    normalized["article_number"] = raw_metadata.get("article_number", "")
    normalized["article_title"] = raw_metadata.get("article_title", "")

    # chunk_index는 나중에 일괄 처리 (동일 article_number 그룹 내 순번)
    normalized["chunk_index"] = 0
    normalized["is_deleted"] = raw_metadata.get("is_deleted", False)

    # 5. 권장 필드 (있으면 포함)
    if "chapter" in raw_metadata:
        normalized["chapter"] = raw_metadata["chapter"]
    if "chapter_title" in raw_metadata:
        normalized["chapter_title"] = raw_metadata["chapter_title"]
    if "section" in raw_metadata:
        normalized["section"] = raw_metadata["section"]
    if "abbreviation" in raw_metadata and raw_metadata["abbreviation"]:
        normalized["abbreviation"] = raw_metadata["abbreviation"]

    # 6. Boolean 선택 필드 (true일 때만 포함)
    if raw_metadata.get("is_tenant_protection"):
        normalized["is_tenant_protection"] = True
    if raw_metadata.get("is_tax_related"):
        normalized["is_tax_related"] = True
    if raw_metadata.get("is_delegation"):
        normalized["is_delegation"] = True
    if raw_metadata.get("is_penalty_related"):
        normalized["is_penalty_related"] = True

    # 7. 참조 관계
    if "other_law_references" in raw_metadata and raw_metadata["other_law_references"]:
        normalized["other_law_references"] = json.dumps(raw_metadata["other_law_references"], ensure_ascii=False)

    # 8. 용어집 전용
    if "term_name" in raw_metadata:
        normalized["term_name"] = raw_metadata["term_name"]
        normalized["term_category"] = raw_metadata.get("term_category", "")
        normalized["term_number"] = raw_metadata.get("term_number", 0)

    return normalized


def assign_chunk_indices(documents: List[Dict]) -> List[Dict]:
    """
    동일한 title + article_number를 가진 문서들에게 chunk_index 부여

    예시:
        주택임대차보호법 제3조 → chunk_index: 0, 1, 2, ...
    """
    # title + article_number로 그룹화
    groups = {}
    for doc in documents:
        key = f"{doc['metadata']['title']}||{doc['metadata']['article_number']}"
        if key not in groups:
            groups[key] = []
        groups[key].append(doc)

    # 각 그룹 내에서 chunk_index 부여
    for key, group in groups.items():
        for idx, doc in enumerate(group):
            doc['metadata']['chunk_index'] = idx

    return documents


async def embed_documents(test_mode: bool = False, category_filter: str = None):
    """
    청킹 파일들을 ChromaDB에 임베딩

    Args:
        test_mode: True면 1개 카테고리만 처리 (2_임대차_전세_월세)
        category_filter: 특정 카테고리만 처리 (예: "2_임대차_전세_월세")
    """
    start_time = datetime.now()
    print(f"\n{'='*60}")
    print(f"ChromaDB 재임베딩 시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # 1. ChromaDB 초기화
    print("[1] ChromaDB 초기화 중...")
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    try:
        chroma_client.delete_collection("korean_legal_documents")
        print("   [OK] 기존 컬렉션 삭제 완료")
    except Exception as e:
        print(f"   [INFO] 기존 컬렉션 없음 (새로 생성)")

    collection = chroma_client.create_collection(
        name="korean_legal_documents",
        metadata={"hnsw:space": "cosine"}
    )
    print("   [OK] 새 컬렉션 생성 완료\n")

    # 2. 임베딩 모델 로드
    print("[2] 임베딩 모델 로드 중...")
    model = SentenceTransformer(str(MODEL_PATH))
    print("   [OK] kure_v1 모델 로드 완료\n")

    # 3. 카테고리 결정
    if test_mode:
        categories_to_process = ["2_임대차_전세_월세"]
        print("   [EMOJI] 테스트 모드: 2_임대차_전세_월세만 처리\n")
    elif category_filter:
        categories_to_process = [category_filter]
        print(f"   [EMOJI] 필터 모드: {category_filter}만 처리\n")
    else:
        categories_to_process = CATEGORIES
        print("   [EMOJI] 전체 모드: 모든 카테고리 처리\n")

    # 4. 카테고리별 처리
    total_embedded = 0
    total_files = 0
    category_stats = {}

    for category in categories_to_process:
        category_path = CHUNKED_DIR / category

        if not category_path.exists():
            print(f"   [WARN] 카테고리 폴더 없음: {category}")
            continue

        print(f"[3] 처리 중: {category}")
        print(f"   경로: {category_path}\n")

        json_files = list(category_path.glob("*_chunked.json"))
        category_embedded = 0

        for json_file in json_files:
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    chunks = json.load(f)

                if not chunks:
                    print(f"   [WARN] 빈 파일: {json_file.name}")
                    continue

                # 메타데이터 정규화
                documents = []
                for idx, chunk in enumerate(chunks):
                    normalized_meta = normalize_metadata(
                        raw_metadata=chunk.get("metadata", {}),
                        category=category,
                        source_file=json_file.name,
                        chunk_id=chunk["id"]
                    )

                    # ID를 완전히 고유하게 만들기 (파일명_인덱스)
                    unique_id = f"{json_file.stem}_{idx}"

                    documents.append({
                        "id": unique_id,
                        "text": chunk["text"],
                        "metadata": normalized_meta
                    })

                # chunk_index 부여
                documents = assign_chunk_indices(documents)

                # 배치 처리 (100개씩)
                batch_size = 100
                for i in range(0, len(documents), batch_size):
                    batch = documents[i:i+batch_size]

                    ids = [doc["id"] for doc in batch]
                    texts = [doc["text"] for doc in batch]
                    metadatas = [doc["metadata"] for doc in batch]

                    # 임베딩 생성
                    embeddings = model.encode(texts, show_progress_bar=False).tolist()

                    # ChromaDB 추가
                    collection.add(
                        ids=ids,
                        documents=texts,
                        embeddings=embeddings,
                        metadatas=metadatas
                    )

                category_embedded += len(documents)
                total_embedded += len(documents)
                total_files += 1

                print(f"   [OK] {json_file.name}: {len(documents)}개 문서 임베딩 완료")

            except Exception as e:
                print(f"   [FAIL] {json_file.name} 처리 실패: {e}")

        category_stats[category] = category_embedded
        print(f"   [EMOJI] {category} 완료: {category_embedded}개 문서\n")

    # 5. 최종 통계
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print(f"\n{'='*60}")
    print(f"[OK] ChromaDB 재임베딩 완료!")
    print(f"{'='*60}")
    print(f"[EMOJI] 처리 통계:")
    print(f"   - 처리 파일: {total_files}개")
    print(f"   - 임베딩 문서: {total_embedded}개")
    print(f"   - 소요 시간: {duration:.2f}초")
    print(f"\n[EMOJI] 카테고리별 통계:")
    for category, count in category_stats.items():
        print(f"   - {category}: {count}개")
    print(f"\n종료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    return total_embedded, category_stats


def verify_embedding():
    """임베딩 결과 검증"""
    print("\n[EMOJI] 임베딩 결과 검증 중...\n")

    chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = chroma_client.get_collection("korean_legal_documents")

    # 전체 문서 개수
    total_count = collection.count()
    print(f"[OK] 전체 문서 개수: {total_count}\n")

    # Unknown title 개수 확인
    try:
        unknown_results = collection.get(
            where={"title": "Unknown"},
            limit=10000
        )
        unknown_count = len(unknown_results['ids'])
        print(f"[WARN] Unknown title 문서: {unknown_count}개 ({unknown_count/total_count*100:.1f}%)")

        if unknown_count > 0:
            print(f"   샘플 ID: {unknown_results['ids'][:5]}")
    except Exception as e:
        print(f"   Unknown 체크 실패: {e}")

    # doc_type 분포
    print(f"\n[EMOJI] doc_type 분포:")
    for doc_type in ["법률", "시행령", "시행규칙", "대법원규칙", "용어집", "기타"]:
        try:
            results = collection.get(
                where={"doc_type": doc_type},
                limit=10000
            )
            count = len(results['ids'])
            if count > 0:
                print(f"   - {doc_type}: {count}개 ({count/total_count*100:.1f}%)")
        except:
            pass

    # 카테고리 분포
    print(f"\n[EMOJI] 카테고리 분포:")
    for category in CATEGORIES:
        try:
            results = collection.get(
                where={"category": category},
                limit=10000
            )
            count = len(results['ids'])
            if count > 0:
                print(f"   - {category}: {count}개 ({count/total_count*100:.1f}%)")
        except:
            pass

    # 샘플 메타데이터 확인
    print(f"\n[EMOJI] 샘플 메타데이터 (첫 3개 문서):")
    sample = collection.get(limit=3, include=["metadatas"])
    for i, (doc_id, metadata) in enumerate(zip(sample['ids'], sample['metadatas']), 1):
        print(f"\n   [{i}] {doc_id}")
        print(f"       title: {metadata.get('title')}")
        print(f"       doc_type: {metadata.get('doc_type')}")
        print(f"       category: {metadata.get('category')}")
        print(f"       article_number: {metadata.get('article_number')}")
        print(f"       chunk_index: {metadata.get('chunk_index')}")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    import asyncio

    # 명령행 인자 처리
    if len(sys.argv) > 1:
        mode = sys.argv[1]

        if mode == "--test":
            print("[EMOJI] 테스트 모드로 실행 (2_임대차_전세_월세만 처리)")
            asyncio.run(embed_documents(test_mode=True))
            verify_embedding()
        elif mode == "--full":
            print("[EMOJI] 전체 모드로 실행 (모든 카테고리 처리)")
            asyncio.run(embed_documents(test_mode=False))
            verify_embedding()
        elif mode.startswith("--category="):
            category = mode.split("=")[1]
            print(f"[EMOJI] 카테고리 필터 모드로 실행: {category}")
            asyncio.run(embed_documents(test_mode=False, category_filter=category))
            verify_embedding()
        else:
            print("❌ 잘못된 인자입니다.")
            print("사용법:")
            print("  python embed_legal_documents.py --test")
            print("  python embed_legal_documents.py --full")
            print("  python embed_legal_documents.py --category=2_임대차_전세_월세")
    else:
        print("사용법:")
        print("  python embed_legal_documents.py --test          # 테스트 (1개 카테고리)")
        print("  python embed_legal_documents.py --full          # 전체 재임베딩")
        print("  python embed_legal_documents.py --category=2_임대차_전세_월세  # 특정 카테고리만")
